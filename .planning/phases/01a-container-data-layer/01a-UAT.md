---
status: complete
phase: 01a-container-data-layer
source: [01a-01-SUMMARY.md, 01a-02-SUMMARY.md, 01a-03-SUMMARY.md, 01a-04-SUMMARY.md]
started: 2026-05-10T03:30:00Z
updated: 2026-05-10T03:30:00Z
---

## Current Test

number: 1
name: Cold Start Smoke Test
expected: |
  Kill any running containers. Run `docker build -t smart-copilot:1a server/` then
  `docker run --rm -p 8000:8000 smart-copilot:1a`. Container should:
  - Start PostgreSQL and pgvector within 30 seconds
  - Run Alembic migrations successfully
  - Start all 5 supervisord programs (postgresql, fastapi, mcp-http, apscheduler, watchdog)
  - Respond to GET /health with {"status":"ok"}
awaiting: user response

## Tests

### 1. Cold Start Smoke Test
expected: |
  Kill any running containers. Run `docker build -t smart-copilot:1a server/` then
  `docker run --rm -p 8000:8000 smart-copilot:1a`. Container should:
  - Start PostgreSQL and pgvector within 30 seconds
  - Run Alembic migrations successfully
  - Start all 5 supervisord programs (postgresql, fastapi, mcp-http, apscheduler, watchdog)
  - Respond to GET /health with {"status":"ok"}
result: pass

### 2. Dev Environment Setup
expected: |
  On a fresh clone: `pnpm install` completes without errors and produces pnpm-lock.yaml.
  `cd server && pip install -r requirements-dev.txt` completes.
  `ruff check app/` exits with 0 violations.
result: pass

### 3. Docker Compose Dev Stack
expected: |
  `docker compose up -d` brings up pgvector/pg16 and pgAdmin.
  `docker compose ps` shows both services healthy.
  `docker compose exec postgres pg_isready` returns success.
result: pass

### 4. Test Harness
expected: |
  `cd server && pytest app/tests/integration/test_boot.py -v` runs against a real
  PostgreSQL container (testcontainers) with rollback-per-test isolation.
  All 7 tests pass.
result: pass
note: "Warning about missing Fernet key is expected (Phase 1b sets this)"

### 5. Alembic Migration
expected: |
  `cd server && alembic upgrade head` creates all 32 tables in the database.
  Tables: users, sessions, mcp_tokens, provider_keys, vaults, pages, page_versions,
  chunks, entities, links, timeline_events, tags, jobs, audit_logs, skills, recipes,
  eval_candidates, conversations, messages, memories, dream_audit_logs, projects,
  operation_logs, llm_usage, index_events, user_settings, system_configs, mcp_servers,
  golden_eval, and junction tables.
result: pass

### 6. Monorepo Structure
expected: |
  `pnpm-workspace.yaml` exists and declares "packages" with server and clients/desktop.
  `server/pyproject.toml` has Python 3.12 target, ruff config, pytest-asyncio config.
  `package.json` has root scripts for lint, test, etc.
result: pass

### 7. Pre-commit Hooks
expected: |
  `pre-commit install` succeeds.
  `pre-commit run --all-files` runs ruff-check and ruff-format.
  No errors on clean codebase.
result: pass

### 8. Model Definitions
expected: |
  All 28 model files exist under server/app/models/ (one per domain per D-07).
  Each file has proper SQLAlchemy 2.0 Mapped[] types.
  No ruff violations.
result: pass

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0

## Gaps

- truth: "pgAdmin starts successfully and remains healthy"
  status: resolved
  reason: "Changed PGADMIN_DEFAULT_EMAIL to admin@smartcopilot.dev — valid format that passes pgAdmin validation"
  severity: minor
  test: 3

- truth: "Container boots without errors, all 5 supervisord programs RUNNING, /health returns 200"
  status: resolved
  reason: "Fixed in UAT: pre-compute escaped vars before psql -c. User confirmed container starts successfully."
  severity: blocker
  test: 1