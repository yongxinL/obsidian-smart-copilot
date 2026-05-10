# Phase 1b: Auth + Security Primitives - Pattern Map

**Mapped:** 2026-05-08
**Files analyzed:** 27 (new + modified)
**Analogs found:** 24 / 27 (3 files have no close analog — flagged below)

> Notes:
> - Phase 1a delivered the **skeleton**: domain models for `users`, `sessions`,
>   `mcp_tokens`, `provider_keys`, `audit_log` already exist; `dependencies.get_db_session`
>   already does `RESET app.current_user_id` in `finally:` (canonical shape); RLS is
>   `ENABLE + FORCE`d on 22 tables but `CREATE POLICY` is deferred to 1b.
> - Phase 1b extends in place. The planner should **not duplicate** existing models,
>   migrations, or the dependency shape — extend them.

---

## File Classification

| New / Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `server/app/encryption.py` | utility / crypto wrapper | transform | `server/app/database.py` (singleton + lazy init pattern) | role-match |
| `server/app/auth/__init__.py` | package marker | n/a | `server/app/routes/__init__.py` | exact |
| `server/app/auth/context.py` | model (frozen dataclass) | transform | `server/app/models/base.py` (declarative class layout) | partial — no existing dataclass |
| `server/app/auth/core.py` | service (transport-neutral validators) | request-response | NEW SHAPE — closest discipline analog: `server/app/database.py` (no FastAPI imports) | partial |
| `server/app/auth/password.py` | utility | transform (CPU-bound async-offload) | NO ANALOG (first CPU-bound async helper) | none |
| `server/app/auth/tokens.py` | utility | transform | NO ANALOG (first JWT helper) | none |
| `server/app/auth/mcp_tokens.py` | utility | transform | `server/app/auth/tokens.py` (sibling, both `secrets`+`hashlib`) | n/a — peer module |
| `server/app/auth/middleware.py` | middleware | request-response | NO ANALOG (first ASGI middleware in repo) | none |
| `server/app/auth/deps.py` | dependency factory (FastAPI Depends) | request-response | `server/app/dependencies.py:get_db_session` | exact |
| `server/app/auth/audit.py` | service helper | CRUD-write | NEW; uses `models/audit_log.py` directly | partial |
| `server/app/services/__init__.py` | package marker | n/a | `server/app/routes/__init__.py` | exact |
| `server/app/services/users.py` | service | CRUD | NEW; pure-function pattern; NO FastAPI imports per CLAUDE.md | partial |
| `server/app/services/sessions.py` | service | CRUD (transactional rotate) | sibling `services/users.py` | peer |
| `server/app/services/mcp_tokens.py` | service | CRUD + last_used_at touch | sibling | peer |
| `server/app/services/provider_keys.py` | service | CRUD + Fernet wrap | sibling | peer |
| `server/app/routes/auth.py` | controller (HTTP) | request-response | `server/app/routes/health.py` | role-match (only existing route) |
| `server/app/routes/admin.py` | controller (HTTP) | request-response | `server/app/routes/health.py` | role-match |
| `server/app/dependencies.py` (MODIFY) | dependency | request-response | itself, Phase 1a shape | extend in place |
| `server/app/settings.py` (MODIFY) | config | n/a | itself | extend in place |
| `server/app/main.py` (MODIFY) | bootstrap | startup-fail | itself | extend in place |
| `server/app/database.py` (MODIFY — add PoolEvents.reset listener) | infra | event-driven | itself (already has `event.listens_for(engine.sync_engine, "connect")`) | exact pattern present |
| `server/app/models/login_attempt.py` | model | n/a | `server/app/models/audit_log.py` (no `user_id` FK to user; system-only writer; no RLS) | exact |
| `server/app/models/__init__.py` (MODIFY — register login_attempt) | barrel | n/a | itself | extend in place |
| `server/app/models/session.py` (MODIFY — add `admin_fresh_until`) | model | n/a | itself | extend in place |
| `alembic/versions/0002_phase_1b_auth.py` | migration | schema | `alembic/versions/0001_initial_schema.py` | role-match (only existing migration) |
| `server/app/scheduler/jobs/prune_login_attempts.py` | scheduled job | batch | `server/app/scheduler/run.py` (signal handlers + module-level loop) | partial |
| `server/app/logging/redaction.py` | utility (structlog processor) | transform | NO ANALOG (no logging module yet) | none |
| `server/app/cli/__init__.py` + entry-points | controller (CLI) | command | NO ANALOG (no CLI yet) | none |
| `server/app/tests/auth/conftest.py` + tests | test | request-response | `server/app/tests/conftest.py` + `tests/integration/test_boot.py` | exact |
| `server/app/tests/test_rls_isolation.py` | test (TEST-02) | request-response | `server/app/tests/integration/test_boot.py::test_rollback_isolation_first` (rollback isolation pattern, very similar two-phase test shape) | role-match |
| `server/requirements.txt` (MODIFY) | dependency manifest | n/a | itself | extend in place |
| `.env.example` (MODIFY) | config | n/a | itself | extend in place |

---

## Pattern Assignments

### `server/app/encryption.py` (NEW — utility / Fernet seam)

**Analog:** `server/app/database.py` (lazy/eager singleton pattern via module-level state)

**Imports pattern** (database.py:12-18):
```python
from __future__ import annotations

from pgvector.asyncpg import register_vector
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.settings import settings
```
→ Apply: `from cryptography.fernet import Fernet, MultiFernet`, `from app.settings import settings`. Always use `from __future__ import annotations`. Settings imported as `settings` (module-level singleton, never `Settings()` re-instantiated).

**Singleton pattern** (database.py:20-24, 40-44):
```python
engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=settings.debug,
)
# ...
async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
```
→ Apply: module-level `_fernet: MultiFernet | None = None` + `fernet()` accessor; the lazy form (per RESEARCH §Pattern 5) is preferred over eager so the test suite can swap settings without import-time side-effect. **Container fail-on-startup** lives in `main.py` (see below), not in `encryption.py` — keep this module testable in isolation.

**Function-shape pattern** (database.py:27-37 — small, doc-rich, single concern):
```python
@event.listens_for(engine.sync_engine, "connect")
def _register_vector_type(dbapi_connection, connection_record):  # noqa: ARG001
    """Register pgvector codec on every new asyncpg connection."""
    dbapi_connection.run_async(register_vector)
```
→ Apply same level of inline justification (`Why … not …`) for `decrypt_provider_key` (the `ttl=None` rationale per Landmine #4).

**Public surface:** `encrypt_provider_key(plaintext: str) -> bytes`, `decrypt_provider_key(ciphertext: bytes) -> str`, `class FernetKeyMissing(RuntimeError)`. Plain functions — no class.

---

### `server/app/auth/__init__.py` (NEW — package marker)

**Analog:** `server/app/routes/__init__.py:1` (one-liner package docstring):
```python
"""HTTP route modules."""
```
→ Apply: `"""Auth subsystem: argon2, JWT, MCP bearer, OperationContext, RLS GUC."""`. Single-line, no re-exports. Sibling modules are imported by full path.

---

### `server/app/auth/context.py` (NEW — frozen dataclasses)

**Analog:** `server/app/models/base.py:1-21` (declarative shape) — but this is *not* an ORM model. The frozen-dataclass shape is new. Use the **convention** from base.py:
- `from __future__ import annotations` at top
- module docstring referencing the relevant `D-` decision
- subclassing pattern (`@dataclass(frozen=True, slots=True)` ≅ `class Base(DeclarativeBase)`)

**Direct copy from RESEARCH.md §"OperationContext dataclass" (lines 1062-1087)** — already concrete:
```python
from dataclasses import dataclass
from typing import Literal
import uuid

@dataclass(frozen=True, slots=True)
class AuthResult:
    user_id: uuid.UUID | None = None
    role: str | None = None
    session_id: uuid.UUID | None = None
    mcp_token_id: uuid.UUID | None = None
    error: str | None = None  # "invalid_token" | "missing_auth" | "service_unavailable"

@dataclass(frozen=True, slots=True)
class OperationContext:
    user_id: uuid.UUID
    role: Literal["admin", "user"]
    transport: Literal["rest", "mcp_http", "mcp_stdio", "cli", "system"]
    remote: bool
    client_name: str
    request_id: str
    session_id: uuid.UUID | None = None
    mcp_token_id: uuid.UUID | None = None
```

**Critical:** No FastAPI imports. No SQLAlchemy imports. `auth/core.py` imports this; transports import this; services import this — but this module imports neither.

---

### `server/app/auth/core.py` (NEW — pure validators)

**Analog (discipline only):** `server/app/database.py` — both modules deliberately avoid FastAPI types. There is no closer analog because this is the first transport-neutral service-style module.

**Function shape** — `validate_jwt`, `validate_refresh`, `validate_bearer` all return `AuthResult` (frozen dataclass). NEVER raise HTTP exceptions. Errors return `AuthResult(error="...")`. RESEARCH.md §"MCP SDK TokenVerifier integration" (lines 989-1004) confirms callers map `AuthResult.error` → transport response.

**Imports allowed in core.py:**
- `app.auth.context.AuthResult`
- `app.settings.settings`
- `app.database.async_session_factory` (DB lookups for refresh/MCP tokens)
- stdlib (`hashlib`, `uuid`, `secrets`)
- `jose.jwt`, `jose.JWTError` — **must** include `algorithms=["HS256"]` allowlist (Landmine #2; RESEARCH.md lines 386-394)

**Imports forbidden:** `fastapi.*`, `starlette.*` — anything HTTP-shaped.

---

### `server/app/auth/password.py` (NEW)

**No analog in repo.** Use the verified pattern from RESEARCH.md §Pattern 1 (lines 322-352):
```python
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError, VerificationError
import asyncio

_HASHER = PasswordHasher(
    time_cost=3,
    memory_cost=64 * 1024,
    parallelism=1,
    hash_len=32,
    salt_len=16,
)

async def hash_password(plaintext: str) -> str:
    return await asyncio.to_thread(_HASHER.hash, plaintext)

async def verify_password(stored_hash: str, plaintext: str) -> bool:
    try:
        await asyncio.to_thread(_HASHER.verify, stored_hash, plaintext)
        return True
    except (VerifyMismatchError, InvalidHashError, VerificationError):
        return False

def needs_rehash(stored_hash: str) -> bool:
    return _HASHER.check_needs_rehash(stored_hash)
```

**Why no in-repo analog:** First CPU-bound code on the async path. **`asyncio.to_thread` is mandatory** (Landmine #6). Lint rule: any direct `_HASHER.verify` call outside this module is a bug.

---

### `server/app/auth/tokens.py` (NEW — JWT)

**No analog.** Direct copy from RESEARCH.md §Pattern 2 (lines 369-389). **Two non-negotiable details:**
1. `algorithms=[ALGORITHM]` is a **non-empty list** (Landmine #2 / CVE-2024-33663 + CVE-2025-61152)
2. python-jose floor is **`>= 3.4`** (NOT 3.3 — the literal CLAUDE.md pin). Researcher overrides this in requirements.txt.

CI grep gate (RESEARCH.md line 846):
```bash
git grep -nE 'jwt\.decode\([^)]*\)' | grep -v 'algorithms=\['
```
must return empty.

---

### `server/app/auth/mcp_tokens.py` (NEW — peer of tokens.py)

**Analog:** sibling `auth/tokens.py` (use the same import header + module-docstring convention).

Direct copy from RESEARCH.md §Pattern 4 (lines 446-470):
```python
import secrets, hashlib

PREFIX = "scmcp_"
HASH_ALG = "sha256"

def generate_token() -> tuple[str, str, str]:
    raw = secrets.token_urlsafe(32)
    plaintext = PREFIX + raw
    token_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    last4 = plaintext[-4:]
    return plaintext, token_hash, last4
```

**Place the DB-touching `verify_token` in `services/mcp_tokens.py`**, not here — `auth/mcp_tokens.py` is the pure crypto helper, `services/mcp_tokens.py` is the row CRUD (mirrors the `auth/` vs `services/` discipline).

---

### `server/app/auth/middleware.py` (NEW — first ASGI middleware)

**No analog in repo.** Phase 1a's `main.py:create_app()` adds no middleware. Direct copy from RESEARCH.md §Pattern 10 (lines 712-735) for `TrustedProxyMiddleware`. Mounted in `main.py:create_app()` per RESEARCH.md lines 740-745.

**`get_operation_context` Depends factory** also lives here (or in `auth/deps.py` — planner's call; my recommendation is `deps.py`):
- reads `Authorization: Bearer <jwt>` from `request.headers`
- calls `auth.core.validate_jwt(token)`
- builds `OperationContext(transport="rest", remote=True, ...)` from `AuthResult`
- raises `HTTPException(401)` if `AuthResult.error` set (transports map errors to HTTP)
- reads `request.state.client_ip` (set by `TrustedProxyMiddleware`) for `OperationContext.client_name` if useful

---

### `server/app/auth/deps.py` (NEW — FastAPI Depends factories)

**Analog:** `server/app/dependencies.py:get_db_session` (existing — current shape):
```python
async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            try:
                await session.execute(text("RESET app.current_user_id"))
            except Exception:  # noqa: BLE001 — defensive cleanup only
                pass
            await session.close()
```
→ Apply: `async def` + `Depends(other)` in signature (chain `require_admin` → `require_fresh_auth`); raise `HTTPException(403, detail=...)` for failures.

Direct copy from RESEARCH.md §Pattern 9 (lines 680-705) for `require_admin`, `require_fresh_auth`, `admin_reauth_required_envelope()`. Failure envelope shape locked by D-16:
```json
{"error": {"code": "admin_reauth_required",
           "message": "Fresh admin authentication is required.",
           "details": {"reauth_url": "/api/v1/admin/reauth", "freshness_window_minutes": 60}}}
```

---

### `server/app/auth/audit.py` (NEW)

**Analog:** writes rows to the **existing** `models/audit_log.py` table (Phase 1a shape). Imports needed:
```python
from app.models.audit_log import AuditLog
from app.auth.context import OperationContext
```
Helper: `async def write_audit_log(session, ctx: OperationContext, *, action: str, target_kind: str | None, target_id: str | None, details: dict | None) -> None`.

**Critical:** `audit_log` is **not** in the `RLS_TABLES` list in 0001 (verified — line 32-55 of `0001_initial_schema.py` does **not** include `audit_log`). Writes work without any RLS dance. Service routinely writes from authenticated and from system contexts.

---

### `server/app/services/__init__.py`, `services/users.py`, `services/sessions.py`, `services/mcp_tokens.py`, `services/provider_keys.py` (NEW package)

**Discipline:** services take `OperationContext` + `AsyncSession`; **NO FastAPI imports** (CLAUDE.md, D-17, D-18). The closest in-repo discipline analog is `database.py` (no FastAPI types). There is no full service in the repo yet — this phase introduces the convention.

**Package marker** (`services/__init__.py`):
```python
"""Transport-agnostic service layer. Services take OperationContext, never FastAPI request types."""
```

**`services/sessions.py:rotate_refresh`** — direct copy of the atomic transaction pattern from RESEARCH.md §Pattern 3 (lines 412-435):
```python
async def rotate_refresh(session: AsyncSession, raw_refresh: str) -> tuple[str, str]:
    rh = hashlib.sha256(raw_refresh.encode()).hexdigest()
    async with session.begin():
        row = await session.execute(
            select(SessionModel).where(SessionModel.token_hash == rh).with_for_update()
        )
        s = row.scalar_one_or_none()
        if s is None or s.expires_at < utcnow():
            raise InvalidToken()
        await session.execute(delete(SessionModel).where(SessionModel.id == s.id))
        new_refresh = secrets.token_urlsafe(32)
        new_session = SessionModel(
            user_id=s.user_id,
            token_hash=hashlib.sha256(new_refresh.encode()).hexdigest(),
            expires_at=utcnow() + timedelta(seconds=settings.jwt_refresh_ttl_seconds),
        )
        session.add(new_session)
        access = issue_access_jwt(user_id=s.user_id, role=user.role, ...)
    return access, new_refresh
```

**`services/provider_keys.py`** — Pydantic response model with `Field(exclude=True)` per CLAUDE.md / D-28; direct copy from RESEARCH.md §Pattern 6 (lines 535-543):
```python
class ProviderKeyResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    provider: str
    key_hint: str
    created_at: datetime
    encrypted_key: bytes = Field(exclude=True)
```

---

### `server/app/routes/auth.py`, `routes/admin.py` (NEW controllers)

**Analog:** `server/app/routes/health.py:1-16` (the only existing route file):
```python
"""Health endpoint. Phase 1a returns shallow {status: ok} only."""
from __future__ import annotations
from fastapi import APIRouter

router = APIRouter(tags=["system"])

@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

**Apply pattern:**
1. Module docstring lists which `D-` decisions / REQ-IDs the route implements.
2. `router = APIRouter(tags=["auth"])` (and `prefix="/api/v1/admin"` for admin.py per D-12).
3. Async handlers, return `dict | BaseModel`.
4. Add to `main.py:create_app()` with `app.include_router(router)` (mirror `health_router` line 27).
5. **Use `Depends`** for `OperationContext`, `AsyncSession`, `require_admin`, `require_fresh_auth`. Never inline auth logic in the handler.
6. Map service-layer domain errors (`InvalidToken`, `RateLimited`, `InvalidPassword`) to HTTP status codes **here**, not in services.

**Rate-limit transaction discipline (Landmine #9):** in `/auth/login`, INSERT the `login_attempts` row in **its own transaction** before password verify, so a downstream rollback cannot erase the failure record.

---

### `server/app/dependencies.py` (MODIFY — extend existing)

**Existing canonical shape** (lines 1-32) is already correct for Phase 1a (defensive RESET in finally). Phase 1b extends:

1. Add `Depends(get_operation_context)` parameter to `get_db_session`.
2. After session is opened and BEFORE `yield`: SET three GUCs via `set_config(name, value, false)` (Landmine #5 — `SET ... = $1` is illegal SQL):
   ```python
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
   ```
3. Extend the existing `finally:` (lines 27-32) to RESET all three. The existing `try/except BLE001` shape is the canonical cleanup — keep it.
4. Add `session_with_rls(ctx: OperationContext)` helper (per D-20 / "specifics") — same body, but takes ctx as a regular argument, not `Depends`. Used by APScheduler jobs and CLI.

Direct copy of the extended shape from RESEARCH.md §Pattern 7 (lines 575-606). The Phase 1a `RESET app.current_user_id` line is preserved in the new shape — do NOT rewrite from scratch; **patch in place**.

---

### `server/app/database.py` (MODIFY — add PoolEvents.reset listener)

**Analog:** itself, lines 27-37 — the existing `@event.listens_for(engine.sync_engine, "connect")` decorator. Apply the **same `event.listens_for(engine.sync_engine, "reset")` shape** as a fail-safe per Landmine #1.

Direct copy from RESEARCH.md lines 619-630:
```python
@event.listens_for(engine.sync_engine, "reset")
def _on_pool_reset(dbapi_conn, connection_record, reset_state):
    """Defense-in-depth: even if get_db_session's RESET fails, scrub on pool checkin."""
    try:
        with dbapi_conn.cursor() as cur:
            cur.execute("RESET app.current_user_id")
            cur.execute("RESET app.current_user_role")
            cur.execute("RESET app.request_id")
    except Exception:  # noqa: BLE001
        pass
```

**Place the new listener directly under the existing `_register_vector_type` listener** so the pattern signature reads consistently.

---

### `server/app/settings.py` (MODIFY — extend Settings)

**Existing shape** (lines 1-29):
```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str = Field(default="...")
    alembic_database_url: str = Field(default="...")
    test_database_url: str = Field(default="")
    smartcopilot_fernet_key: str = Field(default="")  # ← already present
    smartcopilot_host_url: str = Field(default="http://localhost:8000")
    debug: bool = Field(default=False)

settings = Settings()
```

**Apply pattern:** add fields **into the same `Settings` class**, immediately under the Phase 1a fields (no new BaseSettings subclass). Use `Field(default=...)` exclusively (matches existing convention; do NOT mix in `Field(default_factory=...)` unless required — for `list[str]` it is required, see below).

Direct copy from RESEARCH.md §"Pydantic v2 settings extension" (lines 1033-1056):
```python
# JWT
jwt_signing_key: str = Field(default="")  # fail-fast in main.py if empty
jwt_access_ttl_seconds: int = Field(default=900)
jwt_refresh_ttl_seconds: int = Field(default=2592000)
# Argon2 (D-23)
argon2_time_cost: int = Field(default=3)
argon2_memory_cost: int = Field(default=64 * 1024)
argon2_parallelism: int = Field(default=1)
# Rate limit
login_rate_limit_window_seconds: int = Field(default=900)
login_rate_limit_max_failures: int = Field(default=10)
login_attempts_retention_hours: int = Field(default=24)
# Step-up
admin_fresh_window_minutes: int = Field(default=60)
# Trusted proxy
smartcopilot_trust_proxy: bool = Field(default=False)
smartcopilot_trusted_proxy_cidrs: list[str] = Field(default_factory=list)
```

`extra="ignore"` (line 13) is already configured — unrecognised env vars are silently dropped. `case_sensitive=False` (line 14) means `JWT_SIGNING_KEY` and `jwt_signing_key` map to the same field.

---

### `server/app/main.py` (MODIFY — startup-fail check + middleware + routers)

**Existing shape** (lines 1-31):
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import engine
from app.routes.health import router as health_router

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()

def create_app() -> FastAPI:
    app = FastAPI(title="Smart Copilot", version="0.0.0", lifespan=lifespan)
    app.include_router(health_router)
    return app

app = create_app()
```

**Apply patches (preserve module discipline from D-09 — main.py is bootstrap only):**
1. Top of module (or in `lifespan`'s "before yield" half): import `fernet, FernetKeyMissing` from `app.encryption`; call `fernet()` once and `sys.exit(1)` on `FernetKeyMissing`. Direct copy from RESEARCH.md lines 516-523. Same `JWT_SIGNING_KEY` empty-check (fail closed if `settings.jwt_signing_key == ""`).
2. In `create_app()`, after `app = FastAPI(...)` and **before** `include_router`:
   ```python
   app.add_middleware(
       TrustedProxyMiddleware,
       trust_proxy=settings.smartcopilot_trust_proxy,
       allowlist_cidrs=settings.smartcopilot_trusted_proxy_cidrs,
   )
   ```
3. `app.include_router(auth_router)` and `app.include_router(admin_router)` next to the existing `health_router` line. Mirror the existing one-line-per-router style.
4. Do **NOT** create the engine here. Phase 1a D-09 owner discipline: engine lives in `database.py`.

---

### `server/app/models/login_attempt.py` (NEW model)

**Analog:** `server/app/models/audit_log.py` (the closest model — both are append-only, `user_id` is FK-like but nullable, no RLS in `RLS_TABLES`, single-writer system table):

```python
"""Audit log domain model — REQ-313."""
from __future__ import annotations
from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[object | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    # ...
    ip: Mapped[object | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()",
    )
```

**Apply directly** to `login_attempt.py`:
- `__tablename__ = "login_attempts"`
- `id: BigInteger primary_key autoincrement`
- `ip: INET nullable=False`
- `username: String(64) nullable=False`
- `attempted_at: DateTime(timezone=True) nullable=False server_default="now()"` (mirror `audit_log.created_at`)
- `user_agent: Text nullable=True`
- `request_id: String(64) nullable=True`
- **No FK to users** (D-06: written via system context regardless of user existence; usernames may not exist)
- **No `TimestampMixin`** (single timestamp, named `attempted_at`, mirrors audit_log)

**Critical:** D-06 says `login_attempts` is **NOT** under user RLS. Migration must NOT add it to the RLS-enable loop or any `CREATE POLICY` block.

---

### `server/app/models/__init__.py` (MODIFY — register login_attempt)

**Existing shape** (lines 15-44): alphabetical-ish import list with `# noqa: F401`. Apply: insert
```python
login_attempt,  # noqa: F401
```
between `link` and `llm_usage` (alphabetical). The `# noqa: F401` is mandatory (per the existing module docstring line 12-14) — Ruff F401 is not globally exempted.

---

### `server/app/models/session.py` (MODIFY — add `admin_fresh_until`)

**Existing shape** (lines 1-37): single-class file with five columns. Apply: add one column under `created_at` (or order with `expires_at`):
```python
admin_fresh_until: Mapped[object | None] = mapped_column(
    DateTime(timezone=True), nullable=True,
)
```
Keep the `Mapped[object | None]` style used by `expires_at` (line 30) — the existing file uses `object` not `datetime` for these. Stay consistent within the file even though `models/base.py:TimestampMixin` uses `datetime`.

---

### `alembic/versions/0002_phase_1b_auth.py` (NEW migration)

**Analog:** `alembic/versions/0001_initial_schema.py` (the only existing migration, 1,127 lines). Apply structure:

**Header pattern** (0001 lines 1-27):
```python
"""initial_schema

Revision ID: 0001
Revises:
Create Date: 2026-05-08 04:59:26.003260

D-06: Single initial migration covering all 32 domain tables.
D-07: Created via Alembic autogenerate against live pgvector:pg16 DB.
"""

from __future__ import annotations
from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import VECTOR
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
```
→ Apply: revision = `"0002"`, `down_revision = "0001"`. File name `0002_phase_1b_auth.py` matches D-06 / Phase 1a precedent.

**Table-create pattern** (0001 lines 226-244 — `audit_log` is the closest match for `login_attempts` shape):
```python
op.create_table(
    "audit_log",
    sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column("user_id", sa.UUID(), nullable=True),
    sa.Column("ip", postgresql.INET(), nullable=True),
    sa.Column("user_agent", sa.Text(), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True),
              server_default="now()", nullable=False),
    sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    sa.PrimaryKeyConstraint("id"),
)
```
→ Apply directly to `login_attempts`. Use `server_default="now()"` (string) — that's the convention in 0001 for `created_at` columns, NOT `sa.text("now()")`. Both work; stay consistent with the closest analog.

**Column-add pattern (`sessions.admin_fresh_until`):** standard alembic op:
```python
op.add_column("sessions", sa.Column("admin_fresh_until", sa.DateTime(timezone=True), nullable=True))
```

**Index-create pattern** (0001 lines 1027-1043): three styles in 0001 — `op.execute("CREATE INDEX ...")` for partial / specialised, and `op.create_index(...)` for plain B-tree. For `login_attempts` use `op.execute` with the explicit DESC ordering (RESEARCH.md lines 661-663):
```python
op.execute(
    "CREATE INDEX IF NOT EXISTS login_attempts_lookup_idx "
    "ON login_attempts (ip, username, attempted_at DESC)"
)
```

**RLS POLICY pattern** (0001 lines 1050-1054 + RESEARCH.md §Pattern 7):
```python
# 0001 already ENABLED + FORCED RLS on these tables (line 32-55 list).
# 0002 adds the POLICY for each. Boilerplate (one per RLS_TABLES entry):
for tbl, user_col in RLS_POLICY_TABLES:  # list of (table, owner_column) tuples
    op.execute(f"""
        CREATE POLICY {tbl}_owner ON {tbl}
        USING ({user_col} = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        WITH CHECK ({user_col} = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
    """)
```
**`NULLIF(..., '')::uuid` + `current_setting('...', true)` is mandatory** — Landmine #8 + RESEARCH.md lines 562-571 (graceful unset → fail-closed).

`RLS_POLICY_TABLES` is a sibling of 0001's `RLS_TABLES` constant (line 32-55) — adapt the list, but for tables where the owner column is on a parent (`pages.vault_id → vaults.owner_user_id`), the policy uses a subquery; planner must enumerate per-table.

**`downgrade()` pattern** (0001 lines 1057-1126): mirror image of `upgrade()`. Drop policies first (`DROP POLICY ...`), then column, then table. Drop the index inside the table-drop (or separately with `op.drop_index` if added with `op.create_index`).

**Seed pattern (system user):** 0001 has no seed. For 1b's `INSERT INTO users (id, username, ...)`, use raw `op.execute("INSERT INTO ...")` — no seed file needed for one row.

**ENUM caution (Landmine #10):** 0002 must NOT redefine `user_role_enum`. Migration only references existing types. If a new ENUM is needed (e.g., for a `factor` column), follow the 0001 convention: `op.execute("CREATE TYPE foo AS ENUM (...)")` paired with `postgresql.ENUM(..., create_type=False)` in column definitions and a paired `DROP TYPE IF EXISTS` in downgrade.

---

### `server/app/scheduler/jobs/prune_login_attempts.py` (NEW)

**Analog:** `server/app/scheduler/run.py` (the supervisord scheduler entrypoint). The **job module** (not entrypoint) is new. Use the convention:
- Module-level functions only (CLAUDE.md: "Lambda / closure job args cannot be pickled; always use module-level functions for scheduled jobs")
- Take no arguments (or only picklable args)
- Use `session_with_rls(SystemContext)` from `dependencies.py` (per D-20) to get a DB session — system context bypasses user RLS by setting a system UUID

**Function shape:**
```python
async def prune_login_attempts() -> None:
    """Hourly APScheduler job — D-09 retention default 24h."""
    ctx = system_operation_context()  # helper in auth/context.py
    async for session in session_with_rls(ctx):
        await session.execute(
            text("DELETE FROM login_attempts WHERE attempted_at < now() - make_interval(hours => :h)"),
            {"h": settings.login_attempts_retention_hours},
        )
        await session.commit()
```

The job is **registered** in `app.scheduler.run.main()` when 1b extends it from stub to real (or in a sibling registration helper). For 1b the registration call can be a stub if APScheduler full wiring is deferred — but the **function** must exist and be testable.

---

### `server/app/logging/redaction.py` (NEW — first logging module)

**No analog in repo.** Per D-27 and CLAUDE.md (structlog field redaction filter). Add `structlog>=24` to requirements (RESEARCH.md line 184). Implement a structlog `processor` that walks event_dict and replaces values for keys: `password, password_hash, encrypted_key, token, token_hash, refresh_token, access_jwt` with `"<redacted>"`.

**Wiring:** module-level `structlog.configure(...)` call. Phase 1b is the right phase to land the basic logging skeleton — every later phase logs through it. Keep it minimal (one processor + JSON renderer); rich logging is Phase 6.

---

### `server/app/cli/__init__.py` and CLI entry-points (NEW stub)

**No analog.** CONTEXT.md §"Integration Points" calls this a stub for 1b (full CLI is 1d). Minimal surface:
- `server/app/cli/main.py` with `argparse` (or `typer` — but `typer` is not in CLAUDE.md's stack; **use stdlib `argparse`** for 1b)
- Subcommands: `user create`, `mcp token create/list/revoke`, `provider key set`
- Each subcommand calls into `services/*` directly with a CLI-built `OperationContext(transport="cli", remote=False, ...)` and `session_with_rls(ctx)`.

The CLI is a **test consumer** of the services for Phase 1b success criterion 1 ("admin can create user, MCP token, set provider key via CLI without HTTP").

---

### `server/app/tests/auth/conftest.py` and `tests/auth/test_*.py` (NEW)

**Analog:** `server/app/tests/conftest.py` (lines 1-95) and `tests/integration/test_boot.py`.

**conftest.py existing fixtures to reuse (do NOT duplicate):**
- `postgres_container` (session-scope) — line 38-42
- `test_engine` (session-scope, runs alembic upgrade head) — line 45-79
- `db_session` (session-scope) — line 82-94

**Apply pattern in `tests/auth/conftest.py`:** add **function-scoped** auth fixtures that consume the existing engine — for example `seed_admin_user`, `seed_basic_user`, `issue_access_jwt_for(user_id)`. Don't override session-scope fixtures.

The existing pyproject config (`asyncio_default_test_loop_scope = "session"`, line 40 of pyproject.toml) **forbids function-scoped event loops** that try to use session-scoped asyncpg resources — every new fixture must be session-scoped or function-scoped without crossing the boundary. New tests follow the existing test_boot.py module-level pytestmark style (line 18: `pytestmark = pytest.mark.integration`).

**Test-file shape** copy from test_boot.py:
```python
"""Phase 1b auth integration tests — covers AUTH-01..AUTH-10."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from app.main import app

pytestmark = pytest.mark.integration

async def test_login_returns_jwt_pair(db_session, seed_basic_user) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/auth/login", json={"username": "...", "password": "..."})
    assert resp.status_code == 200
    body = resp.json()
    assert "access_jwt" in body and "refresh_token" in body
```

---

### `server/app/tests/test_rls_isolation.py` (NEW — TEST-02 / D-30)

**Analog:** `server/app/tests/integration/test_boot.py` lines 65-114 — the **two-phase rollback isolation pattern**. Apply the same shape: one test seeds and runs request-scope as User A, second test (or same test using two factories) verifies User B sees no leak.

```python
async def test_rls_isolation_first(test_engine) -> None:
    factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        # SET app.current_user_id to user A, INSERT a row in pages, commit
        # ... (uses set_config like dependencies.py)
async def test_rls_isolation_second(test_engine) -> None:
    factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        # Without SET — assert current_setting('app.current_user_id', true) returns ''
        # Assert: SELECT * FROM pages returns 0 rows (RLS fails closed when GUC unset)
```

**Critical:** the test must reuse `test_engine` so it shares the same connection pool that Landmine #1 attacks. Building a fresh engine inside the test would short-circuit the leak detection.

---

### `server/requirements.txt` (MODIFY)

**Existing shape** (lines 1-10): one-package-per-line, `>=` floors only.
```
fastapi>=0.111
uvicorn[standard]>=0.30
pydantic>=2
pydantic-settings>=2.0
python-dotenv>=1.0
sqlalchemy>=2.0
alembic>=1.13
asyncpg>=0.29
psycopg2-binary>=2.9
pgvector>=0.3
```

**Apply pattern (additions, in same style):**
```
argon2-cffi>=23.1
python-jose[cryptography]>=3.4   # NOT >=3.3 — CVE-2024-33663 + CVE-2025-61152
cryptography>=42
structlog>=24
```

Add `testcontainers>=4.0` to `requirements-dev.txt` only if not already present (it is — line 4 of requirements-dev.txt).

---

## Shared Patterns

### Authentication chain: transport → core → context → DB session
**Sources:** RESEARCH.md §Architecture Diagram (lines 213-271); RESEARCH.md §Pattern 7 (lines 552-606); existing `dependencies.py` lines 23-32.

**Apply to:** every authenticated route, every transport adapter (REST middleware, MCP HTTP TokenVerifier, MCP stdio bootstrap, CLI), every APScheduler job.

```
request → middleware (build OperationContext) → Depends(get_db_session, ctx)
       → SET 3 GUCs via set_config(name, value, false) before yield
       → service layer (takes ctx + session)
       → finally: RESET 3 GUCs (existing canonical shape)
       → connection returns to pool
       → PoolEvents.reset listener (fail-safe) RESETs again
```

### Error envelope shape
**Source:** D-16 (CONTEXT.md), RESEARCH.md §Pattern 9 (lines 700-705).
**Apply to:** every HTTP error from `routes/auth.py`, `routes/admin.py`, and `auth/deps.py` raises.
```json
{"error": {"code": "<snake_case>", "message": "<human>", "details": {...}}}
```

### Async-offload for CPU-bound calls
**Source:** RESEARCH.md §Landmine #6 (lines 913-925).
**Apply to:** every `argon2 .hash` and `.verify` call (only one call site: `auth/password.py`).

### `Field(exclude=True)` for sensitive bytes
**Source:** CLAUDE.md line "encrypted_key fields MUST use Field(exclude=True)…", D-28.
**Apply to:** every Pydantic model in `services/provider_keys.py` and any future module that surfaces a `provider_keys` row. CI grep gate (RESEARCH.md line 547) recommended.

### RLS GUC `set_config` pattern
**Source:** RESEARCH.md §Pattern 7 + Landmine #5 (lines 891-911).
**Apply to:** `dependencies.py:get_db_session`, `dependencies.py:session_with_rls`, anywhere else that opens an `AsyncSession` outside the dependency (= nowhere; this is the one true path). NEVER use `text("SET app.x = :x")`.

### RLS POLICY shape
**Source:** RESEARCH.md §Pattern 7 lines 553-571.
**Apply to:** `0002_phase_1b_auth.py` for every table in 0001's `RLS_TABLES` list.
```sql
CREATE POLICY <table>_owner ON <table>
    USING (<owner_col> = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
    WITH CHECK (<owner_col> = NULLIF(current_setting('app.current_user_id', true), '')::uuid);
```
For tables whose owner is on a parent (e.g., `pages.vault_id → vaults.owner_user_id`), use a subquery `EXISTS (SELECT 1 FROM vaults v WHERE v.id = pages.vault_id AND v.owner_user_id = …)`.

### Alembic migration file conventions
**Source:** `alembic/versions/0001_initial_schema.py`.
**Apply to:** `0002_phase_1b_auth.py`.
- `from __future__ import annotations` first
- Top-of-file docstring lists the `D-` decisions and REQ-IDs covered
- `revision: str = "0002"`, `down_revision: str | None = "0001"`
- `upgrade()` → tables → indices → RLS policies → seed
- `downgrade()` → seed delete → drop policies → drop indices → drop tables (reverse order of upgrade)
- ENUM `create_type=False` if reusing existing types (Landmine #10)

### Models barrel registration
**Source:** `models/__init__.py` lines 15-44.
**Apply to:** any new model file added to `models/`. Import in alphabetical order with `# noqa: F401`.

### Test-file conventions
**Source:** `tests/integration/test_boot.py`.
**Apply to:** every test file under `tests/auth/` and `tests/test_rls_isolation.py`.
- `from __future__ import annotations`
- module docstring referencing the REQ-IDs covered
- `pytestmark = pytest.mark.integration` (or `unit` for `tests/unit/test_password.py` — add `unit` marker to pyproject.toml `markers` list)
- prefer `httpx.AsyncClient(transport=ASGITransport(app=app))` for HTTP routes
- reuse `db_session` / `test_engine` fixtures from existing `conftest.py` — do not build new engines

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `server/app/auth/password.py` | utility | CPU-bound async transform | First CPU-bound code on async path; `asyncio.to_thread` pattern is new in repo |
| `server/app/auth/tokens.py` | utility | transform | First JWT helper |
| `server/app/auth/middleware.py` | middleware | request-response | First ASGI middleware; main.py currently has none |
| `server/app/logging/redaction.py` | utility (structlog processor) | transform | No logging module exists yet |
| `server/app/cli/*` | controller (CLI) | command | No CLI exists yet |

For these files the planner should follow **RESEARCH.md** code excerpts directly (cited above per file). They establish the convention rather than copy from one.

---

## Metadata

**Analog search scope:** `server/app/`, `server/alembic/`, `server/app/tests/` (read-only)
**Files scanned:** ~25 source files + 1 migration + 2 tests
**Phase 1a status:** all 32 domain models present; `0001_initial_schema.py` shipped; `dependencies.get_db_session` already has the RESET-in-finally shape; mcp/server.py and scheduler/run.py are stubs awaiting Phase 1b/1d wiring; tests use real PG via testcontainers (`pgvector/pgvector:pg16` — same as production).
**Pattern extraction date:** 2026-05-08
