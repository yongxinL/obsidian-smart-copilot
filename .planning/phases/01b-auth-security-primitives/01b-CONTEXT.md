# Phase 1b: Auth + Security Primitives - Context

**Gathered:** 2026-05-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Stand up the auth/security primitives every later phase depends on:
- argon2-cffi password hashing (REQ-400)
- JWT session pair: short-lived access JWT + revocable refresh token, refresh stored as SHA-256 hash in `sessions` (REQ-401)
- Login rate-limiting at 10 failures / 15 min / (IP, username) (REQ-402)
- Per-user named MCP bearer tokens — 256-bit, SHA-256-hashed, revocable within 5s, `last_used_at` updated on every auth (REQ-410–414)
- RBAC with two roles only: `admin`, `user`; admin operations audited in `audit_log` (REQ-420–421)
- Trusted-proxy header support (`SMARTCOPILOT_TRUST_PROXY` + IP allowlist) for accurate client IP under reverse proxy (REQ-422–425)
- Step-up "fresh" authentication for destructive admin operations within a 60-min window via `POST /api/v1/admin/reauth` (REQ-430–434)
- Fernet-encrypted provider API keys at rest; encrypted column never returned in any API response; container refuses to start without `SMARTCOPILOT_FERNET_KEY` (REQ-110, REQ-303, REQ-602)
- RLS GUC enforcement: `SET app.current_user_id` + `RESET` in `finally:` discipline integrated with the auth pipeline (REQ-330–341)
- TEST-02: assert no `app.current_user_id` GUC bleeds across pooled connections after request scope exits

This phase establishes `server/app/auth/` as the canonical auth package and the `OperationContext` shape consumed by every later transport (REST, MCP HTTP, MCP stdio, CLI).

</domain>

<decisions>
## Implementation Decisions

### Token Lifetimes & Refresh Rotation
- **D-01:** Access JWT TTL = **15 minutes**. Standard short-lived access window.
- **D-02:** Refresh token TTL = **30 days**. Comfortable for intermittent homelab users.
- **D-03:** Refresh rotation policy = **rotate-and-revoke**. `/auth/refresh` issues a new (access JWT, refresh token) pair and DELETEs the old refresh-token row from `sessions`. Replay of an old refresh = forced logout (theft signal).
- **D-04:** Access JWT claims = `sub` (user_id), `role`, `jti`. Role is a 15-min snapshot — acceptable for a 2-role system that rarely changes; refresh re-issues with current role.

### Rate-Limit Storage Backend
- **D-05:** New table `login_attempts(id, ip, username, attempted_at, user_agent NULL, request_id NULL)` — Alembic migration `0002_add_login_attempts.py`.
- **D-06:** `login_attempts` is written via a system/internal context; **NOT** exposed under user RLS. The auth path is the only writer.
- **D-07:** Sliding-window enforcement: count rows where `attempted_at >= now() - interval '15 minutes'` AND `(ip, username)` match. When count ≥ 10, reject with `rate_limited` and include `retry_after_seconds` in the error envelope (the time until the oldest in-window row falls out).
- **D-08:** On successful login: `DELETE FROM login_attempts WHERE username = :u AND ip = :ip` so a user who fumbled their password and finally got it right is not one mistake from lockout. Successful logins are recorded in `audit_log`, not `login_attempts`.
- **D-09:** Pruning via APScheduler hourly job (reuses Phase 1a's `apscheduler` supervisord process). Default retention = **24 hours** (configurable via settings). The 15-min enforcement window only needs ~15 min of history; 24h gives short-term debug/audit visibility while keeping the table tiny at homelab scale.
- **D-10:** Username is **normalized at the application layer before write/query** (case-fold + strip). `users.username` is the canonical form.

### Step-Up Freshness Representation
- **D-11:** Add column `admin_fresh_until TIMESTAMPTZ NULL` to `sessions` (Alembic migration `0002` or a sibling). NOT stored in JWT (cannot be revoked before JWT expiry; survives logout).
- **D-12:** `POST /api/v1/admin/reauth` re-validates the admin's password via argon2 against `users.password_hash`. On success: `UPDATE sessions SET admin_fresh_until = now() + interval '60 minutes' WHERE id = :current_session_id`.
- **D-13:** `require_fresh_auth` dependency checks all four:
  1. authenticated user
  2. `role = 'admin'`
  3. session row exists, not revoked, not expired
  4. `sessions.admin_fresh_until > now()`
- **D-14:** Phase 1b factor = **password only**. Admin-scoped MCP-token path returns `not_implemented` / `unsupported_factor`. The PRD's "password or admin-scoped MCP token" remains future-compatible — Phase 1b reserves the factor enum without implementing the MCP-token path. No MFA/TOTP in 1b.
- **D-15:** Per-route enforcement via FastAPI `Depends`:
  - normal admin reads: `Depends(require_admin)`
  - destructive/security-sensitive admin routes: `Depends(require_fresh_auth)` (which itself depends on `require_admin`)
  No path-prefix rule, no central policy table — explicit, grep-able, fails closed if a new route forgets to add it.
- **D-16:** Failure response shape (HTTP 403):
  ```json
  {
    "error": {
      "code": "admin_reauth_required",
      "message": "Fresh admin authentication is required.",
      "details": {
        "reauth_url": "/api/v1/admin/reauth",
        "freshness_window_minutes": 60
      }
    }
  }
  ```
  Client/CLI prompts for password, calls `/admin/reauth`, retries the original request.

### Auth Middleware + OperationContext Shape
- **D-17:** New module `server/app/auth/core.py` exposes pure, transport-neutral functions:
  - `validate_jwt(token: str) -> AuthResult` — for REST access JWT
  - `validate_refresh(token: str) -> AuthResult` — for `/auth/refresh`
  - `validate_bearer(token: str) -> AuthResult` — for MCP bearer tokens (HTTP and stdio share)
  - `AuthResult` is a small dataclass: `{user_id, role, session_id?, mcp_token_id?, error?}`
  - **No FastAPI imports** in `auth/core.py`. Returns `AuthResult`, never raises HTTP exceptions.
- **D-18:** Each transport has its own thin adapter that builds `OperationContext` from `AuthResult`:
  - **REST:** `auth/middleware.py` (or `Depends(get_operation_context)`) — extracts `Authorization: Bearer <jwt>` or session cookie, calls `validate_jwt`, builds `OperationContext(transport="rest", remote=True, ...)`.
  - **MCP HTTP:** auth hook in `mcp/server.py` — extracts `Authorization: Bearer <mcp_token>`, calls `validate_bearer`, builds `OperationContext(transport="mcp_http", remote=True, ...)`.
  - **MCP stdio:** stdio entry-point — reads `SMARTCOPILOT_MCP_TOKEN` env var **once at process startup**, calls `validate_bearer`, builds `OperationContext(transport="mcp_stdio", remote=False, ...)` reused for every JSON-RPC request from that process.
- **D-19:** `OperationContext` (dataclass, frozen) fields per REQ-520: `user_id: UUID, role: Literal['admin','user'], transport: Literal['rest','mcp_http','mcp_stdio','cli','system'], remote: bool, client_name: str, request_id: str, session_id: UUID | None, mcp_token_id: UUID | None`.
- **D-20:** RLS GUC integration owned by `get_db_session`:
  - Depend chain: route → `Depends(get_operation_context)` → `Depends(get_db_session)`.
  - `get_db_session` extends today's Phase 1a shape: after `get_operation_context` has authenticated, execute `SET app.current_user_id = :user_id` (and optionally `SET app.current_user_role = :role`, `SET app.request_id = :request_id`). RESET all `app.*` GUCs in `finally:`.
  - Helper alias `session_with_rls(ctx)` may be exposed for service-layer ergonomics; it's `get_db_session` parameterized by an explicit context (used by APScheduler jobs and CLI, where there is no FastAPI request scope).
  - The existing Phase 1a defensive `RESET app.current_user_id` becomes the canonical cleanup for all `app.*` keys.
- **D-21:** MCP HTTP shares auth_core by import — **not** by HTTP callback. MCP HTTP runs as a separate `mcp-http` supervisord process launched via `python -m app.mcp.server --http`, but it lives in the same Python package and imports `app.auth.core` directly. No cross-process auth-as-a-service, no replicated logic.
- **D-22:** `remote` flag is **transport-driven only**:
  - `mcp_stdio` → `remote=False`
  - `mcp_http` → `remote=True`
  - `rest` → `remote=True`
  - `cli` → `remote=False`
  - `system` (background jobs) → `remote=False` only when using the designated **system `OperationContext`** with `user_id` = system UUID
  Drop the REQ-521 CWD-inside-/vaults heuristic — PRD itself flags it as not load-bearing. Trust boundary enforcement relies on `transport` + token scope + `OperationContext` + RLS + path validation + explicit service-level permission checks.

### Claude's Discretion (small follow-ups not asked but locked)
- **D-23:** Argon2 parameters: `time_cost=3, memory_cost=64*1024 (64 MiB), parallelism=1` — at PRD minima (REQ-400). Conservative for homelab CPU; can raise post-Phase-1 once perf is measured.
- **D-24:** Fernet handling: load `SMARTCOPILOT_FERNET_KEY` at startup; container exits non-zero if missing or invalid. Wrap in `MultiFernet([primary])` from day 1 so a future rotation is a one-line settings change. PRD explicitly defers actual rotation to post-Phase-5 — this is just the seam.
- **D-25:** `audit_log` entry on `/admin/reauth` success: `event='admin_reauth', user_id, session_id, ip, ts`. On failure: `event='admin_reauth_failed', user_id, session_id, ip, ts, reason='invalid_password'`.
- **D-26:** `audit_log` entry on every refresh-token rotation success/failure (rotation failure on stale-refresh = potential theft signal).
- **D-27:** structlog field redaction: filter must redact `password`, `password_hash`, `encrypted_key`, `token`, `token_hash`, `refresh_token`, `access_jwt` keys before log emission.
- **D-28:** `encrypted_key` is enforced absent from response schemas via `Field(exclude=True)` on every Pydantic model that touches `provider_keys` (CLAUDE.md), not via post-hoc filtering.
- **D-29:** Trusted-proxy IP source: when `SMARTCOPILOT_TRUST_PROXY=true` AND the direct socket peer IP is in the allowlist, use **left-most** `X-Forwarded-For` IP as client IP for rate-limiting and `audit_log`. Otherwise use the socket peer.
- **D-30:** RLS isolation test (TEST-02) lives in `server/app/tests/test_rls_isolation.py`: spins testcontainer pgvector db, creates two users, executes a request scope as user A, then asserts (a) the same pooled connection used by user B sees no leaked `app.current_user_id`, and (b) cross-user reads of `pages` (or any RLS-enabled table seeded with two rows) return only the caller's row.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents (researcher, planner) MUST read these before planning or implementing.**

### Product Requirements
- `docs/product_requirements_document_v26.05.md` — authoritative PRD (v26.05.1). Phase 1b directly implements: §7.3 (RLS policies), §7.4 (RLS session context discipline), §8.1–8.5 (Authentication and Authorization), §10.3 (Errors), §24.2 (Provider key resolution order).

### Planning Artifacts
- `.planning/REQUIREMENTS.md` — structured requirements AUTH-01 through AUTH-10, TEST-02 scoped to Phase 1b
- `.planning/ROADMAP.md` — phase boundary and 5 success criteria for Phase 1b
- `.planning/PROJECT.md` — out-of-scope list (no MFA, no Redis, etc.)
- `.planning/phases/01a-container-data-layer/01a-CONTEXT.md` — Phase 1a decisions: D-09 module ownership (database.py vs dependencies.py vs main.py), D-13 settings via pydantic-settings + .env

### Architecture Constraints (from CLAUDE.md)
- `encrypted_key` fields MUST use `Field(exclude=True)` on every Pydantic response model — never filtered after the fact
- Do NOT import FastAPI types (`Request`, `Response`, `HTTPException`) in `services/`. Services take `OperationContext`, not request objects
- RLS discipline: `SET app.current_user_id` (not `SET LOCAL`); always `RESET` in `finally:`
- Fernet: `encrypted_key` column MUST be `BYTEA`; `MultiFernet` is the rotation seam; never log key or intermediate values
- argon2-cffi: PRD min memory ≥ 64 MiB, iterations ≥ 3, parallelism ≥ 1
- python-jose for JWT (HS256)
- Two-worker uvicorn — rate-limit storage MUST be shared (postgres, not in-process)

### Existing Code (already shipped in Phase 1a)
- `server/app/models/user.py` — `users` table (id, username, email, password_hash, role, is_active)
- `server/app/models/session.py` — `sessions` table (id, user_id, token_hash, expires_at, created_at) — Phase 1b adds `admin_fresh_until` column
- `server/app/models/mcp_token.py` — `mcp_tokens` table (id, user_id, name, token_hash, last_used_at, revoked_at)
- `server/app/models/provider_key.py` — `provider_keys` table (id, user_id, provider, encrypted_key BYTEA, key_hint) with unique (user_id, provider)
- `server/app/dependencies.py:get_db_session` — already implements `RESET app.current_user_id` in `finally:`. Phase 1b extends to also `SET` after auth.
- `server/app/database.py` — async engine + pgvector connect-event registration
- `server/app/settings.py` — pydantic-settings with `smartcopilot_fernet_key` slot already present
- `alembic/` — migration infra; new `0002_*.py` migrations needed for `login_attempts` table and `sessions.admin_fresh_until` column

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `dependencies.py:get_db_session` — extend in place; the RESET-in-finally is canonical and already there
- All four auth-domain SQLAlchemy models (User, Session, McpToken, ProviderKey) — created up-front per D-05; Phase 1b adds Alembic column to Session and a new login_attempts model
- `settings.Settings` — add `smartcopilot_trust_proxy: bool`, `smartcopilot_trusted_proxy_cidrs: list[str]`, `jwt_access_ttl_seconds: int = 900`, `jwt_refresh_ttl_seconds: int = 2592000`, `jwt_signing_key: str`, `argon2_*` knobs, `login_rate_limit_window_seconds: int = 900`, `login_rate_limit_max_failures: int = 10`, `login_attempts_retention_hours: int = 24`, `admin_fresh_window_minutes: int = 60` to existing pydantic-settings
- `main.py` lifespan — register the auth router and the trusted-proxy middleware here; lifespan body itself stays minimal per Phase 1a D-09
- APScheduler process from Phase 1a — register the hourly `prune_login_attempts` job

### Established Patterns (from Phase 1a)
- One file per domain in `models/` (D-07) — new model `models/login_attempt.py`
- Alembic migrations named by purpose/domain (D-06) — `0002_add_login_attempts.py`, `0003_add_session_fresh_auth.py` (or combine into single `0002_phase_1b_auth.py` — planner's call)
- Settings live in `pydantic-settings` reading `.env` — extend, don't fork
- Tests use real PostgreSQL via testcontainers (D-01–D-04) — no mocks; RLS isolation test runs against a real DB

### Integration Points
- `auth/core.py` (NEW) ← imported by REST middleware/Depends, MCP HTTP server, MCP stdio entry-point, CLI
- `auth/middleware.py` (NEW) → produces `OperationContext` from FastAPI request; chains into `get_db_session`
- `mcp/server.py` (NEW or stub) → uses MCP SDK auth hook to call `auth_core.validate_bearer`, build OperationContext
- `routes/auth.py` (NEW) → `/auth/login`, `/auth/refresh`, `/auth/logout`, `/api/v1/admin/reauth`
- `services/users.py`, `services/mcp_tokens.py`, `services/provider_keys.py` (NEW) — pure transport-agnostic; take OperationContext, no FastAPI types
- `cli/` (stub for Phase 1b — full CLI is Phase 1d): `smartcopilot user create`, `smartcopilot mcp token create/list/revoke`, `smartcopilot provider key set` need just enough surface to satisfy Phase 1b success criterion 1
- `apscheduler` supervisord process — register `prune_login_attempts` hourly job
- `audit_log` model (already exists in 01a) — write entries from auth flows

</code_context>

<specifics>
## Specific Patterns and References

- **OperationContext dataclass** (`auth/context.py`): frozen dataclass; `transport` is `Literal['rest','mcp_http','mcp_stdio','cli','system']`. Constructed by transport adapters; consumed by services. Never imported by `auth/core.py` (auth_core returns `AuthResult`, transports build `OperationContext`).
- **AuthResult** (`auth/core.py`): small frozen dataclass `{user_id: UUID | None, role: str | None, session_id: UUID | None, mcp_token_id: UUID | None, error: str | None}`. Returns `error="invalid_token"` / `"missing_auth"` / `"service_unavailable"` per REQ-511 — transport adapter maps these to HTTP/MCP error responses.
- **Refresh rotation atomicity** — `/auth/refresh` MUST be a single transaction: validate → DELETE old session row → INSERT new session row → return new pair. Concurrent refresh from two clients with the same refresh token = one wins, the other gets `invalid_token` (theft signal).
- **`session_with_rls(ctx)` helper** (`dependencies.py`): an alternate constructor of `get_db_session` parameterized by an explicit `OperationContext`. Used by APScheduler jobs (no FastAPI request) and CLI (no HTTP transport) to set the same RLS GUCs.
- **Stdio MCP one-shot auth** — stdio process validates `SMARTCOPILOT_MCP_TOKEN` once at startup; the resulting `OperationContext` is reused for every JSON-RPC request from that process. Per-request re-validation would require a DB hit on every tool call and is unnecessary because stdio process lifetime ≈ session lifetime.
- **Trusted-proxy CIDR allowlist** — `SMARTCOPILOT_TRUSTED_PROXY_CIDRS` env var, comma-separated. Parsed with `ipaddress.ip_network`. Middleware at the very front of the request pipeline computes `client_ip` and stashes it on `request.state.client_ip`; rate-limit logic reads from there.
- **Migration shape** (planner discretion: combine or split): `0002_phase_1b_auth.py` adds `login_attempts` table + index on (ip, username, attempted_at) + `sessions.admin_fresh_until` column. Single migration is fine because both ship in Phase 1b.
- **Fernet seam** — `app/encryption.py` exposes `encrypt_provider_key(plaintext: str) -> bytes` and `decrypt_provider_key(ciphertext: bytes) -> str`, internally using `MultiFernet([Fernet(primary_key)])`. Adding a second key later = list extension; no call-site change.

</specifics>

<deferred>
## Deferred Ideas

- **Admin-scoped MCP tokens** for `/admin/reauth` factor — Phase 1b returns `not_implemented` for this path; revisit when a use case appears (Phase 6 admin surfaces likely)
- **MultiFernet active rotation** — wired as a seam (D-24) but actual rotation procedure (`smartcopilot admin rotate-fernet`) is post-Phase-5 per PRD
- **MFA / TOTP / passkeys** — explicitly out of scope for v1
- **Per-token `remote` flag on `mcp_tokens`** — not in 1b; transport drives `remote` instead
- **WebSocket fresh-auth challenge** — defer to when WebSocket client flows exist (Phase 1c/1d)
- **Per-scope fresh-auth grants** (e.g., per-vault, per-job) — single global freshness window in v1; revisit if multiple admin scopes emerge
- **Prometheus metrics for auth events** (login success/fail rate, fresh-auth grants/expiries, MCP token last-used distribution) — Phase 6 (Admin Surfaces + Observability)
- **APScheduler `prune_audit_log` parallel job** — `audit_log` retention policy is a Phase 6 concern; 1b only adds entries, doesn't prune

</deferred>

---

*Phase: 1b — Auth + Security Primitives*
*Context gathered: 2026-05-08*
*Areas discussed: Token lifetimes & refresh rotation, Rate-limit storage backend, Step-up freshness representation, Auth middleware + OperationContext shape*
