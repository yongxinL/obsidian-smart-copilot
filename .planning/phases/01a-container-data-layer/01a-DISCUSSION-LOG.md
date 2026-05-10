# Phase 1a: Container + Data Layer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-08
**Phase:** 1a — Container + Data Layer
**Areas discussed:** Test DB setup, Model scope, pgvector registration, Docker dev workflow

---

## Test DB Setup

### Q1: How should pytest spin up a real PostgreSQL instance?

| Option | Description | Selected |
|--------|-------------|----------|
| testcontainers-python | Auto-starts throwaway PostgreSQL container per pytest session; zero env setup | ✓ |
| TEST_DATABASE_URL env var | Tests read env var pointing to already-running PostgreSQL; CI uses postgres service | |
| docker-compose in CI only | Tests assume localhost:5432; CI uses docker-compose; local dev needs native postgres | |

**User's choice:** testcontainers-python
**Notes:** Zero setup for contributors — `pytest` just works on a clean clone. Requires Docker daemon locally.

---

### Q2: How should test isolation work between individual tests?

| Option | Description | Selected |
|--------|-------------|----------|
| Rollback per test | Each test runs inside a transaction rolled back at teardown. Fast, no bleed. | ✓ |
| Truncate tables per test | Truncate all tables after each test. Slower but compatible with background tasks. | |
| Separate schema per test | Each test gets its own PostgreSQL schema. Cleanest isolation, complex setup. | |

**User's choice:** Rollback per test

---

### Q3: How often should the testcontainers PostgreSQL instance be created?

| Option | Description | Selected |
|--------|-------------|----------|
| Once per session | One container per pytest run; Alembic migrations run once at start. | ✓ |
| Once per test module | Container restarts between test files. Slower. | |
| Once per test | New container per test. 2-3s overhead each. Not recommended. | |

**User's choice:** Once per session

---

### Q4: What pytest-asyncio event loop mode?

| Option | Description | Selected |
|--------|-------------|----------|
| asyncio_mode = auto, loop_scope = session | Single event loop for entire session; required for shared async fixtures. | ✓ |
| asyncio_mode = auto, loop_scope = function | New event loop per test; makes session-scoped async fixtures impossible. | |
| asyncio_mode = strict | Each async test marked explicitly. Verbose but explicit. | |

**User's choice:** `asyncio_mode = auto, loop_scope = session` in `pyproject.toml`

---

## Model Scope

### Q1: Which SQLAlchemy models should Phase 1a define?

| Option | Description | Selected |
|--------|-------------|----------|
| All domain models up-front | Every model (users, pages, chunks, links, conversations, etc.) now. | ✓ |
| Phase-gated models | Only models Phase 1a+1b need. Subsequent phases add their own. | |
| Infrastructure only | No domain models — just proves stack wires up. | |

**User's choice:** All domain models up-front
**Notes:** Complete schema in one pass. Subsequent phases add service logic and incremental migrations, not model files (unless schema genuinely changes).

---

### Q2: How should the all-at-once schema be structured in Alembic?

| Option | Description | Selected |
|--------|-------------|----------|
| Single initial migration | One `0001_initial_schema.py` creates all tables. | ✓ |
| Domain-grouped migrations | Multiple initial migrations: 0001_users.py, 0002_vault.py, etc. | |
| One migration per table | Most granular but results in 20+ migrations for initial schema. | |

**User's choice:** Single initial migration: `0001_initial_schema.py`
**Notes:** User reviewed this decision carefully before confirming. Future schema changes use incremental migrations from `0002` onward, named by purpose/domain (e.g., `0002_add_inbox_triage.py`).

---

### Q3: Where should SQLAlchemy model files live?

| Option | Description | Selected |
|--------|-------------|----------|
| models/ package, one file per domain | server/app/models/user.py, page.py, chunk.py, etc. | ✓ |
| Single models.py | All models in one file. 1000+ lines with all models up-front. | |
| models/ package with __init__ re-exports | Domain files + re-exports. Can confuse Alembic autogenerate. | |

**User's choice:** `models/` package, one file per domain

---

## pgvector Registration

### Q1: How should asyncpg register the vector type?

| Option | Description | Selected |
|--------|-------------|----------|
| Pool init callback | `connect_args={"init": register_vector}` on `create_async_engine`. | |
| Explicit call in FastAPI dependency | `await register_vector(conn)` inside `get_db`. | |
| SQLAlchemy engine connect event | `@event.listens_for(engine.sync_engine, "connect")` + `dbapi_connection.run_async(register_vector)`. | ✓ |

**User's choice:** SQLAlchemy engine connect event + `dbapi_connection.run_async(register_vector)`
**Notes:** User provided detailed clarification: do not use `connect_args={"init": ...}` (that's for raw asyncpg pool, not SQLAlchemy async engine). Do not register inside `get_db` — background jobs, tests, CLI commands, and Alembic helpers may open sessions outside that dependency. Engine connect event fires once per new connection regardless of caller.

---

### Q2: Where should engine setup live?

| Option | Description | Selected |
|--------|-------------|----------|
| server/app/database.py | Dedicated module: async engine, event listener, async_session_factory. | ✓ |
| server/app/dependencies.py | Engine created inside FastAPI dependencies module. | |
| server/app/main.py | Engine created at app startup in main.py lifespan. | |

**User's choice:** `server/app/database.py`
**Notes:** User specified the full module boundary contract:
- `database.py` — engine, event listener, `async_session_factory`
- `dependencies.py` — imports `async_session_factory`; implements `get_db_session` + RLS GUC
- `main.py` — app lifecycle only; no engine creation
- `alembic/env.py` — imports `Base.metadata` + all model modules; creates own sync psycopg2 engine; never imports runtime async engine

---

## Docker Dev Workflow

### Q1: How should developers run the stack locally?

| Option | Description | Selected |
|--------|-------------|----------|
| docker-compose for dev, monolithic image for prod | Postgres + pgAdmin in compose; Python app runs locally with `uvicorn --reload`. | ✓ |
| Monolithic image for both | Same single-container image for dev and prod. No hot reload. | |
| docker-compose for everything | Separate containers for dev + prod. Abandons PRD single-container constraint. | |

**User's choice:** docker-compose for dev, monolithic image for prod
**Notes:** Dev compose is inner-loop convenience only — does not redefine production deployment architecture. PRD single-container requirement is preserved.

---

### Q2: What should docker-compose.yml include?

| Option | Description | Selected |
|--------|-------------|----------|
| postgres + pgAdmin | pgvector/pgvector:pg16 + pgAdmin. Python app runs outside compose. | ✓ |
| postgres only | Lean, no GUI tool. | |
| postgres + pgAdmin + mailpit | Also includes local mail catcher for future email flows. | |

**User's choice:** postgres + pgAdmin
**Notes:** No Mailpit in Phase 1a. Password reset / email flows deferred.

---

### Q3: How should local env config work?

| Option | Description | Selected |
|--------|-------------|----------|
| .env file + python-dotenv, gitignored | .env holds DATABASE_URL etc.; .env.example committed with placeholders. | ✓ |
| Shell exports only | No .env file — developers export in shell profile. | |
| direnv + .envrc | Auto-loads on directory entry. Requires direnv installed. | |

**User's choice:** `.env` file + `python-dotenv`, gitignored
**Notes:** Variables: `DATABASE_URL`, `ALEMBIC_DATABASE_URL`, `TEST_DATABASE_URL`, `SMARTCOPILOT_FERNET_KEY`, `SMARTCOPILOT_HOST_URL`, dev ports. Loaded via `pydantic-settings` `env_file` or explicit `python-dotenv` load.

---

## Claude's Discretion

- Pre-commit hook scope in Phase 1a: Ruff only. OpenAPI hook deferred to Phase 1c (no routes yet). mypy skipped (not in stack spec).
- Health endpoint depth: `{status: ok}` with 200. Full checks (postgres, pgvector, Fernet) are Phase 6.

## Deferred Ideas

- Mailpit — deferred to when email flows are needed
- OpenAPI pre-commit regeneration hook — deferred to Phase 1c
- Full health check depth — Phase 6 (`smartcopilot doctor`)
