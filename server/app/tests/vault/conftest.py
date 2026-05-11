"""Function-scoped vault fixtures consuming session-scope test_engine.

Reuses postgres_container, test_engine from server/app/tests/conftest.py.
Adds: tmp_vault_dir, seed_vault, seed_page, system_ctx.
Also adds: _patch_session_factory (session-scoped, autouse) — redirects
app.dependencies.async_session_factory to the testcontainer engine so that
session_with_rls() in vault service tests targets the test DB.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def _patch_session_factory(test_engine: AsyncEngine) -> AsyncIterator[None]:
    """Redirect session_with_rls to use the test engine pool (not prod DB).

    Mirrors server/app/tests/auth/conftest.py _patch_session_factory exactly.
    Also registers the production PoolEvents.reset listener on test_engine.
    """
    import app.dependencies as deps

    @event.listens_for(test_engine.sync_engine, "reset")
    def _on_pool_reset(dbapi_conn, connection_record, reset_state):  # noqa: ARG001
        async def _scrub(conn):
            await conn.execute("RESET app.current_user_id")
            await conn.execute("RESET app.current_user_role")
            await conn.execute("RESET app.request_id")

        try:
            dbapi_conn.run_async(_scrub)
        except Exception:  # noqa: BLE001
            pass

    test_factory = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=AsyncSession
    )
    original = deps.async_session_factory
    deps.async_session_factory = test_factory
    yield
    deps.async_session_factory = original


@pytest.fixture
def tmp_vault_dir(tmp_path: Path) -> Path:
    """Return a temporary directory simulating a private vault root."""
    vault_root = tmp_path / "vaults" / "private" / "testuser"
    vault_root.mkdir(parents=True)
    return vault_root


@pytest_asyncio.fixture(loop_scope="session")
async def seed_user_for_vault(test_engine: AsyncEngine) -> AsyncIterator[uuid.UUID]:
    """Seed a user for vault tests. Returns the user UUID."""
    uid = uuid.uuid4()
    factory = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=AsyncSession
    )
    async with factory() as session:
        await session.execute(
            text(
                "INSERT INTO users (id, username, role, password_hash, is_active, created_at, updated_at) "
                "VALUES (:id, :u, 'user', '$argon2id$v=19$m=65536,t=3,p=1$placeholder', true, now(), now())"
            ),
            {"id": uid, "u": f"vaultuser-{uid.hex[:8]}"},
        )
        await session.commit()
    yield uid
    async with factory() as session:
        await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": uid})
        await session.commit()


@pytest_asyncio.fixture(loop_scope="session")
async def seed_vault(
    test_engine: AsyncEngine, seed_user_for_vault: uuid.UUID
) -> AsyncIterator[uuid.UUID]:
    """Seed a private vault row for the vault test user. Returns vault UUID."""
    vid = uuid.uuid4()
    factory = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=AsyncSession
    )
    async with factory() as session:
        await session.execute(
            text(
                "INSERT INTO vaults (id, owner_user_id, kind, path, created_at, updated_at) "
                "VALUES (:id, :uid, 'private', :path, now(), now())"
            ),
            {
                "id": vid,
                "uid": seed_user_for_vault,
                "path": f"/vaults/private/vaultuser-{seed_user_for_vault.hex[:8]}/",
            },
        )
        await session.commit()
    yield vid
    async with factory() as session:
        await session.execute(text("DELETE FROM vaults WHERE id = :id"), {"id": vid})
        await session.commit()


@pytest_asyncio.fixture(loop_scope="session")
async def seed_page(
    test_engine: AsyncEngine, seed_vault: uuid.UUID
) -> AsyncIterator[uuid.UUID]:
    """Seed a minimal page row for upsert/soft-delete tests. Returns page UUID."""
    pid = uuid.uuid4()
    factory = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=AsyncSession
    )
    async with factory() as session:
        await session.execute(
            text(
                "INSERT INTO pages (id, vault_id, slug, type, note_type, frontmatter, "
                "compiled_truth, timeline, content_hash, deleted_at, deleted_by, delete_reason, "
                "created_at, updated_at) "
                "VALUES (:id, :vid, 'seed-page', 'note', 'fleeting', '{}', 'Seed content', "
                "'', 'abc123def456789a', NULL, NULL, NULL, now(), now())"
            ),
            {"id": pid, "vid": seed_vault},
        )
        await session.commit()
    yield pid
    async with factory() as session:
        await session.execute(text("DELETE FROM pages WHERE id = :id"), {"id": pid})
        await session.commit()


@pytest.fixture
def system_ctx():
    """Return a system OperationContext for watchdog/scheduler use."""
    from app.auth.context import system_operation_context

    return system_operation_context(request_id="test", client_name="test-vault")
