---
phase: 01a
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - server/app/__init__.py
  - pnpm-workspace.yaml
  - package.json
  - .nvmrc
  - .gitignore
  - .env.example
  - docker-compose.yml
  - clients/desktop/package.json
  - server/pyproject.toml
  - server/.python-version
  - server/requirements.txt
  - server/requirements-dev.txt
  - server/.pre-commit-config.yaml
autonomous: true
requirements: [INFRA-04, INFRA-05, INFRA-06]
must_haves:
  truths:
    - "pnpm install resolves both server and clients/desktop workspaces"
    - "ruff check on the server scaffold exits 0"
    - "Python 3.12 and Node 20 LTS are pinned in repo"
    - "pre-commit hooks (ruff-check, ruff-format) run successfully on a sample commit"
    - ".env.example is committed; .env is gitignored"
    - "docker-compose up -d brings PostgreSQL 16 + pgvector and pgAdmin online for dev"
  artifacts:
    - path: "pnpm-workspace.yaml"
      provides: "monorepo workspace declaration"
      contains: "packages:"
    - path: "package.json"
      provides: "root pnpm workspace package"
    - path: ".nvmrc"
      provides: "Node 20 LTS pin"
      contains: "20"
    - path: "server/pyproject.toml"
      provides: "Python 3.12 pin + Ruff config + pytest config"
      contains: "target-version = \"py312\""
    - path: "server/.python-version"
      provides: "Python 3.12 pin"
      contains: "3.12"
    - path: "server/.pre-commit-config.yaml"
      provides: "Ruff lint + format hooks"
      contains: "astral-sh/ruff-pre-commit"
    - path: "server/requirements.txt"
      provides: "runtime deps (FastAPI, SQLAlchemy, asyncpg, pgvector, etc.)"
    - path: "server/requirements-dev.txt"
      provides: "test deps (pytest, pytest-asyncio, testcontainers)"
    - path: ".env.example"
      provides: "safe placeholder env template"
      contains: "SMARTCOPILOT_FERNET_KEY"
    - path: "docker-compose.yml"
      provides: "dev inner-loop services (pgvector + pgAdmin)"
      contains: "pgvector/pgvector:pg16"
    - path: "clients/desktop/package.json"
      provides: "Electron client stub (Phase 8)"
  key_links:
    - from: ".pre-commit-config.yaml"
      to: "Ruff"
      via: "ruff-pre-commit hook"
      pattern: "astral-sh/ruff-pre-commit"
    - from: "pnpm-workspace.yaml"
      to: "server + clients/desktop"
      via: "packages glob"
      pattern: "packages:"
    - from: "pyproject.toml"
      to: "Ruff + pytest"
      via: "[tool.ruff] and [tool.pytest.ini_options]"
      pattern: "\\[tool\\.ruff\\]"
---

<objective>
Stand up the monorepo scaffold and Python tooling chain that all subsequent phases depend on. After this plan, a contributor on a clean clone can run `pnpm install`, `pip install -r server/requirements-dev.txt`, `pre-commit install`, and `ruff check server/app/` with zero errors. Dev compose brings up PostgreSQL 16 + pgvector and pgAdmin.

Purpose: Establish canonical project layout and tooling per D-13 (.env + pydantic-settings), D-12 (dev compose: pgvector + pgAdmin only), D-10/D-11 (compose for dev, monolithic image for prod), and the Claude's Discretion decision to limit pre-commit to Ruff in Phase 1a.

Output: Repo root scaffolded with pnpm workspaces, Node/Python pins, Ruff + pre-commit, .env.example, dev docker-compose, and Electron client stub.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/01a-container-data-layer/01a-CONTEXT.md
@.planning/phases/01a-container-data-layer/01a-RESEARCH.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create monorepo root scaffold (pnpm workspaces, Node/.gitignore/.env.example)</name>
  <files>pnpm-workspace.yaml, package.json, .nvmrc, .gitignore, .env.example, clients/desktop/package.json</files>
  <read_first>
    - CLAUDE.md (project layout constraints, monorepo policy, env var list)
    - .planning/phases/01a-container-data-layer/01a-CONTEXT.md (D-13 env vars, D-12 dev services)
    - .planning/phases/01a-container-data-layer/01a-RESEARCH.md (Pattern 11: pnpm workspaces; "Recommended Project Structure")
  </read_first>
  <action>
Create the monorepo root files (per D-04, D-05 monorepo layout in RESEARCH.md):

1. `pnpm-workspace.yaml`:
```yaml
packages:
  - "server"
  - "clients/desktop"
```

2. `package.json` (root):
```json
{
  "name": "smart-copilot",
  "private": true,
  "version": "0.0.0",
  "engines": { "node": ">=20" },
  "scripts": {
    "lint:py": "cd server && ruff check app/",
    "fmt:py": "cd server && ruff format app/",
    "test:py": "cd server && pytest app/tests/ -x -q",
    "compose:up": "docker compose up -d",
    "compose:down": "docker compose down -v"
  }
}
```

3. `.nvmrc` — single line: `20`

4. `.gitignore` — append (do not destroy existing entries; check current contents first):
```
# Python
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.ruff_cache/
*.egg-info/
.venv/
venv/

# Node / pnpm
node_modules/
.pnpm-store/

# Env files (CRITICAL: never commit real secrets per D-13)
.env
.env.local
.env.*.local

# Editor
.vscode/
.idea/

# Docker volumes for local dev
data/
vaults/
config/
```

5. `.env.example` (committed; placeholder values only, per D-13 and threat T-1a-02):
```
# Smart Copilot — local dev environment template
# Copy to .env (gitignored) and fill in real values for local development.
# NEVER commit .env. NEVER put real secrets in this file.

# Runtime DB (asyncpg) — used by FastAPI / services
DATABASE_URL=postgresql+asyncpg://smartcopilot:smartcopilot@localhost:5432/smartcopilot

# Migration DB (psycopg2) — used by Alembic env.py only
ALEMBIC_DATABASE_URL=postgresql+psycopg2://smartcopilot:smartcopilot@localhost:5432/smartcopilot

# Test DB — set automatically by testcontainers; leave blank locally
TEST_DATABASE_URL=

# Fernet key for at-rest API key encryption — generate with:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
SMARTCOPILOT_FERNET_KEY=REPLACE_ME_WITH_FERNET_KEY

# Public host URL (used in CORS, MCP host metadata)
SMARTCOPILOT_HOST_URL=http://localhost:8000

# Feature flags / debug
DEBUG=false
```

6. `clients/desktop/package.json` (Electron stub for Phase 8 — placeholder so workspace resolves):
```json
{
  "name": "@smart-copilot/desktop",
  "version": "0.0.0",
  "private": true,
  "description": "Smart Copilot Electron desktop client (deferred to Phase 8)",
  "scripts": {
    "build": "echo 'desktop client deferred to Phase 8' && exit 0"
  }
}
```

Use the Write tool for every file. Do NOT use heredoc. After writing, run `pnpm install` from the repo root to verify workspace resolution.
  </action>
  <verify>
    <automated>test -f pnpm-workspace.yaml && test -f package.json && test -f .nvmrc && test -f .gitignore && test -f .env.example && test -f clients/desktop/package.json && grep -q '^packages:' pnpm-workspace.yaml && grep -q '^20' .nvmrc && grep -q 'SMARTCOPILOT_FERNET_KEY=REPLACE_ME_WITH_FERNET_KEY' .env.example && grep -q '^\.env$' .gitignore && pnpm install --silent 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - `pnpm-workspace.yaml` contains the literal line `packages:` and references `"server"` and `"clients/desktop"`
    - `package.json` contains `"private": true` and `"engines": { "node": ">=20" }`
    - `.nvmrc` first line is exactly `20`
    - `.gitignore` contains `.env` on its own line (verifiable with `grep -q '^\.env$' .gitignore`)
    - `.env.example` contains all 6 variables: `DATABASE_URL=`, `ALEMBIC_DATABASE_URL=`, `TEST_DATABASE_URL=`, `SMARTCOPILOT_FERNET_KEY=REPLACE_ME_WITH_FERNET_KEY`, `SMARTCOPILOT_HOST_URL=`, `DEBUG=`
    - `.env.example` does NOT contain any real key (no base64 string > 30 chars after `SMARTCOPILOT_FERNET_KEY=` other than the placeholder)
    - `pnpm install` exits 0 and produces a `pnpm-lock.yaml`
    - `clients/desktop/package.json` contains `"name": "@smart-copilot/desktop"`
  </acceptance_criteria>
  <done>Monorepo root committed; pnpm install resolves both workspaces; .env.example present and free of real secrets; .env gitignored.</done>
</task>

<task type="auto">
  <name>Task 2: Create Python tooling — pyproject.toml, .python-version, requirements.txt, requirements-dev.txt, Ruff + pre-commit</name>
  <files>server/pyproject.toml, server/.python-version, server/requirements.txt, server/requirements-dev.txt, server/.pre-commit-config.yaml</files>
  <read_first>
    - CLAUDE.md (technology stack table — exact pinned versions; Ruff is sole linter)
    - .planning/phases/01a-container-data-layer/01a-RESEARCH.md (Pattern 10: Ruff config; Pattern 5: pytest-asyncio 1.x config; Standard Stack table — exact version pins; Pitfall 2: pytest-asyncio event_loop removed)
  </read_first>
  <action>
Create the Python project tooling. All version pins MUST match the CLAUDE.md "Versions Reference" table and RESEARCH.md "Standard Stack" table.

1. `server/.python-version` — single line: `3.12`

2. `server/pyproject.toml`:
```toml
[project]
name = "smart-copilot-server"
version = "0.0.0"
description = "Smart Copilot self-hosted AI knowledge brain — server"
requires-python = ">=3.12,<3.13"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["app*"]

[tool.ruff]
target-version = "py312"
line-length = 88
extend-exclude = ["alembic/versions"]

[tool.ruff.lint]
select = ["E", "F", "UP", "B", "I"]
ignore = ["E501"]

[tool.ruff.lint.per-file-ignores]
"alembic/versions/*.py" = ["E402"]
"app/tests/**/*.py" = ["S101"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.pytest.ini_options]
# pytest-asyncio 1.x: event_loop fixture override is REMOVED (Pitfall 2 / D-04).
# Use config-driven loop scoping instead.
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"
asyncio_default_test_loop_scope = "function"
testpaths = ["app/tests"]
addopts = "-ra --strict-markers"
markers = [
  "integration: integration tests requiring testcontainers (PostgreSQL via Docker)",
]
```

3. `server/requirements.txt` (runtime — match CLAUDE.md Versions Reference exactly):
```
fastapi>=0.111
uvicorn[standard]>=0.30
pydantic>=2
pydantic-settings>=2.0
python-dotenv>=1.0
sqlalchemy>=2.0
alembic>=1.13
asyncpg>=0.29
psycopg2-binary>=2.9
pgvector>=0.3
```

4. `server/requirements-dev.txt`:
```
-r requirements.txt
pytest>=8
pytest-asyncio>=1.0
testcontainers[postgres]>=4.0
ruff>=0.4
pre-commit>=4.0
```

5. `server/.pre-commit-config.yaml` (Ruff only per Claude's Discretion in CONTEXT.md; OpenAPI hook deferred to 1c):
```yaml
# Pre-commit hooks for Smart Copilot — Ruff only in Phase 1a.
# Per D-13 (Claude's Discretion): Ruff lint + format. OpenAPI regeneration deferred to Phase 1c.
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.9.0
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format
```

After writing, install dev deps and pre-commit:
```bash
cd server && pip install -r requirements-dev.txt
cd .. && cd server && pre-commit install --install-hooks
```

The empty `app/` directory does not yet exist — create `server/app/__init__.py` as an empty file so Ruff has a target to lint without errors. Run `cd server && ruff check app/` to confirm exit 0.
  </action>
  <verify>
    <automated>test -f server/pyproject.toml && test -f server/.python-version && test -f server/requirements.txt && test -f server/requirements-dev.txt && test -f server/.pre-commit-config.yaml && grep -q 'target-version = "py312"' server/pyproject.toml && grep -q 'asyncio_default_fixture_loop_scope = "session"' server/pyproject.toml && grep -q 'asyncio_mode = "auto"' server/pyproject.toml && grep -q 'astral-sh/ruff-pre-commit' server/.pre-commit-config.yaml && grep -q '^fastapi>=0.111' server/requirements.txt && grep -q '^asyncpg>=0.29' server/requirements.txt && grep -q '^psycopg2-binary>=2.9' server/requirements.txt && grep -q '^pgvector>=0.3' server/requirements.txt && grep -q '^testcontainers\[postgres\]>=4.0' server/requirements-dev.txt && cat server/.python-version | tr -d '[:space:]' | grep -qx '3.12' && (cd server && ruff check app/ 2>&1 | tail -3)</automated>
  </verify>
  <acceptance_criteria>
    - `server/.python-version` contains exactly `3.12`
    - `server/pyproject.toml` `[tool.ruff]` block contains `target-version = "py312"` and `line-length = 88`
    - `server/pyproject.toml` `[tool.ruff.lint]` block contains `select = ["E", "F", "UP", "B", "I"]`
    - `server/pyproject.toml` `[tool.pytest.ini_options]` contains all three: `asyncio_mode = "auto"`, `asyncio_default_fixture_loop_scope = "session"`, `asyncio_default_test_loop_scope = "function"` (D-04 + Pitfall 2)
    - `server/pyproject.toml` does NOT contain a fixture override `event_loop` (Pitfall 2: removed in 1.x)
    - `server/requirements.txt` contains exactly these lines (in any order, but all present): `fastapi>=0.111`, `uvicorn[standard]>=0.30`, `pydantic>=2`, `pydantic-settings>=2.0`, `python-dotenv>=1.0`, `sqlalchemy>=2.0`, `alembic>=1.13`, `asyncpg>=0.29`, `psycopg2-binary>=2.9`, `pgvector>=0.3`
    - `server/requirements-dev.txt` first line is `-r requirements.txt` and contains `pytest-asyncio>=1.0` and `testcontainers[postgres]>=4.0`
    - `server/.pre-commit-config.yaml` references `https://github.com/astral-sh/ruff-pre-commit` and registers both `ruff-check` and `ruff-format` hooks
    - `cd server && ruff check app/` exits 0 (empty package; placeholder __init__.py only)
  </acceptance_criteria>
  <done>Python tooling committed; ruff check passes on the empty app/ package; pre-commit installed locally; pytest-asyncio 1.x config locked in (no deprecated event_loop fixture).</done>
</task>

<task type="auto">
  <name>Task 3: Create dev docker-compose.yml (pgvector/pg16 + pgAdmin)</name>
  <files>docker-compose.yml</files>
  <read_first>
    - CLAUDE.md (base image policy: pgvector/pgvector:pg16; volumes; env vars)
    - .planning/phases/01a-container-data-layer/01a-CONTEXT.md (D-10, D-11, D-12: dev compose for pgvector + pgAdmin only — NO Mailpit)
  </read_first>
  <action>
Create `docker-compose.yml` at repo root for the dev inner loop. Per D-10/D-11/D-12: pgvector + pgAdmin only. Mailpit is deferred (CONTEXT.md "Deferred Ideas"). Production deployment uses the monolithic image (Plan 03), NOT this compose file.

```yaml
# Development docker-compose — inner-loop convenience only.
# Per D-10/D-11/D-12: dev runs PostgreSQL+pgvector + pgAdmin as separate containers;
# the Python app runs OUTSIDE compose with `uvicorn --reload` against this DB.
# Production uses the monolithic supervisord image (server/Dockerfile, Plan 03).
# Mailpit is INTENTIONALLY ABSENT — deferred per CONTEXT.md "Deferred Ideas".

services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: smart-copilot-postgres-dev
    environment:
      POSTGRES_USER: smartcopilot
      POSTGRES_PASSWORD: smartcopilot
      POSTGRES_DB: smartcopilot
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U smartcopilot -d smartcopilot"]
      interval: 5s
      timeout: 3s
      retries: 10

  pgadmin:
    image: dpage/pgadmin4:latest
    container_name: smart-copilot-pgadmin-dev
    environment:
      PGADMIN_DEFAULT_EMAIL: dev@smart-copilot.local
      PGADMIN_DEFAULT_PASSWORD: dev
      PGADMIN_CONFIG_SERVER_MODE: "False"
    ports:
      - "5050:80"
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - pgadmin:/var/lib/pgadmin

volumes:
  pgdata:
  pgadmin:
```

After writing, validate with `docker compose config` (no exec — just config validation).
  </action>
  <verify>
    <automated>test -f docker-compose.yml && grep -q 'pgvector/pgvector:pg16' docker-compose.yml && grep -q 'dpage/pgadmin4' docker-compose.yml && ! grep -q 'mailpit' docker-compose.yml && ! grep -qi 'mailpit' docker-compose.yml && docker compose config 2>&1 | tail -3</automated>
  </verify>
  <acceptance_criteria>
    - `docker-compose.yml` contains `image: pgvector/pgvector:pg16` (D-12: same image as production)
    - `docker-compose.yml` contains `image: dpage/pgadmin4` (D-12: dev pgAdmin)
    - `docker-compose.yml` does NOT contain the substring `mailpit` (case-insensitive) — Mailpit deferred
    - `docker-compose.yml` defines a `healthcheck` for the postgres service using `pg_isready`
    - `docker-compose.yml` exposes port `5432` on postgres and `5050` on pgadmin
    - `docker compose config` exits 0 (valid compose file)
  </acceptance_criteria>
  <done>Dev compose committed; postgres and pgadmin services validated; no Mailpit (deferred per CONTEXT.md).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| developer machine -> repo | Real secrets must never cross from `.env` (gitignored) into `.env.example` (committed) |
| repo -> docker-compose | Dev DB credentials are non-secret demo values; never share namespace with production |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-1a-02 | Information Disclosure | `.env.example`, `.gitignore` | mitigate | `.gitignore` includes `.env`, `.env.local`, `.env.*.local`; `.env.example` carries placeholder strings only (`REPLACE_ME_WITH_FERNET_KEY`); pre-commit + grep gate in acceptance verifies no real key strings present |
| T-1a-04 | Information Disclosure | `docker-compose.yml` dev credentials | accept | Hard-coded `smartcopilot:smartcopilot` is a non-secret dev credential bound to localhost; documented in compose file comment; never used in production (D-11) |
</threat_model>

<verification>
- `pnpm install` from repo root resolves both workspaces and produces lockfile
- `cd server && ruff check app/` exits 0
- `docker compose config` exits 0 and shows postgres + pgadmin services only (no mailpit)
- `grep -q '^\.env$' .gitignore` succeeds (env file gitignored)
- `grep -L 'REPLACE_ME_WITH_FERNET_KEY' .env.example` returns empty (placeholder present)
</verification>

<success_criteria>
- Monorepo root scaffold present (pnpm-workspace.yaml, package.json, .nvmrc)
- Server tooling present (pyproject.toml, .python-version, requirements*.txt, .pre-commit-config.yaml)
- Ruff + pre-commit configured per D-13 Claude's Discretion (Ruff only)
- pytest-asyncio 1.x config locked in (no deprecated event_loop fixture override per D-04 + Pitfall 2)
- Dev compose runs pgvector/pg16 + pgAdmin only (D-10, D-12); Mailpit absent
- `.env.example` committed with placeholder values; `.env` gitignored (D-13 + T-1a-02)
- All version pins match CLAUDE.md Versions Reference table
</success_criteria>

<output>
After completion, create `.planning/phases/01a-container-data-layer/01a-01-SUMMARY.md` with:
- Files created
- Versions pinned (exact)
- Confirmation that pre-commit hooks installed
- Any deviations from plan
</output>
