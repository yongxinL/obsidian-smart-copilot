# Phase 1b: Auth + Security Primitives - Discussion Log

**Date:** 2026-05-08
**Mode:** discuss-phase (default, interactive)
**Audience:** humans only — for audit/retrospective. NOT consumed by researcher/planner/executor.

---

## Setup

**Phase boundary** (from ROADMAP.md):
> All authentication and authorization primitives are in place — users can be created via CLI, JWT sessions issued, MCP bearer tokens generated, provider API keys stored encrypted, and PostgreSQL RLS enforces per-user data isolation.

**Carried forward from Phase 1a (no re-asking):**
- All auth-domain SQLAlchemy models exist: `users`, `sessions`, `mcp_tokens`, `provider_keys`
- `dependencies.py:get_db_session` already implements canonical `RESET app.current_user_id` in `finally:` (Phase 1a defensive cleanup shape)
- `Settings` (pydantic-settings) has `smartcopilot_fernet_key` slot
- Tests run against real PostgreSQL via testcontainers — no mocks
- Alembic migrations named by purpose/domain (D-06 from 01a)

**Locked by PRD** (presented to user but not discussed):
- argon2-cffi minima (REQ-400), JWT short-lived + revocable refresh (REQ-401), 10/15min rate limit shape (REQ-402)
- 256-bit MCP tokens, SHA-256 hashed, presented once, revocable in 5s, last_used_at (REQ-410–414)
- Two roles only: admin/user (REQ-420)
- 60-min freshness window (REQ-430)
- `SMARTCOPILOT_TRUST_PROXY` + IP allowlist + left-most XFF (REQ-422–425)
- `app.current_user_id` GUC drives RLS (REQ-331, REQ-340–341)
- MultiFernet rotation deferred post-Phase 5

**Areas presented for discussion:**
1. Token lifetimes & refresh rotation
2. Rate-limit storage backend
3. Step-up freshness representation
4. Auth middleware + OperationContext shape

**Areas the user selected:** all four.

---

## Area 1 — Token lifetimes & refresh rotation

### Q1.1: Access JWT TTL?
**Options presented:**
- 15 minutes (Recommended) — industry default; pairs well with 7–30 day refresh
- 5 minutes — tighter blast radius, more refresh chatter
- 30 minutes — looser, less chatter, larger leak window

**User selected:** 15 minutes.

### Q1.2: Refresh token TTL?
**Options presented:**
- 30 days (Recommended) — comfortable for intermittent homelab users
- 7 days — tighter, more frequent re-logins
- 90 days — looser, longer-lived sessions

**User selected:** 30 days.

### Q1.3: Refresh rotation policy on /auth/refresh?
**Options presented:**
- Rotate-and-revoke (Recommended) — issue new pair, delete old hash; theft signal on replay
- Reuse — same refresh returns new access; no theft detection
- Sliding window — bump expires_at on use; harder to revoke

**User selected:** Rotate-and-revoke.

### Q1.4: JWT identity binding beyond `sub`?
**Options presented:**
- sub + role + jti (Recommended) — fast RBAC + audit correlation
- sub only — DB lookup of role per request
- sub + role + role_version — overkill for 2-role system

**User selected:** sub + role + jti.

---

## Area 2 — Rate-limit storage backend

### Q2.1: Where do login-failure counters live?
**Options presented:**
- DB-backed `login_attempts` table (Recommended) — multi-worker safe, auditable
- In-process per-worker dict — fastest but splits across `--workers 2`
- Postgres advisory locks + counter row — equivalent correctness, more parts

**User selected:** Option 1 (DB-backed). Refined:
- Schema: `(ip, username, attempted_at, optional user_agent, optional request_id)`
- Written via system/internal context; not exposed to user RLS
- Indexed query for sliding-window count
- Pruning job, retention 24–72h

### Q2.2: Sliding-window vs fixed-window?
**Options presented:**
- Sliding window (Recommended) — `attempted_at >= now() - interval '15 min'`, no boundary-flip exploit
- Fixed 15-min bucket — simpler bookkeeping, exposes boundary exploit

**User selected:** Sliding window. Refined: reject with `rate_limited` and include `retry_after_seconds`.

### Q2.3: Wipe attempts on successful login?
**Options presented:**
- Wipe on success (Recommended) — honest user shouldn't be one mistake from lockout
- Leave attempts in place — simpler, locks out real users

**User selected:** Wipe on success. Refined: clear failed rows for that exact `(normalized_username, client_ip)` pair on success; record successful logins separately in `audit_log`.

### Q2.4: Pruning of `login_attempts` rows?
**Options presented:**
- APScheduler hourly job (Recommended)
- Inline prune on each insert
- Defer to Phase 6

**User selected:** APScheduler hourly job. Refined: default retention 24 hours (not 1) — better short-term security/debug visibility while keeping table tiny.

---

## Area 3 — Step-up freshness representation

### Q3.1: Where is `admin_fresh_until` stored?
**Options presented:**
- Column on `sessions` (Recommended) — zero extra query; logout/refresh-rotate drops freshness
- Separate `fresh_auth_grants` table — overkill for v1
- JWT claim re-issued on /admin/reauth — cannot revoke before JWT expiry

**User selected:** Option 1 (sessions column). Refined: middleware checks (1) authenticated, (2) `role='admin'`, (3) session not revoked/expired, (4) `sessions.admin_fresh_until > now()`. Else `admin_reauth_required`.

### Q3.2: What does /admin/reauth accept?
**Options presented:**
- Password only (Recommended) — Phase 1b primary path
- Password OR admin-scoped MCP token — adds scoping concept 1b doesn't need
- Password + 2nd factor (TOTP) — out of scope

**User selected:** Password only. Refined: argon2 verify against `users.password_hash`; on success `UPDATE sessions SET admin_fresh_until = now() + interval '60 minutes'`. MCP-token path returns `not_implemented` / `unsupported_factor` (future-compatible reservation). No MFA/TOTP in 1b.

### Q3.3: Which routes are flagged `requires_fresh_auth`?
**Options presented:**
- Per-route Depends decorator (Recommended) — explicit, grep-able, fails closed
- Path-prefix rule — relies on URL discipline, easy to bypass
- Centralized policy table — drift risk

**User selected:** Per-route Depends. Refined: normal admin reads use `Depends(require_admin)`; destructive admin routes add `Depends(require_fresh_auth)` on top.

### Q3.4: What happens on freshness expiry mid-request?
**Options presented:**
- 403 with structured `admin_reauth_required` envelope (Recommended) — REQ-434
- Generic 403 forbidden — fails REQ-434
- Auto-prompt via WebSocket — out of scope (no /ws yet)

**User selected:** Option 1. Specified envelope:
```json
{"error":{"code":"admin_reauth_required","message":"Fresh admin authentication is required.","details":{"reauth_url":"/api/v1/admin/reauth","freshness_window_minutes":60}}}
```
Client/CLI prompts for password, calls `/admin/reauth`, retries.

---

## Area 4 — Auth middleware + OperationContext shape

### Q4.1: Where is `OperationContext` constructed?
**Options presented:**
- Per-transport adapter, single shared `auth_core` (Recommended) — pure functions; transports build OperationContext
- Single FastAPI middleware with MCP HTTP as sub-app — couples MCP to FastAPI lifecycle, contradicts CLAUDE.md
- Pure FastAPI Depends tree only — drift risk for non-REST transports

**User selected:** Option 1. Refined:
- `server/app/auth/core.py` — pure transport-neutral validators returning `AuthResult`
- REST adapter: middleware/Depends → `OperationContext(transport="rest", remote=True)`
- MCP HTTP adapter: bearer token → `OperationContext(transport="mcp_http", remote=True)`
- MCP stdio: `SMARTCOPILOT_MCP_TOKEN` validated **once at process startup** → `OperationContext(transport="mcp_stdio", remote=False)` reused for every JSON-RPC request

### Q4.2: How does `app.current_user_id` get SET?
**Options presented:**
- Inside `get_db_session` after auth dependency (Recommended) — single ownership of session lifecycle
- Inside auth middleware before route handler — splits SET/RESET across modules
- Inside service layer via OperationContext — pollutes services with infra

**User selected:** Option 1. Refined: `get_db_session` owns SET app.current_user_id, optionally SET app.current_user_role / app.request_id, yield session, RESET all `app.*` GUCs in `finally`. Not in middleware. Not in services.

### Q4.3: How does MCP HTTP share auth core?
**Options presented:**
- Both processes import `auth/core.py` (Recommended) — same Python package, no IPC
- MCP HTTP calls REST `/api/v1/internal/validate-token` — adds roundtrip + recursion
- Replicate auth logic in mcp/server.py — drift over 11 phases

**User selected:** Option 1. Refined: MCP HTTP launched via `python -m app.mcp.server --http`, separate process but same package; imports `app.auth.core`. Both REST and MCP HTTP build `OperationContext` and call services through shared `session_with_rls(ctx)` helper.

### Q4.4: `remote=true` derivation per REQ-521?
**Options presented:**
- Transport-driven only (Recommended) — drop CWD heuristic (PRD says it's not load-bearing)
- Transport + CWD heuristic — more code, same security
- Per-token policy on mcp_tokens row — adds column 1b doesn't need

**User selected:** Option 1. Refined rules:
- mcp_stdio → remote=False
- mcp_http → remote=True
- rest → remote=True
- cli → remote=False
- system/background jobs → remote=False only when using designated system OperationContext (system UUID)
Trust boundary: transport + token scope + OperationContext + RLS + path validation + service-level permission checks. Not CWD.

---

## Wrap-up question

> "We've discussed all four areas. Anything still unclear before I write CONTEXT.md?"

**User selected:** "I'm ready for context."

---

## Claude's discretion (locked without explicit user question — flagged in CONTEXT.md)

- Argon2 params: `time_cost=3, memory_cost=64MiB, parallelism=1` (PRD minima — D-23)
- Fernet seam: `MultiFernet([primary])` from day 1; rotation deferred (D-24)
- `audit_log` entries on `/admin/reauth` success/failure and refresh-token rotation (D-25, D-26)
- structlog field redaction filter for password/token/encrypted_key keys (D-27)
- `Field(exclude=True)` on every Pydantic model touching `provider_keys` (D-28)
- Trusted-proxy IP source: socket peer in allowlist + left-most XFF (D-29)
- TEST-02 location and shape: `server/app/tests/test_rls_isolation.py` against testcontainer pgvector db (D-30)

## Deferred ideas (captured for later phases)

- Admin-scoped MCP tokens for `/admin/reauth` — Phase 6 likely
- Active MultiFernet rotation procedure — post-Phase 5 per PRD
- MFA / TOTP / passkeys — out of scope for v1
- Per-token `remote` flag on `mcp_tokens` — not in 1b
- WebSocket fresh-auth challenge — Phase 1c/1d when /ws exists
- Per-scope fresh-auth grants — single global window in v1
- Prometheus metrics for auth events — Phase 6
- `prune_audit_log` parallel job — Phase 6

---

*End of discussion log.*
