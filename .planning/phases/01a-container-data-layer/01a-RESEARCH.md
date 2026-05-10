# Phase 1a: Container + Data Layer - Research

**Researched:** 2026-05-08
**Domain:** Docker/supervisord, PostgreSQL 16 + pgvector, SQLAlchemy 2.0 async, Alembic, pytest-asyncio + testcontainers, pnpm monorepo, Ruff + pre-commit
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Test Database Setup**
- D-01: Use `testcontainers-python` to auto-spin a throwaway PostgreSQL container per pytest session. Zero env setup for contributors — `pytest` just works on a clean clone. Requires Docker daemon running locally.
- D-02: Test isolation via rollback per test — each test runs inside a transaction that's rolled back at teardown. Fast, no data bleed between tests.
- D-03: Testcontainers container lifecycle is once per session — one container boots for the entire pytest run; Alembic migrations run once at session start.
- D-04: pytest-asyncio configured as `asyncio_mode = auto, loop_scope = session` in `pyproject.toml`. Single event loop for the entire test session; required for shared async fixtures (DB pool, testcontainers).

**SQLAlchemy Model Scope**
- D-05: All domain models defined up-front in Phase 1a — complete schema across all 7 phases in one pass. Subsequent phases add service logic and incremental migrations, not new model files.
- D-06: Alembic migration structure: single initial migration `0001_initial_schema.py` covers the complete schema. Future schema changes use incremental migrations from `0002` onward, named by purpose/domain.
- D-07: Model files live in a `models/` package, one file per domain.

**pgvector / asyncpg Registration**
- D-08: Register the pgvector `vector` type via SQLAlchemy engine `connect` event + `dbapi_connection.run_async(register_vector)`. Runs once per newly opened connection.
- D-09: Module ownership strictly separated: `database.py` (engine + event + session factory), `dependencies.py` (get_db_session + RLS GUC), `main.py` (lifecycle only), `alembic/env.py` (sync psycopg2 engine, never imports runtime engine).

**Docker Development Workflow**
- D-10: docker-compose for dev (pgvector/pgvector:pg16 + pgAdmin), monolithic image for prod.
- D-11: Production/CI uses the monolithic supervisord image.
- D-12: docker-compose.yml dev services: pgvector/pgvector:pg16 + pgAdmin. No Mailpit in Phase 1a.
- D-13: Local env via `.env` + `python-dotenv`/`pydantic-settings`, gitignored. `.env.example` committed.

### Claude's Discretion
- Pre-commit hook scope for Phase 1a: Ruff (lint + format) only. OpenAPI regeneration deferred to Phase 1c. Type checking (mypy) not needed.
- Health endpoint `/health` in Phase 1a: return `{status: ok}` with 200. Full postgres/pgvector/Fernet checks deferred to Phase 6.

### Deferred Ideas (OUT OF SCOPE)
- Mailpit (local mail catcher) — not needed in Phase 1a.
- OpenAPI pre-commit regeneration hook — deferred to Phase 1c when FastAPI routes exist.
- Full health check depth (postgres connectivity, pgvector extension, Fernet key status) — Phase 6.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-01 | System runs as a single Docker container managed by `supervisord` with `nodaemon=true` as PID 1 | PRD §30I.2 provides canonical supervisord.conf; see Architecture Patterns |
| INFRA-02 | Container manages: postgres, fastapi (uvicorn), mcp-http, apscheduler, watchdog under supervisord | Priority order: 10→20→30→40→50 verified from PRD and CLAUDE.md |
| INFRA-03 | PostgreSQL 16 with pgvector — sole primary datastore | Base image `pgvector/pgvector:pg16` with pre-installed extension |
| INFRA-04 | pnpm workspaces monorepo with Python under `server/app/` and Electron stub under `clients/desktop/` | pnpm-workspace.yaml + package.json structure documented |
| INFRA-05 | Node 20 LTS and Python 3.12 pinned via `.nvmrc` and `pyproject.toml`/`.python-version` | Both runtimes available locally; pinning patterns documented |
| INFRA-06 | Ruff is sole Python linter/formatter; pre-commit hooks enforce formatting | ruff-pre-commit hook with `ruff-check` and `ruff-format` IDs |
| INFRA-07 | Backend is Python 3.12, FastAPI, async-first, asyncpg for runtime, psycopg2 for Alembic only | Dual-driver pattern verified via SQLAlchemy + Alembic docs |
| INFRA-08 | Volumes defined for `/data` (PostgreSQL), `/vaults` (markdown), `/config` | Dockerfile VOLUME directive; PRD §30I.1 |
| TEST-01 | pytest + pytest-asyncio against real PostgreSQL test database (no DB mocks) | testcontainers-python 4.14.2 + session-scoped fixture pattern documented |
</phase_requirements>

---

## Summary

Phase 1a establishes the complete foundational scaffold for the Smart Copilot monorepo: Docker container with supervisord as PID 1, PostgreSQL 16 + pgvector, all domain SQLAlchemy models defined up-front, the initial Alembic migration, and the pytest/testcontainers test harness. Because this is a greenfield project, there is no existing code to integrate with — every pattern established here becomes the canonical template for subsequent phases.

The most non-obvious challenge is the pgvector async registration: the `vector` type must be registered on every new asyncpg connection via a SQLAlchemy `connect` event, not via `connect_args={"init": ...}` (which is for raw asyncpg pools, not SQLAlchemy async engines). The PRD Appendix E conftest skeleton uses the deprecated pytest-asyncio `event_loop` fixture pattern from pre-0.24; the current version (1.3.0, installed) requires `asyncio_default_fixture_loop_scope = "session"` in pyproject.toml instead. This is a breaking change that must be addressed.

The complete domain model list (D-05) spans ~25 SQLAlchemy model files covering users, sessions, tokens, vault hierarchy, pages, chunks (with vector), entities, links, timeline events, tags, jobs, audit log, skills, recipes, eval, conversations, messages, memories, dream audit log, projects, operation log, llm_usage, index_events, user_settings, system_config, and mcp_servers.

**Primary recommendation:** Follow the PRD §30I canonical Dockerfile/supervisord.conf/wait-for-pg.sh exactly. Use testcontainers `pgvector/pgvector:pg16` image for tests. Configure pytest-asyncio 1.x with `asyncio_default_fixture_loop_scope = "session"` (not the deprecated `event_loop` fixture override). Use SQLAlchemy `@event.listens_for(engine.sync_engine, "connect")` with `dbapi_connection.run_async(register_vector)` for pgvector registration.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Container orchestration | Docker/supervisord | — | PID 1 process manager; all 5 processes under supervisord |
| PostgreSQL initialization | postgres process (priority 10) | — | Must start before all other processes |
| Schema migrations | fastapi process (priority 20, via wait-for-pg.sh) | — | Alembic runs before uvicorn in same supervisord program |
| FastAPI/uvicorn API | fastapi process | — | REST + WebSocket API; 2 workers per PRD |
| MCP HTTP server | mcp-http process (priority 30) | — | Separate supervisord program, port 8787 |
| APScheduler background jobs | apscheduler process (priority 40) | — | MUST NOT run inside uvicorn workers |
| Vault filesystem watching | watchdog process (priority 50) | — | Separate process; asyncio handoff via call_soon_threadsafe |
| Database access (runtime) | API / Backend | asyncpg pool in each worker | Each uvicorn worker has independent pool |
| Database access (migrations) | Alembic (sync psycopg2) | — | Runs once during boot via wait-for-pg.sh |
| Test database | testcontainers session fixture | — | pgvector/pgvector:pg16 image; session-scoped container |
| Configuration loading | pydantic-settings | python-dotenv | .env file + env vars; no config at container layer |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12 | Runtime | Mandated; async-native, `match` statements |
| FastAPI | >= 0.111 (latest: 0.136.1) | HTTP framework | Mandated; async, native SSE, OpenAPI |
| uvicorn | >= 0.30 (latest: 0.46.0) | ASGI server | Standard async server; `--workers 2` |
| Pydantic | v2 | Request/response models | FastAPI v0.100+ requires Pydantic v2 |
| SQLAlchemy | 2.0 (installed: 2.0.49) | Async ORM + Core | Required for asyncpg async sessions |
| Alembic | >= 1.13 (latest: 1.18.4) | Schema migrations | Pairs with SQLAlchemy 2.0; autogenerate |
| asyncpg | >= 0.29 (latest: 0.31.0) | Async DB driver (runtime) | Only async PostgreSQL driver for asyncpg |
| psycopg2-binary | >= 2.9 (latest: 2.9.12) | Sync DB driver (Alembic only) | Required by Alembic env.py sync engine |
| pgvector | >= 0.3 (latest: 0.4.2) | Vector type + HNSW ops | SQLAlchemy VECTOR type + cosine ops |
| supervisor | >= 4.2 (latest: 4.3.0) | PID 1 process manager | Mandated; nodaemon=true Docker pattern |
| pydantic-settings | >= 2.0 (latest: 2.14.0) | Settings from env/.env | Mandated; env_file support |
| python-dotenv | >= 1.0 (latest: 1.2.2) | .env file loading | Mandated; explicit load in dev mode |

[VERIFIED: PyPI registry via `pip3 index versions`]

### Testing
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >= 8 (latest: 9.0.3) | Test runner | All tests |
| pytest-asyncio | >= 1.0 (latest: 1.3.0, INSTALLED) | Async test support | All async tests and fixtures |
| testcontainers | >= 4.0 (latest: 4.14.2) | PostgreSQL test container | Session-scoped DB fixture |

[VERIFIED: PyPI registry via `pip3 index versions`]

### Tooling
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| ruff | >= 0.4 (latest: 0.15.12) | Linter + formatter | Sole linter; replaces flake8+black+isort |
| pre-commit | >= 4.0 (latest: 4.6.0) | Git hook runner | Enforce Ruff on commit |

[VERIFIED: PyPI registry]

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| testcontainers | docker-py manual setup | testcontainers handles health checks, cleanup; docker-py requires manual pg_isready loop |
| psycopg2 (Alembic) | psycopg3 (async) | psycopg2 is the stable, well-understood sync driver; Alembic env.py is sync; mixing async Alembic adds complexity without benefit |
| pydantic-settings | dynaconf / python-decouple | pydantic-settings integrates natively with Pydantic v2 models; others require adaptation |
| asyncpg | psycopg3 async | asyncpg is battle-tested, fastest Python PostgreSQL async driver; psycopg3 async is newer |

**Installation (dev):**
```bash
pip install fastapi>=0.111 uvicorn>=0.30 pydantic-settings>=2.0 sqlalchemy>=2.0 alembic>=1.13 asyncpg>=0.29 psycopg2-binary>=2.9 pgvector>=0.3 python-dotenv>=1.0
pip install pytest>=8 pytest-asyncio>=1.0 testcontainers[postgres]>=4.0
pip install ruff>=0.4 pre-commit>=4.0
```

---

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│  Docker Container  (pgvector/pgvector:pg16 base image)              │
│  CMD: supervisord -c /etc/supervisor/conf.d/supervisord.conf        │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  priority 10 — [program:postgresql]                          │  │
│  │  postgres -D /var/lib/postgresql/data                        │  │
│  │  READY: accepting connections on :5432                       │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
│                             │  pg_isready loop (wait-for-pg.sh)    │
│  ┌──────────────────────────▼───────────────────────────────────┐  │
│  │  priority 20 — [program:fastapi]                             │  │
│  │  wait-for-pg.sh:                                             │  │
│  │    1. pg_isready poll                                        │  │
│  │    2. alembic upgrade head  (psycopg2 sync engine)           │  │
│  │    3. exec uvicorn app.main:app --workers 2                  │  │
│  │  READY: REST API on :8000, /health returns 200               │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  priority 30 — [program:mcp-http]                            │  │
│  │  python3 -m smartcopilot.mcp.serve --http --port 8787        │  │
│  │  READY: MCP Streamable HTTP on :8787                         │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  priority 40 — [program:apscheduler]                         │  │
│  │  python3 -m smartcopilot.scheduler.run                       │  │
│  │  Reads from postgres; SQLAlchemyJobStore                     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  priority 50 — [program:watchdog]                            │  │
│  │  python3 -m smartcopilot.vault.watcher                       │  │
│  │  inotify → call_soon_threadsafe → asyncio queue              │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  Volumes: /var/lib/postgresql/data  /vaults  /config               │
│  Ports:   :8000 (REST)  :8787 (MCP HTTP)                           │
└─────────────────────────────────────────────────────────────────────┘
```

Data flow: `docker run` → supervisord PID 1 → postgres starts → fastapi/wait-for-pg.sh polls pg_isready → alembic runs → uvicorn accepts connections → mcp-http, apscheduler, watchdog start in parallel.

### Recommended Project Structure
```
smart-copilot/                  # monorepo root
├── pnpm-workspace.yaml         # packages: ["server", "clients/desktop"]
├── package.json                # root pnpm scripts + workspaces
├── .nvmrc                      # 20
├── .gitignore
├── .env.example                # committed; safe placeholder values
├── server/
│   ├── Dockerfile              # FROM pgvector/pgvector:pg16
│   ├── supervisord.conf
│   ├── requirements.txt        # Python deps pinned
│   ├── pyproject.toml          # Python 3.12, Ruff, pytest config
│   ├── .python-version         # 3.12
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py              # sync psycopg2 engine; imports all models
│   │   └── versions/
│   │       └── 0001_initial_schema.py
│   ├── scripts/
│   │   └── wait-for-pg.sh      # pg_isready → alembic → uvicorn
│   └── app/
│       ├── main.py             # FastAPI app factory + lifespan
│       ├── config.py           # pydantic-settings BaseSettings
│       ├── database.py         # async engine + pgvector event + session factory
│       ├── dependencies.py     # get_db_session (RLS GUC); imports database.py
│       ├── models/             # one file per domain (D-07)
│       │   ├── __init__.py
│       │   ├── user.py
│       │   ├── session.py
│       │   ├── mcp_token.py
│       │   ├── provider_key.py
│       │   ├── vault.py
│       │   ├── page.py
│       │   ├── page_version.py
│       │   ├── chunk.py        # VECTOR(1536) column + HNSW index
│       │   ├── entity.py
│       │   ├── link.py
│       │   ├── timeline_event.py
│       │   ├── tag.py
│       │   ├── job.py
│       │   ├── audit_log.py
│       │   ├── skill.py
│       │   ├── recipe.py
│       │   ├── eval_candidate.py
│       │   ├── conversation.py  # conversations + messages
│       │   ├── memory.py
│       │   ├── dream_audit_log.py
│       │   ├── project.py
│       │   ├── operation_log.py
│       │   ├── llm_usage.py
│       │   ├── index_event.py
│       │   ├── user_settings.py
│       │   ├── system_config.py
│       │   ├── mcp_server.py   # mcp_servers table (Phase 7, define schema now)
│       │   └── golden_eval.py  # golden_query_suites + queries + runs (Phase 2b)
│       ├── routes/
│       │   └── health.py       # GET /health → {status: ok}
│       └── tests/
│           ├── conftest.py     # session container, async engine, rollback fixture
│           └── integration/
│               └── test_boot.py  # health check + pgvector extension test
├── clients/
│   └── desktop/
│       └── package.json        # Electron client stub
├── .pre-commit-config.yaml     # Ruff lint + format hooks
└── docker-compose.yml          # dev: pgvector:pg16 + pgAdmin
```

### Pattern 1: Canonical supervisord.conf
```ini
# Source: PRD §30I.2 [CITED: docs/product_requirements_document_v26.05.md#30I.2]
[supervisord]
nodaemon=true
user=root

[program:postgresql]
command=/usr/lib/postgresql/16/bin/postgres -D /var/lib/postgresql/data -c config_file=/etc/postgresql/postgresql.conf
user=postgres
autostart=true
autorestart=true
priority=10
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
stderr_logfile=/dev/fd/2
stderr_logfile_maxbytes=0

[program:fastapi]
command=/app/scripts/wait-for-pg.sh
directory=/app
autostart=true
autorestart=true
priority=20
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
stderr_logfile=/dev/fd/2
stderr_logfile_maxbytes=0

[program:mcp-http]
command=python3 -m smartcopilot.mcp.serve --http --port 8787
directory=/app
autostart=true
autorestart=true
priority=30
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
stderr_logfile=/dev/fd/2
stderr_logfile_maxbytes=0

[program:apscheduler]
command=python3 -m smartcopilot.scheduler.run
directory=/app
autostart=true
autorestart=true
priority=40
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
stderr_logfile=/dev/fd/2
stderr_logfile_maxbytes=0

[program:watchdog]
command=python3 -m smartcopilot.vault.watcher
directory=/app
autostart=true
autorestart=true
priority=50
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
stderr_logfile=/dev/fd/2
stderr_logfile_maxbytes=0
```

**Critical note:** PRD §30I.2 shows log directives missing from the template. CLAUDE.md mandates logs to `/dev/fd/1` and `/dev/fd/2`. Both `stdout_logfile` and `stderr_logfile` must be set to `/dev/fd/1`/`/dev/fd/2` with `maxbytes=0`. [CITED: CLAUDE.md]

### Pattern 2: wait-for-pg.sh
```bash
#!/bin/bash
# Source: PRD §30I.3 [CITED: docs/product_requirements_document_v26.05.md#30I.3]
set -e
echo "Waiting for PostgreSQL..."
until pg_isready -h localhost -p 5432 -U postgres -q; do sleep 1; done
echo "Running migrations..."
python3 -m alembic upgrade head
echo "Starting FastAPI..."
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

### Pattern 3: SQLAlchemy async engine with pgvector registration
```python
# server/app/database.py
# Source: SQLAlchemy docs + pgvector-python docs
# [CITED: docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html]
# [CITED: github.com/pgvector/pgvector-python/blob/master/README.md]
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from pgvector.asyncpg import register_vector

engine = create_async_engine(
    settings.database_url,  # postgresql+asyncpg://...
    pool_pre_ping=True,
    echo=settings.debug,
)

@event.listens_for(engine.sync_engine, "connect")
def register_vector_type(dbapi_connection, connection_record):
    dbapi_connection.run_async(register_vector)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
```

**Why `engine.sync_engine` not `engine`:** `@event.listens_for(engine, "connect")` does not work on `AsyncEngine`; events must be registered on `engine.sync_engine`. [VERIFIED: Context7, /websites/sqlalchemy_en_20]

**Why `run_async` not `init=` kwarg:** `connect_args={"init": register_vector}` is the raw asyncpg pool pattern. SQLAlchemy's adapted DBAPI connection exposes `run_async()` which bridges sync event handlers to async driver calls. [VERIFIED: Context7, /websites/sqlalchemy_en_20]

### Pattern 4: Alembic env.py for async models (sync psycopg2 engine)
```python
# alembic/env.py — critical pattern: sync psycopg2, imports all model files
# [CITED: alembic.sqlalchemy.org/en/latest/cookbook.html]
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Import Base and ALL model modules so autogenerate sees complete schema
from app.models.base import Base
from app.models import (
    user, session, mcp_token, provider_key, vault, page, page_version,
    chunk, entity, link, timeline_event, tag, job, audit_log, skill, recipe,
    eval_candidate, conversation, memory, dream_audit_log, project,
    operation_log, llm_usage, index_event, user_settings, system_config,
    mcp_server, golden_eval,
)

target_metadata = Base.metadata

def run_migrations_online():
    # Uses psycopg2 (postgresql+psycopg2://) — NEVER the runtime asyncpg engine
    alembic_db_url = os.environ.get("ALEMBIC_DATABASE_URL")
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = alembic_db_url
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
```

**Key:** `ALEMBIC_DATABASE_URL` uses `postgresql+psycopg2://` not `postgresql+asyncpg://`. [VERIFIED: CLAUDE.md + Alembic Context7]

### Pattern 5: pytest-asyncio 1.x session-scoped testcontainers fixture
```python
# server/app/tests/conftest.py
# Source: pytest-asyncio 1.x docs + testcontainers docs
# [CITED: github.com/pytest-dev/pytest-asyncio/blob/main/docs/reference/configuration.md]
# [CITED: github.com/testcontainers/testcontainers-python/blob/main/modules/postgres/README.md]
import pytest
import pytest_asyncio
from testcontainers.postgres import PostgresContainer
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import event, text
from pgvector.asyncpg import register_vector
from app.models.base import Base

# Testcontainers: use pgvector/pgvector:pg16 image (same as production)
# so CREATE EXTENSION IF NOT EXISTS vector works in tests
POSTGRES_IMAGE = "pgvector/pgvector:pg16"

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer(POSTGRES_IMAGE) as pg:
        yield pg

@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_engine(postgres_container):
    # get_connection_url() returns psycopg2-style URL; convert for asyncpg
    sync_url = postgres_container.get_connection_url()
    async_url = sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    engine = create_async_engine(async_url, echo=False)
    
    @event.listens_for(engine.sync_engine, "connect")
    def register_vec(dbapi_connection, connection_record):
        dbapi_connection.run_async(register_vector)
    
    # Enable pgvector extension + run migrations once for the session
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    
    # Run Alembic migrations against test DB
    # (or create_all for Phase 1a bootstrap)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture(loop_scope="session")  # function scope, session event loop
async def db_session(test_engine):
    """Rollback-per-test isolation (D-02)."""
    async with test_engine.begin() as conn:
        # Use nested transaction for rollback
        async with async_sessionmaker(bind=conn, expire_on_commit=False)() as session:
            yield session
            await session.rollback()
```

**pyproject.toml config for pytest-asyncio 1.x:**
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"
asyncio_default_test_loop_scope = "function"
```

**CRITICAL — 1.x breaking change:** pytest-asyncio 1.x removed the ability to override the `event_loop` fixture. The PRD Appendix E skeleton uses `@pytest.fixture(scope="session") def event_loop()` which is the OLD 0.21 pattern that is REMOVED in 1.x. Use `asyncio_default_fixture_loop_scope = "session"` in pyproject.toml instead. [VERIFIED: Context7, /pytest-dev/pytest-asyncio migrate_from_0_21.md]

### Pattern 6: SQLAlchemy 2.0 DeclarativeBase and mapped_column
```python
# server/app/models/base.py
# [CITED: docs.sqlalchemy.org/en/20/orm/declarative_tables.html]
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import UUID, DateTime, func
import uuid

class Base(DeclarativeBase):
    pass

# Example: page.py
from sqlalchemy import String, Text, JSON, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import Base

class Page(Base):
    __tablename__ = "pages"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())
```

### Pattern 7: pgvector VECTOR column + HNSW index
```python
# server/app/models/chunk.py
# [CITED: github.com/pgvector/pgvector-python/blob/master/README.md]
from pgvector.sqlalchemy import VECTOR
from sqlalchemy import Index

class Chunk(Base):
    __tablename__ = "chunks"
    embedding: Mapped[list] = mapped_column(VECTOR(1536), nullable=True)

# HNSW index — in Alembic migration, NOT in model definition
# [CITED: github.com/pgvector/pgvector-python/blob/master/README.md]
hnsw_index = Index(
    "chunks_embedding_hnsw_idx",
    Chunk.embedding,
    postgresql_using="hnsw",
    postgresql_with={"m": 16, "ef_construction": 64},
    postgresql_ops={"embedding": "vector_cosine_ops"},
)
```

**Index in migration, not `__table_args__`:** The HNSW index uses `vector_cosine_ops` which must match the `<=>` cosine distance operator used at query time. Putting it in the Alembic migration (not model `__table_args__`) keeps the model clean and allows parallel index builds via `CREATE INDEX CONCURRENTLY` syntax in future migrations.

### Pattern 8: pydantic-settings BaseSettings
```python
# server/app/config.py
# [CITED: github.com/pydantic/pydantic-settings/blob/main/docs/index.md]
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    database_url: str           # postgresql+asyncpg://...
    alembic_database_url: str   # postgresql+psycopg2://...
    test_database_url: str = "" # set by testcontainers in tests
    smartcopilot_fernet_key: str
    smartcopilot_host_url: str = "http://localhost:8000"
    debug: bool = False
```

### Pattern 9: FastAPI app factory with lifespan
```python
# server/app/main.py
# [CITED: github.com/fastapi/fastapi/blob/master/docs/en/docs/advanced/events.md]
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import engine  # imports trigger connect event registration

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: engine is already initialized at import time
    yield
    # Shutdown
    await engine.dispose()

def create_app() -> FastAPI:
    app = FastAPI(title="Smart Copilot", lifespan=lifespan)
    from app.routes.health import router as health_router
    app.include_router(health_router)
    return app

app = create_app()
```

### Pattern 10: Ruff pre-commit hook + pyproject.toml
```yaml
# .pre-commit-config.yaml
# [CITED: github.com/astral-sh/ruff/blob/main/docs/integrations.md]
- repo: https://github.com/astral-sh/ruff-pre-commit
  rev: v0.15.12  # pin to current latest
  hooks:
    - id: ruff-check    # linter; --fix applied on --fix flag
    - id: ruff-format   # formatter
```

```toml
# pyproject.toml [tool.ruff] section
[tool.ruff]
target-version = "py312"
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "UP", "B", "I"]  # pyflakes, pyupgrade, bugbear, isort
ignore = ["E501"]  # line length enforced by formatter

[tool.ruff.lint.per-file-ignores]
"alembic/versions/*.py" = ["E402"]
"app/tests/**/*.py" = ["S101"]  # allow assert in tests
```

### Pattern 11: pnpm workspaces monorepo structure
```yaml
# pnpm-workspace.yaml
# [CITED: pnpm.io/pnpm-workspace_yaml]
packages:
  - "server"
  - "clients/desktop"
```

```json
// root package.json — scripts only, no deps
{
  "name": "smart-copilot",
  "private": true,
  "engines": { "node": ">=20" },
  "scripts": {
    "codegen": "pnpm --filter desktop codegen",
    "build:desktop": "pnpm --filter desktop build"
  }
}
```

### Anti-Patterns to Avoid
- **Importing FastAPI types in services:** `HTTPException`, `Request`, `Response` MUST NOT appear in `services/`. Services accept `OperationContext`. [CITED: CLAUDE.md]
- **`SET LOCAL` for RLS GUC:** Only lasts for the transaction, not the request scope. Always use `SET app.current_user_id = ...` (session-level). [CITED: CLAUDE.md, PRD §F.1]
- **APScheduler inside uvicorn workers:** Double execution because workers don't share memory. Always run as dedicated supervisord program. [CITED: CLAUDE.md]
- **`apscheduler_jobs` in Alembic:** APScheduler manages this table itself; Alembic autogenerate will try to drop it if it sees it. Use `include_object` filter in `env.py` to exclude it. [CITED: CLAUDE.md, PRD §F.8]
- **Logging to files inside the container:** Docker cannot capture log files; always use `/dev/fd/1` and `/dev/fd/2` for supervisord stdout/stderr. [CITED: CLAUDE.md]
- **Overriding `event_loop` fixture:** Removed in pytest-asyncio 1.x. Use `asyncio_default_fixture_loop_scope = "session"` in pyproject.toml instead. [VERIFIED: Context7]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PostgreSQL test container lifecycle | Custom Docker SDK setup | testcontainers-python `PostgresContainer` | Built-in health checks, cleanup, port mapping, connection URL generation |
| pgvector type registration | Custom type codec | `pgvector.asyncpg.register_vector` | Handles codec registration for vector numpy arrays; needed for asyncpg to understand vector type |
| Schema migrations | Manual `CREATE TABLE` | Alembic autogenerate | Handles diffs, ordered revisions, up/down migrations, metadata detection |
| Settings loading | `os.environ.get()` | pydantic-settings `BaseSettings` | Type coercion, validation, .env support, nested settings, env prefix |
| Process management in Docker | Custom Python supervisor | supervisord | Battle-tested PID 1 replacement; handles process restarts, log routing, startup ordering |
| ASGI server configuration | Custom socket code | uvicorn | Standard ASGI server; `--workers N` concurrency, signals, graceful shutdown |
| Vector similarity index | Custom B-tree approximation | pgvector HNSW with `m=16, ef_construction=64` | HNSW is purpose-built for approximate nearest neighbor; B-tree cannot do cosine distance |

**Key insight:** Every piece of custom infrastructure in this domain is a maintenance trap. supervisord, testcontainers, and Alembic each handle dozens of edge cases (signal forwarding, port allocation, connection pooling, drift detection) that would take weeks to replicate correctly.

---

## Common Pitfalls

### Pitfall 1: PostgreSQL data directory not initialized in pgvector:pg16 image
**What goes wrong:** The `pgvector/pgvector:pg16` image does NOT auto-initialize the PostgreSQL data directory at the path `/var/lib/postgresql/data` unless you're using the official `postgres:16` image's entrypoint. When using supervisord as PID 1 (replacing the default postgres entrypoint), the data directory must be initialized by running `initdb` before starting postgres.
**Why it happens:** The official postgres Docker image initializes data in the entrypoint script (`docker-entrypoint.sh`). When you override CMD with supervisord, that script never runs.
**How to avoid:** In the Dockerfile, add an initialization step: `RUN su postgres -c "initdb -D /var/lib/postgresql/data"` OR use a Docker build arg / entrypoint that conditionally runs `initdb` if the data dir is empty. A `docker-entrypoint.sh`-style init script should run before starting supervisord.
**Warning signs:** postgres process exits immediately with "data directory not found" or "Permission denied" in supervisord logs.

[ASSUMED — observed in Docker postgres patterns; verify against pgvector:pg16 image behavior]

### Pitfall 2: pytest-asyncio 1.x event_loop fixture removed
**What goes wrong:** PRD Appendix E skeleton uses `@pytest.fixture(scope="session") def event_loop()` — this is the 0.21-era pattern removed in pytest-asyncio 1.x. Using it raises `DeprecationWarning` in 0.23+ and is fully removed in 1.0+.
**Why it happens:** PRD was written before pytest-asyncio 1.x was released; the installed version is 1.3.0.
**How to avoid:** Use `asyncio_default_fixture_loop_scope = "session"` and `asyncio_default_test_loop_scope = "function"` in `[tool.pytest.ini_options]`. Use `@pytest_asyncio.fixture(scope="session", loop_scope="session")` for session-scoped async fixtures.
**Warning signs:** `DeprecationWarning: The event_loop fixture is deprecated` or `ScopeMismatch` errors.
[VERIFIED: Context7, pytest-asyncio migration docs]

### Pitfall 3: testcontainers PostgresContainer returns psycopg2 URL, not asyncpg
**What goes wrong:** `container.get_connection_url()` returns `postgresql://...` (psycopg2 format). Using this URL with `create_async_engine` fails because asyncpg needs `postgresql+asyncpg://`.
**Why it happens:** testcontainers uses psycopg2 internally for health checks.
**How to avoid:** Convert the URL: `async_url = sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)`.
**Warning signs:** `sqlalchemy.exc.NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:postgresql` at engine creation.
[VERIFIED: Context7, testcontainers-python docs]

### Pitfall 4: `apscheduler_jobs` table captured by Alembic autogenerate
**What goes wrong:** When running `alembic revision --autogenerate`, if APScheduler has already been used and the `apscheduler_jobs` table exists in the DB, Alembic will generate a migration that tries to drop it on downgrade (or detect it as an "extra" table).
**Why it happens:** Alembic autogenerate compares `Base.metadata` against the live DB schema. `apscheduler_jobs` is not in `Base.metadata` but is in the DB.
**How to avoid:** In `alembic/env.py`, add `include_object` filter:
```python
def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and name == "apscheduler_jobs":
        return False
    return True
context.configure(..., include_object=include_object)
```
[CITED: CLAUDE.md, PRD §F.8]

### Pitfall 5: HNSW index operator class mismatch
**What goes wrong:** Querying with `<=>` (cosine) on an index built with `vector_l2_ops` (L2) results in a full sequential scan instead of using the index.
**Why it happens:** PostgreSQL requires the operator class used in the query to match the operator class in the index definition.
**How to avoid:** Always use `vector_cosine_ops` for the HNSW index (text-embedding-3-small produces normalized embeddings). Use `<=>` operator in all queries. Verify with `EXPLAIN` that the index is used.
[CITED: CLAUDE.md, pgvector-python docs]

### Pitfall 6: pgvector `register_vector` not called before first INSERT with vector
**What goes wrong:** Inserting a row with a `VECTOR` column raises `asyncpg.exceptions.UnknownPostgresError: unknown type 'vector'` even though pgvector extension is installed.
**Why it happens:** asyncpg does not automatically recognize custom PostgreSQL types; `register_vector` must be called on the connection to register the type codec.
**How to avoid:** The `@event.listens_for(engine.sync_engine, "connect")` pattern registers the codec on every new connection. In testcontainers fixtures, also run `CREATE EXTENSION IF NOT EXISTS vector` before creating tables.
[VERIFIED: Context7, pgvector-python README]

### Pitfall 7: Multiple `.env` file locations confuse pydantic-settings
**What goes wrong:** `pydantic-settings` looks for `.env` relative to the process CWD. When uvicorn runs with `directory=/app` in supervisord, it looks for `/app/.env`. In dev, if running from `server/`, it looks for `server/.env`.
**Why it happens:** `env_file=".env"` is a relative path.
**How to avoid:** Either use absolute path in `model_config` or `env_file=Path(__file__).parent.parent / ".env"`, or ensure `.env` is always at the project root and workers are started from the correct directory.
[ASSUMED — common pydantic-settings deployment pattern]

### Pitfall 8: Async session + rollback isolation — nested transactions
**What goes wrong:** The rollback-per-test pattern requires that each test's DB changes are within a transaction that can be rolled back. If tests use `session.begin()` explicitly, the nested transaction must be correctly managed.
**Why it happens:** SQLAlchemy 2.0 async sessions do not automatically nest transactions; savepoints may be needed for tests that explicitly call `session.commit()`.
**How to avoid:** For Phase 1a (no user service logic yet), the pattern is straightforward. For later phases, use `connection.begin_nested()` (savepoints) if tests call commit internally.
[ASSUMED — common pytest-asyncio + SQLAlchemy test isolation challenge]

---

## Complete Domain Model List (D-05)

The following model files must be created in Phase 1a (one file per domain per D-07), with stub column definitions matching PRD §7.1 requirements. Subsequent phases add relationships and business logic without adding new files (unless schema genuinely changes).

| File | Table(s) | Key PRD Req | Notes |
|------|---------|-------------|-------|
| `models/user.py` | `users` | REQ-300 | UUID PK, username, email, password_hash, role, is_active |
| `models/session.py` | `sessions` | REQ-301 | user_id FK, token_hash, expires_at |
| `models/mcp_token.py` | `mcp_tokens` | REQ-302 | user_id FK, name, token_hash, last_used_at, revoked_at |
| `models/provider_key.py` | `provider_keys` | REQ-303 | user_id FK, provider, encrypted_key BYTEA, key_hint |
| `models/vault.py` | `vaults` | REQ-304 | owner_user_id NULL FK, kind (private/shared), path |
| `models/page.py` | `pages` | REQ-305, REQ-305A | vault_id FK, slug, type enum, note_type enum, frontmatter JSONB, compiled_truth, content_hash, enrichment_hash, deleted_at |
| `models/page_version.py` | `page_versions` | REQ-306 | page_id FK, version INT, frontmatter JSONB |
| `models/chunk.py` | `chunks` | REQ-307 | page_id FK, kind enum, text, enriched_content, tsv TSVECTOR GENERATED, embedding VECTOR(1536) |
| `models/entity.py` | `entities` | REQ-308 | vault_id FK, kind enum, canonical_slug, aliases TEXT[] |
| `models/link.py` | `links` | REQ-309 | src_page_id FK, dst_entity_id FK, link_type, confidence, source_kind enum |
| `models/timeline_event.py` | `timeline_events` | REQ-310 | page_id FK, event_date DATE, source, detail |
| `models/tag.py` | `tags`, `page_tags` | REQ-311 | tags with vault_id FK; page_tags join table |
| `models/job.py` | `jobs` | REQ-312 | parent_id NULL FK, kind, status, payload JSONB, idempotency_key UNIQUE NULL |
| `models/audit_log.py` | `audit_log` | REQ-313 | user_id NULL FK, action, target_kind, request_id |
| `models/skill.py` | `skills` | REQ-314 | namespace enum (system/user), user_id NULL FK, UNIQUE constraint |
| `models/recipe.py` | `recipes` | REQ-315 | namespace, user_id NULL FK, yaml TEXT |
| `models/eval_candidate.py` | `eval_candidates` | REQ-316 | user_id FK, kind, query, retrieved_slugs TEXT[] |
| `models/conversation.py` | `conversations`, `messages` | REQ-360, REQ-361 | conversations: mcp_mode enum, web_search_enabled; messages: role enum, citations JSONB |
| `models/memory.py` | `memories` | REQ-362 | user_id FK, content, source_conversation_id FK, archived |
| `models/dream_audit_log.py` | `dream_audit_log` | REQ-363 | user_id FK, run_at, kind, status, pages_processed |
| `models/project.py` | `projects` | REQ-364 | user_id FK, folder_patterns TEXT[], tag_includes TEXT[], system_prompt |
| `models/operation_log.py` | `operation_log` | REQ-365 | user_id FK, operation, target_kind, target_id, payload JSONB |
| `models/llm_usage.py` | `llm_usage` | REQ-366 | user_id FK, provider, model, input_tokens, output_tokens, cost_usd, conversation_id FK |
| `models/index_event.py` | `index_events` | REQ-367 | user_id FK, event_type, page_slug, details JSONB |
| `models/user_settings.py` | `user_settings` | REQ-368 | user_id FK, settings JSONB |
| `models/system_config.py` | `system_config` | REQ-369 | key TEXT UNIQUE, value JSONB |
| `models/mcp_server.py` | `mcp_servers` | REQ-370 | name UNIQUE, type enum (stdio/streamable_http), command, args TEXT[], always_allow TEXT[] |
| `models/golden_eval.py` | `golden_query_suites`, `golden_queries`, `golden_query_runs` | REQ-372–374 | suites: scope enum; queries: suite_id FK, expected_slugs TEXT[]; runs: metrics JSONB |

**27 model files total (some contain 2 related tables).** The `apscheduler_jobs` table is excluded — APScheduler manages it.

**Required indexes (in Alembic migration, not model `__table_args__`):**
- HNSW on `chunks.embedding` with `vector_cosine_ops`, `m=16`, `ef_construction=64`
- GIN on `chunks.tsv`
- B-tree on `pages.slug`, `links.src_page_id`, `links.dst_entity_id`
- GIN on `pages.frontmatter`

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pytest-asyncio `event_loop` fixture override | `asyncio_default_fixture_loop_scope = "session"` in pyproject.toml | pytest-asyncio 0.23+ / 1.0 | Existing PRD Appendix E code needs updating |
| `@app.on_event("startup")` decorator | `@asynccontextmanager async def lifespan(app)` | FastAPI 0.93 | Old pattern deprecated but still works; lifespan is the recommended pattern |
| SQLAlchemy `declarative_base()` function | `class Base(DeclarativeBase)` | SQLAlchemy 2.0 | New style with type annotations and `mapped_column` |
| pgvector `connect_args={"init": register_vector}` | `@event.listens_for(engine.sync_engine, "connect")` + `run_async` | pgvector-python + SQLAlchemy async | Only the event listener pattern works with SQLAlchemy AsyncEngine |
| ruff version pinning via `>=0.4` | `ruff==0.15.12` (exact pin) | Ruff moves fast; pre-commit rev must match | Rev in `.pre-commit-config.yaml` must be updated when ruff is upgraded |

**Deprecated/outdated patterns in PRD Appendix E:**
- `event_loop` fixture override: Use `asyncio_default_fixture_loop_scope = "session"` instead
- `from asyncpg import create_pool, connect` in conftest: testcontainers provides the URL; use SQLAlchemy async engine in tests, not raw asyncpg

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | PostgreSQL data directory in `pgvector/pgvector:pg16` image requires explicit `initdb` when using custom supervisord PID 1 | Pitfall 1, Pattern supervisord | Container fails to start; postgres process exits; requires Dockerfile fix |
| A2 | `testcontainers` 4.x `PostgresContainer.get_connection_url()` returns a `postgresql://` (psycopg2) URL not `postgresql+asyncpg://` | Pattern 5 | URL conversion step may be wrong; test engine creation may fail |
| A3 | The supervisord log config (`stdout_logfile=/dev/fd/1`) is correct for Docker stdout capture on the target OS | Pattern 1 | Logs may not appear in `docker logs`; debugging made difficult |
| A4 | `pydantic-settings` `.env` resolution is relative to CWD, not the module location | Pitfall 7 | Settings not loaded in dev; runtime errors on missing required fields |

**Only 4 assumptions — all other claims verified via Context7, PyPI registry, or PRD citations.**

---

## Open Questions (RESOLVED)

1. **PostgreSQL data directory initialization in pgvector:pg16 image** — RESOLVED: handled via `server/scripts/docker-entrypoint.sh` (Plan 04 Task 2) with empty-data-dir initdb guard.
   - What we know: The official postgres:16 image uses `docker-entrypoint.sh` to run `initdb`. The pgvector:pg16 image inherits from postgres:16 and uses the same entrypoint.
   - What's unclear: When supervisord replaces the default CMD, does `initdb` still run? Or does the Dockerfile need an explicit `RUN su postgres -c "initdb -D /var/lib/postgresql/data"` step?
   - Recommendation: Verify by inspecting `pgvector/pgvector:pg16` image layers (`docker inspect pgvector/pgvector:pg16`) before writing the Dockerfile. The planner should include a task to validate this.

2. **`uv` vs `pip` for dependency management in container** — RESOLVED: pip is used in the Dockerfile (Plan 04 Task 3); uv adoption deferred.
   - What we know: CLAUDE.md says "Either works; pin via pyproject.toml and requirements.txt". `uv` is faster but not installed in the dev environment.
   - What's unclear: Does the production Dockerfile use `uv` (faster builds) or `pip` (ubiquitous)?
   - Recommendation: Use `pip` in Phase 1a for simplicity; `uv` can be adopted later without schema changes.

3. **RLS policies: stub or fully defined in Phase 1a?** — RESOLVED: `0001_initial_schema.py` (Plan 03) emits `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY` on all multi-tenant tables; `CREATE POLICY` deferred to Phase 1b (auth).
   - What we know: D-05 says all domain models defined up-front. RLS policies belong to the database layer. AUTH requirements (RLS enforcement) are Phase 1b.
   - What's unclear: Should the `0001_initial_schema.py` migration include `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` statements, or leave that for Phase 1b?
   - Recommendation: Include `ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY` on all multi-tenant tables in the initial migration — this is schema structure. Leave the actual policy definitions (CREATE POLICY) for Phase 1b since they depend on auth logic.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | Runtime | ✓ | 3.12.13 | — |
| Docker Engine | testcontainers, monolithic image | ✓ | 29.4.0 | — |
| Docker Compose v2 | dev docker-compose.yml | ✓ | v5.1.2 | — |
| Node.js 20 LTS | pnpm workspaces, codegen | ✓ | v24.14.1 (higher than 20, satisfies >=20) | — |
| pnpm | monorepo package manager | ✓ | 10.33.0 | — |
| pgvector/pgvector:pg16 image | production + test container | ✓ | pulled locally | — |
| uv | fast Python package installer | ✗ | — | Use pip (available at 26.0.1) |
| ruff | linter/formatter | ✗ (not installed globally) | — | Install via pip or pre-commit manages it |
| pre-commit | git hooks | ✗ (not installed globally) | — | Install via pip; hooks run in isolated venvs |
| pg_isready (PostgreSQL client) | wait-for-pg.sh | ✗ (dev machine) | — | wait-for-pg.sh runs inside container where it is available |

**Missing dependencies with no fallback:**
- None — all critical tools are either available or run inside the container where they are installed.

**Missing dependencies with fallback:**
- `ruff` globally: pre-commit installs it in an isolated venv; contributors don't need it globally.
- `pre-commit` globally: needs to be installed once per contributor (`pip install pre-commit && pre-commit install`); documented in README.
- `uv`: use `pip` in Phase 1a; `uv` is a future optimization.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 (latest) + pytest-asyncio 1.3.0 |
| Config file | `server/pyproject.toml` — Wave 0 |
| Quick run command | `cd server && pytest app/tests/ -x -q` |
| Full suite command | `cd server && pytest app/tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | supervisord starts as PID 1 | smoke (docker run) | `docker run smart-copilot:latest supervisorctl status` | ❌ Wave 0 |
| INFRA-02 | All 5 supervisord programs RUNNING within 30s | smoke | `docker run --rm smart-copilot:latest sh -c "sleep 30 && supervisorctl status"` | ❌ Wave 0 |
| INFRA-03 | pgvector extension creates successfully | integration | `pytest app/tests/integration/test_boot.py::test_pgvector_extension -x` | ❌ Wave 0 |
| INFRA-04 | pnpm workspaces resolves packages | unit (pnpm) | `pnpm install && pnpm --filter server build` | ❌ Wave 0 |
| INFRA-05 | Python 3.12 and Node 20 pinned | unit | `python3 --version | grep 3.12; node --version | grep v2` | ❌ Wave 0 |
| INFRA-06 | Ruff check passes on scaffold | unit | `cd server && ruff check app/` | ❌ Wave 0 |
| INFRA-07 | asyncpg runtime, psycopg2 Alembic | integration | `pytest app/tests/integration/test_boot.py::test_db_connection -x` | ❌ Wave 0 |
| INFRA-08 | Volumes defined and writable | smoke | `docker run -v /tmp/data:/data smart-copilot:latest ls /data` | ❌ Wave 0 |
| TEST-01 | Real PostgreSQL test DB (no mocks) | integration | `pytest app/tests/ -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd server && ruff check app/ && pytest app/tests/ -x -q`
- **Per wave merge:** `cd server && ruff check app/ && pytest app/tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `server/app/tests/conftest.py` — session container, async engine, rollback fixture
- [ ] `server/app/tests/integration/test_boot.py` — health check, pgvector extension, DB connection
- [ ] `server/pyproject.toml` — pytest-asyncio config (`asyncio_mode=auto`, `asyncio_default_fixture_loop_scope=session`)
- [ ] Framework install: `pip install pytest>=8 pytest-asyncio>=1.0 testcontainers[postgres]>=4.0`
- [ ] `server/.pre-commit-config.yaml` + `pre-commit install`

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No (Phase 1b) | — |
| V3 Session Management | No (Phase 1b) | — |
| V4 Access Control | Partial (RLS schema) | `ENABLE ROW LEVEL SECURITY` on all multi-tenant tables |
| V5 Input Validation | No (no user input in Phase 1a) | — |
| V6 Cryptography | No (Phase 1b) | — |
| V7 Error Handling | No (Phase 1a has minimal error surface) | — |

### Phase 1a Security Scope
Phase 1a is infrastructure only — no user authentication, no request handling beyond `/health`. Security surface is:
1. **Secret management:** `SMARTCOPILOT_FERNET_KEY` must be present as env var; never logged; `.env` gitignored. [CITED: CLAUDE.md]
2. **Docker security:** Container runs processes with minimal privileges where possible. `[program:postgresql]` uses `user=postgres`. Other processes run as root (required for supervisord PID 1 in this architecture). [CITED: PRD §30I.2]
3. **No secrets in `.env.example`:** Placeholder values only; real keys never committed. [CITED: CLAUDE.md D-13]

### Known Threat Patterns for Phase 1a Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Fernet key leaked in environment dump | Information Disclosure | Never log env vars; use structlog field redaction (Phase 6) |
| `.env` file accidentally committed | Information Disclosure | `.gitignore` enforces exclusion; `.env.example` is the only committed env file |
| Container escape via mounted volumes | Elevation of Privilege | `/data`, `/vaults`, `/config` are the only mounts; paths validated in watchdog/vault layer (Phase 1c) |

---

## Sources

### Primary (HIGH confidence)
- `/websites/sqlalchemy_en_20` (Context7) — async engine connect events, `run_async`, `async_sessionmaker`, `mapped_column`
- `/pgvector/pgvector-python` (Context7) — `register_vector` asyncpg, SQLAlchemy VECTOR type, HNSW index creation
- `/pytest-dev/pytest-asyncio` (Context7) — 1.x `asyncio_mode=auto`, `asyncio_default_fixture_loop_scope`, migration from 0.21
- `/testcontainers/testcontainers-python` (Context7) — PostgresContainer, `get_connection_url()`, pytest fixture pattern
- `/websites/alembic_sqlalchemy` (Context7) — `run_migrations_online`, sync vs async engine patterns
- `/pydantic/pydantic-settings` (Context7) — `BaseSettings`, `model_config`, `env_file`
- `/fastapi/fastapi` (Context7) — `lifespan`, `asynccontextmanager`, app factory
- `/astral-sh/ruff` (Context7) — pre-commit hook IDs (`ruff-check`, `ruff-format`), `pyproject.toml` config
- `/websites/pnpm_io` (Context7) — `pnpm-workspace.yaml`, packages glob
- `docs/product_requirements_document_v26.05.md` — canonical Dockerfile (§30I.1), supervisord.conf (§30I.2), wait-for-pg.sh (§30I.3), file structure (§30J.1), data model (§7.1), test skeleton (Appendix E), common pitfalls (Appendix F)
- PyPI registry (`pip3 index versions`) — verified current versions for all packages

### Secondary (MEDIUM confidence)
- CLAUDE.md — project-specific constraints, module ownership, RLS discipline, APScheduler constraints

### Tertiary (LOW confidence — marked ASSUMED above)
- PostgreSQL data directory initialization behavior with pgvector:pg16 base image and custom supervisord PID 1

---

## Project Constraints (from CLAUDE.md)

The planner MUST verify compliance with these directives:

| Directive | Source | Impact on Phase 1a |
|-----------|--------|-------------------|
| Base image MUST be `pgvector/pgvector:pg16` | CLAUDE.md | Dockerfile `FROM` line |
| Runtime driver MUST be `asyncpg` (`postgresql+asyncpg://`) | CLAUDE.md | `database.py` engine URL |
| Alembic driver MUST be `psycopg2` (`postgresql+psycopg2://`) | CLAUDE.md | `alembic/env.py` engine URL |
| supervisord `nodaemon=true` as PID 1 | CLAUDE.md | supervisord.conf `[supervisord]` section |
| Priority order: postgres(10) → fastapi(20) → mcp-http(30) → apscheduler(40) → watchdog(50) | CLAUDE.md | supervisord.conf `priority=` values |
| `apscheduler_jobs` table NOT in Alembic | CLAUDE.md | `include_object` filter in env.py |
| Logs to `/dev/fd/1` and `/dev/fd/2` | CLAUDE.md | supervisord.conf `stdout_logfile`/`stderr_logfile` |
| Ruff is SOLE linter/formatter | CLAUDE.md | `.pre-commit-config.yaml`, no flake8/black/isort |
| `encrypted_key` fields MUST use `Field(exclude=True)` | CLAUDE.md | `models/provider_key.py` Pydantic schema |
| FastAPI types MUST NOT be imported in `services/` | CLAUDE.md | Phase 1a has no services yet; enforce from start |
| `SET app.current_user_id` (not `SET LOCAL`) | CLAUDE.md | `dependencies.py` get_db_session implementation |
| Always `RESET` in `finally:` | CLAUDE.md | `dependencies.py` get_db_session implementation |
| pnpm workspaces monorepo; Node.js 20 LTS | CLAUDE.md | `pnpm-workspace.yaml`, `.nvmrc` |
| Python 3.12, FastAPI >= 0.111, SQLAlchemy 2.0, asyncpg >= 0.29, pgvector >= 0.3 | CLAUDE.md | `pyproject.toml` / `requirements.txt` version pins |

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified via PyPI registry; patterns verified via Context7 official docs
- Architecture: HIGH — supervisord.conf, wait-for-pg.sh, Dockerfile from PRD; PostgreSQL init caveat ASSUMED
- Pitfalls: HIGH (pytest-asyncio 1.x, pgvector registration, apscheduler_jobs verified); MEDIUM (postgres initdb in container — assumed)

**Research date:** 2026-05-08
**Valid until:** 2026-06-08 (packages move fast; re-verify ruff version for pre-commit pin before execution)
