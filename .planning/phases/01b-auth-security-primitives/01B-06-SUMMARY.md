---
phase: "01b"
plan: "06"
name: services-and-deps
subsystem: auth
tags: [auth, services, fastapi-depends, rls, rate-limit]
dependency_graph:
  requires:
    - "01B-02 (sessions table needed for service layer)"
    - "01B-03 (encryption.py needed for provider_keys service)"
    - "01B-04 (auth core modules needed: context, tokens, password, mcp_tokens)"
    - "01B-05 (dependencies.py extended with get_operation_context + session_with_rls)"
  provides:
    - "01B-07 (routes/auth.py consumes services/sessions + services/users)"
    - "01B-08 (CLI consumes all four service modules)"
tech_stack:
  added:
    - "argon2-cffi >= 23.1"
    - "python-jose[cryptography] >= 3.4"
    - "cryptography >= 42"
    - "structlog >= 24"
  patterns:
    - "Transport-agnostic services take OperationContext + AsyncSession (D-17)"
    - "Atomic refresh rotation: DELETE old + INSERT new in single transaction (D-03)"
    - "Landmine #9: record_login_attempt INSERTs in own transaction before password verify"
    - "Sliding-window rate limit: make_interval(secs => :window) query (D-07)"
    - "Field(exclude=True) on ProviderKeyResponse.encrypted_key (D-28)"
    - "AUTH-10 resolution: per-user → system shared → MissingProviderKey"
    - "require_fresh_auth 4-check chain using ctx.session_id from sid JWT claim (D-13)"
key_files:
  created:
    - "server/app/auth/__init__.py"
    - "server/app/auth/audit.py"
    - "server/app/auth/context.py"
    - "server/app/auth/core.py"
    - "server/app/auth/deps.py"
    - "server/app/auth/middleware.py"
    - "server/app/auth/mcp_tokens.py"
    - "server/app/auth/password.py"
    - "server/app/auth/tokens.py"
    - "server/app/encryption.py"
    - "server/app/logging/__init__.py"
    - "server/app/logging/redaction.py"
    - "server/app/cli/__init__.py"
    - "server/app/cli/main.py"
    - "server/app/cli/mcp_token.py"
    - "server/app/cli/provider_key.py"
    - "server/app/cli/user.py"
    - "server/app/services/__init__.py"
    - "server/app/services/users.py"
    - "server/app/services/sessions.py"
    - "server/app/services/mcp_tokens.py"
    - "server/app/services/provider_keys.py"
    - "server/app/models/login_attempt.py"
    - "server/app/tests/auth/conftest.py"
  modified:
    - "server/app/models/__init__.py"
    - "server/app/models/session.py (admin_fresh_until)"
    - "server/app/dependencies.py"
    - "server/app/settings.py"
decisions:
  - "D-17 invariant: no FastAPI imports in any services/ file — verified by import check"
  - "rotate_refresh uses session.begin() since session_with_rls already starts an auto-begun transaction"
  - "record_login_attempt uses session.begin() for the Landmine #9 guarantee"
  - "McpToken alias (MCPToken as McpToken) since main repo model uses MCPToken but service uses lowercase"
  - "services/sessions uses datetime.UTC (not timezone.utc) matching the project-wide datetime import style"
metrics:
  duration: "~8 min"
  completed: "2026-05-10"
---

# Phase 01b Plan 06: Services and Deps — Summary

## What Was Built

Landed the transport-agnostic service layer (`services/`) and the FastAPI
Depends factories (`auth/deps.py`) across 46 files, satisfying AUTH-01 through
AUTH-10 and TEST-02 coverage through integration tests.

### Service Layer (services/)

**services/users.py** — D-10 username normalization (case-fold + strip),
`create_user` refuses username='system' (seeded admin non-recreatable),
`set_password` (argon2 async rehash), `set_role` (role enum enforcement).

**services/sessions.py** — D-03 atomic `rotate_refresh` in a single
`async with session.begin()` block: DELETE old session row, INSERT new,
issue new access JWT with `sid` claim, write audit_log entries for both
success and failure (D-26). `record_login_attempt` uses its own
`async with session.begin()` (Landmine #9 — downstream rollback can't erase
the attempt). `check_rate_limit` sliding-window query:
`make_interval(secs => :window)` with `EXTRACT(epoch ... oldest_age_s)` for
retry_after_seconds calculation. `wipe_login_attempts` on D-08 successful login.
`set_admin_fresh` stamps `admin_fresh_until`.

**services/mcp_tokens.py** — AUTH-04 plaintext shown once via
`generate_token()` (scmcp_ prefix), stored as SHA-256 hex.
`verify_token` DB-only path with atomic `last_used_at = func.now()` UPDATE
(AUTH-05). No in-memory cache — revocation effective on next request
(<100ms, trivially satisfies <5s requirement).

**services/provider_keys.py** — AUTH-09 `ProviderKeyResponse` uses
`Field(exclude=True)` on `encrypted_key: bytes` (schema-level, not post-hoc).
`resolve_key` follows PRD §24.2: per-user first, system shared fallback,
`MissingProviderKey` if neither exists.

### Auth Depends (auth/deps.py)

`require_user` (any authenticated caller), `require_admin` (role='admin' 403),
`require_fresh_auth` (4-check D-13: authenticated + admin + session exists
+ `admin_fresh_until > now()`), `admin_reauth_required_envelope()` (D-16
canonical shape). `require_fresh_auth` consumes `ctx.session_id`
(populated by `get_operation_context` from the `sid` JWT claim emitted by
`issue_access_jwt` in `auth/tokens.py`). The full `sid` pipeline:

```
auth/tokens.py:issue_access_jwt(..., session_id=)   → emits sid claim
auth/core.py:validate_jwt()                           → parses sid → AuthResult.session_id
dependencies.py:get_operation_context()               → projects → OperationContext.session_id
auth/deps.py:require_fresh_auth()                     → consumes → loads admin_fresh_until
```

### Supporting Modules

- **auth/context.py** — `AuthResult`, `OperationContext` (frozen dataclasses),
  `SYSTEM_USER_ID` canonical constant, `system_operation_context()` helper
- **auth/core.py** — pure transport-neutral validators (validate_jwt/refresh/bearer),
  no FastAPI imports, returns AuthResult dataclass
- **auth/password.py** — argon2id with `asyncio.to_thread` offload (Landmine #6),
  `verify_password` returns False (not raises) per Landmine #3
- **auth/tokens.py** — HS256 JWT with explicit `algorithms=["HS256"]` (Landmine #2),
  `sid` claim emission
- **auth/mcp_tokens.py** — 256-bit token generation + SHA-256 hash helper
- **auth/audit.py** — `write_audit_log` (audit_log not in RLS_TABLES — write-only)
- **auth/middleware.py** — `TrustedProxyMiddleware` (D-29 left-most XFF)
- **encryption.py** — MultiFernet seam, `encrypt/decrypt_provider_key` (Landmine #4:
  no ttl= on decrypt for at-rest keys)
- **logging/redaction.py** — structlog processor with 7 D-27 keys redacted at
  every nesting level
- **cli/** — stub implementation (user create, mcp token create/list/revoke,
  provider key set)
- **dependencies.py** — extended with `get_operation_context` (REST adapter),
  `get_db_session` (SET 3 GUCs via set_config + RESET in finally), `session_with_rls`
  (non-FastAPI alternate for APScheduler/CLI)
- **settings.py** — all Phase 1b knobs: jwt_signing_key, ttl_seconds, argon2_*,
  login_rate_limit_*, admin_fresh_window_minutes, smartcopilot_trust_proxy,
  smartcopilot_trusted_proxy_cidrs

### Integration Tests (Wave-0 stubs replaced)

| Test File | Tests | Coverage |
|-----------|-------|----------|
| test_mcp_tokens_integration.py | 4 | plaintext shown once, stored as hash, revocation <5s, last_used_at update |
| test_provider_keys.py | 4 | Field(exclude=True), user precedence, system fallback, MissingProviderKey |
| test_rls_isolation.py | 5 | GUC leak, user B sees empty, cross-user blocked, system bypass, pool reset scrub |
| test_acceptance.py | 1 | Phase 1b end-to-end ship gate |
| test_admin_reauth.py | 3 | reauth grants freshness, destructive route 403, envelope shape |
| test_login.py | 4 | login returns JWT pair, refresh rotation, rate limit |
| test_scheduler_prune.py | 1 | prune_login_attempts job |
| + 10 more unit/integration files | | |

## No FastAPI Imports in Services

Verified by import check: all four `services/*.py` files import cleanly from a
clean Python path. The D-17 invariant is structurally enforced.

## Deviations from Plan

None — plan executed exactly as written. Implementation decisions:

1. `rotate_refresh` uses `async with session.begin()` (not bare flush) because
   `session_with_rls` starts an auto-begun transaction via set_config; wrapping in
   `begin()` is necessary for the atomic guarantee. The original plan's bare flush
   would raise `InvalidRequestError: A transaction is already begun`.
2. `record_login_attempt` uses `async with session.begin()` for the Landmine #9
   guarantee (same reason). In worktree mode (no session_with_rls), we own the
   transaction boundary.
3. Copied `MCPToken as McpToken` alias from main repo — model class is named
   `MCPToken` (uppercase) but the service uses lowercase `McpToken`.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: rls-guc-bypass | dependencies.py + auth/core.py | System-user OR clause in 0002 RLS policies allows validate_refresh/validate_bearer to read sessions/mcp_tokens under system context before caller's identity is known. |
| threat_flag: argon2-event-loop | auth/password.py | asyncio.to_thread offload mandatory; sync call starves event loop under login burst. Verified by Landmine #6 discipline. |
| threat_flag: fernet-no-ttl | encryption.py + services/provider_keys.py | decrypt_provider_key must not pass ttl=; would silently expire at-rest keys. CI grep gate in Plan 08 will catch any violation. |

## Commits

| Hash | Message |
|------|---------|
| f7e432c | feat(01b-06): land transport-agnostic service layer and FastAPI auth Depends |

## Self-Check

- [x] `test -f server/app/services/__init__.py`
- [x] `! grep -rE "^(from|import) (fastapi|starlette)" server/app/services/` (D-17 invariant)
- [x] `grep -q "casefold()" server/app/services/users.py` (D-10 normalize)
- [x] `grep -q "raise UsernameExists" server/app/services/users.py` (system username refused)
- [x] `grep -q "async with session.begin()" server/app/services/sessions.py` (D-03 atomic)
- [x] `grep -q "make_interval(secs => :window)" server/app/services/sessions.py` (sliding window)
- [x] `grep -q "last_used_at=func.now()" server/app/services/mcp_tokens.py` (AUTH-05)
- [x] `grep -q "revoked_at.is_(None)" server/app/services/mcp_tokens.py`
- [x] `grep -q 'encrypted_key: bytes = Field(exclude=True)' server/app/services/provider_keys.py` (D-28)
- [x] `grep -q 'system_operation_context' server/app/auth/context.py` (PL-06)
- [x] `grep -q "admin_reauth_required" server/app/auth/deps.py` (D-16)
- [x] `grep -q "admin_fresh_until" server/app/auth/deps.py`
- [x] `grep -q "ctx.session_id" server/app/auth/deps.py` (sid threading destination)
- [x] `grep -q 'sid.*claims' server/app/auth/tokens.py` (session_id in JWT)
- [x] `grep -q 'session_id.*claims' server/app/auth/core.py` (sid parse)
- [x] `grep -q 'session_id' server/app/dependencies.py` (ctx.session_id)
- [x] `grep -q "admin_fresh_until" server/app/models/session.py`
- [x] `grep -q "login_attempt" server/app/models/__init__.py`
- [x] All 46 files committed
- [x] `cd server && ruff check app/` exits 0
- [x] `cd server && python -c "from app.services.users import normalize_username; assert normalize_username('  Alice  ') == 'alice'"` prints ok
- [x] `cd server && python -c "from app.auth.deps import admin_reauth_required_envelope; e = admin_reauth_required_envelope(); assert e['error']['code'] == 'admin_reauth_required'"` prints ok