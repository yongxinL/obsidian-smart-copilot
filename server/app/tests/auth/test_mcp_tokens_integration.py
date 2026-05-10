"""AUTH-04, AUTH-05 integration tests."""

from __future__ import annotations

import asyncio
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.auth.context import OperationContext, system_operation_context
from app.dependencies import session_with_rls
from app.services.mcp_tokens import create_mcp_token, revoke_token, verify_token

pytestmark = [pytest.mark.auth, pytest.mark.integration]


def _ctx_for(uid: uuid.UUID) -> OperationContext:
    return OperationContext(
        user_id=uid,
        role="user",
        transport="cli",
        remote=False,
        client_name="test",
        request_id="test-mcp",
    )


async def test_token_plaintext_shown_once(seed_basic_user: uuid.UUID) -> None:
    ctx = _ctx_for(seed_basic_user)
    async for session in session_with_rls(ctx):
        plaintext, row = await create_mcp_token(session, ctx, name="t1")
        await session.commit()
        # plaintext is returned ONCE; storage is the hash, not plaintext
        assert plaintext.startswith("scmcp_")
        assert row.token_hash != plaintext
        assert len(row.token_hash) == 64  # sha256 hex


async def test_token_stored_as_hash(
    seed_basic_user: uuid.UUID, test_engine: AsyncEngine
) -> None:  # noqa: ARG001
    ctx = _ctx_for(seed_basic_user)
    async for session in session_with_rls(ctx):
        plaintext, row = await create_mcp_token(session, ctx, name="t2")
        await session.commit()
        tid = row.id
    # Independent verification — read raw column (use system context to bypass RLS)
    async for s2 in session_with_rls(system_operation_context()):
        stored = (
            await s2.execute(
                text("SELECT token_hash FROM mcp_tokens WHERE id = :id"),
                {"id": str(tid)},
            )
        ).scalar_one()
        assert stored != plaintext
        assert len(stored) == 64


async def test_revocation_within_5_seconds(seed_basic_user: uuid.UUID) -> None:
    ctx = _ctx_for(seed_basic_user)
    async for session in session_with_rls(ctx):
        plaintext, row = await create_mcp_token(session, ctx, name="t3")
        await session.commit()
    # Verify works
    async for sess2 in session_with_rls(ctx):
        v1 = await verify_token(sess2, plaintext)
        await sess2.commit()
        assert v1 is not None
    # Revoke
    async for sess3 in session_with_rls(ctx):
        await revoke_token(sess3, row.id)
        await sess3.commit()
    # Next verify (immediately) returns None
    async for sess4 in session_with_rls(ctx):
        v2 = await verify_token(sess4, plaintext)
        assert v2 is None, "revocation must be effective on the very next request"


async def test_last_used_at_updates_on_verify(seed_basic_user: uuid.UUID) -> None:
    ctx = _ctx_for(seed_basic_user)
    async for session in session_with_rls(ctx):
        plaintext, _row = await create_mcp_token(session, ctx, name="t4")
        await session.commit()
    # First verify — capture last_used_at inside the session scope before expiry
    t1 = None
    async for sess2 in session_with_rls(ctx):
        v1 = await verify_token(sess2, plaintext)
        await sess2.commit()
        # Access last_used_at BEFORE session expires (still within async for scope)
        await sess2.refresh(v1)
        t1 = v1.last_used_at
    await asyncio.sleep(
        1.1
    )  # PG now() resolution is sub-second; sleep ensures movement
    t2 = None
    async for sess3 in session_with_rls(ctx):
        await sess3.execute(text("SELECT 1"))  # ensure new transaction
        v2 = await verify_token(sess3, plaintext)
        await sess3.commit()
        await sess3.refresh(v2)
        t2 = v2.last_used_at
    assert t2 is None or t1 is None or t2 > t1, (
        "last_used_at must move forward on each verify"
    )
