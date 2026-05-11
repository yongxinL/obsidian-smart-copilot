# Phase 1d: MCP Server + REST API + CLI - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-08
**Phase:** 1d — MCP Server + REST API + CLI
**Areas discussed:** brain_search scope, MCP tool set scope, WebSocket event bus, Vault REST URL prefix

---

## brain_search scope

### Q1: What should brain_search return before RAG exists?

| Option | Description | Selected |
|--------|-------------|----------|
| PostgreSQL tsvector full-text search | to_tsvector/websearch_to_tsquery over title + compiled_truth; zero extra deps; Phase 2a inherits column | ✓ |
| ILIKE pattern match | Simple ILIKE on compiled_truth + title; fast to implement; poor quality | |
| Stub — returns empty list | Returns [] with metadata noting Phase 2a; fastest to implement | |

**User's choice:** Option 1 — tsvector full-text search
**Notes:** Phase 1d search should cover title, slug, compiled_truth, and optionally timeline. Use websearch_to_tsquery or plainto_tsquery. Return page-level hits, not chunk-level RAG results. No embeddings, no LLMs. Response shape must be forward-compatible with Phase 2 hybrid search by reserving `chunk_hits[]` field.

---

### Q2: What does a brain_search result item look like?

| Option | Description | Selected |
|--------|-------------|----------|
| Page-level hit with score and snippet | {slug, title, note_type, score, snippet, matched_fields, page_id, updated_at, chunk_hits: []} | ✓ |
| Minimal page refs only | {slug, title, page_id, score} — simplest, would need breaking change in Phase 2a | |
| You decide | Claude picks shape | |

**User's choice:** Option 1 — full page-level hit with snippet and chunk_hits placeholder
**Notes:** chunk_hits should be empty array in Phase 1d (not omitted), for schema stability. Phase 2a adds real chunk hits without breaking callers.

---

### Q3: How should Phase 1d set up full-text search on pages?

| Option | Description | Selected |
|--------|-------------|----------|
| Add search_vector column + GIN index via Alembic | TSVECTOR generated stored; GIN index; Alembic migration 0004 | ✓ |
| Computed at query time — to_tsvector() in SELECT | No migration; no index; fine for Phase 1d vault sizes | |
| You decide | Claude picks | |

**User's choice:** Option 1 — materialized search_vector column with GIN index
**Notes:** Fold into 0001 if initial schema is not yet committed/applied; otherwise add as 0004. Phase 2a inherits the page-level search path and extends it with chunk-level BM25 + vector + graph.

---

## MCP tool set scope

### Q1: Which MCP tools ship as real implementations in Phase 1d?

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 1 surface only | 14 real tools (brain.* page ops + health/capabilities); stubs for future-phase tools | ✓ |
| Acceptance test minimum only | brain.put, brain.get, brain.search, capability_discovery, brain.health only | |
| Register all 30+ upfront with 501 stubs | Every MCP-06 tool registered; future phases fill implementations | |

**User's choice:** Option 1 — Phase 1 surface only
**Notes:** Do not implement future-phase business logic in Phase 1d. Stubs should be explicit, stable, discoverable, with phase metadata telling the client when the tool becomes real.

---

### Q2: How should stubbed MCP tools respond?

| Option | Description | Selected |
|--------|-------------|----------|
| Structured not_implemented with phase metadata | {error: {code: 'not_implemented', message: ..., available_in_phase: '2a'}} | ✓ |
| MCP error — raise McpError(NOT_FOUND) | Protocol-level error; less informative | |
| You decide | Claude picks | |

**User's choice:** Option 1 — structured not_implemented payload
**Notes:** NOT_FOUND should be reserved for unknown/unregistered tools. Stubs are intentionally registered and discoverable.

---

### Q3: How should MCP tool schemas be organized?

| Option | Description | Selected |
|--------|-------------|----------|
| Per-domain modules matching tool namespace | server/app/mcp/tools/{brain,ingest,enrich,recipe,skill,jobs,maintain,entity,graph,capability}.py | ✓ |
| Single tools.py file | server/app/mcp/tools.py; simpler upfront | |

**User's choice:** Option 1 — per-domain package
**Notes:** Phase 1d implements real tools in brain.py and capability.py. All other modules contain structured stubs.

---

## WebSocket event bus

### Q1: How does watchdog deliver indexing events to WebSocket clients?

| Option | Description | Selected |
|--------|-------------|----------|
| PostgreSQL LISTEN/NOTIFY | Watchdog pg_notify; FastAPI workers asyncpg LISTEN; cross-process, zero extra deps | ✓ |
| Polling the index_events table | WS handler polls every N seconds; simpler; higher latency | |
| In-process asyncio.Queue | Module-level broadcast queue; not viable (watchdog is separate process) | |

**User's choice:** Option 1 — PostgreSQL LISTEN/NOTIFY
**Notes:** Watchdog persists to index_events AND calls pg_notify. FastAPI worker routes notifications to matching WebSocket clients. Polling is not the primary mechanism.

---

### Q2: Should /ws filter events by user_id?

| Option | Description | Selected |
|--------|-------------|----------|
| Filter by user_id | Private events to owning user only; consistent with RLS isolation | ✓ |
| Broadcast to all authenticated clients | Every client sees every event; simpler fan-out | |
| You decide | Claude picks | |

**User's choice:** Option 1 — filter by user_id
**Notes:** Shared-vault events may be sent to all authenticated users only if explicitly marked namespace="shared" with no private path/content leakage. Phase 1d default: private events to owner only.

---

### Q3: What WebSocket auth mechanism?

| Option | Description | Selected |
|--------|-------------|----------|
| JWT token in query param | Standard WS auth; consistent with auth_deps.py | |
| MCP bearer in query param | Reuse MCP token for WS | |
| Support both JWT and MCP bearer | Maximum compatibility | |

**User's choice:** First-frame auth (per PRD), not query param
**Notes:** Client connects to /api/v1/ws, immediately sends {"type":"auth","data":{"token":"<access_jwt>"}}. Server validates JWT, builds OperationContext, binds socket to user_id. Invalid/missing = close socket.

---

## Vault REST URL prefix

### Q1: What URL prefix should vault/page REST endpoints use?

| Option | Description | Selected |
|--------|-------------|----------|
| /api/v1/brain/ | Mirrors MCP brain.* namespace | |
| /api/v1/vault/ | Mirrors code layer name | |
| /api/v1/pages/ | Explicit resource name; CRUD-natural | ✓ |

**User's choice:** Option 3 — /api/v1/pages/ for page CRUD
**Notes:** /api/v1/vault/ reserved for vault-level workflow/file operations (write, move, split, graph, index/events). /api/v1/brain/ not introduced — conflicts with PRD's REST API contract. brain.* stays as MCP tool namespace only.

---

### Q2: Should Phase 1d wire all REST endpoints upfront or only Phase 1d surface?

| Option | Description | Selected |
|--------|-------------|----------|
| Only Phase 1d surface | pages + search + capabilities + /ws + vault ops with real MCP tools | ✓ |
| Register all routes upfront as stubs | Full future API surface registered; future phases fill in | |
| You decide | Claude picks | |

**User's choice:** Option 1 — Phase 1d surface only
**Notes:** REST↔MCP parity is phase-aware. Future REST routes (ingest/enrich/skills/jobs/maintain) are not registered in Phase 1d.

---

## Claude's Discretion

- MCP SDK `stateless_http=True` and `json_response=True` (per CLAUDE.md)
- brain.stats content: vault-level stats without LLM or RAG
- brain.health shared service call with /health endpoint
- MCP tool input schemas use Pydantic models consistent with FastAPI conventions

## Deferred Ideas

None — discussion stayed within phase scope.
