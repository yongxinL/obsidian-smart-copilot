# Roadmap: Smart Copilot

## Overview

Smart Copilot is built in strict horizontal layers — foundational infrastructure and security before RAG and agent surfaces, skills and enrichment before nightly dream consolidation, and operational features before platform polish. Seven phases (with fine-granularity sub-phases where the work density demands it) deliver a fully MCP-native, self-hosted AI knowledge brain. The Electron desktop client is deferred post-v1. Every phase ends with a concrete acceptance test runnable from a terminal or Claude Code.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (1a, 1b, 1c): Fine-granularity sub-phases derived from work density
- Decimal insertions (2.1, 2.2): Urgent insertions added post-planning (via `/gsd-insert-phase`)

Decimal sub-phases execute in order within their parent integer phase.

- [ ] **Phase 1a: Container + Data Layer** - Docker/supervisord, PostgreSQL 16 + pgvector, monorepo scaffold, core models and Alembic migrations (planned)
- [x] **Phase 1b: Auth + Security Primitives** - Argon2 password hashing, JWT sessions, MCP bearer tokens, Fernet-encrypted API keys, RLS enforcement (completed 2026-05-10)
- [ ] **Phase 1c: Vault + Watchdog Indexer** - Page CRUD with compiled-truth/timeline convention, frontmatter parsing, wikilink resolution, filesystem watchdog
- [ ] **Phase 1d: MCP Server + REST API + CLI** - Stdio and HTTP MCP transports, REST/WebSocket API, smartcopilot CLI binary
- [ ] **Phase 2a: LLM Gateway + Hybrid RAG Pipeline** - LiteLLM router, chunker/embedder, pgvector HNSW, BM25 tsvector, RRF fusion engine
- [ ] **Phase 2b: Knowledge Graph + Agent Runner** - Zero-LLM wikilink extraction, typed graph, recursive CTE traversal, 22-tool ReAct agent, golden query eval
- [ ] **Phase 3: Skills + Ingestion + Entity Enrichment** - Skills runtime, RESOLVER.md, default skill pack, idea/media/meeting ingestion, tiered entity enrichment
- [ ] **Phase 4: Memory Dream + Brain Maintenance** - Nightly consolidation cycle, orphan/dead-link audit, memory extraction, maintenance report
- [ ] **Phase 5: Web Search + Projects + Vault Intelligence** - DuckDuckGo/Jina/Wikipedia search, project-scoped RAG, vault organize/suggest, embedding migration
- [ ] **Phase 6: Admin Surfaces + Observability** - Prometheus metrics, structured JSON logs, audit log API, full admin REST, user cost dashboards
- [ ] **Phase 7: MCP Registry + Durable Job DAGs + Backup** - External MCP server registry, APScheduler parent-child DAGs, automated backup + verified restore

## Phase Details

### Phase 1a: Container + Data Layer
**Goal**: A single Docker container boots with supervisord as PID 1, PostgreSQL 16 + pgvector initializes, Alembic migrations run before uvicorn starts, and the monorepo scaffold with all tooling (Ruff, pre-commit, pnpm) is in place
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, INFRA-06, INFRA-07, INFRA-08, TEST-01
**Success Criteria** (what must be TRUE):
  1. `docker run` starts the container and supervisord reports all 5 programs (postgres, fastapi, mcp-http, apscheduler, watchdog) as RUNNING within 30 seconds
  2. PostgreSQL 16 with pgvector extension is reachable inside the container; `CREATE EXTENSION IF NOT EXISTS vector` succeeds without errors
  3. Alembic migrations run to completion before uvicorn accepts connections; `/health` returns 200 with `{status: ok}` after boot
  4. `pytest` runs against a real PostgreSQL test database (no DB mocks); the test suite passes with zero failures on a clean clone
  5. Ruff formatting check and pre-commit hooks pass on the initial scaffold commit
**Plans**: 4 plans
- [x] 01a-01-PLAN.md — Monorepo scaffold + Python tooling + dev compose (INFRA-04, INFRA-05, INFRA-06)
- [x] 01a-02-PLAN.md — Domain models package (27 model files, 32 tables) (INFRA-07)
- [x] 01a-03-PLAN.md — App runtime + Alembic + test harness (INFRA-07, INFRA-03, TEST-01)
- [x] 01a-04-PLAN.md — Production Dockerfile + supervisord + boot verification (INFRA-01, INFRA-02, INFRA-03, INFRA-08)
**UI hint**: no

### Phase 1b: Auth + Security Primitives
**Goal**: All authentication and authorization primitives are in place — users can be created via CLI, JWT sessions issued, MCP bearer tokens generated, provider API keys stored encrypted, and PostgreSQL RLS enforces per-user data isolation
**Depends on**: Phase 1a
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, AUTH-07, AUTH-08, AUTH-09, AUTH-10, TEST-02
**Success Criteria** (what must be TRUE):
  1. `smartcopilot user create --username alice --role admin` succeeds; `POST /auth/login` returns `{access_jwt, refresh_token}`; invalid credentials are rejected with `rate_limited` after 10 failures per 15 minutes
  2. MCP bearer token is issued via CLI; token plaintext shown once and not stored; `last_used_at` updates on every authenticated request; token is revocable within 5 seconds
  3. RLS isolation test passes: a request executed as user A leaves no `app.current_user_id` GUC set on the pooled connection after the request scope exits (user B cannot see user A's pages)
  4. Provider API key stored as Fernet-encrypted BYTEA; decrypted value never returned in any API response; container refuses to start if `SMARTCOPILOT_FERNET_KEY` env var is absent
  5. Step-up re-auth endpoint `POST /api/v1/admin/reauth` grants the admin fresh-auth window; destructive admin operations without fresh auth return `forbidden`
**Plans**: 8 plans (6 waves)
- [x] 01B-01-test-foundation-PLAN.md — Wave 0 — requirements deltas + Settings extension + structlog redaction + 14 test stubs + auth conftest (TEST-02 stub authored)
- [x] 01B-02-migration-and-models-PLAN.md — Alembic 0002 (login_attempts table, sessions.admin_fresh_until, 22 RLS POLICY blocks, system user seed) + LoginAttempt model
- [x] 01B-03-encryption-PLAN.md — Fernet/MultiFernet seam + Landmine #4 source-level gate (AUTH-09)
- [x] 01B-04-auth-primitives-PLAN.md — auth/{context,password,tokens,mcp_tokens}.py + 12 unit tests (AUTH-01, AUTH-02, AUTH-04; Landmines #2, #3, #6 closed)
- [x] 01B-05-core-rls-deps-PLAN.md — auth/{core,audit}.py + dependencies.py SET 3 GUCs + database.py PoolEvents.reset listener + 5 RLS isolation tests (TEST-02 headline)
- [x] 01B-06-services-and-deps-PLAN.md — services/{users,sessions,mcp_tokens,provider_keys}.py + auth/deps.py + 8 integration tests
- [x] 01B-07-routes-and-middleware-PLAN.md — TrustedProxyMiddleware + routes/{auth,admin}.py + main.py startup-fail + APScheduler prune job + 23 integration tests
- [x] 01B-08-cli-and-acceptance-PLAN.md — smartcopilot CLI stub + repo-wide grep gates + Phase 1b acceptance test + populate VALIDATION.md
**UI hint**: no

### Phase 1c: Vault + Watchdog Indexer
**Goal**: Pages can be written and read through the page CRUD layer with compiled-truth/timeline convention enforced, frontmatter parsed, wikilinks resolved, content-hash deduplication active, and the filesystem watchdog indexing changes in near-real-time
**Depends on**: Phase 1b
**Requirements**: VAULT-01, VAULT-02, VAULT-03, VAULT-04, VAULT-05, VAULT-06, VAULT-07, VAULT-08, VAULT-09, VAULT-10, VAULT-11, IDX-01, IDX-02, IDX-03, IDX-04
**Success Criteria** (what must be TRUE):
  1. Writing a page creates it under the correct private vault path (`/vaults/private/{username}/`); symlink escapes and `..` traversal are rejected with `forbidden`; cross-namespace access to `[[shared/Topic]]` resolves correctly
  2. Page written with compiled-truth + timeline convention stores above-the-line content as rewritable summary and below-the-line as append-only event log; page versions table records every change with `deleted_at` + `delete_reason` on soft delete
  3. Frontmatter parsed and page type recognized (`person`, `company`, `concept`, `idea`, etc.); xxhash64 content-hash computed from raw file bytes; re-index triggered only when hash changes
  4. Watchdog detects a vault file modification within 1 second (inotify on Linux); thread-to-asyncio handoff uses `run_coroutine_threadsafe` exclusively (not `call_soon_threadsafe`); reconciliation job corrects filesystem/database drift
  5. OpenAPI spec auto-generated at `/docs` and `docs/openapi.json` regenerated by pre-commit hook on route changes
**Plans**: 8 plans (4 waves)
- [ ] 01c-01-PLAN.md — Wave 0 — Alembic migration 0003 (timeline, deleted_by, enum fix) + Page/PageVersion model updates + settings + requirements.txt (VAULT-04, VAULT-06, VAULT-07, VAULT-08)
- [ ] 01c-02-PLAN.md — Wave 0 — Wave 0 test stubs + vault conftest.py (all VAULT/IDX requirements)
- [ ] 01c-03-PLAN.md — Wave 1 — vault/parser.py + vault/paths.py + real unit tests (VAULT-01, VAULT-04, VAULT-05, VAULT-07, VAULT-10)
- [ ] 01c-04-PLAN.md — Wave 2 — services/pages.py + 4 integration test files (VAULT-02, VAULT-03, VAULT-04, VAULT-06, VAULT-07, VAULT-08, VAULT-09)
- [ ] 01c-05-PLAN.md — Wave 3 — vault/watcher.py real watchdog + test_watcher.py (IDX-01, IDX-02, IDX-03)
- [ ] 01c-06-PLAN.md — Wave 3 — scheduler/jobs/reconcile_vault.py + scheduler/run.py extension + test_reconcile.py (IDX-04)
- [ ] 01c-07-PLAN.md — Wave 4 — scripts/regen_openapi.py + pre-commit hook + docs/openapi.json + test_openapi.py (VAULT-11)
- [ ] 01c-08-PLAN.md — Wave 1 (gap closure) — Fix CR-01 commit placement in reconcile_vault.py + add mcp/apscheduler to requirements.txt + align IDX-02 text with D-06 decision (IDX-02, IDX-04)
**UI hint**: no

### Phase 1d: MCP Server + REST API + CLI
**Goal**: All MCP tools, REST endpoints, and CLI commands for the Phase 1 feature surface are wired up and pass the Phase 1 acceptance test — Claude Code connects via stdio MCP, performs brain_put/brain_get/brain_search, and the CLI can perform full user/token management
**Depends on**: Phase 1c
**Requirements**: MCP-01, MCP-02, MCP-03, MCP-04, MCP-05, MCP-06, MCP-07, MCP-08, REST-01, REST-02, REST-03, REST-04, REST-05, REST-06, CLI-01, CLI-02, CLI-03, CLI-04, CLI-05, TEST-03, TEST-04
**Success Criteria** (what must be TRUE):
  1. Claude Code connects via `smartcopilot mcp serve --stdio` with `SMARTCOPILOT_MCP_TOKEN`; `brain_put` writes a page, `brain_get` retrieves it, `brain_search` returns matching results — all three succeed against a seeded vault
  2. MCP Streamable HTTP server on port 8787 accepts `Authorization: Bearer` token; both transports call identical service functions (no transport-specific logic in services); `test_tool_rest_parity` passes for all Phase 1 tools
  3. MCP stdio test asserts no unexpected bytes on stdout after initialization; all log output routes to stderr; JSON-RPC framing is uncorrupted
  4. `smartcopilot doctor` runs smoke tests and reports Fernet key status, inotify watch limit, CORS config, and MCP token storage mode; `smartcopilot check-resolvable` reports skill tree status (empty tree passes cleanly at Phase 1)
  5. Every REST endpoint returns errors in `{error: {code, message, details?}}` format with stable codes; `GET /api/v1/capabilities` returns transport list, ingestion limits, and clipboard availability; WebSocket `/ws` streams indexing progress events
**Plans**: 6 plans (5 waves)

**Wave 1** — Foundation
- [ ] 01d-01-PLAN.md — Migration 0004 (search_vector + GIN) + extended services/pages.py + services/capabilities.py (REST-05, REST-06)

**Wave 2** *(blocked on Wave 1 completion)*
- [ ] 01d-02-PLAN.md — MCP server (stdio + HTTP) + tools/ package + services/vault_resolver.py (14 real + 17 stubs) (MCP-01..08)

**Wave 3** *(blocked on Wave 2 completion — 01d-03 and 01d-05 run in parallel)*
- [ ] 01d-03-PLAN.md — REST routes (pages, search, vault, capabilities) + REST↔MCP parity test + openapi.json (REST-01, REST-02, REST-04, REST-05, REST-06, CLI-04, CLI-05)
- [ ] 01d-05-PLAN.md — CLI expansion (page CRUD, doctor, check-resolvable, mcp serve, reconcile, stats) (CLI-01, CLI-02, CLI-03)

**Wave 4** *(blocked on Wave 3 completion)*
- [ ] 01d-04-PLAN.md — WebSocket /api/v1/ws + LISTEN/NOTIFY plumbing + watcher pg_notify migration (REST-03, REST-04)

**Wave 5** *(blocked on Wave 4 completion)*
- [ ] 01d-06-PLAN.md — Phase 1d acceptance test (TEST-04) + stdio cleanliness invariant (TEST-03) + VALIDATION.md (TEST-03, TEST-04, MCP-08)

**Cross-cutting constraints:**
- `session_with_rls(ctx)` required for all DB operations (present in Plans 01–05)
- No FastAPI types in services/ (enforced by acceptance criteria grep gates in Plans 02–05)
- `asyncio.run_coroutine_threadsafe` for watchdog→asyncio handoff (Plan 04)
**UI hint**: no

### Phase 2a: LLM Gateway + Hybrid RAG Pipeline
**Goal**: All LLM calls route through `llm/router.py` for cost tracking and key injection; the hybrid retrieval pipeline (pgvector HNSW + BM25 tsvector + RRF fusion) returns ranked, citation-backed results from the vault
**Depends on**: Phase 1d
**Requirements**: LLM-01, LLM-02, LLM-03, LLM-04, LLM-05, RAG-01, RAG-02, RAG-03, RAG-04, RAG-05, RAG-06, RAG-07
**Success Criteria** (what must be TRUE):
  1. LiteLLM imported as library (no proxy process); all embedding and completion calls go through `llm/router.py`; `llm_usage` table records provider, model, input/output tokens, and cost_usd for every request; direct LiteLLM calls from services or routes fail Ruff lint
  2. `brain.search` with a semantic query returns top-k results ranked by RRF (vector + BM25 + graph fused); compiled-truth sections receive +0.15 RRF boost; stale pages (compiled truth >30 days behind latest timeline) are annotated in results
  3. pgvector type registered via pool `init` callback (`register_vector` on every new connection); HNSW index created with `m=16, ef_construction=64`; embedding dimension pre-insert assert prevents dimension mismatch
  4. Multi-query expansion generates 3 paraphrases via cheap LLM tier; 4-layer deduplication runs before results returned; intent classifier routes queries to the correct retrieval mode
  5. Embedding migration endpoints (estimate/start/status/cancel) allow dimension-change migration: add column → backfill concurrently → `CREATE INDEX CONCURRENTLY` → atomic rename; migration progresses without downtime
**Plans**: TBD
**UI hint**: no

### Phase 2b: Knowledge Graph + Agent Runner
**Goal**: Zero-LLM typed wikilink extraction populates the knowledge graph on every page write; the 22-tool ReAct agent can query the brain before any external call; golden query eval suite measures retrieval quality
**Depends on**: Phase 2a
**Requirements**: GRAPH-01, GRAPH-02, GRAPH-03, GRAPH-04, GRAPH-05, GRAPH-06, AGENT-01, AGENT-02, AGENT-03, AGENT-04, AGENT-05, AGENT-06, TEST-05
**Success Criteria** (what must be TRUE):
  1. Writing a page containing `[[John Smith]]` triggers deterministic zero-LLM link extraction; extracted link recorded with type (`works_at`, `invested_in`, `founded`, etc.) in the `links` table; `brain.backlinks` returns correct reverse traversal
  2. `brain.graph.traverse` resolves `who works at Acme Corp` and `what did Y invest in` query patterns via recursive CTE (no external graph engine); B-tree index on `links.src_page_id` and `links.dst_entity_id` confirmed by query plan
  3. Agent queries local brain (`search`/`get_page`) before any external API call; ReAct loop with all 22 tools operational; `skill_run` tool stub present and callable (wired to skills runtime in Phase 3); `jobs.submit` tool submits to APScheduler
  4. Multi-turn conversation recorded in `conversations` table with citations, token usage, and model tracking; `mcp_mode` (`disable`/`auto`/`manual`) and `web_search_enabled` flags respected
  5. Golden query eval suite initialized: `golden_query_suites` and `golden_queries` tables seeded with fixture corpus; `golden_query_runs` records Precision@K, Recall@K, MRR, nDCG@K, p95 latency; retrieval benchmark passes quality gate before Phase 3
**Plans**: TBD
**UI hint**: no

### Phase 3: Skills + Ingestion + Entity Enrichment
**Goal**: The skills runtime dispatches intents through RESOLVER.md, the default skill pack handles idea/media/meeting ingestion end-to-end, and tiered entity enrichment automatically upgrades stubs to full dossiers
**Depends on**: Phase 2b
**Requirements**: SKILLS-01, SKILLS-02, SKILLS-03, SKILLS-04, SKILLS-05, SKILLS-06, SKILLS-07, INGEST-01, INGEST-02, INGEST-03, INGEST-04, INGEST-05, ENRICH-01, ENRICH-02, ENRICH-03, ENRICH-04
**Success Criteria** (what must be TRUE):
  1. Pasting a meeting transcript via `ingest.meeting` MCP tool creates or updates person and company pages with compiled-truth summary and timeline entry; typed wikilinks auto-extracted; `smartcopilot ingest <transcript.md>` CLI produces the same result
  2. `idea-ingest` skill creates a fleeting note with typed links; `media-ingest` skill processes PDF (PyMuPDF), DOCX, and URL (readability + nh3) inputs; HTML is always converted to markdown before storage; re-ingesting identical content produces no duplicate (content-hash dedup)
  3. RESOLVER.md skill dispatches intents to the correct skill deterministically; `smartcopilot check-resolvable` passes with zero orphaned triggers, MECE coverage enforced; `skillify check` and `skillify scaffold` CLI commands functional
  4. Entity enrichment triggered by `enrichment_hash` change on page write; T1 (free web/Wikipedia), T2 (cheap LLM), T3 (strong LLM) tiers applied proportionally to mention count; `enrich.entity` MCP/REST tool and `smartcopilot enrich` CLI operational; re-enrichment storm prevented (1-hop limit, 5-min per-page debounce)
  5. `skill_run` agent tool calls skills runtime end-to-end (Phase 2 stub now fully wired); `recipe.run` MCP/REST tool executes YAML data-research pipelines; per-user and system skill namespaces both resolve with correct override semantics
**Plans**: TBD
**UI hint**: no

### Phase 4: Memory Dream + Brain Maintenance
**Goal**: The nightly Memory Dream consolidation cycle runs under advisory lock, audits the vault for stale pages, dead links, orphans, and citation health, and emits a queryable maintenance report accessible via MCP and REST
**Depends on**: Phase 3
**Requirements**: DREAM-01, DREAM-02, DREAM-03, DREAM-04, DREAM-05, DREAM-06
**Success Criteria** (what must be TRUE):
  1. Nightly Dream job runs at scheduled time under `pg_try_advisory_lock`; a second concurrent trigger is refused (no double execution); `dream_audit_log` records run_at, kind, status, pages_processed, memories_created, errors for every run
  2. Dream detects stale pages (compiled truth >30 days behind latest timeline), dead wikilinks, orphan pages, and citation URL failures; defects are archived (soft-deleted, not hard-deleted); `maintain.report` MCP/REST endpoint returns the latest report
  3. `maintain.run` MCP/REST tool triggers on-demand Dream with `--dry-run` option; `smartcopilot maintain run [--dry-run]` CLI produces same report; maintenance report emitted as a brain page queryable via `brain.search`
  4. Memory extraction from conversations: `memories` table populated with extracted insights, `archived` flag, and `source_conversation_id`; memories contribute to future RAG retrieval
**Plans**: TBD
**UI hint**: no

### Phase 5: Web Search + Projects + Vault Intelligence
**Goal**: Agents can search the web and blend results with vault knowledge, users can create project-scoped RAG contexts, vault intelligence surfaces orphans and hub pages, and embedding migration tooling is operator-accessible
**Depends on**: Phase 4
**Requirements**: WEB-01, WEB-02, WEB-03, WEB-04, WEB-05, INTEL-01, INTEL-02, INTEL-03, ADMIN-02
**Success Criteria** (what must be TRUE):
  1. Query prefixed with `@web` triggers DuckDuckGo + Jina Reader + Wikipedia search; results ranked and cited; cross-vault references to matching local pages detected and surfaced alongside web results
  2. Project created via `POST /api/v1/projects` with `include_folders`, `exclude_folders`, `tags`, and optional system prompt; `brain.search` inside a project scope returns only pages within the project definition; per-user RLS enforced on `projects` table
  3. Vault intelligence endpoints return orphan pages (no inbound links), hub pages (high in-degree), and link suggestions; `/vault/organize` proposes reorganization; `/vault/organize/apply` applies it; `/vault/organize/undo` reverts it
  4. `smartcopilot extract links` and `smartcopilot extract timeline` CLI commands backfill graph and timeline data for an existing vault; embedding migration (estimate/start/status/cancel) accessible to admin without downtime
**Plans**: TBD
**UI hint**: no

### Phase 6: Admin Surfaces + Observability
**Goal**: Operators can monitor system health via Prometheus metrics, query structured audit logs, manage users and costs via admin REST, and view per-user usage dashboards — all without a UI
**Depends on**: Phase 5
**Requirements**: OBS-01, OBS-02, OBS-03, OBS-04, OBS-05, ADMIN-01, ADMIN-03, ADMIN-04
**Success Criteria** (what must be TRUE):
  1. `GET /metrics` returns Prometheus-formatted metrics including per-user request counts, LLM token usage, and cost_usd; all supervisord process logs route to Docker stdout/stderr (no log files inside container)
  2. `audit_log` table records every admin mutation with `request_id` for correlation with `OperationContext`; `GET /api/v1/admin/audit-log` endpoint returns filterable audit events; `OBS-03` REST endpoint passes auth and pagination tests
  3. Admin can create users, rotate shared API keys, view per-user LLM cost via REST without a UI; `index_events` table tracks indexing activity per user/page; all admin REST endpoints enforce `role='admin'` AND fresh auth for destructive operations
  4. `GET /health` and `smartcopilot doctor` report postgres connectivity, pgvector extension, Fernet key status, inotify watch limit, CORS config, and embedding dimension consistency; `smartcopilot smoke-test` runs drop-in scripts from `/etc/smartcopilot/smoke-tests.d/*.sh`
**Plans**: TBD
**UI hint**: no

### Phase 7: MCP Registry + Durable Job DAGs + Backup
**Goal**: Admins can register external MCP servers that expand the agent's tool surface, background jobs execute as persistent parent-child DAGs across container restarts, and a verified backup/restore procedure protects all data
**Depends on**: Phase 6
**Requirements**: REGISTRY-01, REGISTRY-02, REGISTRY-03, JOBS-01, JOBS-02, JOBS-03, JOBS-04, JOBS-05, BACKUP-01, BACKUP-02, BACKUP-03
**Success Criteria** (what must be TRUE):
  1. Admin registers an external `stdio` MCP server via `POST /api/v1/admin/mcp-servers`; agent's tool surface includes the external server's tools at runtime; `always_allow` list bypasses per-call approval for whitelisted tools
  2. `jobs.submit` submits a parent job that spawns child jobs; DAG survives a container restart mid-execution and resumes from the last completed step; `jobs.cancel` halts execution; idempotency key prevents duplicate submission
  3. `smartcopilot backup create` produces a deterministic archive of PostgreSQL dump + `/vaults/` + `/config/`; `smartcopilot backup verify` runs the smoke test suite against a restored instance and reports pass/fail; restore procedure documented in Appendix G
  4. APScheduler runs in dedicated supervisord process (never inside uvicorn); `pg_try_advisory_lock` prevents duplicate Dream job execution across workers; `coalesce=True` and `max_instances=1` enforced on all scheduled jobs
**Plans**: TBD
**UI hint**: no

## Progress

**Execution Order:**
Phases execute in order: 1a → 1b → 1c → 1d → 2a → 2b → 3 → 4 → 5 → 6 → 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1a. Container + Data Layer | 4/4 | Complete | 2026-05-10 |
| 1b. Auth + Security Primitives | 8/8 | Complete   | 2026-05-10 |
| 1c. Vault + Watchdog Indexer | 0/8 | Not started | - |
| 1d. MCP Server + REST API + CLI | 0/6 | Not started | - |
| 2a. LLM Gateway + Hybrid RAG Pipeline | 0/TBD | Not started | - |
| 2b. Knowledge Graph + Agent Runner | 0/TBD | Not started | - |
| 3. Skills + Ingestion + Entity Enrichment | 0/TBD | Not started | - |
| 4. Memory Dream + Brain Maintenance | 0/TBD | Not started | - |
| 5. Web Search + Projects + Vault Intelligence | 0/TBD | Not started | - |
| 6. Admin Surfaces + Observability | 0/TBD | Not started | - |
| 7. MCP Registry + Durable Job DAGs + Backup | 0/TBD | Not started | - |
