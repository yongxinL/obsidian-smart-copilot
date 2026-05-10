---
phase: 01a
plan: 03
subsystem: runtime-migration-testing
tags: [fastapi, alembic, testcontainers, pytest-asyncio, pgvector, rls, migration]
dependency_graph:
  requires: [01a-01, 01a-02]
  provides: [01a-04]
  affects: [01b-authentication, 01c-vault-indexer, 01d-mcp-server]
tech_stack:
  added:
    - FastAPI (app factory + lifespan)
    - SQLAlchemy 2.0 async engine + async_sessionmaker
    - Alembic 1.x (sync psycopg2 engine, autogenerate)
    - pgvector 0.3 (VECTOR type, HNSW index, vector_cosine_ops)
    - pytest-asyncio 1.3.0 (session-scoped fixtures, loop_scope)
    - testcontainers-python 4.x (PostgresContainer)
    - httpx (ASGITransport for health endpoint testing)
key_files:
  created:
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
  modified:
    - server/requirements-dev.txt (added httpx>=0.27)
    - server/pyproject.toml (asyncio_default_test_loop_scope = "session")
decisions:
  - "asyncpg runtime + psycopg2 Alembic separation enforced (D-09)"
  - "pgvector registered via engine.sync_engine connect event + run_async (D-08)"
  - "Module ownership: database.py owns engine/event/session_factory; dependencies.py owns get_db_session+RLS GUC; main.py is lifecycle only; alembic/env.py uses its own sync engine"
  - "RLS ENABLE + FORCE on 22 multi-tenant tables in initial migration (CREATE POLICY deferred to Phase 1b)"
  - "FIXME #3100: asyncio_default_test_loop_scope must be 'session' to match session-scoped async fixtures; function-scoped tests + session-scoped engine loop mismatch causes asyncpg future errors"
metrics:
  duration: ~2100s (~35 minutes)
  completed: 2026-05-10
  tasks: 4/4
  files: 14 created, 2 modified
  tests: 7 passed
  tables: 32 (verified via pg_tables query)
  indexes: 8 (1 HNSW + 3 GIN + 3 B-tree + 1 implicit)
---

# Phase 01a Plan 03 Summary: Runtime Application, Migration, and Test Harness

## One-liner
FastAPI app + async pgvector engine + 32-table Alembic migration + pytest/testcontainers harness: all 7 boot tests pass against a real pgvector/pgvector:pg16 testcontainer with rollback-per-test isolation.

## What was built

### Task 1: App Runtime (settings.py, database.py, dependencies.py, main.py, routes/)
- **server/app/settings.py** — pydantic-settings BaseSettings with all 6 env vars from D-13: `database_url` (asyncpg), `alembic_database_url` (psycopg2), `test_database_url`, `smartcopilot_fernet_key`, `smartcopilot_host_url`, `debug`
- **server/app/database.py** — async engine + pgvector connect event (`@event.listens_for(engine.sync_engine, "connect")` + `dbapi_connection.run_async(register_vector)`) + `async_session_factory`
- **server/app/dependencies.py** — `get_db_session` FastAPI dependency with RLS GUC RESET discipline (`RESET app.current_user_id` in finally; SET deferred to Phase 1b)
- **server/app/main.py** — FastAPI app factory + lifespan (imports engine, never creates it — D-09 lifecycle-only)
- **server/app/routes/health.py** — `GET /health` returns `{"status": "ok"}`
- Module ownership enforced: main.py does NOT contain `create_async_engine`, dependencies.py does NOT create engines, alembic/env.py does NOT import `app.database`

### Task 2: Alembic Configuration (env.py, alembic.ini, script.py.mako)
- **server/alembic.ini** — script_location=alembic, ruff post-write hook, warning-level logging
- **server/alembic/env.py** — sync psycopg2 engine (never asyncpg), `import app.models` side-effect populates `Base.metadata`, `include_object` filter excludes `apscheduler_jobs` (Pitfall 4), `_resolve_url()` reads `ALEMBIC_DATABASE_URL` env var first
- **server/alembic/script.py.mako** — standard Alembic revision template
- Verified: `! grep -q 'from app.database' alembic/env.py`, `! grep -q 'create_async_engine' alembic/env.py`, `grep -q 'apscheduler_jobs' alembic/env.py`

### Task 3: 0001_initial_schema.py Migration (32 tables, pgvector, RLS, indexes)
Generated via `alembic revision --autogenerate` against a fresh compose DB, then manually enhanced:

**Extension + Tables:**
- `CREATE EXTENSION IF NOT EXISTS vector` as first statement (before any VECTOR column references)
- All 32 tables from `Base.metadata`: users, sessions, mcp_tokens, provider_keys, vaults, pages, page_versions, chunks, entities, links, timeline_events, tags, page_tags, jobs, audit_log, skills, recipes, eval_candidates, conversations, messages, memories, dream_audit_log, projects, operation_log, llm_usage, index_events, user_settings, system_config, mcp_servers, golden_query_suites, golden_queries, golden_query_runs

**Custom Indexes:**
- HNSW on `chunks.embedding` with `vector_cosine_ops`, `m=16`, `ef_construction=64` (CLAUDE.md)
- GIN on `chunks.tsv` (TSVECTOR for BM25, Phase 2a)
- GIN on `pages.frontmatter` (JSONB tag queries)
- B-tree on `pages.slug`, `links.src_page_id`, `links.dst_entity_id`

**RLS (ENABLE + FORCE, CREATE POLICY deferred to Phase 1b):**
22 multi-tenant tables: provider_keys, sessions, mcp_tokens, pages, page_versions, chunks, entities, links, timeline_events, tags, page_tags, eval_candidates, conversations, messages, memories, projects, llm_usage, index_events, user_settings, recipes, skills, dream_audit_log

**Verification:** `alembic upgrade head` + `alembic downgrade base` both succeed; `SELECT COUNT(*) FROM pg_tables` returns 33 (32 tables + alembic_version); `pg_extension` confirms vector; `pg_class.relrowsecurity` confirms 22 RLS-enabled tables; `apscheduler_jobs` count = 0.

### Task 4: Test Harness (conftest.py + test_boot.py, 7 tests)

**Fixtures:**
- `postgres_container`: `@pytest_asyncio.fixture(scope="session", loop_scope="session")` — single testcontainer for the session, initialized inside the pytest session event loop
- `test_engine`: session-scoped async engine with pgvector registered, runs `alembic upgrade head` once at session start
- `db_session`: function-scoped async session with rollback-per-test isolation (D-02)

**Tests (all 7 passing):**
1. `test_health_endpoint` — ASGITransport + AsyncClient, expects 200 + `{"status": "ok"}`
2. `test_db_connection` — raw `SELECT 1` via asyncpg
3. `test_pgvector_extension` — `SELECT extname FROM pg_extension WHERE extname='vector'`
4. `test_all_tables_present` — `Base.metadata.tables.keys()` vs `pg_tables` diff
5. `test_apscheduler_jobs_not_in_metadata` — defensive assertion
6. `test_rollback_isolation_first` — INSERT test_isolation_marker
7. `test_rollback_isolation_second` — verifies marker absent (proves rollback works)

**FIXME #3100 (deviation from D-02 literal):** The D-02 specification of "rollback per test inside a transaction" conflicts with pytest-asyncio 1.x session-loop scoping. Root cause: `asyncio_default_test_loop_scope = "function"` creates a new event loop per test, but session-scoped fixtures share the session loop. asyncpg detects the loop mismatch. Fix: `asyncio_default_test_loop_scope = "session"` in pyproject.toml. This preserves rollback-per-test (each test gets a fresh session) while ensuring all tests + fixtures share the same event loop. D-01 (testcontainers session-scoped) and D-03 (container lifecycle) are fully satisfied.

**testcontainer boot observation:** First test run boots a fresh pgvector/pgvector:pg16 container (~3-5s). Subsequent runs reuse the container for the session.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] ruff format on pre-commit hook caused commit failures**
- **Found during:** Task 1, 2 commit attempts
- **Issue:** `.pre-commit-config.yaml` hook runs `ruff format` after every commit. When files weren't pre-formatted, the hook failed post-commit. Ruff then modified the files, and the original commit was lost.
- **Fix:** Pre-commit hook always runs before commit succeeds. Pre-format all files with `ruff format` before staging, or accept that pre-commit may fail. Since the commit WAS successful after the second attempt, the pattern is: stage → pre-commit fails with formatted patch → restore → re-stage → commit succeeds (pre-commit passes).
- **Files modified:** All 6 app runtime files; all 4 alembic files; all 4 test files
- **Commit:** `d2bc6b1`, `7ebae2a`, `50f4874`, `2218b0f`

**2. [Rule 1 - Bug] alembic.ini post-write hook failed on autogenerate**
- **Found during:** Task 3 (migration generation)
- **Issue:** `alembic revision --autogenerate` ran `ruff format` as post-write hook. `ruff format REVISION_SCRIPT_FILENAME` failed because `console_scripts.ruff` entrypoint is not installed in the environment (pre-commit manages ruff in an isolated venv, not globally).
- **Fix:** Removed `ruff format REVISION_SCRIPT_FILENAME` from the post-write hook command in `alembic.ini`. The migration file was generated successfully; ruff format was applied separately.
- **Files modified:** `server/alembic.ini`
- **Commit:** `7ebae2a`

**3. [Rule 2 - Critical] Migration file missing pgvector extension CREATE statement**
- **Found during:** Task 3 verification
- **Issue:** Alembic autogenerate produced table creation statements but no `CREATE EXTENSION IF NOT EXISTS vector`. This would fail at apply time because the chunks table references `VECTOR(1536)` which requires the extension.
- **Fix:** Manually prepended `op.execute("CREATE EXTENSION IF NOT EXISTS vector")` as the first statement in `upgrade()`. Also added `import pgvector.sqlalchemy.vector` for the autogenerated chunk table column.
- **Files modified:** `server/alembic/versions/0001_initial_schema.py`
- **Commit:** `50f4874`

**4. [Rule 1 - Bug] asyncpg event-loop mismatch with pytest-asyncio session fixtures**
- **Found during:** Task 4 test execution (5th attempt)
- **Issue:** After session.rollback() in teardown, asyncpg's underlying connection retained transaction state. Next test got a connection already in a transaction, causing "cannot use Connection.transaction() in a manually started transaction" errors. Multiple patterns attempted: autobegin=False, manual BEGIN/ROLLBACK, connection-level control — all failed due to asyncpg session state conflicts.
- **Root cause:** `asyncio_default_test_loop_scope = "function"` (D-02 default) creates a new event loop per test function. Session-scoped fixtures (postgres_container, test_engine) run in the pytest session loop. asyncpg detected that the task was created in the function loop but the connection was from the session loop.
- **Fix:** Changed `asyncio_default_test_loop_scope = "session"` in pyproject.toml. All tests now run in the same event loop as the session-scoped fixtures. `db_session` is function-scoped (fresh session per test) with rollback at teardown.
- **Files modified:** `server/pyproject.toml`
- **Commit:** `2218b0f`

**5. [Rule 1 - Bug] Old alembic_version row (0002) from prior work caused autogenerate to fail**
- **Found during:** Task 3
- **Issue:** `alembic revision --autogenerate` failed with "Can't locate revision identified by '0002'" because a previous alembic_version row existed from an earlier incomplete attempt.
- **Fix:** Dropped and recreated the smartcopilot database before running autogenerate.
- **Files affected:** Database state only
- **Commit:** `50f4874`

## Known Stubs

None — all stub candidates are intentional design decisions:
- RLS policies not created (deferred to Phase 1b)
- Fernet key not validated in /health (deferred to Phase 6)
- `RESET app.current_user_id` in finally (no SET because auth not yet in Phase 1a)

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: env-leak | server/app/settings.py | SMARTCOPILOT_FERNET_KEY can be empty in dev; `.env` gitignored |
| threat_flag: rls-closed | server/alembic/versions/0001_initial_schema.py | Multi-tenant tables have RLS ENABLED but no policies — all queries return empty (fail-closed per Open Question 3) |

## Commits

| Commit | Description |
|--------|-------------|
| `d2bc6b1` | feat(01a-03): add app runtime — settings, database, dependencies, main, routes |
| `7ebae2a` | feat(01a-03): add Alembic config — env.py, alembic.ini, script template |
| `50f4874` | feat(01a-03): add 0001_initial_schema migration — 32 tables, pgvector, RLS, indexes |
| `2218b0f` | feat(01a-03): add pytest+testcontainers test harness — 7 boot tests, rollback isolation |

## Self-Check

- All 14 files exist at their expected paths
- `cd server && ruff check app/ alembic/` exits 0
- `cd server && pytest app/tests/ -v` exits 0 with 7 tests passing
- `grep -q 'CREATE EXTENSION IF NOT EXISTS vector' server/alembic/versions/0001_initial_schema.py`
- `grep -q 'vector_cosine_ops' server/alembic/versions/0001_initial_schema.py`
- `grep -q 'ENABLE ROW LEVEL SECURITY' server/alembic/versions/0001_initial_schema.py`
- `grep -q 'FORCE ROW LEVEL SECURITY' server/alembic/versions/0001_initial_schema.py`
- `grep -q 'chunks_embedding_hnsw_idx' server/alembic/versions/0001_initial_schema.py`
- `grep -c 'op.create_table(' server/alembic/versions/0001_initial_schema.py` = 32
- `! grep -q 'apscheduler_jobs' server/alembic/versions/0001_initial_schema.py`
- `grep -q 'RESET app.current_user_id' server/app/dependencies.py`
- `! grep -q 'SET LOCAL' server/app/dependencies.py`
- `! grep -q 'from app.database' server/alembic/env.py`
- `grep -q 'asyncio_default_test_loop_scope = "session"' server/pyproject.toml`

## Self-Check: PASSED