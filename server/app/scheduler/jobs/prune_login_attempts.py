"""Hourly retention job for login_attempts (D-09).

Phase 1b ships the function AND registers it with APScheduler 3.x
AsyncIOScheduler via the extended scheduler/run.py (see sub-action below).
Phase 4 will swap to SQLAlchemyJobStore for durability across restarts;
Phase 1b uses the default in-memory store, which is sufficient because
the job is idempotent and re-registers on every supervisord restart.

CLAUDE.md: module-level function (no closures, no lambdas) — APScheduler 3.x
SQLAlchemyJobStore pickles job args.
"""

from __future__ import annotations

from sqlalchemy import text

from app.auth.context import system_operation_context
from app.dependencies import session_with_rls
from app.settings import settings


async def prune_login_attempts() -> int:
    """DELETE rows older than retention_hours. Returns the number deleted."""
    ctx = system_operation_context(
        request_id="prune_login_attempts", client_name="scheduler"
    )
    deleted = 0
    async for session in session_with_rls(ctx):
        result = await session.execute(
            text(
                "DELETE FROM login_attempts "
                "WHERE attempted_at < now() - make_interval(hours => :h)"
            ),
            {"h": settings.login_attempts_retention_hours},
        )
        deleted = result.rowcount or 0
        await session.commit()
    return deleted
