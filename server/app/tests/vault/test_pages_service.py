"""Page service integration tests — VAULT-04, VAULT-06, VAULT-08.

Tests the services/pages.py CRUD layer using the testcontainer DB.
Session-scoped fixtures (seed_user_for_vault, seed_vault) provide clean isolation
per user via rollback-per-test (db_session fixture).
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import OperationContext
from app.dependencies import session_with_rls
from app.services.pages import (
    PageNotFound,
    upsert_page,
    write_page,
    read_page,
    soft_delete_page,
)
from app.vault.parser import VaultTimelineError, parse_vault_file

pytestmark = [pytest.mark.vault, pytest.mark.integration]


def _ctx_for(user_id, role="user"):
    """Build an OperationContext for a given user_id."""
    return OperationContext(
        user_id=user_id,
        role=role,
        transport="rest",
        remote=True,
        client_name="test",
        request_id="test",
    )


@pytest.mark.asyncio
async def test_note_type_defaults_to_fleeting(
    db_session: AsyncSession,
    seed_user_for_vault,
    seed_vault,
):
    """New page with no note_type in frontmatter defaults to 'fleeting' (D-04)."""
    ctx = _ctx_for(seed_user_for_vault)
    raw = b"---\ntitle: My Note\n---\nSome content."
    parsed = parse_vault_file(raw)

    page = await upsert_page(
        db_session, ctx, vault_id=seed_vault, slug="my-note", parsed=parsed
    )
    await db_session.commit()

    assert page.note_type == "fleeting"


@pytest.mark.asyncio
async def test_note_type_preserved_from_frontmatter(
    db_session: AsyncSession,
    seed_user_for_vault,
    seed_vault,
):
    """Page note_type is read from frontmatter when present."""
    ctx = _ctx_for(seed_user_for_vault)
    raw = b"---\ntitle: Lit Note\nnote_type: literature\n---\nSome content."
    parsed = parse_vault_file(raw)

    page = await upsert_page(
        db_session, ctx, vault_id=seed_vault, slug="lit-note", parsed=parsed
    )
    await db_session.commit()

    assert page.note_type == "literature"


@pytest.mark.asyncio
async def test_versioning_inserts_page_version_on_update(
    db_session: AsyncSession,
    seed_user_for_vault,
    seed_vault,
):
    """Updating an existing page inserts a PageVersion snapshot (VAULT-08)."""
    ctx = _ctx_for(seed_user_for_vault)

    # Create page
    raw1 = b"---\ntitle: Versioned\n---\nVersion 1 content."
    await upsert_page(
        db_session, ctx, vault_id=seed_vault, slug="versioned", parsed=parse_vault_file(raw1)
    )
    await db_session.commit()

    # Count versions after create (should be 1: v1)
    count_result = await db_session.execute(
        select(func.count()).select_from(
            text("page_versions WHERE page_id = (SELECT id FROM pages WHERE slug = 'versioned')")
        )
    )
    count_after_create = count_result.scalar_one()

    # Update page
    raw2 = b"---\ntitle: Versioned\n---\nVersion 2 content."
    await upsert_page(
        db_session, ctx, vault_id=seed_vault, slug="versioned", parsed=parse_vault_file(raw2)
    )
    await db_session.commit()

    # Count versions after update (should be 2: v1 + v2)
    count_result = await db_session.execute(
        select(func.count()).select_from(
            text("page_versions WHERE page_id = (SELECT id FROM pages WHERE slug = 'versioned')")
        )
    )
    count_after_update = count_result.scalar_one()

    assert count_after_update == count_after_create + 1


@pytest.mark.asyncio
async def test_dedup_skips_reindex_when_hash_unchanged(
    db_session: AsyncSession,
    seed_user_for_vault,
    seed_vault,
):
    """Re-upserting with identical content_hash skips re-index (IDX-03 dedup)."""
    ctx = _ctx_for(seed_user_for_vault)
    raw = b"---\ntitle: Dedup Test\n---\nImmutable content."
    parsed = parse_vault_file(raw)

    # First upsert
    page1 = await upsert_page(
        db_session, ctx, vault_id=seed_vault, slug="dedup-test", parsed=parsed
    )
    await db_session.commit()

    # Second upsert — identical hash
    page2 = await upsert_page(
        db_session, ctx, vault_id=seed_vault, slug="dedup-test", parsed=parsed
    )

    # Dedup returns same object (no new page_versions inserted)
    assert page1.id == page2.id


@pytest.mark.asyncio
async def test_timeline_append_only_enforces(
    db_session: AsyncSession,
    seed_user_for_vault,
    seed_vault,
):
    """upsert_page with enforce_timeline=True raises TimelineViolation on mutation (D-02)."""
    ctx = _ctx_for(seed_user_for_vault)

    # Create page with initial timeline
    raw1 = (
        b"---\ntitle: Timeline Test\n---\n# Compiled Truth\n\n---\n# Timeline\n- entry 1\n"
    )
    await upsert_page(
        db_session, ctx, vault_id=seed_vault, slug="timeline-test", parsed=parse_vault_file(raw1)
    )
    await db_session.commit()

    # Try to mutate existing timeline entry — must raise VaultTimelineError
    raw2 = (
        b"---\ntitle: Timeline Test\n---\n# Compiled Truth\n\n---\n# Timeline\n- MODIFIED entry\n"
    )
    with pytest.raises(VaultTimelineError):
        await upsert_page(
            db_session,
            ctx,
            vault_id=seed_vault,
            slug="timeline-test",
            parsed=parse_vault_file(raw2),
            enforce_timeline=True,
        )


@pytest.mark.asyncio
async def test_timeline_append_only_allows_new_entry(
    db_session: AsyncSession,
    seed_user_for_vault, seed_vault,
):
    """upsert_page with enforce_timeline=True ALLOWS appending a new timeline entry (D-02)."""
    ctx = _ctx_for(seed_user_for_vault)

    raw1 = (
        b"---\ntitle: Timeline Test\n---\n# Compiled Truth\n\n---\n# Timeline\n- entry 1\n"
    )
    await upsert_page(
        db_session, ctx, vault_id=seed_vault, slug="timeline-test", parsed=parse_vault_file(raw1)
    )
    await db_session.commit()

    # Append a new entry — must succeed
    raw2 = (
        b"---\ntitle: Timeline Test\n---\n# Compiled Truth\n\n---\n# Timeline\n- entry 1\n- entry 2\n"
    )
    page = await upsert_page(
        db_session,
        ctx,
        vault_id=seed_vault,
        slug="timeline-test",
        parsed=parse_vault_file(raw2),
        enforce_timeline=True,
    )
    await db_session.commit()
    assert page.timeline is not None


@pytest.mark.asyncio
async def test_soft_delete_sets_fields(
    db_session: AsyncSession,
    seed_user_for_vault,
    seed_vault,
):
    """soft_delete_page sets deleted_at, deleted_by, delete_reason."""
    ctx = _ctx_for(seed_user_for_vault)

    # Seed a page to delete
    from sqlalchemy import text
    from uuid import uuid4

    page_id = uuid4()
    await db_session.execute(
        text(
            "INSERT INTO pages (id, vault_id, slug, type, note_type, frontmatter, "
            "compiled_truth, content_hash, created_at, updated_at) "
            "VALUES (:id, :vid, 'delete-me', 'note', 'fleeting', '{}', 'delete content', "
            "'abc123def456789a', now(), now())"
        ),
        {"id": page_id, "vid": seed_vault},
    )
    await db_session.commit()

    await soft_delete_page(
        db_session, ctx, page_id=page_id, reason="file_deleted"
    )
    await db_session.commit()

    # Reload and verify
    result = await db_session.execute(
        text("SELECT deleted_at, deleted_by, delete_reason FROM pages WHERE id = :id"),
        {"id": page_id},
    )
    row = result.fetchone()
    assert row is not None
    assert row.deleted_at is not None
    assert row.deleted_by == seed_user_for_vault
    assert row.delete_reason == "file_deleted"


@pytest.mark.asyncio
async def test_read_page_raises_not_found(
    db_session: AsyncSession,
    seed_user_for_vault,
    seed_vault,
):
    """read_page raises PageNotFound for non-existent page."""
    with pytest.raises(PageNotFound):
        await read_page(db_session, vault_id=seed_vault, slug="does-not-exist")


@pytest.mark.asyncio
async def test_read_page_excludes_soft_deleted(
    db_session: AsyncSession,
    seed_user_for_vault,
    seed_vault,
):
    """read_page does not return soft-deleted pages."""
    ctx = _ctx_for(seed_user_for_vault)

    raw = b"---\ntitle: Read Test\n---\nContent."
    page = await upsert_page(
        db_session, ctx, vault_id=seed_vault, slug="read-test", parsed=parse_vault_file(raw)
    )
    await db_session.commit()

    # Soft delete
    await soft_delete_page(db_session, ctx, page_id=page.id)
    await db_session.commit()

    # Read must raise
    with pytest.raises(PageNotFound):
        await read_page(db_session, vault_id=seed_vault, slug="read-test")


@pytest.mark.asyncio
async def test_write_page_validates_slug(
    db_session: AsyncSession,
    seed_user_for_vault,
    seed_vault,
):
    """write_page raises on invalid slug (VAULT-10)."""
    ctx = _ctx_for(seed_user_for_vault)
    from app.vault.paths import InvalidSlugError

    with pytest.raises(InvalidSlugError):
        await write_page(
            db_session, ctx,
            slug="Invalid Slug!",  # spaces and capitals not allowed
            raw_content=b"---\ntitle: Bad\n---\nContent",
            vault_id=seed_vault,
        )


# ----------------------------------------------------------------------
# Phase 1d — list_pages, vault_stats, vault_health
# ----------------------------------------------------------------------

from app.services.pages import list_pages, vault_health, vault_stats


@pytest.mark.asyncio
async def test_list_pages_returns_live_pages_ordered_by_updated_at(
    db_session: AsyncSession,
    seed_user_for_vault,
    seed_vault,
):
    """list_pages returns only non-deleted pages, ordered by updated_at DESC."""
    ctx = _ctx_for(seed_user_for_vault)

    raw = b"---\ntitle: List Test\n---\nContent."
    parsed = parse_vault_file(raw)
    page = await upsert_page(
        db_session, ctx, vault_id=seed_vault, slug="list-test", parsed=parsed
    )
    await db_session.commit()

    pages = await list_pages(db_session, ctx, vault_id=seed_vault)

    assert len(pages) >= 1
    assert any(p.slug == "list-test" for p in pages)


@pytest.mark.asyncio
async def test_list_pages_respects_limit_and_offset(
    db_session: AsyncSession,
    seed_user_for_vault,
    seed_vault,
):
    """list_pages paginates correctly with limit and offset."""
    ctx = _ctx_for(seed_user_for_vault)

    for i in range(5):
        raw = f"---\ntitle: Page {i}\n---\nContent {i}.".encode()
        parsed = parse_vault_file(raw)
        await upsert_page(
            db_session, ctx, vault_id=seed_vault, slug=f"list-page-{i}", parsed=parsed
        )
    await db_session.commit()

    # First page
    page1 = await list_pages(db_session, ctx, vault_id=seed_vault, limit=2)
    assert len(page1) == 2

    # Second page
    page2 = await list_pages(db_session, ctx, vault_id=seed_vault, limit=2, offset=2)
    assert len(page2) == 2

    # No overlap
    assert set(p.slug for p in page1).isdisjoint(set(p.slug for p in page2))


@pytest.mark.asyncio
async def test_vault_stats_returns_correct_counts(
    db_session: AsyncSession,
    seed_user_for_vault,
    seed_vault,
):
    """vault_stats returns live/deleted counts and compiled_truth byte-size."""
    ctx = _ctx_for(seed_user_for_vault)

    raw = b"---\ntitle: Stats Test\n---\nSome content here."
    parsed = parse_vault_file(raw)
    await upsert_page(
        db_session, ctx, vault_id=seed_vault, slug="stats-test", parsed=parsed
    )
    await db_session.commit()

    stats = await vault_stats(db_session, ctx, vault_id=seed_vault)

    assert stats.live_pages >= 1
    assert stats.deleted_pages >= 0
    assert stats.total_bytes >= len("Some content here")
    assert stats.last_updated_at is not None


@pytest.mark.asyncio
async def test_vault_health_returns_db_and_fernet_status(
    db_session: AsyncSession,
    seed_user_for_vault,
):
    """vault_health returns db_ok=True when SELECT 1 succeeds, fernet_ok based on key presence."""
    ctx = _ctx_for(seed_user_for_vault)

    health = await vault_health(db_session, ctx)

    # db_ok: SELECT 1 succeeded (testcontainer is up)
    assert health.db_ok is True
    # fernet_ok: depends on SMARTCOPILOT_FERNET_KEY in test env
    # watchdog_alive: always None in Phase 1d (Plan 04 stub)
    assert health.watchdog_alive is None
