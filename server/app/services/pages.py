"""Page CRUD service (transport-agnostic).

CLAUDE.md: no FastAPI imports; services take OperationContext + AsyncSession.
D-02: timeline append-only enforcement on API writes (enforce_timeline=True).
D-03: watchdog path bypasses enforcement (enforce_timeline=False).
D-04: note_type defaults to 'fleeting' for new pages.
D-09: wikilink resolution stored in frontmatter._resolved_links; no writes to links table.
VAULT-03: shared vault write policy enforced per settings.shared_vault_write_policy.
VAULT-07: content-hash deduplication — re-index skipped when content_hash unchanged.
VAULT-08: page_versions snapshot on every update.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import OperationContext
from app.models.index_event import IndexEvent
from app.models.page import Page
from app.models.page_version import PageVersion
from app.models.vault import Vault
from app.settings import settings
from app.vault.parser import (
    ParsedPage,
    assert_timeline_append_only,
    extract_wikilinks,
    parse_vault_file,
)
from app.vault.paths import validate_slug


class PageNotFound(Exception):
    """Raised when a page does not exist or is soft-deleted."""


class TimelineViolation(Exception):
    """Raised when a timeline mutation is detected on the API write path."""


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
    search_target = target_text.lstrip("/")
    # Build ILIKE pattern to match slug ending with search_target
    # Handles both single-component and multi-component targets
    like_pattern = f"%/{search_target}"

    def _execute_match(vault_ids: list[uuid.UUID]) -> Page | None:
        if not vault_ids:
            return None
        result = session.execute(
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
        return _execute_match([shared_vault_id])
    else:
        # Private namespace: search user vault first, then shared as fallback
        private_first = _execute_match([user_vault_id])
        if private_first is not None:
            return private_first
        if shared_vault_id is not None:
            return _execute_match([shared_vault_id])
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
            assert_timeline_append_only(existing.timeline or "", parsed.timeline)

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
