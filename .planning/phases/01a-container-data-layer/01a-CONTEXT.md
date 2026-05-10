# Phase 1a: Container + Data Layer - Context

**Gathered:** 2026-05-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Stand up the foundational infrastructure layer: a single Docker container managed by supervisord (PID 1), PostgreSQL 16 + pgvector initialized and reachable, Alembic migrations run before uvicorn starts, all domain SQLAlchemy models defined up-front, and the full monorepo scaffold with tooling (Ruff, pre-commit, pnpm) committed. A local docker-compose provides the dev inner loop; the monolithic image is the production artifact.

</domain>

<decisions>
## Implementation Decisions

### Test Database Setup
- **D-01:** Use `testcontainers-python` to auto-spin a throwaway PostgreSQL container per pytest session. Zero env setup for contributors — `pytest` just works on a clean clone. Requires Docker daemon running locally.
- **D-02:** Test isolation via **rollback per test** — each test runs inside a transaction that's rolled back at teardown. Fast, no data bleed between tests.
- **D-03:** Testcontainers container lifecycle is **once per session** — one container boots for the entire pytest run; Alembic migrations run once at session start.
- **D-04:** pytest-asyncio configured as `asyncio_mode = auto, loop_scope = session` in `pyproject.toml`. Single event loop for the entire test session; required for shared async fixtures (DB pool, testcontainers).

### SQLAlchemy Model Scope
- **D-05:** **All domain models defined up-front in Phase 1a** — complete schema across all 7 phases in one pass. Subsequent phases add service logic and incremental migrations, not new model files (unless schema genuinely changes).
- **D-06:** Alembic migration structure: single initial migration `0001_initial_schema.py` covers the complete schema. Future schema changes use incremental migrations from `0002` onward, **named by purpose/domain** (e.g., `0002_add_inbox_triage.py`, `0003_add_dream_audit_log.py`).
- **D-07:** Model files live in a `models/` package, **one file per domain**: `models/user.py`, `models/page.py`, `models/chunk.py`, `models/link.py`, `models/conversation.py`, `models/skill.py`, `models/dream.py`, `models/project.py`, `models/audit.py`, `models/job.py`, etc.

### pgvector / asyncpg Registration
- **D-08:** Register the pgvector `vector` type via **SQLAlchemy engine `connect` event + `dbapi_connection.run_async(register_vector)`**. Runs once per newly opened connection; covers all callers (background jobs, CLI, tests, Alembic helpers) without requiring the `get_db` dependency to be in the call path.
- **D-09:** **Module ownership** is strictly separated:
  - `server/app/database.py` — creates the async engine, registers the pgvector event listener, exports `async_session_factory` and `engine`. Single source of truth for the runtime DB layer.
  - `server/app/dependencies.py` — imports `async_session_factory` from `database.py`; implements `get_db_session` and RLS GUC handling (`SET app.current_user_id` / `RESET` in `finally:`).
  - `server/app/main.py` — manages FastAPI app lifecycle only; does NOT create the engine.
  - `alembic/env.py` — imports `Base.metadata` and all model modules for autogenerate; creates its own **sync psycopg2 engine** from the migration `DATABASE_URL` (e.g., `postgresql+psycopg2://`). Never imports the runtime async engine.

### Docker Development Workflow
- **D-10:** **docker-compose for dev, monolithic image for prod.** Local development: `docker-compose.yml` runs PostgreSQL 16 + pgvector (`pgvector/pgvector:pg16`) and pgAdmin as separate containers; Python app runs outside compose with `uvicorn --reload`. Hot reload, direct debugger attachment, local `pytest` execution, fast migration loop.
- **D-11:** Production and CI release validation use the PRD-required monolithic image (supervisord + postgres + FastAPI + mcp-http + APScheduler + watchdog in one container). The dev compose is an **inner-loop convenience only** and does not redefine the production deployment architecture.
- **D-12:** `docker-compose.yml` dev services: `pgvector/pgvector:pg16` + pgAdmin. No Mailpit in Phase 1a (deferred to when email flows are needed).
- **D-13:** Local env config via **`.env` file + `python-dotenv`**, gitignored. Variables: `DATABASE_URL`, `ALEMBIC_DATABASE_URL`, `TEST_DATABASE_URL`, `SMARTCOPILOT_FERNET_KEY`, `SMARTCOPILOT_HOST_URL`, dev ports. `.env.example` committed with safe placeholder values. Application loads `.env` in dev mode via `pydantic-settings` `env_file` or explicit `python-dotenv` load.

### Claude's Discretion
- Pre-commit hook scope for Phase 1a: Ruff (lint + format) only. OpenAPI regeneration hook is deferred to Phase 1c when routes exist. Type checking (mypy) not mentioned in CLAUDE.md — skip unless there's a clear need.
- Health endpoint `/health` in Phase 1a: return `{status: ok}` with 200. Full postgres/pgvector/Fernet checks are Phase 6 work — don't over-build now.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product Requirements
- `docs/product_requirements_document_v26.05.md` — authoritative PRD (v26.05.1); complete spec for all phases including container layout, supervisord config, database schema, and acceptance criteria

### Planning Artifacts
- `.planning/REQUIREMENTS.md` — structured requirements (INFRA-01 through INFRA-08, TEST-01) scoped to Phase 1a
- `.planning/ROADMAP.md` — phase boundary, success criteria, and dependency chain for Phase 1a

### Architecture Constraints (from CLAUDE.md)
- Base image: `pgvector/pgvector:pg16` (pre-installed pgvector, avoids compile)
- asyncpg for runtime (`postgresql+asyncpg://`); psycopg2 for Alembic only (`postgresql+psycopg2://`)
- supervisord `nodaemon=true` as PID 1; priority order: postgres(10) → fastapi(20) → mcp-http(30) → apscheduler(40) → watchdog(50)
- `apscheduler_jobs` table NOT in Alembic — APScheduler manages it
- Logs to `/dev/fd/1` and `/dev/fd/2`; never to files inside the container
- `wait-for-pg.sh` runs Alembic migrations before uvicorn starts (priority 20 in supervisord)
- Volumes: `/data` (PostgreSQL), `/vaults` (markdown), `/config`
- Ruff is the sole linter/formatter (replaces flake8 + black + isort)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project. No existing code.

### Established Patterns
- None yet — Phase 1a establishes the patterns all subsequent phases follow.

### Integration Points
- `server/app/database.py` → imported by `dependencies.py`, `alembic/env.py`, and test fixtures
- `alembic/env.py` → must import all `models/*.py` files so autogenerate sees the complete schema
- `docker-compose.yml` (dev) → postgres container must use same image version (`pgvector/pgvector:pg16`) and volume paths as the production monolithic container to avoid environment drift

</code_context>

<specifics>
## Specific Ideas

- Migration naming convention (from discussion): `0001_initial_schema.py` for the initial all-domains migration; `000N_<purpose>_<domain>.py` for future schema changes (e.g., `0002_add_inbox_triage.py`)
- pgvector event registration pattern (from discussion): `@event.listens_for(engine.sync_engine, "connect")` decorator on a function that calls `dbapi_connection.run_async(register_vector)` — not `connect_args={"init": ...}` (that's for raw asyncpg pool, not SQLAlchemy async engine)
- `async_session_factory` exported from `database.py` and consumed by `dependencies.py` — keeps FastAPI dependency thin (validate → session → service → response)

</specifics>

<deferred>
## Deferred Ideas

- Mailpit (local mail catcher) — not needed in Phase 1a; add to docker-compose when email flows arrive (Phase 1b password reset or later)
- OpenAPI pre-commit regeneration hook — deferred to Phase 1c when FastAPI routes exist
- Full health check depth (postgres connectivity, pgvector extension, Fernet key status) — Phase 6 adds these via `smartcopilot doctor`; Phase 1a health endpoint returns `{status: ok}` only

</deferred>

---

*Phase: 1a — Container + Data Layer*
*Context gathered: 2026-05-08*
