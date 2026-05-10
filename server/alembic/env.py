"""Alembic env.py.

D-09: This module uses a SYNC psycopg2 engine and NEVER imports app.database
(the async runtime engine). It imports app.models so that Base.metadata
enumerates the complete schema (D-05).

Pitfall 4: include_object filter excludes apscheduler_jobs from autogenerate.
APScheduler manages that table itself; Alembic must ignore it.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# Make `app` importable when running `alembic` from the server/ directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import the aggregate models package — side-effect populates Base.metadata.
import app.models  # noqa: F401, E402
from app.models.base import Base  # noqa: E402
from app.settings import settings  # noqa: E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_object(object_, name, type_, reflected, compare_to):
    """Exclude apscheduler_jobs from autogenerate (Pitfall 4 / CLAUDE.md)."""
    if type_ == "table" and name == "apscheduler_jobs":
        return False
    return True


def _resolve_url() -> str:
    """Use ALEMBIC_DATABASE_URL (psycopg2) — never the runtime asyncpg URL."""
    explicit = os.environ.get("ALEMBIC_DATABASE_URL")
    if explicit:
        return explicit
    return settings.alembic_database_url


def run_migrations_offline() -> None:
    url = _resolve_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _resolve_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
