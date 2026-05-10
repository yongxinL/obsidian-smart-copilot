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

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.audit import write_audit_log
from app.auth.context import OperationContext, system_operation_context
from app.auth.password import _HASHER, verify_password
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

# D-timing: computed once at import; same argon2 params as the real hasher so the
# timing profile of a dummy verify is indistinguishable from a real password miss.
_DUMMY_HASH: str = _HASHER.hash("dummy")


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
        await session.commit()  # Landmine #9: durable before verify

    # Verify — runs under system context so the user lookup AND the immediate
    # session pair INSERT (sessions row is owned by the user; the system-bypass
    # OR clause in 0002 admits the INSERT before the user GUC is set).
    async for session in session_with_rls(_system_ctx(request, action="verify")):
        user = await get_user_by_username(session, username)
        if user is None or not user.is_active:
            # CR-01: constant-time blind — identical timing to a real password miss
            await verify_password(_DUMMY_HASH, payload.password)
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
    ctx: OperationContext = Depends(get_operation_context),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> dict:
    if ctx.session_id is not None:
        await revoke_session(session, session_id=ctx.session_id)
        await session.commit()
    return {"status": "ok"}
