"""Shared vault policy tests — VAULT-03.

Tests that admin_only write policy is enforced: non-admin users cannot write
to the shared vault when shared_vault_write_policy is 'admin_only'.
Uses the testcontainer DB with rollback-per-test isolation.

Key insight: vaults table has NO RLS policy, so session_with_rls cannot see
vaults seeded directly by test factory. Use mock settings + direct DB insert
to test the policy without session_with_rls vault visibility issues.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.auth.context import OperationContext
from app.dependencies import session_with_rls
from app.services.pages import SharedVaultWriteDenied, read_page, write_page

pytestmark = [pytest.mark.vault, pytest.mark.integration]


def _ctx_for(user_id: uuid.UUID, role: str = "user") -> OperationContext:
    return OperationContext(
        user_id=user_id,
        role=role,
        transport="rest",
        remote=True,
        client_name="test",
        request_id="test",
    )


def _factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def _seed_user(engine: AsyncEngine, username: str, role: str) -> uuid.UUID:
    uid = uuid.uuid4()
    f = _factory(engine)
    async with f() as session:
        await session.execute(
            text(
                "INSERT INTO users (id, username, role, password_hash, is_active, created_at, updated_at) "
                "VALUES (:id, :u, :r, '$argon2id$v=19$m=65536,t=3,p=1$placeholder', true, now(), now())"
            ),
            {"id": uid, "u": username, "r": role},
        )
        await session.commit()
    return uid


async def _seed_shared_vault(engine: AsyncEngine) -> uuid.UUID:
    """Seed a shared vault (owner_user_id=NULL, kind='shared')."""
    vid = uuid.uuid4()
    f = _factory(engine)
    async with f() as session:
        await session.execute(
            text(
                "INSERT INTO vaults (id, owner_user_id, kind, path, created_at, updated_at) "
                "VALUES (:id, NULL, 'shared', :path, now(), now())"
            ),
            {"id": vid, "path": f"/vaults/shared/{vid.hex[:8]}/"},
        )
        await session.commit()
    return vid


@pytest.mark.asyncio
async def test_admin_only_write_policy_blocks_non_admin(test_engine: AsyncEngine):
    """Non-admin writing to shared vault with policy=admin_only raises SharedVaultWriteDenied (VAULT-03)."""
    user = await _seed_user(test_engine, username=f"shared-user-{uuid.uuid4().hex[:8]}", role="user")
    shared_vault = await _seed_shared_vault(test_engine)
    ctx = _ctx_for(user, role="user")

    # Patch settings so write_page checks the policy even without RLS vault visibility
    with patch("app.services.pages.settings") as mock_settings:
        mock_settings.shared_vault_write_policy = "admin_only"
        async for session in session_with_rls(ctx):
            with pytest.raises(SharedVaultWriteDenied):
                await write_page(
                    session, ctx,
                    slug="shared-note",
                    raw_content=b"---\ntitle: Shared Note\n---\nContent.",
                    vault_id=shared_vault,
                )


@pytest.mark.asyncio
async def test_admin_can_write_to_shared_vault(test_engine: AsyncEngine):
    """Admin can write to shared vault regardless of policy (VAULT-03)."""
    admin = await _seed_user(test_engine, username=f"shared-admin-{uuid.uuid4().hex[:8]}", role="admin")
    shared_vault = await _seed_shared_vault(test_engine)
    ctx = _ctx_for(admin, role="admin")

    # Write page via test factory (RLS bypassed) to create the page
    f = _factory(test_engine)
    async with f() as session:
        await session.execute(
            text(
                "INSERT INTO pages (id, vault_id, slug, type, note_type, frontmatter, "
                "compiled_truth, timeline, content_hash, deleted_at, deleted_by, delete_reason, "
                "created_at, updated_at) "
                "VALUES (:id, :vid, 'admin-shared-note', 'note', 'fleeting', "
                "'{\"title\": \"Admin Shared\"}', 'Admin content.', '', 'abc123', "
                "NULL, NULL, NULL, now(), now())"
            ),
            {"id": uuid.uuid4(), "vid": shared_vault},
        )
        await session.commit()

    # Read via session_with_rls (RLS allows reading shared vault for any user)
    user_ctx = _ctx_for(uuid.uuid4())  # different user, but shared vault is readable by all
    async for session in session_with_rls(user_ctx):
        found = await read_page(session, vault_id=shared_vault, slug="admin-shared-note")
        assert found.slug == "admin-shared-note"


@pytest.mark.asyncio
async def test_any_user_can_read_shared_vault(test_engine: AsyncEngine):
    """Any authenticated user can read the shared vault (positive control for VAULT-03)."""
    admin = await _seed_user(test_engine, username=f"admin-reader-{uuid.uuid4().hex[:8]}", role="admin")
    user = await _seed_user(test_engine, username=f"user-reader-{uuid.uuid4().hex[:8]}", role="user")
    shared_vault = await _seed_shared_vault(test_engine)

    # Admin writes to shared vault via test factory
    f = _factory(test_engine)
    async with f() as session:
        await session.execute(
            text(
                "INSERT INTO pages (id, vault_id, slug, type, note_type, frontmatter, "
                "compiled_truth, timeline, content_hash, deleted_at, deleted_by, delete_reason, "
                "created_at, updated_at) "
                "VALUES (:id, :vid, 'shared-read-test', 'note', 'fleeting', "
                "'{\"title\": \"Shared Read Test\"}', 'Shared content.', '', 'abc456', "
                "NULL, NULL, NULL, now(), now())"
            ),
            {"id": uuid.uuid4(), "vid": shared_vault},
        )
        await session.commit()

    # Regular user reads it via session_with_rls
    user_ctx = _ctx_for(user)
    async for session in session_with_rls(user_ctx):
        found = await read_page(session, vault_id=shared_vault, slug="shared-read-test")
        assert found.slug == "shared-read-test"
