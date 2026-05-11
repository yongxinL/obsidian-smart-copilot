# Phase 1d: MCP Server + REST API + CLI - Context

**Gathered:** 2026-05-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire up the complete external API surface on top of the Phase 1a–1c foundation:

- MCP stdio transport (`smartcopilot mcp serve --stdio`) with JSON-RPC framing; all log output to stderr
- MCP Streamable HTTP transport on port 8787; `stateless_http=True`; `Authorization: Bearer` via MCP token
- Both transports call the same tool implementations (no transport-specific logic in services)
- `server/app/mcp/tools/` per-domain package: `brain.py` (real), `capability.py` (real), all other modules (structured stubs)
- Real tools: brain.put, brain.get, brain.search, brain.list, brain.delete, brain.history, brain.diff, brain.revert, brain.append_timeline, brain.update_compiled_truth, brain.backlinks, brain.stats, brain.health, capability_discovery
- Stub tools: ingest.*, enrich.*, recipe.*, skill.*, jobs.*, maintain.*, brain.entity.*, brain.graph.*
- REST routes: `/api/v1/pages/` (page CRUD), `POST /api/v1/search`, `/api/v1/vault/` (vault-level operations), `GET /api/v1/capabilities`, `GET /api/v1/ws`
- WebSocket `/api/v1/ws`: first-frame JWT auth, user-filtered indexing events via PostgreSQL LISTEN/NOTIFY
- `brain_search` backed by PostgreSQL tsvector full-text search (page-level hits, no embeddings or LLM)
- CLI expansion: `doctor`, `check-resolvable`, `mcp serve`, vault CRUD, search, get, put, etc.
- Phase 1d acceptance test: new user → MCP token → Claude Code stdio → brain_put / brain_get / brain_search succeed

**Not in this phase:** chunk-level BM25 or vector search (Phase 2a), typed link extraction to `links` table (Phase 2b), entity enrichment (Phase 3), skills runtime (Phase 3), jobs/DAGs (Phase 7), admin observability endpoints (Phase 6).

</domain>

<decisions>
## Implementation Decisions

### brain_search (Phase 1d)

- **D-01:** `brain_search` uses PostgreSQL full-text search via `websearch_to_tsquery` (or `plainto_tsquery` as fallback) over `pages.title`, `pages.compiled_truth`, and optionally `pages.timeline`. Page-level hits only — no chunk-level results, no embeddings, no LLM calls.
- **D-02:** Response shape per result item: `{slug, title, note_type, score: float, snippet: str, matched_fields: list["title"|"compiled_truth"|"timeline"], page_id: UUID, updated_at: datetime, chunk_hits: []}`. `chunk_hits` is an empty array in Phase 1d (schema marks it optional). Shape is forward-compatible: Phase 2a adds real chunk hits without breaking callers.
- **D-03:** Add `pages.search_vector TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', coalesce(title,'') || ' ' || coalesce(compiled_truth,''))) STORED` + GIN index. Deliver via Alembic migration 0004 (or fold into a still-unapplied migration if applicable). Phase 2a inherits the column and GIN index for BM25 expansion.

### MCP Tool Set Scope

- **D-04:** Phase 1d ships **real** MCP implementations for: `brain.put`, `brain.get`, `brain.search`, `brain.list`, `brain.delete`, `brain.history`, `brain.diff`, `brain.revert`, `brain.append_timeline`, `brain.update_compiled_truth`, `brain.backlinks`, `brain.stats`, `brain.health`, `capability_discovery`. All other MCP-06 tools (`ingest.*`, `enrich.*`, `recipe.*`, `skill.*`, `jobs.*`, `maintain.*`, `brain.entity.*`, `brain.graph.*`) are registered as stubs.
- **D-05:** Stubbed tools return a structured not_implemented payload (normal MCP tool result, not a protocol-level error): `{"error": {"code": "not_implemented", "message": "tool available in Phase Xa", "available_in_phase": "2a"}}`. Tool is registered and discoverable; `NOT_FOUND` is reserved for unknown/unregistered tools.
- **D-06:** MCP tools organized as per-domain package `server/app/mcp/tools/`: `__init__.py`, `brain.py`, `ingest.py`, `enrich.py`, `recipe.py`, `skill.py`, `jobs.py`, `maintain.py`, `entity.py`, `graph.py`, `capability.py`. Phase 1d implements real tools in `brain.py` and `capability.py`; all others contain structured stubs.

### WebSocket Event Distribution

- **D-07:** PostgreSQL LISTEN/NOTIFY. The watchdog process writes to `index_events` table AND calls `pg_notify('index_events', json_payload)`. Each FastAPI worker maintains a dedicated asyncpg listener connection on the `'index_events'` channel. On notification, the worker routes the event to matching WebSocket connections for the owning user.
- **D-08:** Events filtered by `user_id`. Private vault events are delivered only to the owning user's WebSocket connections. Shared-vault events may be broadcast to all authenticated users only if the event payload is explicitly marked `namespace="shared"` and contains no private path or content leakage. Phase 1d default: private events to owner only.
- **D-09:** WebSocket auth via first frame (per PRD). Client connects to `/api/v1/ws`, immediately sends `{"type": "auth", "data": {"token": "<access_jwt>"}}`. Server validates JWT, builds `OperationContext`, binds socket to `user_id`. Invalid or missing token → server closes the socket. No token in query string.

### REST URL Design

- **D-10:** Page CRUD REST routes use `/api/v1/pages/` (resource-oriented):
  - `GET /api/v1/pages` — list (maps to `brain.list`)
  - `GET /api/v1/pages/{slug}` — read (maps to `brain.get`)
  - `PUT /api/v1/pages/{slug}` — write (maps to `brain.put`)
  - `DELETE /api/v1/pages/{slug}` — soft delete (maps to `brain.delete`)
  - `POST /api/v1/pages/{slug}/timeline` — append timeline (maps to `brain.append_timeline`)
  - `PUT /api/v1/pages/{slug}/compiled_truth` — update compiled truth (maps to `brain.update_compiled_truth`)
  - `GET /api/v1/pages/{slug}/history` — history (maps to `brain.history`)
  - `GET /api/v1/pages/{slug}/diff` — diff (maps to `brain.diff`)
  - `POST /api/v1/pages/{slug}/revert` — revert (maps to `brain.revert`)
  - `GET /api/v1/pages/{slug}/backlinks` — backlinks (maps to `brain.backlinks`)
  - `POST /api/v1/search` — page-level FTS (maps to `brain.search`)
- **D-11:** Vault-level workflow/file operations use `/api/v1/vault/`: `POST /api/v1/vault/write`, `/vault/move`, `/vault/split`, `GET /api/v1/vault/graph`, `GET /api/v1/vault/index/events`. Phase 1d wires only what has corresponding real MCP tools.
- **D-12:** REST↔MCP parity is phase-aware. Phase 1d wires only REST counterparts for Phase 1d MCP tools. Future-phase stub MCP tools may return `not_implemented` at their REST counterparts if registered. REST routes for `ingest/enrich/skills/jobs/maintain` are NOT registered in Phase 1d.

### CLI Expansion

- **D-13:** Phase 1d expands the CLI stub with: `smartcopilot mcp serve [--stdio|--http]`, `smartcopilot doctor`, `smartcopilot check-resolvable`, `smartcopilot reconcile [--deep]`, vault CRUD commands (`page get/put/delete/list/search`), and `smartcopilot stats`. Existing `user`, `mcp token`, `provider_key` subcommands from Phase 1b are carried forward unchanged.
- **D-14:** `smartcopilot doctor` reports: Fernet key status, inotify watch limit (`/proc/sys/fs/inotify/max_user_watches`), CORS config, MCP token storage mode (sha256-hashed; AUTH-04 — plaintext shown once at creation, only the hash is stored). `smartcopilot check-resolvable` validates the skills tree for reachability — an empty tree passes cleanly at Phase 1.

### Claude's Discretion

- MCP SDK version `>= 1.25, < 2` (per CLAUDE.md); `stateless_http=True` and `json_response=True` for Streamable HTTP (per CLAUDE.md notes)
- STDIO auth: read `SMARTCOPILOT_MCP_TOKEN` env var on process start; validate via `auth.core.validate_bearer`
- `brain.stats` returns vault-level stats (page count, size, last indexed, etc.) without requiring LLM or RAG
- `brain.health` returns container health + component status (DB connection, Fernet key, watchdog alive)
- `brain.diff` and `brain.revert` operate on `page_versions` table populated in Phase 1c
- MCP tool input schemas use Pydantic models (consistent with CLAUDE.md's FastAPI/Pydantic v2 conventions); output schemas use same Pydantic response models as REST layer
- `GET /api/v1/capabilities` returns: `{transports: ["stdio", "http"], ingestion_limits: {}, clipboard_available: false, phase: "1d"}`

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product Requirements
- `docs/product_requirements_document_v26.05.md` — authoritative PRD (v26.05.1). Phase 1d directly implements: §9 (MCP server, tools, auth), §10 (REST + WebSocket API), §11–12 (CLI admin tools + admin REST), §28 (Phase acceptance tests). Requirements MCP-01–MCP-08, REST-01–REST-06, CLI-01–CLI-05, TEST-03, TEST-04.

### Planning Artifacts
- `.planning/REQUIREMENTS.md` — structured requirements for MCP-01–08, REST-01–06, CLI-01–05, TEST-03, TEST-04 scoped to Phase 1d
- `.planning/ROADMAP.md` — Phase 1d goal, success criteria (5 items), and dependency on Phase 1c
- `.planning/phases/01c-vault-watchdog-indexer/01c-CONTEXT.md` — Phase 1c decisions (compiled-truth/timeline, wikilink, watchdog handoff, OpenAPI hook). Phase 1d inherits all; D-06 (run_coroutine_threadsafe) is relevant to watchdog→pg_notify integration.

### Technology References (from CLAUDE.md)
- MCP Python SDK `>= 1.25, < 2` — `stateless_http=True`, `json_response=True`, never write to stdout in stdio mode
- `asyncpg` for runtime DB (not psycopg2); LISTEN/NOTIFY via raw asyncpg connection (not SQLAlchemy)
- FastAPI `>= 0.111`, Pydantic v2 — `Field(exclude=True)` on sensitive fields, services never import FastAPI types

### Existing Stubs to Wire
- `server/app/mcp/server.py` — current stub that raises `NotImplementedError`; Phase 1d replaces with real MCP SDK
- `server/app/cli/main.py` — Phase 1b argparse stub; Phase 1d extends with new subcommands

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server/app/services/pages.py` — full page CRUD, version snapshots, compiled-truth/timeline enforcement; all `brain.*` page tools call into this service
- `server/app/services/users.py`, `mcp_tokens.py`, `sessions.py`, `provider_keys.py` — complete; CLI expansion calls these directly
- `server/app/auth/core.py` — `validate_bearer()` is the MCP stdio auth entry point (D-21 seam already in place)
- `server/app/auth/deps.py` — FastAPI auth dependencies; WebSocket handler needs a WS-specific variant (can't use `Depends()` for WS upgrade)
- `server/app/auth/context.py` — `OperationContext` dataclass; `system_operation_context()` for CLI use
- `server/app/models/index_event.py` — `IndexEvent` model; watchdog writes here; WS handler reads/subscribes via LISTEN/NOTIFY
- `server/app/main.py` — error envelope handler (`{error: {code, message}}`) already wired; new routes added via `app.include_router()`

### Established Patterns
- Services are transport-agnostic: `OperationContext` in, domain objects out — no FastAPI types (enforced from Phase 1b)
- `session_with_rls()` async generator for all DB calls; `SET app.current_user_id` + `RESET` in `finally:` (critical — Phase 1b)
- Routes follow: validate input → call service → return Pydantic response model (thin routes)
- `encrypted_key` fields use `Field(exclude=True)` on every Pydantic response model
- APScheduler reconciliation job lives in `server/app/scheduler/jobs/`; watchdog NOTIFY call follows same async-in-separate-process pattern as existing scheduler jobs

### Integration Points
- `main.py` `create_app()` — add WebSocket route and new REST routers here
- `supervisord.conf` — MCP HTTP process (`mcp-http`, priority 30) will invoke `python -m app.mcp.server --http`; Phase 1d replaces the `NotImplementedError` stub
- `docs/openapi.json` — pre-commit hook (Phase 1c) regenerates on route changes; adding Phase 1d routes triggers automatic regeneration

</code_context>

<specifics>
## Specific Ideas

- brain_search POST body: `{query: str, limit: int = 20, namespace: "private"|"shared"|"all" = "private"}`; response: `{results: [...], total: int, query: str, search_type: "fts_v1"}`
- The `search_type` field in the response envelope is a forward-compatibility hook: Phase 2a changes it to `"hybrid_v1"` without breaking the shape
- WebSocket auth failure: server sends `{"type": "auth_error", "error": {"code": "unauthorized", ...}}` then closes — consistent with REST-04 error codes
- `brain.health` and `GET /api/v1/health` may share the same service call; `brain.health` is the MCP tool, `/health` is the shallow HTTP ping (existing)
- `capability_discovery` MCP tool and `GET /api/v1/capabilities` return the same payload; they share one service function (REST-01 parity)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 1d — MCP Server + REST API + CLI*
*Context gathered: 2026-05-08*
