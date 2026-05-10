# Phase 1b: Code Review Report

**Reviewed:** 2026-05-10T00:00:00Z
**Depth:** standard
**Files Reviewed:** 50
**Status:** issues_found

## Summary

Reviewed 50 source files across auth, services, routes, models, CLI, and tests for Phase 1b (Auth + Security Primitives). The implementation is generally well-structured with strong security discipline: constant-time blind login, proper JWT allowlisting, RLS GUC hygiene, argon2 threading, and Fernet TTL awareness all correctly implemented.

One critical runtime issue was found: three settings used by `main.py` and `routes/admin.py` are referenced but not declared in `Settings`, which will cause `AttributeError` at startup when those code paths execute.

## Critical Issues

### CR-01: Missing settings cause AttributeError at startup

**File:** `server/app/settings.py`
**Lines:** (class end) — missing fields

**Issue:** Three settings are referenced in production code paths but never declared in `Settings`:

1. `settings.admin_fresh_window_minutes` — used in `routes/admin.py:72` (`set_admin_fresh` call) and `routes/admin.py:79` (response body). This is D-12's 60-minute freshness window.
2. `settings.smartcopilot_trust_proxy` — used in `main.py:63` to configure `TrustedProxyMiddleware`
3. `settings.smartcopilot_trusted_proxy_cidrs` — used in `main.py:64` as the allowlist

When the application starts (or when any admin route is hit), Pydantic will raise `AttributeError: object has no attribute 'admin_fresh_window_minutes'` before any request is processed.

**Fix:** Add to the `Settings` class in `server/app/settings.py`:

```python
    # Admin step-up fresh auth (D-12)
    admin_fresh_window_minutes: int = Field(default=60)

    # Trusted proxy (D-29 / REQ-422-425)
    smartcopilot_trust_proxy: bool = Field(default=False)
    smartcopilot_trusted_proxy_cidrs: list[str] = Field(default_factory=list)
```

---

## Warnings

### WR-01: Missing JWT access TTL setting

**File:** `server/app/settings.py:32`
**Issue:** `jwt_access_ttl_seconds` has a default of 900 (15 minutes, D-01) which is correct, but the JWT module comments reference "D-01: 15-min default" while `server/app/auth/tokens.py` hardcodes no TTL value in `issue_access_jwt`. The TTL flows through `settings.jwt_access_ttl_seconds` at the call site (`services/sessions.py:111`). This is functionally correct, but the comment in `tokens.py:26` ("15-min default") is misleading — the default is in `settings.py`, not in `tokens.py`. No user-facing bug, but the misleading comment could confuse future maintainers.

**Fix:** Update the docstring in `server/app/auth/tokens.py:26` to clarify:
```python
"""Issue a short-lived HS256 JWT.

The TTL is passed from settings.jwt_access_ttl_seconds (default: 900s).
"""

```

---

## Info

### IN-01: Test stubs with pytest.skip are correctly marked

**Files:** Multiple test files (`test_acceptance.py`, `test_admin_reauth.py`, `test_audit_log.py`, `test_login.py`, `test_encryption.py`, `test_mcp_tokens_integration.py`, `test_mcp_tokens_unit.py`, `test_password.py`, `test_provider_keys.py`, `test_rls_isolation.py`, `test_scheduler_prune.py`, `test_trusted_proxy.py`, `test_trusted_proxy_unit.py`)
**Issue:** All test files use `pytest.skip("Wave 0 stub — implemented in Plan ...")` as placeholders. These are correctly tagged with `pytestmark = [pytest.mark.integration]` or `pytestmark = [pytest.mark.unit]`. No action needed.

### IN-02: Security invariants CI test is skip-safe

**File:** `server/app/tests/auth/test_security_invariants.py`
**Issue:** The `_grep` helper calls `subprocess.run(["grep", ...])` and returns an empty list if `FileNotFoundError` is raised, causing all invariant tests to pass trivially if `grep` is missing. This is acceptable as a CI-level test; developers running locally should have `grep` available.

**Fix (optional):** Convert to `pytest.skip("grep not available")` pattern for clarity.

---

## Verification: Security Landmine Checklist

| Landmine | Rule | Status |
|----------|------|--------|
| #1 | Pool reset scrubs GUCs | PASS — `database.py:48-54` executes RESET on every pool reset |
| #2 | jwt.decode requires algorithms= | PASS — `auth/tokens.py:53-57` passes `algorithms=[ALGORITHM]` |
| #3 | argon2 uses asyncio.to_thread | PASS — `password.py:38,44` offload correctly |
| #4 | Fernet decrypt without ttl= | PASS — grep found 0 violations |
| #5 | No SET app.* = $1 (use set_config) | PASS — `dependencies.py` uses `set_config` correctly |
| #6 | Dummy hash for constant-time blind login | PASS — `routes/auth.py:38` pre-computes `_DUMMY_HASH` |
| #9 | record_login_attempt in own transaction | PASS — `services/sessions.py:45-51` uses `session.begin()` |

## Verification: D-17 Transport Neutrality

| Module | Imports FastAPI? |
|--------|-----------------|
| `auth/context.py` | No |
| `auth/core.py` | No |
| `auth/password.py` | No |
| `auth/tokens.py` | No |
| `auth/mcp_tokens.py` | No |
| `auth/audit.py` | No |
| `services/mcp_tokens.py` | No |
| `services/provider_keys.py` | No |
| `services/sessions.py` | No |
| `services/users.py` | No |

All service modules correctly avoid FastAPI imports. The `providers_keys.py` schema correctly uses `Field(exclude=True)` for `encrypted_key`.

---

_Reviewed: 2026-05-10T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_