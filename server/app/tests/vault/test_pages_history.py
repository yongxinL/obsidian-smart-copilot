"""Integration tests for history/diff/revert helpers in services/pages.py.

Tests use the testcontainer DB via seed_vault / seed_user_for_vault fixtures.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import OperationContext
from app.dependencies import session_with_rls
from app.services.pages import (
    PageNotFound,
    get_page_diff,
    get_page_history,
    revert_page,
    upsert_page,
)
from app.vault.parser import parse_vault_file

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


async def _insert_page_raw(
    session: AsyncSession,
    page_id: uuid.UUID,
    vault_id: uuid.UUID,
    slug: str,
    frontmatter: str,
    compiled_truth: str,
    timeline: str,
    content_hash: str,
) -> None:
    """Insert a page row directly (bypass service, for version setup)."""
    await session.execute(
        text(
            "INSERT INTO pages (id, vault_id, slug, type, note_type, frontmatter, "
            "compiled_truth, timeline, content_hash, created_at, updated_at) "
            "VALUES (:id, :vid, :slug, 'note', 'fleeting', :fm, :ct, :tl, :ch, now(), now())"
        ),
        {
            "id": page_id,
            "vid": vault_id,
            "slug": slug,
            "fm": frontmatter,
            "ct": compiled_truth,
            "tl": timeline,
            "ch": content_hash,
        },
    )
    await session.flush()


async def _insert_version(
    session: AsyncSession,
    page_id: uuid.UUID,
    version: int,
    frontmatter: str,
    compiled_truth: str,
    timeline: str,
    content_hash: str,
) -> None:
    """Insert a page_version row directly (bypass service, for history setup)."""
    await session.execute(
        text(
            "INSERT INTO page_versions (id, page_id, version, frontmatter, compiled_truth, "
            "timeline, content_hash, created_at) "
            "VALUES (:id, :pid, :v, :fm, :ct, :tl, :ch, now())"
        ),
        {
            "id": uuid.uuid4(),
            "pid": page_id,
            "v": version,
            "fm": frontmatter,
            "ct": compiled_truth,
            "tl": timeline,
            "ch": content_hash,
        },
    )
    await session.flush()


@pytest.mark.asyncio
async def test_get_page_history_returns_versions_newest_first(
    db_session: AsyncSession,
    seed_user_for_vault,
    seed_vault,
):
    """get_page_history returns version list ordered by version DESC."""
    ctx = _ctx_for(seed_user_for_vault)

    # Create a page
    raw = b"---\ntitle: History Test\n---\n# Compiled Truth\nContent.\n"
    parsed = parse_vault_file(raw)
    page = await upsert_page(
        db_session, ctx, vault_id=seed_vault, slug="history-test", parsed=parsed
    )
    await db_session.commit()

    # Insert extra versions manually
    await _insert_version(db_session, page.id, 2, '{"title":"v2"}', "V2 content", "", "v2hash")
    await _insert_version(db_session, page.id, 3, '{"title":"v3"}', "V3 content", "", "v3hash")
    await db_session.commit()

    history = await get_page_history(db_session, ctx, page_id=page.id)

    assert len(history) == 3
    assert [h.version for h in history] == [3, 2, 1]  # newest first


@pytest.mark.asyncio
async def test_get_page_diff_returns_unified_diffs(
    db_session: AsyncSession,
    seed_user_for_vault,
    seed_vault,
):
    """get_page_diff returns unified diff strings for compiled_truth and timeline."""
    ctx = _ctx_for(seed_user_for_vault)

    raw = b"---\ntitle: Diff Test\n---\n# Compiled Truth\nLine one.\n"
    parsed = parse_vault_file(raw)
    page = await upsert_page(
        db_session, ctx, vault_id=seed_vault, slug="diff-test", parsed=parsed
    )
    await db_session.commit()

    # Insert v1 (already via upsert_page on create)
    await _insert_version(
        db_session, page.id, 2, '{"title":"v2"}',
        "Line one.\nLine two.", "", "v2hash"
    )
    await db_session.commit()

    diff = await get_page_diff(db_session, ctx, page_id=page.id, from_version=1, to_version=2)

    assert diff.from_version == 1
    assert diff.to_version == 2
    assert "---" in diff.compiled_truth_diff  # unified diff header
    assert "+++" in diff.compiled_truth_diff


@pytest.mark.asyncio
async def test_get_page_diff_raises_when_version_missing(
    db_session: AsyncSession,
    seed_user_for_vault,
    seed_vault,
):
    """get_page_diff raises PageNotFound if either version row is absent."""
    ctx = _ctx_for(seed_user_for_vault)

    raw = b"---\ntitle: Missing Test\n---\n# Compiled Truth\nContent.\n"
    parsed = parse_vault_file(raw)
    page = await upsert_page(
        db_session, ctx, vault_id=seed_vault, slug="missing-test", parsed=parsed
    )
    await db_session.commit()

    with pytest.raises(PageNotFound):
        await get_page_diff(db_session, ctx, page_id=page.id, from_version=1, to_version=99)


@pytest.mark.asyncio
async def test_revert_page_restores_content_and_creates_new_version(
    db_session: AsyncSession,
    seed_user_for_vault,
    seed_vault,
):
    """revert_page copies target version content into a new max-version snapshot."""
    ctx = _ctx_for(seed_user_for_vault)

    # Create page with v1
    raw1 = b"---\ntitle: Revert Test\n---\n# Compiled Truth\nV1 content.\n"
    parsed1 = parse_vault_file(raw1)
    page = await upsert_page(
        db_session, ctx, vault_id=seed_vault, slug="revert-test", parsed=parsed1
    )
    await db_session.commit()

    # Update to v2
    raw2 = b"---\ntitle: Revert Test\n---\n# Compiled Truth\nV2 content.\n"
    parsed2 = parse_vault_file(raw2)
    await upsert_page(
        db_session, ctx, vault_id=seed_vault, slug="revert-test", parsed=parsed2
    )
    await db_session.commit()

    # Revert to v1
    reverted = await revert_page(
        db_session, ctx, vault_id=seed_vault, slug="revert-test", target_version=1
    )
    await db_session.commit()

    # Content matches v1
    assert "V1 content" in (reverted.compiled_truth or "")

    # A new version snapshot (v3) was created
    history = await get_page_history(db_session, ctx, page_id=page.id)
    assert len(history) == 3
    assert history[0].version == 3  # newest (the revert)


@pytest.mark.asyncio
async def test_revert_page_raises_when_version_not_found(
    db_session: AsyncSession,
    seed_user_for_vault,
    seed_vault,
):
    """revert_page raises PageNotFound if the target version row does not exist."""
    ctx = _ctx_for(seed_user_for_vault)

    raw = b"---\ntitle: Revert Fail\n---\n# Compiled Truth\nContent.\n"
    parsed = parse_vault_file(raw)
    await upsert_page(
        db_session, ctx, vault_id=seed_vault, slug="revert-fail", parsed=parsed
    )
    await db_session.commit()

    with pytest.raises(PageNotFound):
        await revert_page(
            db_session, ctx, vault_id=seed_vault, slug="revert-fail", target_version=99
        )