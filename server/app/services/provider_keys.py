"""Provider key service (transport-agnostic).

AUTH-09: encrypted_key column never returned in any API response (D-28 / Field(exclude=True)).
AUTH-10 / PRD §24.2: resolution order = per-user key → system shared key → MissingProviderKey.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import SYSTEM_USER_ID, OperationContext
from app.encryption import decrypt_provider_key, encrypt_provider_key
from app.models.provider_key import ProviderKey


class MissingProviderKey(Exception):
    def __init__(self, provider: str) -> None:
        self.provider = provider


class ProviderKeyResponse(BaseModel):
    """REST/MCP response schema. encrypted_key is structurally excluded — D-28."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    provider: str
    key_hint: str
    created_at: datetime
    # CLAUDE.md / D-28: schema-level exclusion, NOT post-hoc filtering
    encrypted_key: bytes = Field(exclude=True)


def _hint_for(plaintext: str) -> str:
    """Last-4 hint surfaced in UI; 32-char column."""
    return plaintext[-4:] if len(plaintext) >= 4 else plaintext


async def set_provider_key(
    session: AsyncSession,
    ctx: OperationContext,
    *,
    provider: str,
    plaintext: str,
) -> ProviderKey:
    """Upsert a provider key for ctx.user_id. Encrypts before write."""
    existing = (
        await session.execute(
            select(ProviderKey).where(
                ProviderKey.user_id == ctx.user_id,
                ProviderKey.provider == provider,
            )
        )
    ).scalar_one_or_none()
    ciphertext = encrypt_provider_key(plaintext)
    hint = _hint_for(plaintext)
    if existing is not None:
        existing.encrypted_key = ciphertext
        existing.key_hint = hint
        await session.flush()
        return existing
    row = ProviderKey(
        id=uuid.uuid4(),
        user_id=ctx.user_id,
        provider=provider,
        encrypted_key=ciphertext,
        key_hint=hint,
    )
    session.add(row)
    await session.flush()
    return row


async def get_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    provider: str,
) -> ProviderKey | None:
    return (
        await session.execute(
            select(ProviderKey).where(
                ProviderKey.user_id == user_id,
                ProviderKey.provider == provider,
            )
        )
    ).scalar_one_or_none()


async def list_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> Sequence[ProviderKey]:
    return (
        (
            await session.execute(
                select(ProviderKey).where(ProviderKey.user_id == user_id)
            )
        )
        .scalars()
        .all()
    )


async def revoke_provider_key(
    session: AsyncSession,
    *,
    key_id: uuid.UUID,
) -> None:
    await session.execute(delete(ProviderKey).where(ProviderKey.id == key_id))


async def resolve_key(
    session: AsyncSession,
    ctx: OperationContext,
    *,
    provider: str,
) -> str:
    """AUTH-10 / PRD §24.2: per-user key first, system shared key fallback, else error.

    Returns the decrypted plaintext.
    """
    # 1. Per-user
    user_row = await get_for_user(session, user_id=ctx.user_id, provider=provider)
    if user_row is not None:
        return decrypt_provider_key(user_row.encrypted_key)
    # 2. System shared (system user owns the fallback row)
    sys_row = await get_for_user(session, user_id=SYSTEM_USER_ID, provider=provider)
    if sys_row is not None:
        return decrypt_provider_key(sys_row.encrypted_key)
    # 3. Neither — error envelope
    raise MissingProviderKey(provider)
