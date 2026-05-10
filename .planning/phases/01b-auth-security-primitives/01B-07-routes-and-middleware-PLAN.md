---
phase: 1b
plan: "07"
name: routes-and-middleware
wave: 4
depends_on: ["03", "05", "06"]
requirements: [AUTH-02, AUTH-03, AUTH-06, AUTH-07, AUTH-08]
files_modified:
  - server/app/auth/middleware.py
  - server/app/routes/auth.py
  - server/app/routes/admin.py
  - server/app/routes/__init__.py
  - server/app/main.py
  - server/app/scheduler/jobs/__init__.py
  - server/app/scheduler/jobs/prune_login_attempts.py
  - server/app/scheduler/run.py
  - server/app/mcp/__init__.py
  - server/app/mcp/server.py
  - server/app/tests/auth/test_login.py
  - server/app/tests/auth/test_admin_reauth.py
  - server/app/tests/auth/test_audit_log.py
  - server/app/tests/auth/test_trusted_proxy.py
  - server/app/tests/auth/test_trusted_proxy_unit.py
  - server/app/tests/auth/test_scheduler_prune.py
autonomous: true
must_haves:
  truths:
    - "main.py:create_app fails-fast (sys.exit(1)) if SMARTCOPILOT_FERNET_KEY or jwt_signing_key is empty (Phase 1b success criterion #4)"
    - "main.py mounts TrustedProxyMiddleware before any router (REQ-422-425, D-29)"
    - "POST /auth/login returns {access_jwt, refresh_token} on valid credentials"
    - "POST /auth/login rejects with 401 unauthorized on invalid credentials AND records login_attempts in own transaction (Landmine #9)"
    - "POST /auth/login returns 429 rate_limited (with retry_after_seconds) after 10 failures in 15 min (D-07)"
    - "POST /auth/refresh rotates atomically (D-03); replay returns 401 invalid_token"
    - "POST /api/v1/admin/reauth re-validates password via argon2 and stamps sessions.admin_fresh_until = now() + 60min (D-12)"
    - "Destructive admin route (the existing /api/v1/admin/_demo_destructive in Plan 07) requires Depends(require_fresh_auth); without fresh auth returns 403 admin_reauth_required envelope (D-16 verbatim)"
    - "TrustedProxyMiddleware: when trust_proxy=true AND socket peer in CIDR allowlist, request.state.client_ip = left-most XFF (D-29)"
    - "TrustedProxyMiddleware: when trust_proxy=false OR socket peer NOT in allowlist, request.state.client_ip = socket peer (XFF ignored)"
    - "scheduler/jobs/prune_login_attempts.prune_login_attempts() DELETEs rows older than retention_hours (D-09)"
    - "scheduler/run.py registers prune_login_attempts with AsyncIOScheduler add_job(... 'interval', hours=1, replace_existing=True) so the supervisord priority 40 process picks it up (D-09)"
    - "main.py registers a global @app.exception_handler(HTTPException) that returns JSONResponse(content=exc.detail) — flattens body[\"detail\"] to body[\"error\"] for the canonical envelope (BLOCKER #3)"
    - "server/app/mcp/__init__.py + server/app/mcp/server.py exist; main_http imports validate_bearer (D-21 seam) and raises NotImplementedError until Phase 1d wires the SDK"
    - "structlog configured (configure_logging called in lifespan startup)"
    - "PL-06: all system-user UUID references use auth.context.SYSTEM_USER_ID — never hardcode the string literal in application code"
    - "PL-07: `make_interval(hours => :h)` is PostgreSQL 16 named-parameter notation (Plan 06 uses `make_interval(secs => :window)`) — target is pgvector:pg16, so named notation is correct"
  artifacts:
    - path: "server/app/auth/middleware.py"
      provides: "TrustedProxyMiddleware (ASGI) populating request.state.client_ip"
    - path: "server/app/routes/auth.py"
      provides: "/auth/login, /auth/refresh, /auth/logout"
    - path: "server/app/routes/admin.py"
      provides: "/api/v1/admin/reauth, /api/v1/admin/_demo_destructive (proves require_fresh_auth gate)"
    - path: "server/app/scheduler/jobs/prune_login_attempts.py"
      provides: "prune_login_attempts() module-level coroutine (callable by APScheduler)"
    - path: "server/app/main.py"
      provides: "create_app() with startup-fail check + middleware + routers + structlog config + global HTTPException flattening handler"
    - path: "server/app/scheduler/run.py"
      provides: "AsyncIOScheduler bootstrap + add_job(prune_login_attempts, 'interval', hours=1, replace_existing=True)"
    - path: "server/app/mcp/server.py"
      provides: "D-21 seam: imports validate_bearer; main_http() raises NotImplementedError; full SDK wired in Phase 1d"
  key_links:
    - from: "server/app/main.py:create_app"
      to: "server/app/encryption.py:fernet"
      via: "lifespan startup calls fernet() — raises FernetKeyMissing if env empty → sys.exit(1)"
      pattern: "fernet()"
    - from: "server/app/routes/auth.py:login"
      to: "server/app/services/sessions.py:check_rate_limit + record_login_attempt + wipe_login_attempts"
      via: "rate-limit gate before password verify; record on failure; wipe on success"
      pattern: "check_rate_limit"
    - from: "server/app/routes/admin.py:reauth"
      to: "server/app/services/sessions.py:set_admin_fresh"
      via: "stamp admin_fresh_until on the current session_id from ctx"
      pattern: "set_admin_fresh"
threat_refs: [T-1b-04, T-1b-05, T-1b-07, T-1b-08, T-1b-09]
---

<plan_objective>
Wire the HTTP surface: ASGI `TrustedProxyMiddleware` for accurate client IP under reverse proxy (D-29), `routes/auth.py` for login/refresh/logout, `routes/admin.py` for `/api/v1/admin/reauth` plus a representative destructive route guarded by `require_fresh_auth`, and the APScheduler hourly `prune_login_attempts` job. Patch `main.py:create_app` to (a) startup-fail if Fernet/JWT keys missing (success criterion #4), (b) configure structlog with redaction processor (D-27), (c) mount the trusted-proxy middleware, (d) include the new routers. Replace remaining Wave-0 integration stubs (test_login, test_admin_reauth, test_audit_log, test_trusted_proxy*, test_scheduler_prune) with passing tests.
</plan_objective>

<threat_model>

## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Reverse proxy XFF header ↔ trusted client IP | Validate socket peer against CIDR allowlist BEFORE trusting XFF (D-29) — otherwise any client can spoof their IP for rate-limit bypass |
| /auth/login surface ↔ login_attempts row | Rate-limit gate runs BEFORE password verify; failure records in own transaction (Landmine #9) |
| /admin/* destructive routes ↔ session.admin_fresh_until | Per-route Depends(require_fresh_auth) — fails closed if a developer adds a destructive route without the gate (D-15) |
| Container start ↔ Fernet/JWT secret presence | Boot fails if either env var missing — ensures encrypted_key cannot be silently re-encrypted with a per-process random key |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-1b-04 | S (Spoofing — credential brute-force) | server/app/routes/auth.py:login | mitigate | Calls services.sessions.check_rate_limit BEFORE password verify; on failure calls record_login_attempt (own txn — Landmine #9). Returns 429 with `{error: {code: rate_limited, retry_after: N}}` envelope. |
| T-1b-05 | E (Elevation — admin freshness bypass) | server/app/routes/admin.py | mitigate | Per-route Depends(require_fresh_auth) on every destructive route. The /reauth route uses Depends(require_admin) (NOT require_fresh_auth) — re-auth is the gate that GRANTS freshness. |
| T-1b-07 | E (Refresh-token replay) | server/app/routes/auth.py:refresh | mitigate | Calls services.sessions.rotate_refresh (atomic txn, Plan 06). On InvalidToken returns 401. write_audit_log entries (D-26) trace replay attempts. |
| T-1b-08 | T (Audit-log tampering) | audit_log writes from /auth/refresh + /admin/reauth | mitigate | Routes call write_audit_log (Plan 05) — single INSERT path. audit_log has no UPDATE policies in 0002. |
| T-1b-09 | A (boot with no key) | server/app/main.py:create_app + lifespan | mitigate | At startup: `fernet()` → FernetKeyMissing if SMARTCOPILOT_FERNET_KEY empty → `sys.exit(1)` with stderr message. Same for empty `settings.jwt_signing_key`. Documented in `.env.example` (Plan 01). |
| T-1b-10 | I (log plaintext leak) | structlog config | mitigate | `configure_logging()` (Plan 01) called in lifespan startup; redaction processor scrubs the 7 D-27 keys before any sink. |

</threat_model>

<read_first_global>
- server/app/main.py (current shape — extend in place; preserve D-09 module discipline)
- server/app/encryption.py (Plan 03 — fernet(), FernetKeyMissing)
- server/app/dependencies.py (Plan 05 — get_operation_context, get_db_session)
- server/app/auth/deps.py (Plan 06 — require_admin, require_fresh_auth, admin_reauth_required_envelope)
- server/app/services/{users,sessions,provider_keys,mcp_tokens}.py (Plan 06)
- server/app/auth/audit.py (Plan 05 — write_audit_log)
- server/app/auth/password.py (Plan 04 — verify_password)
- server/app/logging/redaction.py (Plan 01 — configure_logging)
- server/app/routes/health.py (only existing route — convention)
- server/app/scheduler/run.py (existing scheduler stub — extend to register the prune job)
- .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md decisions D-12, D-13, D-15, D-16, D-29
- .planning/phases/01b-auth-security-primitives/01b-RESEARCH.md §"Pattern 10" (TrustedProxyMiddleware), §"Pattern 9", §"Step-up Re-auth", §"Login Throttling"
- .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md sections for `auth/middleware.py`, `routes/auth.py`, `routes/admin.py`, `main.py (MODIFY)`, `scheduler/jobs/prune_login_attempts.py`
- All Wave-0 stubs in tests/auth/{test_login,test_admin_reauth,test_audit_log,test_trusted_proxy,test_trusted_proxy_unit,test_scheduler_prune}.py
</read_first_global>

<tasks>

<task type="auto">
  <id>07-01</id>
  <name>Task 1: TrustedProxyMiddleware + unit tests</name>
  <read_first>
    - .planning/phases/01b-auth-security-primitives/01b-RESEARCH.md §"Pattern 10" (lines 712-735)
    - .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md "auth/middleware.py" section
    - .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md D-29
    - server/app/tests/auth/test_trusted_proxy_unit.py (Wave 0 stubs)
  </read_first>
  <action>
    Create `server/app/auth/middleware.py`:
    ```python
    """Trusted-proxy XFF middleware (D-29 / REQ-422-425).

    Populates scope['state']['client_ip'] which Starlette exposes as request.state.client_ip.
    Rate-limit logic and audit_log read from there.

    D-29 rule:
      IF settings.smartcopilot_trust_proxy is True
         AND socket peer IP is in any CIDR in settings.smartcopilot_trusted_proxy_cidrs
         AND X-Forwarded-For header is present
      THEN client_ip = left-most XFF entry
      ELSE client_ip = socket peer IP
    """
    from __future__ import annotations

    from collections.abc import Sequence
    from ipaddress import ip_address, ip_network


    class TrustedProxyMiddleware:
        def __init__(self, app, *, trust_proxy: bool, allowlist_cidrs: Sequence[str]):
            self.app = app
            self.trust = trust_proxy
            self.cidrs = []
            for c in allowlist_cidrs:
                if not c:
                    continue
                try:
                    self.cidrs.append(ip_network(c, strict=False))
                except ValueError:
                    # Skip malformed CIDR — silent (logged at config-load time elsewhere)
                    continue

        def _resolve_client_ip(self, scope: dict) -> str | None:
            peer = scope["client"][0] if scope.get("client") else None
            if not peer:
                return None
            if not self.trust:
                return peer
            try:
                peer_ip = ip_address(peer)
            except ValueError:
                return peer
            if not any(peer_ip in c for c in self.cidrs):
                return peer
            xff = next(
                (v for k, v in scope.get("headers", []) if k == b"x-forwarded-for"),
                None,
            )
            if not xff:
                return peer
            # D-29 / REQ-425: left-most IP
            leftmost = xff.decode().split(",")[0].strip()
            return leftmost or peer

        async def __call__(self, scope, receive, send):
            if scope["type"] != "http":
                await self.app(scope, receive, send)
                return
            client_ip = self._resolve_client_ip(scope)
            state = scope.setdefault("state", {})
            state["client_ip"] = client_ip
            await self.app(scope, receive, send)
    ```

    Implement `server/app/tests/auth/test_trusted_proxy_unit.py` (replace 3 Wave-0 stubs):
    ```python
    """AUTH-08 unit tests — TrustedProxyMiddleware D-29 logic."""
    from __future__ import annotations

    import pytest

    from app.auth.middleware import TrustedProxyMiddleware

    pytestmark = [pytest.mark.auth, pytest.mark.unit]


    def _scope(*, peer: str, xff: str | None = None) -> dict:
        headers = []
        if xff:
            headers.append((b"x-forwarded-for", xff.encode()))
        return {"type": "http", "client": (peer, 12345), "headers": headers}


    def test_leftmost_xff_chosen() -> None:
        mw = TrustedProxyMiddleware(app=None, trust_proxy=True, allowlist_cidrs=["10.0.0.0/8"])
        scope = _scope(peer="10.0.0.5", xff="203.0.113.10, 198.51.100.1")
        assert mw._resolve_client_ip(scope) == "203.0.113.10"


    def test_xff_ignored_when_trust_disabled() -> None:
        mw = TrustedProxyMiddleware(app=None, trust_proxy=False, allowlist_cidrs=["10.0.0.0/8"])
        scope = _scope(peer="10.0.0.5", xff="203.0.113.10")
        assert mw._resolve_client_ip(scope) == "10.0.0.5"


    def test_xff_ignored_when_peer_not_in_allowlist() -> None:
        mw = TrustedProxyMiddleware(app=None, trust_proxy=True, allowlist_cidrs=["10.0.0.0/8"])
        scope = _scope(peer="8.8.8.8", xff="203.0.113.10")
        # Peer is NOT in 10.0.0.0/8 → peer wins
        assert mw._resolve_client_ip(scope) == "8.8.8.8"
    ```
  </action>
  <acceptance_criteria>
    - `test -f server/app/auth/middleware.py`
    - `grep -q "class TrustedProxyMiddleware" server/app/auth/middleware.py` returns 0
    - `grep -q "left-most" server/app/auth/middleware.py || grep -q "leftmost" server/app/auth/middleware.py` returns 0
    - `cd server && pytest -x -q app/tests/auth/test_trusted_proxy_unit.py` exits 0 (3 tests pass)
    - `cd server && ruff check app/auth/middleware.py app/tests/auth/test_trusted_proxy_unit.py` exits 0
  </acceptance_criteria>
  <done>Middleware resolves left-most XFF when trust+allowlist match; ignores otherwise; 3 unit tests pass.</done>
</task>

<task type="auto">
  <id>07-02</id>
  <name>Task 2: routes/auth.py — login, refresh, logout</name>
  <read_first>
    - server/app/routes/health.py (only existing route — convention to follow)
    - server/app/services/users.py + services/sessions.py (Plan 06 — consume create_user, get_user_by_username, issue_session_pair, rotate_refresh, check_rate_limit, record_login_attempt, wipe_login_attempts, RateLimited, InvalidToken, normalize_username)
    - server/app/auth/password.py (verify_password)
    - server/app/auth/audit.py (write_audit_log)
    - server/app/dependencies.py (get_db_session, get_operation_context — for /auth/logout)
    - .planning/phases/01b-auth-security-primitives/01b-RESEARCH.md §"Pattern 9" (envelope), §"Pattern 8" (sliding window)
    - .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md D-03, D-07, D-08, D-26
    - server/app/tests/auth/test_login.py (Wave 0 stubs — 9 test names)
  </read_first>
  <action>
    Create `server/app/routes/auth.py`. **Critical (BLOCKER #2):** every DB session opened
    by this route is opened via `session_with_rls(...)` — never `async_session_factory()`
    directly — because Plan 02's RLS policies on `sessions`/`mcp_tokens` (and downstream
    tables touched here) require a GUC value. The pre-auth reads/writes use
    `system_operation_context()` so the system-bypass OR clause admits them; once the user
    is identified, the session pair issuance switches to the user's own context. The
    rate-limit/attempt/login_attempts paths target tables that are NOT in RLS_TABLES —
    they would work under any GUC — but standardizing on `session_with_rls` keeps the
    discipline uniform and avoids leaking unset-GUC sessions into the pool.

    ```python
    """Authentication endpoints (AUTH-02, AUTH-03).

    /auth/login   — username + password → {access_jwt, refresh_token}
    /auth/refresh — refresh_token → new pair (rotate-and-revoke, D-03)
    /auth/logout  — revoke caller's session

    All DB sessions are opened via `session_with_rls(...)` — pre-auth reads use
    `system_operation_context()` so 0002's RLS system-bypass OR clause admits them
    (BLOCKER #2 closure); the post-auth issuance/audit path runs under the user's
    own context.
    Rate limit: 10 failures / 15 min / (ip, username) — D-05–D-08.
    """
    from __future__ import annotations

    import uuid

    from fastapi import APIRouter, Depends, HTTPException, Request
    from pydantic import BaseModel, Field
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.auth.audit import write_audit_log
    from app.auth.context import OperationContext, system_operation_context
    from app.auth.password import verify_password
    from app.dependencies import get_db_session, get_operation_context, session_with_rls
    from app.services.sessions import (
        InvalidToken,
        check_rate_limit,
        issue_session_pair,
        record_login_attempt,
        revoke_session,
        rotate_refresh,
        wipe_login_attempts,
    )
    from app.services.users import get_user_by_username, normalize_username

    router = APIRouter(tags=["auth"])


    class LoginIn(BaseModel):
        username: str = Field(..., min_length=1, max_length=64)
        password: str = Field(..., min_length=1, max_length=512)


    class TokenPair(BaseModel):
        access_jwt: str
        refresh_token: str
        token_type: str = "Bearer"


    class RefreshIn(BaseModel):
        refresh_token: str


    def _client_ip(request: Request) -> str:
        return getattr(request.state, "client_ip", None) or (request.client.host if request.client else "unknown")


    def _system_ctx(request: Request, *, action: str) -> OperationContext:
        return system_operation_context(
            request_id=request.headers.get("x-request-id") or f"login-{action}",
            client_name=_client_ip(request),
        )


    @router.post("/auth/login", response_model=TokenPair)
    async def login(payload: LoginIn, request: Request) -> TokenPair:
        """Login — rate-limit-then-verify-then-issue, with own-transaction attempt record."""
        ip = _client_ip(request)
        username = normalize_username(payload.username)

        # Rate-limit gate (own connection under system context — login_attempts is
        # not RLS-gated but we still standardize on session_with_rls for pool hygiene)
        async for session in session_with_rls(_system_ctx(request, action="rate-check")):
            retry = await check_rate_limit(session, ip=ip, username=username)
            if retry is not None:
                raise HTTPException(
                    status_code=429,
                    detail={"error": {"code": "rate_limited", "message": "too many login failures",
                                     "details": {"retry_after_seconds": retry}}},
                )

        # Record attempt in OWN transaction BEFORE verify (Landmine #9)
        async for session in session_with_rls(_system_ctx(request, action="record-attempt")):
            await record_login_attempt(
                session, ip=ip, username=username,
                request_id=request.headers.get("x-request-id"),
                user_agent=request.headers.get("user-agent"),
            )

        # Verify — runs under system context so the user lookup AND the immediate
        # session pair INSERT (sessions row is owned by the user; the system-bypass
        # OR clause in 0002 admits the INSERT before the user GUC is set).
        async for session in session_with_rls(_system_ctx(request, action="verify")):
            user = await get_user_by_username(session, username)
            if user is None or not user.is_active:
                raise HTTPException(
                    status_code=401,
                    detail={"error": {"code": "unauthorized", "message": "invalid credentials"}},
                )
            if not await verify_password(user.password_hash, payload.password):
                raise HTTPException(
                    status_code=401,
                    detail={"error": {"code": "unauthorized", "message": "invalid credentials"}},
                )

            # Success: wipe attempts (D-08), issue session pair, audit.
            await wipe_login_attempts(session, ip=ip, username=username)
            user_ctx = OperationContext(
                user_id=user.id, role=user.role, transport="rest", remote=True,
                client_name=ip, request_id=request.headers.get("x-request-id") or "login",
            )
            access, refresh, sess_id = await issue_session_pair(session, user_ctx, user=user)
            ctx_with_session = OperationContext(
                user_id=user.id, role=user.role, transport="rest", remote=True,
                client_name=ip, request_id=user_ctx.request_id, session_id=sess_id,
            )
            await write_audit_log(
                session, ctx_with_session, action="login", target_kind="session",
                target_id=str(sess_id), ip=ip,
                user_agent=request.headers.get("user-agent"),
            )
            await session.commit()
        return TokenPair(access_jwt=access, refresh_token=refresh)


    @router.post("/auth/refresh", response_model=TokenPair)
    async def refresh(payload: RefreshIn, request: Request) -> TokenPair:
        """Atomic rotate-and-revoke — D-03. Replay = invalid_token (theft signal).

        Lookup runs under system context (we don't know whose refresh this is yet
        — RLS system-bypass OR clause admits the SELECT). The atomic DELETE+INSERT
        inside `rotate_refresh` runs in the same session, also under system context.
        """
        ip = _client_ip(request)
        # rotate_refresh writes audit_log on failure even when user is unknown.
        anon_ctx = system_operation_context(
            request_id=request.headers.get("x-request-id") or "refresh",
            client_name=ip,
        )
        async for session in session_with_rls(anon_ctx):
            try:
                access, new_refresh = await rotate_refresh(session, anon_ctx, raw_refresh=payload.refresh_token)
            except InvalidToken:
                raise HTTPException(
                    status_code=401,
                    detail={"error": {"code": "unauthorized", "message": "invalid refresh token"}},
                ) from None
            await session.commit()
        return TokenPair(access_jwt=access, refresh_token=new_refresh)


    @router.post("/auth/logout")
    async def logout(
        ctx: OperationContext = Depends(get_operation_context),
        session: AsyncSession = Depends(get_db_session),
    ) -> dict:
        if ctx.session_id is not None:
            await revoke_session(session, session_id=ctx.session_id)
            await session.commit()
        return {"status": "ok"}
    ```
  </action>
  <acceptance_criteria>
    - `test -f server/app/routes/auth.py`
    - `grep -q '@router.post("/auth/login"' server/app/routes/auth.py && grep -q '@router.post("/auth/refresh"' server/app/routes/auth.py && grep -q '@router.post("/auth/logout"' server/app/routes/auth.py` returns 0
    - `grep -q "check_rate_limit" server/app/routes/auth.py && grep -q "record_login_attempt" server/app/routes/auth.py && grep -q "wipe_login_attempts" server/app/routes/auth.py` returns 0
    - `grep -q "rotate_refresh" server/app/routes/auth.py` returns 0
    - `grep -q "rate_limited" server/app/routes/auth.py && grep -q "retry_after_seconds" server/app/routes/auth.py` returns 0
    - **BLOCKER #2 closure — all DB sessions go through session_with_rls (no bare async_session_factory):** `grep -q 'session_with_rls' server/app/routes/auth.py && ! grep -q 'async_session_factory()' server/app/routes/auth.py` returns 0
    - **System-context for pre-auth lookups:** `grep -q 'system_operation_context' server/app/routes/auth.py` returns 0
    - `cd server && ruff check app/routes/auth.py` exits 0
  </acceptance_criteria>
  <done>auth router exposes /auth/login, /auth/refresh, /auth/logout with rate-limit-then-verify ordering; canonical error envelope used.</done>
  <threat_ref>T-1b-04</threat_ref>
</task>

<task type="auto">
  <id>07-03</id>
  <name>Task 3: routes/admin.py — /admin/reauth + demo destructive route</name>
  <read_first>
    - server/app/services/sessions.py (set_admin_fresh — Plan 06)
    - server/app/services/users.py (get_user_by_id)
    - server/app/auth/password.py (verify_password)
    - server/app/auth/deps.py (require_admin, require_fresh_auth, admin_reauth_required_envelope — Plan 06)
    - server/app/auth/audit.py (write_audit_log)
    - .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md D-12, D-13, D-15, D-16, D-25
    - server/app/tests/auth/test_admin_reauth.py (Wave 0 stubs)
  </read_first>
  <action>
    Create `server/app/routes/admin.py`:
    ```python
    """Admin endpoints (AUTH-06, AUTH-07).

    /api/v1/admin/reauth         — password re-validation; stamps admin_fresh_until (D-12)
    /api/v1/admin/_demo_destructive — example route guarded by require_fresh_auth (D-15);
                                      proves the per-route gate. A real destructive
                                      operation (rotate-Fernet, delete-user) lands in
                                      Phase 1d/6 with the same Depends pattern.
    """
    from __future__ import annotations

    from fastapi import APIRouter, Depends, HTTPException, Request
    from pydantic import BaseModel, Field
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.auth.audit import write_audit_log
    from app.auth.context import OperationContext
    from app.auth.deps import admin_reauth_required_envelope, require_admin, require_fresh_auth
    from app.auth.password import verify_password
    from app.dependencies import get_db_session
    from app.services.sessions import set_admin_fresh
    from app.services.users import get_user_by_id
    from app.settings import settings

    router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


    class ReauthIn(BaseModel):
        # D-14: only password factor in 1b. The factor field reserves the enum; only "password" accepted.
        factor: str = Field(default="password")
        password: str = Field(..., min_length=1, max_length=512)


    @router.post("/reauth")
    async def reauth(
        payload: ReauthIn,
        request: Request,
        ctx: OperationContext = Depends(require_admin),
        session: AsyncSession = Depends(get_db_session),
    ) -> dict:
        """D-12: re-validate the admin's password; stamp admin_fresh_until = now() + 60min."""
        if payload.factor != "password":
            # D-14 — reserved for future factor; reject other values explicitly
            raise HTTPException(
                status_code=501,
                detail={"error": {"code": "not_implemented", "message": "factor 'password' is the only supported value in v1"}},
            )
        if ctx.session_id is None:
            raise HTTPException(status_code=403, detail=admin_reauth_required_envelope())

        user = await get_user_by_id(session, ctx.user_id)
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=401,
                detail={"error": {"code": "unauthorized", "message": "user not found"}},
            )
        ip = getattr(request.state, "client_ip", None) or (request.client.host if request.client else "unknown")
        if not await verify_password(user.password_hash, payload.password):
            await write_audit_log(
                session, ctx, action="admin_reauth_failed", target_kind="session",
                target_id=str(ctx.session_id), ip=ip,
                user_agent=request.headers.get("user-agent"),
            )
            await session.commit()
            raise HTTPException(
                status_code=401,
                detail={"error": {"code": "unauthorized", "message": "invalid password"}},
            )
        await set_admin_fresh(session, session_id=ctx.session_id, minutes=settings.admin_fresh_window_minutes)
        await write_audit_log(
            session, ctx, action="admin_reauth", target_kind="session",
            target_id=str(ctx.session_id), ip=ip,
            user_agent=request.headers.get("user-agent"),
        )
        await session.commit()
        return {"status": "ok", "freshness_window_minutes": settings.admin_fresh_window_minutes}


    @router.post("/_demo_destructive")
    async def _demo_destructive(
        ctx: OperationContext = Depends(require_fresh_auth),
    ) -> dict:
        """Phase 1b proof: ANY destructive admin route uses Depends(require_fresh_auth).

        Returns 200 only when caller has fresh admin auth. Otherwise the gate raises 403 admin_reauth_required.
        Replace with real destructive routes in Phase 1d/6 — same pattern.
        """
        return {"status": "ok", "actor": str(ctx.user_id)}
    ```

    Edit `server/app/routes/__init__.py` (currently `"""HTTP route modules."""` — leave docstring; the file is intentionally empty of imports). Routers are wired in main.py.
  </action>
  <acceptance_criteria>
    - `test -f server/app/routes/admin.py`
    - `grep -q '@router.post("/reauth")' server/app/routes/admin.py && grep -q '@router.post("/_demo_destructive")' server/app/routes/admin.py` returns 0
    - `grep -q "Depends(require_admin)" server/app/routes/admin.py && grep -q "Depends(require_fresh_auth)" server/app/routes/admin.py` returns 0 (D-15 — explicit per route)
    - `grep -q "set_admin_fresh" server/app/routes/admin.py` returns 0
    - `grep -q "admin_reauth_failed" server/app/routes/admin.py && grep -q "admin_reauth" server/app/routes/admin.py` returns 0 (D-25)
    - `grep -q "prefix=\"/api/v1/admin\"" server/app/routes/admin.py` returns 0
    - `cd server && ruff check app/routes/admin.py` exits 0
  </acceptance_criteria>
  <done>admin router exposes /reauth (require_admin) + /_demo_destructive (require_fresh_auth); audit_log entries on success/failure of reauth.</done>
  <threat_ref>T-1b-05</threat_ref>
</task>

<task type="auto">
  <id>07-04</id>
  <name>Task 4: scheduler/jobs/prune_login_attempts.py + integration test</name>
  <read_first>
    - server/app/scheduler/run.py (existing Phase 1a stub — extend to register the prune job with APScheduler 3.x AsyncIOScheduler; D-09 mandates hourly pruning so Phase 1b owns the wire-up, not Phase 4)
    - server/app/dependencies.py (session_with_rls)
    - server/app/auth/context.py (system_operation_context)
    - .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md "scheduler/jobs/prune_login_attempts.py" section
    - .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md D-09 (24h retention)
    - server/app/tests/auth/test_scheduler_prune.py (Wave 0 stubs)
  </read_first>
  <action>
    Create `server/app/scheduler/jobs/__init__.py` — single line: `"""Scheduled jobs. Module-level callables only (APScheduler picklability)."""`

    Create `server/app/scheduler/jobs/prune_login_attempts.py`:
    ```python
    """Hourly retention job for login_attempts (D-09).

    Phase 1b ships the function AND registers it with APScheduler 3.x
    AsyncIOScheduler via the extended scheduler/run.py (see sub-action below).
    Phase 4 will swap to SQLAlchemyJobStore for durability across restarts;
    Phase 1b uses the default in-memory store, which is sufficient because
    the job is idempotent and re-registers on every supervisord restart.

    CLAUDE.md: module-level function (no closures, no lambdas) — APScheduler 3.x
    SQLAlchemyJobStore pickles job args.
    """
    from __future__ import annotations

    from sqlalchemy import text

    from app.auth.context import system_operation_context
    from app.dependencies import session_with_rls
    from app.settings import settings


    async def prune_login_attempts() -> int:
        """DELETE rows older than retention_hours. Returns the number deleted."""
        ctx = system_operation_context(request_id="prune_login_attempts", client_name="scheduler")
        deleted = 0
        async for session in session_with_rls(ctx):
            result = await session.execute(
                text(
                    "DELETE FROM login_attempts "
                    "WHERE attempted_at < now() - make_interval(hours => :h)"
                ),
                {"h": settings.login_attempts_retention_hours},
            )
            deleted = result.rowcount or 0
            await session.commit()
        return deleted
    ```

    **Sub-action (WARNING #7 closure — D-09 APScheduler wire-up):** extend
    `server/app/scheduler/run.py` (Phase 1a stub) to register the job. The Phase 1a
    stub currently does no APScheduler work; replace its loop with an AsyncIOScheduler
    bootstrap that adds the prune job and runs the asyncio event loop. New shape:

    ```python
    """APScheduler process entry point.

    Phase 1b: registers the hourly prune_login_attempts job (D-09).
    Phase 4 will swap the default in-memory store for SQLAlchemyJobStore for
    cross-restart durability. Supervisord program priority 40 invokes this as:
        python -m app.scheduler.run
    """
    from __future__ import annotations

    import asyncio
    import logging
    import signal
    import sys

    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    from app.scheduler.jobs.prune_login_attempts import prune_login_attempts

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [scheduler.run] %(message)s")
    log = logging.getLogger("smart_copilot.scheduler")


    async def _amain() -> int:
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            prune_login_attempts,
            "interval",
            hours=1,
            id="prune_login_attempts",
            replace_existing=True,
            coalesce=True,
        )
        scheduler.start()
        log.info("scheduler started; jobs registered: prune_login_attempts (hourly)")
        stop_event = asyncio.Event()

        def _stop(signum, _frame):  # noqa: ARG001
            log.info("received signal %s; shutting down", signum)
            stop_event.set()

        signal.signal(signal.SIGTERM, _stop)
        signal.signal(signal.SIGINT, _stop)
        await stop_event.wait()
        scheduler.shutdown(wait=False)
        log.info("scheduler shutdown complete")
        return 0


    def main() -> int:
        return asyncio.run(_amain())


    if __name__ == "__main__":
        sys.exit(main())
    ```

    Implement `server/app/tests/auth/test_scheduler_prune.py`:
    ```python
    """AUTH-03 / D-09 — login_attempts retention job."""
    from __future__ import annotations

    import pytest
    from sqlalchemy import text

    from app.auth.context import system_operation_context
    from app.dependencies import session_with_rls
    from app.scheduler.jobs.prune_login_attempts import prune_login_attempts

    pytestmark = [pytest.mark.auth, pytest.mark.integration]


    async def _seed_attempt(*, age_hours: int) -> None:
        async for session in session_with_rls(system_operation_context()):
            await session.execute(
                text(
                    "INSERT INTO login_attempts (username, ip, attempted_at) "
                    "VALUES ('seed_user', '127.0.0.1', now() - make_interval(hours => :h))"
                ),
                {"h": age_hours},
            )
            await session.commit()


    async def _count_attempts() -> int:
        async for session in session_with_rls(system_operation_context()):
            return (await session.execute(text("SELECT count(*) FROM login_attempts WHERE username='seed_user'"))).scalar_one()


    async def test_prune_login_attempts_deletes_old_rows() -> None:
        # cleanup any pre-existing rows
        async for session in session_with_rls(system_operation_context()):
            await session.execute(text("DELETE FROM login_attempts WHERE username = 'seed_user'"))
            await session.commit()
        await _seed_attempt(age_hours=48)  # older than 24h retention
        before = await _count_attempts()
        assert before == 1
        deleted = await prune_login_attempts()
        assert deleted >= 1
        after = await _count_attempts()
        assert after == 0


    async def test_prune_login_attempts_keeps_recent_rows() -> None:
        async for session in session_with_rls(system_operation_context()):
            await session.execute(text("DELETE FROM login_attempts WHERE username = 'seed_user'"))
            await session.commit()
        await _seed_attempt(age_hours=1)  # within 24h retention
        await prune_login_attempts()
        after = await _count_attempts()
        assert after == 1
        # cleanup
        async for session in session_with_rls(system_operation_context()):
            await session.execute(text("DELETE FROM login_attempts WHERE username = 'seed_user'"))
            await session.commit()
    ```
  </action>
  <acceptance_criteria>
    - `test -f server/app/scheduler/jobs/__init__.py && test -f server/app/scheduler/jobs/prune_login_attempts.py`
    - `grep -q "async def prune_login_attempts" server/app/scheduler/jobs/prune_login_attempts.py` returns 0
    - `grep -q "make_interval(hours => :h)" server/app/scheduler/jobs/prune_login_attempts.py` returns 0
    - **No closure/lambda in job (CLAUDE.md anti-pattern):** `! grep -E "lambda" server/app/scheduler/jobs/prune_login_attempts.py` returns 0
    - **APScheduler wire-up (WARNING #7 closure / D-09):** `grep -q "AsyncIOScheduler" server/app/scheduler/run.py && grep -q "prune_login_attempts" server/app/scheduler/run.py && grep -q "'interval'" server/app/scheduler/run.py && grep -q "hours=1" server/app/scheduler/run.py && grep -q "replace_existing=True" server/app/scheduler/run.py` returns 0
    - `cd server && pytest -x -q app/tests/auth/test_scheduler_prune.py` exits 0 (2 tests pass)
    - `cd server && ruff check app/scheduler/jobs/ app/scheduler/run.py` exits 0
  </acceptance_criteria>
  <done>Module-level prune coroutine works against testcontainer DB; deletes >24h rows; preserves recent rows; 2 tests pass.</done>
</task>

<task type="auto">
  <id>07-05</id>
  <name>Task 5: main.py — startup-fail + middleware + routers + structlog</name>
  <read_first>
    - server/app/main.py (current Phase 1a shape — extend in place; preserve D-09 discipline)
    - server/app/encryption.py (Plan 03)
    - server/app/auth/middleware.py (Task 07-01)
    - server/app/routes/auth.py (Task 07-02)
    - server/app/routes/admin.py (Task 07-03)
    - server/app/logging/redaction.py (Plan 01)
    - .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md "server/app/main.py (MODIFY)" section
    - .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md D-24, D-27 (Fernet startup-fail, structlog redaction)
  </read_first>
  <action>
    Replace `server/app/main.py` with the extended shape:

    ```python
    """FastAPI application factory.

    D-09: this module manages app lifecycle ONLY. It does NOT create the engine.
    D-24: Fernet key required at startup — container exits non-zero if missing.
    D-27: structlog redaction processor configured in lifespan startup.

    Error envelope discipline (BLOCKER #3): every route raises
    HTTPException(detail={"error": {"code": ..., "message": ...}}). FastAPI's
    default handler wraps that in {"detail": ...} — clients then see
    body["detail"]["error"]["code"]. We register a global exception handler that
    returns JSONResponse(content=exc.detail) so clients see body["error"]["code"]
    directly. Tests in 07-06 and Plan 08 acceptance assert against this flat shape.
    """

    from __future__ import annotations

    import sys
    from collections.abc import AsyncIterator
    from contextlib import asynccontextmanager

    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse

    from app.auth.middleware import TrustedProxyMiddleware
    from app.database import engine  # import triggers connect event registration
    from app.encryption import FernetKeyMissing, fernet
    from app.logging.redaction import configure_logging
    from app.routes.admin import router as admin_router
    from app.routes.auth import router as auth_router
    from app.routes.health import router as health_router
    from app.settings import settings


    def _fail_startup_if_missing_secrets() -> None:
        """D-24 + Phase 1b success criterion #4: refuse to start without keys."""
        try:
            fernet()  # validates SMARTCOPILOT_FERNET_KEY
        except FernetKeyMissing as e:
            print(f"FATAL: {e}", file=sys.stderr)
            sys.exit(1)
        if not settings.jwt_signing_key:
            print(
                "FATAL: JWT_SIGNING_KEY env var is required to start",
                file=sys.stderr,
            )
            sys.exit(1)


    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging()
        _fail_startup_if_missing_secrets()
        yield
        await engine.dispose()


    def create_app() -> FastAPI:
        app = FastAPI(title="Smart Copilot", version="0.0.0", lifespan=lifespan)
        app.add_middleware(
            TrustedProxyMiddleware,
            trust_proxy=settings.smartcopilot_trust_proxy,
            allowlist_cidrs=settings.smartcopilot_trusted_proxy_cidrs,
        )

        # BLOCKER #3 closure — flatten HTTPException(detail={"error": {...}}) to
        # body["error"][...] (otherwise the default handler wraps in body["detail"]).
        @app.exception_handler(HTTPException)
        async def _flatten_http_error(request: Request, exc: HTTPException) -> JSONResponse:  # noqa: ARG001
            payload = exc.detail
            # If a route raised HTTPException with a non-dict detail (string/int),
            # fall back to the default {"detail": ...} shape.
            if not isinstance(payload, dict):
                payload = {"detail": payload}
            return JSONResponse(status_code=exc.status_code, content=payload)

        app.include_router(health_router)
        app.include_router(auth_router)
        app.include_router(admin_router)
        return app


    app = create_app()
    ```

    Note: `_fail_startup_if_missing_secrets()` runs INSIDE `lifespan` (on app startup) — when uvicorn imports `main.py`, the FastAPI app is constructed but the lifespan callback only fires when uvicorn starts serving. This means tests that import `app.main` do NOT crash on missing keys (Phase 1a tests use `db_session` fixture which triggers Alembic; tests don't enter lifespan unless they spin up the ASGI server via `httpx.AsyncClient(transport=ASGITransport(app=app))` — which DOES run lifespan). For test usage, conftest fixtures set `SMARTCOPILOT_FERNET_KEY` and `SMARTCOPILOT_JWT_SIGNING_KEY` env vars BEFORE testcontainer boot.

    To support this, edit `server/app/tests/conftest.py` (top of file, BEFORE importing `app.main`): add a session-scoped autouse fixture that ensures both env vars exist for the test process. Add this fixture at the top of the existing conftest.py BEFORE the `from app.models import Base` import is fine — but importing app.main is the trigger. Add at the very top of conftest.py:

    ```python
    import os
    # NOTE: SMARTCOPILOT_JWT_SIGNING_KEY matches the project convention (SMARTCOPILOT_* prefix).
    # pydantic-settings (case_sensitive=False) maps the jwt_signing_key field to
    # both SMARTCOPILOT_JWT_SIGNING_KEY and JWT_SIGNING_KEY; we use the former
    # for consistency with SMARTCOPILOT_FERNET_KEY.
    os.environ.setdefault("SMARTCOPILOT_FERNET_KEY", "T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU=")  # test-only Fernet key
    os.environ.setdefault("SMARTCOPILOT_JWT_SIGNING_KEY", "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa")
    ```

    This is a TEST-only escape hatch; production runs with real keys. Keep the rest of conftest.py unchanged.
  </action>
  <acceptance_criteria>
    - `grep -q "from app.encryption import FernetKeyMissing, fernet" server/app/main.py` returns 0
    - `grep -q "TrustedProxyMiddleware" server/app/main.py && grep -q "configure_logging()" server/app/main.py` returns 0
    - `grep -q "auth_router" server/app/main.py && grep -q "admin_router" server/app/main.py && grep -q "health_router" server/app/main.py` returns 0
    - `grep -q 'sys.exit(1)' server/app/main.py` returns 0 (startup-fail)
    - **BLOCKER #3 closure — global HTTPException handler flattens detail:** `grep -q '@app.exception_handler(HTTPException)' server/app/main.py && grep -q 'JSONResponse(status_code=exc.status_code, content=payload)' server/app/main.py` returns 0
    - Engine creation NOT in main.py (D-09 invariant): `! grep -q "create_async_engine" server/app/main.py` returns 0
    - conftest sets test env vars: `grep -q 'os.environ.setdefault("SMARTCOPILOT_FERNET_KEY"' server/app/tests/conftest.py` returns 0
    - `grep -q 'os.environ.setdefault("SMARTCOPILOT_JWT_SIGNING_KEY"' server/app/tests/conftest.py` returns 0
    - Phase 1a boot tests still pass: `cd server && pytest -x -q app/tests/integration/test_boot.py` exits 0
    - `cd server && ruff check app/main.py app/tests/conftest.py` exits 0
  </acceptance_criteria>
  <done>main.py mounts trusted-proxy + 3 routers; startup-fails on missing secrets; structlog configured; test env vars seeded; Phase 1a tests still green.</done>
  <threat_ref>T-1b-09</threat_ref>
</task>

<task type="auto" tdd="true">
  <id>07-06</id>
  <name>Task 6: Implement remaining integration tests (login, admin_reauth, audit_log, trusted_proxy)</name>
  <read_first>
    - server/app/tests/auth/{test_login,test_admin_reauth,test_audit_log,test_trusted_proxy}.py (Wave 0 stubs)
    - server/app/tests/auth/conftest.py (seed_admin_user, seed_basic_user fixtures)
    - server/app/main.py (just-extended)
    - server/app/auth/tokens.py (issue_access_jwt — for issuing test tokens)
    - server/app/services/sessions.py (issue_session_pair — alternative)
  </read_first>
  <action>
    Replace stubs in 4 files. Use `httpx.AsyncClient(transport=ASGITransport(app=app))` for HTTP. Each test creates its own user (or uses fixture), POSTs to the route, asserts response shape.

    Provide a helper in `tests/auth/conftest.py` to issue a valid access JWT for a fixture user (append to existing conftest.py — do NOT replace):
    ```python
    # Append to server/app/tests/auth/conftest.py

    import asyncio

    import pytest_asyncio
    from app.auth.tokens import issue_access_jwt
    from app.services.sessions import issue_session_pair
    from app.auth.context import OperationContext
    from app.dependencies import session_with_rls


    @pytest_asyncio.fixture(loop_scope="session")
    async def admin_token_pair(seed_admin_user):
        """Return (access_jwt, refresh_token, session_id) for the admin fixture."""
        ctx = OperationContext(
            user_id=seed_admin_user, role="admin", transport="rest", remote=True,
            client_name="test", request_id="fixture",
        )
        async for session in session_with_rls(ctx):
            from app.services.users import get_user_by_id
            user = await get_user_by_id(session, seed_admin_user)
            access, refresh, sid = await issue_session_pair(session, ctx, user=user)
            await session.commit()
            return access, refresh, sid
    ```

    Now implement test files. For each, follow this skeleton (concrete bodies vary by test):

    `server/app/tests/auth/test_login.py` — full implementation. Sample patterns:
    ```python
    """AUTH-02 / AUTH-03 integration — /auth/login + /auth/refresh + rate limit."""
    from __future__ import annotations

    import asyncio
    import hashlib
    import uuid

    import pytest
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import text

    from app.auth.context import system_operation_context
    from app.dependencies import session_with_rls
    from app.main import app

    pytestmark = [pytest.mark.auth, pytest.mark.integration]


    def _new_client():
        # AsyncClient(...) is a regular constructor, NOT a coroutine — no await needed
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


    async def _create_user_via_service(username: str, password: str, role: str = "user"):
        from app.services.users import create_user
        ctx = system_operation_context()
        async for session in session_with_rls(ctx):
            user = await create_user(session, ctx, username=username, password_plain=password, role=role)
            await session.commit()
            return user.id


    async def _delete_user(user_id):
        async for session in session_with_rls(system_operation_context()):
            await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": str(user_id)})
            await session.commit()


    async def test_login_returns_jwt_pair() -> None:
        uid = await _create_user_via_service("loginuser1", "p@ssw0rd")
        try:
            async with _new_client() as c:
                r = await c.post("/auth/login", json={"username": "loginuser1", "password": "p@ssw0rd"})
            assert r.status_code == 200, r.text
            body = r.json()
            assert "access_jwt" in body and "refresh_token" in body
            assert body["token_type"] == "Bearer"
        finally:
            await _delete_user(uid)


    async def test_login_invalid_credentials_returns_401() -> None:
        uid = await _create_user_via_service("loginuser2", "p@ssw0rd")
        try:
            async with _new_client() as c:
                r = await c.post("/auth/login", json={"username": "loginuser2", "password": "WRONG"})
            assert r.status_code == 401
            assert r.json()["error"]["code"] == "unauthorized"
        finally:
            await _delete_user(uid)


    async def test_refresh_token_stored_as_hash() -> None:
        uid = await _create_user_via_service("refreshuser", "p@ssw0rd")
        try:
            async with _new_client() as c:
                r = await c.post("/auth/login", json={"username": "refreshuser", "password": "p@ssw0rd"})
            refresh = r.json()["refresh_token"]
            expected_hash = hashlib.sha256(refresh.encode()).hexdigest()
            async for s in session_with_rls(system_operation_context()):
                row = (await s.execute(text("SELECT token_hash FROM sessions WHERE token_hash = :h"), {"h": expected_hash})).first()
                assert row is not None, "refresh stored as sha256 hex matching client value"
        finally:
            await _delete_user(uid)


    async def test_refresh_rotation_revokes_old() -> None:
        uid = await _create_user_via_service("rotuser", "p@ssw0rd")
        try:
            async with _new_client() as c:
                r = await c.post("/auth/login", json={"username": "rotuser", "password": "p@ssw0rd"})
                old_refresh = r.json()["refresh_token"]
                r2 = await c.post("/auth/refresh", json={"refresh_token": old_refresh})
                assert r2.status_code == 200
                new_refresh = r2.json()["refresh_token"]
                assert new_refresh != old_refresh
        finally:
            await _delete_user(uid)


    async def test_old_refresh_replay_rejected() -> None:
        uid = await _create_user_via_service("replayuser", "p@ssw0rd")
        try:
            async with _new_client() as c:
                r = await c.post("/auth/login", json={"username": "replayuser", "password": "p@ssw0rd"})
                old_refresh = r.json()["refresh_token"]
                # First rotate succeeds
                ok = await c.post("/auth/refresh", json={"refresh_token": old_refresh})
                assert ok.status_code == 200
                # Replay of old refresh now fails
                bad = await c.post("/auth/refresh", json={"refresh_token": old_refresh})
                assert bad.status_code == 401
                assert bad.json()["error"]["code"] == "unauthorized"
        finally:
            await _delete_user(uid)


    async def test_rate_limit_after_10_failures() -> None:
        uid = await _create_user_via_service("rluser", "p@ssw0rd")
        try:
            async with _new_client() as c:
                # 10 failed attempts
                for _ in range(10):
                    await c.post("/auth/login", json={"username": "rluser", "password": "WRONG"})
                # 11th should be rate-limited
                r = await c.post("/auth/login", json={"username": "rluser", "password": "WRONG"})
                assert r.status_code == 429
                body = r.json()
                assert body["error"]["code"] == "rate_limited"
                assert "retry_after_seconds" in body["error"]["details"]
        finally:
            # cleanup login_attempts
            async for s in session_with_rls(system_operation_context()):
                await s.execute(text("DELETE FROM login_attempts WHERE username = :u"), {"u": "rluser"})
                await s.commit()
            await _delete_user(uid)


    async def test_rate_limit_response_envelope() -> None:
        # Ensures the envelope shape is exactly {error: {code, message, details: {retry_after_seconds}}}
        uid = await _create_user_via_service("envuser", "p@ssw0rd")
        try:
            async with _new_client() as c:
                for _ in range(10):
                    await c.post("/auth/login", json={"username": "envuser", "password": "X"})
                r = await c.post("/auth/login", json={"username": "envuser", "password": "X"})
                body = r.json()
                assert set(body["error"].keys()) >= {"code", "message", "details"}
                assert body["error"]["code"] == "rate_limited"
                assert isinstance(body["error"]["details"]["retry_after_seconds"], int)
        finally:
            async for s in session_with_rls(system_operation_context()):
                await s.execute(text("DELETE FROM login_attempts WHERE username = :u"), {"u": "envuser"})
                await s.commit()
            await _delete_user(uid)


    async def test_successful_login_wipes_attempts() -> None:
        uid = await _create_user_via_service("wipeuser", "p@ssw0rd")
        try:
            async with _new_client() as c:
                await c.post("/auth/login", json={"username": "wipeuser", "password": "WRONG"})
                await c.post("/auth/login", json={"username": "wipeuser", "password": "WRONG"})
                ok = await c.post("/auth/login", json={"username": "wipeuser", "password": "p@ssw0rd"})
                assert ok.status_code == 200
                # Attempts should be wiped
                async for s in session_with_rls(system_operation_context()):
                    cnt = (await s.execute(text("SELECT count(*) FROM login_attempts WHERE username = :u"), {"u": "wipeuser"})).scalar_one()
                    assert cnt == 0
        finally:
            await _delete_user(uid)


    async def test_sliding_window_ages_out() -> None:
        # Seed an attempt 16 minutes ago (> 15 min window) and verify it doesn't count
        uid = await _create_user_via_service("agingouser", "p@ssw0rd")
        try:
            async for s in session_with_rls(system_operation_context()):
                await s.execute(
                    text(
                        "INSERT INTO login_attempts (username, ip, attempted_at) "
                        "SELECT 'agingouser', '127.0.0.1', now() - make_interval(mins => 16) "
                        "FROM generate_series(1, 12)"
                    ),
                )
                await s.commit()
            async with _new_client() as c:
                # Should NOT be rate-limited because seeded rows are >15 min old
                r = await c.post("/auth/login", json={"username": "agingouser", "password": "p@ssw0rd"})
                assert r.status_code == 200, f"sliding window should age out — got {r.status_code}: {r.text}"
        finally:
            async for s in session_with_rls(system_operation_context()):
                await s.execute(text("DELETE FROM login_attempts WHERE username = :u"), {"u": "agingouser"})
                await s.commit()
            await _delete_user(uid)
    ```

    `server/app/tests/auth/test_admin_reauth.py` — implement 7 tests. Cover:
    - `test_role_enum_is_admin_or_user`: query `SELECT enumlabel FROM pg_enum WHERE enumtypid = 'user_role_enum'::regtype` and assert exactly `{'admin','user'}`.
    - `test_non_admin_forbidden_from_admin_route`: log in as basic user; POST /api/v1/admin/_demo_destructive with their token → 403 forbidden envelope (not admin_reauth_required since require_admin fails first).
    - `test_reauth_sets_admin_fresh_until`: log in admin, POST /api/v1/admin/reauth with correct password, assert sessions.admin_fresh_until > now().
    - `test_destructive_route_403_without_fresh_auth`: log in admin; immediately call /_demo_destructive → 403 admin_reauth_required envelope.
    - `test_admin_reauth_required_envelope_shape`: assert envelope shape exactly `{error: {code: 'admin_reauth_required', message: '...', details: {reauth_url: '/api/v1/admin/reauth', freshness_window_minutes: 60}}}`.
    - `test_fresh_auth_expires_after_60_minutes`: use freezegun OR direct UPDATE on sessions.admin_fresh_until to set it to 5 minutes ago, then call /_demo_destructive → 403.
    - `test_reauth_unsupported_factor_returns_not_implemented`: POST /reauth with `{"factor":"mcp_token","password":"x"}` → 501 not_implemented (D-14).

    `server/app/tests/auth/test_audit_log.py` — implement 4 tests:
    - `test_admin_op_writes_audit_log`: do reauth, query audit_log for action='admin_reauth'.
    - `test_admin_reauth_success_writes_audit_log`: same as above with details check.
    - `test_admin_reauth_failure_writes_audit_log_with_reason`: bad password → 401 + audit_log row with action='admin_reauth_failed'.
    - `test_refresh_rotation_audit_logged`: rotate refresh; assert audit_log row with action='refresh_rotated'.

    `server/app/tests/auth/test_trusted_proxy.py` — 3 integration tests via ASGI client. Inject `X-Forwarded-For` header and (since ASGI test client peer is 127.0.0.1) configure settings to allow 127.0.0.1 in allowlist using `monkeypatch`. Verify:
    - `test_xff_used_when_peer_trusted`: trust_proxy=True + cidrs=['127.0.0.0/8'], login fails 10x with XFF=1.2.3.4 → rate-limit row in login_attempts.ip = '1.2.3.4'.
    - `test_xff_ignored_when_untrusted_peer`: trust_proxy=True + cidrs=['10.0.0.0/8'] (does NOT include 127.0.0.1), login → row.ip = '127.0.0.1' (peer wins).
    - `test_rate_limit_keys_on_xff_when_trusted`: 10 failed logins with XFF=1.2.3.4, 11th with XFF=1.2.3.4 → 429; an immediate login with XFF=5.6.7.8 → NOT rate-limited.

    For trusted_proxy tests, monkey-patch `settings.smartcopilot_trust_proxy` and `settings.smartcopilot_trusted_proxy_cidrs`. The middleware reads these at app construction (`add_middleware`); for testing, you may need to rebuild the app within the test using a helper:
    ```python
    def _build_app(trust: bool, cidrs: list[str]):
        from fastapi import FastAPI
        from app.auth.middleware import TrustedProxyMiddleware
        from app.routes.auth import router as auth_router
        from app.routes.admin import router as admin_router
        a = FastAPI()
        a.add_middleware(TrustedProxyMiddleware, trust_proxy=trust, allowlist_cidrs=cidrs)
        a.include_router(auth_router); a.include_router(admin_router)
        return a
    ```
  </action>
  <acceptance_criteria>
    - All 4 test files have stubs replaced: `for f in test_login test_admin_reauth test_audit_log test_trusted_proxy; do ! grep -q 'pytest.skip("Wave 0 stub' server/app/tests/auth/$f.py || { echo "$f still stubbed"; exit 1; }; done` exits 0
    - `cd server && pytest -x -q app/tests/auth/test_login.py app/tests/auth/test_admin_reauth.py app/tests/auth/test_audit_log.py app/tests/auth/test_trusted_proxy.py` exits 0
    - Test count: at least 9 (login) + 7 (admin_reauth) + 4 (audit_log) + 3 (trusted_proxy) = 23 passing
    - `cd server && ruff check app/tests/auth/` exits 0
  </acceptance_criteria>
  <done>23 integration tests pass against testcontainer; covers AUTH-02 / AUTH-03 / AUTH-06 / AUTH-07 / AUTH-08 end-to-end.</done>
  <threat_ref>T-1b-04</threat_ref>
</task>

<task type="auto">
  <id>07-07</id>
  <name>Task 7: app/mcp stub — minimal module so supervisord priority 30 can import (D-21 / WARNING #9)</name>
  <read_first>
    - server/app/auth/core.py (Plan 05 task 05-01 — validate_bearer is the symbol the stub references; full SDK wiring is Phase 1d)
    - .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md D-21 (MCP HTTP shares auth_core by import — not by HTTP callback)
  </read_first>
  <action>
    D-21 says "MCP HTTP shares auth_core by import" and supervisord priority 30 launches
    `python -m app.mcp.server --http`. Without a `server/app/mcp/` package the supervisord
    process crashes on every container boot. Phase 1d wires the actual MCP SDK; Phase 1b
    only needs the importable seam so the boot path doesn't fall over.

    Create `server/app/mcp/__init__.py` — single line:
    ```python
    """MCP transport surface. Phase 1b: stub for D-21 imports. Full SDK wiring in Phase 1d."""
    ```

    Create `server/app/mcp/server.py`:
    ```python
    """MCP HTTP / stdio entry point.

    Phase 1b: minimal stub. Imports `validate_bearer` from app.auth.core to prove
    the D-21 "MCP HTTP shares auth_core by import" seam is in place. Phase 1d wires
    the actual MCP SDK + AuthSettings + Streamable HTTP server.

    Supervisord priority 30 invokes:
        python -m app.mcp.server --http
    Until Phase 1d ships, that exits non-zero with NotImplementedError — which
    is the desired behavior (the MCP HTTP process is not part of the Phase 1b
    success criteria; it must just not break the container BUILD/IMPORT).
    """
    from __future__ import annotations

    from app.auth.core import validate_bearer  # noqa: F401 — D-21 seam


    def main_http() -> int:
        raise NotImplementedError("Phase 1d wires MCP SDK")


    def main_stdio() -> int:
        raise NotImplementedError("Phase 1d wires MCP SDK")


    if __name__ == "__main__":
        import sys
        sys.exit(main_http())
    ```

    Note: `__main__` invocation calls `main_http`, which raises `NotImplementedError`.
    Supervisord will see a non-zero exit; mark this program with `autorestart=false`
    OR `startsecs=0` in supervisord.conf so it doesn't crash-loop. (Phase 1a left
    a stub for the mcp-http program; the supervisord change to mark it as
    "don't restart in 1b" is captured in the Phase 1a SUMMARY for reference —
    if not yet captured, leave the existing `autorestart=true` and accept the
    crash-loop — it doesn't affect Phase 1b acceptance because no test starts
    the supervisord stack; the integration tests run pytest directly.)
  </action>
  <acceptance_criteria>
    - `test -f server/app/mcp/__init__.py && test -f server/app/mcp/server.py`
    - **Module imports cleanly (D-21 seam):** `cd server && python -c "from app.mcp.server import main_http"` exits 0
    - **validate_bearer reference present (D-21 invariant):** `grep -q "validate_bearer" server/app/mcp/server.py` returns 0
    - **NotImplementedError in body:** `grep -q "NotImplementedError" server/app/mcp/server.py` returns 0
    - `cd server && ruff check app/mcp/` exits 0
  </acceptance_criteria>
  <done>D-21 stub exists; importable; references validate_bearer; main_http raises NotImplementedError so Phase 1d can swap in the real SDK without changing the import surface.</done>
</task>

</tasks>

<verification>
  <command>cd server && ruff check app/ && pytest -x -q app/tests/auth/ app/tests/integration/</command>
  <expected>All Phase 1b auth tests pass (~50 tests); all Phase 1a integration tests pass (7 tests); ruff clean across all of app/.</expected>
</verification>

<must_haves>

## Truths
- main.py:create_app fails-fast (sys.exit(1)) when SMARTCOPILOT_FERNET_KEY or JWT_SIGNING_KEY is empty (Phase 1b success criterion #4 verified at Plan 08).
- main.py mounts TrustedProxyMiddleware → routes (in that order).
- structlog redaction processor (D-27) configured at lifespan startup.
- /auth/login: rate-limit-then-record-then-verify; rate_limited envelope includes retry_after_seconds (D-07).
- /auth/refresh: atomic rotate-and-revoke; replay = 401 invalid_token (D-03 + theft signal); audit_log entries (D-26).
- /api/v1/admin/reauth: re-validates password via argon2; stamps admin_fresh_until = now() + 60min (D-12); audit_log on success and failure (D-25).
- /api/v1/admin/_demo_destructive: requires Depends(require_fresh_auth); returns D-16 envelope on failure (D-15).
- TrustedProxyMiddleware honors D-29 left-most-XFF rule.
- prune_login_attempts deletes rows older than retention_hours; module-level coroutine (APScheduler-pickle-safe).

## Artifacts
- `server/app/auth/middleware.py`, `server/app/routes/auth.py`, `server/app/routes/admin.py`, `server/app/main.py` (extended).
- `server/app/scheduler/jobs/__init__.py`, `server/app/scheduler/jobs/prune_login_attempts.py`.
- 6 implemented integration test files (Wave-0 → real tests).

## Key Links
- `main.py` → `fernet()` (Plan 03 fail-on-startup) + `configure_logging()` (Plan 01 redaction) + `TrustedProxyMiddleware` (this plan) + 3 routers.
- `routes/auth.py:login` → `services.sessions.{check_rate_limit, record_login_attempt, wipe_login_attempts, issue_session_pair}` (Plan 06).
- `routes/admin.py:_demo_destructive` → `Depends(require_fresh_auth)` (Plan 06) → `sessions.admin_fresh_until` (Plan 02).

</must_haves>

<output>
Append per-task rows to `.planning/phases/01b-auth-security-primitives/01B-VALIDATION.md`. Create `01B-07-SUMMARY.md` documenting the HTTP surface, startup-fail wiring, and Wave-0 → integration replacement count.
</output>
