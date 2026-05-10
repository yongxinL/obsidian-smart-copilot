---
phase: 01b-auth-security-primitives
status: planning_complete
score: n/a
note: "This document tracks verification state across the planning → execution lifecycle. Before execution: all checks are PRE-VERIFICATION. After execution: populated with actual results."
---

# Phase 1b: Auth Security Primitives — Verification Report

**Phase Goal:** All auth/security primitives in place — CLI user creation, JWT sessions, MCP bearer tokens, Fernet-encrypted provider keys, PostgreSQL RLS per-user isolation.

**Status:** `planning_complete` — implementation pending

**Current stage:** Planning. Execution has not started. All references to file contents, code patterns, and function signatures below are derived from **plan documents only** — they do not represent implemented code.

---

## Planning Completeness

| Check | Status | Notes |
|-------|--------|-------|
| 8 plans written | ✅ Complete | Plans 01–08 covering Wave 0 through Wave 5 |
| VALIDATION.md exists | ✅ Complete | 79 task rows, nyquist_compliant: true |
| PATTERNS.md exists | ✅ Complete | Pattern mappings for new files |
| DISCUSSION-LOG.md exists | ✅ Complete | All 4 discussion areas resolved |
| CONTEXT.md exists | ✅ Complete | User decisions locked in |
| RESEARCH.md exists | ✅ Complete | Technical research on landmines |
| No missing requirements | ✅ Complete | All AUTH-01..10, TEST-02 covered |
| No unimplemented acceptance criteria | ✅ Complete | All ROADMAP success criteria mapped |

---

## Pre-Implementation Baseline (from plans)

> The following tables document what the verification should look like **after** execution. Status values indicate planning-stage confidence, not implementation state.

### ROADMAP Success Criteria Mapping

| # | Criterion | Plan(s) | Implementation Note | Status |
|---|-----------|---------|---------------------|--------|
| 1 | Admin can create a user via CLI; credentials stored as argon2id hash | 01, 04, 08 | Plan 04: `password.py` with asyncio.to_thread; Plan 08: CLI dispatch | PRE-VERIFICATION |
| 2 | Login issues short-lived JWT (15min) + long-lived refresh; atomic rotation | 04, 06 | Plan 04: `tokens.py` HS256; Plan 06: `sessions.py rotate_refresh()` in single transaction | PRE-VERIFICATION |
| 3 | MCP bearer tokens stored as SHA-256 hashes only; plaintext shown once | 04, 08 | Plan 04: `mcp_tokens.py` secrets.token_urlsafe(32); Plan 08: CLI command | PRE-VERIFICATION |
| 4 | Provider API keys Fernet-encrypted at rest; never returned in responses | 03, 06, 08 | Plan 03: `encryption.py` MultiFernet; Plan 06: `ProviderKeyResponse` Field(exclude=True) | PRE-VERIFICATION |
| 5 | PostgreSQL RLS enforces per-user isolation; system context bypasses RLS | 02, 05, 08 | Plan 02: 0002 migration with 22 policies; Plan 05: `dependencies.py` SET/RESET + PoolEvents.reset | PRE-VERIFICATION |

### Security Landmine Coverage

| # | Landmine | CVE/Issue | Plan(s) | Mitigation in Plan | Status |
|---|----------|-----------|---------|--------------------|--------|
| LM-01 | GUC leak via connection pool | Security | 05 | `database.py` PoolEvents.reset scrubs app.* GUCs | PRE-VERIFICATION |
| LM-02 | JWT algorithm confusion | CVE-2024-33663 | 04 | `algorithms=["HS256"]` non-empty list in decode | PRE-VERIFICATION |
| LM-03 | Argon2 raises not returns False | Logic bug | 04 | Catches VerifyMismatchError, InvalidHashError, VerificationError | PRE-VERIFICATION |
| LM-04 | Fernet TTL footgun | Logic bug | 03 | No `ttl=` argument in `decrypt_provider_key()` | PRE-VERIFICATION |
| LM-05 | SET app.x = $1 illegal | SQL error | 05 | Uses `set_config('app.x', :val, false)` raw SQL | PRE-VERIFICATION |
| LM-06 | Argon2 blocks event loop | Concurrency | 04 | `asyncio.to_thread` wrapper on all argon2 calls | PRE-VERIFICATION |
| LM-09 | login_attempts needs own txn | DB logic | 06 | `record_login_attempt()` commits in dedicated session | PRE-VERIFICATION |

### Required Artifacts (from plans)

| Artifact | Plan | Expected Behavior | Status |
|----------|------|------------------|--------|
| `server/app/auth/password.py` | 04 | argon2id hash/verify in asyncio.to_thread; catches LM-03 | PRE-VERIFICATION |
| `server/app/auth/tokens.py` | 04 | HS256 JWT, algorithms=["HS256"], sid/jti claims | PRE-VERIFICATION |
| `server/app/auth/mcp_tokens.py` | 04 | PREFIX="scmcp_", secrets.token_urlsafe(32), sha256 hash | PRE-VERIFICATION |
| `server/app/auth/context.py` | 04 | Frozen slotted dataclass, SYSTEM_USER_ID, no FastAPI imports | PRE-VERIFICATION |
| `server/app/auth/core.py` | 05 | validate_jwt/validate_refresh/validate_bearer → AuthResult, no HTTPException | PRE-VERIFICATION |
| `server/app/auth/deps.py` | 07 | require_user/admin/fresh_auth, D-16 admin_reauth_required envelope | PRE-VERIFICATION |
| `server/app/auth/audit.py` | 05 | write_audit_log, AsyncSession, no FastAPI imports | PRE-VERIFICATION |
| `server/app/auth/middleware.py` | 07 | TrustedProxyMiddleware, left-most XFF, CIDR allowlist | PRE-VERIFICATION |
| `server/app/encryption.py` | 03 | MultiFernet from day 1, no ttl= in decrypt, FernetKeyMissing | PRE-VERIFICATION |
| `server/app/dependencies.py` | 05 | session_with_rls sets 3 GUCs, RESET in finally; get_db_session canonical | PRE-VERIFICATION |
| `server/app/database.py` | 05 | PoolEvents.reset listener (LM-01 guard) | PRE-VERIFICATION |
| `server/alembic/versions/0002_phase_1b_auth.py` | 02 | 22 RLS policies, system-bypass OR clause, SYSTEM_USER_ID seed | PRE-VERIFICATION |
| `server/app/models/login_attempt.py` | 02 | 6 cols, no FK to users | PRE-VERIFICATION |
| `server/app/models/session.py` | 02 | admin_fresh_until column | PRE-VERIFICATION |
| `server/app/services/users.py` | 06 | normalize_username, create_user refuses 'system' | PRE-VERIFICATION |
| `server/app/services/sessions.py` | 06 | check_rate_limit sliding window, record_login_attempt own flush | PRE-VERIFICATION |
| `server/app/services/mcp_tokens.py` | 06 | create/verify/revoke; verify updates last_used_at | PRE-VERIFICATION |
| `server/app/services/provider_keys.py` | 06 | resolve_key user-first → system → MissingProviderKey | PRE-VERIFICATION |
| `server/app/routes/auth.py` | 07 | /auth/login: rate-check → record → verify → wipe → issue | PRE-VERIFICATION |
| `server/app/routes/admin.py` | 07 | /reauth stamps admin_fresh_until; /_demo_destructive requires fresh_auth | PRE-VERIFICATION |
| `server/app/main.py` | 07 | startup rejects missing Fernet key; global HTTPException flattening | PRE-VERIFICATION |
| `server/app/logging/redaction.py` | 01 | structlog redaction for 7 D-27 keys, recursive | PRE-VERIFICATION |
| `server/app/cli/main.py` | 08 | argparse CLI, user/mcp/provider subcommands | PRE-VERIFICATION |
| `server/app/cli/user.py` | 08 | `user create` via session_with_rls | PRE-VERIFICATION |
| `server/app/cli/mcp_token.py` | 08 | `mcp token create/list/revoke`, plaintext shown once | PRE-VERIFICATION |
| `server/app/cli/provider_key.py` | 08 | `provider key set` via session_with_rls | PRE-VERIFICATION |
| `server/app/scheduler/jobs/prune_login_attempts.py` | 07 | Module-level async function (APScheduler-pickle-safe) | PRE-VERIFICATION |
| `server/app/scheduler/run.py` | 07 | AsyncIOScheduler, hourly prune job | PRE-VERIFICATION |
| `server/app/mcp/server.py` | 07 | validate_bearer imported, main_http raises NotImplementedError | PRE-VERIFICATION |
| `server/app/tests/auth/conftest.py` | 01 | seed_user_a/b, seed_admin_user, seed_basic_user, admin_token_pair | PRE-VERIFICATION |
| `server/app/tests/auth/test_rls_isolation.py` | 01 | 5 TEST-02 cases (LM-01, LM-01, D-30) | PRE-VERIFICATION |
| `server/app/tests/auth/test_acceptance.py` | 08 | End-to-end Phase 1b acceptance | PRE-VERIFICATION |
| `server/app/tests/auth/test_security_invariants.py` | 08 | 7 grep-gate security invariant tests | PRE-VERIFICATION |
| `server/app/tests/auth/test_cli.py` | 08 | CLI integration tests | PRE-VERIFICATION |
| `server/requirements.txt` | 01 | python-jose>=3.4, argon2-cffi>=23.1, structlog>=24, cryptography>=42 | PRE-VERIFICATION |
| `server/pyproject.toml` | 08 | `smartcopilot` entry point | PRE-VERIFICATION |

### Key Integration Points (from plans)

| From | To | Via | Status |
|------|----|-----|--------|
| `routes/auth.py` | `services/sessions.py` | `session_with_rls(system_operation_context())` | PRE-VERIFICATION |
| `routes/auth.py` | `auth/password.py` | `verify_password()` | PRE-VERIFICATION |
| `routes/admin.py` | `services/sessions.py` | `set_admin_fresh()` | PRE-VERIFICATION |
| `auth/deps.py` | `auth/core.py` | `validate_jwt()`, `validate_bearer()` | PRE-VERIFICATION |
| `auth/deps.py` | `services/sessions.py` | `ctx.session_id` | PRE-VERIFICATION |
| `dependencies.py` | `database.py` | `session_with_rls` + PoolEvents.reset | PRE-VERIFICATION |
| `main.py` | `encryption.py` | `fernet()` in `_fail_startup_if_missing_secrets` | PRE-VERIFICATION |
| `main.py` | `logging/redaction.py` | `configure_logging()` in lifespan | PRE-VERIFICATION |
| `main.py` | `auth/middleware.py` | `app.add_middleware(TrustedProxyMiddleware, ...)` | PRE-VERIFICATION |
| `services/provider_keys.py` | `encryption.py` | `encrypt_provider_key()` / `decrypt_provider_key()` | PRE-VERIFICATION |
| `cli/user.py` | `services/users.py` | `create_user()` via `session_with_rls` | PRE-VERIFICATION |
| `scheduler/run.py` | `scheduler/jobs/prune_login_attempts.py` | `add_job(prune_login_attempts, ...)` | PRE-VERIFICATION |
| `mcp/server.py` | `auth/core.py` | `from app.auth.core import validate_bearer` | PRE-VERIFICATION |

---

## Issues Identified During Planning Review

The following issues were found during plan review and should be addressed before execution begins. All are documented in DISCUSSION-LOG and/or plan acceptance criteria.

### Critical (may break execution)

| ID | File | Issue | Recommendation |
|----|------|-------|----------------|
| PL-01 | `session_with_rls` (Plan 05) | Must use `yield session` not `return session` — Plans 06/07/08 use `async for session in session_with_rls(ctx):` which requires an async generator | Verify Plan 05 implementation uses `yield`; Plans 06/07/08 test code also uses `async for` |
| PL-02 | Plan 06 `sessions.py` | `record_login_attempt()` commits INSIDE the function via `session.flush()`. Plan 07 `routes/auth.py` must NOT call `session.commit()` after calling this. | Document this contract explicitly in Plan 06; Plan 07 test code must not double-commit |
| PL-03 | Plan 07 conftest | JWT_SIGNING_KEY env var naming — pydantic-settings `case_sensitive=False` maps `jwt_signing_key` field to `JWT_SIGNING_KEY` (uppercase). Project convention uses `SMARTCOPILOT_` prefix. | Decide: use `JWT_SIGNING_KEY` (match pydantic-settings convention) or `SMARTCOPILOT_JWT_SIGNING_KEY` (project convention) and update Plans 07/08 test fixtures accordingly |

### High (may cause test failures)

| ID | File | Issue | Recommendation |
|----|------|-------|----------------|
| PL-04 | Plan 08-02 `test_cli.py` | `_run_cli` creates nested event loop: `cli_main` calls `asyncio.run()` internally; threading.Thread wraps another `asyncio.run()`. May cause "asyncio.run() cannot be called from a running event loop" | Use `subprocess.run(['python', '-m', 'app.cli.main', ...])` or patch `cli_main` to accept loop parameter |
| PL-05 | Plan 07-02 `test_login.py` | `async with await _new_client() as c:` — incorrect. `AsyncClient` context manager protocol returns a coroutine that resolves to the client. Should be `async with _new_client() as c:` | Fix: remove `await` on the context manager expression |
| PL-06 | System user UUID | No canonical constant defined in auth/context.py — Plans 02/05 reference `00000000-0000-0000-0000-000000000001` as both literal string and quoted UUID | Define `SYSTEM_USER_ID: Final[UUID] = UUID("00000000-0000-0000-0000-000000000001")` in Plan 04 context.py; all other plans import from there |

### Medium (code quality / consistency)

| ID | File | Issue | Recommendation |
|----|------|-------|----------------|
| PL-07 | All plans | No type stubs for `alembic env` imports — SQLAlchemy models not available at migration time | Document in Plan 02: migration 0002 should use `from app.models import *` carefully, or use raw SQL for RLS policies |
| PL-08 | Plan 01-01 | `requirements.txt` grep check requires exact match on `python-jose[cryptography]>=3.4` — version pinning may differ | Verify actual requirements.txt pin matches plan's grep command |

---

## Post-Execution Verification Plan

After implementation, the following automated checks and human verifications apply:

### Automated (via `pytest -x -q server/app/tests/auth/`)

| Test File | What It Verifies | Landmine |
|----------|-----------------|----------|
| `test_redaction.py` | 7 D-27 keys scrubbed at all nesting levels | D-27 |
| `test_password.py` | argon2 verify returns False on mismatch, blocks to thread | LM-03, LM-06 |
| `test_jwt_tokens.py` | algorithms=["HS256"] source-level gate | LM-02 |
| `test_mcp_tokens_unit.py` | 256-bit token generation, SHA-256 hash | AUTH-04 |
| `test_encryption.py` | MultiFernet round-trip, no TTL in decrypt | LM-04 |
| `test_trusted_proxy_unit.py` | left-most XFF derivation | AUTH-08 |
| `test_rls_isolation.py` | 5 TEST-02 cases (GUC leak, cross-user block, system bypass, pool reset) | LM-01, TEST-02 |
| `test_login.py` | login flow, rate limit, wipe on success | AUTH-02/03/08 |
| `test_mcp_tokens_integration.py` | verify updates last_used_at, <5s revocation | AUTH-04/05 |
| `test_provider_keys.py` | resolve order, Field(exclude=True) | AUTH-09/10, D-28 |
| `test_admin_reauth.py` | freshness window, 403 on expiry | AUTH-06/07 |
| `test_audit_log.py` | write_audit_log called on login/reauth | AUTH-06 |
| `test_trusted_proxy.py` | CIDR allowlist, XFF chain handling | AUTH-08 |
| `test_scheduler_prune.py` | prune_job async function, APScheduler integration | D-09 |
| `test_security_invariants.py` | 7 grep-gate tests (all landmines + D-17/D-28) | LM-01..06 |
| `test_cli.py` | user create, mcp token, provider key set | AUTH-01/04 |
| `test_acceptance.py` | end-to-end Phase 1b happy path + startup fail | All criteria |

### Human Verification Required

| Test | Why Human | Expected Result |
|------|-----------|-----------------|
| Rate limit 11th attempt | Sliding window requires real DB + time-based data | HTTP 429 with retry_after_seconds |
| Startup rejection without Fernet key | Subprocess exit code | Exit 1, stderr contains FATAL |
| admin_fresh_until expiry mid-request | DB writes + timestamp comparison | 403 with admin_reauth_required envelope |

---

## Verification Status History

| Date | Stage | Status | Notes |
|------|-------|--------|-------|
| 2026-05-08 | Planning | planning_complete | Initial plan review; PRE-VERIFICATION status for all artifacts |
| TBD | Post-Plan-01 | pending | Wave 0 complete |
| TBD | Post-Plan-02 | pending | Migration 0002 applied |
| TBD | Post-Plan-03 | pending | Encryption seam implemented |
| TBD | Post-Plan-04 | pending | Auth core implemented |
| TBD | Post-Plan-05 | pending | Dependencies + database pool |
| TBD | Post-Plan-06 | pending | Services layer |
| TBD | Post-Plan-07 | pending | Routes + middleware |
| TBD | Post-Plan-08 | pending | CLI + security invariants + acceptance |
| TBD | Post-execution | pending | Full suite run, human verification |

---

_Planning review: 2026-05-08_
_Note: This document will be updated to `in_progress` → `verified` after execution. All `PRE-VERIFICATION` entries become `VERIFIED` or `FAILED` based on actual test results._