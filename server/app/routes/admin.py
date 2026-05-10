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
from app.auth.deps import (
    admin_reauth_required_envelope,
    require_admin,
    require_fresh_auth,
)
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
    ctx: OperationContext = Depends(require_admin),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> dict:
    """D-12: re-validate the admin's password; stamp admin_fresh_until = now() + 60min."""
    if payload.factor != "password":
        # D-14 — reserved for future factor; reject other values explicitly
        raise HTTPException(
            status_code=501,
            detail={
                "error": {
                    "code": "not_implemented",
                    "message": "factor 'password' is the only supported value in v1",
                }
            },
        )
    if ctx.session_id is None:
        raise HTTPException(status_code=403, detail=admin_reauth_required_envelope())

    user = await get_user_by_id(session, ctx.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "unauthorized", "message": "user not found"}},
        )
    ip = getattr(request.state, "client_ip", None) or (
        request.client.host if request.client else "unknown"
    )
    if not await verify_password(user.password_hash, payload.password):
        await write_audit_log(
            session,
            ctx,
            action="admin_reauth_failed",
            target_kind="session",
            target_id=str(ctx.session_id),
            ip=ip,
            user_agent=request.headers.get("user-agent"),
        )
        await session.commit()
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "unauthorized", "message": "invalid password"}},
        )
    await set_admin_fresh(
        session, session_id=ctx.session_id, minutes=settings.admin_fresh_window_minutes
    )
    await write_audit_log(
        session,
        ctx,
        action="admin_reauth",
        target_kind="session",
        target_id=str(ctx.session_id),
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    return {
        "status": "ok",
        "freshness_window_minutes": settings.admin_fresh_window_minutes,
    }


@router.post("/_demo_destructive")
async def _demo_destructive(
    ctx: OperationContext = Depends(require_fresh_auth),  # noqa: B008
) -> dict:
    """Phase 1b proof: ANY destructive admin route uses Depends(require_fresh_auth).

    Returns 200 only when caller has fresh admin auth. Otherwise the gate raises 403 admin_reauth_required.
    Replace with real destructive routes in Phase 1d/6 — same pattern.
    """
    return {"status": "ok", "actor": str(ctx.user_id)}
