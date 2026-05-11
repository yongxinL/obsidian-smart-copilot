"""Vault-level REST routes (D-11) — Phase 1d wires capabilities + index events.

Vault file ops (move/split/graph/organize) are scaffolded for Phase 5 (INTEL).
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import OperationContext
from app.auth.deps import require_user
from app.dependencies import get_db_session
from app.services.capabilities import get_capabilities

router_capabilities = APIRouter(prefix="/api/v1", tags=["capabilities"])
router_vault = APIRouter(prefix="/api/v1/vault", tags=["vault"])


@router_capabilities.get("/capabilities")
async def capabilities_endpoint() -> dict:
    """REST-05 / D-15: same payload as the capability_discovery MCP tool.

    No auth required — capability discovery is public per REST-05.
    """
    return get_capabilities()


class IndexEventItem(BaseModel):
    id: int
    event_type: str | None
    page_slug: str | None
    details: dict
    created_at: datetime


class IndexEventsOut(BaseModel):
    events: list[IndexEventItem]
    next_since: str | None


@router_vault.get("/index/events", response_model=IndexEventsOut)
async def index_events_endpoint(
    since: datetime | None = None,
    limit: int = 50,
    ctx: OperationContext = Depends(require_user),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> IndexEventsOut:
    if limit < 1 or limit > 200:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "validation_error", "message": "limit must be 1..200"}},
        )
    sql_parts = [
        "SELECT id, event_type, page_slug, details, created_at",
        "FROM index_events",
        "WHERE user_id = :uid",
    ]
    params: dict = {"uid": str(ctx.user_id), "lim": limit}
    if since is not None:
        sql_parts.append("AND created_at > :since")
        params["since"] = since
    sql_parts.append("ORDER BY created_at DESC LIMIT :lim")
    sql = "\n".join(sql_parts)
    rows = (await session.execute(text(sql), params)).mappings().all()
    events = [IndexEventItem(**dict(r)) for r in rows]
    next_since = events[0].created_at.isoformat() if events else None
    return IndexEventsOut(events=events, next_since=next_since)