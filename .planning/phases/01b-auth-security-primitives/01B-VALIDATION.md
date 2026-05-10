---
phase: 1b
slug: auth-security-primitives
status: ready
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-08
plans: 8
waves: 6
---

# Phase 1b — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (+ pytest-asyncio 1.x, testcontainers-python with pgvector image) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) — established in Phase 1a |
| **Quick run command** | `pytest -x -q server/app/tests/auth/` |
| **Full suite command** | `pytest -q server/app/tests/` |
| **Estimated runtime** | ~120 seconds (testcontainers boot ~15s; ~55 Phase 1b auth tests + 7 Phase 1a integration tests) |

---

## Sampling Rate

- **After every task commit:** Run `pytest -x -q server/app/tests/auth/` (quick run)
- **After every plan wave:** Run `pytest -q server/app/tests/` (full suite)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

> One row per task across all 8 plans. Updated by execute-phase to flip Status (⬜ → ✅).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01 | 01 | 0 | TEST-02 | T-1b-10 | python-jose>=3.4 + structlog>=24 + .env.example documents new secrets | grep | `grep -q "python-jose\[cryptography\]>=3.4" server/requirements.txt` | ✅ | ⬜ pending |
| 01-02 | 01 | 0 | AUTH-02,03,07,09 | — | Settings exposes Phase 1b knobs (D-01/02/12/23/29) | grep | `grep -q "argon2_memory_cost: int = Field(default=64 \* 1024)" server/app/settings.py` | ✅ | ⬜ pending |
| 01-03 | 01 | 0 | — | T-1b-10 | structlog redaction processor scrubs 7 D-27 keys at every nesting level | unit | `pytest -x -q server/app/tests/auth/test_redaction.py` | ❌ W0 | ⬜ pending |
| 01-04 | 01 | 0 | AUTH-01..10,TEST-02 | — | 14 Wave-0 test stubs collected; 13 skip; redaction tests pass | unit | `pytest --collect-only -q server/app/tests/auth/` | ❌ W0 | ⬜ pending |
| 02-01 | 02 | 1 | AUTH-03 | T-1b-04 | LoginAttempt model — 6 cols, no FK, system-internal | grep | `grep -q '__tablename__ = "login_attempts"' server/app/models/login_attempt.py` | ❌ | ⬜ pending |
| 02-02 | 02 | 1 | AUTH-07 | T-1b-03 | sessions.admin_fresh_until column added | grep | `grep -q "admin_fresh_until: Mapped\[object \| None\]" server/app/models/session.py` | ❌ | ⬜ pending |
| 02-03 | 02 | 1 | TEST-02 | T-1b-03 | 0002 migration — 22 RLS POLICY blocks + login_attempts + admin_fresh_until + system seed | integration | `pytest -x -q server/app/tests/integration/test_boot.py` | ❌ | ⬜ pending |
| 03-01 | 03 | 1 | AUTH-09 | T-1b-01 | encryption.py: encrypt/decrypt round-trip; ttl= forbidden; MultiFernet from day 1 | unit | `pytest -x -q server/app/tests/auth/test_encryption.py` | ❌ | ⬜ pending |
| 03-02 | 03 | 1 | AUTH-09 | T-1b-01 | 4 unit tests pass — Landmine #4 source-level gate enforced | unit | `pytest -x -q server/app/tests/auth/test_encryption.py` | ❌ W0 | ⬜ pending |
| 04-01 | 04 | 1 | AUTH-02,06 | — | AuthResult + OperationContext frozen dataclasses, no FastAPI imports (D-17) | grep+import | `python -c "from app.auth.context import AuthResult, OperationContext, SYSTEM_USER_ID, system_operation_context"` | ❌ | ⬜ pending |
| 04-02 | 04 | 1 | AUTH-01 | — | argon2 wrapper with asyncio.to_thread; verify returns False on mismatch (Landmine #3, #6) | unit | `pytest -x -q server/app/tests/auth/test_password.py` | ❌ W0 | ⬜ pending |
| 04-03 | 04 | 1 | AUTH-02 | T-1b-02 | jwt.decode uses algorithms=["HS256"] non-empty list (Landmine #2 / CVE-2024-33663+CVE-2025-61152) | unit | `pytest -x -q server/app/tests/auth/test_jwt_tokens.py` | ❌ W0 | ⬜ pending |
| 04-04 | 04 | 1 | AUTH-04 | T-1b-06 | 256-bit token via secrets.token_urlsafe(32); SHA-256 hex storage | unit | `pytest -x -q server/app/tests/auth/test_mcp_tokens_unit.py` | ❌ W0 | ⬜ pending |
| 05-01 | 05 | 2 | AUTH-02,04 | T-1b-02 | auth/core.py validators return AuthResult (no HTTP exceptions) | grep+import | `! grep -q "raise HTTPException" server/app/auth/core.py` | ❌ | ⬜ pending |
| 05-02 | 05 | 2 | AUTH-06 | T-1b-08 | write_audit_log helper; INSERT-only (audit_log not RLS-gated) | grep+import | `python -c "from app.auth.audit import write_audit_log"` | ❌ | ⬜ pending |
| 05-03 | 05 | 2 | TEST-02 | T-1b-03 | dependencies.get_db_session SETs 3 GUCs via set_config (Landmine #5); session_with_rls helper | grep | `grep -q "set_config('app.current_user_id', :uid, false)" server/app/dependencies.py` | ❌ | ⬜ pending |
| 05-04 | 05 | 2 | TEST-02 | T-1b-03 | database.py PoolEvents.reset listener — Landmine #1 fail-safe | grep | `grep -q '@event.listens_for(engine.sync_engine, "reset")' server/app/database.py` | ❌ | ⬜ pending |
| 05-05 | 05 | 2 | TEST-02 | T-1b-03 | 5 RLS isolation tests pass — TEST-02 contract | integration | `pytest -x -q server/app/tests/auth/test_rls_isolation.py` | ❌ W0 | ⬜ pending |
| 06-01 | 06 | 3 | AUTH-01,02,03 | T-1b-04,07 | services/users (normalize, refuses 'system') + services/sessions (atomic rotate, sliding window, own-txn record) | grep+import | `! grep -rE "^(from\|import) (fastapi\|starlette)" server/app/services/` | ❌ | ⬜ pending |
| 06-02 | 06 | 3 | AUTH-04,05 | T-1b-06 | verify_token DB-only; last_used_at on every verify; <5s revocation | integration | `pytest -x -q server/app/tests/auth/test_mcp_tokens_integration.py` | ❌ W0 | ⬜ pending |
| 06-03 | 06 | 3 | AUTH-09,10 | T-1b-01 | ProviderKeyResponse Field(exclude=True); resolve order per-user → system → MissingProviderKey | integration | `pytest -x -q server/app/tests/auth/test_provider_keys.py` | ❌ W0 | ⬜ pending |
| 06-04 | 06 | 3 | AUTH-06,07 | T-1b-05 | require_user/admin/fresh_auth chain; sid claim threaded through tokens→core→deps | grep | `grep -q '"code": "admin_reauth_required"' server/app/auth/deps.py` | ❌ | ⬜ pending |
| 07-01 | 07 | 4 | AUTH-08 | — | TrustedProxyMiddleware: left-most XFF when peer in CIDR allowlist (D-29) | unit | `pytest -x -q server/app/tests/auth/test_trusted_proxy_unit.py` | ✅ | ✅ |
| 07-02 | 07 | 4 | AUTH-02,03 | T-1b-04,07 | /auth/login rate-limit-then-record-then-verify; /auth/refresh atomic rotation | integration | (covered by 07-06 acceptance) | ✅ | ✅ |
| 07-03 | 07 | 4 | AUTH-06,07 | T-1b-05,08 | /api/v1/admin/reauth + /_demo_destructive guarded by require_fresh_auth (D-15) | integration | (covered by 07-06 acceptance) | ✅ | ✅ |
| 07-04 | 07 | 4 | AUTH-03 | — | prune_login_attempts module-level coroutine (APScheduler-pickle-safe) | integration | `pytest -x -q server/app/tests/auth/test_scheduler_prune.py` | ✅ | ✅ |
| 07-05 | 07 | 4 | AUTH-09 | T-1b-09,10 | main.py startup-fail on missing Fernet/JWT keys; structlog configured; 3 routers + middleware | grep | `grep -q "FernetKeyMissing" server/app/main.py && grep -q "TrustedProxyMiddleware" server/app/main.py` | ✅ | ✅ |
| 07-06 | 07 | 4 | AUTH-02,03,06,07,08 | T-1b-04,05,07,08 | 23 integration tests across login/admin_reauth/audit/trusted_proxy | integration | `pytest -x -q server/app/tests/auth/test_login.py app/tests/auth/test_admin_reauth.py app/tests/auth/test_audit_log.py app/tests/auth/test_trusted_proxy.py` | ✅ | ✅ |
| 07-07 | 07 | 4 | — | — | D-21 MCP stub: app/mcp/__init__.py + app/mcp/server.py importing validate_bearer; main_http raises NotImplementedError | grep+import | `python -c "from app.mcp.server import main_http"` && `grep -q "validate_bearer" server/app/mcp/server.py` | ✅ | ✅ |
| 08-01 | 08 | 5 | AUTH-01,04,09 | — | smartcopilot CLI: user create + mcp token create/list/revoke + provider key set | invoke | `python -m app.cli.main --help` | ❌ | ⬜ pending |
| 08-02 | 08 | 5 | AUTH-01,04 | — | CLI smoke tests against testcontainer | integration | `pytest -x -q server/app/tests/auth/test_cli.py` | ❌ | ⬜ pending |
| 08-03 | 08 | 5 | All | T-1b-01,02,03,06,07 | Repo-wide grep gates (Landmine #1, #2, #4, #5; D-17, D-28; main startup-fail) | unit | `pytest -x -q server/app/tests/auth/test_security_invariants.py` | ❌ | ⬜ pending |
| 08-04 | 08 | 5 | AUTH-01..10,TEST-02 | All | Phase 1b acceptance — all 5 ROADMAP success criteria covered end-to-end | integration | `pytest -x -q server/app/tests/auth/test_acceptance.py::test_phase_1b_acceptance` | ❌ | ⬜ pending |
| 08-05 | 08 | 5 | All | All | This Per-Task Verification Map populated; nyquist_compliant: true | n/a | manual review | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `server/app/tests/auth/conftest.py` — shared fixtures (seed_user_a, seed_user_b, seed_admin_user, seed_basic_user, admin_token_pair)
- [ ] `server/app/tests/auth/__init__.py` — package marker
- [ ] `server/app/tests/auth/test_password.py` — stubs for AUTH-01 (4 tests)
- [ ] `server/app/tests/auth/test_jwt_tokens.py` — stubs for AUTH-02 (5 tests including source-level guard)
- [ ] `server/app/tests/auth/test_mcp_tokens_unit.py` — stubs for AUTH-04 (3 tests)
- [ ] `server/app/tests/auth/test_encryption.py` — stubs for AUTH-09 (4 tests; implemented in Plan 03)
- [ ] `server/app/tests/auth/test_trusted_proxy_unit.py` — stubs for AUTH-08 (3 tests)
- [ ] `server/app/tests/auth/test_login.py` — stubs for AUTH-02/03 (9 tests)
- [ ] `server/app/tests/auth/test_mcp_tokens_integration.py` — stubs for AUTH-04/05 (4 tests)
- [ ] `server/app/tests/auth/test_provider_keys.py` — stubs for AUTH-09/10 (4 tests)
- [ ] `server/app/tests/auth/test_admin_reauth.py` — stubs for AUTH-06/07 (7 tests)
- [ ] `server/app/tests/auth/test_audit_log.py` — stubs for AUTH-06 audit trail (4 tests)
- [ ] `server/app/tests/auth/test_trusted_proxy.py` — stubs for AUTH-08 integration (3 tests)
- [ ] `server/app/tests/auth/test_rls_isolation.py` — **headline TEST-02 (5 tests)**
- [ ] `server/app/tests/auth/test_redaction.py` — D-27 redaction (3 tests, IMPLEMENTED in Plan 01)
- [ ] `server/app/tests/auth/test_scheduler_prune.py` — D-09 prune job (2 tests)

*Wave 0 (Plan 01) must finish before any auth task in Waves 1+ is allowed to run. The conftest fixtures are the contract every other test consumes.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Container refuses to start with no `SMARTCOPILOT_FERNET_KEY` (full-stack) | AUTH-09 / success-criterion-4 | Requires full container boot under supervisord; pytest cannot easily exit-code the entrypoint. Source-level enforcement is verified by `test_security_invariants.py::test_main_has_startup_fail_check`. | `unset SMARTCOPILOT_FERNET_KEY && docker run --rm smart-copilot:dev` — must exit non-zero with FATAL on stderr |
| MCP bearer `last_used_at` updates over Streamable HTTP | AUTH-04 | Streamable HTTP integration is Phase 1d; Phase 1b verifies the service-layer path via `test_mcp_tokens_integration.py::test_last_used_at_updates_on_verify` | Phase 1b proves the service contract; Phase 1d adds the HTTP wire-up |
| Operator playbook for `MultiFernet` rotation | AUTH-09 | Procedural — defers to post-Phase-5 rotation. Phase 1b validates the seam via `test_encryption.py::test_multifernet_decrypts_with_secondary_key`. | Documented post-Phase-5 |

---

## Validation Sign-Off

- [x] All tasks have `<acceptance_criteria>` with grep-verifiable conditions
- [x] Sampling continuity: Wave 0 lands 14 stubs in Plan 01; subsequent plans replace them
- [x] Wave 0 covers all MISSING references (every AUTH-* requirement maps to ≥1 stub)
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** ready
