---
phase: 01a
plan: 03
type: execute
wave: 3
depends_on: [01a-01, 01a-02]
files_modified:
  - server/app/settings.py
  - server/app/database.py
  - server/app/dependencies.py
  - server/app/main.py
  - server/app/routes/__init__.py
  - server/app/routes/health.py
  - server/alembic.ini
  - server/alembic/env.py
  - server/alembic/script.py.mako
  - server/alembic/versions/0001_initial_schema.py
  - server/app/tests/__init__.py
  - server/app/tests/conftest.py
  - server/app/tests/integration/__init__.py
  - server/app/tests/integration/test_boot.py
autonomous: true
requirements: [INFRA-07, INFRA-03, TEST-01]
must_haves:
  truths:
    - "FastAPI app starts and GET /health returns 200 with body {status: ok}"
    - "PostgreSQL pgvector extension is created during migration; vector type usable"
    - "Alembic upgrade head runs against testcontainer DB and creates all 32 tables"
    - "Test suite (pytest) executes against a real PostgreSQL container; zero mocks for DB"
    - "Each test runs inside a rollback transaction (no data bleed between tests)"
    - "asyncpg is the runtime driver; psycopg2 is the Alembic driver — never the reverse"
    - "apscheduler_jobs is excluded from Alembic autogenerate via include_object filter"
  artifacts:
    - path: "server/app/database.py"
      provides: "Async engine + pgvector connect event + async_session_factory"
    - path: "server/app/dependencies.py"
      provides: "get_db_session FastAPI dependency with RLS GUC discipline"
    - path: "server/app/settings.py"
      provides: "pydantic-settings BaseSettings"
    - path: "server/app/main.py"
      provides: "FastAPI app factory + lifespan; /health route mounted"
    - path: "server/app/routes/health.py"
      provides: "GET /health returns {status: ok}"
    - path: "server/alembic/env.py"
      provides: "sync psycopg2 alembic env with all models imported and apscheduler_jobs excluded"
    - path: "server/alembic/versions/0001_initial_schema.py"
      provides: "Initial migration creating all 32 tables + pgvector extension + RLS ENABLE"
    - path: "server/app/tests/conftest.py"
      provides: "Session-scoped testcontainer + async engine + rollback-per-test fixture"
    - path: "server/app/tests/integration/test_boot.py"
      provides: "Boot integration tests (health, pgvector ext, DB connection, table presence)"
  key_links:
    - from: "alembic/env.py"
      to: "Base.metadata"
      via: "import app.models (side-effect)"
      pattern: "import app.models"
    - from: "database.py engine connect event"
      to: "pgvector.asyncpg.register_vector"
      via: "dbapi_connection.run_async(register_vector)"
      pattern: "run_async.register_vector"
    - from: "dependencies.py get_db_session"
      to: "PostgreSQL session GUC"
      via: "RESET app.current_user_id in finally"
      pattern: "RESET app.current_user_id"
    - from: "main.py"
      to: "routes/health.py"
      via: "include_router"
      pattern: "include_router"
    - from: "alembic/env.py include_object"
      to: "apscheduler_jobs exclusion"
      via: "include_object filter"
      pattern: "apscheduler_jobs"
---

<objective>
Wire up the runtime application layer (FastAPI app, async engine with pgvector registration, RLS-aware session dependency, settings), create the Alembic migration that builds the entire 32-table schema in one shot (D-06), and stand up the pytest+testcontainers harness so the full test suite runs against a real PostgreSQL container with rollback-per-test isolation (D-01, D-02, D-03, D-04).

After this plan, `cd server && pytest app/tests/` boots a fresh `pgvector/pgvector:pg16` container, runs Alembic, executes integration tests including a pgvector extension check, and exits clean.

Purpose: Establish the canonical patterns the next 10 phases build on. Module ownership is strict (D-09): database.py owns the engine + event + session_factory; dependencies.py owns the DB session dependency + RLS GUC; main.py is lifecycle only; alembic/env.py uses sync psycopg2 and never imports the runtime async engine.

Output: Application runtime + initial migration + test harness, all green.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.planning/REQUIREMENTS.md
@.planning/phases/01a-container-data-layer/01a-CONTEXT.md
@.planning/phases/01a-container-data-layer/01a-RESEARCH.md
@.planning/phases/01a-container-data-layer/01a-VALIDATION.md

<interfaces>
Models package contract from Plan 02 — do not re-derive. Use these directly.

From server/app/models/__init__.py:
- Importing app.models triggers side-effect registration of all 32 domain tables.
- `from app.models.base import Base, TimestampMixin`
- 32 tables on Base.metadata.tables: users, sessions, mcp_tokens, provider_keys, vaults, pages, page_versions, chunks, entities, links, timeline_events, tags, page_tags, jobs, audit_log, skills, recipes, eval_candidates, conversations, messages, memories, dream_audit_log, projects, operation_log, llm_usage, index_events, user_settings, system_config, mcp_servers, golden_query_suites, golden_queries, golden_query_runs.
- apscheduler_jobs is INTENTIONALLY NOT a model — APScheduler manages it (CLAUDE.md).

Multi-tenant tables (have user_id FK; will be RLS-ENABLED in 0001 migration):
provider_keys, sessions, mcp_tokens, pages (via vault), page_versions (via page), chunks (via page), entities (via vault), links (via page), timeline_events (via page), tags (via vault), page_tags (via page), eval_candidates, conversations, messages, memories, projects, llm_usage, index_events, user_settings, recipes (when namespace=user), skills (when namespace=user), dream_audit_log.

Single-tenant / system tables (no RLS):
users, audit_log, system_config, mcp_servers, jobs, vaults (kind=shared row), golden_query_suites, golden_queries, golden_query_runs, operation_log.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create app runtime — settings.py, database.py, dependencies.py, main.py, routes/health.py</name>
  <files>server/app/settings.py, server/app/database.py, server/app/dependencies.py, server/app/main.py, server/app/routes/__init__.py, server/app/routes/health.py</files>
  <read_first>
    - .planning/phases/01a-container-data-layer/01a-RESEARCH.md (Patterns 3, 8, 9: SQLAlchemy async engine + pgvector event, pydantic-settings, FastAPI lifespan)
    - .planning/phases/01a-container-data-layer/01a-CONTEXT.md (D-08, D-09 module ownership boundaries; D-13 env vars)
    - CLAUDE.md (Key Integration Patterns section: RLS Session GUC Discipline; module ownership)
    - server/pyproject.toml (verify Ruff target-version = py312 from Plan 01)
  </read_first>
  <action>
Create the runtime application files. Module ownership boundaries from D-09 are CRITICAL — do NOT cross them.

1. `server/app/settings.py` — pydantic-settings BaseSettings with all 6 env vars from D-13:

```python
"""Application settings loaded from environment + .env file (D-13)."""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str = Field(
        default="postgresql+asyncpg://smartcopilot:smartcopilot@localhost:5432/smartcopilot"
    )
    alembic_database_url: str = Field(
        default="postgresql+psycopg2://smartcopilot:smartcopilot@localhost:5432/smartcopilot"
    )
    test_database_url: str = Field(default="")
    smartcopilot_fernet_key: str = Field(default="")
    smartcopilot_host_url: str = Field(default="http://localhost:8000")
    debug: bool = Field(default=False)


settings = Settings()
```

2. `server/app/database.py` — engine + pgvector connect event + session factory (D-08, D-09):

```python
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


async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
```

3. `server/app/dependencies.py` — get_db_session with RLS GUC discipline (D-09 + CLAUDE.md):

```python
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
```

4. `server/app/routes/__init__.py`:

```python
"""HTTP route modules."""
```

5. `server/app/routes/health.py` — /health endpoint returning exactly {"status": "ok"}:

```python
"""Health endpoint. Phase 1a returns shallow {status: ok} only.

Per CONTEXT.md Claude's Discretion: full DB/pgvector/Fernet checks deferred
to Phase 6 (smartcopilot doctor).
"""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

6. `server/app/main.py` — FastAPI app factory + lifespan (D-09: lifecycle only):

```python
"""FastAPI application factory.

D-09: this module manages app lifecycle ONLY. It does NOT create the engine
(that lives in database.py and is initialized at import time so the connect
event listener registers before the first connection is opened).
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import engine  # import triggers connect event registration
from app.routes.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="Smart Copilot", version="0.0.0", lifespan=lifespan)
    app.include_router(health_router)
    return app


app = create_app()
```

After writing, run `cd server && ruff check app/` and verify it exits 0.
  </action>
  <verify>
    <automated>cd server && ruff check app/ && python -c "from app.main import app; from app.database import async_session_factory, engine; assert async_session_factory is not None; print('OK', engine.sync_engine.dialect.name)"</automated>
  </verify>
  <acceptance_criteria>
    - All 6 files exist
    - `server/app/database.py` contains exact substring `@event.listens_for(engine.sync_engine, "connect")` (D-08)
    - `server/app/database.py` contains exact substring `dbapi_connection.run_async(register_vector)` (D-08)
    - `server/app/database.py` defines and exports `async_session_factory` and `engine`
    - `server/app/main.py` does NOT contain `create_async_engine` (D-09: main.py is lifecycle only, NOT engine creation)
    - `server/app/dependencies.py` does NOT contain `create_async_engine` (D-09)
    - `server/app/dependencies.py` contains exact substring `RESET app.current_user_id` (CLAUDE.md RLS discipline)
    - `server/app/dependencies.py` does NOT contain `SET LOCAL` (CLAUDE.md anti-pattern)
    - `server/app/settings.py` contains `class Settings(BaseSettings)` and a `database_url` field
    - `server/app/routes/health.py` contains `@router.get("/health")`
    - `server/app/main.py` contains `@asynccontextmanager` and `app.include_router(health_router)`
    - `cd server && ruff check app/` exits 0
    - `cd server && python -c "from app.main import app"` exits 0 (smoke import)
  </acceptance_criteria>
  <done>App runtime committed; module ownership preserved (D-09); ruff clean; FastAPI app importable.</done>
</task>

<task type="auto">
  <name>Task 2: Create Alembic env.py + alembic.ini + script template (sync psycopg2; apscheduler_jobs excluded)</name>
  <files>server/alembic.ini, server/alembic/env.py, server/alembic/script.py.mako, server/alembic/versions/.gitkeep</files>
  <read_first>
    - .planning/phases/01a-container-data-layer/01a-RESEARCH.md (Pattern 4: Alembic env.py for async models with sync psycopg2 engine; Pitfall 4: apscheduler_jobs exclusion)
    - .planning/phases/01a-container-data-layer/01a-CONTEXT.md (D-09 alembic env never imports runtime async engine)
    - server/app/models/__init__.py (verify aggregate import works)
    - CLAUDE.md (psycopg2 for Alembic only; apscheduler_jobs NOT in Alembic)
  </read_first>
  <action>
Create the Alembic configuration. Alembic uses the SYNC psycopg2 driver (postgresql+psycopg2://). Per D-09 it MUST NOT import `app.database`. Per Pitfall 4 it MUST exclude the `apscheduler_jobs` table from autogenerate.

1. `server/alembic.ini`:

```ini
[alembic]
script_location = alembic
file_template = %%(rev)s_%%(slug)s
prepend_sys_path = .
version_path_separator = os
output_encoding = utf-8

# sqlalchemy.url is overridden in env.py from settings.alembic_database_url
sqlalchemy.url =

[post_write_hooks]
hooks = ruff
ruff.type = console_scripts
ruff.entrypoint = ruff
ruff.options = format REVISION_SCRIPT_FILENAME

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARNING
handlers = console
qualname =

[logger_sqlalchemy]
level = WARNING
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

2. `server/alembic/env.py` — sync psycopg2 engine, imports app.models for autogenerate, excludes apscheduler_jobs:

```python
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

from alembic import context
from sqlalchemy import engine_from_config, pool

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
```

3. `server/alembic/script.py.mako` — standard Alembic template (copy verbatim):

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

4. `server/alembic/versions/.gitkeep` — empty file so the directory is tracked.

After writing, verify with `cd server && python -c "from alembic.config import Config; cfg = Config('alembic.ini'); print(cfg.get_main_option('script_location'))"`.
  </action>
  <verify>
    <automated>cd server && python -c "
import os
os.environ.setdefault('ALEMBIC_DATABASE_URL', 'postgresql+psycopg2://x:x@localhost/x')
from alembic.config import Config
cfg = Config('alembic.ini')
assert cfg.get_main_option('script_location') == 'alembic'
" && grep -q 'apscheduler_jobs' server/alembic/env.py && grep -q 'import app.models' server/alembic/env.py && ! grep -q 'from app.database' server/alembic/env.py && ! grep -q 'create_async_engine' server/alembic/env.py && grep -q 'postgresql+psycopg2' server/app/settings.py && (cd server && ruff check alembic/env.py)</automated>
  </verify>
  <acceptance_criteria>
    - `server/alembic.ini` exists and contains `script_location = alembic`
    - `server/alembic/env.py` contains exact substring `import app.models` (side-effect import per D-09)
    - `server/alembic/env.py` contains a function or expression that returns False for table named `apscheduler_jobs` (Pitfall 4 / CLAUDE.md)
    - `server/alembic/env.py` does NOT contain `from app.database` (D-09: never import runtime engine)
    - `server/alembic/env.py` does NOT contain `create_async_engine` (D-09: psycopg2 only)
    - `server/alembic/env.py` references `settings.alembic_database_url` or `ALEMBIC_DATABASE_URL` env var
    - `server/alembic/script.py.mako` exists with the standard Alembic template structure
    - `server/alembic/versions/.gitkeep` exists
    - `cd server && ruff check alembic/env.py` exits 0
    - `cd server && python -c "from alembic.config import Config; Config('alembic.ini')"` exits 0
  </acceptance_criteria>
  <done>Alembic configured with sync psycopg2; app.models imported for autogenerate; apscheduler_jobs excluded; ruff clean.</done>
</task>

<task type="auto">
  <name>Task 3: Author 0001_initial_schema.py — full 32-table schema + pgvector extension + RLS ENABLE</name>
  <files>server/alembic/versions/0001_initial_schema.py</files>
  <read_first>
    - server/app/models/ (every file — Plan 02 output, definitive column shapes)
    - .planning/phases/01a-container-data-layer/01a-RESEARCH.md (Pattern 7 HNSW index; Complete Domain Model List "Required indexes" section)
    - .planning/phases/01a-container-data-layer/01a-CONTEXT.md (D-06: single 0001_initial_schema.py; D-07 multi-tenant tables; Open Question 3: ENABLE RLS yes, CREATE POLICY no)
    - CLAUDE.md (HNSW index params m=16, ef_construction=64, vector_cosine_ops; encrypted_key BYTEA)
  </read_first>
  <action>
Generate the initial migration. Strategy: use Alembic autogenerate as a STARTING POINT, then manually add:
1. `CREATE EXTENSION IF NOT EXISTS vector` as the FIRST upgrade statement (before any column references VECTOR)
2. PostgreSQL ENUM type creation (Alembic autogenerate sometimes misses these; verify all enums introduced in Plan 02 are explicitly created)
3. HNSW index on `chunks.embedding` with `vector_cosine_ops`, `m=16`, `ef_construction=64`
4. GIN index on `chunks.tsv`
5. Standard B-tree indexes: `pages.slug`, `links.src_page_id`, `links.dst_entity_id`
6. GIN index on `pages.frontmatter`
7. `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` AND `FORCE ROW LEVEL SECURITY` for every multi-tenant table (per Open Question 3 resolution: schema-level enable in 1a; CREATE POLICY in 1b)

Procedure:

Step 1: Boot the dev DB and run autogenerate as a draft:
```bash
docker compose up -d postgres
sleep 5
cd server && export ALEMBIC_DATABASE_URL=postgresql+psycopg2://smartcopilot:smartcopilot@localhost:5432/smartcopilot
psql "$ALEMBIC_DATABASE_URL" -c "CREATE EXTENSION IF NOT EXISTS vector;"
alembic revision --autogenerate -m "initial_schema" --rev-id 0001
```

Step 2: Open the generated `server/alembic/versions/0001_initial_schema.py` and edit the `upgrade()` and `downgrade()` functions:

`upgrade()` MUST start with these statements BEFORE the autogenerated table creation block:
```python
op.execute("CREATE EXTENSION IF NOT EXISTS vector")
```

After the autogenerated `op.create_table(...)` calls, append manual index + RLS statements:
```python
# HNSW index on chunks.embedding (m=16, ef_construction=64, cosine ops per CLAUDE.md)
op.execute(
    "CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw_idx "
    "ON chunks USING hnsw (embedding vector_cosine_ops) "
    "WITH (m = 16, ef_construction = 64)"
)

# GIN index on tsvector for BM25 (Phase 2a)
op.execute(
    "CREATE INDEX IF NOT EXISTS chunks_tsv_gin_idx ON chunks USING gin (tsv)"
)

# GIN on pages.frontmatter for tag/property queries
op.execute(
    "CREATE INDEX IF NOT EXISTS pages_frontmatter_gin_idx "
    "ON pages USING gin (frontmatter)"
)

# B-tree indexes
op.create_index("pages_slug_idx", "pages", ["slug"])
op.create_index("links_src_page_id_idx", "links", ["src_page_id"])
op.create_index("links_dst_entity_id_idx", "links", ["dst_entity_id"])

# RLS ENABLE + FORCE on multi-tenant tables (CREATE POLICY deferred to Phase 1b — Open Question 3).
RLS_TABLES = [
    "provider_keys", "sessions", "mcp_tokens",
    "pages", "page_versions", "chunks",
    "entities", "links", "timeline_events",
    "tags", "page_tags",
    "eval_candidates", "conversations", "messages",
    "memories", "projects", "llm_usage",
    "index_events", "user_settings",
    "recipes", "skills", "dream_audit_log",
]
for tbl in RLS_TABLES:
    op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY")
```

`downgrade()` MUST drop in reverse order:
```python
for tbl in reversed(RLS_TABLES):
    op.execute(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY")
op.execute("DROP INDEX IF EXISTS pages_frontmatter_gin_idx")
op.execute("DROP INDEX IF EXISTS chunks_tsv_gin_idx")
op.execute("DROP INDEX IF EXISTS chunks_embedding_hnsw_idx")
# autogenerated drop_table calls...
op.execute("DROP EXTENSION IF EXISTS vector")
```

Step 3: Verify the migration applies cleanly:
```bash
cd server
alembic downgrade base
alembic upgrade head
psql "$ALEMBIC_DATABASE_URL" -c "\dt" | grep -c -E '^ public' | grep -q '^32'  # expect 32 tables (excluding alembic_version)
psql "$ALEMBIC_DATABASE_URL" -c "SELECT extname FROM pg_extension WHERE extname='vector';" | grep vector
psql "$ALEMBIC_DATABASE_URL" -c "SELECT relname FROM pg_class WHERE relname='chunks_embedding_hnsw_idx';" | grep chunks_embedding_hnsw_idx
```

Step 4: Format the file with `cd server && ruff format alembic/versions/0001_initial_schema.py` then run `ruff check alembic/versions/0001_initial_schema.py` (the per-file E402 ignore in pyproject.toml allows imports below the docstring header).

NOTE: If autogenerate produces ENUM types as separate `sa.Enum(...)` definitions inside the column rather than using `postgresql.ENUM(..., create_type=True)`, that is acceptable for this phase — Alembic creates the underlying TYPE automatically when it first encounters the enum.
  </action>
  <verify>
    <automated>test -f server/alembic/versions/0001_initial_schema.py && grep -q 'CREATE EXTENSION IF NOT EXISTS vector' server/alembic/versions/0001_initial_schema.py && grep -q 'chunks_embedding_hnsw_idx' server/alembic/versions/0001_initial_schema.py && grep -q 'ENABLE ROW LEVEL SECURITY' server/alembic/versions/0001_initial_schema.py && grep -q 'FORCE ROW LEVEL SECURITY' server/alembic/versions/0001_initial_schema.py && grep -q 'vector_cosine_ops' server/alembic/versions/0001_initial_schema.py && grep -q 'm = 16' server/alembic/versions/0001_initial_schema.py && grep -q 'ef_construction = 64' server/alembic/versions/0001_initial_schema.py && (cd server && ruff check alembic/versions/0001_initial_schema.py)</automated>
  </verify>
  <acceptance_criteria>
    - `server/alembic/versions/0001_initial_schema.py` exists and is the only file in `versions/` (D-06: single initial migration)
    - File contains exact substring `CREATE EXTENSION IF NOT EXISTS vector` (INFRA-03)
    - File contains exact substring `chunks_embedding_hnsw_idx` (HNSW index name)
    - File contains exact substring `vector_cosine_ops` (CLAUDE.md required ops class)
    - File contains exact substrings `m = 16` and `ef_construction = 64` (CLAUDE.md HNSW params)
    - File contains exact substring `ENABLE ROW LEVEL SECURITY` AND `FORCE ROW LEVEL SECURITY` (Open Question 3 resolution)
    - File creates exactly 32 tables (count by `grep -c "op.create_table(" server/alembic/versions/0001_initial_schema.py` returns 32)
    - File does NOT contain `apscheduler_jobs` (Pitfall 4)
    - `cd server && ruff check alembic/versions/0001_initial_schema.py` exits 0
    - Migration applies and rolls back successfully against the dev compose DB: `alembic upgrade head` and `alembic downgrade base` both exit 0
  </acceptance_criteria>
  <done>Single 0001_initial_schema.py migration in place; creates pgvector extension, all 32 tables, HNSW + GIN + B-tree indexes, RLS ENABLE on multi-tenant tables; ruff clean; verified upgrade+downgrade against dev compose DB.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 4: Test harness — conftest.py (testcontainers), test_boot.py (health, pgvector ext, table count, rollback isolation)</name>
  <files>server/app/tests/__init__.py, server/app/tests/conftest.py, server/app/tests/integration/__init__.py, server/app/tests/integration/test_boot.py</files>
  <read_first>
    - .planning/phases/01a-container-data-layer/01a-RESEARCH.md (Pattern 5: pytest-asyncio 1.x + testcontainers session fixture; Pitfall 2: event_loop removed; Pitfall 3: postgresql:// to postgresql+asyncpg:// URL conversion; Pitfall 6: register_vector before INSERT)
    - .planning/phases/01a-container-data-layer/01a-CONTEXT.md (D-01, D-02, D-03, D-04 test setup)
    - .planning/phases/01a-container-data-layer/01a-VALIDATION.md (Wave 0 requirements; per-task verification map)
    - server/app/database.py + server/app/models/__init__.py (the modules conftest imports)
    - server/alembic/env.py (the migration runner conftest will invoke)
    - server/pyproject.toml (verify asyncio_default_fixture_loop_scope = session)
  </read_first>
  <behavior>
The conftest provides a session-scoped PostgreSQL testcontainer + an async engine wired to it + a function-scoped DB session that rolls back after every test (D-01, D-02, D-03). The boot test suite verifies:

  - test_health_endpoint — GET /health returns 200 and {"status": "ok"} via httpx ASGITransport (no live server)
  - test_db_connection — async session executes `SELECT 1` against the testcontainer
  - test_pgvector_extension — `SELECT extname FROM pg_extension WHERE extname='vector'` returns one row
  - test_all_tables_present — Alembic ran successfully; `Base.metadata.tables` (32 entries) all exist as actual rows in `pg_class`
  - test_rollback_isolation_first / _second — write a row in test A, expect it absent in test B (proves D-02 rollback per test works)
  - test_apscheduler_jobs_not_in_metadata — defensive: `'apscheduler_jobs' not in Base.metadata.tables`
  </behavior>
  <action>
Create the test harness files. Pattern 5 in RESEARCH.md is the canonical reference; adapt it to also run Alembic (not Base.metadata.create_all) so the migration itself is exercised.

1. `server/app/tests/__init__.py` — empty: `"""Smart Copilot test suite."""`

2. `server/app/tests/integration/__init__.py` — empty: `"""Integration tests against a real PostgreSQL container."""`

3. `server/app/tests/conftest.py`:

```python
"""pytest fixtures: session-scoped testcontainer + rollback-per-test session.

D-01: testcontainers-python spins a throwaway PostgreSQL container per session.
D-02: rollback per test (function-scoped session inside SAVEPOINT).
D-03: container lifecycle is once per session.
D-04: pytest-asyncio 1.x with asyncio_mode = auto, asyncio_default_fixture_loop_scope = session
       (pyproject.toml). NO event_loop fixture override (Pitfall 2).
"""
from __future__ import annotations

import os
import subprocess
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from pgvector.asyncpg import register_vector
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer

from app.models import Base  # noqa: F401 — side-effect: registers all 32 tables

# Pitfall 1 / D-12 / CLAUDE.md base image: use the same pgvector/pgvector:pg16
# tag as production so CREATE EXTENSION vector succeeds without compile.
POSTGRES_IMAGE = "pgvector/pgvector:pg16"

SERVER_DIR = Path(__file__).resolve().parent.parent.parent  # server/


@pytest.fixture(scope="session")
def postgres_container() -> PostgresContainer:
    """Boot a single PostgreSQL container for the whole pytest session (D-03)."""
    with PostgresContainer(POSTGRES_IMAGE, driver=None) as pg:
        yield pg


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_engine(postgres_container: PostgresContainer) -> AsyncIterator:
    """Async engine bound to the testcontainer, with pgvector type registered.

    Pitfall 3: testcontainers returns postgresql:// (psycopg2) URL; convert to
    postgresql+asyncpg:// for the runtime async engine.

    Migrations are applied via Alembic (not Base.metadata.create_all) so the
    actual 0001_initial_schema.py migration is exercised by every test run.
    """
    sync_url = postgres_container.get_connection_url()
    # testcontainers may return postgresql+psycopg2:// or postgresql://; normalize:
    base_url = sync_url.replace("postgresql+psycopg2://", "postgresql://", 1)
    async_url = base_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    psycopg2_url = base_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    engine = create_async_engine(async_url, echo=False)

    @event.listens_for(engine.sync_engine, "connect")
    def _register_vec(dbapi_connection, connection_record):  # noqa: ARG001
        dbapi_connection.run_async(register_vector)

    # Run Alembic migrations against the test container using the SYNC URL.
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

    Pattern: open a connection, BEGIN a transaction, bind a session to that
    connection, yield, then ROLLBACK and close. Any inserts/updates/deletes
    in the test are reverted before the next test begins. No data bleed.
    """
    async with test_engine.connect() as connection:
        trans = await connection.begin()
        factory = async_sessionmaker(bind=connection, expire_on_commit=False, class_=AsyncSession)
        async with factory() as session:
            try:
                yield session
            finally:
                await trans.rollback()
```

4. `server/app/tests/integration/test_boot.py`:

```python
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
            text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            )
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
        text("INSERT INTO system_config (key, value) VALUES ('test_isolation_marker', '\"first\"'::jsonb)")
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
    assert row is None, "rollback-per-test isolation broken: previous test's data leaked"
```

5. Add `httpx` to `server/requirements-dev.txt` if not already present (it is required by `httpx.AsyncClient`):
```
httpx>=0.27
```
(already in `requirements.txt` indirectly via FastAPI? No — FastAPI does not depend on httpx. Add it to requirements-dev.txt.)

After writing, run `pip install -r server/requirements-dev.txt && cd server && pytest app/tests/ -v` and verify all 7 tests pass.

NOTE: test_pgvector_extension does NOT require register_vector to be called (we are only checking pg_extension catalog). Pitfall 6 only applies when INSERTING rows containing vector data — we are not doing that in Phase 1a tests.
  </action>
  <verify>
    <automated>test -f server/app/tests/conftest.py && test -f server/app/tests/integration/test_boot.py && grep -q 'PostgresContainer' server/app/tests/conftest.py && grep -q 'pgvector/pgvector:pg16' server/app/tests/conftest.py && grep -q 'register_vector' server/app/tests/conftest.py && grep -q 'alembic.*upgrade.*head' server/app/tests/conftest.py && grep -q 'rollback' server/app/tests/conftest.py && ! grep -q 'def event_loop' server/app/tests/conftest.py && grep -q 'test_pgvector_extension' server/app/tests/integration/test_boot.py && grep -q 'test_health_endpoint' server/app/tests/integration/test_boot.py && grep -q 'test_rollback_isolation' server/app/tests/integration/test_boot.py && grep -q 'test_apscheduler_jobs_not_in_metadata' server/app/tests/integration/test_boot.py && (cd server && ruff check app/tests/) && (cd server && pytest app/tests/integration/test_boot.py -v 2>&1 | tail -20)</automated>
  </verify>
  <acceptance_criteria>
    - All 4 files exist
    - `server/app/tests/conftest.py` contains substring `PostgresContainer` (D-01)
    - `server/app/tests/conftest.py` contains substring `pgvector/pgvector:pg16` (D-12 same image as prod)
    - `server/app/tests/conftest.py` contains substring `register_vector` (D-08 — registered on test engine)
    - `server/app/tests/conftest.py` runs `alembic upgrade head` via subprocess (TEST-01: real migration, not create_all)
    - `server/app/tests/conftest.py` does NOT define `def event_loop` (Pitfall 2: removed in pytest-asyncio 1.x)
    - `server/app/tests/conftest.py` defines `db_session` with rollback in finally (D-02)
    - `server/app/tests/integration/test_boot.py` contains all 6 test functions: `test_health_endpoint`, `test_db_connection`, `test_pgvector_extension`, `test_all_tables_present`, `test_apscheduler_jobs_not_in_metadata`, `test_rollback_isolation_first`, `test_rollback_isolation_second` (count >= 7)
    - `cd server && ruff check app/tests/` exits 0
    - `cd server && pytest app/tests/integration/test_boot.py -v` exits 0 with all 7 tests passing (or 7+ if more discovered)
    - testcontainer boot logs appear (proving real PostgreSQL was used; no DB mocks per TEST-01)
  </acceptance_criteria>
  <done>Test harness committed; 7 boot tests pass against a real pgvector/pgvector:pg16 testcontainer; rollback-per-test isolation verified; pytest-asyncio 1.x config exercised end-to-end.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| application -> PostgreSQL | All runtime queries go through asyncpg + pgvector codec; Alembic uses psycopg2 for migrations only |
| FastAPI request -> DB session | Future RLS GUC boundary (Phase 1b); Phase 1a establishes the RESET-in-finally discipline |
| testcontainer -> host Docker daemon | testcontainers requires Docker socket access for the local dev/test machine; CI sandbox impact noted |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-1a-08 | Tampering | RLS GUC bleed across pooled connections | mitigate | `dependencies.py` ALWAYS calls `RESET app.current_user_id` in finally (CLAUDE.md). Phase 1b adds the `SET` half. Acceptance criterion `grep -q 'RESET app.current_user_id'` in dependencies.py enforces the discipline at scaffold time |
| T-1a-09 | Information Disclosure | Alembic env.py imports runtime async engine | mitigate | Acceptance criterion verifies `! grep -q 'from app.database' server/alembic/env.py` — Alembic uses its own sync psycopg2 engine (D-09) |
| T-1a-10 | Denial of Service | apscheduler_jobs accidentally migrated | mitigate | `include_object` filter in env.py + acceptance criterion `! grep -q apscheduler_jobs server/alembic/versions/0001_initial_schema.py` (Pitfall 4 / CLAUDE.md) |
| T-1a-11 | Elevation of Privilege | RLS POLICY missing on multi-tenant tables in Phase 1a | accept | RLS is `ENABLED` and `FORCED` at schema level in 0001_initial_schema.py (Open Question 3 resolution). Without policies, this fails CLOSED — only the table owner can read. Real policies arrive in Phase 1b along with auth. The fail-closed default is the safer disposition |
</threat_model>

<verification>
- `cd server && ruff check app/ alembic/` exits 0
- `cd server && pytest app/tests/ -v` boots a pgvector/pgvector:pg16 testcontainer, runs alembic upgrade head, executes 7 tests, all pass
- `Base.metadata.tables` has exactly 32 entries (Plan 02 contract preserved)
- `apscheduler_jobs` does not appear anywhere in Base.metadata or in the migration file
- `chunks_embedding_hnsw_idx` exists with `vector_cosine_ops`, `m=16`, `ef_construction=64`
- All multi-tenant tables have RLS ENABLED (verifiable by querying `pg_class.relrowsecurity`)
</verification>

<success_criteria>
- INFRA-07: asyncpg runtime + psycopg2 Alembic separation enforced (D-09); database.py exposes engine + session_factory; alembic/env.py uses psycopg2 only
- INFRA-03: pgvector extension created in 0001_initial_schema.py; test_pgvector_extension passes
- TEST-01: pytest+pytest-asyncio+testcontainers running against a real pgvector PostgreSQL; rollback-per-test isolation verified; zero DB mocks
- D-01..D-04 satisfied (testcontainers, rollback-per-test, session lifecycle, pytest-asyncio 1.x config)
- D-05/D-06 satisfied (single 0001_initial_schema.py migration covering all 32 tables)
- D-08/D-09 satisfied (pgvector connect event + strict module ownership)
- D-13 satisfied (settings.py uses pydantic-settings + .env)
- /health returns 200 {"status": "ok"} via ASGI transport (Phase 1a success criterion 3 prerequisite)
</success_criteria>

<output>
After completion, create `.planning/phases/01a-container-data-layer/01a-03-SUMMARY.md` with:
- Files created (exact list)
- Test count and pass/fail breakdown
- testcontainer boot time observation
- Any deviations from spec (e.g., extra indexes added during autogenerate)
- Confirmation that alembic upgrade head + downgrade base both succeed
</output>
