"""Page CRUD service (transport-agnostic).

CLAUDE.md: no FastAPI imports; services take OperationContext + AsyncSession.
D-02: timeline append-only enforcement on API writes (enforce_timeline=True).
D-03: watchdog path bypasses enforcement (enforce_timeline=False).
D-04: note_type defaults to 'fleeting' for new pages.
D-09: wikilink resolution stored in frontmatter._resolved_links; no writes to links table.
VAULT-03: shared vault write policy enforced per settings.shared_vault_write_policy.
VAULT-07: content-hash deduplication — re-index skipped when content_hash unchanged.
VAULT-08: page_versions snapshot on every update.

Phase 1d extensions:
  - search_pages_fts: PostgreSQL FTS via websearch_to_tsquery + GIN on pages.search_vector
  - list_pages: paginated page listing by vault_id
  - get_page_history: ordered version list from page_versions
  - get_page_diff: unified diff between two versions
  - revert_page: restore a page to a prior version snapshot
  - get_backlinks_for_page: scan _resolved_links for incoming references
  - vault_stats: counts and byte-size for a vault
  - vault_health: DB/fernet/watchdog status
"""

from __future__ import annotations

import difflib
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import OperationContext
from app.encryption import FernetKeyMissing, fernet
from app.models.index_event import IndexEvent
from app.models.page import Page
from app.models.page_version import PageVersion
from app.models.vault import Vault
from app.settings import settings
from app.vault.parser import (
    ParsedPage,
    VaultTimelineError,
    assert_timeline_append_only,
    extract_wikilinks,
    parse_vault_file,
)
from app.vault.paths import validate_slug


class PageNotFound(Exception):
    """Raised when a page does not exist or is soft-deleted."""


class TimelineViolation(Exception):
    """Raised when a timeline mutation is detected on the API write path."""

    def __init__(self, message: str = "Timeline is append-only; existing entries cannot be edited, deleted, or reordered."):
        super().__init__(message)


class SharedVaultWriteDenied(PermissionError):
    """Raised when a non-admin attempts to write to the shared vault with admin_only policy."""


async def _next_version(session: AsyncSession, page_id: uuid.UUID) -> int:
    """Return the next version number for page_id.

    Queries MAX(page_versions.version) WHERE page_id = page_id.
    Returns 1 if no versions exist yet.
    """
    result = await session.execute(
        select(PageVersion.version)
        .where(PageVersion.page_id == page_id)
        .order_by(PageVersion.version.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return 1 if row is None else row + 1


async def _find_slug_match(
    session: AsyncSession,
    target_text: str,
    namespace: str,
    user_vault_id: uuid.UUID,
    shared_vault_id: uuid.UUID | None,
) -> Page | None:
    """Find a page matching target_text using shortest-unique-path against slug.

    D-11 algorithm:
    1. For 'shared' namespace: query only shared vault.
    2. For 'private' namespace: query user vault first, then shared if no match.
    3. Shortest-unique-path: ORDER BY LENGTH(slug) ASC, slug ASC (alphabetical tie-break).
    4. Strip leading path components to derive resolved_slug from the matched slug.
    5. No match: return None (forward references are valid — never reject).
    """
    # Strip leading "/" and normalize spaces to hyphens for slug matching
    # e.g., [[Target Note]] → "target-note" → matches slug "target-note"
    search_target = target_text.lstrip("/").replace(" ", "-").lower()

    async def _execute_match(vault_ids: list[uuid.UUID]) -> Page | None:
        if not vault_ids:
            return None
        # Try exact match first (handles simple slugs like "target-note")
        exact_result = await session.execute(
            select(Page)
            .where(
                Page.vault_id.in_(vault_ids),
                Page.slug == search_target,
                Page.deleted_at.is_(None),
            )
            .limit(1)
        )
        exact_match = exact_result.scalar_one_or_none()
        if exact_match is not None:
            return exact_match
        # Then try ILIKE pattern for nested paths (e.g., "projects/target-note")
        like_pattern = f"%/{search_target}"
        result = await session.execute(
            select(Page)
            .where(
                Page.vault_id.in_(vault_ids),
                Page.slug.ilike(like_pattern),
                Page.deleted_at.is_(None),
            )
            .order_by(text("LENGTH(slug)"), Page.slug)
            .limit(1)
        )
        return result.scalar_one_or_none()

    if namespace == "shared":
        if shared_vault_id is None:
            return None
        return await _execute_match([shared_vault_id])
    else:
        # Private namespace: search user vault first, then shared as fallback
        private_first = await _execute_match([user_vault_id])
        if private_first is not None:
            return private_first
        if shared_vault_id is not None:
            return await _execute_match([shared_vault_id])
        return None


async def upsert_page(
    session: AsyncSession,
    ctx: OperationContext,
    *,
    vault_id: uuid.UUID,
    slug: str,
    parsed: ParsedPage,
    enforce_timeline: bool = True,
) -> Page:
    """Create or update a page.

    D-02: enforce_timeline=True (API path) raises VaultTimelineError on timeline mutation.
    D-03: enforce_timeline=False (watchdog path) bypasses timeline enforcement.
    D-04: note_type defaults to 'fleeting' for new pages.
    IDX-03: returns existing page without flush if content_hash is unchanged.
    VAULT-08: inserts a PageVersion snapshot on every update (and on create for v1).
    """
    existing = (
        await session.execute(
            select(Page).where(Page.vault_id == vault_id, Page.slug == slug)
        )
    ).scalar_one_or_none()

    is_update = existing is not None

    if is_update:
        # IDX-03: content-hash deduplication — skip re-index when unchanged
        if existing.content_hash == parsed.content_hash:
            return existing

        # D-02: timeline append-only enforcement on API writes
        if enforce_timeline and parsed.timeline:
            try:
                assert_timeline_append_only(existing.timeline or "", parsed.timeline)
            except VaultTimelineError as e:
                raise TimelineViolation(str(e)) from e

        # VAULT-08: snapshot existing state before update
        version_num = await _next_version(session, existing.id)
        pv = PageVersion(
            page_id=existing.id,
            version=version_num,
            frontmatter=dict(existing.frontmatter),
            compiled_truth=existing.compiled_truth or "",
            timeline=existing.timeline,
            content_hash=existing.content_hash,
        )
        session.add(pv)

        # Update existing page
        existing.frontmatter = dict(parsed.frontmatter)
        existing.compiled_truth = parsed.compiled_truth
        existing.timeline = parsed.timeline
        existing.content_hash = parsed.content_hash
        existing.note_type = parsed.frontmatter.get("note_type", "fleeting")
        await session.flush()

        # IndexEvent: updated
        idx = IndexEvent(
            user_id=ctx.user_id,
            event_type="updated",
            page_slug=slug,
            details={"vault_id": str(vault_id), "page_id": str(existing.id)},
        )
        session.add(idx)
        await session.flush()
        return existing
    else:
        # Create new page
        note_type = parsed.frontmatter.get("note_type", "fleeting")
        page = Page(
            vault_id=vault_id,
            slug=slug,
            type=parsed.frontmatter.get("type", "note"),
            note_type=note_type,
            frontmatter=dict(parsed.frontmatter),
            compiled_truth=parsed.compiled_truth,
            timeline=parsed.timeline,
            content_hash=parsed.content_hash,
        )
        session.add(page)
        await session.flush()

        # VAULT-08: establish version 1 on create for complete history
        pv = PageVersion(
            page_id=page.id,
            version=1,
            frontmatter=dict(parsed.frontmatter),
            compiled_truth=parsed.compiled_truth,
            timeline=parsed.timeline,
            content_hash=parsed.content_hash,
        )
        session.add(pv)

        # IndexEvent: created
        idx = IndexEvent(
            user_id=ctx.user_id,
            event_type="created",
            page_slug=slug,
            details={"vault_id": str(vault_id)},
        )
        session.add(idx)
        await session.flush()
        return page


async def write_page(
    session: AsyncSession,
    ctx: OperationContext,
    *,
    slug: str,
    raw_content: bytes,
    vault_id: uuid.UUID,
    shared_vault_id: uuid.UUID | None = None,
) -> Page:
    """Full write path: parse, validate, upsert, resolve wikilinks.

    1. Parse raw_content via parse_vault_file.
    2. Validate slug via vault.paths.validate_slug.
    3. Check shared vault write policy (VAULT-03).
    4. Upsert with enforce_timeline=True (D-02).
    5. Resolve and store wikilinks via resolve_and_store_wikilinks.
    """
    parsed = parse_vault_file(raw_content)

    # Validate slug — raises InvalidSlugError on violation
    validate_slug(slug)

    # VAULT-03: shared vault write policy
    vault_row = await session.get(Vault, vault_id)
    if vault_row is not None and vault_row.kind == "shared":
        if settings.shared_vault_write_policy == "admin_only" and ctx.role != "admin":
            raise SharedVaultWriteDenied(
                "Non-admin users cannot write to the shared vault "
                "when shared_vault_write_policy is admin_only"
            )

    page = await upsert_page(session, ctx, vault_id=vault_id, slug=slug, parsed=parsed)

    # Resolve and store wikilinks (D-09: stored in frontmatter._resolved_links)
    raw_text = raw_content.decode("utf-8", errors="replace")
    await resolve_and_store_wikilinks(
        session, page, raw_text, user_vault_id=vault_id, shared_vault_id=shared_vault_id
    )

    return page


async def read_page(session: AsyncSession, *, vault_id: uuid.UUID, slug: str) -> Page:
    """Read a non-deleted page by vault_id + slug.

    Raises PageNotFound if not found or soft-deleted.
    """
    page = (
        await session.execute(
            select(Page).where(
                Page.vault_id == vault_id,
                Page.slug == slug,
                Page.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if page is None:
        raise PageNotFound(f"Page {slug!r} not found in vault {vault_id}")
    return page


async def soft_delete_page(
    session: AsyncSession,
    ctx: OperationContext,
    *,
    page_id: uuid.UUID,
    reason: str = "file_deleted",
) -> None:
    """Soft-delete a page: set deleted_at, deleted_by, delete_reason.

    Inserts an IndexEvent with event_type='deleted'.
    """
    page = await session.get(Page, page_id)
    if page is None:
        raise PageNotFound(f"Page {page_id} not found")
    page.deleted_at = func.now()
    page.deleted_by = ctx.user_id
    page.delete_reason = reason
    await session.flush()

    # IndexEvent: deleted
    idx = IndexEvent(
        user_id=ctx.user_id,
        event_type="deleted",
        page_slug=page.slug,
        details={"page_id": str(page_id), "reason": reason},
    )
    session.add(idx)
    await session.flush()


async def append_timeline(
    session: AsyncSession,
    ctx: OperationContext,
    *,
    vault_id: uuid.UUID,
    slug: str,
    entry: str,
) -> Page:
    """Append a timeline entry to an existing page.

    D-02 exception: this is a service-controlled append, not raw user content,
    so enforce_timeline=False bypasses the API hard-reject to allow the write.
    """
    page = await read_page(session, vault_id=vault_id, slug=slug)
    current_timeline = page.timeline or ""
    # Append entry with newline separator
    new_timeline = f"{current_timeline}\n{entry}".strip()
    parsed = ParsedPage(
        frontmatter=dict(page.frontmatter),
        compiled_truth=page.compiled_truth or "",
        timeline=new_timeline,
        body_shape=page.frontmatter.get("_body_shape", "compiled_truth_only"),
        content_hash=page.content_hash,  # not used for timeline append
    )
    return await upsert_page(
        session,
        ctx,
        vault_id=vault_id,
        slug=slug,
        parsed=parsed,
        enforce_timeline=False,
    )


async def resolve_and_store_wikilinks(
    session: AsyncSession,
    page: Page,
    raw_content: str,
    *,
    user_vault_id: uuid.UUID,
    shared_vault_id: uuid.UUID | None = None,
) -> None:
    """Parse wikilinks, resolve to page IDs/slugs, store in frontmatter._resolved_links.

    D-09: stores result in frontmatter JSONB; does NOT write to links table.
    D-10: resolved_links schema per entry: raw, target_text, resolved_slug,
           page_id (UUID string or null), namespace, unresolved (bool).
    D-11: namespace routing + shortest-unique-path resolution.
    """
    parsed_links = extract_wikilinks(raw_content)
    resolved_list: list[dict] = []

    for link in parsed_links:
        target_text = link["target_text"]
        namespace = link["namespace"]

        match = await _find_slug_match(
            session,
            target_text,
            namespace,
            user_vault_id,
            shared_vault_id,
        )
        if match is not None:
            resolved_list.append(
                {
                    "raw": link["raw"],
                    "target_text": target_text,
                    "resolved_slug": match.slug,
                    "page_id": str(match.id),
                    "namespace": namespace,
                    "unresolved": False,
                }
            )
        else:
            # Forward references are valid — never reject the write
            resolved_list.append(
                {
                    "raw": link["raw"],
                    "target_text": target_text,
                    "resolved_slug": None,
                    "page_id": None,
                    "namespace": namespace,
                    "unresolved": True,
                }
            )

    page.frontmatter["_resolved_links"] = resolved_list
    await session.flush()


# ----------------------------------------------------------------------
# Phase 1d — FTS, history, diff, revert, backlinks, stats, health
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SearchHit:
    """Full-text search hit with ranked score and matched-field indicators."""

    page_id: uuid.UUID
    slug: str
    title: str | None
    note_type: str | None
    score: float
    snippet: str
    matched_fields: list[str]
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class PageVersionSummary:
    """One entry in the version history for a page."""

    version: int
    content_hash: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class PageDiff:
    """Unified diffs between two snapshots of a page."""

    from_version: int
    to_version: int
    compiled_truth_diff: str
    timeline_diff: str


@dataclass(frozen=True, slots=True)
class BacklinkHit:
    """A live page that links to the target page via _resolved_links."""

    page_id: uuid.UUID
    slug: str
    title: str | None


@dataclass(frozen=True, slots=True)
class VaultStats:
    """Aggregate counts and byte-size for a vault."""

    live_pages: int
    deleted_pages: int
    total_bytes: int
    last_updated_at: datetime | None


@dataclass(frozen=True, slots=True)
class VaultHealth:
    """Health-check result for the vault subsystem."""

    db_ok: bool
    fernet_ok: bool
    watchdog_alive: bool | None = None


async def search_pages_fts(
    session: AsyncSession,
    ctx: OperationContext,  # noqa: ARG001 — accepted for future scoping; vault_id is explicit
    *,
    vault_id: uuid.UUID,
    query: str,
    limit: int = 20,
    namespace: Literal["private", "shared", "all"] = "private",  # noqa: ARG001 — Phase 1d uses vault_id directly
) -> list[SearchHit]:
    """Full-text search via PostgreSQL websearch_to_tsquery + GIN index.

    websearch_to_tsquery is tried first; plainto_tsquery is used as fallback
    when websearch_to_tsquery parses an empty query (e.g. "&&&").
    """
    if not query or not query.strip():
        raise ValueError("query must be non-empty")
    limit = max(1, min(int(limit), 100))

    sql = """
        WITH q AS (
            SELECT
                COALESCE(NULLIF(websearch_to_tsquery('english', :q), ''::tsquery),
                         plainto_tsquery('english', :q)) AS tsq
        )
        SELECT
            p.id, p.slug,
            p.frontmatter->>'title' AS title,
            p.note_type,
            p.updated_at,
            ts_rank(p.search_vector, q.tsq) AS score,
            ts_headline(
                'english',
                COALESCE(p.compiled_truth, ''),
                q.tsq,
                'MaxFragments=1,MaxWords=20'
            ) AS snippet,
            (to_tsvector('english', COALESCE(p.frontmatter->>'title', '')) @@ q.tsq) AS title_match,
            (to_tsvector('english', COALESCE(p.compiled_truth, '')) @@ q.tsq) AS truth_match
        FROM pages p, q
        WHERE p.vault_id = :vid
          AND p.deleted_at IS NULL
          AND p.search_vector @@ q.tsq
        ORDER BY score DESC, p.updated_at DESC
        LIMIT :lim
    """
    rows = (
        (
            await session.execute(
                text(sql), {"q": query, "vid": str(vault_id), "lim": limit}
            )
        )
        .mappings()
        .all()
    )

    hits: list[SearchHit] = []
    for r in rows:
        matched: list[str] = []
        if r["title_match"]:
            matched.append("title")
        if r["truth_match"]:
            matched.append("compiled_truth")
        hits.append(
            SearchHit(
                page_id=r["id"],
                slug=r["slug"],
                title=r["title"],
                note_type=r["note_type"],
                score=float(r["score"]),
                snippet=r["snippet"] or "",
                matched_fields=matched,
                updated_at=r["updated_at"],
            )
        )
    return hits


async def list_pages(
    session: AsyncSession,
    ctx: OperationContext,  # noqa: ARG001
    *,
    vault_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[Page]:
    """Paginated live-page listing for a vault, ordered by updated_at desc."""
    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))
    rows = await session.execute(
        select(Page)
        .where(Page.vault_id == vault_id, Page.deleted_at.is_(None))
        .order_by(Page.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(rows.scalars().all())


async def get_page_history(
    session: AsyncSession,
    ctx: OperationContext,  # noqa: ARG001
    *,
    page_id: uuid.UUID,
) -> list[PageVersionSummary]:
    """All version snapshots for a page, newest first."""
    rows = await session.execute(
        select(PageVersion.version, PageVersion.content_hash, PageVersion.created_at)
        .where(PageVersion.page_id == page_id)
        .order_by(PageVersion.version.desc())
    )
    return [
        PageVersionSummary(version=v, content_hash=h, created_at=ts)
        for v, h, ts in rows.all()
    ]


async def get_page_diff(
    session: AsyncSession,
    ctx: OperationContext,  # noqa: ARG001
    *,
    page_id: uuid.UUID,
    from_version: int,
    to_version: int,
) -> PageDiff:
    """Compute unified diffs for compiled_truth and timeline between two versions."""
    rows = (
        (
            await session.execute(
                select(PageVersion).where(
                    PageVersion.page_id == page_id,
                    PageVersion.version.in_([from_version, to_version]),
                )
            )
        )
        .scalars()
        .all()
    )

    if len(rows) != 2:
        raise PageNotFound(
            f"missing one of versions {from_version}, {to_version} for page {page_id}"
        )

    by_v = {r.version: r for r in rows}
    a, b = by_v[from_version], by_v[to_version]

    truth_diff = "\n".join(
        difflib.unified_diff(
            (a.compiled_truth or "").splitlines(),
            (b.compiled_truth or "").splitlines(),
            fromfile=f"v{from_version}",
            tofile=f"v{to_version}",
            lineterm="",
        )
    )
    tl_diff = "\n".join(
        difflib.unified_diff(
            (a.timeline or "").splitlines(),
            (b.timeline or "").splitlines(),
            fromfile=f"v{from_version}",
            tofile=f"v{to_version}",
            lineterm="",
        )
    )
    return PageDiff(
        from_version=from_version,
        to_version=to_version,
        compiled_truth_diff=truth_diff,
        timeline_diff=tl_diff,
    )


async def revert_page(
    session: AsyncSession,
    ctx: OperationContext,
    *,
    vault_id: uuid.UUID,
    slug: str,
    target_version: int,
) -> Page:
    """Restore a page to the content of a prior version snapshot."""
    page = await read_page(session, vault_id=vault_id, slug=slug)
    target = (
        await session.execute(
            select(PageVersion).where(
                PageVersion.page_id == page.id,
                PageVersion.version == target_version,
            )
        )
    ).scalar_one_or_none()

    if target is None:
        raise PageNotFound(f"version {target_version} not found for page {slug}")

    parsed = ParsedPage(
        frontmatter=dict(target.frontmatter),
        compiled_truth=target.compiled_truth or "",
        timeline=target.timeline or "",
        body_shape=None,  # type: ignore[arg-type] — not used on revert
        content_hash=target.content_hash,
    )
    return await upsert_page(
        session,
        ctx,
        vault_id=vault_id,
        slug=slug,
        parsed=parsed,
        enforce_timeline=False,  # revert is service-controlled; bypass D-02
    )


async def get_backlinks_for_page(
    session: AsyncSession,
    ctx: OperationContext,  # noqa: ARG001
    *,
    vault_id: uuid.UUID,
    target_page_id: uuid.UUID,
) -> list[BacklinkHit]:
    """Find live pages in the vault whose _resolved_links contains target_page_id."""
    sql = """
        SELECT p.id, p.slug, p.frontmatter->>'title' AS title
        FROM pages p
        WHERE p.vault_id = :vid
          AND p.deleted_at IS NULL
          AND EXISTS (
              SELECT 1
              FROM jsonb_array_elements(
                       COALESCE(p.frontmatter->'_resolved_links', '[]'::jsonb)
                   ) AS link
              WHERE link->>'page_id' = :tpid
          )
        ORDER BY p.slug ASC
    """
    rows = (
        (
            await session.execute(
                text(sql), {"vid": str(vault_id), "tpid": str(target_page_id)}
            )
        )
        .mappings()
        .all()
    )

    return [
        BacklinkHit(page_id=r["id"], slug=r["slug"], title=r["title"]) for r in rows
    ]


async def vault_stats(
    session: AsyncSession,
    ctx: OperationContext,  # noqa: ARG001
    *,
    vault_id: uuid.UUID,
) -> VaultStats:
    """Aggregate counts and byte-size for a vault."""
    row = (
        await session.execute(
            select(
                func.count(Page.id).filter(Page.deleted_at.is_(None)),
                func.count(Page.id).filter(Page.deleted_at.is_not(None)),
                func.coalesce(
                    func.sum(func.length(func.coalesce(Page.compiled_truth, ""))),
                    0,
                ),
                func.max(Page.updated_at),
            ).where(Page.vault_id == vault_id)
        )
    ).one()

    return VaultStats(
        live_pages=row[0],
        deleted_pages=row[1],
        total_bytes=int(row[2]),
        last_updated_at=row[3],
    )


async def vault_health(
    session: AsyncSession,
    ctx: OperationContext,  # noqa: ARG001 — db check is connection-level
) -> VaultHealth:
    """Check DB, Fernet key, and watchdog liveness.

    watchdog_alive is None in Phase 1d; Plan 04 will wire pg_notify-based
    heartbeat detection.
    """
    db_ok = True
    try:
        await session.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 — degraded, not a crash
        db_ok = False

    fernet_ok = True
    try:
        fernet()
    except FernetKeyMissing:
        fernet_ok = False

    return VaultHealth(db_ok=db_ok, fernet_ok=fernet_ok, watchdog_alive=None)
