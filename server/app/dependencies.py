"""FastAPI dependencies. D-09: this module owns get_db_session + RLS GUC.

CLAUDE.md mandates SET app.current_user_id (NOT SET LOCAL) and always RESET
in finally. SET LOCAL only lasts for the transaction; the request scope can
outlive the transaction. SET (session-level) followed by RESET in finally
guarantees no GUC bleed across pooled connections.

Phase 1a does not yet have authentication (Phase 1b), so this dependency
yields a session WITHOUT setting the GUC. The defensive RESET in finally
is the canonical shape so subsequent phases extend without restructuring.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            try:
                await session.execute(text("RESET app.current_user_id"))
            except Exception:  # noqa: BLE001 — defensive cleanup only
                pass
            await session.close()
