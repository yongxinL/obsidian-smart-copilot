"""MCP bearer token service (transport-agnostic).

AUTH-04: plaintext shown once at create; storage column = SHA-256 hex.
AUTH-05: last_used_at updated on every successful verify (DB UPDATE per request — homelab scale fine).
AUTH-04 success criterion #2: revocation effective in <5s — DB-only path (no in-memory cache).
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import OperationContext
from app.auth.mcp_tokens import generate_token, sha256_token_hash
from app.models.mcp_token import MCPToken as McpToken


async def create_mcp_token(
    session: AsyncSession,
    ctx: OperationContext,
    *,
    name: str | None = None,
) -> tuple[str, McpToken]:
    """Create a new MCP bearer for the calling user.

    Returns (plaintext, row). Caller is responsible for showing plaintext
    to the operator ONCE; the DB only ever stores the sha256 hex.
    """
    plaintext, token_hash, _last4 = generate_token()
    row = McpToken(
        id=uuid.uuid4(),
        user_id=ctx.user_id,
        name=name,
        token_hash=token_hash,
    )
    session.add(row)
    await session.flush()
    return plaintext, row


async def list_for_user(session: AsyncSession, user_id: uuid.UUID) -> Sequence[McpToken]:
    result = await session.execute(
        select(McpToken).where(McpToken.user_id == user_id, McpToken.revoked_at.is_(None))
    )
    return result.scalars().all()


async def revoke_token(session: AsyncSession, token_id: uuid.UUID) -> None:
    await session.execute(
        update(McpToken).where(McpToken.id == token_id).values(revoked_at=func.now())
    )


async def verify_token(session: AsyncSession, plaintext: str) -> McpToken | None:
    """DB-only verify path. Updates last_used_at on success.

    Revocation is effective on the next call (<100ms) — no worker-local cache.
    """
    h = sha256_token_hash(plaintext)
    result = await session.execute(
        select(McpToken).where(
            McpToken.token_hash == h,
            McpToken.revoked_at.is_(None),
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    await session.execute(
        update(McpToken).where(McpToken.id == row.id).values(last_used_at=func.now())
    )
    return row
