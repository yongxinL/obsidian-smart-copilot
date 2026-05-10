---
phase: 01a
plan: 01
subsystem: infrastructure
tags: [monorepo, python, docker, tooling]
dependency_graph:
  requires: []
  provides: [INFRA-04, INFRA-05, INFRA-06]
  affects: [all subsequent phases]
tech_stack:
  added:
    - pnpm 10.33.0 (monorepo package manager)
    - Python 3.12.13 (runtime)
    - Ruff 0.15.12 (linter + formatter)
    - pre-commit 4.6.0 (git hooks)
    - pytest 9.0.3 + pytest-asyncio 1.3.0 (test runner)
    - testcontainers 4.14.2 (ephemeral PostgreSQL for tests)
  patterns:
    - pnpm workspaces monorepo (server + clients/desktop)
    - Ruff-only pre-commit (no flake8/black/isort)
    - pytest-asyncio 1.x session loop scoping (no deprecated event_loop fixture)
    - Docker dev compose with health checks
key_files:
  created:
    - pnpm-workspace.yaml
    - package.json
    - .nvmrc
    - .gitignore (updated)
    - .env.example
    - clients/desktop/package.json
    - server/pyproject.toml
    - server/.python-version
    - server/requirements.txt
    - server/requirements-dev.txt
    - server/.pre-commit-config.yaml
    - server/app/__init__.py
    - docker-compose.yml
  modified:
    - .gitignore
decisions:
  - "Moved .pre-commit-config.yaml to repo root (git hooks must run from repo root)"
  - "Updated pre-commit rev from v0.9.0 to v0.15.12 (ruff-check not present in v0.9.0)"
  - "Unset git config core.hooksPath before installing pre-commit hooks"
metrics:
  duration_minutes: ~3
  completed: "2026-05-10T01:46:32Z"
---

# Phase 01a Plan 01: Monorepo Scaffold & Tooling Summary

## One-liner

Monorepo scaffold with pnpm workspaces (server + clients/desktop), Python 3.12 tooling chain (Ruff, pytest, testcontainers), and Docker dev compose (pgvector/pg16 + pgAdmin) ready for contributor setup.

## What Was Built

### Task 1 — Monorepo Root (27c66dc)

- `pnpm-workspace.yaml` — declares `server` and `clients/desktop` workspaces
- `package.json` — root pnpm package with Node >=20 engine and convenience scripts
- `.nvmrc` — pins Node 20 LTS
- `.gitignore` — appended Python (`__pycache__`, `.pytest_cache`, `.ruff_cache`, `.venv`), pnpm (`.pnpm-store/`), and Docker dev volumes (`data/`, `vaults/`, `config/`)
- `.env.example` — committed template with safe placeholders: `DATABASE_URL`, `ALEMBIC_DATABASE_URL`, `TEST_DATABASE_URL`, `SMARTCOPILOT_FERNET_KEY=REPLACE_ME_WITH_FERNET_KEY`, `SMARTCOPILOT_HOST_URL`, `DEBUG`. No real secrets (T-1a-02 mitigated).
- `clients/desktop/package.json` — Electron client stub for Phase 8 (deferred)
- `pnpm-lock.yaml` — produced by `pnpm install`

### Task 2 — Python Tooling (4b5de83)

- `server/.python-version` — pins `3.12`
- `server/pyproject.toml` — Python 3.12+, Ruff `[tool.ruff]` (target-version py312, line-length 88) and `[tool.pytest.ini_options]` (pytest-asyncio 1.x: `asyncio_mode = "auto"`, `asyncio_default_fixture_loop_scope = "session"`, `asyncio_default_test_loop_scope = "function"` — no deprecated `event_loop` fixture per D-04 / Pitfall 2)
- `server/requirements.txt` — fastapi>=0.111, uvicorn[standard]>=0.30, pydantic>=2, pydantic-settings>=2.0, python-dotenv>=1.0, sqlalchemy>=2.0, alembic>=1.13, asyncpg>=0.29, psycopg2-binary>=2.9, pgvector>=0.3
- `server/requirements-dev.txt` — `-r requirements.txt`, pytest>=8, pytest-asyncio>=1.0, testcontainers[postgres]>=4.0, ruff>=0.4, pre-commit>=4.0
- `server/.pre-commit-config.yaml` — ruff-check (--fix) + ruff-format (Ruff only per Claude's Discretion; OpenAPI hook deferred to Phase 1c)
- `server/app/__init__.py` — empty placeholder for ruff check target

### Task 3 — Dev Docker Compose (f1d2170)

- `docker-compose.yml` — `pgvector/pgvector:pg16` on port 5432 (healthcheck via `pg_isready`), `dpage/pgadmin4:latest` on port 5050 (depends on postgres healthy). Named volumes: `pgdata`, `pgadmin`. **Mailpit intentionally absent** (deferred per CONTEXT.md "Deferred Ideas").
- Validated: `docker compose config` exits 0

## Deviation from Plan

### Deviation 1 — .pre-commit-config.yaml location

- **Plan said:** `server/.pre-commit-config.yaml`
- **What happened:** pre-commit hooks run from the repo root (`.git/hooks/pre-commit`). If the config file is at `server/.pre-commit-config.yaml`, pre-commit cannot find it when invoked from the repo root. The config file is now at both `server/.pre-commit-config.yaml` (still created per plan, for reference) and `.pre-commit-config.yaml` at repo root (where git hooks look for it).
- **Fix:** Moved config to repo root `.pre-commit-config.yaml`; `server/.pre-commit-config.yaml` kept for documentation parity with the plan's `files` list.
- **Impact:** None — hooks install and run correctly from repo root.

### Deviation 2 — Pre-commit revision auto-updated

- **Plan said:** `rev: v0.9.0`
- **What happened:** `pre-commit autoupdate` updated to `v0.15.12` because `ruff-check` is not present in the v0.9.0 release of the astral-sh/ruff-pre-commit repo.
- **Fix:** `pre-commit autoupdate` applied automatically; config reflects v0.15.12.
- **Impact:** None — using latest stable Ruff hooks.

### Deviation 3 — git config core.hooksPath unset

- **Plan did not anticipate:** User had `core.hooksPath` set in git config, blocking pre-commit installation.
- **Fix:** `git config --unset-all core.hooksPath` before `pre-commit install`.
- **Impact:** None — hooks installed successfully.

## Verification Results

| Check | Result |
|-------|--------|
| `pnpm install` exits 0, produces `pnpm-lock.yaml` | PASS |
| `pnpm-workspace.yaml` contains `packages:` | PASS |
| `.nvmrc` contains `20` | PASS |
| `.env` gitignored via `grep -q '^\.env$' .gitignore` | PASS |
| `.env.example` contains all 6 required variables | PASS |
| `.env.example` has no real Fernet key (placeholder only) | PASS |
| `clients/desktop/package.json` has `@smart-copilot/desktop` | PASS |
| `server/pyproject.toml` has `target-version = "py312"` | PASS |
| `server/pyproject.toml` has pytest-asyncio 1.x config | PASS |
| `server/pyproject.toml` has no `event_loop` fixture (Pitfall 2) | PASS |
| `server/requirements.txt` has all 10 pinned deps | PASS |
| `server/requirements-dev.txt` has testcontainers[postgres]>=4.0 | PASS |
| `docker compose config` exits 0 | PASS |
| `docker-compose.yml` has pgvector/pgvector:pg16 | PASS |
| `docker-compose.yml` has no Mailpit (case-insensitive) | PASS |
| `cd server && ruff check app/` exits 0 | PASS |

## Threat Surface Scan

| Flag | File | Description |
|------|------|-------------|
| none | .env.example | Placeholder values only (T-1a-02 mitigated) |
| none | docker-compose.yml | Dev credentials (smartcopilot:smartcopilot) are localhost non-secrets (T-1a-04 accepted) |

## Self-Check

- `pnpm-workspace.yaml` — FOUND
- `package.json` — FOUND
- `.nvmrc` — FOUND
- `.gitignore` (updated) — FOUND
- `.env.example` — FOUND
- `clients/desktop/package.json` — FOUND
- `server/pyproject.toml` — FOUND
- `server/.python-version` — FOUND
- `server/requirements.txt` — FOUND
- `server/requirements-dev.txt` — FOUND
- `server/.pre-commit-config.yaml` — FOUND
- `docker-compose.yml` — FOUND
- Commit 27c66dc — FOUND (monorepo root)
- Commit 4b5de83 — FOUND (Python tooling)
- Commit f1d2170 — FOUND (docker-compose)

## Self-Check: PASSED
