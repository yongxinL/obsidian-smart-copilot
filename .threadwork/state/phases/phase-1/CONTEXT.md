# Phase 1 Context

## Phase: Foundation (Weeks 1–2)
**Discussed**: 2026-04-15

Docker container (supervisord + wait-for-pg.sh), Alembic migrations (full schema), auth system (JWT, register, login, password change, require_admin, must_change_password), user management CRUD + password reset, VaultRegistry + file watcher (watchdog) + IndexQueue, markdown parser (frontmatter + wikilink extraction), NoteTypeClassifier, Workspace CRUD (UI-only shell), indexing progress endpoint. Electron shell with Forge + Vite, Login page, API client generated from OpenAPI spec, auth flow (JWT safeStorage, refresh, forced password change).

## Library/Framework Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Password hashing | `argon2-cffi` directly | No passlib wrapper — argon2-cffi's API is straightforward enough. |
| Alembic migration style | Single initial migration covering all 17 tables + RLS policies | Grouping by table creates artificial ordering complexity. Alembic handles dependency resolution. |
| Test framework | `pytest` + `pytest-asyncio` (asyncio_mode = "auto") + `httpx` AsyncClient | No SQLite — test suite runs against real PostgreSQL only. |
| Settings loading | `pydantic-settings` with custom `YamlSettingsSource` | `pydantic-settings[yaml]` extra (pulls pyyaml). Env var overrides + validation + typed settings object. |
| Logging | stdlib `logging` with JSON formatter | No structlog or loguru. Single `logging.config.dictConfig` in `main.py`. JSON formatter for production, plain for dev (controlled by `settings.debug`). |

## Patterns

| Pattern | Rule |
|---|---|
| Service layer | Thin routes calling service functions. Route handlers: validate input → call service → return response. No business logic in route handlers. |
| Dependency injection | `Depends(get_db)` and `Depends(get_current_user)` / `Depends(require_admin)` are the full DI surface. Settings via module-level singleton (loaded once in `config.py`). VaultRegistry via singleton. |

## Constraints

- Python packages pinned to minor versions in requirements.txt (e.g., `fastapi>=0.115,<0.116`). Patch updates allowed in CI without PR.
- No minimum coverage gate in Phase 1 — but all auth flows and RLS session lifecycle must have integration tests as a quality gate condition.
- `asyncio_mode = "auto"` in `pyproject.toml` is **required** — no `@pytest.mark.asyncio` decorators on individual tests.
- All 27 locked architecture decisions from PRD Section 4 apply.

## Known Risks

| Risk | Detail | Mitigation |
|---|---|---|
| Alembic + asyncpg mismatch | `env.py` must use a synchronous `psycopg2` connection string, not the `asyncpg` URL used by the app. Agents frequently get this wrong → hard-to-debug startup failure. | Enforce separate `ALEMBIC_DATABASE_URL` or rewrite URL scheme in `env.py`. |
| supervisord nodaemon | If `nodaemon=true` is omitted, the container exits immediately after PostgreSQL starts. Looks like a PostgreSQL crash. | Enforce `nodaemon=true` in supervisord.conf. Verify in Docker smoke test. |
| RLS context leak | `SET app.current_user_id` not RESET → user data leaks to next request on the same connection. | `RESET` in `finally` block (Decision 23). Integration test: two users cannot see each other's data. |

## Out of Scope

- No embeddings, chunking, or LLM calls of any kind
- Watcher parses frontmatter and wikilinks only — no enrichment, no `enrichment_hash` population
- `GET /api/v1/models`, `GET /api/v1/settings`, and `POST /api/v1/projects` endpoints exist as stubs only (return 501 or empty list) — wired up in Phase 2/5
- No `api_keys` encryption logic exercised in Phase 1 (`encryption.py` exists but is not called from routes)
- No RAG pipeline, no editor, no agent, no memory

## Enforcement Rules

### Must-NOT-exist (grep_must_not_exist)

| Rule | Pattern | Scope |
|---|---|---|
| No print() for logging | `print(` in `server/app/` (excluding tests) | backend |
| No raw SQL outside allowed locations | Raw SQL strings outside `rag/queries.py` and `alembic/versions/` | backend |
| No plaintext secrets | `ENCRYPTION_KEY`, `SECRET_KEY`, or API key literals in committed files | all |
| No wildcard imports | `import *` anywhere in Python codebase | backend |
| No sync SQLAlchemy in async handlers | `session.execute(` without `await` in `server/app/api/` | backend |
| No SET LOCAL for RLS | `SET LOCAL` for `app.current_user_id` | backend |

### Must-exist (grep_must_exist)

| Rule | Pattern | Scope |
|---|---|---|
| RLS-protected routes use get_db | `Depends(get_db)` in all route handlers querying RLS tables | backend API |
| Admin endpoints use require_admin | `Depends(require_admin)` on all admin-only endpoints | backend API |
| Pydantic base config | `model_config = ConfigDict(from_attributes=True)` on response schemas | backend schemas |
| RLS RESET in finally | `RESET app.current_user_id` inside `finally` in `get_db_session` | backend dependencies |
| Explicit __tablename__ | `__tablename__` on every SQLAlchemy model | backend models |
| wait-for-pg.sh polls before start | `pg_isready` check before `alembic upgrade head` and `uvicorn` | scripts |

### Naming conventions (naming_pattern)

| Rule | Pattern | Scope |
|---|---|---|
| Python identifiers | `snake_case` for all filenames, functions, variables | backend |
| API routes | `/api/v1/{resource}` RESTful paths | backend API |
| SQLAlchemy models | `PascalCase` class names, `snake_case` `__tablename__` | backend models |
| Pydantic schemas | `{Resource}Create`, `{Resource}Update`, `{Resource}Response` | backend schemas |
| Test files | `test_{module}.py` mirroring `app/` structure | tests |
| Alembic revisions | `{verb}_{noun}` in snake_case (e.g., `create_users_table`) | migrations |
| CSS modules | `.sc-` prefix for all class names | frontend |

## Design References

- `docs/design/prototype/` — HTML prototypes (Login page, Electron shell)
- `docs/ui-spec.md` — design tokens, components, layout specs
- **Fidelity: Structural** — correct layout and components, styling can vary. Apply `--sc-*` tokens and correct Radix primitives. Two-column Login layout (dark branding left / white form right, first-run variant). Pixel-perfect spacing deferred to Phase 2+.

## Verification Profile

**Type**: `smart-copilot-phase1` (custom — combined backend + frontend)

| Check | Type | Gate |
|---|---|---|
| `GET /health` Docker smoke test | automated | Backend alive, PostgreSQL connected, `setup_required` field correct |
| pytest integration suite: RLS isolation | automated | Two users cannot see each other's data |
| pytest integration suite: full auth flow | automated | register → login → refresh → change-password |
| pytest integration suite: VaultRegistry path resolution | automated | Path → (user_id, namespace) mapping correct |
| Manual Electron walkthrough: admin bootstrap | manual | First-run → create admin → login |
| Manual Electron walkthrough: safeStorage | manual | Token survives app restart |

## Autonomy Level

**Guided** — Agents retry with guidance from specs, document decisions with `# DECISION:` comments, and escalate only for: schema changes, deviations from the 27 locked decisions, or ambiguity not resolvable from the PRD.

## Known Gaps

| Gap | Resolution |
|---|---|
| CI/CD | Deferred to Phase 8. Phase 1 gets a Makefile with `make test`, `make build`, `make docker-build` targets only. No GitHub Actions. |
| Logging configuration | Resolved: stdlib `logging` + JSON formatter. `logging.config.dictConfig` in `main.py`. |
| Settings loading | Resolved: `pydantic-settings[yaml]` with custom `YamlSettingsSource`. |
