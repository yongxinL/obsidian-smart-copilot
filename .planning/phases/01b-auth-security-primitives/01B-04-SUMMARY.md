---
phase: 1b
plan: "04"
name: auth-primitives
subsystem: auth
tags: [AUTH-01, AUTH-02, AUTH-04]
dependency_graph:
  requires: []
  provides:
    - server/app/auth/context.py (AuthResult + OperationContext frozen dataclasses)
    - server/app/auth/password.py (hash_password/verify_password/needs_rehash)
    - server/app/auth/tokens.py (issue_access_jwt/decode_access_jwt)
    - server/app/auth/mcp_tokens.py (generate_token/sha256_token_hash)
  affects:
    - Plan 05 (auth/core.py — pure validators consume these modules)
    - Plan 06 (services — consume OperationContext)
tech_stack:
  added: [argon2-cffi, python-jose>=3.4]
  patterns: [asyncio.to_thread offload, HS256 explicit algorithms allowlist, frozen slotted dataclass]
key_files:
  created:
    - server/app/auth/__init__.py (package marker)
    - server/app/auth/context.py (AuthResult, OperationContext, SYSTEM_USER_ID, system_operation_context)
    - server/app/auth/password.py (argon2 hash/verify with to_thread)
    - server/app/auth/tokens.py (JWT HS256 encode/decode)
    - server/app/auth/mcp_tokens.py (256-bit token generation + SHA-256 hash)
    - server/app/tests/auth/test_password.py (4 tests)
    - server/app/tests/auth/test_jwt_tokens.py (5 tests)
    - server/app/tests/auth/test_mcp_tokens_unit.py (3 tests)
  modified:
    - server/app/settings.py (added argon2_*, jwt_signing_key, jwt_access_ttl_seconds, jwt_refresh_ttl_seconds)
decisions:
  - "Argon2: time_cost=3, memory_cost=64*1024, parallelism=1 — PRD minima; parallelism=1 for homelab CPU"
  - "JWT: algorithms=[ALGORITHM] non-empty list — CVE-2024-33663 + CVE-2025-61152 require python-jose>=3.4"
  - "MCP token: 256-bit via secrets.token_urlsafe(32), plaintext=scmcp_+base64, stored as SHA-256 hex"
  - "OperationContext.remote: transport-driven only (rest=True, mcp_http=True, mcp_stdio=False, cli=False, system=False)"
  - "SYSTEM_USER_ID: hardcoded 00000000-0000-0000-0000-000000000001 for system contexts (APScheduler/Alembic)"
metrics:
  duration: ~8 minutes
  tasks_completed: 4
  files_created: 8
  files_modified: 1
  tests_passed: 12
  commit: 3a85d4c
---

# Phase 1b Plan 04: Auth Primitives — Execution Summary

## One-liner

Landed the four pure auth primitives (argon2, JWT HS256, MCP token generation, OperationContext dataclasses) with no FastAPI imports, asyncio.to_thread offload, and explicit HS256 algorithms allowlist.

## Completed Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 04-01 | auth package + context.py | 3a85d4c | auth/__init__.py, auth/context.py |
| 04-02 | auth/password.py + test_password.py | 3a85d4c | auth/password.py, tests/auth/test_password.py |
| 04-03 | auth/tokens.py + test_jwt_tokens.py | 3a85d4c | auth/tokens.py, tests/auth/test_jwt_tokens.py |
| 04-04 | auth/mcp_tokens.py + test_mcp_tokens_unit.py | 3a85d4c | auth/mcp_tokens.py, tests/auth/test_mcp_tokens_unit.py |

## What Was Built

### auth/context.py — AuthResult + OperationContext (D-17, D-19, D-22)
- `AuthResult`: frozen slotted dataclass — `user_id`, `role`, `session_id`, `mcp_token_id`, `error`
- `OperationContext`: frozen slotted dataclass — `user_id`, `role`, `transport`, `remote`, `client_name`, `request_id`, `session_id`, `mcp_token_id`
- `SYSTEM_USER_ID = 00000000-0000-0000-0000-000000000001` (must match alembic 0002 seed)
- `system_operation_context()` helper for APScheduler/Alembic/CLI
- **NO FastAPI imports, NO SQLAlchemy imports** (D-17 invariant)

### auth/password.py — Argon2 with asyncio.to_thread (AUTH-01, Landmine #3, Landmine #6)
- `hash_password(plaintext) -> str`: argon2id hash via `asyncio.to_thread` (Landmine #6 — event loop protection)
- `verify_password(stored_hash, plaintext) -> bool`: catches VerifyMismatchError and returns False (Landmine #3 — does NOT raise)
- `needs_rehash(stored_hash) -> bool`: flags hashes built with old params
- `PasswordHasher` constructed at module import with settings: `time_cost=3, memory_cost=64*1024, parallelism=1`
- **No FastAPI imports**

### auth/tokens.py — JWT HS256 with explicit algorithms allowlist (AUTH-02, Landmine #2)
- `issue_access_jwt(*, user_id, role, signing_key, ttl_seconds, session_id=None) -> str`
  - Claims: `sub`, `role`, `jti`, `iat`, `nbf`, `exp`
  - Optional `sid` claim when `session_id` provided (for refresh-issued tokens)
- `decode_access_jwt(token, signing_key) -> dict`
  - `algorithms=[ALGORITHM]` non-empty list (Landmine #2 — CVE-2024-33663 + CVE-2025-61152)
  - `options={"require": ["sub", "role", "jti", "exp"]}` — missing claims cause decode error
- Source-level test `test_decode_uses_explicit_algorithms_allowlist` prevents regression
- **No FastAPI imports**

### auth/mcp_tokens.py — MCP Bearer Token Generation (AUTH-04, T-1b-06)
- `generate_token() -> tuple[str, str, str]`: returns `(plaintext, sha256_hex, last4)`
  - Plaintext: `scmcp_` prefix + 43-char base64 (256 bits entropy via `secrets.token_urlsafe(32)`)
  - SHA-256 hex stored in DB; plaintext shown once at issuance
- `sha256_token_hash(plaintext) -> str`: helper for verify path (Plan 06 services)
- **No FastAPI/SQLAlchemy imports**

### settings.py — Extended with JWT + Argon2 settings
- `jwt_signing_key: str` (no default — container fails to start if empty)
- `jwt_access_ttl_seconds: int = 900` (15 minutes, D-01)
- `jwt_refresh_ttl_seconds: int = 2592000` (30 days, D-02)
- `argon2_time_cost: int = 3`
- `argon2_memory_cost: int = 65536` (64 * 1024)
- `argon2_parallelism: int = 1`

## Security Mitigations

| Threat | Mitigation | Reference |
|--------|------------|-----------|
| T-1b-02: JWT algorithm confusion | `algorithms=["HS256"]` (non-empty list); python-jose >= 3.4 | Landmine #2 |
| T-1b-06: MCP token theft | 256-bit entropy; plaintext shown once; SHA-256 storage | Pattern 4 |
| Landmine #3: VerifyMismatchError vs False | `except (...): return False` wrapper | Pattern 1 |
| Landmine #6: argon2 event-loop block | `asyncio.to_thread()` on every hash/verify call | Pattern 1 |

## Test Results

```
pytest -x -q app/tests/auth/
  test_password.py         4 passed
  test_jwt_tokens.py        5 passed
  test_mcp_tokens_unit.py   3 passed
============================
12 passed
```

## Key Decisions Made

1. **Argon2 params at PRD minima**: `time_cost=3, memory_cost=64*1024, parallelism=1` — parallelism=1 for shared homelab CPU
2. **JWT algorithms allowlist**: `algorithms=[ALGORITHM]` (non-empty list) — CVE-2024-33663 + CVE-2025-61152 require python-jose >= 3.4
3. **MCP token format**: `scmcp_` prefix + 43-char base64 (256-bit entropy); SHA-256 hex stored
4. **Transport-driven remote**: `rest=True, mcp_http=True, mcp_stdio=False, cli=False, system=False`
5. **SYSTEM_USER_ID**: Hardcoded UUID `00000000-0000-0000-0000-000000000001` for system contexts

## Deviations from Plan

None — plan executed exactly as written.

## Verification

| Criterion | Result |
|-----------|--------|
| Frozen slotted dataclasses | 2 present (AuthResult, OperationContext) |
| No FastAPI/SQLAlchemy imports | Verified via grep on all auth/* files |
| asyncio.to_thread on hash/verify | Verified via grep |
| Exception wrapper returns False | Verified via grep |
| HS256 explicit allowlist | Verified via grep + source-level test |
| 256-bit MCP token | Verified via `secrets.token_urlsafe(32)` |
| Transport literals all 5 | `rest`, `mcp_http`, `mcp_stdio`, `cli`, `system` all present |
| Python imports clean | `python -c "from app.auth.context import ..."` passes |
| ruff check | Clean — no issues |
| pytest | 12 passed |

## Self-Check

All files exist at expected paths. Commit `3a85d4c` exists in git history. Tests pass. Ruff clean.