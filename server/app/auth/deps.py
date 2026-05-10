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

from datetime import UTC, datetime

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
    ctx: OperationContext = Depends(get_operation_context),  # noqa: B008
) -> OperationContext:
    """Any authenticated request — placeholder gate so handlers can opt-in explicitly."""
    return ctx


async def require_admin(
    ctx: OperationContext = Depends(get_operation_context),  # noqa: B008
) -> OperationContext:
    if ctx.role != "admin":
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "forbidden", "message": "admin role required"}},
        )
    return ctx


async def require_fresh_auth(
    ctx: OperationContext = Depends(require_admin),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
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
    now = datetime.now(UTC)
    if s.expires_at is not None and s.expires_at < now:
        raise HTTPException(status_code=403, detail=admin_reauth_required_envelope())
    if s.admin_fresh_until is None or s.admin_fresh_until < now:
        raise HTTPException(status_code=403, detail=admin_reauth_required_envelope())
    return ctx
