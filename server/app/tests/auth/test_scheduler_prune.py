"""AUTH-03 / D-09 — login_attempts retention job."""
from __future__ import annotations

import pytest
from app.scheduler.jobs.prune_login_attempts import prune_login_attempts
from sqlalchemy import text

from app.auth.context import system_operation_context
from app.dependencies import session_with_rls

pytestmark = [pytest.mark.auth, pytest.mark.integration]


async def _seed_attempt(*, age_hours: int) -> None:
    async for session in session_with_rls(system_operation_context()):
        await session.execute(
            text(
                "INSERT INTO login_attempts (username, ip, attempted_at) "
                "VALUES ('seed_user', '127.0.0.1', now() - make_interval(hours => :h))"
            ),
            {"h": age_hours},
        )
        await session.commit()


async def _count_attempts() -> int:
    async for session in session_with_rls(system_operation_context()):
        return (await session.execute(text("SELECT count(*) FROM login_attempts WHERE username='seed_user'"))).scalar_one()
    return 0  # unreachable; satisfies type checker


async def test_prune_login_attempts_deletes_old_rows() -> None:
    # cleanup any pre-existing rows
    async for session in session_with_rls(system_operation_context()):
        await session.execute(text("DELETE FROM login_attempts WHERE username = 'seed_user'"))
        await session.commit()
    await _seed_attempt(age_hours=48)  # older than 24h retention
    before = await _count_attempts()
    assert before == 1
    deleted = await prune_login_attempts()
    assert deleted >= 1
    after = await _count_attempts()
    assert after == 0


async def test_prune_login_attempts_keeps_recent_rows() -> None:
    async for session in session_with_rls(system_operation_context()):
        await session.execute(text("DELETE FROM login_attempts WHERE username = 'seed_user'"))
        await session.commit()
    await _seed_attempt(age_hours=1)  # within 24h retention
    await prune_login_attempts()
    after = await _count_attempts()
    assert after == 1
    # cleanup
    async for session in session_with_rls(system_operation_context()):
        await session.execute(text("DELETE FROM login_attempts WHERE username = 'seed_user'"))
        await session.commit()
