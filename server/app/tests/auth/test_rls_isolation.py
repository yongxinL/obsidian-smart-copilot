"""TEST-02 / D-30 — RLS isolation across pooled connections.

The headline test for Phase 1b. Belt-and-braces verification:
  1. dependencies.session_with_rls SET-then-RESET is the primary mechanism.
  2. database.py PoolEvents.reset listener is the fail-safe.
  3. RLS POLICY on provider_keys (alembic 0002) enforces row-level isolation.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.auth.context import SYSTEM_USER_ID, OperationContext, system_operation_context
from app.dependencies import session_with_rls

pytestmark = [pytest.mark.auth, pytest.mark.integration]


def _ctx_for(user_id: uuid.UUID, *, role: str = "user", request_id: str = "test-rls") -> OperationContext:
    return OperationContext(
        user_id=user_id, role=role, transport="rest", remote=True,
        client_name="test", request_id=request_id,
    )


async def test_no_guc_leak_after_request(test_engine: AsyncEngine, seed_user_a: uuid.UUID) -> None:
    """After a session_with_rls scope exits, current_setting('app.current_user_id') is empty."""
    async for session in session_with_rls(_ctx_for(seed_user_a)):
        row = (await session.execute(text("SELECT current_setting('app.current_user_id', true)"))).first()
        assert row[0] == str(seed_user_a)
    # Open a fresh session against the SAME engine (= same pool)
    factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as fresh:
        row = (await fresh.execute(text("SELECT current_setting('app.current_user_id', true)"))).first()
        # PoolEvents.reset listener AND get_db_session finally:-block both scrubbed
        assert row[0] == "" or row[0] is None


async def test_user_b_sees_empty_guc(test_engine: AsyncEngine, seed_user_a: uuid.UUID, seed_user_b: uuid.UUID) -> None:
    """User A request, then User B opens a fresh session — must NOT inherit user A's GUC."""
    async for sess_a in session_with_rls(_ctx_for(seed_user_a)):
        await sess_a.execute(text("SELECT 1"))
    # User B: completely fresh session, no SET
    factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as sess_b:
        row = (await sess_b.execute(text("SELECT current_setting('app.current_user_id', true)"))).first()
        assert row[0] in ("", None), f"GUC leaked across pool: {row[0]!r} != ''"


async def test_cross_user_read_blocked(test_engine: AsyncEngine, seed_user_a: uuid.UUID, seed_user_b: uuid.UUID) -> None:
    """RLS POLICY: User A inserts a provider_keys row; User B sees zero rows."""
    # User A inserts
    async for sess_a in session_with_rls(_ctx_for(seed_user_a)):
        await sess_a.execute(
            text(
                "INSERT INTO provider_keys (id, user_id, provider, encrypted_key, key_hint, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :uid, 'openai', '\\x00'::bytea, 'sk-...test', now(), now())"
            ),
            {"uid": str(seed_user_a)},
        )
        await sess_a.commit()
    # User B tries to read
    async for sess_b in session_with_rls(_ctx_for(seed_user_b)):
        rows = (await sess_b.execute(text("SELECT count(*) FROM provider_keys"))).scalar_one()
        assert rows == 0, f"RLS leak: user B saw {rows} rows from user A"
    # Cleanup as user A
    async for sess_a in session_with_rls(_ctx_for(seed_user_a)):
        await sess_a.execute(text("DELETE FROM provider_keys WHERE user_id = :uid"), {"uid": str(seed_user_a)})
        await sess_a.commit()


async def test_system_context_bypass(test_engine: AsyncEngine) -> None:
    """system_operation_context sets app.current_user_id = SYSTEM_USER_ID; can write audit_log."""
    ctx = system_operation_context()
    async for session in session_with_rls(ctx):
        row = (await session.execute(text("SELECT current_setting('app.current_user_id', true)"))).first()
        assert row[0] == str(SYSTEM_USER_ID)
        # audit_log is NOT in RLS_TABLES — write succeeds
        await session.execute(
            text(
                "INSERT INTO audit_log (user_id, action, request_id, created_at) "
                "VALUES (:uid, 'system_test', :rid, now())"
            ),
            {"uid": str(SYSTEM_USER_ID), "rid": ctx.request_id},
        )
        await session.commit()
        # Cleanup
        await session.execute(
            text("DELETE FROM audit_log WHERE action = 'system_test' AND request_id = :rid"),
            {"rid": ctx.request_id},
        )
        await session.commit()


async def test_pool_reset_scrubs_guc(test_engine: AsyncEngine) -> None:
    """Bypass session_with_rls and tamper directly: PoolEvents.reset must scrub."""
    factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    # Tamper: set GUC outside of session_with_rls
    async with factory() as session:
        await session.execute(
            text("SELECT set_config('app.current_user_id', :uid, false)"),
            {"uid": "deadbeef-dead-beef-dead-beefdeadbeef"},
        )
        await session.commit()
    # Connection returns to pool — PoolEvents.reset listener fires.
    # Open a new session and verify GUC is empty.
    async with factory() as fresh:
        row = (await fresh.execute(text("SELECT current_setting('app.current_user_id', true)"))).first()
        assert row[0] in ("", None), (
            f"PoolEvents.reset listener did not scrub GUC: still {row[0]!r}"
        )
