"""RLS isolation tests for pages — VAULT-02.

Tests that pages written by user A are invisible to user B via RLS.
Uses direct test factory sessions (RLS bypassed) for seeding.
session_with_rls is used for the cross-user isolation assertion.

VAULT-02 acceptance criteria: cross-user read blocked via session_with_rls + RLS policy.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.auth.context import OperationContext
from app.services.pages import PageNotFound, read_page, upsert_page
from app.vault.parser import parse_vault_file

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


@pytest.mark.asyncio
async def test_user_a_cannot_read_user_b_pages(test_engine: AsyncEngine):
    """User B (via session_with_rls) cannot read a page from user A's vault (VAULT-02 RLS).

    Setup:
    1. Seed user A + vault A via test factory (RLS bypassed)
    2. Seed user B + vault B via test factory (RLS bypassed)
    3. User A writes a page to vault A via test factory

    Test (session_with_rls scoped to user B):
    4. User B tries to read User A's page → RLS blocks → PageNotFound
    5. User B CAN read their own vault's pages (raw SQL, RLS bypassed)
    """
    from app.dependencies import session_with_rls

    f = _factory(test_engine)

    uid_a = uuid.uuid4()
    vid_a = uuid.uuid4()
    uid_b = uuid.uuid4()
    vid_b = uuid.uuid4()

    async with f() as session:
        for uid, vid, prefix in [(uid_a, vid_a, "rls-a"), (uid_b, vid_b, "rls-b")]:
            await session.execute(
                text(
                    "INSERT INTO users (id, username, role, password_hash, is_active, created_at, updated_at) "
                    "VALUES (:id, :u, :r, '$argon2id$v=19$m=65536,t=3,p=1$placeholder', true, now(), now())"
                ),
                {"id": uid, "u": f"{prefix}-{uid.hex[:8]}", "r": "user"},
            )
            await session.execute(
                text(
                    "INSERT INTO vaults (id, owner_user_id, kind, path, created_at, updated_at) "
                    "VALUES (:id, :uid, 'private', :path, now(), now())"
                ),
                {"id": vid, "uid": uid, "path": f"/vaults/private/{prefix}-{uid.hex[:8]}/"},
            )
        await session.commit()

    ctx_a = _ctx_for(uid_a)
    ctx_b = _ctx_for(uid_b)

    # User A writes a page to their vault via test factory
    async with f() as session:
        page = await upsert_page(
            session, ctx_a,
            vault_id=vid_a,
            slug="rls-secret",
            parsed=parse_vault_file(b"---\ntitle: Secret\n---\nPrivate content."),
        )
        await session.commit()
        assert page.id is not None

    # User B writes a page to their own vault via test factory
    async with f() as session:
        page_b = await upsert_page(
            session, ctx_b,
            vault_id=vid_b,
            slug="user-b-page",
            parsed=parse_vault_file(b"---\ntitle: User B Page\n---\nUser B content."),
        )
        await session.commit()

    # User B's session_with_rls tries to read User A's vault's page
    # RLS blocks this → PageNotFound raised (VAULT-02 verified)
    async for session in session_with_rls(ctx_b):
        with pytest.raises(PageNotFound):
            await read_page(session, vault_id=vid_a, slug="rls-secret")

    # User B CAN read their own page via test factory (RLS bypassed, positive control)
    async with f() as session:
        result = await session.execute(
            text("SELECT id, slug FROM pages WHERE vault_id = :vid AND slug = 'user-b-page'"),
            {"vid": vid_b},
        )
        row = result.fetchone()
        assert row is not None
        assert row.slug == "user-b-page"


@pytest.mark.asyncio
async def test_guc_not_leaked_after_page_request(test_engine: AsyncEngine):
    """After a session_with_rls context exits, app.current_user_id GUC is reset (no leak)."""
    from app.dependencies import session_with_rls

    f = _factory(test_engine)

    uid = uuid.uuid4()
    vid = uuid.uuid4()
    async with f() as session:
        await session.execute(
            text(
                "INSERT INTO users (id, username, role, password_hash, is_active, created_at, updated_at) "
                "VALUES (:id, :u, 'user', '$argon2id$v=19$m=65536,t=3,p=1$placeholder', true, now(), now())"
            ),
            {"id": uid, "u": f"guc-{uid.hex[:8]}"},
        )
        await session.execute(
            text(
                "INSERT INTO vaults (id, owner_user_id, kind, path, created_at, updated_at) "
                "VALUES (:id, :uid, 'private', :path, now(), now())"
            ),
            {"id": vid, "uid": uid, "path": f"/vaults/private/guc-{uid.hex[:8]}/"},
        )
        await session.commit()

    ctx = _ctx_for(uid)

    # Insert page via test factory (RLS bypassed) — session_with_rls can't see vault due to no RLS on vaults
    async with f() as session:
        await session.execute(
            text(
                "INSERT INTO pages (id, vault_id, slug, type, note_type, frontmatter, "
                "compiled_truth, timeline, content_hash, deleted_at, deleted_by, delete_reason, "
                "created_at, updated_at) "
                "VALUES (:id, :vid, 'guc-page', 'note', 'fleeting', '{}', 'content', "
                "'', 'def456', NULL, NULL, NULL, now(), now())"
            ),
            {"id": uuid.uuid4(), "vid": vid},
        )
        await session.commit()

    # Run session_with_rls to set GUC
    async for session in session_with_rls(ctx):
        await session.commit()  # no-op, just sets GUC then resets in finally

    # After session exits, check GUC is RESET on a fresh connection
    async with f() as check_session:
        result = await check_session.execute(
            text("SELECT current_setting('app.current_user_id', true) AS val")
        )
        row = result.fetchone()
        # Empty string means GUC was RESET
        assert row[0] == "" or row[0] is None
