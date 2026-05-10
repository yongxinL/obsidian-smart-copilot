"""Phase 1a boot integration tests.

Covers INFRA-03 (pgvector extension), INFRA-07 (asyncpg runtime), TEST-01
(real PostgreSQL via testcontainers, no DB mocks). All tests in this module
are auto-marked async by pytest-asyncio asyncio_mode = auto (D-04).
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.main import app
from app.models import Base

pytestmark = pytest.mark.integration


async def test_health_endpoint() -> None:
    """GET /health returns 200 with body {"status": "ok"} (INFRA-01 success criterion)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_db_connection(db_session) -> None:
    """asyncpg async session executes against the testcontainer DB (INFRA-07)."""
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar_one() == 1


async def test_pgvector_extension(db_session) -> None:
    """pgvector extension is installed and reachable (INFRA-03)."""
    row = (
        await db_session.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        )
    ).first()
    assert row is not None
    assert row[0] == "vector"


async def test_all_tables_present(db_session) -> None:
    """Alembic upgrade head created every domain table (D-05, D-06)."""
    rows = (
        await db_session.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        )
    ).all()
    actual = {r[0] for r in rows}
    expected = set(Base.metadata.tables.keys())
    missing = expected - actual
    assert not missing, f"missing tables in DB: {sorted(missing)}"


async def test_apscheduler_jobs_not_in_metadata() -> None:
    """apscheduler_jobs MUST NOT appear in Base.metadata (CLAUDE.md anti-pattern)."""
    assert "apscheduler_jobs" not in Base.metadata.tables


async def test_rollback_isolation_first(db_session) -> None:
    """First half of D-02 rollback isolation check.

    Insert a row using a raw INSERT against the system_config table (which
    has a simple shape: key TEXT PK, value JSONB). Rollback at teardown means
    test_rollback_isolation_second must NOT see this row.
    """
    await db_session.execute(
        text(
            "INSERT INTO system_config (key, value) VALUES ('test_isolation_marker', '\"first\"'::jsonb)"
        )
    )
    row = (
        await db_session.execute(
            text("SELECT value FROM system_config WHERE key = 'test_isolation_marker'")
        )
    ).first()
    assert row is not None


async def test_rollback_isolation_second(db_session) -> None:
    """Second half — verify previous test's row was rolled back (D-02)."""
    row = (
        await db_session.execute(
            text("SELECT value FROM system_config WHERE key = 'test_isolation_marker'")
        )
    ).first()
    assert row is None, (
        "rollback-per-test isolation broken: previous test's data leaked"
    )
