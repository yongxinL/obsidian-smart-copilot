"""Async DB engine + pgvector type registration + session factory.

D-08: pgvector vector type registered via SQLAlchemy connect event +
dbapi_connection.run_async(register_vector). Runs once per newly opened
connection; covers all callers (background jobs, CLI, tests).

D-09: This module owns the engine + event + session_factory. dependencies.py
imports async_session_factory from here. main.py NEVER creates the engine.
alembic/env.py NEVER imports this module (it uses its own sync psycopg2 engine).
"""

from __future__ import annotations

from pgvector.asyncpg import register_vector
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.settings import settings

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=settings.debug,
)


@event.listens_for(engine.sync_engine, "connect")
def _register_vector_type(dbapi_connection, connection_record):  # noqa: ARG001
    """Register pgvector codec on every new asyncpg connection.

    Why engine.sync_engine, not engine: events cannot register on AsyncEngine.
    Why run_async, not connect_args={'init': ...}: SQLAlchemy's adapted DBAPI
    connection exposes run_async() that bridges sync event handlers to async
    driver calls. The connect_args={'init': ...} pattern is for raw asyncpg
    pools, not SQLAlchemy AsyncEngine. [Pattern 3 in 01a-RESEARCH.md]
    """
    dbapi_connection.run_async(register_vector)


@event.listens_for(engine.sync_engine, "reset")
def _on_pool_reset(dbapi_conn, connection_record, reset_state):  # noqa: ARG001
    """Defense-in-depth: scrub app.* GUCs on connection check-in (Landmine #1).

    Even if get_db_session's finally:-block fails (exception, future code path
    change), this listener fires on every pool reset. Synchronous via dbapi
    cursor — runs before the connection is reused by another request.
    """
    try:
        with dbapi_conn.cursor() as cur:
            cur.execute("RESET app.current_user_id")
            cur.execute("RESET app.current_user_role")
            cur.execute("RESET app.request_id")
    except Exception:  # noqa: BLE001 — never block pool reset
        pass


async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
