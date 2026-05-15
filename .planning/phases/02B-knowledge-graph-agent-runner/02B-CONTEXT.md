# Phase 2b: Knowledge Graph + Agent Runner - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the reasoning layer on top of Phase 2a's retrieval foundation:

- **Zero-LLM Wikilink Extraction**: Deterministic regex-based extraction of `[[bracket]]` wikilinks and typed edges from YAML frontmatter on every page write. No LLM calls. Populates `links` table.
- **Knowledge Graph**: Typed link graph queryable via recursive CTEs. B-tree indexes on `links.src_page_id` and `links.dst_entity_id`. Entity deduplication with canonical slugs + aliases. `brain.graph.traverse` MCP/REST tool activated (currently a stub).
- **22-Tool ReAct Agent**: In-process ReAct loop (thought → action → observation) with brain-first system prompt. All 22 tools operational. `skill_run` wired as stub (skills runtime in Phase 3). `jobs.submit` submits to APScheduler.
- **Conversation Persistence**: All agent invocations stored in `conversations`/`messages` tables. Tool traces in separate store referenced by message_id.
- **Golden Query Eval Suite**: Fixture corpus in `server/tests/fixtures/`. Phase 3 gate: Precision@5 ≥ 0.7 AND MRR ≥ 0.6.

**Not in this phase:** Skills runtime (Phase 3), ingestion skills (Phase 3), entity enrichment (Phase 3), web search (Phase 5), projects/workspaces (Phase 5). Prose relationship extraction from page body (deferred beyond Phase 2b).

</domain>

<decisions>
## Implementation Decisions

### Wikilink Extraction Scope

- **D-01:** Extract all explicit `[[...]]` wikilinks from page body with full syntax support:
  - `[[Target]]` — simple link
  - `[[Target|Alias]]` — store `anchor_text="Alias"`
  - `[[Target#Heading]]` — store `fragment="Heading"`
  - `[[Target#Heading|Alias]]` — store both fragment + anchor_text
  - Normalization: preserve folder paths (`shared/Topic`), normalize whitespace, resolve target to canonical slug via existing "shortest-unique-path" rules (Phase 1c).
  - Default `edge_type = "wikilink"`, `confidence = 1.0`.
- **D-02:** Typed edges extracted **from YAML frontmatter only** (not prose). Two supported forms:
  - **Mapped keys** (simple): `employer: [[Acme Corp]]`, `manager: [[Durga Dasari]]`, `investments: [[[Startup A]], [[Startup B]]]` — edge_type inferred from key name via a mapping table.
  - **Explicit `edges:` list**: `edges: [{target: "[[Acme Corp]]", type: "works_at"}]` — fully explicit typed edges.
  - `confidence = 1.0` for frontmatter edges (user-authored).
- **D-03:** Prose relationship parsing (e.g., "X works at Y", "X invested in Y" from body text) is **NOT implemented in Phase 2b**.
- **D-04:** Unresolved wikilinks (target cannot be matched to existing slug): `target_slug = null`, `unresolved = true`, `target_text` stored (raw link text). No auto-stub entity creation. Extraction is **side-effect-free** — no page creation on write path. Resolution may succeed later if the page is created. Phase 4 Dream audits unresolved links.

### ReAct Loop Limits + Failure Behavior

- **D-05:** Max **10 ReAct iterations** (thought → action → observation cycles). On reaching limit: return best available partial answer with `status: "max_iterations_reached"`.
- **D-06:** Empty local brain behavior:
  1. Call `brain.search` (hybrid retrieval from Phase 2a)
  2. If empty → call `brain.graph.traverse`
  3. If still empty → return structured `{"status": "no_local_knowledge", "message": "No local knowledge found for [query]. You can add relevant pages or ask to use external sources."}`
  4. **NEVER** auto-invoke external APIs without explicit user request.
- **D-07:** Tool error handling:
  - Classify errors: retryable (timeout, transient DB) vs. non-retryable (auth, validation, schema).
  - On retryable: retry once (same args).
  - If still failing (or non-retryable): record failure in observation, skip if non-critical, abort if critical.
  - **Non-critical tools** (skip on failure): `brain.graph.traverse`, query expansion, enrichment.
  - **Critical tools** (abort on failure): `brain.search` when no fallback; page read/write when required by request; auth/integrity failures.
  - Return status: `"success"` | `"success_with_warnings"` | `"tool_error"`. Include `warnings[]` with tool failure details when continuing.

### Conversation Persistence

- **D-08:** ALL agent invocations (MCP `brain.query` tool + `POST /api/v1/query` REST) create or append to a conversation record. No parity gap between transports.
- **D-09:** Session handling: if `session_id` provided → append to existing conversation. If not → create new single-turn conversation (auto-generated UUID). CLI: optional `--session-id` flag.
- **D-10:** Do NOT store in conversations: background jobs, ingestion/indexing operations, internal tool-to-tool calls (agent calling brain.search internally is not a new conversation turn).
- **D-11:** `messages` table stores: user message + final assistant response only. **Not** intermediate ReAct thought/action/observation pairs.
- **D-12:** Tool traces (thought/action/observation pairs) stored in a separate `tool_traces` table (or JSONB column on messages), referenced by `message_id`. Keeps messages table clean; preserves full trace for debugging and Phase 4 memory extraction.

### Golden Eval Corpus Initialization

- **D-13:** Fixture corpus checked into repo:
  - `server/tests/fixtures/sample_vault/` — 10–20 markdown pages (persons, companies, concepts, ideas, meetings, with typed frontmatter and wikilinks)
  - `server/tests/fixtures/golden_queries.yaml` — 20–30 queries with expected results (`top_slug`, `top_k` set, `expected_status`)
- **D-14:** CI loads fixture vault into test DB, runs indexing + embedding pipeline, executes golden queries, computes Precision@K, Recall@K, MRR, nDCG@K.
- **D-15:** **Phase 3 quality gate**: Precision@5 ≥ 0.7 AND MRR ≥ 0.6 on fixture corpus. Gate must pass in CI before Phase 3 work begins. Applies to hybrid search (`hybrid_v1`).
- **D-16:** Fixture data: deterministic, reproducible, no LLM-generated or runtime-generated queries. Admin-populated golden queries are optional post-deploy (not required for CI gate).

### Claude's Discretion

- `brain.graph.traverse` recursive CTE: implement with `WITH RECURSIVE` PostgreSQL syntax using `links` table. Edge type filters via WHERE clause. Depth limit parameter (default 3 hops). Cycle detection via visited set.
- Entity deduplication: `canonical_slug` + `aliases` array on `entities` table. Merge operation consolidates duplicate entity rows.
- `brain.query` MCP tool and `POST /api/v1/query` REST route are the agent entry points (distinct from `brain.search` which is pure retrieval without ReAct).
- `tool_traces` table or JSONB: planner decides based on query patterns. JSONB on messages row if traces are always accessed with their message; separate table if traces need independent querying.
- Agent system prompt: "brain-first" — query local knowledge before any external action. Included in every conversation.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product Requirements
- `docs/product_requirements_document_v26.05.md` — authoritative PRD (v26.05.1). Phase 2b directly implements: §17 (Agent runner, 22 tools), §18 (Knowledge graph + wikilink extraction), §19 (Conversation + memory model), §20 (Golden query eval). Requirements: GRAPH-01–06, AGENT-01–06, TEST-05.

### Planning Artifacts
- `.planning/REQUIREMENTS.md` — structured requirements for GRAPH-01–06, AGENT-01–06, TEST-05
- `.planning/ROADMAP.md` — Phase 2b goal, 5 success criteria, dependency on Phase 2a
- `.planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-CONTEXT.md` — Phase 2a decisions. Key inheritances: hybrid retrieval service (agent calls `brain.search` before any external tool); `session_with_rls()` discipline; `SearchResponse` shape; RRF/dedup pipeline.
- `.planning/phases/01d-mcp-server-rest-api-cli/01d-CONTEXT.md` — Phase 1d decisions. `brain.graph.*` stubs (D-05, D-06 there) are now real implementations in Phase 2b. `OperationContext`, transport-agnostic services pattern.

### Existing Models (inherit, don't rewrite)
- `server/app/models/link.py` — `Link` model (if exists) or create in Phase 2b. Fields: src_page_id, dst_entity_id/target_slug, edge_type, anchor_text, fragment, unresolved, confidence, target_text.
- `server/app/models/entity.py` — `Entity` model with canonical_slug + aliases.
- `server/app/models/conversation.py` — `Conversation` model (mcp_mode, web_search_enabled). `Message` model.
- `server/app/models/golden_eval.py` — `GoldenQuerySuite`, `GoldenQuery`, `GoldenQueryRun` models.
- `server/app/mcp/tools/graph.py` — current stub registered as `brain.graph.traverse`. Phase 2b replaces with real implementation.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server/app/vault/parser.py` — frontmatter parser (Phase 1c). Phase 2b reads frontmatter for typed edge extraction.
- `server/app/vault/paths.py` — wikilink resolution (`shortest-unique-path`). Phase 2b calls this to resolve `[[Target]]` to canonical slug.
- `server/app/services/pages.py` — `brain.put` / `brain.get` write path. Wikilink extraction hooks into the page write path here (or via watchdog, after-write trigger).
- `server/app/mcp/tools/graph.py` — stub registered with MCP. Phase 2b replaces stub body with real implementation. Do NOT re-register; replace body only.
- `server/app/mcp/tools/brain.py` — `brain.search`, `brain.get`, `brain.backlinks` already real. Phase 2b adds `brain.query` (agent entry point, distinct from brain.search).
- `server/app/scheduler/` — APScheduler job pattern. Wikilink extraction may be sync (inline on write) or async (job). Prefer inline on write path for link table freshness — it's deterministic and fast.

### Established Patterns
- `session_with_rls()` + `SET app.current_user_id` — mandatory for all DB ops in graph and agent paths.
- Services are transport-agnostic: `OperationContext` in, domain objects out.
- MCP stubs use `_AVAILABLE_IN_PHASE = "2b"` pattern (in `graph.py`, `entity.py`). Phase 2b activates these.
- Error envelope: `{"error": {"code": ..., "message": ..., "details?": ...}}` — agent responses follow same format.

### Integration Points
- `server/app/services/pages.py` — wikilink extractor called here after page content is parsed (on write path, before returning). Or as a post-write hook.
- `server/app/mcp/tools/graph.py` — replace stub with real `brain.graph.traverse` implementation.
- `server/app/main.py` — register `POST /api/v1/query` (agent route) and conversation/message CRUD routes.
- `server/tests/fixtures/` — new directory for sample_vault/ and golden_queries.yaml.

</code_context>

<specifics>
## Specific Ideas

- Wikilink extraction runs synchronously on page write (inline in `pages.py` after content parse). Fast because it's regex-only, zero I/O for pattern matching. DB write for link rows is the only I/O.
- `golden_queries.yaml` format: list of `{id, query, expected_top_slug, expected_top_k_slugs, notes}`. Planner designs exact schema.
- `brain.query` (agent entry point) vs `brain.search` (pure retrieval): `brain.query` invokes the ReAct loop; `brain.search` is just retrieval with no reasoning. Both MCP tools + REST endpoints.
- Conversation table: `mcp_mode` field values `disable`/`auto`/`manual`; `web_search_enabled` boolean — both from AGENT-05.
- `tool_traces` reference: whether table or JSONB column, must be query-able for Phase 4 memory extraction (which reads traces to extract memories from multi-tool agent sessions).

</specifics>

<deferred>
## Deferred Ideas

- Prose relationship parsing ("X works at Y" from body text) — deferred beyond Phase 2b. May be added as an optional enrichment step in Phase 3 or later.
- Admin-populated golden queries (post-deploy, production vault) — not required for Phase 2b CI gate; optional future enhancement.

</deferred>

---

*Phase: 2b — Knowledge Graph + Agent Runner*
*Context gathered: 2026-05-15*
