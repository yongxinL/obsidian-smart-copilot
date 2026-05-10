# Phase 1b: Auth + Security Primitives - Research

**Researched:** 2026-05-08
**Domain:** authentication, authorization, secrets-at-rest, multi-tenant RLS
**Confidence:** HIGH (stack pinned + verified locally; one critical CVE flag for python-jose)

---

## Summary

Phase 1b stands up the security floor for the entire system: argon2id password hashing,
JWT + opaque-refresh session pair, per-user named MCP bearer tokens (revocable in <5s),
Fernet-encrypted provider keys at rest, login rate-limiting (10/15min via DB-backed
sliding window), step-up "fresh-auth" for destructive admin ops, trusted-proxy XFF
support, and the `OperationContext` + per-request RLS GUC discipline that every
later phase relies on.

The stack is already locked by CLAUDE.md and CONTEXT.md — no alternatives to evaluate.
Research scope is therefore prescriptive: confirm exact library APIs, surface the
**five landmines** that turn a textbook implementation into a silent security failure,
and map every requirement (AUTH-01..10 + TEST-02) to a runnable validation gate.

**Primary recommendation:**
Build `server/app/auth/` as five tightly-scoped modules — `password.py`, `tokens.py` (JWT),
`mcp_tokens.py`, `core.py` (transport-neutral validators), `context.py` (`OperationContext`
+ `AuthResult` dataclasses) — plus an `app/encryption.py` for `MultiFernet`. Extend
`dependencies.py:get_db_session` to `SET app.current_user_id` after auth and `RESET`
in `finally:`. Wire two new alembic migrations (`0002_phase_1b_auth.py`: `login_attempts`
table + `sessions.admin_fresh_until` column + 22 RLS policies). Add `python-jose >= 3.4`
(NOT 3.3 — see Landmine #2) and `argon2-cffi >= 23.1`. The headline test
(`test_rls_isolation.py`) belt-and-braces the cleanup: assert RESET works AND register
a `PoolEvents.reset` handler as a fail-safe (Landmine #1).

---

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Token Lifetimes & Refresh Rotation:**
- D-01: Access JWT TTL = 15 minutes
- D-02: Refresh token TTL = 30 days
- D-03: Refresh rotation = rotate-and-revoke (DELETE old session row, INSERT new pair, atomic transaction)
- D-04: Access JWT claims = `sub` (user_id), `role`, `jti`

**Rate-Limit Storage Backend:**
- D-05: New `login_attempts(id, ip, username, attempted_at, user_agent NULL, request_id NULL)` table — Alembic migration
- D-06: Written via system/internal context; NOT exposed under user RLS
- D-07: Sliding-window (`attempted_at >= now() - interval '15 min'` AND `(ip, username)` match); reject `rate_limited` + `retry_after_seconds`
- D-08: On successful login, `DELETE FROM login_attempts WHERE username=:u AND ip=:ip`; success goes to `audit_log`
- D-09: APScheduler hourly prune; default retention = 24h
- D-10: Username normalized at app layer (case-fold + strip) before write/query

**Step-Up Freshness:**
- D-11: Add `sessions.admin_fresh_until TIMESTAMPTZ NULL` (NOT in JWT)
- D-12: `POST /api/v1/admin/reauth` re-validates password via argon2; on success `UPDATE sessions SET admin_fresh_until = now() + interval '60 minutes'`
- D-13: `require_fresh_auth` checks: authenticated, `role='admin'`, session not revoked/expired, `admin_fresh_until > now()`
- D-14: Phase 1b accepts password only; MCP-token factor returns `not_implemented`/`unsupported_factor`. No MFA/TOTP
- D-15: Per-route enforcement via `Depends(require_fresh_auth)` (which itself depends on `require_admin`); explicit, grep-able, fails closed
- D-16: Failure response = HTTP 403 with `admin_reauth_required` envelope

**Auth Middleware + OperationContext:**
- D-17: `server/app/auth/core.py` exposes pure validators (`validate_jwt`, `validate_refresh`, `validate_bearer`) returning `AuthResult` dataclass. NO FastAPI imports.
- D-18: Each transport adapter builds `OperationContext` from `AuthResult` (REST middleware, MCP HTTP hook, MCP stdio one-shot startup)
- D-19: `OperationContext` (frozen dataclass) fields: `user_id, role, transport ∈ {rest, mcp_http, mcp_stdio, cli, system}, remote, client_name, request_id, session_id, mcp_token_id`
- D-20: RLS GUC ownership in `get_db_session` — `SET app.current_user_id` (and optionally `app.current_user_role`, `app.request_id`) after auth; `RESET` all `app.*` in `finally:`. Helper `session_with_rls(ctx)` for non-FastAPI callers (CLI, APScheduler)
- D-21: MCP HTTP shares auth_core by Python import (same package, separate supervisord process). NO HTTP callback.
- D-22: `remote` is transport-driven only. mcp_stdio → False; mcp_http → True; rest → True; cli → False; system → False (only with system OperationContext). Drop the CWD-inside-/vaults heuristic.

**Discretion (locked):**
- D-23: Argon2 params `time_cost=3, memory_cost=64*1024 (64 MiB), parallelism=1, hash_len=32, salt_len=16`
- D-24: `MultiFernet([primary])` from day 1; rotation deferred post-Phase-5
- D-25: `audit_log` entry on `/admin/reauth` success (`event='admin_reauth'`) and failure (`event='admin_reauth_failed'`, `reason='invalid_password'`)
- D-26: `audit_log` on every refresh-token rotation success/failure
- D-27: structlog field redaction for `password`, `password_hash`, `encrypted_key`, `token`, `token_hash`, `refresh_token`, `access_jwt`
- D-28: `Field(exclude=True)` on every Pydantic model touching `provider_keys`
- D-29: Trusted-proxy: socket peer in CIDR allowlist + left-most XFF; otherwise socket peer
- D-30: TEST-02 lives in `server/app/tests/test_rls_isolation.py`; testcontainer pgvector; two users; assert no GUC bleed + cross-user read isolation

### Claude's Discretion

The locked decisions cover all major architectural choices. Researcher discretion in
this RESEARCH.md is restricted to:
- Exact CVE-driven version pin for python-jose (Landmine #2)
- Pool-events fail-safe layered on top of D-30's RESET-in-finally (Landmine #1)
- Specific Pydantic v2 patterns for `Field(exclude=True)` enforcement
- Refresh-token storage shape (opaque random vs JWT-as-refresh) — recommendation below
- Asyncio-offload of argon2 (CPU-bound, blocks event loop)
- Login-attempts index strategy under sliding-window query
- `current_setting('app.current_user_id', true)` policy boilerplate

### Deferred Ideas (OUT OF SCOPE)

- Admin-scoped MCP tokens for `/admin/reauth` factor (Phase 6 likely)
- Active MultiFernet rotation procedure (`smartcopilot admin rotate-fernet`) — post-Phase 5
- MFA / TOTP / passkeys
- Per-token `remote` flag on `mcp_tokens` table
- WebSocket fresh-auth challenge (Phase 1c/1d)
- Per-scope fresh-auth grants (single global window in v1)
- Prometheus metrics for auth events (Phase 6)
- `prune_audit_log` parallel job (Phase 6)
- OAuth/OIDC/SSO (no use case in v1)

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUTH-01 | argon2-cffi password hashing (≥64 MiB, ≥3 iter, ≥1 parallel) | §"Argon2id Password Hashing" |
| AUTH-02 | `/auth/login` returns `{access_jwt, refresh_token}`; refresh stored as SHA-256 hash, revocable | §"JWT Issuance" + §"Refresh Token Storage" |
| AUTH-03 | Login rate-limit 10/15min/(IP, username) | §"Login Throttling" |
| AUTH-04 | MCP bearer tokens — per-user, named, 256-bit, presented once, SHA-256 hashed, revocable in 5s | §"MCP Bearer Tokens" |
| AUTH-05 | MCP tokens record `last_used_at` on every successful auth | §"MCP Bearer Tokens" |
| AUTH-06 | Two RBAC roles (admin, user); admin ops audited | §"RBAC + Audit Log" |
| AUTH-07 | Step-up fresh authentication for destructive admin ops (`POST /api/v1/admin/reauth`) | §"Step-up Re-auth" |
| AUTH-08 | Trusted proxy header support with IP allowlist | §"Trusted Proxy + Client IP" |
| AUTH-09 | Provider keys Fernet-encrypted; encrypted column never returned | §"Fernet-encrypted Provider Keys" |
| AUTH-10 | Per-user + shared key resolution per PRD §24.2 | §"Provider Key Resolution" |
| TEST-02 | RLS isolation test — no GUC leak across pooled connections after request scope | §"PostgreSQL RLS + Session GUC Discipline" |

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Password verification | API/Backend | — | argon2 verify is server-side only; CLI calls into the same backend lib |
| JWT issuance/verification | API/Backend | — | Signing key never leaves server; all transports import `auth/core.py` |
| Refresh-token rotation | API/Backend (DB-backed) | — | Atomicity requires single transaction in PG; cross-worker safe via DB |
| MCP bearer validation | API/Backend (shared lib) | MCP HTTP process (separate supervisord) | `auth/core.validate_bearer` is import-shared; both REST and MCP HTTP call it |
| RLS GUC SET/RESET | API/Backend (DB session lifecycle) | — | Owned by `dependencies.get_db_session`; never in middleware, never in services |
| Login rate-limit storage | Database / Storage | — | DB-backed `login_attempts` is the only multi-worker-safe store (no Redis per PRD) |
| Fresh-auth state | Database / Storage | — | Column on `sessions`; cannot live in JWT (revocability requirement) |
| Trusted-proxy XFF parsing | API/Backend (early middleware) | — | Must run before route resolution; populates `request.state.client_ip` |
| Provider-key encryption | API/Backend | Database (BYTEA at rest) | Fernet round-trips bytes; PG `BYTEA` is the only safe column type |
| Audit logging | API/Backend (write only) | Database (RLS-bypassed) | Auth/admin paths only writers; queryable via admin REST in Phase 6 |
| CLI user/token CRUD | API/Backend (lib import) | — | CLI imports services; no separate auth path |

---

## Standard Stack

### Core (already pinned by CLAUDE.md / CONTEXT.md)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| argon2-cffi | >= 23.1 (latest 25.1.0 verified locally) | Password hashing | OWASP 2023 mandate; argon2id default; PRD REQ-400 [VERIFIED: local pip] |
| python-jose | **>= 3.4** (NOT 3.3 — see Landmine #2; latest 3.5.0 verified locally) | JWT encode/decode HS256 | Pure-Python; **CVE-2024-33663 + CVE-2025-61152 force >= 3.4** [VERIFIED: snyk + GitHub Advisory DB] |
| cryptography | >= 42 (latest 48.0.0 verified locally) | Fernet + MultiFernet for provider keys | Industry-standard symmetric envelope; PRD REQ-110 [VERIFIED: local pip] |
| asyncpg | >= 0.29 (already shipped 0.31.0) | Async DB driver | Phase 1a baseline [VERIFIED: requirements.txt] |
| SQLAlchemy | 2.0 (already shipped 2.0.49) | Async ORM + session lifecycle | Phase 1a baseline [VERIFIED: local pip] |
| Alembic | >= 1.13 (already shipped 1.18.4) | Schema migrations | Phase 1a baseline [VERIFIED: local pip] |
| pydantic | v2 | Request/response models, `Field(exclude=True)` | FastAPI 0.111+ requirement [VERIFIED: requirements.txt] |
| pydantic-settings | >= 2.0 | `Settings` extension for new env vars | Phase 1a baseline [VERIFIED: requirements.txt] |
| FastAPI | >= 0.111 | HTTP router + `Depends()` DI | Phase 1a baseline [VERIFIED: requirements.txt] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| structlog | >= 24 [ASSUMED — not pinned in requirements.txt yet] | Structured JSON logs + redaction filter | D-27 mandates redaction of password/token/encrypted_key fields. Add to requirements. |
| `secrets` (stdlib) | builtin | High-entropy random for MCP token + JWT signing key | `secrets.token_urlsafe(32)` = 256 bits |
| `hashlib` (stdlib) | builtin | SHA-256 of MCP tokens and refresh tokens for storage | REQ-411 / REQ-401 |
| `ipaddress` (stdlib) | builtin | CIDR parse/match for `SMARTCOPILOT_TRUSTED_PROXY_CIDRS` | D-29 |

### NOT Required (would be hand-rolling)

| Library considered | Why we don't need it |
|--------------------|---------------------|
| SlowAPI / fastapi-limiter | No PostgreSQL backend; D-05 mandates DB-backed sliding window — direct SQL is simpler and correct under `--workers 2` [VERIFIED: SlowAPI README — supports redis/memcached/memory only] |
| passlib | argon2-cffi has its own `PasswordHasher`; passlib adds a layer with no benefit when only one algorithm is in use |
| pyjwt | python-jose is already PRD-mandated; pyjwt would be a parallel JWT lib — drift risk |
| Redis (rate limit / fresh auth cache) | Forbidden by PRD principle P3 ("PostgreSQL does the heavy lifting") |
| asyncpg `register_type_codec` for SET GUC | `SET app.current_user_id = $1` parameter binding works; no codec needed [VERIFIED: existing 1a code] |

**Installation (delta from Phase 1a):**

```bash
# server/requirements.txt — additions
argon2-cffi>=23.1
python-jose[cryptography]>=3.4
cryptography>=42
structlog>=24
```

The `[cryptography]` extra on python-jose pulls in `cryptography` for the secure backend
(versus the default `pyca/cryptography`-less builds). Project already includes
`cryptography>=42` so this is just an explicit declaration.

**Version verification:** All four libraries verified by direct import in the existing
`server/` venv (already installed transitively in some cases):

```
argon2-cffi 25.1.0   [VERIFIED: python -c "import argon2; argon2.__version__"]
python-jose 3.5.0    [VERIFIED: same]
cryptography 48.0.0  [VERIFIED: same]
sqlalchemy 2.0.49    [VERIFIED: same]
asyncpg 0.31.0       [VERIFIED: same]
alembic 1.18.4       [VERIFIED: same]
```

The `>= 3.4` floor for python-jose is **load-bearing** — the locally-installed 3.5.0 is
fine, but if anyone reads CLAUDE.md's `>= 3.3` and pins literally to 3.3, they ship CVEs.

---

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─────────────────────────────────────────────┐
                    │ Inbound Request (REST | MCP HTTP | MCP stdio)│
                    └──────────────────┬──────────────────────────┘
                                       │
                          ┌────────────▼────────────┐
                          │  Trusted-proxy middleware│ (REST only)
                          │  populates               │  parses XFF if
                          │  request.state.client_ip │  socket peer ∈ allowlist
                          └────────────┬────────────┘
                                       │
                          ┌────────────▼────────────┐
                          │ Transport adapter       │
                          │ • REST: Depends         │
                          │ • MCP HTTP: TokenVerifier
                          │ • MCP stdio: startup-once│
                          └────────────┬────────────┘
                                       │ extracts token, calls
                                       ▼
                          ┌─────────────────────────┐
                          │  app/auth/core.py       │  PURE — no FastAPI imports
                          │  validate_jwt() /        │
                          │  validate_bearer() /     │  returns AuthResult dataclass
                          │  validate_refresh()      │
                          └────────────┬────────────┘
                                       │ AuthResult
                                       ▼
                          ┌─────────────────────────┐
                          │  Build OperationContext │  per transport adapter
                          │  (frozen dataclass)     │
                          └────────────┬────────────┘
                                       │ ctx
                                       ▼
                          ┌─────────────────────────┐
                          │  get_db_session(ctx)    │  D-20
                          │  SET app.current_user_id│
                          │  yield session          │
                          │  RESET in finally:      │
                          └────────────┬────────────┘
                                       │ session bound to user
                                       ▼
                          ┌─────────────────────────┐
                          │  Service layer          │  takes ctx + session
                          │  (transport-agnostic)   │  pure business logic
                          │  NO FastAPI types here  │
                          └────────────┬────────────┘
                                       │
                          ┌────────────▼────────────┐
                          │  PostgreSQL             │
                          │  RLS policies fire on   │
                          │  current_setting(       │
                          │   'app.current_user_id')│
                          └─────────────────────────┘

  System contexts (APScheduler prune_login_attempts, Alembic migrations) bypass via:
   ┌─────────────────────────────┐
   │  session_with_rls(SystemCtx)│  helper alias of get_db_session that takes
   │  OR BYPASSRLS-roled session │  explicit OperationContext (no request scope)
   └─────────────────────────────┘
```

### Recommended Project Structure (delta from Phase 1a)

```
server/app/
├── auth/                          # NEW — Phase 1b canonical auth package
│   ├── __init__.py
│   ├── context.py                 # OperationContext + AuthResult dataclasses
│   ├── core.py                    # validate_jwt/validate_refresh/validate_bearer (PURE)
│   ├── password.py                # argon2 hash/verify + check_needs_rehash
│   ├── tokens.py                  # JWT encode/decode (HS256)
│   ├── mcp_tokens.py              # 256-bit gen + SHA-256 hash + verify
│   ├── middleware.py              # FastAPI: trusted-proxy + Depends(get_operation_context)
│   ├── deps.py                    # require_user, require_admin, require_fresh_auth
│   └── audit.py                   # write_audit_log helper
├── encryption.py                  # NEW — MultiFernet wrapper for provider keys
├── models/
│   └── login_attempt.py           # NEW — `login_attempts` table
├── routes/
│   └── auth.py                    # NEW — /auth/login, /auth/refresh, /auth/logout, /api/v1/admin/reauth
├── services/                      # NEW — services package (transport-agnostic)
│   ├── __init__.py
│   ├── users.py                   # create_user, set_password, set_role
│   ├── sessions.py                # issue_session_pair, rotate_refresh, revoke_session
│   ├── mcp_tokens.py              # create/list/revoke/verify (with last_used_at update)
│   └── provider_keys.py           # set/get/list/revoke; Fernet wrap/unwrap
├── cli/                           # NEW (stub for 1b — full CLI is 1d)
│   ├── __init__.py
│   ├── main.py                    # smartcopilot entrypoint
│   ├── user.py                    # user create
│   ├── mcp_token.py               # mcp token create/list/revoke
│   └── provider_key.py            # provider key set
├── scheduler/
│   └── jobs/
│       └── prune_login_attempts.py # NEW — hourly APScheduler job (D-09)
├── dependencies.py                # EXTEND — get_db_session sets GUC + adds session_with_rls(ctx)
└── settings.py                    # EXTEND — new env vars listed below

alembic/versions/
└── 0002_phase_1b_auth.py          # NEW — login_attempts + sessions.admin_fresh_until + RLS policies
```

### Pattern 1: argon2 password hashing with asyncio offload

**What:** argon2 is CPU-bound (~50-200ms per hash at our params). Calling it from a
FastAPI async route blocks the event loop — login bursts will starve other requests.

**When to use:** Every `password_hash` and `password.verify` call.

```python
# Source: argon2-cffi docs + CLAUDE.md async pattern
# server/app/auth/password.py
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError, VerificationError
import asyncio

# D-23: PRD minima. parallelism=1 (NOT the default 4) — we run on shared homelab CPU.
_HASHER = PasswordHasher(
    time_cost=3,
    memory_cost=64 * 1024,    # 64 MiB
    parallelism=1,
    hash_len=32,
    salt_len=16,
)

async def hash_password(plaintext: str) -> str:
    """Hash a password; offload to a thread to keep the event loop hot."""
    return await asyncio.to_thread(_HASHER.hash, plaintext)

async def verify_password(stored_hash: str, plaintext: str) -> bool:
    """Verify; returns False on mismatch (do NOT propagate VerifyMismatchError to caller)."""
    try:
        await asyncio.to_thread(_HASHER.verify, stored_hash, plaintext)
        return True
    except (VerifyMismatchError, InvalidHashError, VerificationError):
        return False

def needs_rehash(stored_hash: str) -> bool:
    """Cheap, runs in-loop (no thread). Caller rehashes after successful login."""
    return _HASHER.check_needs_rehash(stored_hash)
```

[VERIFIED: argon2-cffi.readthedocs.io/en/stable/api.html — `verify` raises `VerifyMismatchError`,
not False; defaults are `time_cost=3, memory_cost=65536, parallelism=4` — we override
parallelism to 1.]

### Pattern 2: JWT issuance + verification (HS256 hardened)

```python
# Source: python-jose docs + CVE-2024-33663 mitigation
# server/app/auth/tokens.py
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
import uuid

ALGORITHM = "HS256"

def issue_access_jwt(*, user_id: uuid.UUID, role: str, signing_key: str, ttl_seconds: int) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(user_id),
        "role": role,
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
        "nbf": int(now.timestamp()),
    }
    return jwt.encode(claims, signing_key, algorithm=ALGORITHM)

def decode_access_jwt(token: str, signing_key: str) -> dict:
    """Decode with explicit algorithms allowlist — Landmine #2."""
    return jwt.decode(
        token,
        signing_key,
        algorithms=[ALGORITHM],     # MUST be a list; never None or [] — both bypass alg check
        options={"require": ["sub", "role", "jti", "exp"]},
    )
```

**Critical:** `algorithms=[ALGORITHM]` is non-negotiable. `algorithms=None` or `algorithms=[]`
opens the algorithm-confusion attack class (CVE-2024-33663) and the `alg=none` bypass
(CVE-2025-61152). Linting should grep for `jwt.decode` calls without explicit
`algorithms=`.

[VERIFIED: snyk.io + GitHub Advisory DB; python-jose 3.4.0 is the floor]

### Pattern 3: Refresh-token storage (opaque random + SHA-256)

**Recommended shape (Claude's discretion within D-03):**
- Refresh token = 256-bit `secrets.token_urlsafe(32)` — opaque, not a JWT
- Stored as `sessions.token_hash = sha256(refresh).hexdigest()` (REQ-401)
- `/auth/refresh` validates, DELETEs old row, INSERTs new row, returns new pair — single PG transaction (D-03)

**Why opaque, not JWT-as-refresh:**
- Revocability is a row delete (no JWT denylist required)
- Theft signal: replay of a deleted refresh hash = `invalid_token` → forced logout (D-03 explicit)
- Smaller wire footprint
- No claim drift across rotation

```python
# server/app/services/sessions.py — atomic rotate (D-03)
async def rotate_refresh(session: AsyncSession, raw_refresh: str) -> tuple[str, str]:
    rh = hashlib.sha256(raw_refresh.encode()).hexdigest()
    async with session.begin():
        row = await session.execute(
            select(SessionModel).where(SessionModel.token_hash == rh).with_for_update()
        )
        s = row.scalar_one_or_none()
        if s is None or s.expires_at < utcnow():
            raise InvalidToken()  # potential theft if a previously-valid refresh is replayed
        # delete old row
        await session.execute(delete(SessionModel).where(SessionModel.id == s.id))
        # mint new pair
        new_refresh = secrets.token_urlsafe(32)
        new_session = SessionModel(
            user_id=s.user_id,
            token_hash=hashlib.sha256(new_refresh.encode()).hexdigest(),
            expires_at=utcnow() + timedelta(seconds=settings.jwt_refresh_ttl_seconds),
        )
        session.add(new_session)
        # admin_fresh_until intentionally NOT carried over — re-auth required after rotate
        access = issue_access_jwt(user_id=s.user_id, role=user.role, ...)
    return access, new_refresh
```

### Pattern 4: MCP bearer token (256-bit, hashed, fast revocation)

```python
# server/app/services/mcp_tokens.py
import secrets, hashlib

PREFIX = "scmcp_"  # easy to grep in code search / leak detection
HASH_ALG = "sha256"

def generate_token() -> tuple[str, str, str]:
    """Returns (plaintext, sha256_hash, last4_hint). Plaintext shown once, never stored."""
    raw = secrets.token_urlsafe(32)               # 256 bits
    plaintext = PREFIX + raw
    token_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    last4 = plaintext[-4:]
    return plaintext, token_hash, last4

async def verify_token(session: AsyncSession, plaintext: str) -> McpToken | None:
    """Lookup by hash; check not revoked; update last_used_at. <5s revocation = next request."""
    th = hashlib.sha256(plaintext.encode()).hexdigest()
    row = (await session.execute(
        select(McpToken).where(
            McpToken.token_hash == th,
            McpToken.revoked_at.is_(None),
        )
    )).scalar_one_or_none()
    if row is None:
        return None
    # touch last_used_at (REQ-414); cheap UPDATE, every request is fine at homelab scale
    await session.execute(
        update(McpToken).where(McpToken.id == row.id).values(last_used_at=func.now())
    )
    return row
```

**Revocation-within-5-seconds (REQ-413, success criterion #2):**
- DB-only path means revoke = `UPDATE mcp_tokens SET revoked_at = now()` → next verify
  call sees `revoked_at IS NOT NULL` and rejects.
- No in-memory cache → no `--workers 2` consistency window. Effectively <100ms.
- The success criterion's "5 seconds" is an upper bound; we satisfy it trivially.
- **Anti-pattern to avoid:** caching token rows in worker memory (would create up-to-N-second
  staleness windows). The `last_used_at` write per request makes a cache pointless anyway.

### Pattern 5: Fernet-encrypted provider keys (MultiFernet from day 1)

```python
# server/app/encryption.py
from cryptography.fernet import Fernet, MultiFernet, InvalidToken

class FernetKeyMissing(RuntimeError): ...

def _build_multifernet() -> MultiFernet:
    """Load primary key from settings; refuse to start if missing."""
    if not settings.smartcopilot_fernet_key:
        raise FernetKeyMissing("SMARTCOPILOT_FERNET_KEY env var is required to start")
    primary = Fernet(settings.smartcopilot_fernet_key.encode())
    # D-24: MultiFernet from day 1; rotation is a one-line addition later.
    return MultiFernet([primary])

_fernet: MultiFernet | None = None

def fernet() -> MultiFernet:
    global _fernet
    if _fernet is None:
        _fernet = _build_multifernet()
    return _fernet

def encrypt_provider_key(plaintext: str) -> bytes:
    return fernet().encrypt(plaintext.encode())

def decrypt_provider_key(ciphertext: bytes) -> str:
    # NOTE: do NOT pass ttl=. Provider keys are at-rest with no expiry — Fernet TTL would
    # silently expire valid stored keys. Default ttl=None disables it. (Landmine #5)
    return fernet().decrypt(ciphertext).decode()
```

**Fail-on-startup wiring** (in `main.py:create_app` or `lifespan`):

```python
# server/app/main.py — at module load (or in lifespan)
from app.encryption import fernet, FernetKeyMissing
try:
    fernet()  # initialise — raises FernetKeyMissing if env var absent
except FernetKeyMissing as e:
    import sys
    print(f"FATAL: {e}", file=sys.stderr)
    sys.exit(1)
```

[VERIFIED: cryptography.fernet.Fernet.decrypt signature `(self, token, ttl=None) -> bytes`
— TTL only enforced if explicitly passed. ASSUMED: locally inspected via inspect.signature]

### Pattern 6: Pydantic v2 `Field(exclude=True)` for `encrypted_key`

```python
# server/app/services/provider_keys.py
from pydantic import BaseModel, Field

class ProviderKeyResponse(BaseModel):
    """REST response model. Field(exclude=True) ensures encrypted_key never leaves the server."""
    id: uuid.UUID
    user_id: uuid.UUID
    provider: str
    key_hint: str
    created_at: datetime
    # CLAUDE.md: enforce-by-schema, NOT post-hoc filtering.
    encrypted_key: bytes = Field(exclude=True)  # never serialised in any response
```

**Linter check** (recommend Ruff custom rule or grep gate in CI): no Pydantic model
that has `encrypted_key:` may omit `Field(exclude=True)`. The plan should add
a CI grep to enforce this.

### Pattern 7: PostgreSQL RLS — policy + `current_setting` + GUC SET/RESET

```sql
-- alembic 0002_phase_1b_auth.py — CREATE POLICY block (one per multi-tenant table)
-- Phase 1a already enabled+forced RLS on these 22 tables; only POLICY missing.

-- Example: provider_keys
CREATE POLICY provider_keys_owner ON provider_keys
    USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
    WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid);

-- Example: sessions, mcp_tokens, etc. — same shape with their user_id column.
```

**Why `NULLIF(..., '')::uuid` and `current_setting('...', true)`:**
- The `true` second arg to `current_setting` returns NULL/empty if GUC is unset (instead of raising).
- `NULLIF(..., '')` converts the empty string to NULL.
- The `::uuid` cast on NULL produces NULL.
- An RLS predicate that returns NULL is treated as FALSE → no rows → fail closed.
- This is the **deny-by-default-when-unauthenticated** behavior the architecture wants.

[VERIFIED: postgresql.org/docs/16/ddl-rowsecurity.html — `current_setting(setting_name, missing_ok)`]

```python
# server/app/dependencies.py — extend Phase 1a shape
from app.auth.context import OperationContext

async def get_db_session(
    ctx: OperationContext = Depends(get_operation_context),  # built by transport adapter
) -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        try:
            # D-20 / REQ-340: SET (not SET LOCAL).
            # Parameter binding via SQLAlchemy text() with bindparams — NEVER string-concat.
            await session.execute(
                text("SELECT set_config('app.current_user_id', :uid, false)"),
                {"uid": str(ctx.user_id)},
            )
            await session.execute(
                text("SELECT set_config('app.current_user_role', :role, false)"),
                {"role": ctx.role},
            )
            await session.execute(
                text("SELECT set_config('app.request_id', :rid, false)"),
                {"rid": ctx.request_id},
            )
            yield session
        finally:
            try:
                # REQ-340 mandate. Reset BEFORE the connection returns to the pool.
                await session.execute(text("RESET app.current_user_id"))
                await session.execute(text("RESET app.current_user_role"))
                await session.execute(text("RESET app.request_id"))
            except Exception:  # noqa: BLE001 — defensive cleanup only
                pass
            await session.close()
```

**Why `set_config(name, value, false)` instead of `SET app.x = '$1'`:**
- `SET` does not accept parameter placeholders — only literal strings or current_user etc.
- `set_config(name, value, is_local)` IS a normal function and accepts bind parameters,
  preventing SQL injection on the GUC value.
- `is_local=false` = session-scope (matches CLAUDE.md "not SET LOCAL").

```python
# Belt-and-braces: pool reset event handler (Landmine #1 fail-safe)
# server/app/database.py — register on engine.sync_engine
from sqlalchemy import event

@event.listens_for(engine.sync_engine, "reset")
def _on_pool_reset(dbapi_conn, connection_record, reset_state):
    """Defense-in-depth: even if get_db_session's RESET fails, scrub on pool checkin."""
    # Run synchronously via dbapi_conn (NOT async). Cheap.
    try:
        with dbapi_conn.cursor() as cur:
            cur.execute("RESET app.current_user_id")
            cur.execute("RESET app.current_user_role")
            cur.execute("RESET app.request_id")
    except Exception:  # noqa: BLE001
        pass  # never block pool reset
```

[VERIFIED: docs.sqlalchemy.org/en/20/core/pooling.html — `PoolEvents.reset` hook fires on connection check-in.]

### Pattern 8: Login throttling (DB-backed sliding window)

```python
# server/app/services/auth.py — sliding window query
async def check_rate_limit(
    session: AsyncSession, ip: str, username: str, *, window_s: int = 900, max_failures: int = 10
) -> int | None:
    """Returns None if allowed; otherwise retry_after_seconds."""
    row = (await session.execute(
        text("""
        SELECT count(*) AS cnt,
               extract(epoch from (now() - min(attempted_at)))::int AS oldest_age_s
        FROM login_attempts
        WHERE ip = :ip
          AND username = :u
          AND attempted_at >= now() - make_interval(secs => :window_s)
        """),
        {"ip": ip, "u": username, "window_s": window_s},
    )).first()
    if row.cnt < max_failures:
        return None
    retry_after = max(1, window_s - row.oldest_age_s)
    return retry_after
```

**Index strategy** (in 0002 migration):
```sql
CREATE INDEX login_attempts_lookup_idx
  ON login_attempts (ip, username, attempted_at DESC);
```

The `attempted_at DESC` ordering helps both (a) the sliding-window count via index-only
scan if the planner chooses, and (b) the prune job's range-deletion. At homelab scale
(<10 users, <100 attempts/day) the table stays in PG's shared_buffers and the index
is cosmetic; we still ship it because it's cheap and forward-proof.

**Race condition under `--workers 2`:** Two simultaneous requests both pass the count
check at 9 attempts, then both INSERT. Result: 11 rows in window — but ONLY ONE was
the over-limit attempt. This is acceptable: the 12th is rejected, the user is locked
out within 1 attempt of the threshold. The PRD requirement is `≥ 10 failures`, not
`exactly 10`. No need for advisory locks.

### Pattern 9: Step-up fresh-auth dependency

```python
# server/app/auth/deps.py
async def require_admin(ctx: OperationContext = Depends(get_operation_context)) -> OperationContext:
    if ctx.role != "admin":
        raise HTTPException(status_code=403, detail={"error": {"code": "forbidden", "message": "admin role required"}})
    return ctx

async def require_fresh_auth(
    ctx: OperationContext = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> OperationContext:
    """D-13: 4-check enforcement. Returns ctx on success; raises 403 admin_reauth_required otherwise."""
    if ctx.session_id is None:
        # MCP bearer / system contexts don't have a session — D-14: not_implemented for now
        raise HTTPException(status_code=403, detail=admin_reauth_required_envelope())
    s = await session.get(SessionModel, ctx.session_id)
    if s is None or s.expires_at < utcnow():
        raise HTTPException(status_code=403, detail=admin_reauth_required_envelope())
    if s.admin_fresh_until is None or s.admin_fresh_until < utcnow():
        raise HTTPException(status_code=403, detail=admin_reauth_required_envelope())
    return ctx

def admin_reauth_required_envelope() -> dict:
    return {"error": {
        "code": "admin_reauth_required",
        "message": "Fresh admin authentication is required.",
        "details": {"reauth_url": "/api/v1/admin/reauth", "freshness_window_minutes": 60},
    }}
```

### Pattern 10: Trusted-proxy XFF middleware

```python
# server/app/auth/middleware.py
from ipaddress import ip_address, ip_network
from fastapi import Request

class TrustedProxyMiddleware:
    """REQ-422–425. Sets request.state.client_ip from XFF if socket peer is trusted."""

    def __init__(self, app, *, trust_proxy: bool, allowlist_cidrs: list[str]):
        self.app = app
        self.trust = trust_proxy
        self.cidrs = [ip_network(c, strict=False) for c in allowlist_cidrs]

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send); return
        peer = scope["client"][0] if scope.get("client") else None
        client_ip = peer
        if self.trust and peer and any(ip_address(peer) in c for c in self.cidrs):
            xff = next((v for k, v in scope["headers"] if k == b"x-forwarded-for"), None)
            if xff:
                # D-29 / REQ-425: left-most IP
                client_ip = xff.decode().split(",")[0].strip()
        scope["state"] = scope.get("state", {})
        scope["state"]["client_ip"] = client_ip
        await self.app(scope, receive, send)
```

Mounted in `main.py:create_app()`:

```python
app.add_middleware(
    TrustedProxyMiddleware,
    trust_proxy=settings.smartcopilot_trust_proxy,
    allowlist_cidrs=settings.smartcopilot_trusted_proxy_cidrs,
)
```

### Anti-Patterns to Avoid

- **`SET LOCAL app.current_user_id`:** Only lasts until end of current transaction. Phase 1a
  already mandates regular `SET` (per REQ-340). Using `SET LOCAL` would mean a service that
  commits a transaction loses RLS on subsequent reads in the same request scope. [VERIFIED: postgresql.org/docs/16/sql-set.html]
- **Storing the JWT signing key in code:** Must come from `settings.jwt_signing_key` (env var),
  not a hardcoded constant.
- **`jwt.decode(token, key, algorithms=None)`:** Algorithm-confusion bypass (CVE-2024-33663
  + CVE-2025-61152). MUST be a non-empty list `[ALGORITHM]`.
- **`Fernet(...).decrypt(ciphertext, ttl=N)` for at-rest provider keys:** TTL silently
  expires valid stored keys. Default `ttl=None` is correct for at-rest.
- **String-concatenating user IDs into `SET app.current_user_id = '...'`:** Use
  `set_config(name, value, false)` with bind parameters. `SET` does not accept binds.
- **Looking up MCP tokens by plaintext:** Tokens are stored as SHA-256 hashes. Lookup MUST
  hash the candidate first.
- **Caching MCP token rows in worker memory:** Breaks the <5s revocation guarantee under
  `--workers 2` (no shared memory). DB-only path is correct and fast enough.
- **In-process per-worker rate-limit dict:** Same problem; D-05 explicitly rejects this.
- **`from fastapi import HTTPException` inside `services/`:** Forbidden by CLAUDE.md and
  D-17. Services raise domain errors, transports map to HTTP.
- **Returning the encrypted_key by accident:** D-28 mandates `Field(exclude=True)`. Add a
  CI grep to enforce.
- **Not RESET-ing GUCs in `finally:`:** Pool returns connection with stale GUC. Next
  request leaks. (Landmine #1).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Argon2 hashing | Custom KDF wrapper | `argon2.PasswordHasher` | OWASP-blessed; already handles salt/encoding/parameter migration |
| Symmetric envelope encryption | AES-CBC + HMAC by hand | `cryptography.fernet.Fernet` | Constant-time MAC; prevents canonicalisation bugs |
| Key rotation seam | Re-encrypt-on-read with current key only | `MultiFernet([primary, ...secondaries])` | Atomic rotation across keyset; single-line addition later |
| JWT encode/decode | Manual base64 + HMAC | `jose.jwt.encode` / `jwt.decode(..., algorithms=[ALGORITHM])` | Protects against alg-confusion if used correctly |
| 256-bit random tokens | `os.urandom(32).hex()` | `secrets.token_urlsafe(32)` | Constant-time, URL-safe, drop-in standard |
| Token-hash lookup index | Plaintext column with index | SHA-256 hex column with unique index | Loss of plaintext leaks → DB dump only contains hashes |
| Sliding-window counter | Fixed window with reset | `now() - interval '15 min'` count + `min(attempted_at)` | Prevents boundary-flip exploit; one query |
| Rate-limit cache eviction | Manual cron via OS | APScheduler hourly job in dedicated supervisord process | Consistent with D-09 + Phase 1a infra |
| RLS-bypass pattern for system jobs | Service-role superuser everywhere | `BYPASSRLS` role attribute on a dedicated DB user OR `session_with_rls(SystemCtx)` with a system UUID | Principle of least privilege; explicit role |
| Connection pool GUC scrubbing | None (rely solely on dependency RESET) | `PoolEvents.reset` listener fail-safe in `database.py` | Defense in depth — Landmine #1 |
| MCP bearer-token verifier | Hand-rolled HTTP middleware | MCP SDK 1.25+ `TokenVerifier` protocol + `AuthSettings` | Standard wire shape; FastMCP integrates natively |

**Key insight:** The five "do-not-hand-roll" items above (argon2 params, Fernet+MultiFernet,
JWT alg-confusion, sliding-window query, pool reset) are exactly where prior projects ship
silent breaks. Sticking to library-blessed defaults plus the documented hardening
(`algorithms=[...]`, `ttl=None` on at-rest decrypt, `current_setting(..., true)` graceful
unset) closes them all.

---

## Common Pitfalls

### Landmine #1: Pool-leaked GUCs (the headline TEST-02 failure)

**What goes wrong:** Request A sets `app.current_user_id = <user_a>`, then commits a
transaction. The connection is returned to the pool. Request B (different user) checks
the connection out without setting GUC. Postgres still sees `app.current_user_id = <user_a>`
on that connection. RLS policies authorize User B as User A.

**Why it happens:**
- `SET` (without LOCAL) is **session-scope**, not transaction-scope. It survives commit.
  [VERIFIED: postgresql.org/docs/16/sql-set.html]
- SQLAlchemy's default `reset_on_return` only calls `rollback()` — does NOT issue
  `RESET ALL` or `DISCARD ALL`. [VERIFIED: docs.sqlalchemy.org/en/20/core/pooling.html]
- Therefore the connection retains GUC state until something explicitly resets it.

**How to avoid (defense in depth):**
1. **Primary:** `RESET app.current_user_id` (and any other `app.*` we set) in the
   `get_db_session` `finally:` block — already canonical in CLAUDE.md and Phase 1a code.
2. **Fail-safe:** Register a `PoolEvents.reset` listener on `engine.sync_engine` that
   issues `RESET app.current_user_id` (and siblings) on connection check-in. If the
   primary path is bypassed (exception, future code change, helper not used), this
   catches it.
3. **Test:** TEST-02 / `test_rls_isolation.py` (D-30) actively probes for the leak with two
   users on the same connection.

**Warning signs:**
- Tests where User B sees User A's pages
- Audit log entries with mismatched `request_id` and `user_id`
- A `current_setting('app.current_user_id')` in pgbench shows a stale value after `RESET`
  is not called

### Landmine #2: python-jose CVE-2024-33663 + CVE-2025-61152

**What goes wrong:** JWT signature verification is bypassed.

- CVE-2024-33663: Algorithm confusion when handling OpenSSH ECDSA keys; affects all versions ≤ 3.3.0.
- CVE-2025-61152: `alg=none` accepted as a valid token; affects versions ≤ 3.3.0.

**Why it happens:** CLAUDE.md pins `python-jose >= 3.3` — literal interpretation ships
3.3.0, which is vulnerable. The lock file or pinning convention used by the planner
matters.

**How to avoid:**
- Pin **`python-jose[cryptography] >= 3.4`** (we install 3.5.0 locally — fine).
- ALWAYS pass `algorithms=["HS256"]` (a non-empty list) to `jwt.decode`. Never `None`,
  never `[]`.
- Add a Ruff/grep CI gate: `git grep -nE 'jwt\.decode\([^)]*\)' | grep -v 'algorithms=\['`
  must return empty.

**Warning signs:**
- A token whose header contains `"alg":"none"` decodes successfully
- A token signed with the JWT key as both private and public (RS256→HS256 confusion) decodes successfully

[VERIFIED: GitHub Advisory DB GHSA-6c5p-j8vq-pqhj; Snyk security.snyk.io/package/pip/python-jose]

### Landmine #3: argon2 `verify` raises, doesn't return False

**What goes wrong:** A naive caller writes `if hasher.verify(stored, plaintext): ...`. On
mismatch, `verify` raises `VerifyMismatchError` — the `if` branch never runs and the caller
gets a 500 instead of "invalid credentials".

**Why it happens:** `argon2.PasswordHasher.verify` returns `True` on success, raises on any
failure, and there are three failure subclasses (`VerifyMismatchError`, `VerificationError`,
`InvalidHashError`). [VERIFIED: argon2-cffi.readthedocs.io API ref]

**How to avoid:** Wrap in a helper (`verify_password`) that catches all three and returns
`False`. Keep the wrapper as the only call site; lint for any direct `PasswordHasher.verify`
call outside that module.

**Warning signs:**
- 500 errors on bad passwords (instead of 401 / `unauthorized`)
- Login throttling never triggers (the failure isn't reaching the rate-limit recorder)

### Landmine #4: Fernet's at-rest TTL footgun

**What goes wrong:** A developer sees `Fernet.decrypt(token, ttl=...)` and "for safety"
passes `ttl=86400` because that's their session length. Provider keys silently expire
24 hours after creation; LLM calls start failing with `InvalidToken`.

**Why it happens:** Fernet was originally designed for transient session tokens, not
at-rest secrets. Its TTL parameter measures **seconds since the ciphertext was created**,
not since last decryption. For `provider_keys` we want NO expiry — keys are valid until
explicitly rotated.

**How to avoid:**
- Helper `decrypt_provider_key(ciphertext)` MUST NOT pass a `ttl=` argument.
- Lint: grep for `\.decrypt\(.*ttl=` in `app/encryption.py` and `app/services/provider_keys.py` — must be empty.

[VERIFIED: cryptography.fernet.Fernet.decrypt signature `(self, token, ttl: int|None = None)`]

### Landmine #5: asyncpg + `SET ... = $1` is illegal SQL

**What goes wrong:** Developer writes `await session.execute(text("SET app.current_user_id = :uid"), {"uid": ...})`. Postgres parses this and rejects: `SET` is a utility statement that
does not accept parameter placeholders.

**Why it happens:** The natural FastAPI/SQLAlchemy idiom for parameterised SQL doesn't
apply to all PG statements.

**How to avoid:** Use `set_config(name, value, is_local)` instead, which IS a normal
function and accepts bind parameters:

```python
await session.execute(
    text("SELECT set_config('app.current_user_id', :uid, false)"),
    {"uid": str(user_id)},
)
```

This is also more SQL-injection resilient than constructing the SET statement via Python
string formatting.

[VERIFIED: postgresql.org/docs/16/functions-admin.html — set_config(name, value, is_local)]

### Landmine #6: argon2 blocks the FastAPI event loop

**What goes wrong:** A login burst (10 users in 100ms) takes 1-2 seconds total because
each `verify` blocks the loop for ~100ms. Other unrelated requests also stall.

**Why it happens:** argon2 is intentionally CPU-bound. A synchronous `verify` call inside
an async route holds the loop until done.

**How to avoid:** Wrap every `hash` and `verify` call in `await asyncio.to_thread(...)`.
This pushes the CPU work onto the default thread pool (per-worker; safe under `--workers 2`).

**Warning signs:** p95 latency on `/health` spikes during login burst tests; profiling
shows `argon2._ffi` on the hot path of the main thread.

### Landmine #7: testcontainers-pgvector image vs psycopg2/asyncpg URL prefix

**What goes wrong:** `PostgresContainer.get_connection_url()` returns
`postgresql+psycopg2://...` (or sometimes `postgresql://...`). The runtime engine needs
`postgresql+asyncpg://...`; Alembic needs `postgresql+psycopg2://...`. Mixing them
silently fails with cryptic `connection.run_async` errors.

**How to avoid:** Already handled in `app/tests/conftest.py` (Phase 1a). Test code that
mints its own engine MUST replicate the URL normalization. The `test_rls_isolation.py`
test should reuse the existing `test_engine` / `db_session` fixture rather than building
its own. [VERIFIED: existing conftest.py lines 56-59]

### Landmine #8: `current_setting('app.current_user_id')` raises if GUC unset

**What goes wrong:** A code path fails to set the GUC (system context, edge case),
the RLS policy fires, and Postgres raises `unrecognized configuration parameter`.
Whole request 500s instead of failing closed.

**How to avoid:** Always use `current_setting('app.current_user_id', true)` (the second
arg `missing_ok=true` makes it return NULL/empty on unset). Then `NULLIF(..., '')::uuid`
in the policy converts to NULL, which makes the predicate evaluate to NULL → FALSE
→ no rows. Fail-closed by default.

[VERIFIED: postgresql.org/docs/16/functions-admin.html#FUNCTIONS-ADMIN-SET]

### Landmine #9: `--workers 2` and rate-limit DB transactions

**What goes wrong:** Rate-limit `INSERT INTO login_attempts` uses the same SQLAlchemy
session as the login attempt itself. If the login fails because of a DB constraint
(e.g., user not found exception), the transaction rolls back, undoing the rate-limit
insert — failed attempt is not counted.

**How to avoid:** Insert the rate-limit row in its own transaction, BEFORE password
verification. Pattern:

```python
async with session.begin():
    session.add(LoginAttempt(ip=client_ip, username=username))
# transaction committed; row persists regardless of subsequent failures
ok = await verify_password(stored_hash, plaintext)
```

### Landmine #10: ENUM `user_role_enum` already exists from 0001

The Phase 1a migration already created `user_role_enum`. Phase 1b code that uses it
must use `create_type=False` on every `postgresql.ENUM(...)` reference (Phase 1a precedent).
Don't re-create it.

[VERIFIED: existing 0001_initial_schema.py:67 + provider_key.py uses ENUM(..., create_type=False)]

---

## Code Examples

### MCP SDK TokenVerifier integration

```python
# Source: github.com/modelcontextprotocol/python-sdk README + FastMCP auth docs
# server/app/mcp/server.py — Phase 1d will fully wire this; Phase 1b just provides the seam
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.fastmcp import FastMCP

from app.auth.core import validate_bearer

class SmartCopilotTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        result = await validate_bearer(token)  # AuthResult dataclass
        if result.error is not None:
            return None
        return AccessToken(
            token=token,
            client_id=str(result.user_id),
            scopes=["user"] if result.role == "user" else ["user", "admin"],
            # any other AccessToken fields the SDK requires
        )

# Phase 1b: only the seam (validate_bearer in auth/core.py).
# Phase 1d: instantiate FastMCP(..., token_verifier=SmartCopilotTokenVerifier(), ...)
```

[CITED: github.com/modelcontextprotocol/python-sdk]

### MCP stdio one-shot bootstrap

```python
# server/app/mcp/server.py — stdio path (Phase 1d full impl, 1b seam only)
def main_stdio() -> int:
    """Validate SMARTCOPILOT_MCP_TOKEN ONCE at startup. Reuse OperationContext per-request."""
    import os, asyncio
    token = os.environ.get("SMARTCOPILOT_MCP_TOKEN")
    if not token:
        sys.stderr.write("FATAL: SMARTCOPILOT_MCP_TOKEN required for stdio mode\n")
        return 1
    result = asyncio.run(validate_bearer(token))
    if result.error is not None:
        sys.stderr.write(f"FATAL: {result.error}\n")
        return 1
    # Build OperationContext(transport="mcp_stdio", remote=False, user_id=result.user_id, ...)
    # Stash in module-level state; every JSON-RPC request reuses it.
    ...
```

### Pydantic v2 settings extension

```python
# server/app/settings.py — additions for Phase 1b
class Settings(BaseSettings):
    # ... existing Phase 1a fields ...

    # JWT
    jwt_signing_key: str = Field(default="")  # NO default in production; container fails to start if empty
    jwt_access_ttl_seconds: int = Field(default=900)        # D-01
    jwt_refresh_ttl_seconds: int = Field(default=2592000)   # D-02

    # Argon2 (D-23)
    argon2_time_cost: int = Field(default=3)
    argon2_memory_cost: int = Field(default=64 * 1024)
    argon2_parallelism: int = Field(default=1)

    # Rate limit (D-05–D-09)
    login_rate_limit_window_seconds: int = Field(default=900)
    login_rate_limit_max_failures: int = Field(default=10)
    login_attempts_retention_hours: int = Field(default=24)

    # Step-up
    admin_fresh_window_minutes: int = Field(default=60)

    # Trusted proxy (D-29)
    smartcopilot_trust_proxy: bool = Field(default=False)
    smartcopilot_trusted_proxy_cidrs: list[str] = Field(default_factory=list)
```

### `OperationContext` dataclass

```python
# server/app/auth/context.py
from dataclasses import dataclass
from typing import Literal
import uuid

@dataclass(frozen=True, slots=True)
class AuthResult:
    """Pure transport-neutral result of token validation. NO FastAPI imports here."""
    user_id: uuid.UUID | None = None
    role: str | None = None
    session_id: uuid.UUID | None = None
    mcp_token_id: uuid.UUID | None = None
    error: str | None = None  # "invalid_token" | "missing_auth" | "service_unavailable"

@dataclass(frozen=True, slots=True)
class OperationContext:
    """REQ-520. Built by transport adapter from AuthResult."""
    user_id: uuid.UUID
    role: Literal["admin", "user"]
    transport: Literal["rest", "mcp_http", "mcp_stdio", "cli", "system"]
    remote: bool                      # D-22 transport-driven
    client_name: str
    request_id: str
    session_id: uuid.UUID | None = None
    mcp_token_id: uuid.UUID | None = None
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| bcrypt for password hashing | argon2id (PRD/OWASP-mandated) | OWASP 2023 update | bcrypt is acceptable but argon2id is the recommendation; PRD locks argon2id |
| JWT-as-refresh-token | Opaque random + SHA-256 hash + DB row | OWASP guidance + REQ-401 | Easy revocation by row delete; theft-detection by replay |
| In-process rate limit | DB-backed sliding window | Multi-worker correctness | `--workers 2` cannot share memory; PG is the single source of truth |
| `SET LOCAL` for RLS | `SET` (session-scope) + `RESET` in finally + pool-event fail-safe | REQ-340 + Landmine #1 | `SET LOCAL` reverts on commit, breaking multi-statement requests |
| python-jose < 3.3 | python-jose >= 3.4 | CVE-2024-33663 + CVE-2025-61152 | Algorithm confusion + alg=none bypass — non-negotiable |
| Custom Fernet wrapper | `MultiFernet([primary])` from day 1 | D-24 | Rotation seam without code change later |

**Deprecated/outdated:**
- pyjwt as an alternative: not listed in CLAUDE.md; would parallel python-jose. Skip.
- bcrypt as a fallback: not listed; argon2id is the only password hash.

---

## Project Constraints (from CLAUDE.md)

The following directives from `./CLAUDE.md` must be honored by the planner. Research did
not propose anything that contradicts these:

1. `encrypted_key` fields MUST use `Field(exclude=True)` on every Pydantic response model
   — never filtered after the fact. (Pattern 6, D-28)
2. Do NOT import FastAPI types (`Request`, `Response`, `HTTPException`) in `services/`.
   Services take `OperationContext`, not request objects. (D-17, D-18)
3. RLS discipline: `SET app.current_user_id` (not `SET LOCAL`); always `RESET` in `finally:`.
   (Pattern 7, Landmine #1)
4. `--workers 2` uvicorn — rate-limit storage and login_attempts MUST live in postgres,
   not memory. (Pattern 8)
5. Fernet key is master secret; container MUST refuse to start if `SMARTCOPILOT_FERNET_KEY`
   absent; column type is BYTEA. (Pattern 5)
6. `MultiFernet` from day 1 (D-24); rotation deferred but seam present.
7. argon2id parameters per PRD minima (D-23): `time_cost=3, memory_cost=64*1024, parallelism=1`.
8. python-jose for JWT (HS256). [Research adds: ≥ 3.4, never `algorithms=None`]
9. No new supervisord process for auth (subsystem runs inside fastapi worker; APScheduler
   prune job runs inside the existing apscheduler process).
10. APScheduler must NOT run inside uvicorn workers (D-09's prune job lives in the dedicated
    `app.scheduler.run` process).
11. structlog field redaction filter for `password`, `token`, etc. (D-27).
12. `BYPASSRLS` role attribute or system OperationContext for APScheduler/Alembic auth-bypass.
13. Tests against real PostgreSQL via testcontainers; no mocks for DB (TEST-01 inheritance).
14. One file per domain in `models/`; new model `models/login_attempt.py` (D-05 from CONTEXT).
15. Alembic migrations named by purpose (`0002_phase_1b_auth.py`).

---

## Runtime State Inventory

> Phase 1b is not a rename/refactor phase, so this section is informational only —
> documents which existing runtime state Phase 1b extends.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `users` (already created in 0001), `sessions` (extend with `admin_fresh_until`), `mcp_tokens` (already created), `provider_keys` (already created BYTEA) | Code edits + Alembic migration `0002` for column add |
| Live service config | None — Phase 1a has no external services beyond PG | None |
| OS-registered state | None — supervisord process list unchanged | None |
| Secrets/env vars | New: `SMARTCOPILOT_FERNET_KEY` (mandatory at startup), `JWT_SIGNING_KEY` (new), `SMARTCOPILOT_TRUST_PROXY` (new), `SMARTCOPILOT_TRUSTED_PROXY_CIDRS` (new). Existing: `database_url`, `alembic_database_url` carry over from 1a | Add to `.env.example`; document in deployment runbook |
| Build artifacts | None — no compiled artifacts; all Python | None |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | All Phase 1b code | ✓ | 3.12.13 | — |
| Docker | Integration tests via testcontainers | ✓ | 29.4.0 | — |
| Alembic CLI | Migration generation/run | ✓ | 1.18.4 | — |
| `pgvector/pgvector:pg16` image | testcontainers test fixture | ✓ (Phase 1a inherited) | pg16 | — |
| argon2-cffi | Password hashing | ✓ | 25.1.0 | — |
| python-jose | JWT | ✓ | 3.5.0 | — |
| cryptography | Fernet | ✓ | 48.0.0 | — |
| asyncpg | Async DB driver | ✓ | 0.31.0 | — |
| SQLAlchemy 2.0 | Async ORM | ✓ | 2.0.49 | — |
| structlog | Logging + redaction | ✗ (not in requirements yet) | — | Add to requirements.txt; no functional fallback acceptable for D-27 |
| mcp SDK | TokenVerifier seam (full impl Phase 1d) | [ASSUMED — not verified locally; Phase 1b only adds the import seam in `auth/core.validate_bearer`] | — | If absent, Phase 1d adds it. Phase 1b can ship without this dependency |

**Missing dependencies with no fallback:** None blocking Phase 1b execution.

**Missing dependencies with fallback:** `structlog` — must be added to requirements.txt as
part of the first plan. Without it, D-27 redaction policy cannot be enforced.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.x + pytest-asyncio 1.x + testcontainers-python 4.x (Phase 1a inheritance) |
| Config file | `server/pyproject.toml` |
| Quick run command | `cd server && ruff check app/ && pytest app/tests/ -x -q` |
| Full suite command | `cd server && ruff check app/ && pytest app/tests/ -v` |
| Estimated runtime | ~90 seconds (testcontainer ~20s + migrations ~5s + ~20 new tests) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-01 | argon2 hash/verify happy path | unit | `pytest app/tests/unit/test_password.py::test_hash_verify_roundtrip -x` | ❌ Wave 0 |
| AUTH-01 | argon2 params at PRD minima | unit | `pytest app/tests/unit/test_password.py::test_argon2_params_meet_owasp_minima -x` | ❌ Wave 0 |
| AUTH-01 | `verify` returns False on bad pwd (not raises) | unit | `pytest app/tests/unit/test_password.py::test_verify_returns_false_on_mismatch -x` | ❌ Wave 0 |
| AUTH-01 | `check_needs_rehash` flags old params | unit | `pytest app/tests/unit/test_password.py::test_check_needs_rehash_after_param_change -x` | ❌ Wave 0 |
| AUTH-02 | `/auth/login` happy path returns access+refresh | integration | `pytest app/tests/integration/test_auth.py::test_login_returns_jwt_pair -x` | ❌ Wave 0 |
| AUTH-02 | refresh stored as SHA-256 hash, not plaintext | integration | `pytest app/tests/integration/test_auth.py::test_refresh_token_stored_as_hash -x` | ❌ Wave 0 |
| AUTH-02 | refresh rotate-and-revoke (D-03) | integration | `pytest app/tests/integration/test_auth.py::test_refresh_rotation_revokes_old -x` | ❌ Wave 0 |
| AUTH-02 | replayed old refresh = invalid_token | integration | `pytest app/tests/integration/test_auth.py::test_old_refresh_replay_rejected -x` | ❌ Wave 0 |
| AUTH-02 | JWT decode rejects `alg=none` | unit | `pytest app/tests/unit/test_jwt.py::test_decode_rejects_alg_none -x` | ❌ Wave 0 |
| AUTH-02 | JWT decode rejects wrong algorithm | unit | `pytest app/tests/unit/test_jwt.py::test_decode_rejects_alg_confusion -x` | ❌ Wave 0 |
| AUTH-03 | 10 failures in 15 min triggers `rate_limited` | integration | `pytest app/tests/integration/test_auth.py::test_rate_limit_after_10_failures -x` | ❌ Wave 0 |
| AUTH-03 | response includes `retry_after_seconds` | integration | `pytest app/tests/integration/test_auth.py::test_rate_limit_response_envelope -x` | ❌ Wave 0 |
| AUTH-03 | successful login wipes attempts (D-08) | integration | `pytest app/tests/integration/test_auth.py::test_successful_login_wipes_attempts -x` | ❌ Wave 0 |
| AUTH-03 | sliding window — old attempts age out | integration | `pytest app/tests/integration/test_auth.py::test_sliding_window_ages_out -x` | ❌ Wave 0 |
| AUTH-03 | `prune_login_attempts` retention job | integration | `pytest app/tests/integration/test_scheduler.py::test_prune_login_attempts -x` | ❌ Wave 0 |
| AUTH-04 | MCP token plaintext shown once, never stored | integration | `pytest app/tests/integration/test_mcp_tokens.py::test_token_plaintext_shown_once -x` | ❌ Wave 0 |
| AUTH-04 | MCP token stored as SHA-256 hash | integration | `pytest app/tests/integration/test_mcp_tokens.py::test_token_stored_as_hash -x` | ❌ Wave 0 |
| AUTH-04 | MCP token revoke takes effect <5s | integration | `pytest app/tests/integration/test_mcp_tokens.py::test_revocation_within_5_seconds -x` | ❌ Wave 0 |
| AUTH-04 | 256-bit entropy on generation | unit | `pytest app/tests/unit/test_mcp_tokens.py::test_token_is_256_bits -x` | ❌ Wave 0 |
| AUTH-05 | `last_used_at` updates on each verify | integration | `pytest app/tests/integration/test_mcp_tokens.py::test_last_used_at_updates_on_verify -x` | ❌ Wave 0 |
| AUTH-06 | role enum: only admin/user accepted | unit | `pytest app/tests/unit/test_users.py::test_role_enum_is_admin_or_user -x` | ❌ Wave 0 |
| AUTH-06 | admin op writes to audit_log | integration | `pytest app/tests/integration/test_audit_log.py::test_admin_op_audited -x` | ❌ Wave 0 |
| AUTH-06 | non-admin rejected from /admin route | integration | `pytest app/tests/integration/test_admin.py::test_non_admin_forbidden -x` | ❌ Wave 0 |
| AUTH-07 | `/admin/reauth` happy path sets fresh window | integration | `pytest app/tests/integration/test_admin.py::test_reauth_sets_fresh_until -x` | ❌ Wave 0 |
| AUTH-07 | destructive route 403 without fresh-auth | integration | `pytest app/tests/integration/test_admin.py::test_destructive_requires_fresh_auth -x` | ❌ Wave 0 |
| AUTH-07 | response envelope = `admin_reauth_required` | integration | `pytest app/tests/integration/test_admin.py::test_reauth_envelope_shape -x` | ❌ Wave 0 |
| AUTH-07 | fresh window expires after 60 min (mocked clock) | unit | `pytest app/tests/unit/test_auth_deps.py::test_fresh_auth_expiry -x` | ❌ Wave 0 |
| AUTH-08 | XFF respected only when trust_proxy + allowlist match | integration | `pytest app/tests/integration/test_trusted_proxy.py::test_xff_used_when_peer_trusted -x` | ❌ Wave 0 |
| AUTH-08 | XFF ignored when trust_proxy=false | integration | `pytest app/tests/integration/test_trusted_proxy.py::test_xff_ignored_when_untrusted -x` | ❌ Wave 0 |
| AUTH-08 | left-most XFF used (D-29 / REQ-425) | unit | `pytest app/tests/unit/test_trusted_proxy.py::test_leftmost_xff_chosen -x` | ❌ Wave 0 |
| AUTH-09 | provider_key Fernet round-trip | unit | `pytest app/tests/unit/test_encryption.py::test_fernet_roundtrip -x` | ❌ Wave 0 |
| AUTH-09 | encrypted_key never appears in any response model | integration | `pytest app/tests/integration/test_provider_keys.py::test_encrypted_key_excluded_from_responses -x` | ❌ Wave 0 |
| AUTH-09 | container fails to start without SMARTCOPILOT_FERNET_KEY | unit | `pytest app/tests/unit/test_encryption.py::test_missing_fernet_key_raises -x` | ❌ Wave 0 |
| AUTH-09 | MultiFernet seam — secondary key still decrypts | unit | `pytest app/tests/unit/test_encryption.py::test_multifernet_decrypts_legacy -x` | ❌ Wave 0 |
| AUTH-10 | per-user key resolves before shared (PRD §24.2) | integration | `pytest app/tests/integration/test_provider_keys.py::test_user_key_takes_precedence -x` | ❌ Wave 0 |
| AUTH-10 | shared key fallback when no user key | integration | `pytest app/tests/integration/test_provider_keys.py::test_shared_key_fallback -x` | ❌ Wave 0 |
| AUTH-10 | both missing → `missing_provider_key` error | integration | `pytest app/tests/integration/test_provider_keys.py::test_missing_provider_key_error -x` | ❌ Wave 0 |
| **TEST-02** | **GUC RESET happens after request scope (no leak across pool)** | **integration** | `pytest app/tests/test_rls_isolation.py::test_no_guc_leak_after_request -x` | ❌ Wave 0 |
| TEST-02 | user A request leaves `app.current_user_id` empty for user B's checkout | integration | `pytest app/tests/test_rls_isolation.py::test_user_b_sees_empty_guc -x` | ❌ Wave 0 |
| TEST-02 | RLS policy fires — User B cannot read User A's pages | integration | `pytest app/tests/test_rls_isolation.py::test_cross_user_read_blocked -x` | ❌ Wave 0 |
| TEST-02 | system context bypass works (BYPASSRLS or system uuid) | integration | `pytest app/tests/test_rls_isolation.py::test_system_context_bypass -x` | ❌ Wave 0 |
| TEST-02 | pool reset event fires `RESET app.current_user_id` (Landmine #1 fail-safe) | integration | `pytest app/tests/test_rls_isolation.py::test_pool_reset_scrubs_guc -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `cd server && ruff check app/ && pytest app/tests/ -x -q --timeout=60`
- **Per wave merge:** `cd server && ruff check app/ && pytest app/tests/ -v`
- **Phase gate:** Full suite green + manual smoke of `smartcopilot user create` + `POST /auth/login` against a live container

### Wave 0 Gaps

> Wave 0 = files that must exist before integration tests can run.

- [ ] `server/app/tests/unit/__init__.py` — new unit test package
- [ ] `server/app/tests/unit/test_password.py` — argon2 unit tests
- [ ] `server/app/tests/unit/test_jwt.py` — JWT roundtrip + CVE regression
- [ ] `server/app/tests/unit/test_encryption.py` — Fernet roundtrip + missing-key fail
- [ ] `server/app/tests/unit/test_mcp_tokens.py` — entropy + hash format
- [ ] `server/app/tests/unit/test_users.py` — role enum
- [ ] `server/app/tests/unit/test_auth_deps.py` — require_admin / require_fresh_auth
- [ ] `server/app/tests/unit/test_trusted_proxy.py` — left-most XFF + allowlist
- [ ] `server/app/tests/integration/test_auth.py` — /auth/login + /auth/refresh
- [ ] `server/app/tests/integration/test_mcp_tokens.py` — generate/verify/revoke flow
- [ ] `server/app/tests/integration/test_admin.py` — /admin/reauth + require_fresh_auth
- [ ] `server/app/tests/integration/test_provider_keys.py` — encrypted_key never in response + resolution order
- [ ] `server/app/tests/integration/test_audit_log.py` — admin op writes to audit_log
- [ ] `server/app/tests/integration/test_trusted_proxy.py` — proxy header end-to-end
- [ ] `server/app/tests/integration/test_scheduler.py` — prune_login_attempts job
- [ ] `server/app/tests/test_rls_isolation.py` — D-30 / TEST-02 (the headline test)
- [ ] Shared fixture: `seeded_users` (creates user A + user B with known passwords + tokens) — add to `app/tests/conftest.py` or a new `app/tests/auth_fixtures.py`
- [ ] Shared fixture: `authenticated_client` (httpx AsyncClient with valid JWT for a given role)
- [ ] Shared fixture: `system_context` (OperationContext for system/APScheduler tests)
- [ ] `requirements.txt`: add `argon2-cffi>=23.1`, `python-jose[cryptography]>=3.4`, `structlog>=24`
- [ ] `requirements-dev.txt`: add `freezegun` if mocking time for fresh-auth expiry tests
- [ ] `.env.example`: document new env vars (`SMARTCOPILOT_FERNET_KEY`, `JWT_SIGNING_KEY`, `SMARTCOPILOT_TRUST_PROXY`, `SMARTCOPILOT_TRUSTED_PROXY_CIDRS`)

---

## Security Domain

> `security_enforcement` is implicit (config has no explicit `false`).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | yes | argon2id (V2.4.1), JWT short-lived (V2.5), refresh-token rotation (V2.5.5), step-up re-auth (V2.5.7) |
| V3 Session Management | yes | Server-side session via `sessions` table (V3.2), session expiration (V3.3.1), `last_used_at`/idle policy candidate (V3.3) |
| V4 Access Control | yes | RBAC two-role (admin/user) (V4.1.3), RLS per-user (V4.2.1), step-up for destructive ops (V4.3.1), trust boundary on `remote=true` MCP (V4.2.2) |
| V5 Input Validation | yes | username normalization (D-10), CIDR parse via `ipaddress` stdlib, JWT claim validation (`require=[sub,role,jti,exp]`) |
| V6 Cryptography | yes | argon2id for password (V6.2.5), Fernet AES-128 + HMAC for at-rest (V6.2.1), HS256 JWT with explicit algorithms allowlist (V6.2.2 + Landmine #2) |
| V7 Error Handling | yes | Stable error codes (`unauthorized`, `forbidden`, `rate_limited`, `admin_reauth_required`, `missing_provider_key`); no stack traces leaked |
| V8 Data Protection | yes | `Field(exclude=True)` on `encrypted_key`, structlog field redaction (D-27) |
| V9 Communication | (deferred) | TLS termination is reverse-proxy concern (out of Phase 1b scope) |
| V10 Malicious Code | (n/a) | No file upload / no code execution surface in Phase 1b |
| V11 Business Logic | yes | Refresh rotate-and-revoke replay detection (D-03 — theft signal) |

### Known Threat Patterns for the auth/security stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| RLS bypass via leaked GUC across pool | I (Information Disclosure) | RESET in finally + pool-event fail-safe (Landmine #1) |
| JWT algorithm confusion (RS256→HS256) | S (Spoofing) | `algorithms=["HS256"]` on every decode; python-jose >= 3.4 (Landmine #2) |
| `alg=none` JWT | S | Same as above; CVE-2025-61152 fixed in 3.4+ |
| Login brute-force | S | DB-backed sliding window 10/15min (D-05–D-08) |
| Credential stuffing | S | Same rate limit; PRD does not require CAPTCHA at homelab scale |
| MCP token leak / non-revocable | E (Elevation) | SHA-256 hash storage + `revoked_at` column + DB-only verify path (<5s) |
| Provider-key exfiltration via API response | I | `Field(exclude=True)` schema-level enforcement (D-28) |
| Admin privilege misuse | E | Step-up fresh-auth (60-min window) on destructive ops (D-12, D-15) |
| XFF spoofing for IP-based trust | S | Trusted-proxy CIDR allowlist; reject if direct peer not in list (D-29) |
| SQL injection via `SET app.current_user_id = $1` | T (Tampering) | Use `set_config(name, value, false)` with bind parameters (Landmine #5) |
| Refresh-token theft + replay | E | Rotate-and-revoke deletes old hash on use; replay yields `invalid_token` (D-03) |
| Connection pool GUC leakage | I, T | RESET in finally + `PoolEvents.reset` listener |
| Fernet ciphertext silently expiring | A (Availability) | Never pass `ttl=` to decrypt for at-rest (Landmine #4) |
| argon2 event-loop block under burst | A | `await asyncio.to_thread(...)` wrapper (Pattern 1, Landmine #6) |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | structlog 24.x exists and is API-compatible with the redaction-filter pattern we'll use | Standard Stack | Plan would need to swap to a different logger; D-27 redaction still required |
| A2 | MCP SDK 1.25+ `TokenVerifier` protocol shape is stable through 1.27 (the version on PyPI today) | Code Examples — MCP TokenVerifier | If shape changes between 1.25→1.27, the `validate_bearer` adapter signature shifts. Phase 1b only adds the import seam; Phase 1d does the full integration |
| A3 | `freezegun` is acceptable for mocking time in fresh-auth expiry tests | Wave 0 | Plan can use `monkeypatch` of `datetime.now` instead — equivalent |
| A4 | `BYPASSRLS` role attribute on a dedicated PG user is acceptable for system contexts (Alembic, APScheduler prune job), OR alternative: `SET app.current_user_id` to a system UUID and write RLS policies to allow it. The choice is open — both work. | Pattern 7, Don't Hand-Roll | If neither approach is accepted (e.g., security team mandates a different bypass), planner picks one; both are documented |
| A5 | `--workers 2` setting in the production supervisord/uvicorn config is a hard limit; rate-limit race condition under D-05 is acceptable (lockout fires within 1 attempt of threshold) | Pattern 8 | If user requires exact 10-attempt lockout, planner adds `pg_advisory_lock` per `(ip, username)` — small additional task |
| A6 | `mcp` package is not yet installed in the venv (Phase 1b only adds the import seam in `auth/core.validate_bearer`; the actual MCP SDK client lands in Phase 1d) | Environment Availability | If a Phase 1b plan happens to pull in MCP SDK, that's fine; if not, the seam is a function reference only |
| A7 | The 22 RLS-FORCED tables from 0001 should all receive owner-only policies in 0002 (Phase 1b adds POLICY for tables that have a `user_id` column — `provider_keys`, `sessions`, `mcp_tokens`, `pages`, `page_versions`, `chunks`, `entities` (via vault_id→user), `links` (transitive), `timeline_events` (transitive), `tags` (transitive), `page_tags` (transitive), `eval_candidates`, `conversations`, `messages` (transitive via conversation_id), `memories`, `projects`, `llm_usage`, `index_events`, `user_settings`, `recipes`, `skills`, `dream_audit_log`). Some are transitive — policy boilerplate should reflect that. The exact set may need refining at plan time. | Pattern 7 | If a table is missed, that table fails-closed (no rows returned) which is safer than fails-open; planner spots and adds. Phase 1c additionally adds vault scoping that may reshape some |
| A8 | Trust boundary on `remote=true` callers (REQ-511 / VAULT-10 slug validation, etc.) is fully wired in Phase 1c/1d, not 1b. Phase 1b only seeds the `OperationContext.remote` field correctly. | OperationContext shape | Planner verifies that Phase 1b does not need to enforce remote=true restrictions yet — only seed the flag |

**Empty assumption table = research is fully verified.** This section is non-empty; the
planner and discuss-phase should validate A1, A4, and A7 with the user before locking
into specific plan tasks.

---

## Open Questions (RESOLVED)

1. **Should the JWT signing key be auto-generated at first boot or required?**
   - What we know: PRD doesn't specify. Auto-generation simplifies first-run; required env var matches Fernet pattern.
   - What's unclear: which fits the homelab UX better.
   - RESOLVED: **mirror Fernet — required env var (`JWT_SIGNING_KEY`); container fails to start if absent.** Add a `smartcopilot init-keys` CLI command (or doc snippet) that prints `secrets.token_urlsafe(64)` for both keys. Consistency with Fernet is more valuable than the marginal first-run convenience.

2. **Where does the system OperationContext UUID come from?**
   - What we know: D-22 says system contexts have `remote=False`; CONTEXT.md mentions a "system UUID."
   - What's unclear: is this a single hardcoded UUID, or a per-system-process UUID, or a row in `users` with role='admin' + flag `is_system=true`?
   - RESOLVED: **add a single seeded `users` row with `username='system'`, `role='admin'`, `is_active=true`** in 0002 migration. `OperationContext.user_id` for APScheduler/Alembic = that row's UUID. RLS policies then naturally apply (system user owns no per-user data, so it's effectively bypass for the empty intersection). For tables that the system genuinely needs to write across users (e.g., audit_log), use a `BYPASSRLS`-attributed PG role for those connections.

3. **`audit_log` for `/admin/reauth` failures — does that itself open a side channel for username enumeration?**
   - What we know: D-25 records failures with `reason='invalid_password'`.
   - What's unclear: is the failure log queryable by non-admin users? (Should be no — `audit_log` queries are Phase 6 admin-only.)
   - RESOLVED: **fine for Phase 1b** — audit_log API is Phase 6. If sensitivity emerges, hash the reason or exclude failed-reauth from the user-facing trail at that point.

4. **Refresh-token replay detection storage — how aggressive?**
   - What we know: D-03 says replay = forced logout (theft signal). We DELETE the old row.
   - What's unclear: should we keep a "previously-used token hash" table for ~24h to distinguish replay from accidental re-submit?
   - RESOLVED: **don't.** A genuine accidental re-submit (network retry) would also indicate that the new pair the client got didn't reach storage — the user logging in fresh is correct UX. The PRD's intent is clear: replay = invalid_token. Don't engineer past it.

5. **Should `last_used_at` be updated on EVERY MCP request, or debounced (e.g., once per minute)?**
   - What we know: REQ-414 says "every successful auth." A small UPDATE per request is cheap at homelab scale.
   - What's unclear: would skip-when-recent be a future optimization?
   - RESOLVED: **update every request for now.** PG row UPDATE on a hot row is sub-millisecond and the homelab traffic shape is low. Optimize only if Phase 6 metrics show contention.

---

## Sources

### Primary (HIGH confidence)

- [argon2-cffi PasswordHasher API](https://argon2-cffi.readthedocs.io/en/stable/api.html) — `verify` raises VerifyMismatchError, `check_needs_rehash` returns bool
- [argon2-cffi Choosing Parameters](https://argon2-cffi.readthedocs.io/en/stable/parameters.html) — RFC 9106 profiles, OWASP guidance
- [PostgreSQL 16 SET](https://www.postgresql.org/docs/16/sql-set.html) — SET vs SET LOCAL semantics
- [PostgreSQL 16 RLS](https://www.postgresql.org/docs/16/ddl-rowsecurity.html) — `current_setting`, BYPASSRLS, policy syntax
- [PostgreSQL 16 set_config](https://www.postgresql.org/docs/16/functions-admin.html#FUNCTIONS-ADMIN-SET) — function form that accepts bind parameters
- [SQLAlchemy 2.0 Connection Pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html) — `reset_on_return` + `PoolEvents.reset`
- [SQLAlchemy GUC + commit + pool discussion](https://github.com/sqlalchemy/sqlalchemy/discussions/13020) — confirms session.commit + pool checkout drops session-scoped SET unless event-restored
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) — TokenVerifier + AuthSettings + FastMCP
- [FastMCP auth docs](https://gofastmcp.com/python-sdk/fastmcp-server-auth-auth) — middleware pattern for HTTP/Streamable
- [cryptography Fernet](https://cryptography.io/en/latest/fernet/) — TTL behavior; MultiFernet rotation
- Local pip inspection (verified versions): argon2-cffi 25.1.0, python-jose 3.5.0, cryptography 48.0.0, sqlalchemy 2.0.49, asyncpg 0.31.0, alembic 1.18.4
- [PRD v26.05.1](file:///docs/product_requirements_document_v26.05.md) §8 (Auth), §7.3-7.4 (RLS), §10.3 (Errors), §24.2 (Provider keys)
- `.planning/phases/01b-auth-security-primitives/01b-CONTEXT.md` — locked decisions D-01 through D-30

### Secondary (MEDIUM confidence)

- [Snyk python-jose advisory page](https://security.snyk.io/package/pip/python-jose) — CVE-2024-33663, CVE-2025-61152
- [GitHub Advisory GHSA-6c5p-j8vq-pqhj](https://github.com/advisories/GHSA-6c5p-j8vq-pqhj) — CVE-2024-33663 detail
- [Algorithm Confusion in python-jose CVE-2024-33663](https://www.vicarius.io/vsociety/posts/algorithm-confusion-in-python-jose-cve-2024-33663) — exploit walkthrough
- [Python-jose alg=none CVE-2025-61152 (vulert)](https://vulert.com/vuln-db/debian-12-python-jose-362548) — alg=none bypass
- [Safir X-Forwarded-For handling](https://safir.lsst.io/user-guide/x-forwarded.html) — left-most vs right-most parsing patterns under trusted-proxy CIDRs

### Tertiary (LOW confidence — flagged for validation)

- [MCP Python SDK issue #1414](https://github.com/modelcontextprotocol/python-sdk/issues/1414) — accessing bearer token inside MCP tool (resolution unclear; flagged for Phase 1d)
- [SlowAPI README](https://github.com/laurentS/slowapi) — confirms no PostgreSQL backend (justification for hand-rolled DB-backed limit)
- structlog 24.x version assumption (A1) — not verified in this venv

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every library verified by direct local import and version check
- Architecture: HIGH — patterns derive from CLAUDE.md + locked CONTEXT.md decisions; no novel choices
- Pitfalls: HIGH — five landmines independently confirmed via official docs + recent CVE advisories + local API inspection
- python-jose CVE flag: HIGH — multiple authoritative sources (Snyk, GitHub Advisory DB, vendor advisories) agree on >= 3.4 floor
- MCP SDK seam (Phase 1b only adds the seam, full impl Phase 1d): MEDIUM — SDK shape verified at 1.25 README level; 1.27 may differ in details
- Validation map: HIGH — all 11 requirements mapped to runnable pytest commands

**Research date:** 2026-05-08
**Valid until:** 2026-06-08 (30 days for the stack — pgvector + asyncpg + SQLAlchemy + FastAPI versions are stable; CVE advisories may add new ones — re-check python-jose advisories before locking the version pin)
