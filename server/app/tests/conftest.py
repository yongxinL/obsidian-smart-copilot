"""pytest fixtures: session-scoped testcontainer + rollback-per-test session.

D-01: testcontainers-python spins a throwaway PostgreSQL container per session.
D-02: rollback per test (function-scoped session inside transaction).
D-03: container lifecycle is once per session.
D-04: pytest-asyncio 1.x with asyncio_mode = auto, asyncio_default_fixture_loop_scope = session
       (pyproject.toml). NO event_loop fixture override (Pitfall 2).

FIXME(#3100): asyncio_default_test_loop_scope must match fixture loop_scope.
Root cause: session-scoped async fixtures run in the pytest session event loop.
Function-scoped tests run in a function-scoped event loop (separate from the
session loop). asyncpg detects this mismatch when the test tries to use
db_session (which is bound to the session-loop engine).
Fix: change asyncio_default_test_loop_scope to "session" so all tests run
in the same loop as the session-scoped fixtures. Rollback-per-test is preserved
by having db_session commit/rollback between tests.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import AsyncIterator
from pathlib import Path

import pytest_asyncio
from pgvector.asyncpg import register_vector
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer

from app.models import Base  # noqa: F401 — side-effect: registers all 32 tables

POSTGRES_IMAGE = "pgvector/pgvector:pg16"
SERVER_DIR = Path(__file__).resolve().parent.parent.parent  # server/


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def postgres_container() -> AsyncIterator[PostgresContainer]:
    """Boot a single PostgreSQL container for the whole pytest session (D-03).

    Uses @pytest_asyncio.fixture with session loop_scope so the container is
    created inside the pytest session event loop — not at module-load time.
    """
    with PostgresContainer(POSTGRES_IMAGE, driver=None) as pg:
        yield pg


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_engine(postgres_container: PostgresContainer) -> AsyncIterator:
    """Session-scoped async engine bound to the testcontainer, with pgvector registered.

    Uses session loop_scope so the engine + its connection pool are created in
    the same event loop as the session (shared with db_session fixtures).
    Alembic migrations run once at session start.
    """
    sync_url = postgres_container.get_connection_url()
    # testcontainers returns postgresql:// or postgresql+psycopg2://; normalize:
    base_url = sync_url.replace("postgresql+psycopg2://", "postgresql://", 1)
    async_url = base_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    psycopg2_url = base_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    engine = create_async_engine(async_url, echo=False)

    @event.listens_for(engine.sync_engine, "connect")
    def _register_vec(dbapi_connection, connection_record):  # noqa: ARG001
        dbapi_connection.run_async(register_vector)

    # Run Alembic migrations once against the test container (D-06: real migration).
    env = os.environ.copy()
    env["ALEMBIC_DATABASE_URL"] = psycopg2_url
    subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=str(SERVER_DIR),
        env=env,
        check=True,
        capture_output=True,
    )

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def db_session(test_engine) -> AsyncIterator[AsyncSession]:
    """Function-scoped DB session with rollback-per-test isolation (D-02).

    Opens a fresh session per test, yields it, rolls back at teardown.
    Each test gets a clean state — no data bleed between tests.
    """
    factory = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    async with factory() as session:
        try:
            yield session
        finally:
            try:
                await session.rollback()
            except Exception:  # noqa: BLE001 — defensive cleanup only
                pass
