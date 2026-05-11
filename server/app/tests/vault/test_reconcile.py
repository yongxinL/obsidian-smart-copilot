"""Reconciliation job tests — IDX-04.

Tests for the 5-minute reconciliation job (scheduler/jobs/reconcile_vault.py):
  - test_reconcile_picks_up_new_file: new file on disk creates DB page
  - test_reconcile_soft_deletes_missing_file: file deleted from disk soft-deletes DB page
  - test_reconcile_skips_unchanged_hash: unchanged file doesn't grow page_versions
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.auth.context import system_operation_context
from app.dependencies import session_with_rls
from app.scheduler.jobs.reconcile_vault import reconcile_vault

pytestmark = [pytest.mark.vault, pytest.mark.integration]


async def _seed_vault_and_user(
    tmp_vault_dir,
    vault_slug: str,
) -> tuple[uuid.UUID, uuid.UUID]:
    """Create a user and a vault whose path is tmp_vault_dir.

    Uses the session_with_rls pattern (reconciles both seed and query through
    the same patched async_session_factory from conftest._patch_session_factory).
    """
    ctx = system_operation_context(request_id="test", client_name="test-reconcile")
    async for session in session_with_rls(ctx):
        # Seed a user
        user_id = uuid.uuid4()
        await session.execute(
            text(
                "INSERT INTO users (id, username, role, password_hash, is_active, created_at, updated_at) "
                "VALUES (:id, :u, 'user', '$argon2id$v=19$m=65536,t=3,p=1$placeholder', true, now(), now())"
            ),
            {"id": user_id, "u": f"reconcile-{user_id.hex[:8]}"},
        )

        # Seed a vault pointing to tmp_vault_dir
        vault_id = uuid.uuid4()
        await session.execute(
            text(
                "INSERT INTO vaults (id, owner_user_id, kind, path, created_at, updated_at) "
                "VALUES (:id, :uid, 'private', :path, now(), now())"
            ),
            {"id": vault_id, "uid": user_id, "path": str(tmp_vault_dir)},
        )
        await session.commit()

    return vault_id, user_id


@pytest.mark.asyncio
async def test_reconcile_picks_up_new_file(tmp_vault_dir, monkeypatch):
    """Reconciler picks up a new file and creates a DB page."""
    # Create a user + vault in the test DB (via patched session_with_rls)
    vault_id, _ = await _seed_vault_and_user(tmp_vault_dir, "test-reconcile")
    monkeypatch.setenv("SMARTCOPILOT_VAULT_ROOT", str(tmp_vault_dir))

    # Write a .md file to tmp_vault_dir
    note_file = tmp_vault_dir / "my-note.md"
    note_file.write_bytes(b"---\ntype: note\n---\nContent\n")

    # Run reconciliation
    await reconcile_vault()

    # Verify page was created in DB
    ctx = system_operation_context(request_id="test", client_name="test-reconcile")
    async for session in session_with_rls(ctx):
        result = await session.execute(
            text(
                "SELECT id, slug, content_hash FROM pages WHERE slug = 'my-note' AND vault_id = :vid"
            ),
            {"vid": str(vault_id)},
        )
        row = result.fetchone()
        assert row is not None, (
            "Page 'my-note' should be created by reconciliation. "
            f"vault_id={vault_id}, vault_path={tmp_vault_dir}"
        )
        assert row.slug == "my-note"
        # content_hash should be xxhash64 hexdigest (16 chars)
        assert row.content_hash and len(row.content_hash) == 16


@pytest.mark.asyncio
async def test_reconcile_soft_deletes_missing_file(tmp_vault_dir, monkeypatch):
    """Reconciler soft-deletes a DB page when the corresponding file is missing."""
    # Create a user + vault in the test DB
    vault_id, _ = await _seed_vault_and_user(tmp_vault_dir, "test-reconcile-del")
    monkeypatch.setenv("SMARTCOPILOT_VAULT_ROOT", str(tmp_vault_dir))

    # Insert a page row in DB for that vault, but do NOT write the file to disk
    ctx = system_operation_context(request_id="test", client_name="test-reconcile-del")
    async for session in session_with_rls(ctx):
        orphan_id = uuid.uuid4()
        await session.execute(
            text(
                "INSERT INTO pages (id, vault_id, slug, type, note_type, frontmatter, "
                "compiled_truth, timeline, content_hash, created_at, updated_at) "
                "VALUES (:id, :vid, 'orphan-page', 'note', 'fleeting', '{}', 'Orphan content', "
                "'', 'orphanhash123', now(), now())"
            ),
            {"id": orphan_id, "vid": str(vault_id)},
        )
        await session.commit()

    # Run reconciliation — should find no corresponding file and soft-delete
    await reconcile_vault()

    # Verify page is soft-deleted (deleted_at is set)
    async for session in session_with_rls(ctx):
        result = await session.execute(
            text(
                "SELECT deleted_at, delete_reason FROM pages "
                "WHERE slug = 'orphan-page' AND vault_id = :vid"
            ),
            {"vid": str(vault_id)},
        )
        row = result.fetchone()
        assert row is not None, "Page 'orphan-page' should still exist"
        assert row.deleted_at is not None, (
            "Page should be soft-deleted when corresponding file is missing"
        )
        assert row.delete_reason == "reconciler_file_missing", (
            f"delete_reason should be 'reconciler_file_missing', got {row.delete_reason!r}"
        )


@pytest.mark.asyncio
async def test_reconcile_skips_unchanged_hash(tmp_vault_dir, monkeypatch):
    """Reconciler skips DB write when file content_hash hasn't changed."""
    # Create a user + vault in the test DB
    vault_id, _ = await _seed_vault_and_user(tmp_vault_dir, "test-reconcile-hash")
    monkeypatch.setenv("SMARTCOPILOT_VAULT_ROOT", str(tmp_vault_dir))

    # Write a file and reconcile (creates page with version 1)
    note_file = tmp_vault_dir / "stable-note.md"
    note_file.write_bytes(b"---\ntype: note\n---\nStable content\n")
    await reconcile_vault()

    # Get the page id
    ctx = system_operation_context(request_id="test", client_name="test-reconcile-hash")
    page_id: uuid.UUID | None = None
    async for session in session_with_rls(ctx):
        result = await session.execute(
            text("SELECT id FROM pages WHERE slug = 'stable-note' AND vault_id = :vid"),
            {"vid": str(vault_id)},
        )
        row = result.fetchone()
        assert row is not None, "Page should be created by first reconciliation"
        page_id = row.id

    # Count versions after first reconciliation
    async for session in session_with_rls(ctx):
        result = await session.execute(
            text("SELECT COUNT(*) FROM page_versions WHERE page_id = :id"),
            {"id": str(page_id)},
        )
        first_count = result.scalar_one()
        assert first_count >= 1, "First reconciliation should create at least 1 version"

    # Run reconciliation again — content unchanged, should skip
    await reconcile_vault()

    # Count versions after second reconciliation — should be the same
    async for session in session_with_rls(ctx):
        result = await session.execute(
            text("SELECT COUNT(*) FROM page_versions WHERE page_id = :id"),
            {"id": str(page_id)},
        )
        second_count = result.scalar_one()

    assert second_count == first_count, (
        f"Hash unchanged — page_versions should not grow. "
        f"Before={first_count}, After={second_count}"
    )
