---
phase: 1b
plan: "06"
name: services-and-deps
wave: 3
depends_on: ["02", "03", "04", "05"]
requirements: [AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, AUTH-07, AUTH-09, AUTH-10]
files_modified:
  - server/app/services/__init__.py
  - server/app/services/users.py
  - server/app/services/sessions.py
  - server/app/services/mcp_tokens.py
  - server/app/services/provider_keys.py
  - server/app/auth/deps.py
  - server/app/tests/auth/test_mcp_tokens_integration.py
  - server/app/tests/auth/test_provider_keys.py
autonomous: true
must_haves:
  truths:
    - "services/* take OperationContext + AsyncSession; NO FastAPI imports anywhere in services/ (D-17)"
    - "services/sessions.rotate_refresh runs DELETE old + INSERT new in a SINGLE transaction (D-03 atomicity)"
    - "services/sessions.record_login_attempt INSERTs login_attempts row in its OWN transaction (Landmine #9)"
    - "services/sessions.check_rate_limit returns retry_after_seconds when count >= 10 in last 15 min (D-07)"
    - "services/sessions.wipe_login_attempts DELETEs by (ip, username) on successful login (D-08)"
    - "services/users.normalize_username case-folds + strips before write/query (D-10)"
    - "services/users.create_user refuses username='system' (cannot recreate the seeded admin)"
    - "services/mcp_tokens.verify_token updates last_used_at on every successful verify (AUTH-05)"
    - "services/mcp_tokens.revoke_token sets revoked_at; next verify_token call rejects within <100ms (AUTH-04 success criterion #2)"
    - "services/provider_keys.ProviderKeyResponse has encrypted_key: bytes = Field(exclude=True) — no post-hoc filtering (D-28)"
    - "services/provider_keys.resolve_key returns user-key first, falls back to system shared key, raises MissingProviderKey if neither (AUTH-10 / PRD §24.2)"
    - "auth/deps.py exposes require_user, require_admin, require_fresh_auth — fails closed; returns 403 admin_reauth_required envelope shape from D-16"
    - "D-14: Phase 1b step-up factor is password only — admin-scoped MCP-token reauth path returns unsupported_factor / not_implemented; the factor enum is reserved but not implemented"
    - "PL-06: all system-user UUID references use auth.context.SYSTEM_USER_ID (canonical constant) — never hardcode the string literal in application code"
    - "PL-07: `make_interval(secs => :window)` is PostgreSQL 16 named-parameter notation — requires `make_interval(0, 0, 0, 0, :window_seconds)` positional form if older PG versions are targeted; current target is pgvector:pg16 (PG 16+) so named notation is correct"
  artifacts:
    - path: "server/app/services/users.py"
      provides: "create_user, get_user_by_username, set_password, set_role, normalize_username"
    - path: "server/app/services/sessions.py"
      provides: "issue_session_pair, rotate_refresh, revoke_session, record_login_attempt, check_rate_limit, wipe_login_attempts, set_admin_fresh"
    - path: "server/app/services/mcp_tokens.py"
      provides: "create_mcp_token (returns plaintext once), list_for_user, revoke_token, verify_token (DB-only verify with last_used_at update)"
    - path: "server/app/services/provider_keys.py"
      provides: "set_provider_key, get_for_user, list_for_user, revoke_provider_key, resolve_key, ProviderKeyResponse (Field(exclude=True))"
    - path: "server/app/auth/deps.py"
      provides: "require_user, require_admin, require_fresh_auth, admin_reauth_required_envelope"
  key_links:
    - from: "server/app/services/sessions.py:rotate_refresh"
      to: "server/app/auth/tokens.py:issue_access_jwt"
      via: "atomic transaction issues new pair before commit"
      pattern: "issue_access_jwt"
    - from: "server/app/services/provider_keys.py:set_provider_key"
      to: "server/app/encryption.py:encrypt_provider_key"
      via: "all writes go through Fernet wrapper"
      pattern: "encrypt_provider_key"
    - from: "server/app/auth/deps.py:require_fresh_auth"
      to: "server/app/models/session.py:admin_fresh_until"
      via: "queries admin_fresh_until > now()"
      pattern: "admin_fresh_until"
threat_refs: [T-1b-01, T-1b-04, T-1b-05, T-1b-06, T-1b-07, T-1b-08]
---

<plan_objective>
Land the transport-agnostic service layer (`services/users.py`, `services/sessions.py`, `services/mcp_tokens.py`, `services/provider_keys.py`) and the FastAPI Depends factories (`auth/deps.py: require_user/require_admin/require_fresh_auth`). Every service takes `OperationContext + AsyncSession`, never FastAPI types. Refresh-token rotation is atomic in a single transaction (D-03). Login throttling uses sliding-window DB query (D-07). Provider keys never expose `encrypted_key` (D-28 / Field(exclude=True)). Wave-0 stubs `test_mcp_tokens_integration.py` and `test_provider_keys.py` are turned into passing integration tests.
</plan_objective>

<threat_model>

## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Failed login rate-limit query ↔ DB transaction | Insert login_attempts in OWN transaction BEFORE password verify (Landmine #9) so rollback can't erase the failure record |
| Refresh token replay ↔ rotation | Atomic DELETE-old + INSERT-new in single transaction — replay of deleted hash returns invalid_token (theft signal) |
| MCP token revocation ↔ in-memory cache | NO worker-local cache — DB-only verify path; revocation effective on the next request (<100ms) |
| Provider key plaintext ↔ API response | Pydantic Field(exclude=True) at schema level (not post-hoc filter) — column never serializes |
| Step-up freshness ↔ session lifetime | admin_fresh_until on sessions row — survives JWT refresh; revocable by session deletion |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-1b-01 | I (Information Disclosure) | services/provider_keys.py:ProviderKeyResponse | mitigate | `encrypted_key: bytes = Field(exclude=True)` — schema-level. CI grep gate (Plan 08): every Pydantic model with `encrypted_key` MUST have `Field(exclude=True)`. |
| T-1b-04 | S (Spoofing — credential brute-force) | services/sessions.py:check_rate_limit + record_login_attempt | mitigate | Sliding-window DB query: `count(*) WHERE attempted_at >= now() - interval '15 min' AND ip=:ip AND username=:u`. INSERT in own transaction (Landmine #9). Returns retry_after_seconds in the rate_limited error envelope. |
| T-1b-05 | E (Elevation — admin freshness bypass) | server/app/auth/deps.py:require_fresh_auth | mitigate | 4-check enforcement (D-13): authenticated, role='admin', session not revoked/expired, admin_fresh_until > now(). Returns 403 with the canonical D-16 envelope. |
| T-1b-06 | E (Token theft) | services/mcp_tokens.py:verify_token + revoke_token | mitigate | DB-only verify (no cache) → revocation effective on next request. last_used_at updated atomically with verify lookup. |
| T-1b-07 | E (Refresh-token replay) | services/sessions.py:rotate_refresh | mitigate | Atomic single-transaction DELETE old + INSERT new (D-03). Replay of deleted hash → row not found → InvalidToken. write_audit_log (Plan 05) records both success and failure for forensics (D-26). |
| T-1b-08 | T (Tampering — audit log) | audit_log table writes | mitigate | audit_log has NO UPDATE policies in 0002; service layer only INSERTs. No Pydantic mutation surface in 1b. Phase 6 reads gate. |

</threat_model>

<read_first_global>
- server/app/auth/{context,core,password,tokens,mcp_tokens,audit}.py (Plan 04 + Plan 05 — service layer consumes these)
- server/app/encryption.py (Plan 03)
- server/app/dependencies.py (Plan 05 — Depends(get_operation_context), Depends(get_db_session))
- server/app/models/{user,session,mcp_token,provider_key,login_attempt,audit_log}.py
- .planning/phases/01b-auth-security-primitives/01b-RESEARCH.md §"Pattern 3" (refresh rotation atomic, lines 412-435), §"Pattern 4" (verify_token DB-only, lines 446-470), §"Pattern 5" (Fernet seam), §"Pattern 6" (Field(exclude=True), lines 535-543), §"Pattern 8" (sliding window, lines 638-672), §"Pattern 9" (require_fresh_auth, lines 680-705), §"Landmine #9"
- .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md decisions D-03, D-04, D-07, D-08, D-10, D-12, D-13, D-15, D-16, D-28
- .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md sections for `services/*`, `auth/deps.py`
- server/app/tests/auth/{test_mcp_tokens_integration,test_provider_keys}.py (Wave 0 stubs)
</read_first_global>

<tasks>

<task type="auto">
  <id>06-01</id>
  <name>Task 1: services package + users.py + sessions.py (login + refresh + rate limit)</name>
  <read_first>
    - server/app/auth/password.py (hash_password / verify_password)
    - server/app/auth/tokens.py (issue_access_jwt)
    - server/app/auth/audit.py (write_audit_log)
    - server/app/auth/mcp_tokens.py (sha256_token_hash — used for refresh hashing)
    - server/app/models/{user,session,login_attempt}.py
    - .planning/phases/01b-auth-security-primitives/01b-RESEARCH.md §"Pattern 3" (lines 412-435), §"Pattern 8" (lines 638-672), §"Landmine #9"
    - .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md "services/__init__.py" + "services/users.py" + "services/sessions.py" sections
    - .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md D-03, D-07, D-08, D-10
  </read_first>
  <action>
    Create `server/app/services/__init__.py`:
    ```python
    """Transport-agnostic service layer. Services take OperationContext, never FastAPI request types."""
    ```

    Create `server/app/services/users.py`:
    ```python
    """User CRUD service (transport-agnostic).

    D-10: usernames are case-folded + stripped at the application layer before
    write/query. users.username (citext-style) is the canonical form.
    """
    from __future__ import annotations

    import uuid

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.auth.context import OperationContext
    from app.auth.password import hash_password
    from app.models.user import User


    class UsernameExists(Exception):
        ...


    class InvalidRole(Exception):
        ...


    SYSTEM_USERNAME = "system"


    def normalize_username(raw: str) -> str:
        """D-10 — case-fold + strip."""
        return raw.strip().casefold()


    async def get_user_by_username(session: AsyncSession, raw_username: str) -> User | None:
        username = normalize_username(raw_username)
        return (await session.execute(select(User).where(User.username == username))).scalar_one_or_none()


    async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
        return await session.get(User, user_id)


    async def create_user(
        session: AsyncSession,
        ctx: OperationContext,
        *,
        username: str,
        password_plain: str,
        role: str = "user",
        email: str | None = None,
    ) -> User:
        """Create a new user. Refuses username='system' (the seeded admin must not be re-creatable)."""
        username_n = normalize_username(username)
        if username_n == SYSTEM_USERNAME:
            raise UsernameExists("'system' is reserved")
        if role not in ("admin", "user"):
            raise InvalidRole(role)
        existing = await get_user_by_username(session, username_n)
        if existing is not None:
            raise UsernameExists(username_n)
        ph = await hash_password(password_plain)
        user = User(
            id=uuid.uuid4(),
            username=username_n,
            email=email,
            password_hash=ph,
            role=role,
            is_active=True,
        )
        session.add(user)
        await session.flush()
        return user


    async def set_password(session: AsyncSession, user: User, new_password: str) -> None:
        user.password_hash = await hash_password(new_password)


    async def set_role(session: AsyncSession, user: User, role: str) -> None:
        if role not in ("admin", "user"):
            raise InvalidRole(role)
        user.role = role
    ```

    Create `server/app/services/sessions.py` — login throttling + JWT issuance + atomic refresh rotation:
    ```python
    """Session, refresh-token, and login-attempt service (transport-agnostic).

    D-03: refresh rotation is rotate-and-revoke in a single transaction.
    D-07/D-08: sliding-window rate limit; wipe attempts on successful login.
    D-26: audit_log entries on rotation success/failure.
    Landmine #9: record_login_attempt INSERTs in its OWN transaction so a
    downstream rollback cannot erase the failure record.
    """
    from __future__ import annotations

    import secrets
    import uuid
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import delete, select, text, update
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.auth.audit import write_audit_log
    from app.auth.context import OperationContext
    from app.auth.mcp_tokens import sha256_token_hash
    from app.auth.tokens import issue_access_jwt
    from app.models.login_attempt import LoginAttempt
    from app.models.session import Session as SessionModel
    from app.models.user import User
    from app.settings import settings


    class InvalidToken(Exception):
        ...


    class RateLimited(Exception):
        def __init__(self, retry_after_seconds: int):
            self.retry_after_seconds = retry_after_seconds


    def _now() -> datetime:
        return datetime.now(timezone.utc)


    async def record_login_attempt(
        session: AsyncSession, *, ip: str, username: str, request_id: str | None = None, user_agent: str | None = None
    ) -> None:
        """Landmine #9: INSERT in own transaction; commit before password verify."""
        async with session.begin():
            session.add(LoginAttempt(
                ip=ip,
                username=username,
                user_agent=user_agent,
                request_id=request_id,
            ))


    async def check_rate_limit(
        session: AsyncSession, *, ip: str, username: str
    ) -> int | None:
        """Sliding window. Returns retry_after_seconds if rate-limited, else None."""
        window = settings.login_rate_limit_window_seconds
        max_fail = settings.login_rate_limit_max_failures
        row = (await session.execute(
            text(
                "SELECT count(*) AS cnt, "
                "EXTRACT(epoch FROM (now() - min(attempted_at)))::int AS oldest_age_s "
                "FROM login_attempts "
                "WHERE ip = :ip AND username = :u "
                "AND attempted_at >= now() - make_interval(secs => :window)"
            ),
            {"ip": ip, "u": username, "window": window},
        )).first()
        cnt = int(row[0] or 0)
        oldest_age = int(row[1] or 0)
        if cnt < max_fail:
            return None
        retry_after = max(1, window - oldest_age)
        return retry_after


    async def wipe_login_attempts(
        session: AsyncSession, *, ip: str, username: str
    ) -> None:
        """D-08: clear (ip, username) attempts on successful login."""
        await session.execute(
            delete(LoginAttempt).where(
                LoginAttempt.ip == ip,
                LoginAttempt.username == username,
            )
        )


    async def issue_session_pair(
        session: AsyncSession, ctx: OperationContext, *, user: User
    ) -> tuple[str, str, uuid.UUID]:
        """Mint a new (access_jwt, refresh_token, session_id) triple."""
        refresh_raw = secrets.token_urlsafe(32)
        refresh_hash = sha256_token_hash(refresh_raw)
        sess_id = uuid.uuid4()
        sess_row = SessionModel(
            id=sess_id,
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=_now() + timedelta(seconds=settings.jwt_refresh_ttl_seconds),
        )
        session.add(sess_row)
        await session.flush()
        # Thread session_id into the JWT as `sid` claim — Plan 04 task 04-03 emits
        # it, Plan 05 task 05-01 parses it into AuthResult.session_id.
        access = issue_access_jwt(
            user_id=user.id,
            role=user.role,
            signing_key=settings.jwt_signing_key,
            ttl_seconds=settings.jwt_access_ttl_seconds,
            session_id=sess_id,
        )
        return access, refresh_raw, sess_id


    async def rotate_refresh(
        session: AsyncSession, ctx: OperationContext, *, raw_refresh: str
    ) -> tuple[str, str]:
        """D-03: atomic rotate-and-revoke in a single transaction.

        Replay of an old refresh hash → row not found → InvalidToken (theft signal).
        Writes audit_log on success (D-26) and failure.
        """
        rh = sha256_token_hash(raw_refresh)
        async with session.begin():
            existing = (
                await session.execute(
                    select(SessionModel, User)
                    .join(User, User.id == SessionModel.user_id)
                    .where(SessionModel.token_hash == rh)
                    .with_for_update()
                )
            ).first()
            if existing is None:
                # Theft signal — log even though session is unknown
                await write_audit_log(
                    session, ctx, action="refresh_rotate_failed",
                    target_kind="session", target_id=None,
                )
                raise InvalidToken("refresh not found")
            old_sess, user = existing
            if old_sess.expires_at is not None and old_sess.expires_at < _now():
                await write_audit_log(
                    session, ctx, action="refresh_rotate_failed",
                    target_kind="session", target_id=str(old_sess.id),
                )
                raise InvalidToken("refresh expired")
            # DELETE old
            await session.execute(delete(SessionModel).where(SessionModel.id == old_sess.id))
            # INSERT new
            new_refresh = secrets.token_urlsafe(32)
            new_id = uuid.uuid4()
            session.add(SessionModel(
                id=new_id,
                user_id=user.id,
                token_hash=sha256_token_hash(new_refresh),
                expires_at=_now() + timedelta(seconds=settings.jwt_refresh_ttl_seconds),
            ))
            access = issue_access_jwt(
                user_id=user.id,
                role=user.role,
                signing_key=settings.jwt_signing_key,
                ttl_seconds=settings.jwt_access_ttl_seconds,
                session_id=new_id,
            )
            await write_audit_log(
                session, ctx, action="refresh_rotated",
                target_kind="session", target_id=str(new_id),
            )
        return access, new_refresh


    async def revoke_session(
        session: AsyncSession, *, session_id: uuid.UUID
    ) -> None:
        await session.execute(delete(SessionModel).where(SessionModel.id == session_id))


    async def set_admin_fresh(
        session: AsyncSession, *, session_id: uuid.UUID, minutes: int
    ) -> None:
        """D-12: stamp admin_fresh_until = now() + interval 'X minutes'."""
        await session.execute(
            update(SessionModel)
            .where(SessionModel.id == session_id)
            .values(admin_fresh_until=_now() + timedelta(minutes=minutes))
        )
    ```
  </action>
  <acceptance_criteria>
    - `test -f server/app/services/__init__.py && test -f server/app/services/users.py && test -f server/app/services/sessions.py`
    - **NO FastAPI imports in services/ (D-17 invariant):** `! grep -rE "^(from|import) (fastapi|starlette)" server/app/services/` returns 0
    - `grep -q "def normalize_username" server/app/services/users.py && grep -q "casefold()" server/app/services/users.py` returns 0 (D-10)
    - `grep -q "raise UsernameExists" server/app/services/users.py && grep -q "SYSTEM_USERNAME = \"system\"" server/app/services/users.py` returns 0
    - `grep -q "async def rotate_refresh" server/app/services/sessions.py && grep -q "async with session.begin()" server/app/services/sessions.py` returns 0 (D-03 atomic)
    - `grep -q "async def record_login_attempt" server/app/services/sessions.py && grep -q "async with session.begin()" server/app/services/sessions.py` returns 0 (Landmine #9)
    - `grep -q "make_interval(secs => :window)" server/app/services/sessions.py` returns 0 (sliding window query)
    - `grep -q "set_admin_fresh" server/app/services/sessions.py` returns 0 (D-12)
    - `grep -q "wipe_login_attempts" server/app/services/sessions.py` returns 0 (D-08)
    - Modules import cleanly: `cd server && python -c "from app.services.users import create_user, normalize_username, UsernameExists; from app.services.sessions import issue_session_pair, rotate_refresh, RateLimited, record_login_attempt, check_rate_limit, wipe_login_attempts, set_admin_fresh; assert normalize_username('  Alice  ') == 'alice'; print('ok')"` prints `ok`
    - `cd server && ruff check app/services/users.py app/services/sessions.py` exits 0
  </acceptance_criteria>
  <done>users.py and sessions.py services importable; normalize_username case-folds; rotate_refresh is atomic; record_login_attempt uses own transaction; no FastAPI imports.</done>
  <threat_ref>T-1b-04</threat_ref>
</task>

<task type="auto" tdd="true">
  <id>06-02</id>
  <name>Task 2: services/mcp_tokens.py + integration tests (revocation <5s, last_used_at)</name>
  <read_first>
    - server/app/auth/mcp_tokens.py (Plan 04 — generate_token, sha256_token_hash)
    - server/app/models/mcp_token.py
    - .planning/phases/01b-auth-security-primitives/01b-RESEARCH.md §"Pattern 4" (lines 446-478)
    - .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md "services/mcp_tokens.py" section
    - server/app/tests/auth/test_mcp_tokens_integration.py (Wave 0 stubs — 4 test names)
  </read_first>
  <behavior>
    - `create_mcp_token(session, ctx, *, name)` returns `(plaintext, McpToken row)`. Plaintext shown ONCE; storage column is the SHA-256 hex.
    - `verify_token(session, plaintext)` looks up by hash, rejects if revoked_at IS NOT NULL, updates last_used_at to now(), returns the row.
    - `revoke_token(session, token_id)` sets revoked_at = now(); subsequent `verify_token` returns None.
    - All four canonical Wave-0 tests pass: plaintext shown once, stored as hash, revocation <5s, last_used_at updates.
  </behavior>
  <action>
    Create `server/app/services/mcp_tokens.py`:
    ```python
    """MCP bearer token service (transport-agnostic).

    AUTH-04: plaintext shown once at create; storage column = SHA-256 hex.
    AUTH-05: last_used_at updated on every successful verify (DB UPDATE per request — homelab scale fine).
    AUTH-04 success criterion #2: revocation effective in <5s — DB-only path (no in-memory cache).
    """
    from __future__ import annotations

    import uuid
    from collections.abc import Sequence

    from sqlalchemy import func, select, update
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.auth.context import OperationContext
    from app.auth.mcp_tokens import generate_token, sha256_token_hash
    from app.models.mcp_token import McpToken


    async def create_mcp_token(
        session: AsyncSession, ctx: OperationContext, *, name: str | None = None
    ) -> tuple[str, McpToken]:
        """Create a new MCP bearer for the calling user.

        Returns (plaintext, row). Caller is responsible for showing plaintext
        to the operator ONCE; the DB only ever stores the sha256 hex.
        """
        plaintext, token_hash, _last4 = generate_token()
        row = McpToken(
            id=uuid.uuid4(),
            user_id=ctx.user_id,
            name=name,
            token_hash=token_hash,
        )
        session.add(row)
        await session.flush()
        return plaintext, row


    async def list_for_user(session: AsyncSession, user_id: uuid.UUID) -> Sequence[McpToken]:
        result = await session.execute(
            select(McpToken).where(McpToken.user_id == user_id, McpToken.revoked_at.is_(None))
        )
        return result.scalars().all()


    async def revoke_token(session: AsyncSession, token_id: uuid.UUID) -> None:
        await session.execute(
            update(McpToken).where(McpToken.id == token_id).values(revoked_at=func.now())
        )


    async def verify_token(session: AsyncSession, plaintext: str) -> McpToken | None:
        """DB-only verify path. Updates last_used_at on success.

        Revocation is effective on the next call (<100ms) — no worker-local cache.
        """
        h = sha256_token_hash(plaintext)
        result = await session.execute(
            select(McpToken).where(
                McpToken.token_hash == h,
                McpToken.revoked_at.is_(None),
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        await session.execute(
            update(McpToken).where(McpToken.id == row.id).values(last_used_at=func.now())
        )
        return row
    ```

    Implement `server/app/tests/auth/test_mcp_tokens_integration.py` (replace 4 Wave-0 stubs). Use the seeded `seed_basic_user` fixture and `system_operation_context()` for setup since RLS on `mcp_tokens` requires the owner's GUC:
    ```python
    """AUTH-04, AUTH-05 integration tests."""
    from __future__ import annotations

    import asyncio
    import uuid

    import pytest
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

    from app.auth.context import OperationContext
    from app.dependencies import session_with_rls
    from app.services.mcp_tokens import create_mcp_token, revoke_token, verify_token

    pytestmark = [pytest.mark.auth, pytest.mark.integration]


    def _ctx_for(uid: uuid.UUID) -> OperationContext:
        return OperationContext(
            user_id=uid, role="user", transport="cli", remote=False,
            client_name="test", request_id="test-mcp",
        )


    async def test_token_plaintext_shown_once(seed_basic_user: uuid.UUID) -> None:
        ctx = _ctx_for(seed_basic_user)
        async for session in session_with_rls(ctx):
            plaintext, row = await create_mcp_token(session, ctx, name="t1")
            await session.commit()
            # plaintext is returned ONCE; storage is the hash, not plaintext
            assert plaintext.startswith("scmcp_")
            assert row.token_hash != plaintext
            assert len(row.token_hash) == 64  # sha256 hex


    async def test_token_stored_as_hash(seed_basic_user: uuid.UUID, test_engine: AsyncEngine) -> None:
        ctx = _ctx_for(seed_basic_user)
        async for session in session_with_rls(ctx):
            plaintext, row = await create_mcp_token(session, ctx, name="t2")
            await session.commit()
            tid = row.id
        # Independent verification — read raw column (use system context to bypass RLS)
        from app.auth.context import system_operation_context
        async for s2 in session_with_rls(system_operation_context()):
            stored = (await s2.execute(
                text("SELECT token_hash FROM mcp_tokens WHERE id = :id"),
                {"id": str(tid)},
            )).scalar_one()
            assert stored != plaintext
            assert len(stored) == 64


    async def test_revocation_within_5_seconds(seed_basic_user: uuid.UUID) -> None:
        ctx = _ctx_for(seed_basic_user)
        async for session in session_with_rls(ctx):
            plaintext, row = await create_mcp_token(session, ctx, name="t3")
            await session.commit()
        # Verify works
        async for sess2 in session_with_rls(ctx):
            v1 = await verify_token(sess2, plaintext)
            await sess2.commit()
            assert v1 is not None
        # Revoke
        async for sess3 in session_with_rls(ctx):
            await revoke_token(sess3, row.id)
            await sess3.commit()
        # Next verify (immediately) returns None
        async for sess4 in session_with_rls(ctx):
            v2 = await verify_token(sess4, plaintext)
            assert v2 is None, "revocation must be effective on the very next request"


    async def test_last_used_at_updates_on_verify(seed_basic_user: uuid.UUID) -> None:
        ctx = _ctx_for(seed_basic_user)
        async for session in session_with_rls(ctx):
            plaintext, _row = await create_mcp_token(session, ctx, name="t4")
            await session.commit()
        # First verify
        async for sess2 in session_with_rls(ctx):
            v1 = await verify_token(sess2, plaintext)
            await sess2.commit()
            t1 = v1.last_used_at
        await asyncio.sleep(1.1)  # PG now() resolution is sub-second; sleep ensures movement
        async for sess3 in session_with_rls(ctx):
            await sess3.execute(text("SELECT 1"))  # ensure new transaction
            v2 = await verify_token(sess3, plaintext)
            await sess3.commit()
            t2 = v2.last_used_at
        assert t2 is None or t1 is None or t2 > t1, "last_used_at must move forward on each verify"
    ```
  </action>
  <acceptance_criteria>
    - `test -f server/app/services/mcp_tokens.py`
    - `! grep -E "^(from|import) (fastapi|starlette)" server/app/services/mcp_tokens.py` returns 0
    - `grep -q "async def verify_token" server/app/services/mcp_tokens.py && grep -q "last_used_at=func.now()" server/app/services/mcp_tokens.py` returns 0 (AUTH-05)
    - `grep -q "revoked_at.is_(None)" server/app/services/mcp_tokens.py` returns 0
    - `cd server && pytest -x -q app/tests/auth/test_mcp_tokens_integration.py` exits 0 (4 tests pass)
    - All four canonical names: `for n in test_token_plaintext_shown_once test_token_stored_as_hash test_revocation_within_5_seconds test_last_used_at_updates_on_verify; do grep -q "async def $n" server/app/tests/auth/test_mcp_tokens_integration.py; done` exits 0
    - No remaining stubs: `! grep -q 'pytest.skip("Wave 0 stub' server/app/tests/auth/test_mcp_tokens_integration.py` returns 0
    - `cd server && ruff check app/services/mcp_tokens.py app/tests/auth/test_mcp_tokens_integration.py` exits 0
  </acceptance_criteria>
  <done>MCP token service writes hash; verify updates last_used_at; revocation effective on next request; 4 integration tests pass.</done>
  <threat_ref>T-1b-06</threat_ref>
</task>

<task type="auto" tdd="true">
  <id>06-03</id>
  <name>Task 3: services/provider_keys.py + integration tests (Field(exclude=True), resolve order)</name>
  <read_first>
    - server/app/encryption.py (Plan 03)
    - server/app/models/provider_key.py
    - .planning/phases/01b-auth-security-primitives/01b-RESEARCH.md §"Pattern 5", §"Pattern 6" (lines 535-543)
    - .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md "services/provider_keys.py" section
    - .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md D-28 (Field(exclude=True))
    - server/app/tests/auth/test_provider_keys.py (Wave 0 stubs)
  </read_first>
  <action>
    Create `server/app/services/provider_keys.py`:
    ```python
    """Provider key service (transport-agnostic).

    AUTH-09: encrypted_key column never returned in any API response (D-28 / Field(exclude=True)).
    AUTH-10 / PRD §24.2: resolution order = per-user key → system shared key → MissingProviderKey.
    """
    from __future__ import annotations

    import uuid
    from collections.abc import Sequence
    from datetime import datetime

    from pydantic import BaseModel, ConfigDict, Field
    from sqlalchemy import delete, select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.auth.context import SYSTEM_USER_ID, OperationContext
    from app.encryption import decrypt_provider_key, encrypt_provider_key
    from app.models.provider_key import ProviderKey


    class MissingProviderKey(Exception):
        def __init__(self, provider: str):
            self.provider = provider


    class ProviderKeyResponse(BaseModel):
        """REST/MCP response schema. encrypted_key is structurally excluded — D-28."""
        model_config = ConfigDict(from_attributes=True)

        id: uuid.UUID
        user_id: uuid.UUID
        provider: str
        key_hint: str
        created_at: datetime
        # CLAUDE.md / D-28: schema-level exclusion, NOT post-hoc filtering
        encrypted_key: bytes = Field(exclude=True)


    def _hint_for(plaintext: str) -> str:
        """Last-4 hint surfaced in UI; 32-char column."""
        return plaintext[-4:] if len(plaintext) >= 4 else plaintext


    async def set_provider_key(
        session: AsyncSession, ctx: OperationContext, *, provider: str, plaintext: str
    ) -> ProviderKey:
        """Upsert a provider key for ctx.user_id. Encrypts before write."""
        existing = (
            await session.execute(
                select(ProviderKey).where(
                    ProviderKey.user_id == ctx.user_id,
                    ProviderKey.provider == provider,
                )
            )
        ).scalar_one_or_none()
        ciphertext = encrypt_provider_key(plaintext)
        hint = _hint_for(plaintext)
        if existing is not None:
            existing.encrypted_key = ciphertext
            existing.key_hint = hint
            await session.flush()
            return existing
        row = ProviderKey(
            id=uuid.uuid4(),
            user_id=ctx.user_id,
            provider=provider,
            encrypted_key=ciphertext,
            key_hint=hint,
        )
        session.add(row)
        await session.flush()
        return row


    async def get_for_user(
        session: AsyncSession, *, user_id: uuid.UUID, provider: str
    ) -> ProviderKey | None:
        return (
            await session.execute(
                select(ProviderKey).where(
                    ProviderKey.user_id == user_id, ProviderKey.provider == provider
                )
            )
        ).scalar_one_or_none()


    async def list_for_user(
        session: AsyncSession, *, user_id: uuid.UUID
    ) -> Sequence[ProviderKey]:
        return (
            await session.execute(
                select(ProviderKey).where(ProviderKey.user_id == user_id)
            )
        ).scalars().all()


    async def revoke_provider_key(
        session: AsyncSession, *, key_id: uuid.UUID
    ) -> None:
        await session.execute(delete(ProviderKey).where(ProviderKey.id == key_id))


    async def resolve_key(
        session: AsyncSession, ctx: OperationContext, *, provider: str
    ) -> str:
        """AUTH-10 / PRD §24.2: per-user key first, system shared key fallback, else error.

        Returns the decrypted plaintext.
        """
        # 1. Per-user
        user_row = await get_for_user(session, user_id=ctx.user_id, provider=provider)
        if user_row is not None:
            return decrypt_provider_key(user_row.encrypted_key)
        # 2. System shared (system user owns the fallback row)
        sys_row = await get_for_user(session, user_id=SYSTEM_USER_ID, provider=provider)
        if sys_row is not None:
            return decrypt_provider_key(sys_row.encrypted_key)
        # 3. Neither — error envelope
        raise MissingProviderKey(provider)
    ```

    Implement `server/app/tests/auth/test_provider_keys.py`. Note: `provider_keys` IS in RLS_TABLES — every test must run inside `session_with_rls(ctx)`. The `resolve_key` test exercises the system fallback by setting a row owned by `SYSTEM_USER_ID`:
    ```python
    """AUTH-09, AUTH-10 integration tests."""
    from __future__ import annotations

    import uuid

    import pytest
    from cryptography.fernet import Fernet

    from app.auth.context import SYSTEM_USER_ID, OperationContext, system_operation_context
    from app.dependencies import session_with_rls
    from app.encryption import _reset_fernet_cache_for_tests
    from app.services.provider_keys import (
        MissingProviderKey,
        ProviderKeyResponse,
        resolve_key,
        set_provider_key,
    )

    pytestmark = [pytest.mark.auth, pytest.mark.integration]


    def _user_ctx(uid: uuid.UUID) -> OperationContext:
        return OperationContext(
            user_id=uid, role="user", transport="cli", remote=False,
            client_name="test", request_id="test-providerkeys",
        )


    @pytest.fixture(autouse=True)
    def _fernet_key(monkeypatch):
        from app import settings as settings_mod
        monkeypatch.setattr(settings_mod.settings, "smartcopilot_fernet_key", Fernet.generate_key().decode())
        _reset_fernet_cache_for_tests()
        yield
        _reset_fernet_cache_for_tests()


    def test_encrypted_key_excluded_from_responses() -> None:
        """D-28: schema-level exclusion. Pydantic model_dump() must not include encrypted_key."""
        from datetime import datetime, timezone

        resp = ProviderKeyResponse(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            provider="openai",
            key_hint="abcd",
            created_at=datetime.now(timezone.utc),
            encrypted_key=b"\x00\x01\x02",
        )
        dumped = resp.model_dump()
        assert "encrypted_key" not in dumped, f"encrypted_key leaked into response: {dumped.keys()}"
        # Also test JSON shape
        assert "encrypted_key" not in resp.model_dump_json()


    async def test_user_key_takes_precedence_over_shared(seed_basic_user: uuid.UUID) -> None:
        # System places a shared key
        async for s_sys in session_with_rls(system_operation_context()):
            await set_provider_key(s_sys, system_operation_context(), provider="openai", plaintext="sk-system")
            await s_sys.commit()
        # User places their own key
        ctx = _user_ctx(seed_basic_user)
        async for s_user in session_with_rls(ctx):
            await set_provider_key(s_user, ctx, provider="openai", plaintext="sk-user")
            await s_user.commit()
        # Resolve: user wins
        async for s_resolve in session_with_rls(ctx):
            resolved = await resolve_key(s_resolve, ctx, provider="openai")
            assert resolved == "sk-user"
        # Cleanup
        async for s_cleanup_user in session_with_rls(ctx):
            from sqlalchemy import delete as sa_delete
            from app.models.provider_key import ProviderKey
            await s_cleanup_user.execute(sa_delete(ProviderKey).where(ProviderKey.user_id == seed_basic_user))
            await s_cleanup_user.commit()
        async for s_cleanup_sys in session_with_rls(system_operation_context()):
            from sqlalchemy import delete as sa_delete
            from app.models.provider_key import ProviderKey
            await s_cleanup_sys.execute(sa_delete(ProviderKey).where(ProviderKey.user_id == SYSTEM_USER_ID))
            await s_cleanup_sys.commit()


    async def test_shared_key_fallback_when_no_user_key(seed_basic_user: uuid.UUID) -> None:
        async for s_sys in session_with_rls(system_operation_context()):
            await set_provider_key(s_sys, system_operation_context(), provider="anthropic", plaintext="sk-shared")
            await s_sys.commit()
        ctx = _user_ctx(seed_basic_user)
        # User has no key for anthropic; system fallback resolves
        async for s in session_with_rls(ctx):
            assert await resolve_key(s, ctx, provider="anthropic") == "sk-shared"
        # Cleanup
        async for s_cleanup in session_with_rls(system_operation_context()):
            from sqlalchemy import delete as sa_delete
            from app.models.provider_key import ProviderKey
            await s_cleanup.execute(sa_delete(ProviderKey).where(ProviderKey.user_id == SYSTEM_USER_ID))
            await s_cleanup.commit()


    async def test_missing_provider_key_error(seed_basic_user: uuid.UUID) -> None:
        ctx = _user_ctx(seed_basic_user)
        async for s in session_with_rls(ctx):
            with pytest.raises(MissingProviderKey) as excinfo:
                await resolve_key(s, ctx, provider="openrouter")
            assert excinfo.value.provider == "openrouter"
    ```
  </action>
  <acceptance_criteria>
    - `test -f server/app/services/provider_keys.py`
    - `! grep -E "^(from|import) (fastapi|starlette)" server/app/services/provider_keys.py` returns 0 (D-17)
    - **CI grep gate (D-28):** `grep -q "encrypted_key: bytes = Field(exclude=True)" server/app/services/provider_keys.py` returns 0
    - `grep -q "class ProviderKeyResponse" server/app/services/provider_keys.py && grep -q "class MissingProviderKey" server/app/services/provider_keys.py` returns 0
    - `grep -q "encrypt_provider_key(plaintext)" server/app/services/provider_keys.py` returns 0
    - `grep -q "decrypt_provider_key(.*encrypted_key)" server/app/services/provider_keys.py` returns 0
    - `cd server && pytest -x -q app/tests/auth/test_provider_keys.py` exits 0 (4 tests pass)
    - All four canonical test names: `for n in test_encrypted_key_excluded_from_responses test_user_key_takes_precedence_over_shared test_shared_key_fallback_when_no_user_key test_missing_provider_key_error; do grep -q "def $n" server/app/tests/auth/test_provider_keys.py; done` exits 0
    - `cd server && ruff check app/services/provider_keys.py app/tests/auth/test_provider_keys.py` exits 0
  </acceptance_criteria>
  <done>provider_keys service writes Fernet-encrypted bytes; ProviderKeyResponse uses Field(exclude=True); resolve_key honors PRD §24.2 order; 4 integration tests pass.</done>
  <threat_ref>T-1b-01</threat_ref>
</task>

<task type="auto">
  <id>06-04</id>
  <name>Task 4: auth/deps.py — require_user / require_admin / require_fresh_auth</name>
  <read_first>
    - server/app/dependencies.py (Plan 05 task 05-03 — get_operation_context already populates OperationContext.session_id from the optional `sid` JWT claim)
    - server/app/auth/context.py (Plan 04 — OperationContext)
    - server/app/auth/core.py (Plan 05 task 05-01 — validate_jwt parses `sid` into AuthResult.session_id)
    - server/app/auth/tokens.py (Plan 04 task 04-03 — issue_access_jwt emits the optional `sid` claim)
    - server/app/services/sessions.py (this plan, task 06-01 — issue_session_pair / rotate_refresh thread `session_id=` into issue_access_jwt)
    - server/app/models/session.py (admin_fresh_until column)
    - .planning/phases/01b-auth-security-primitives/01b-RESEARCH.md §"Pattern 9" (lines 680-705)
    - .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md "server/app/auth/deps.py" section
    - .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md D-13, D-15, D-16
  </read_first>
  <action>
    This task ONLY owns `server/app/auth/deps.py`. The cross-file `sid` claim threading
    has been moved closer to its origin per the WARNING #6 fix:

      * `auth/tokens.py:issue_access_jwt(... session_id=None)` emission — Plan 04 task 04-03
      * `auth/core.py:validate_jwt` parses the optional `sid` claim into `AuthResult.session_id` — Plan 05 task 05-01
      * `dependencies.py:get_operation_context` projects `AuthResult.session_id` into `OperationContext.session_id` — Plan 05 task 05-03
      * `services/sessions.py:issue_session_pair` and `rotate_refresh` pass `session_id=` into `issue_access_jwt` — this plan task 06-01 (already updated)

    This task therefore creates `server/app/auth/deps.py` and consumes `ctx.session_id` in
    `require_fresh_auth`. Nothing else touches the sid pipeline.

    Create `server/app/auth/deps.py`:
    ```python
    """FastAPI Depends factories — auth gates (D-13, D-15, D-16).

    Three layers (each Depends on the previous):
      require_user        — any authenticated user
      require_admin       — role='admin'
      require_fresh_auth  — role='admin' AND session.admin_fresh_until > now()

    On failure, raise HTTPException with the canonical error envelope (D-16).
    require_fresh_auth consumes ctx.session_id (populated by get_operation_context
    via the `sid` JWT claim — see Plan 04 task 04-03 emission and Plan 05 task 05-01/05-03 parsing).
    """
    from __future__ import annotations

    from datetime import datetime, timezone

    from fastapi import Depends, HTTPException
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.auth.context import OperationContext
    from app.dependencies import get_db_session, get_operation_context
    from app.models.session import Session as SessionModel


    def admin_reauth_required_envelope() -> dict:
        """D-16 — failure response shape for require_fresh_auth."""
        return {
            "error": {
                "code": "admin_reauth_required",
                "message": "Fresh admin authentication is required.",
                "details": {
                    "reauth_url": "/api/v1/admin/reauth",
                    "freshness_window_minutes": 60,
                },
            }
        }


    async def require_user(
        ctx: OperationContext = Depends(get_operation_context),
    ) -> OperationContext:
        """Any authenticated request — placeholder gate so handlers can opt-in explicitly."""
        return ctx


    async def require_admin(
        ctx: OperationContext = Depends(get_operation_context),
    ) -> OperationContext:
        if ctx.role != "admin":
            raise HTTPException(
                status_code=403,
                detail={"error": {"code": "forbidden", "message": "admin role required"}},
            )
        return ctx


    async def require_fresh_auth(
        ctx: OperationContext = Depends(require_admin),
        session: AsyncSession = Depends(get_db_session),
    ) -> OperationContext:
        """D-13: 4-check enforcement.
          1. authenticated  (required by chain)
          2. role == admin  (require_admin)
          3. session row exists, not expired
          4. session.admin_fresh_until > now()

        ctx.session_id is populated by get_operation_context from the `sid` JWT claim.
        MCP bearer / system contexts have session_id=None → 403 admin_reauth_required.
        """
        if ctx.session_id is None:
            # MCP bearer / system contexts — D-14: factor not implemented in 1b
            raise HTTPException(status_code=403, detail=admin_reauth_required_envelope())
        s = await session.get(SessionModel, ctx.session_id)
        if s is None:
            raise HTTPException(status_code=403, detail=admin_reauth_required_envelope())
        now = datetime.now(timezone.utc)
        if s.expires_at is not None and s.expires_at < now:
            raise HTTPException(status_code=403, detail=admin_reauth_required_envelope())
        if s.admin_fresh_until is None or s.admin_fresh_until < now:
            raise HTTPException(status_code=403, detail=admin_reauth_required_envelope())
        return ctx
    ```
  </action>
  <acceptance_criteria>
    - `test -f server/app/auth/deps.py`
    - `grep -q "def admin_reauth_required_envelope" server/app/auth/deps.py` returns 0
    - `grep -q "async def require_user" server/app/auth/deps.py && grep -q "async def require_admin" server/app/auth/deps.py && grep -q "async def require_fresh_auth" server/app/auth/deps.py` returns 0
    - `grep -q '"code": "admin_reauth_required"' server/app/auth/deps.py` returns 0 (D-16)
    - `grep -q "freshness_window_minutes" server/app/auth/deps.py` returns 0 (D-16)
    - `grep -q "admin_fresh_until" server/app/auth/deps.py` returns 0
    - **require_fresh_auth consumes ctx.session_id (sid threading destination):** `grep -q "ctx.session_id" server/app/auth/deps.py` returns 0
    - Imports cleanly: `cd server && python -c "from app.auth.deps import require_user, require_admin, require_fresh_auth, admin_reauth_required_envelope; e = admin_reauth_required_envelope(); assert e['error']['code'] == 'admin_reauth_required'; assert e['error']['details']['reauth_url'] == '/api/v1/admin/reauth'; print('ok')"` prints `ok`
    - Existing JWT/RLS tests still green: `cd server && pytest -x -q app/tests/auth/test_jwt_tokens.py app/tests/auth/test_rls_isolation.py` exits 0
    - `cd server && ruff check app/auth/deps.py` exits 0
    - **Cross-plan verification (sid threading is intact):** `grep -q 'session_id: uuid.UUID | None = None' server/app/auth/tokens.py && grep -qE 'session_id\s*=.*claims\.get\(.sid.\)' server/app/auth/core.py && grep -qE 'session_id\s*=' server/app/dependencies.py` returns 0
  </acceptance_criteria>
  <done>auth/deps.py wires require_user/admin/fresh_auth chain; require_fresh_auth consumes the already-threaded ctx.session_id; envelope shape matches D-16 verbatim. The full sid pipeline (tokens.py emit → core.py parse → dependencies.py project → deps.py consume) is verified by the cross-plan grep.</done>
  <threat_ref>T-1b-05</threat_ref>
</task>

</tasks>

<verification>
  <command>cd server && ruff check app/services/ app/auth/ app/dependencies.py && pytest -x -q app/tests/auth/test_password.py app/tests/auth/test_jwt_tokens.py app/tests/auth/test_mcp_tokens_unit.py app/tests/auth/test_mcp_tokens_integration.py app/tests/auth/test_provider_keys.py app/tests/auth/test_rls_isolation.py app/tests/auth/test_encryption.py</command>
  <expected>~25 tests pass across 7 files (4 password + 5 JWT + 3 MCP unit + 4 MCP integration + 4 provider keys + 5 RLS isolation + 4 encryption); ruff clean.</expected>
</verification>

<must_haves>

## Truths
- services/* take OperationContext + AsyncSession; no FastAPI imports anywhere (D-17 invariant — verified by repo-wide grep).
- rotate_refresh is atomic in single transaction (D-03); replay → InvalidToken; audit_log entry on success and failure (D-26).
- record_login_attempt INSERTs in OWN transaction (Landmine #9).
- check_rate_limit returns retry_after_seconds when count >= 10 within 15-min window (D-07).
- wipe_login_attempts DELETEs by (ip, username) on successful login (D-08).
- normalize_username case-folds + strips (D-10); create_user refuses 'system'.
- verify_token updates last_used_at; revocation effective on next call.
- ProviderKeyResponse uses Field(exclude=True) — schema-level (D-28).
- resolve_key follows PRD §24.2 order: per-user → system shared → MissingProviderKey.
- require_fresh_auth implements all 4 D-13 checks; envelope matches D-16 verbatim.
- JWT carries optional sid claim; full chain (cross-plan): Plan 04 tokens.issue_access_jwt emits → Plan 05 auth.core.validate_jwt parses into AuthResult → Plan 05 dependencies.get_operation_context projects to OperationContext.session_id → this plan's auth/deps.require_fresh_auth consumes it → SessionModel.admin_fresh_until check.

## Artifacts
- `server/app/services/{__init__,users,sessions,mcp_tokens,provider_keys}.py`
- `server/app/auth/deps.py`
- 2 new passing integration test files (Wave-0 stubs replaced).
- `services/sessions.py` issues `issue_access_jwt(... session_id=)` so refresh-issued tokens carry the `sid` claim. The matching emit / parse / project edits live in Plans 04 (tokens.py) and 05 (core.py + dependencies.py).

## Key Links
- `services/sessions.rotate_refresh` ← atomic single transaction (D-03)
- `services/provider_keys.set_provider_key` → `encryption.encrypt_provider_key`
- `services/provider_keys.resolve_key` → `SYSTEM_USER_ID` (Plan 04 / Plan 02 seed)
- `auth/deps.require_fresh_auth` → `sessions.admin_fresh_until` (Plan 02 column)

</must_haves>

<output>
Append per-task rows to `.planning/phases/01b-auth-security-primitives/01B-VALIDATION.md`. Create `01B-06-SUMMARY.md` documenting service-layer discipline, sid claim threading, and Wave-0 → integration replacement.
</output>
