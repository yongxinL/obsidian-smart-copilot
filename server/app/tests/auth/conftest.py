"""Function-scoped auth fixtures consuming session-scope test_engine.

Reuses postgres_container, test_engine, db_session from server/app/tests/conftest.py.
Adds: seed_user_a, seed_user_b, seed_admin_user, seed_basic_user, system_context.
Every fixture takes test_engine (session-scope) and uses async_sessionmaker.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


async def _seed_user(
    engine: AsyncEngine, *, username: str, role: str, password_hash: str = "$argon2id$v=19$m=65536,t=3,p=1$placeholder"
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
async def seed_user_a(test_engine) -> AsyncIterator[uuid.UUID]:
    """User A — fixed username 'alice'. Caller is responsible for cleanup or relying on rollback."""
    uid = await _seed_user(test_engine, username="alice", role="user")
    yield uid
    # cleanup — RLS-bypassed via system context (we DELETE by id; CASCADE handles refs)
    factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": uid})
        await session.commit()


@pytest_asyncio.fixture(loop_scope="session")
async def seed_user_b(test_engine) -> AsyncIterator[uuid.UUID]:
    uid = await _seed_user(test_engine, username="bob", role="user")
    yield uid
    factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": uid})
        await session.commit()


@pytest_asyncio.fixture(loop_scope="session")
async def seed_admin_user(test_engine) -> AsyncIterator[uuid.UUID]:
    uid = await _seed_user(test_engine, username="admin", role="admin")
    yield uid
    factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": uid})
        await session.commit()


@pytest_asyncio.fixture(loop_scope="session")
async def seed_basic_user(test_engine) -> AsyncIterator[uuid.UUID]:
    uid = await _seed_user(test_engine, username="basic", role="user")
    yield uid
    factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": uid})
        await session.commit()