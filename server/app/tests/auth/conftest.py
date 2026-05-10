<<<<<<< HEAD
"""Auth test fixtures — seed users for integration tests (TEST-02 / D-30)."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.auth.password import hash_password


@pytest.fixture
async def seed_basic_user(test_engine: AsyncEngine) -> uuid.UUID:
    """Create a regular user (seed_basic_user) in the test DB and return their UUID.

    Used by mcp_tokens and provider_keys integration tests. User owns rows
    under RLS so tests can assert isolation.
    """
    user_id = uuid.uuid4()
    factory = text(
        "INSERT INTO users (id, username, email, password_hash, role, is_active, created_at, updated_at) "
        "VALUES (:id, :username, :email, :password_hash, 'user', true, now(), now())"
    )
    async with test_engine.begin() as conn:
        await conn.execute(
            factory,
            {
                "id": str(user_id),
                "username": f"test_basic_{user_id.hex[:8]}",
                "email": f"test_basic_{user_id.hex[:8]}@example.com",
                "password_hash": await hash_password("test-password-basic"),
            },
        )
    yield user_id
    # Cleanup
    async with test_engine.begin() as conn:
        await conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": str(user_id)})


@pytest.fixture
async def seed_user_a(test_engine: AsyncEngine) -> uuid.UUID:
    """Create a regular user (seed_user_a) in the test DB and return their UUID.

    Used by TEST-02 isolation tests. User owns provider_keys rows that
    test_cross_user_read_blocked asserts are invisible to seed_user_b.
    """
    user_id = uuid.uuid4()
    factory = text(
        "INSERT INTO users (id, username, email, password_hash, role, is_active, created_at, updated_at) "
        "VALUES (:id, :username, :email, :password_hash, 'user', true, now(), now())"
    )
    async with test_engine.begin() as conn:
        await conn.execute(
            factory,
            {
                "id": str(user_id),
                "username": f"test_user_a_{user_id.hex[:8]}",
                "email": f"test_a_{user_id.hex[:8]}@example.com",
                "password_hash": await hash_password("test-password-a"),
            },
        )
    yield user_id
    # Cleanup
    async with test_engine.begin() as conn:
        await conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": str(user_id)})


@pytest.fixture
async def seed_user_b(test_engine: AsyncEngine) -> uuid.UUID:
    """Create a regular user (seed_user_b) in the test DB and return their UUID.

    Used by TEST-02 isolation tests. B should never see A's provider_keys rows.
    """
    user_id = uuid.uuid4()
    factory = text(
        "INSERT INTO users (id, username, email, password_hash, role, is_active, created_at, updated_at) "
        "VALUES (:id, :username, :email, :password_hash, 'user', true, now(), now())"
    )
    async with test_engine.begin() as conn:
        await conn.execute(
            factory,
            {
                "id": str(user_id),
                "username": f"test_user_b_{user_id.hex[:8]}",
                "email": f"test_b_{user_id.hex[:8]}@example.com",
                "password_hash": await hash_password("test-password-b"),
            },
        )
    yield user_id
    # Cleanup
    async with test_engine.begin() as conn:
        await conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": str(user_id)})
=======
"""Function-scoped auth fixtures consuming session-scope test_engine.

Reuses postgres_container, test_engine, db_session from server/app/tests/conftest.py.
Adds: seed_user_a, seed_user_b, seed_admin_user, seed_basic_user.
Also adds: _patch_session_factory (session-scoped, autouse) — redirects
app.dependencies.async_session_factory to the testcontainer engine so that
session_with_rls() used in integration tests targets the test DB.
Every fixture takes test_engine (session-scope) and uses async_sessionmaker.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


@pytest_asyncio.fixture(scope="session", autouse=True, loop_scope="session")
async def _patch_session_factory(test_engine: AsyncEngine) -> AsyncIterator[None]:
    """Redirect session_with_rls to use the test engine pool (not prod DB).

    session_with_rls uses async_session_factory from app.database. Patch the
    module-level reference in app.dependencies so all integration tests in this
    package use the testcontainer engine.

    Also registers the production PoolEvents.reset listener on test_engine so
    GUC scrubbing works correctly.
    """
    import app.dependencies as deps

    @event.listens_for(test_engine.sync_engine, "reset")
    def _on_pool_reset(dbapi_conn, connection_record, reset_state):  # noqa: ARG001
        """Mirrors database.py _on_pool_reset — Landmine #1 fail-safe on test engine."""

        async def _scrub(conn):
            await conn.execute("RESET app.current_user_id")
            await conn.execute("RESET app.current_user_role")
            await conn.execute("RESET app.request_id")

        try:
            dbapi_conn.run_async(_scrub)
        except Exception:  # noqa: BLE001
            pass

    test_factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    original = deps.async_session_factory
    deps.async_session_factory = test_factory
    yield
    deps.async_session_factory = original


async def _seed_user(
    engine: AsyncEngine,
    *,
    username: str,
    role: str,
    password_hash: str = "$argon2id$v=19$m=65536,t=3,p=1$placeholder",
) -> uuid.UUID:
    uid = uuid.uuid4()
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        await session.execute(
            text(
                "INSERT INTO users (id, username, role, password_hash, is_active, created_at, updated_at) "
                "VALUES (:id, :u, :r, :ph, true, now(), now())"
            ),
            {"id": uid, "u": username, "r": role, "ph": password_hash},
        )
        await session.commit()
    return uid


@pytest_asyncio.fixture(loop_scope="session")
async def seed_user_a(test_engine: AsyncEngine) -> AsyncIterator[uuid.UUID]:
    """User A — fixed username 'alice'. Caller is responsible for cleanup or relying on rollback."""
    uid = await _seed_user(test_engine, username="alice", role="user")
    yield uid
    factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": uid})
        await session.commit()


@pytest_asyncio.fixture(loop_scope="session")
async def seed_user_b(test_engine: AsyncEngine) -> AsyncIterator[uuid.UUID]:
    uid = await _seed_user(test_engine, username="bob", role="user")
    yield uid
    factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": uid})
        await session.commit()


@pytest_asyncio.fixture(loop_scope="session")
async def seed_admin_user(test_engine: AsyncEngine) -> AsyncIterator[uuid.UUID]:
    uid = await _seed_user(test_engine, username="admin", role="admin")
    yield uid
    factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": uid})
        await session.commit()


@pytest_asyncio.fixture(loop_scope="session")
async def seed_basic_user(test_engine: AsyncEngine) -> AsyncIterator[uuid.UUID]:
    uid = await _seed_user(test_engine, username="basic", role="user")
    yield uid
    factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": uid})
        await session.commit()


import pytest_asyncio  # noqa: E402 (appended)

from app.auth.context import OperationContext  # noqa: E402
from app.dependencies import session_with_rls  # noqa: E402


@pytest_asyncio.fixture(loop_scope="session")
async def admin_token_pair(seed_admin_user):
    """Return (access_jwt, refresh_token, session_id) for the admin fixture."""
    from app.services.sessions import issue_session_pair
    from app.services.users import get_user_by_id

    ctx = OperationContext(
        user_id=seed_admin_user, role="admin", transport="rest", remote=True,
        client_name="test", request_id="fixture",
    )
    async for session in session_with_rls(ctx):
        user = await get_user_by_id(session, seed_admin_user)
        access, refresh, sid = await issue_session_pair(session, ctx, user=user)
        await session.commit()
        return access, refresh, sid
>>>>>>> worktree-agent-ab6ce35163019e143
