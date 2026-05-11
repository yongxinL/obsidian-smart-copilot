"""Phase 1d Page CRUD REST routes (D-10) — REST-01 parity with MCP brain.* tools.

CLAUDE.md: routes are thin (validate -> service -> response model); services
take OperationContext + AsyncSession (no FastAPI types). Error envelope per
REST-04 / main.py:_flatten_http_error.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import xxhash
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import OperationContext
from app.auth.deps import require_user
from app.dependencies import get_db_session
from app.services.pages import (
    PageDiff,
    PageNotFound,
    SharedVaultWriteDenied,
    TimelineViolation,
    append_timeline,
    get_backlinks_for_page,
    get_page_diff,
    get_page_history,
    list_pages,
    read_page,
    revert_page,
    soft_delete_page,
    upsert_page,
    write_page,
)
from app.services.vault_resolver import VaultNotFound, resolve_user_vault_id
from app.vault.parser import ParsedPage

router = APIRouter(prefix="/api/v1/pages", tags=["pages"])


# ── Response models ───────────────────────────────────────────────────────────
class PageOut(BaseModel):
    page_id: uuid.UUID
    slug: str
    title: str | None
    note_type: str
    type: str
    frontmatter: dict
    compiled_truth: str | None
    timeline: str | None
    content_hash: str
    updated_at: datetime


class PageWriteIn(BaseModel):
    content: str = Field(..., min_length=0, max_length=10_000_000)


class PageWriteOut(BaseModel):
    slug: str
    page_id: uuid.UUID
    version: int
    status: str = "ok"


class PageListOut(BaseModel):
    pages: list[PageOut]
    total: int


class TimelineAppendIn(BaseModel):
    entry: str = Field(..., min_length=1, max_length=10_000)


class CompiledTruthIn(BaseModel):
    compiled_truth: str = Field(..., min_length=0, max_length=10_000_000)


class HistoryItem(BaseModel):
    version: int
    content_hash: str
    created_at: datetime


class HistoryOut(BaseModel):
    page_id: uuid.UUID
    slug: str
    versions: list[HistoryItem]


class DiffOut(BaseModel):
    page_id: uuid.UUID
    slug: str
    from_version: int
    to_version: int
    compiled_truth_diff: str
    timeline_diff: str


class RevertIn(BaseModel):
    target_version: int = Field(..., ge=1)


class BacklinkOut(BaseModel):
    page_id: uuid.UUID
    slug: str
    title: str | None


class BacklinksResponse(BaseModel):
    target_page_id: uuid.UUID
    backlinks: list[BacklinkOut]


def _page_to_out(page) -> PageOut:  # noqa: ANN001
    return PageOut(
        page_id=page.id, slug=page.slug,
        title=(page.frontmatter or {}).get("title"),
        note_type=page.note_type, type=page.type,
        frontmatter=page.frontmatter or {},
        compiled_truth=page.compiled_truth, timeline=page.timeline,
        content_hash=page.content_hash, updated_at=page.updated_at,
    )


def _http_error(status_code: int, code: str, message: str, **details) -> HTTPException:
    detail = {"error": {"code": code, "message": message}}
    if details:
        detail["error"]["details"] = details
    return HTTPException(status_code=status_code, detail=detail)


# ── Endpoints ────────────────────────────────────────────────────────────────
@router.get("", response_model=PageListOut)
async def list_pages_endpoint(
    limit: int = 50,
    offset: int = 0,
    ctx: OperationContext = Depends(require_user),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> PageListOut:
    try:
        vault_id = await resolve_user_vault_id(session, ctx.user_id)
    except VaultNotFound as exc:
        raise _http_error(404, "not_found", str(exc)) from None
    pages = await list_pages(session, ctx, vault_id=vault_id, limit=limit, offset=offset)
    return PageListOut(pages=[_page_to_out(p) for p in pages], total=len(pages))


@router.get("/{slug}", response_model=PageOut)
async def read_page_endpoint(
    slug: str,
    ctx: OperationContext = Depends(require_user),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> PageOut:
    try:
        vault_id = await resolve_user_vault_id(session, ctx.user_id)
        page = await read_page(session, vault_id=vault_id, slug=slug)
    except (VaultNotFound, PageNotFound) as exc:
        raise _http_error(404, "not_found", str(exc)) from None
    return _page_to_out(page)


@router.put("/{slug}", response_model=PageWriteOut)
async def put_page_endpoint(
    slug: str,
    payload: PageWriteIn,
    ctx: OperationContext = Depends(require_user),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> PageWriteOut:
    try:
        vault_id = await resolve_user_vault_id(session, ctx.user_id)
        page = await write_page(
            session, ctx,
            slug=slug, raw_content=payload.content.encode("utf-8"),
            vault_id=vault_id,
        )
        await session.commit()
    except VaultNotFound as exc:
        raise _http_error(404, "not_found", str(exc)) from None
    except TimelineViolation as exc:
        raise _http_error(422, "timeline_violation", str(exc)) from None
    except SharedVaultWriteDenied as exc:
        raise _http_error(403, "forbidden", str(exc)) from None
    except ValueError as exc:  # validate_slug
        raise _http_error(422, "validation_error", str(exc)) from None
    history = await get_page_history(session, ctx, page_id=page.id)
    return PageWriteOut(slug=page.slug, page_id=page.id, version=history[0].version if history else 1)


@router.delete("/{slug}")
async def delete_page_endpoint(
    slug: str,
    ctx: OperationContext = Depends(require_user),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> dict:
    try:
        vault_id = await resolve_user_vault_id(session, ctx.user_id)
        page = await read_page(session, vault_id=vault_id, slug=slug)
        await soft_delete_page(session, ctx, page_id=page.id, reason="api_delete")
        await session.commit()
    except (VaultNotFound, PageNotFound) as exc:
        raise _http_error(404, "not_found", str(exc)) from None
    return {"slug": slug, "page_id": str(page.id), "status": "deleted"}


@router.post("/{slug}/timeline")
async def append_timeline_endpoint(
    slug: str,
    payload: TimelineAppendIn,
    ctx: OperationContext = Depends(require_user),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> dict:
    try:
        vault_id = await resolve_user_vault_id(session, ctx.user_id)
        page = await append_timeline(session, ctx, vault_id=vault_id, slug=slug, entry=payload.entry)
        await session.commit()
    except (VaultNotFound, PageNotFound) as exc:
        raise _http_error(404, "not_found", str(exc)) from None
    return {"slug": page.slug, "page_id": str(page.id), "status": "appended"}


@router.put("/{slug}/compiled_truth")
async def update_compiled_truth_endpoint(
    slug: str,
    payload: CompiledTruthIn,
    ctx: OperationContext = Depends(require_user),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> dict:
    try:
        vault_id = await resolve_user_vault_id(session, ctx.user_id)
        page = await read_page(session, vault_id=vault_id, slug=slug)
    except (VaultNotFound, PageNotFound) as exc:
        raise _http_error(404, "not_found", str(exc)) from None
    new_truth = payload.compiled_truth
    new_content = (new_truth + "\n---\n" + (page.timeline or "")).encode("utf-8")
    new_hash = xxhash.xxh64(new_content).hexdigest()
    parsed = ParsedPage(
        frontmatter=dict(page.frontmatter or {}),
        compiled_truth=new_truth, timeline=page.timeline or "",
        body_shape=None,  # type: ignore[arg-type]
        content_hash=new_hash,
    )
    new_page = await upsert_page(
        session, ctx, vault_id=vault_id, slug=slug, parsed=parsed,
        enforce_timeline=False,
    )
    await session.commit()
    return {"slug": new_page.slug, "page_id": str(new_page.id), "status": "ok"}


@router.get("/{slug}/history", response_model=HistoryOut)
async def page_history_endpoint(
    slug: str,
    ctx: OperationContext = Depends(require_user),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> HistoryOut:
    try:
        vault_id = await resolve_user_vault_id(session, ctx.user_id)
        page = await read_page(session, vault_id=vault_id, slug=slug)
    except (VaultNotFound, PageNotFound) as exc:
        raise _http_error(404, "not_found", str(exc)) from None
    versions = await get_page_history(session, ctx, page_id=page.id)
    return HistoryOut(page_id=page.id, slug=page.slug,
                      versions=[HistoryItem(version=v.version, content_hash=v.content_hash, created_at=v.created_at) for v in versions])


@router.get("/{slug}/diff", response_model=DiffOut)
async def page_diff_endpoint(
    slug: str,
    from_version: int,
    to_version: int,
    ctx: OperationContext = Depends(require_user),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> DiffOut:
    try:
        vault_id = await resolve_user_vault_id(session, ctx.user_id)
        page = await read_page(session, vault_id=vault_id, slug=slug)
        diff = await get_page_diff(session, ctx, page_id=page.id, from_version=from_version, to_version=to_version)
    except (VaultNotFound, PageNotFound) as exc:
        raise _http_error(404, "not_found", str(exc)) from None
    return DiffOut(page_id=page.id, slug=page.slug, from_version=diff.from_version, to_version=diff.to_version, compiled_truth_diff=diff.compiled_truth_diff, timeline_diff=diff.timeline_diff)


@router.post("/{slug}/revert")
async def page_revert_endpoint(
    slug: str,
    payload: RevertIn,
    ctx: OperationContext = Depends(require_user),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> dict:
    try:
        vault_id = await resolve_user_vault_id(session, ctx.user_id)
        page = await revert_page(session, ctx, vault_id=vault_id, slug=slug, target_version=payload.target_version)
        await session.commit()
    except (VaultNotFound, PageNotFound) as exc:
        raise _http_error(404, "not_found", str(exc)) from None
    history = await get_page_history(session, ctx, page_id=page.id)
    return {"slug": page.slug, "page_id": str(page.id), "reverted_to": payload.target_version, "new_version": history[0].version}


@router.get("/{slug}/backlinks", response_model=BacklinksResponse)
async def backlinks_endpoint(
    slug: str,
    ctx: OperationContext = Depends(require_user),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> BacklinksResponse:
    try:
        vault_id = await resolve_user_vault_id(session, ctx.user_id)
        page = await read_page(session, vault_id=vault_id, slug=slug)
    except (VaultNotFound, PageNotFound) as exc:
        raise _http_error(404, "not_found", str(exc)) from None
    hits = await get_backlinks_for_page(session, ctx, vault_id=vault_id, target_page_id=page.id)
    return BacklinksResponse(
        target_page_id=page.id,
        backlinks=[BacklinkOut(page_id=h.page_id, slug=h.slug, title=h.title) for h in hits],
    )