"""User CRUD service (transport-agnostic).

D-10: usernames are case-folded + stripped at the application layer before
write/query. users.username (citext-style) is the canonical form.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import OperationContext
from app.auth.password import hash_password
from app.models.user import User


class UsernameExists(Exception):
    ...


class InvalidRole(Exception):
    ...


SYSTEM_USERNAME = "system"


def normalize_username(raw: str) -> str:
    """D-10 — case-fold + strip."""
    return raw.strip().casefold()


async def get_user_by_username(session: AsyncSession, raw_username: str) -> User | None:
    username = normalize_username(raw_username)
    return (await session.execute(select(User).where(User.username == username))).scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await session.get(User, user_id)


async def create_user(
    session: AsyncSession,
    ctx: OperationContext,
    *,
    username: str,
    password_plain: str,
    role: str = "user",
    email: str | None = None,
) -> User:
    """Create a new user. Refuses username='system' (the seeded admin must not be re-creatable)."""
    username_n = normalize_username(username)
    if username_n == SYSTEM_USERNAME:
        raise UsernameExists("'system' is reserved")
    if role not in ("admin", "user"):
        raise InvalidRole(role)
    existing = await get_user_by_username(session, username_n)
    if existing is not None:
        raise UsernameExists(username_n)
    ph = await hash_password(password_plain)
    user = User(
        id=uuid.uuid4(),
        username=username_n,
        email=email,
        password_hash=ph,
        role=role,
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


async def set_password(session: AsyncSession, user: User, new_password: str) -> None:
    user.password_hash = await hash_password(new_password)


async def set_role(session: AsyncSession, user: User, role: str) -> None:
    if role not in ("admin", "user"):
        raise InvalidRole(role)
    user.role = role