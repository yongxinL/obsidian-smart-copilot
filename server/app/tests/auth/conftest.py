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