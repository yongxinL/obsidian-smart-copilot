---
phase: 1b
plan: "05"
name: core-rls-deps
wave: 2
depends_on: ["02", "04"]
requirements: [AUTH-02, AUTH-04, AUTH-06, TEST-02]
files_modified:
  - server/app/auth/core.py
  - server/app/auth/audit.py
  - server/app/dependencies.py
  - server/app/database.py
  - server/app/tests/auth/test_rls_isolation.py
autonomous: true
must_haves:
  truths:
    - "validate_jwt(token) returns AuthResult with user_id+role (and session_id from optional 'sid' claim) on success, or AuthResult(error='invalid_token'|'missing_auth') on failure — never raises HTTPException"
    - "validate_refresh(token) and validate_bearer(token) follow the same AuthResult contract"
    - "validate_refresh and validate_bearer open their DB session via session_with_rls(system_operation_context()) so the system-bypass OR clause in 0002 RLS policies (Plan 02) admits the lookup"
    - "auth/core.py imports NEITHER fastapi NOR starlette (D-17)"
    - "get_db_session SETs three GUCs (app.current_user_id, app.current_user_role, app.request_id) via set_config(name, value, false) — Landmine #5 (SET ... = $1 is illegal SQL)"
    - "get_db_session RESETs all three app.* GUCs in finally — preserves Phase 1a canonical shape"
    - "session_with_rls(ctx) is the canonical non-FastAPI alternate constructor exported from dependencies.py — used by APScheduler, CLI, AND auth/core.py (validate_refresh/validate_bearer)"
    - "PoolEvents.reset listener on engine.sync_engine RESETs all three GUCs as a fail-safe (Landmine #1)"
    - "TEST-02 5 cases pass: no GUC leak after request, user B sees empty GUC, cross-user read blocked, system context bypass, pool reset scrubs GUC"
    - "write_audit_log(session, ctx, ...) writes to audit_log without RLS interference (audit_log is NOT in RLS_TABLES)"
    - "dependencies.get_operation_context populates OperationContext.session_id from the optional 'sid' JWT claim (refresh-issued tokens carry sid)"
    - "D-20: RLS GUC integration is owned by get_db_session — set_config('app.current_user_id', ...) before yield, RESET in finally; session_with_rls(ctx) is the parallel constructor for non-FastAPI callers (APScheduler, CLI, auth/core.py)"
    - "D-30: TEST-02 RLS isolation test lives at server/app/tests/auth/test_rls_isolation.py and proves (a) the same pooled connection used by user B sees no leaked app.current_user_id and (b) cross-user reads of an RLS-enabled table return only the caller's row"
    - "D-18: auth/core.py is the transport-shared validator core; transport adapters (REST in dependencies.py, MCP HTTP in mcp/server.py) translate the AuthResult into a per-transport OperationContext"
    - "PL-06: all system-user UUID references use auth.context.SYSTEM_USER_ID (canonical constant) — never hardcode the string '00000000-0000-0000-0000-000000000001' in application code"
  artifacts:
    - path: "server/app/auth/core.py"
      provides: "validate_jwt (sid claim → AuthResult.session_id), validate_refresh, validate_bearer — pure validators returning AuthResult; DB lookups go through session_with_rls(system_operation_context())"
    - path: "server/app/auth/audit.py"
      provides: "write_audit_log helper used by routes/auth.py and routes/admin.py"
    - path: "server/app/dependencies.py"
      provides: "get_db_session (extended with GUC SET) + session_with_rls(ctx) helper + get_operation_context (sid claim → OperationContext.session_id)"
    - path: "server/app/database.py"
      provides: "PoolEvents.reset listener for fail-safe GUC scrub"
    - path: "server/app/tests/auth/test_rls_isolation.py"
      provides: "TEST-02 — 5 implemented integration tests"
  key_links:
    - from: "server/app/dependencies.py:get_db_session"
      to: "server/app/auth/context.py:OperationContext"
      via: "Depends(get_operation_context) — chained dependency"
      pattern: "ctx: OperationContext = Depends"
    - from: "server/app/auth/core.py:validate_refresh,validate_bearer"
      to: "server/app/dependencies.py:session_with_rls"
      via: "system_operation_context() → session_with_rls — RLS owner policy OR-bypass admits the lookup"
      pattern: "session_with_rls"
    - from: "server/app/database.py:_on_pool_reset"
      to: "engine.sync_engine 'reset' event"
      via: "@event.listens_for(engine.sync_engine, 'reset') decorator"
      pattern: "RESET app.current_user_id"
threat_refs: [T-1b-02, T-1b-03, T-1b-06, T-1b-07]
---

<plan_objective>
Land the auth-pipeline core: `auth/core.py` (pure transport-neutral validators returning AuthResult — no FastAPI imports; DB reads use `session_with_rls(system_operation_context())` so the system-bypass OR clause in 0002 RLS policies admits them), `auth/audit.py` (audit_log writer), the extended `dependencies.py:get_db_session` (now SETs RLS GUCs after a chained `Depends(get_operation_context)`, parses the optional `sid` JWT claim into `OperationContext.session_id`, and exports the canonical `session_with_rls(ctx)` helper), and the `database.py` PoolEvents.reset listener (Landmine #1 fail-safe). Implement the 5 headline TEST-02 RLS isolation tests.

Plan 04 task 04-03 emits the `sid` claim in `issue_access_jwt`; this plan's `validate_jwt` parses it.
</plan_objective>

<threat_model>

## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Untrusted bearer/JWT/refresh token ↔ AuthResult identity | core.py validators are the single trust gate; failures return `AuthResult(error=...)` without raising |
| Pooled connection ↔ per-user request | RLS GUC SET-on-checkout / RESET-on-checkin discipline — defense-in-depth via dependency `finally:` AND PoolEvents.reset listener |
| Auth-pipeline read path (validate_refresh / validate_bearer) ↔ pre-auth GUC state | Reads run BEFORE the caller's identity is known. The session is opened under system context so the 0002 RLS system-bypass OR clause admits the lookup — without this, refresh / bearer validation would return zero rows |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-1b-02 | S (Spoofing — JWT confusion) | server/app/auth/core.py:validate_jwt | mitigate | Delegates to `auth.tokens.decode_access_jwt` (Plan 04) which already enforces `algorithms=["HS256"]`. core.py wraps `JWTError` into `AuthResult(error="invalid_token")` — never raises HTTP exceptions (D-17). Reads optional `sid` claim into `AuthResult.session_id`. |
| T-1b-03 | I (Information Disclosure — RLS leak) | server/app/dependencies.py:get_db_session + server/app/database.py PoolEvents.reset | mitigate | Primary: `set_config('app.current_user_id', :uid, false)` on session entry, `RESET app.current_user_id` in `finally:` (preserved canonical Phase 1a shape). Fail-safe: `engine.sync_engine "reset"` event listener emits `RESET app.current_user_id/role/request_id` on every connection check-in. Verified by 5 TEST-02 tests in this plan. |
| T-1b-06 | E (Elevation — MCP token validation bypass) | server/app/auth/core.py:validate_bearer | mitigate | DB-only verify path (no in-memory cache); session opened under `session_with_rls(system_operation_context())` so 0002's system-bypass OR clause admits the lookup. Hashes the candidate via `auth.mcp_tokens.sha256_token_hash`; rejects if `revoked_at IS NOT NULL`. <5s revocation guarantee preserved. |
| T-1b-07 | E (Refresh-token replay) | server/app/auth/core.py:validate_refresh | mitigate | Plan 06's `services/sessions.rotate_refresh` performs the atomic delete-and-mint. core.py's `validate_refresh` only resolves a hash to (user_id, session_id) and reports invalid_token if missing — replay of a deleted refresh hash → `AuthResult(error="invalid_token")` → forced logout. Lookup runs under system context; the 0002 system-bypass OR is what admits the SELECT. |

</threat_model>

<read_first_global>
- server/app/dependencies.py (current Phase 1a shape — RESET in finally; extend in place)
- server/app/database.py (existing event.listens_for(sync_engine, "connect") pattern; mirror for "reset")
- server/app/auth/context.py (Plan 04 — AuthResult, OperationContext, system_operation_context)
- server/app/auth/tokens.py (Plan 04 — decode_access_jwt; Plan 04 task 04-03 also emits the optional `sid` claim)
- server/app/auth/mcp_tokens.py (Plan 04 — sha256_token_hash)
- server/app/models/{user,session,mcp_token,audit_log}.py
- .planning/phases/01b-auth-security-primitives/01b-RESEARCH.md §"Pattern 7" (lines 552-606), §"Pool reset listener" (lines 619-630), §"Landmine #5" (set_config), §"Landmine #1" (pool leak), §"Landmine #8" (graceful unset)
- .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md sections for `auth/core.py`, `auth/audit.py`, `dependencies.py (MODIFY)`, `database.py (MODIFY)`, `tests/test_rls_isolation.py`
- .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md decisions D-17, D-18, D-20, D-30
- server/app/tests/integration/test_boot.py (lines 65-114 — rollback isolation analog)
- server/app/tests/auth/test_rls_isolation.py (Wave 0 stubs)
</read_first_global>

<tasks>

<task type="auto" tdd="true">
  <id>05-01</id>
  <name>Task 1: auth/core.py — pure transport-neutral validators (with sid parsing + system-context DB reads)</name>
  <read_first>
    - .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md "server/app/auth/core.py" section
    - .planning/phases/01b-auth-security-primitives/01b-RESEARCH.md §"AuthResult dataclass" (lines 1067-1075), §"MCP SDK TokenVerifier integration" (lines 985-1005)
    - server/app/auth/tokens.py (decode_access_jwt + the `sid` claim emitted by Plan 04 task 04-03)
    - server/app/auth/mcp_tokens.py (sha256_token_hash — used by validate_bearer)
    - server/app/auth/context.py (AuthResult, OperationContext, system_operation_context — return + read shapes)
    - server/app/models/{user,session,mcp_token}.py
    - alembic/versions/0002_phase_1b_auth.py (Plan 02 — system-bypass OR clause is what admits the lookup)
  </read_first>
  <behavior>
    - `validate_jwt(token: str) -> AuthResult` — calls `decode_access_jwt`; returns AuthResult(user_id=UUID(claims["sub"]), role=claims["role"], session_id=UUID(claims["sid"]) if "sid" present); on JWTError returns AuthResult(error="invalid_token"); on empty/None token returns AuthResult(error="missing_auth").
    - `validate_refresh(token: str) -> AuthResult` — async; hashes the token, opens DB session via `session_with_rls(system_operation_context())`, looks up `sessions.token_hash`, returns AuthResult(user_id, role, session_id) if found+not-expired; otherwise AuthResult(error="invalid_token").
    - `validate_bearer(token: str) -> AuthResult` — async; hashes via `sha256_token_hash`, opens DB session via `session_with_rls(system_operation_context())`, looks up `mcp_tokens.token_hash`, returns AuthResult(user_id, role, mcp_token_id) if found+not-revoked; otherwise AuthResult(error="invalid_token").
    - All three NEVER raise HTTPException (D-17). All three return AuthResult dataclass.
    - DB lookups use `session_with_rls(system_operation_context())` (NOT a bare `async_session_factory()`) — the 0002 RLS POLICY system-bypass OR clause admits the lookup. A bare session has no GUC set → graceful-unset rule fails closed → zero rows → permanently broken refresh/bearer validation.
  </behavior>
  <action>
    Create `server/app/auth/core.py`:

    ```python
    """Transport-neutral auth validators (D-17).

    Pure: returns AuthResult dataclass. Never raises HTTP exceptions.
    Imported by every transport adapter (REST middleware, MCP HTTP token verifier,
    MCP stdio bootstrap, CLI). The transport translates AuthResult.error to the
    appropriate response shape.

    DB lookups for refresh / bearer go through `session_with_rls(system_operation_context())`
    so 0002's RLS POLICY system-bypass OR clause admits the read — refresh and
    bearer validation run BEFORE the caller's identity is known and so cannot
    use a per-user GUC.
    """
    from __future__ import annotations

    import uuid
    from datetime import datetime, timezone

    from jose import JWTError
    from sqlalchemy import select

    from app.auth.context import AuthResult, system_operation_context
    from app.auth.mcp_tokens import sha256_token_hash
    from app.auth.tokens import decode_access_jwt
    from app.dependencies import session_with_rls
    from app.models.mcp_token import McpToken
    from app.models.session import Session as SessionModel
    from app.models.user import User
    from app.settings import settings


    def validate_jwt(token: str | None) -> AuthResult:
        """Decode an HS256 access JWT and project to AuthResult.

        Reads the optional `sid` claim (refresh-issued tokens carry it) and
        populates AuthResult.session_id so downstream require_fresh_auth can
        load sessions.admin_fresh_until.
        """
        if not token:
            return AuthResult(error="missing_auth")
        try:
            claims = decode_access_jwt(token, settings.jwt_signing_key)
        except JWTError:
            return AuthResult(error="invalid_token")
        try:
            user_id = uuid.UUID(claims["sub"])
        except (KeyError, ValueError):
            return AuthResult(error="invalid_token")
        role = claims.get("role")
        if role not in ("admin", "user"):
            return AuthResult(error="invalid_token")
        session_id: uuid.UUID | None = None
        sid_claim = claims.get("sid")
        if sid_claim:
            try:
                session_id = uuid.UUID(sid_claim)
            except (ValueError, TypeError):
                return AuthResult(error="invalid_token")
        return AuthResult(user_id=user_id, role=role, session_id=session_id)


    async def validate_refresh(refresh_token: str | None) -> AuthResult:
        """Look up a refresh token by SHA-256 hash; verify not expired.

        Does NOT delete the row — that's services/sessions.rotate_refresh's job.
        Runs under system context so 0002's RLS system-bypass OR clause admits
        the SELECT (we don't yet know whose row this is).
        """
        if not refresh_token:
            return AuthResult(error="missing_auth")
        h = sha256_token_hash(refresh_token)
        async for session in session_with_rls(system_operation_context()):
            result = await session.execute(
                select(SessionModel, User)
                .join(User, User.id == SessionModel.user_id)
                .where(SessionModel.token_hash == h)
            )
            row = result.first()
            if row is None:
                return AuthResult(error="invalid_token")
            sess, user = row
            if sess.expires_at is not None and sess.expires_at < datetime.now(timezone.utc):
                return AuthResult(error="invalid_token")
            if not user.is_active:
                return AuthResult(error="invalid_token")
            return AuthResult(
                user_id=sess.user_id,
                role=user.role,
                session_id=sess.id,
            )
        return AuthResult(error="invalid_token")  # unreachable; satisfies type checker


    async def validate_bearer(bearer_token: str | None) -> AuthResult:
        """Verify an MCP bearer token by SHA-256 hash; reject if revoked.

        Does NOT update last_used_at — that's services/mcp_tokens.verify_token's
        job (in the request transaction). Plan 06.

        Runs under system context so 0002's RLS system-bypass OR clause admits
        the SELECT.
        """
        if not bearer_token:
            return AuthResult(error="missing_auth")
        h = sha256_token_hash(bearer_token)
        async for session in session_with_rls(system_operation_context()):
            result = await session.execute(
                select(McpToken, User)
                .join(User, User.id == McpToken.user_id)
                .where(McpToken.token_hash == h, McpToken.revoked_at.is_(None))
            )
            row = result.first()
            if row is None:
                return AuthResult(error="invalid_token")
            mcp, user = row
            if not user.is_active:
                return AuthResult(error="invalid_token")
            return AuthResult(
                user_id=mcp.user_id,
                role=user.role,
                mcp_token_id=mcp.id,
            )
        return AuthResult(error="invalid_token")  # unreachable; satisfies type checker
    ```
  </action>
  <acceptance_criteria>
    - `test -f server/app/auth/core.py`
    - **No FastAPI imports (D-17 invariant):** `! grep -E "^(from|import) (fastapi|starlette)" server/app/auth/core.py` returns 0
    - `grep -q "from app.auth.context import AuthResult" server/app/auth/core.py` returns 0
    - `grep -q "def validate_jwt" server/app/auth/core.py && grep -q "async def validate_refresh" server/app/auth/core.py && grep -q "async def validate_bearer" server/app/auth/core.py` returns 0
    - All three functions return AuthResult on success and AuthResult(error=...) on failure (never raise): `! grep -q "raise HTTPException" server/app/auth/core.py` returns 0
    - **sid claim parsing (BLOCKER #6 / sid threading):** `grep -qE 'session_id\s*=.*claims\.get\(.sid.\)' server/app/auth/core.py` returns 0
    - **System-context DB lookups (BLOCKER #2):** `grep -q 'session_with_rls' server/app/auth/core.py && grep -q 'system_operation_context' server/app/auth/core.py` returns 0
    - Module imports cleanly: `cd server && python -c "from app.auth.core import validate_jwt, validate_refresh, validate_bearer; from app.auth.context import AuthResult; r = validate_jwt(None); assert isinstance(r, AuthResult) and r.error == 'missing_auth'; r2 = validate_jwt('garbage'); assert r2.error == 'invalid_token'; print('ok')"` prints `ok`
    - `cd server && ruff check app/auth/core.py` exits 0
  </acceptance_criteria>
  <done>auth/core.py exposes three pure validators that return AuthResult; never raise HTTP exceptions; no FastAPI imports; validate_jwt parses the optional sid claim into AuthResult.session_id; validate_refresh / validate_bearer open their DB session under system context.</done>
  <threat_ref>T-1b-02</threat_ref>
</task>

<task type="auto">
  <id>05-02</id>
  <name>Task 2: auth/audit.py — write_audit_log helper</name>
  <read_first>
    - server/app/models/audit_log.py (column shape — action, target_kind, target_id, request_id, ip, user_agent, user_id)
    - .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md "server/app/auth/audit.py" section
    - .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md D-25, D-26 (audit events)
    - server/app/auth/context.py (OperationContext — used as input)
  </read_first>
  <action>
    Create `server/app/auth/audit.py`:

    ```python
    """Audit log writer (AUTH-06, D-25, D-26).

    audit_log is NOT in 0001's RLS_TABLES list — writes succeed regardless of
    the current_setting('app.current_user_id') GUC (Phase 6 will gate reads).
    Used by routes/auth.py (refresh rotation events), routes/admin.py
    (admin_reauth success/failure), and any future admin mutation.
    """
    from __future__ import annotations

    from typing import Any

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.auth.context import OperationContext


    async def write_audit_log(
        session: AsyncSession,
        ctx: OperationContext,
        *,
        action: str,
        target_kind: str | None = None,
        target_id: str | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Append an audit_log row.

        Caller is responsible for committing the surrounding transaction.
        details is currently ignored — audit_log doesn't have a JSONB column
        in the 0001 schema; if needed, append a JSON-serialized blob into
        target_id or wait for a Phase 6 schema extension.
        """
        await session.execute(
            text(
                "INSERT INTO audit_log "
                "(user_id, action, target_kind, target_id, request_id, ip, user_agent, created_at) "
                "VALUES (:user_id, :action, :target_kind, :target_id, :request_id, :ip, :user_agent, now())"
            ),
            {
                "user_id": str(ctx.user_id) if ctx.user_id else None,
                "action": action,
                "target_kind": target_kind,
                "target_id": target_id,
                "request_id": ctx.request_id,
                "ip": ip,
                "user_agent": user_agent,
            },
        )
    ```
  </action>
  <acceptance_criteria>
    - `test -f server/app/auth/audit.py`
    - `grep -q "async def write_audit_log" server/app/auth/audit.py` returns 0
    - **No FastAPI imports:** `! grep -E "^(from|import) (fastapi|starlette)" server/app/auth/audit.py` returns 0
    - Imports cleanly: `cd server && python -c "from app.auth.audit import write_audit_log; print('ok')"` prints `ok`
    - `cd server && ruff check app/auth/audit.py` exits 0
  </acceptance_criteria>
  <done>write_audit_log helper signed and importable; takes OperationContext + AsyncSession, no FastAPI types.</done>
</task>

<task type="auto">
  <id>05-03</id>
  <name>Task 3: Extend dependencies.py — SET 3 GUCs + canonical session_with_rls(ctx) helper + sid threading in get_operation_context</name>
  <read_first>
    - server/app/dependencies.py (current Phase 1a shape — preserve canonical RESET-in-finally)
    - .planning/phases/01b-auth-security-primitives/01b-RESEARCH.md §"Pattern 7" (lines 575-606) — direct extension
    - .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md D-20 (RLS GUC ownership), §"specifics" (session_with_rls helper)
    - .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md "server/app/dependencies.py (MODIFY)" section
    - server/app/auth/context.py (OperationContext — used in parameter type)
    - server/app/auth/tokens.py (Plan 04 task 04-03 emits the optional sid claim)
  </read_first>
  <action>
    Replace the body of `server/app/dependencies.py` with the extended shape (preserve module docstring + the canonical RESET-in-finally idiom). NEW shape:

    ```python
    """FastAPI dependencies. D-09: this module owns get_db_session + RLS GUC.

    CLAUDE.md mandates SET app.current_user_id (NOT SET LOCAL) and always RESET
    in finally. Phase 1a defensively RESET only; Phase 1b adds the SET path
    after Depends(get_operation_context) authenticates the caller.

    Landmine #5: SET ... = $1 is illegal SQL — utility statements don't accept
    bind parameters. Use SELECT set_config(name, value, is_local=false) instead,
    which IS a normal function and parameter-binds the value.

    Landmine #1: PoolEvents.reset listener in database.py is the fail-safe; this
    finally:-block is the primary scrub.

    `session_with_rls(ctx)` is the canonical non-FastAPI alternate constructor.
    It is exported and consumed by APScheduler jobs, the CLI, AND auth/core.py
    (validate_refresh / validate_bearer call it under system context). Importing
    it from dependencies.py is intentional even though dependencies.py imports
    fastapi — `session_with_rls` itself does NOT depend on FastAPI types and
    auth/core.py imports only that symbol.
    """
    from __future__ import annotations

    import uuid
    from collections.abc import AsyncIterator
    from typing import TYPE_CHECKING

    from fastapi import Depends, HTTPException, Request
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.auth.context import OperationContext
    from app.database import async_session_factory

    if TYPE_CHECKING:
        pass


    async def get_operation_context(request: Request) -> OperationContext:
        """REST adapter: extract Authorization: Bearer <jwt>, validate, build OperationContext.

        Returns 401 if missing/invalid; the route never sees an unauthenticated request.
        Trusted-proxy XFF parsing populates request.state.client_ip in Plan 07.
        Reads the optional `sid` JWT claim (emitted by Plan 04 task 04-03 issue_access_jwt)
        into OperationContext.session_id so require_fresh_auth (Plan 06) can load
        sessions.admin_fresh_until.
        """
        # Local import — auth.core depends on this module (session_with_rls), so
        # we cannot top-level import to avoid a circular import.
        from app.auth.core import validate_jwt

        auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
        token: str | None = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer "):].strip()
        result = validate_jwt(token)
        if result.error is not None or result.user_id is None:
            raise HTTPException(status_code=401, detail={
                "error": {"code": "unauthorized", "message": "valid bearer token required"}
            })
        request_id = request.headers.get("x-request-id") or "unset"
        client_ip = getattr(request.state, "client_ip", None) or (request.client.host if request.client else "")
        # session_id is populated by validate_jwt from the optional sid claim
        session_id: uuid.UUID | None = result.session_id
        return OperationContext(
            user_id=result.user_id,
            role=result.role or "user",
            transport="rest",
            remote=True,
            client_name=client_ip,
            request_id=request_id,
            session_id=session_id,
        )


    async def get_db_session(
        ctx: OperationContext = Depends(get_operation_context),
    ) -> AsyncIterator[AsyncSession]:
        """Open an async session, SET 3 GUCs, yield, RESET in finally."""
        async with async_session_factory() as session:
            try:
                # Landmine #5 — set_config(name, value, is_local=false), NOT SET ... = $1
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
                # Canonical Phase 1a defensive cleanup, extended to all 3 GUCs
                try:
                    await session.execute(text("RESET app.current_user_id"))
                    await session.execute(text("RESET app.current_user_role"))
                    await session.execute(text("RESET app.request_id"))
                except Exception:  # noqa: BLE001 — defensive cleanup only
                    pass
                await session.close()


    async def session_with_rls(ctx: OperationContext) -> AsyncIterator[AsyncSession]:
        """Non-FastAPI alternate constructor of get_db_session.

        Used by APScheduler jobs, the CLI, AND auth/core.py (validate_refresh /
        validate_bearer call this under system_operation_context() — the 0002
        RLS POLICY system-bypass OR clause is what admits those reads).

        Caller drives lifecycle:

            async for session in session_with_rls(ctx):
                # ... do work ...
        """
        async with async_session_factory() as session:
            try:
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
                    await session.execute(text("RESET app.current_user_id"))
                    await session.execute(text("RESET app.current_user_role"))
                    await session.execute(text("RESET app.request_id"))
                except Exception:  # noqa: BLE001
                    pass
                await session.close()
    ```

    DO NOT change the import site of `async_session_factory`. DO NOT remove the existing module docstring intent. The local import of `validate_jwt` inside `get_operation_context` is required to break the auth.core ↔ dependencies circular import — keep it local.
  </action>
  <acceptance_criteria>
    - `grep -q "set_config('app.current_user_id', :uid, false)" server/app/dependencies.py` returns 0 (Landmine #5)
    - `grep -q "RESET app.current_user_id" server/app/dependencies.py` returns 0 (canonical preserved)
    - `grep -q "set_config('app.current_user_role'" server/app/dependencies.py` returns 0
    - `grep -q "set_config('app.request_id'" server/app/dependencies.py` returns 0
    - `grep -q "async def get_operation_context" server/app/dependencies.py && grep -q "async def session_with_rls" server/app/dependencies.py` returns 0
    - **CI grep gate (Landmine #5):** `! grep -q 'text("SET app.current_user_id' server/app/dependencies.py` returns 0 (no illegal SET binding)
    - **sid threading (BLOCKER #6 / WARNING #6):** `grep -qE 'session_id\s*=' server/app/dependencies.py` returns 0 (get_operation_context populates OperationContext.session_id from validate_jwt result)
    - **session_with_rls export available for auth.core (BLOCKER #2):** `grep -q "async def session_with_rls(ctx: OperationContext)" server/app/dependencies.py` returns 0
    - Imports cleanly: `cd server && python -c "from app.dependencies import get_db_session, get_operation_context, session_with_rls; print('ok')"` prints `ok`
    - `cd server && ruff check app/dependencies.py` exits 0
  </acceptance_criteria>
  <done>dependencies.py extended; SET via set_config; RESET in finally for all 3 GUCs; session_with_rls helper exported; get_operation_context populates OperationContext.session_id from the optional sid claim; existing Phase 1a tests still pass.</done>
  <threat_ref>T-1b-03</threat_ref>
</task>

<task type="auto">
  <id>05-04</id>
  <name>Task 4: database.py — add PoolEvents.reset listener (Landmine #1 fail-safe)</name>
  <read_first>
    - server/app/database.py (existing event.listens_for(sync_engine, "connect") pattern — mirror)
    - .planning/phases/01b-auth-security-primitives/01b-RESEARCH.md §"Pattern 7" (PoolEvents.reset, lines 619-630), §"Landmine #1"
    - .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md "server/app/database.py (MODIFY)" section
  </read_first>
  <action>
    Edit `server/app/database.py`. Add a new `event.listens_for(engine.sync_engine, "reset")` listener directly under the existing `_register_vector_type` listener. Keep the existing listener unchanged.

    Insert AFTER the existing `_register_vector_type` decorator and function (line ~37):
    ```python


    @event.listens_for(engine.sync_engine, "reset")
    def _on_pool_reset(dbapi_conn, connection_record, reset_state):  # noqa: ARG001
        """Defense-in-depth: scrub app.* GUCs on connection check-in (Landmine #1).

        Even if get_db_session's finally:-block fails (exception, future code path
        change), this listener fires on every pool reset. Synchronous via dbapi
        cursor — runs before the connection is reused by another request.
        """
        try:
            with dbapi_conn.cursor() as cur:
                cur.execute("RESET app.current_user_id")
                cur.execute("RESET app.current_user_role")
                cur.execute("RESET app.request_id")
        except Exception:  # noqa: BLE001 — never block pool reset
            pass
    ```

    Do NOT remove or alter `engine`, `_register_vector_type`, or `async_session_factory`.
  </action>
  <acceptance_criteria>
    - `grep -q '@event.listens_for(engine.sync_engine, "reset")' server/app/database.py` returns 0
    - `grep -q "def _on_pool_reset" server/app/database.py` returns 0
    - `grep -q 'cur.execute("RESET app.current_user_id")' server/app/database.py` returns 0
    - All three RESET calls present: `grep -c "RESET app\." server/app/database.py` reports 3 or more
    - Existing connect listener preserved: `grep -q "_register_vector_type" server/app/database.py` returns 0
    - `cd server && ruff check app/database.py` exits 0
    - Phase 1a boot tests still pass: `cd server && pytest -x -q app/tests/integration/test_boot.py` exits 0
  </acceptance_criteria>
  <done>PoolEvents.reset listener registered; runs RESET on three app.* GUCs; connect listener untouched.</done>
  <threat_ref>T-1b-03</threat_ref>
</task>

<task type="auto" tdd="true">
  <id>05-05</id>
  <name>Task 5: TEST-02 implementation — test_rls_isolation.py (5 cases)</name>
  <read_first>
    - server/app/tests/integration/test_boot.py (lines 65-114 — rollback isolation analog; uses test_engine + async_sessionmaker)
    - server/app/tests/auth/test_rls_isolation.py (Wave 0 stub names — preserve them)
    - .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md D-30 (TEST-02 contract)
    - .planning/phases/01b-auth-security-primitives/01b-RESEARCH.md §"Validation Architecture" TEST-02 rows (lines 1229-1233)
    - .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md "server/app/tests/test_rls_isolation.py" section
    - server/app/dependencies.py (just-extended — get_db_session and session_with_rls)
    - server/app/auth/context.py (OperationContext, system_operation_context)
  </read_first>
  <behavior>
    - `test_no_guc_leak_after_request`: open session via `session_with_rls(ctx_a)`, exit; in a NEW session against the same engine, `SELECT current_setting('app.current_user_id', true)` returns empty.
    - `test_user_b_sees_empty_guc`: same as above but explicit two-user case using seed_user_a + seed_user_b fixtures.
    - `test_cross_user_read_blocked`: User A session inserts a `provider_keys` row; User B session SELECTs from `provider_keys` and gets 0 rows (RLS policy fires).
    - `test_system_context_bypass`: `system_operation_context()` runs `session_with_rls`; verifies `app.current_user_id = SYSTEM_USER_ID`. Smoke check the system user can write to `audit_log` (not RLS-gated).
    - `test_pool_reset_scrubs_guc`: SET a GUC manually via `await session.execute(text("SELECT set_config('app.current_user_id', 'tampered', false)"))`, then close session; checkout a new session and `SELECT current_setting('app.current_user_id', true)` returns empty (PoolEvents.reset listener scrubbed).
  </behavior>
  <action>
    Implement `server/app/tests/auth/test_rls_isolation.py`:

    ```python
    """TEST-02 / D-30 — RLS isolation across pooled connections.

    The headline test for Phase 1b. Belt-and-braces verification:
      1. dependencies.session_with_rls SET-then-RESET is the primary mechanism.
      2. database.py PoolEvents.reset listener is the fail-safe.
      3. RLS POLICY on provider_keys (alembic 0002) enforces row-level isolation.
    """
    from __future__ import annotations

    import uuid
    from collections.abc import AsyncIterator

    import pytest
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

    from app.auth.context import SYSTEM_USER_ID, OperationContext, system_operation_context
    from app.dependencies import session_with_rls

    pytestmark = [pytest.mark.auth, pytest.mark.integration]


    def _ctx_for(user_id: uuid.UUID, *, role: str = "user", request_id: str = "test-rls") -> OperationContext:
        return OperationContext(
            user_id=user_id, role=role, transport="rest", remote=True,
            client_name="test", request_id=request_id,
        )


    async def test_no_guc_leak_after_request(test_engine: AsyncEngine, seed_user_a: uuid.UUID) -> None:
        """After a session_with_rls scope exits, current_setting('app.current_user_id') is empty."""
        async for session in session_with_rls(_ctx_for(seed_user_a)):
            row = (await session.execute(text("SELECT current_setting('app.current_user_id', true)"))).first()
            assert row[0] == str(seed_user_a)
        # Open a fresh session against the SAME engine (= same pool)
        factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
        async with factory() as fresh:
            row = (await fresh.execute(text("SELECT current_setting('app.current_user_id', true)"))).first()
            # PoolEvents.reset listener AND get_db_session finally:-block both scrubbed
            assert row[0] == "" or row[0] is None


    async def test_user_b_sees_empty_guc(test_engine: AsyncEngine, seed_user_a: uuid.UUID, seed_user_b: uuid.UUID) -> None:
        """User A request, then User B opens a fresh session — must NOT inherit user A's GUC."""
        async for sess_a in session_with_rls(_ctx_for(seed_user_a)):
            await sess_a.execute(text("SELECT 1"))
        # User B: completely fresh session, no SET
        factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
        async with factory() as sess_b:
            row = (await sess_b.execute(text("SELECT current_setting('app.current_user_id', true)"))).first()
            assert row[0] in ("", None), f"GUC leaked across pool: {row[0]!r} != ''"


    async def test_cross_user_read_blocked(test_engine: AsyncEngine, seed_user_a: uuid.UUID, seed_user_b: uuid.UUID) -> None:
        """RLS POLICY: User A inserts a provider_keys row; User B sees zero rows."""
        # User A inserts
        async for sess_a in session_with_rls(_ctx_for(seed_user_a)):
            await sess_a.execute(
                text(
                    "INSERT INTO provider_keys (id, user_id, provider, encrypted_key, key_hint, created_at, updated_at) "
                    "VALUES (gen_random_uuid(), :uid, 'openai', '\\x00'::bytea, 'sk-...test', now(), now())"
                ),
                {"uid": str(seed_user_a)},
            )
            await sess_a.commit()
        # User B tries to read
        async for sess_b in session_with_rls(_ctx_for(seed_user_b)):
            rows = (await sess_b.execute(text("SELECT count(*) FROM provider_keys"))).scalar_one()
            assert rows == 0, f"RLS leak: user B saw {rows} rows from user A"
        # Cleanup as user A
        async for sess_a in session_with_rls(_ctx_for(seed_user_a)):
            await sess_a.execute(text("DELETE FROM provider_keys WHERE user_id = :uid"), {"uid": str(seed_user_a)})
            await sess_a.commit()


    async def test_system_context_bypass(test_engine: AsyncEngine) -> None:
        """system_operation_context sets app.current_user_id = SYSTEM_USER_ID; can write audit_log."""
        ctx = system_operation_context()
        async for session in session_with_rls(ctx):
            row = (await session.execute(text("SELECT current_setting('app.current_user_id', true)"))).first()
            assert row[0] == str(SYSTEM_USER_ID)
            # audit_log is NOT in RLS_TABLES — write succeeds
            await session.execute(
                text(
                    "INSERT INTO audit_log (user_id, action, request_id, created_at) "
                    "VALUES (:uid, 'system_test', :rid, now())"
                ),
                {"uid": str(SYSTEM_USER_ID), "rid": ctx.request_id},
            )
            await session.commit()
            # Cleanup
            await session.execute(
                text("DELETE FROM audit_log WHERE action = 'system_test' AND request_id = :rid"),
                {"rid": ctx.request_id},
            )
            await session.commit()


    async def test_pool_reset_scrubs_guc(test_engine: AsyncEngine) -> None:
        """Bypass session_with_rls and tamper directly: PoolEvents.reset must scrub."""
        factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
        # Tamper: set GUC outside of session_with_rls
        async with factory() as session:
            await session.execute(
                text("SELECT set_config('app.current_user_id', :uid, false)"),
                {"uid": "deadbeef-dead-beef-dead-beefdeadbeef"},
            )
            await session.commit()
        # Connection returns to pool — PoolEvents.reset listener fires.
        # Open a new session and verify GUC is empty.
        async with factory() as fresh:
            row = (await fresh.execute(text("SELECT current_setting('app.current_user_id', true)"))).first()
            assert row[0] in ("", None), (
                f"PoolEvents.reset listener did not scrub GUC: still {row[0]!r}"
            )
    ```

    Replace any remaining `pytest.skip` stubs in this file. The file is the headline TEST-02 — Plan 08 sweeps to confirm all 5 cases pass.
  </action>
  <acceptance_criteria>
    - All 5 canonical test names present and not stubbed: `for n in test_no_guc_leak_after_request test_user_b_sees_empty_guc test_cross_user_read_blocked test_system_context_bypass test_pool_reset_scrubs_guc; do grep -q "async def $n" server/app/tests/auth/test_rls_isolation.py || { echo "missing $n"; exit 1; }; done` exits 0
    - No remaining stubs: `! grep -q 'pytest.skip("Wave 0 stub' server/app/tests/auth/test_rls_isolation.py` returns 0
    - Tests pass: `cd server && pytest -x -q app/tests/auth/test_rls_isolation.py` exits 0 (5 tests pass against testcontainer)
    - Phase 1a tests still green: `cd server && pytest -x -q app/tests/integration/test_boot.py` exits 0
    - `cd server && ruff check app/tests/auth/test_rls_isolation.py` exits 0
  </acceptance_criteria>
  <done>5 TEST-02 test cases pass against pgvector testcontainer; verifies migration 0002 RLS policies + dependencies SET/RESET + database.py PoolEvents.reset.</done>
  <threat_ref>T-1b-03</threat_ref>
</task>

</tasks>

<verification>
  <command>cd server && ruff check app/auth/ app/dependencies.py app/database.py && pytest -x -q app/tests/auth/test_rls_isolation.py app/tests/integration/test_boot.py</command>
  <expected>5 RLS isolation tests pass; 7 Phase 1a boot tests still pass; ruff clean.</expected>
</verification>

<must_haves>

## Truths
- auth/core.py validators return AuthResult and never raise HTTPException (D-17 invariant verified by source grep).
- auth/core.validate_jwt parses optional `sid` claim into AuthResult.session_id (BLOCKER #6 / sid threading — origin file 04-03 emits, this file parses).
- auth/core.validate_refresh / validate_bearer open their DB session via `session_with_rls(system_operation_context())` so 0002's RLS system-bypass OR clause admits the read (BLOCKER #2 closure).
- get_db_session SETs the 3 GUCs via set_config (Landmine #5 closed) and RESETs in finally (Phase 1a canonical preserved).
- get_operation_context populates OperationContext.session_id from the validate_jwt result (sid threading destination).
- database.py PoolEvents.reset listener fires on every pool checkin (Landmine #1 fail-safe).
- session_with_rls(ctx) is the canonical non-FastAPI alternate path (consumed by Plan 06 services-from-CLI, Plan 07 APScheduler job, AND auth/core.py).
- TEST-02 5 cases pass — no GUC leak, no cross-user read.

## Artifacts
- `server/app/auth/core.py` (validate_jwt with sid + validate_refresh + validate_bearer using session_with_rls(system_operation_context()))
- `server/app/auth/audit.py` (write_audit_log)
- `server/app/dependencies.py` (extended; session_with_rls exported; get_operation_context threads sid)
- `server/app/database.py` (PoolEvents.reset listener added)
- `server/app/tests/auth/test_rls_isolation.py` (5 tests pass)

## Key Links
- `auth/core.validate_jwt` → `auth.tokens.decode_access_jwt` (Landmine #2 enforced) + parses `sid` claim emitted by Plan 04 task 04-03
- `auth/core.validate_refresh` / `validate_bearer` → `dependencies.session_with_rls(system_operation_context())` → 0002 RLS system-bypass OR clause
- `dependencies.get_db_session` → `Depends(get_operation_context)` → `auth.core.validate_jwt` (sid → session_id)
- `database.py:_on_pool_reset` ← `engine.sync_engine "reset"` event (Landmine #1)
- `auth/context.SYSTEM_USER_ID` ↔ `alembic 0002 INSERT INTO users` seed

</must_haves>

<output>
Append per-task rows to `.planning/phases/01b-auth-security-primitives/01B-VALIDATION.md`. Create `01B-05-SUMMARY.md` documenting the Landmine #1, #2, #5 closures, the BLOCKER #2 system-context lookup pattern, the BLOCKER #6 sid claim parsing, and TEST-02 5-case pass.
</output>
</output>
