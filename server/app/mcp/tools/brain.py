"""Real Phase 1d MCP brain.* tool implementations (D-04, D-06).

Transport-agnostic: every tool calls services/ via session_with_rls(ctx).
MCP tools call resolve_user_vault_id() from services/vault_resolver.py (NOT
a private helper) — REST-06 invariant.

DetachedInstanceError mitigation: capture primitive attributes into local
variables BEFORE the session-with-rls block exits. ORM objects must never
be referenced after the session closes.
"""
from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any, Literal

import structlog

from app.auth.context import OperationContext
from app.dependencies import session_with_rls
from app.services.pages import (
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
    search_pages_fts,
    soft_delete_page,
    upsert_page,
    vault_health,
    vault_stats,
    write_page,
)
from app.services.vault_resolver import VaultNotFound, resolve_user_vault_id
from app.vault.paths import validate_slug

log = structlog.get_logger("smart_copilot.mcp.brain")


def _err(code: str, message: str, **details: Any) -> dict:
    """Structured error dict matching D-05 convention."""
    payload: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details:
        payload["error"]["details"] = details
    return payload


def register(mcp: Any, ctx_factory: Callable[..., OperationContext]) -> None:
    """Register all 14 Phase 1d brain.* MCP tools."""

    # ------------------------------------------------------------------
    # brain.put — write a page to the user's private vault
    # ------------------------------------------------------------------

    @mcp.tool(
        name="brain.put",
        description="Write a page to the user's private vault. "
        "Content is a full vault markdown file (YAML frontmatter, "
        "compiled_truth, timeline). Phase 1d supports private namespace only.",
    )
    async def brain_put(
        slug: str,
        content: str,
        namespace: Literal["private"] = "private",
    ) -> dict:
        ctx = ctx_factory()
        if ctx.remote:
            try:
                validate_slug(slug)
            except ValueError as exc:
                return _err("validation_error", str(exc))

        slug_out: str | None = None
        page_id_out: uuid.UUID | None = None
        version_out: int = 1

        try:
            async for session in session_with_rls(ctx):
                try:
                    vault_id = await resolve_user_vault_id(session, ctx.user_id)
                    page = await write_page(
                        session, ctx,
                        slug=slug,
                        raw_content=content.encode("utf-8"),
                        vault_id=vault_id,
                    )
                    slug_out = page.slug
                    page_id_out = page.id
                    await session.commit()
                except VaultNotFound as exc:
                    return _err("not_found", str(exc))
                except TimelineViolation as exc:
                    return _err("timeline_violation", str(exc))
                except SharedVaultWriteDenied as exc:
                    return _err("forbidden", str(exc))

            # Separate session for version lookup (must capture primitives inside block)
            async for session in session_with_rls(ctx):
                history = await get_page_history(session, ctx, page_id=page_id_out)
                version_out = history[0].version if history else 1
        except Exception as exc:  # noqa: BLE001
            log.exception("brain_put_failed", slug=slug)
            return _err("internal_error", str(exc))

        return {
            "slug": slug_out,
            "page_id": str(page_id_out),
            "version": version_out,
            "status": "ok",
        }

    # ------------------------------------------------------------------
    # brain.get — read a page from the user's vault
    # ------------------------------------------------------------------

    @mcp.tool(
        name="brain.get",
        description="Read a page by slug from the user's vault. "
        "Returns title, note_type, frontmatter, compiled_truth, timeline, "
        "content_hash, and updated_at.",
    )
    async def brain_get(slug: str) -> dict:
        ctx = ctx_factory()
        if ctx.remote:
            try:
                validate_slug(slug)
            except ValueError as exc:
                return _err("validation_error", str(exc))

        page_id_out: uuid.UUID | None = None

        async for session in session_with_rls(ctx):
            try:
                vault_id = await resolve_user_vault_id(session, ctx.user_id)
                page = await read_page(session, vault_id=vault_id, slug=slug)
                title = page.frontmatter.get("title") if page.frontmatter else None
                return {
                    "slug": page.slug,
                    "page_id": str(page.id),
                    "title": title,
                    "note_type": page.note_type,
                    "frontmatter": dict(page.frontmatter) if page.frontmatter else {},
                    "compiled_truth": page.compiled_truth or "",
                    "timeline": page.timeline or "",
                    "content_hash": page.content_hash,
                    "updated_at": page.updated_at.isoformat() if page.updated_at else None,
                }
            except PageNotFound:
                return _err("not_found", f"Page {slug!r} not found")
            except VaultNotFound as exc:
                return _err("not_found", str(exc))

        return _err("internal_error", "session loop exited without result")

    # ------------------------------------------------------------------
    # brain.search — full-text search in the user's vault
    # ------------------------------------------------------------------

    @mcp.tool(
        name="brain.search",
        description="Full-text search via PostgreSQL websearch_to_tsquery + GIN index. "
        "Returns results with score, snippet, and matched_fields. "
        "Phase 1d: page-level only (no chunk-level results).",
    )
    async def brain_search(
        query: str,
        limit: int = 20,
        namespace: Literal["private", "shared", "all"] = "private",
    ) -> dict:
        ctx = ctx_factory()
        if not query or not query.strip():
            return _err("validation_error", "query must be non-empty")

        limit = max(1, min(int(limit), 100))

        async for session in session_with_rls(ctx):
            try:
                vault_id = await resolve_user_vault_id(session, ctx.user_id)
                hits = await search_pages_fts(
                    session, ctx,
                    vault_id=vault_id,
                    query=query,
                    limit=limit,
                    namespace=namespace,
                )
                results = [
                    {
                        "slug": h.slug,
                        "title": h.title,
                        "note_type": h.note_type or "unknown",
                        "score": h.score,
                        "snippet": h.snippet,
                        "matched_fields": h.matched_fields,
                        "page_id": str(h.page_id),
                        "updated_at": h.updated_at.isoformat() if h.updated_at else None,
                        "chunk_hits": [],
                    }
                    for h in hits
                ]
                return {
                    "results": results,
                    "total": len(results),
                    "query": query,
                    "search_type": "fts_v1",
                }
            except ValueError as exc:
                return _err("validation_error", str(exc))
            except VaultNotFound as exc:
                return _err("not_found", str(exc))

        return _err("internal_error", "session loop exited without result")

    # ------------------------------------------------------------------
    # brain.list — paginated page listing in the user's vault
    # ------------------------------------------------------------------

    @mcp.tool(
        name="brain.list",
        description="List pages in the user's vault with pagination. "
        "Returns slug, title, note_type, and updated_at per page.",
    )
    async def brain_list(limit: int = 50, offset: int = 0) -> dict:
        ctx = ctx_factory()
        limit = max(1, min(int(limit), 200))
        offset = max(0, int(offset))

        async for session in session_with_rls(ctx):
            try:
                vault_id = await resolve_user_vault_id(session, ctx.user_id)
                pages = await list_pages(
                    session, ctx,
                    vault_id=vault_id,
                    limit=limit,
                    offset=offset,
                )
                return {
                    "pages": [
                        {
                            "slug": p.slug,
                            "title": p.frontmatter.get("title") if p.frontmatter else None,
                            "note_type": p.note_type,
                            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                        }
                        for p in pages
                    ],
                    "total": len(pages),
                }
            except VaultNotFound as exc:
                return _err("not_found", str(exc))

        return _err("internal_error", "session loop exited without result")

    # ------------------------------------------------------------------
    # brain.delete — soft-delete a page from the user's vault
    # ------------------------------------------------------------------

    @mcp.tool(
        name="brain.delete",
        description="Soft-delete a page by slug. Sets deleted_at, deleted_by, "
        "and delete_reason. Emits an index_event (event_type='deleted').",
    )
    async def brain_delete(slug: str) -> dict:
        ctx = ctx_factory()
        if ctx.remote:
            try:
                validate_slug(slug)
            except ValueError as exc:
                return _err("validation_error", str(exc))

        page_id_out: uuid.UUID | None = None

        async for session in session_with_rls(ctx):
            try:
                vault_id = await resolve_user_vault_id(session, ctx.user_id)
                page = await read_page(session, vault_id=vault_id, slug=slug)
                page_id_out = page.id
                await soft_delete_page(session, ctx, page_id=page.id)
                await session.commit()
            except PageNotFound:
                return _err("not_found", f"Page {slug!r} not found")
            except VaultNotFound as exc:
                return _err("not_found", str(exc))

        return {
            "slug": slug,
            "page_id": str(page_id_out),
            "status": "deleted",
        }

    # ------------------------------------------------------------------
    # brain.history — version history for a page
    # ------------------------------------------------------------------

    @mcp.tool(
        name="brain.history",
        description="Return all version snapshots for a page, newest first. "
        "Each entry has version number, content_hash, and created_at.",
    )
    async def brain_history(slug: str) -> dict:
        ctx = ctx_factory()
        if ctx.remote:
            try:
                validate_slug(slug)
            except ValueError as exc:
                return _err("validation_error", str(exc))

        page_id_out: uuid.UUID | None = None

        async for session in session_with_rls(ctx):
            try:
                vault_id = await resolve_user_vault_id(session, ctx.user_id)
                page = await read_page(session, vault_id=vault_id, slug=slug)
                page_id_out = page.id
                history = await get_page_history(session, ctx, page_id=page.id)
            except PageNotFound:
                return _err("not_found", f"Page {slug!r} not found")
            except VaultNotFound as exc:
                return _err("not_found", str(exc))

        return {
            "page_id": str(page_id_out),
            "slug": slug,
            "versions": [
                {
                    "version": h.version,
                    "content_hash": h.content_hash,
                    "created_at": h.created_at.isoformat() if h.created_at else None,
                }
                for h in history
            ],
        }

    # ------------------------------------------------------------------
    # brain.diff — unified diff between two versions
    # ------------------------------------------------------------------

    @mcp.tool(
        name="brain.diff",
        description="Compute unified diffs (compiled_truth and timeline) between "
        "two version snapshots of a page. from_version and to_version are "
        "1-indexed version numbers.",
    )
    async def brain_diff(slug: str, from_version: int, to_version: int) -> dict:
        ctx = ctx_factory()
        if ctx.remote:
            try:
                validate_slug(slug)
            except ValueError as exc:
                return _err("validation_error", str(exc))

        page_id_out: uuid.UUID | None = None

        async for session in session_with_rls(ctx):
            try:
                vault_id = await resolve_user_vault_id(session, ctx.user_id)
                page = await read_page(session, vault_id=vault_id, slug=slug)
                page_id_out = page.id
                diff = await get_page_diff(
                    session, ctx,
                    page_id=page.id,
                    from_version=from_version,
                    to_version=to_version,
                )
            except PageNotFound as exc:
                return _err("not_found", str(exc))
            except VaultNotFound as exc:
                return _err("not_found", str(exc))

        return {
            "page_id": str(page_id_out),
            "slug": slug,
            "from_version": diff.from_version,
            "to_version": diff.to_version,
            "compiled_truth_diff": diff.compiled_truth_diff,
            "timeline_diff": diff.timeline_diff,
        }

    # ------------------------------------------------------------------
    # brain.revert — restore page to a prior version
    # ------------------------------------------------------------------

    @mcp.tool(
        name="brain.revert",
        description="Restore a page to the content of a prior version snapshot. "
        "The revert is service-controlled; the historic version is preserved "
        "as a new entry in the version history.",
    )
    async def brain_revert(slug: str, target_version: int) -> dict:
        ctx = ctx_factory()
        if ctx.remote:
            try:
                validate_slug(slug)
            except ValueError as exc:
                return _err("validation_error", str(exc))

        page_id_out: uuid.UUID | None = None
        new_version_out: int = 1

        async for session in session_with_rls(ctx):
            try:
                vault_id = await resolve_user_vault_id(session, ctx.user_id)
                page = await revert_page(
                    session, ctx,
                    vault_id=vault_id,
                    slug=slug,
                    target_version=target_version,
                )
                page_id_out = page.id
                await session.commit()
                history = await get_page_history(session, ctx, page_id=page.id)
                new_version_out = history[0].version if history else 1
            except PageNotFound as exc:
                return _err("not_found", str(exc))
            except VaultNotFound as exc:
                return _err("not_found", str(exc))

        return {
            "slug": slug,
            "page_id": str(page_id_out),
            "reverted_to": target_version,
            "new_version": new_version_out,
        }

    # ------------------------------------------------------------------
    # brain.append_timeline — append an entry to the page timeline
    # ------------------------------------------------------------------

    @mcp.tool(
        name="brain.append_timeline",
        description="Append a timeline entry to an existing page. "
        "The timeline is append-only; existing entries are never modified.",
    )
    async def brain_append_timeline(slug: str, entry: str) -> dict:
        ctx = ctx_factory()
        if ctx.remote:
            try:
                validate_slug(slug)
            except ValueError as exc:
                return _err("validation_error", str(exc))

        async for session in session_with_rls(ctx):
            try:
                vault_id = await resolve_user_vault_id(session, ctx.user_id)
                await append_timeline(
                    session, ctx,
                    vault_id=vault_id,
                    slug=slug,
                    entry=entry,
                )
                await session.commit()
            except PageNotFound:
                return _err("not_found", f"Page {slug!r} not found")
            except VaultNotFound as exc:
                return _err("not_found", str(exc))

        return {"slug": slug, "status": "appended"}

    # ------------------------------------------------------------------
    # brain.update_compiled_truth — rewrite the compiled truth section
    # ------------------------------------------------------------------

    @mcp.tool(
        name="brain.update_compiled_truth",
        description="Rewrite the compiled_truth section of a page. "
        "The timeline is preserved intact (append-only). "
        "Use this to update the user's current understanding of the topic.",
    )
    async def brain_update_compiled_truth(slug: str, compiled_truth: str) -> dict:
        ctx = ctx_factory()
        if ctx.remote:
            try:
                validate_slug(slug)
            except ValueError as exc:
                return _err("validation_error", str(exc))

        from app.vault.parser import ParsedPage

        slug_out: str | None = None
        page_id_out: uuid.UUID | None = None

        async for session in session_with_rls(ctx):
            try:
                vault_id = await resolve_user_vault_id(session, ctx.user_id)
                page = await read_page(session, vault_id=vault_id, slug=slug)
                slug_out = page.slug
                page_id_out = page.id

                # Build ParsedPage with new compiled_truth, preserve timeline
                parsed = ParsedPage(
                    frontmatter=dict(page.frontmatter) if page.frontmatter else {},
                    compiled_truth=compiled_truth,
                    timeline=page.timeline or "",
                    body_shape=page.frontmatter.get("_body_shape", "compiled_truth_only") if page.frontmatter else "compiled_truth_only",
                    content_hash=page.content_hash,
                )
                await upsert_page(
                    session, ctx,
                    vault_id=vault_id,
                    slug=slug,
                    parsed=parsed,
                    enforce_timeline=False,  # preserve timeline; service-controlled
                )
                await session.commit()
            except PageNotFound:
                return _err("not_found", f"Page {slug!r} not found")
            except VaultNotFound as exc:
                return _err("not_found", str(exc))

        return {"slug": slug_out, "page_id": str(page_id_out), "status": "ok"}

    # ------------------------------------------------------------------
    # brain.backlinks — incoming links to a page
    # ------------------------------------------------------------------

    @mcp.tool(
        name="brain.backlinks",
        description="Return all live pages that link to the target page via "
        "_resolved_links in frontmatter.",
    )
    async def brain_backlinks(slug: str) -> dict:
        ctx = ctx_factory()
        if ctx.remote:
            try:
                validate_slug(slug)
            except ValueError as exc:
                return _err("validation_error", str(exc))

        target_page_id_out: uuid.UUID | None = None

        async for session in session_with_rls(ctx):
            try:
                vault_id = await resolve_user_vault_id(session, ctx.user_id)
                page = await read_page(session, vault_id=vault_id, slug=slug)
                target_page_id_out = page.id
                backlinks = await get_backlinks_for_page(
                    session, ctx,
                    vault_id=vault_id,
                    target_page_id=page.id,
                )
            except PageNotFound:
                return _err("not_found", f"Page {slug!r} not found")
            except VaultNotFound as exc:
                return _err("not_found", str(exc))

        return {
            "target_page_id": str(target_page_id_out),
            "backlinks": [
                {
                    "page_id": str(b.page_id),
                    "slug": b.slug,
                    "title": b.title,
                }
                for b in backlinks
            ],
        }

    # ------------------------------------------------------------------
    # brain.stats — vault-level statistics
    # ------------------------------------------------------------------

    @mcp.tool(
        name="brain.stats",
        description="Return vault-level aggregate statistics: live page count, "
        "deleted page count, total compiled_truth bytes, and last updated_at.",
    )
    async def brain_stats() -> dict:
        ctx = ctx_factory()

        async for session in session_with_rls(ctx):
            try:
                vault_id = await resolve_user_vault_id(session, ctx.user_id)
                stats = await vault_stats(session, ctx, vault_id=vault_id)
            except VaultNotFound as exc:
                return _err("not_found", str(exc))

        return {
            "vault_id": str(vault_id),
            "page_count": stats.live_pages,
            "deleted_page_count": stats.deleted_pages,
            "total_compiled_truth_bytes": stats.total_bytes,
            "last_indexed_at": (
                stats.last_updated_at.isoformat() if stats.last_updated_at else None
            ),
        }

    # ------------------------------------------------------------------
    # brain.health — container health check
    # ------------------------------------------------------------------

    @mcp.tool(
        name="brain.health",
        description="Return container health: DB connection, Fernet key status, "
        "and watchdog alive (None in Phase 1d until pg_notify integration in Plan 04).",
    )
    async def brain_health() -> dict:
        ctx = ctx_factory()

        async for session in session_with_rls(ctx):
            health = await vault_health(session, ctx)

        return {
            "db_ok": health.db_ok,
            "fernet_ok": health.fernet_ok,
            "watchdog_alive": health.watchdog_alive,
        }