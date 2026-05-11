"""Vault resolution helper — transport-agnostic per REST-06.

Phase 1d: each user has exactly one private vault; resolve_user_vault_id returns it.
Imported by:
  - server/app/mcp/tools/brain.py    (Plan 02)
  - server/app/routes/pages.py        (Plan 03)
  - server/app/routes/search.py       (Plan 03)
  - server/app/routes/vault.py       (Plan 03)
  - server/app/cli/page.py            (Plan 05)
  - server/app/cli/stats.py           (Plan 05)

NO FastAPI imports. NO MCP imports. Lives in services/ so callers from any
transport can compose with it without crossing layer boundaries.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vault import Vault


class VaultNotFound(Exception):
    """Raised when a user has no private vault yet."""


async def resolve_user_vault_id(session: AsyncSession, user_id: uuid.UUID) -> uuid.UUID:
    """Return the UUID of the caller's private vault.

    Phase 1d invariant: exactly one private vault per user.
    Raises VaultNotFound if no private vault exists for the user.
    """
    row = (
        await session.execute(
            select(Vault.id)
            .where(
                Vault.owner_user_id == user_id,
                Vault.kind == "private",
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        raise VaultNotFound(f"no private vault for user {user_id}")
    return row
