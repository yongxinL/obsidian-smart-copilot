# Phase 1 Context

## Phase: Foundation — Docker + Schema + Auth + VaultRegistry + Electron Shell
**Discussed:** 2026-04-13

---

## Library/Framework Decisions

**Python tooling:**
- `pyproject.toml` only — no `setup.py`. Build backend: hatchling or setuptools. `[tool.pytest.ini_options]` for test config. `[tool.ruff]` for linting + formatting (replaces flake8 + black + isort entirely).
- Python 3.12 pinned: `requires-python = ">=3.12"`. Matches `FROM python:3.12-slim` in Dockerfile (NOT pgvector base image for dev — only the Docker container uses pgvector/pgvector:pg16).

**Alembic:**
- Auto-generate migrations with `alembic revision --autogenerate --message "..."`, then manually review the diff before committing.
- First migration must manually add: `CREATE EXTENSION IF NOT EXISTS vector`, all RLS policy statements, and any expression-based or partial indexes not captured by autogenerate.
- Every migration file: descriptive `revision` message + comment block at top of `upgrade()` explaining what it does and why.

**Electron Forge:**
- Standard `vite-typescript` template — no custom template.
- Node 20 LTS: specified in `.nvmrc` (content: `20`) and `package.json` `engines.node: ">=20"`.

**Monorepo:**
- `pnpm-workspace.yaml` at repo root with `server/` and `client/` as workspace members.
- Root-level `pnpm codegen` script: starts backend, fetches `openapi.json` from running server, generates TypeScript types into `client/src/api/generated/`. Pre-commit hook enforces this — CI fails if generated types don't match committed.

---

## Patterns

**Backend — thin routes, service layer:**
- `app/api/` route handlers: validate input (Pydantic), call a service function, return a response model. No DB calls in route handlers.
- Service layer: `app/services/`. All business logic and DB access lives here.
- Exception: trivial reads where a service layer adds no value (e.g., `GET /health` reads `system_config` directly).
- Every Pydantic response schema: `model_config = ConfigDict(from_attributes=True)` so `.model_validate(orm_obj)` works without boilerplate.

**Frontend — API client singleton:**
- `client/src/api/client.ts`: global singleton that wraps OpenAPI-generated types. Injects auth headers, handles 401 refresh logic.
- Components never import from generated types directly — they call typed wrapper functions: `api.auth.login(...)`, `api.documents.list(...)`.
- This isolates components from codegen churn and centralizes refresh logic.
- Directory: `client/src/api/` with `client.ts` (singleton), `generated/` (codegen output), `index.ts` (barrel export for wrapper functions).

---

## Constraints

- Python 3.12 (`requires-python = ">=3.12"`)
- Node 20 LTS (`.nvmrc` + `package.json engines`)
- Dev environment: macOS or Linux. Windows dev not supported (Electron Forge can cross-compile for Windows but that's a Phase 1+ concern).
- No existing CI/CD pipeline to wire into — start fresh.
- `ENCRYPTION_KEY`: generate with `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. Document in `README.md`. `.env.example` with placeholder. Real `.env` is gitignored.
- `SECRET_KEY` (JWT): generate with `python3 -c "import secrets; print(secrets.token_hex(32))"`. Same `.env.example` pattern.
- `settings.yaml`: copy verbatim from PRD §22 into `server/config/settings.yaml.example`. App reads from `/config/settings.yaml` — fail fast with clear error if missing (do NOT fall back to defaults).

---

## Known Risks

1. **RLS context leak** — enforce with an integration test, not just code review. Write a test that explicitly verifies a connection returned to the pool after an exception does NOT carry the previous user's `app.current_user_id`. Cheap to write; catches future refactors that break the `finally:` block. A linter rule can't catch async context manager misuse reliably.

2. **Alembic sync/async split** — `alembic/env.py` needs a sync `DATABASE_URL` (psycopg2) for migration execution, while the app uses async (asyncpg). These are two separate URLs in the env. The sync import of psycopg2 in `env.py` is the ONLY place psycopg2 is allowed — comment this explicitly.

3. **watchdog thread handoff** — watchdog events fire in a background thread; IndexQueue processing must hand off to the asyncio event loop safely (use `loop.call_soon_threadsafe` or an asyncio Queue fed via thread-safe put).

4. **supervisord nodaemon=true** — required for Docker (supervisord must be PID 1). Missing this causes the container to exit immediately.

---

## Out of Scope (Phase 1)

- `/api/v1/projects` CRUD endpoints — `projects` table exists (for FK constraints on `conversations.project_id`); API does NOT. No Workspace UI beyond structural route stub at `/workspace`. **Full Workspace CRUD ships in Phase 5 (F-WORK-01).**
- `GET /api/v1/models` — Phase 2 (requires LiteLLM gateway).
- `GET/PUT /api/v1/settings` (user settings CRUD) — Phase 2; `user_settings` table exists, API doesn't.
- APScheduler reconciliation job — APScheduler is initialized in Phase 1, but the reconciliation job is NOT scheduled (nothing to reconcile until Phase 2).
- `GET /api/v1/vault/index/events` — Phase 6 per page map; `index_events` table exists from Phase 1 schema.
- Any RAG, embedding, chat, or editor functionality.
- **REQ-006 bulk-indexing `1000 notes < 5 minutes` perf target (NFR-003)** — verified in Phase 2's quality gate, not Phase 1. Phase 1's `bulk_index` does metadata-only (walk + upsert + wikilink extraction); **the `embedding` column is left NULL**. Do NOT call any embedding API from Phase 1 code. (`grep "embedding" server/app/vault/indexer.py | grep -v "^#"` must return no matches — enforcement check in PLAN-1-6 T-1-6-3.)
- `GET /api/v1/models/embedding` — Phase 2.
- `POST /api/v1/vault/reindex` — Phase 2.

---

## Enforcement Rules

**Must NOT exist (grep_must_not_exist):**
- `import psycopg2` in `server/app/` — asyncpg only; psycopg2 only in `alembic/env.py` with explicit comment
- `localStorage.setItem` / `sessionStorage.setItem` in `client/src/` — use safeStorage or electron-store
- `: any` in TypeScript files in `client/src/` — strict typing required
- `asyncio.get_event_loop()` in `server/app/` — use `asyncio.get_running_loop()`
- `os.environ\[.*(SECRET|KEY|TOKEN|PASSWORD)` in app code (outside config loading) — secrets via config module only
- Direct DB calls in `server/app/api/` route handlers (except `GET /health`) — service layer required

**Must exist (grep_must_exist):**
- `Depends(get_current_user)` in every protected route handler in `server/app/api/`
- `Depends(require_admin)` in every admin route handler in `server/app/api/admin.py`
- `model_config = ConfigDict(from_attributes=True)` in every Pydantic response schema
- `finally:` block with `RESET app.current_user_id` in `get_db_session`

**Naming conventions (naming_pattern):**
- React component files: flat, `PascalCase.tsx` — NOT `ComponentName/index.tsx`. Use `index.ts` only for barrel exports.
- Python service modules: `app/services/{noun}.py` (e.g., `app/services/auth.py`, `app/services/users.py`)
- Python models: `app/models/{noun}.py` matching SQLAlchemy table name
- Alembic migration filenames: auto-generated format `{rev}_{descriptive_message}.py` — never edit the rev prefix

---

## Design References

- `docs/ui-spec.md`: canonical reference for all frontend visual decisions.
- `docs/product_requirements.md` §26: page inventory and API bindings.

**Phase 1 fidelity:**
- **Login page**: implement to **full spec fidelity** — split layout, dark left branding panel, white right form, first-run "Create Admin Account" variant triggered by `setup_required: true`. This is a functional deliverable.
- **Home, Workspace, Customize, Chat History**: **structural only** — correct route, correct page shell (header + nav rail + page title), placeholder body content. No pixel-perfect work on stubs. Routing must work and nav must not crash.

---

## Verification Profile

**Custom** (not a generic electron-app or web-app profile). Four checkpoints. Each checkpoint must pass before Phase 1 is considered complete. Commands below are literal — run them verbatim.

### Checkpoint 1 — Bundled-container backend smoke

**Goal:** verify the single-container deployment path (supervisord-managed PostgreSQL + FastAPI) starts cleanly.

**Setup:**
```bash
# Generate required secrets (run in a throwaway shell; do NOT commit)
export ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Build and run the bundled container (internal PostgreSQL)
docker build -t smart-copilot:phase1 ./server
docker run -d --name sc-bundled \
  -e ENCRYPTION_KEY=$ENCRYPTION_KEY \
  -e SECRET_KEY=$SECRET_KEY \
  -v "$(pwd)/server/config/settings.yaml.example:/config/settings.yaml:ro" \
  -p 8000:8000 smart-copilot:phase1
```

**Pass criteria (all must hold):**
- `curl -sf http://localhost:8000/health` returns HTTP 200 **within 30 seconds** of `docker run`.
- Response JSON contains `"status": "ok"`, `"setup_required": true` (no users yet), `"database": "connected"`, `"version": "1.0.0"`.
- `docker exec sc-bundled supervisorctl status` shows both `postgresql` and `fastapi` in `RUNNING` state.
- `docker exec sc-bundled psql -U postgres -c "\dt"` lists all 17 tables.
- `docker logs sc-bundled 2>&1 | grep -c "alembic upgrade head"` returns ≥1 (migrations ran).

**Teardown:** `docker rm -f sc-bundled`.

---

### Checkpoint 2 — EXTERNAL_DB mode smoke (live PostgreSQL 16 + pgvector + RLS)

**Goal:** verify the external-DB deployment path works end-to-end. supervisord must skip the bundled PostgreSQL program; Alembic must run against the external DB; RLS policies and pgvector must be applied.

**Setup:**
```bash
# 1. Start a standalone PostgreSQL 16 with pgvector
docker run -d --name sc-external-pg \
  -e POSTGRES_PASSWORD=testpass \
  -e POSTGRES_DB=smartcopilot \
  -p 5432:5432 pgvector/pgvector:pg16

# 2. Wait for PostgreSQL to be ready (do not skip — Alembic will race otherwise)
until docker exec sc-external-pg pg_isready -U postgres; do sleep 1; done

# 3. Launch the app container with EXTERNAL_DB=true
export ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

docker run -d --name sc-external-app \
  --add-host=host.docker.internal:host-gateway \
  -e EXTERNAL_DB=true \
  -e DATABASE_URL="postgresql+asyncpg://postgres:testpass@host.docker.internal:5432/smartcopilot" \
  -e ENCRYPTION_KEY=$ENCRYPTION_KEY \
  -e SECRET_KEY=$SECRET_KEY \
  -v "$(pwd)/server/config/settings.yaml.example:/config/settings.yaml:ro" \
  -p 8000:8000 smart-copilot:phase1
```

**Pass criteria (all must hold):**
- `curl -sf http://localhost:8000/health` returns 200 within 30s with `"database": "connected"` and `"setup_required": true`.
- `docker exec sc-external-app supervisorctl status` shows `fastapi` as `RUNNING` and **no** `postgresql` program present (entrypoint.sh stripped it).
- `docker exec sc-external-pg psql -U postgres -d smartcopilot -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"` returns exactly 1 row (`vector`).
- `docker exec sc-external-pg psql -U postgres -d smartcopilot -c "SELECT count(*) FROM pg_tables WHERE rowsecurity = true AND schemaname = 'public';"` returns exactly `14`.
- `docker exec sc-external-pg psql -U postgres -d smartcopilot -c "SELECT count(*) FROM pg_policies WHERE schemaname = 'public';"` returns ≥ `14` (one policy per RLS-enabled table).
- `docker exec sc-external-pg psql -U postgres -d smartcopilot -c "\d chunks"` shows `embedding` column as type `vector(1536)` and `content_tsvector` as generated.
- `docker exec sc-external-pg psql -U postgres -d smartcopilot -c "SELECT key FROM system_config;"` includes `embedding` and `version` rows (seeded by first migration).
- HNSW index exists: `docker exec sc-external-pg psql -U postgres -d smartcopilot -c "SELECT indexname FROM pg_indexes WHERE tablename IN ('chunks', 'memories') AND indexdef LIKE '%hnsw%';"` returns ≥ 2 rows.

**Teardown:** `docker rm -f sc-external-app sc-external-pg`.

---

### Checkpoint 3 — pytest integration suite

**Goal:** automated regression coverage for the three highest-risk areas. Tests run against a real PostgreSQL with RLS enabled — no mocks.

**Setup:** requires `sc-external-pg` from Checkpoint 2 to still be running, OR spin up a fresh pg container as above with `POSTGRES_DB=smartcopilot_test`.

**Command:**
```bash
cd server
export TEST_DATABASE_URL="postgresql+asyncpg://postgres:testpass@localhost:5432/smartcopilot_test"
alembic -x database_url=postgresql+psycopg2://postgres:testpass@localhost:5432/smartcopilot_test upgrade head
pytest tests/integration/ -v
```

**Pass criteria:**
- `pytest tests/integration/test_rls.py -v` — all 4 tests pass (RLS isolation after exception, shared namespace access, private table isolation, api_keys shared access).
- `pytest tests/integration/test_auth.py -v` — all 10 tests pass (first-user-is-admin, login, refresh rotation, change-password, session revocation, admin create user, etc.).
- `pytest tests/integration/test_vault.py -v` — all 10 tests pass (VaultRegistry resolve private/shared/unknown, rebuild on user create, frontmatter extraction, wikilink regex, note type classifier priority).
- Total integration suite exit code: `0`.
- Coverage gate: `pytest --cov=app --cov-report=term --cov-fail-under=80` passes.

---

### Checkpoint 4 — Manual Electron walkthrough

**Goal:** verify first-run admin bootstrap + safeStorage + forced password change work end-to-end in the real Electron client. No Playwright in Phase 1.

**Pre-req:** bundled container from Checkpoint 1 running (or any backend reachable at `http://localhost:8000`), with **no users in the DB**.

**Steps (run in order, tick each box):**

1. `cd client && pnpm install && pnpm start` — Electron window opens, loads `/login` route.
2. Login page shows the `Create Admin Account` variant (because `GET /health` returned `setup_required: true`). Fields: username, email, password, confirm password. **No "Forgot?" link.**
3. Fill admin form → submit → backend returns 200 with tokens → app navigates to `/` (Home).
4. Kill the Electron process, restart it → app auto-logs in (tokens restored from `safeStorage`) → lands on `/` without showing login.
5. Inspect the Electron user data directory — confirm **no plaintext tokens** exist (tokens are OS-keychain-encrypted via safeStorage). On macOS: `~/Library/Application Support/smart-copilot-client/`. On Linux: `~/.config/smart-copilot-client/`.
6. Admin creates a second user via `POST /api/v1/admin/users` (curl or UI) with `must_change_password=true` → log out of admin account → log in as second user → **forced password change overlay blocks all navigation** → set new password → redirected to `/`.
7. Visit each nav-rail route (`/`, `/workspace`, `/customize`, `/history`, `/settings`) → each page stub renders without console errors.

**Pass criteria:** all 7 steps succeed without exception; Electron DevTools console shows **zero red errors** during the walkthrough.

---

## Autonomy Level

**Guided** — one retry with error context on failure, then surface to user with full stack trace and attempted fix if still failing. Never silently swallow failures.

---

## Known Gaps

All gaps resolved:
- `ENCRYPTION_KEY` generation: documented (`python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`) in README + `.env.example`
- `SECRET_KEY` generation: documented (`python3 -c "import secrets; print(secrets.token_hex(32))"`) in README + `.env.example`
- `settings.yaml`: built verbatim from PRD §22 → `server/config/settings.yaml.example`. App fails fast if `/config/settings.yaml` is missing — no silent default fallback.
