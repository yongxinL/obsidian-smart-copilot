"""POST /api/v1/search — page-level FTS via pages.search_vector (D-01, D-02)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import OperationContext
from app.auth.deps import require_user
from app.dependencies import get_db_session
from app.services.pages import search_pages_fts
from app.services.vault_resolver import VaultNotFound, resolve_user_vault_id

router = APIRouter(prefix="/api/v1", tags=["search"])


class SearchIn(BaseModel):
    query: str = Field(..., min_length=1, max_length=512)
    limit: int = Field(default=20, ge=1, le=100)
    namespace: Literal["private", "shared", "all"] = "private"


class SearchResultItem(BaseModel):
    slug: str
    title: str | None
    note_type: str
    score: float
    snippet: str
    matched_fields: list[str]
    page_id: uuid.UUID
    updated_at: datetime
    chunk_hits: list = Field(default_factory=list)  # forward-compat: Phase 2a fills this


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    total: int
    query: str
    search_type: str = "fts_v1"  # D-02 forward-compat hook


@router.post("/search", response_model=SearchResponse)
async def search_endpoint(
    payload: SearchIn,
    ctx: OperationContext = Depends(require_user),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> SearchResponse:
    try:
        vault_id = await resolve_user_vault_id(session, ctx.user_id)
    except VaultNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": str(exc)}},
        ) from None
    try:
        hits = await search_pages_fts(
            session, ctx,
            vault_id=vault_id, query=payload.query,
            limit=payload.limit, namespace=payload.namespace,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "validation_error", "message": str(exc)}},
        ) from None
    items = [
        SearchResultItem(
            slug=h.slug, title=h.title, note_type=h.note_type,
            score=h.score, snippet=h.snippet, matched_fields=h.matched_fields,
            page_id=h.page_id, updated_at=h.updated_at, chunk_hits=getattr(h, "chunk_hits", []),
        )
        for h in hits
    ]
    return SearchResponse(results=items, total=len(items), query=payload.query)