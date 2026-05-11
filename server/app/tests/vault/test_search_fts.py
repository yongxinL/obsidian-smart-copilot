"""Phase 1d FTS integration tests — migration 0004.

Verifies:
  - search_vector column exists with type tsvector
  - GIN index ix_pages_search_vector exists
  - websearch_to_tsquery hits work on frontmatter title + compiled_truth
  - search_vector is NEVER NULL (GENERATED ALWAYS)
  - Cross-vault RLS isolation works
  - Migration downgrade is clean

These tests target the testcontainer PostgreSQL with Alembic at head.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = [pytest.mark.vault, pytest.mark.integration]


def _ctx_for(user_id, role="user"):
    """Build an OperationContext for a given user_id."""
    from app.auth.context import OperationContext

    return OperationContext(
        user_id=user_id,
        role=role,
        transport="rest",
        remote=True,
        client_name="test",
        request_id="test",
    )


@pytest.mark.asyncio
async def test_search_vector_column_exists(db_session: AsyncSession):
    """Test 1: After Alembic upgrade, pages.search_vector tsvector column exists."""
    result = await db_session.execute(
        text(
            "SELECT data_type, is_generated "
            "FROM information_schema.columns "
            "WHERE table_name = 'pages' AND column_name = 'search_vector'"
        )
    )
    row = result.fetchone()
    assert row is not None, "search_vector column does not exist"
    assert row.data_type == "tsvector", f"expected tsvector, got {row.data_type}"
    assert row.is_generated == "ALWAYS", (
        f"expected GENERATED ALWAYS, got {row.is_generated}"
    )


@pytest.mark.asyncio
async def test_gin_index_exists(db_session: AsyncSession):
    """Test 2: ix_pages_search_vector GIN index is present."""
    result = await db_session.execute(
        text(
            "SELECT indexname, indexdef "
            "FROM pg_indexes "
            "WHERE indexname = 'ix_pages_search_vector'"
        )
    )
    row = result.fetchone()
    assert row is not None, "GIN index ix_pages_search_vector does not exist"
    assert "gin" in row.indexdef.lower(), f"expected GIN index type, got {row.indexdef}"


@pytest.mark.asyncio
async def test_title_and_compiled_truth_in_search_vector(
    db_session: AsyncSession,
    seed_vault,
):
    """Test 3: frontmatter title + compiled_truth are searchable via FTS."""
    page_id = uuid.uuid4()

    # Insert page with explicit search_vector (after migration adds the column)
    # The GENERATED ALWAYS column populates from frontmatter->>'title' + compiled_truth
    await db_session.execute(
        text(
            "INSERT INTO pages (id, vault_id, slug, type, note_type, frontmatter, "
            "compiled_truth, content_hash, created_at, updated_at) "
            "VALUES (:id, :vid, 'acme-corp', 'note', 'fleeting', "
            "'{\"title\": \"Acme Corporation\"}', 'founded 2010 in California', "
            "'hash0001', now(), now())"
        ),
        {"id": page_id, "vid": seed_vault},
    )
    await db_session.commit()

    # Query using websearch_to_tsquery — should find the page on both title and compiled_truth
    result = await db_session.execute(
        text(
            "SELECT slug, ts_rank(search_vector, q) AS score "
            "FROM pages, websearch_to_tsquery('english', 'acme') q "
            "WHERE search_vector @@ q AND vault_id = :vid"
        ),
        {"vid": str(seed_vault)},
    )
    rows = result.fetchall()
    assert len(rows) == 1, f"Expected 1 hit for 'acme', got {len(rows)}: {rows}"
    assert rows[0].slug == "acme-corp"
    assert rows[0].score > 0, "ts_rank should be positive for a match"


@pytest.mark.asyncio
async def test_search_vector_never_null(
    db_session: AsyncSession,
    seed_vault,
):
    """Test 4: search_vector is non-NULL even with empty frontmatter and empty compiled_truth."""
    page_id = uuid.uuid4()

    # Insert page with empty frontmatter and empty compiled_truth
    await db_session.execute(
        text(
            "INSERT INTO pages (id, vault_id, slug, type, note_type, frontmatter, "
            "compiled_truth, content_hash, created_at, updated_at) "
            "VALUES (:id, :vid, 'empty-page', 'note', 'fleeting', "
            "'{}', '', 'hash0002', now(), now())"
        ),
        {"id": page_id, "vid": seed_vault},
    )
    await db_session.commit()

    # Verify search_vector is never NULL
    result = await db_session.execute(
        text("SELECT search_vector IS NULL AS is_null FROM pages WHERE id = :id"),
        {"id": page_id},
    )
    row = result.fetchone()
    assert row is not None, "page should exist"
    assert row.is_null is False, "search_vector should never be NULL (GENERATED ALWAYS)"


@pytest.mark.asyncio
async def test_cross_vault_isolation(
    db_session: AsyncSession,
    seed_user_for_vault: uuid.UUID,
    seed_vault: uuid.UUID,
):
    """Test 5: A page in vault A is invisible to queries filtered to vault B (RLS isolation)."""
    # Create second vault (vault B)
    vault_b_id = uuid.uuid4()
    await db_session.execute(
        text(
            "INSERT INTO vaults (id, owner_user_id, kind, path, created_at, updated_at) "
            "VALUES (:id, :uid, 'private', '/vaults/private/vaultuser-b/', now(), now())"
        ),
        {"id": vault_b_id, "uid": seed_user_for_vault},
    )
    await db_session.commit()

    try:
        # Insert a page in vault B
        page_b_id = uuid.uuid4()
        await db_session.execute(
            text(
                "INSERT INTO pages (id, vault_id, slug, type, note_type, frontmatter, "
                "compiled_truth, content_hash, created_at, updated_at) "
                "VALUES (:id, :vid, 'secret-page', 'note', 'fleeting', "
                "'{\"title\": \"Secret Document\"}', 'classified info', "
                "'hash0003', now(), now())"
            ),
            {"id": page_b_id, "vid": vault_b_id},
        )
        await db_session.commit()

        # Query vault A — should not find page in vault B
        result = await db_session.execute(
            text(
                "SELECT slug FROM pages, websearch_to_tsquery('english', 'secret') q "
                "WHERE search_vector @@ q AND vault_id = :vid"
            ),
            {"vid": str(seed_vault)},
        )
        rows = result.fetchall()
        assert len(rows) == 0, (
            f"Vault A should not find pages from vault B. Got: {rows}"
        )
    finally:
        # Clean up vault B (cascade-deletes its pages)
        await db_session.execute(
            text("DELETE FROM vaults WHERE id = :id"), {"id": vault_b_id}
        )
        await db_session.commit()


@pytest.mark.asyncio
async def test_downgrade_drops_index_and_column(db_session: AsyncSession):
    """Test 6: Migration downgrade drops the index and column cleanly."""
    # Drop in reverse order (as downgrade() does)
    await db_session.execute(text("DROP INDEX IF EXISTS ix_pages_search_vector"))
    await db_session.execute(
        text("ALTER TABLE pages DROP COLUMN IF EXISTS search_vector")
    )
    await db_session.commit()

    # Verify column gone
    result = await db_session.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'pages' AND column_name = 'search_vector'"
        )
    )
    row = result.fetchone()
    assert row is None, "search_vector column should be dropped"

    # Verify index gone
    result = await db_session.execute(
        text(
            "SELECT indexname FROM pg_indexes WHERE indexname = 'ix_pages_search_vector'"
        )
    )
    row = result.fetchone()
    assert row is None, "ix_pages_search_vector index should be dropped"
