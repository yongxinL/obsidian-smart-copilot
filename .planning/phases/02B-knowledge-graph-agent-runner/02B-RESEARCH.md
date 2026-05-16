# Phase 2b: Knowledge Graph + Agent Runner - Research

**Researched:** 2026-05-16
**Domain:** Typed wikilink extraction, PostgreSQL recursive CTEs, pure Python ReAct agent (LiteLLM tool_use), golden query eval
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Wikilink Extraction Scope**
- D-01: Extract all `[[...]]` wikilinks from page body: `[[Target]]`, `[[Target|Alias]]`, `[[Target#Heading]]`, `[[Target#Heading|Alias]]`. Default `edge_type = "wikilink"`, `confidence = 1.0`.
- D-02: Typed edges extracted from YAML frontmatter only (not prose). Mapped keys (`employer: [[Acme Corp]]`) and explicit `edges:` list (`edges: [{target: "[[Acme Corp]]", type: "works_at"}]`).
- D-03: Prose relationship parsing NOT implemented in Phase 2b.
- D-04: Unresolved wikilinks: `target_slug = null`, `unresolved = true`, `target_text` stored. No auto-stub entity creation. Extraction is side-effect-free on the write path.

**ReAct Loop Limits + Failure Behavior**
- D-05: Max 10 ReAct iterations. On reaching limit: return best available partial answer with `status: "max_iterations_reached"`.
- D-06: Empty local brain behavior: `brain.search` → `brain.graph.traverse` → `{"status": "no_local_knowledge"}`. NEVER auto-invoke external APIs.
- D-07: Error classification: retryable (Timeout, transient DB) vs. non-retryable (auth, validation, schema). Non-critical tools (skip on failure): `brain.graph.traverse`, `query.expand`, `entity.enrich`. Critical tools (abort on failure): `brain.search` when no fallback, page read/write when required, auth/integrity failures.

**Conversation Persistence**
- D-08: ALL agent invocations (MCP `brain.query` + `POST /api/v1/query`) create or append conversation records. No parity gap.
- D-09: Session handling: `session_id` provided → append to existing. Not provided → create new single-turn conversation (auto UUID). CLI: optional `--session-id` flag.
- D-10: Do NOT store background jobs, ingestion operations, or internal tool-to-tool calls in conversations.
- D-11: `messages` table stores user message + final assistant response only. NOT intermediate ReAct thought/action/observation pairs.
- D-12: Tool traces stored in separate `tool_traces` table (or JSONB on messages), referenced by `message_id`.

**Golden Eval Corpus Initialization**
- D-13: Fixture corpus: `server/tests/fixtures/sample_vault/` (10–20 markdown pages) + `server/tests/fixtures/golden_queries.yaml` (20–30 queries).
- D-14: CI loads fixture vault into test DB, runs indexing + embedding pipeline, executes golden queries, computes Precision@K, Recall@K, MRR, nDCG@K.
- D-15: Phase 3 quality gate: Precision@5 ≥ 0.7 AND MRR ≥ 0.6 on fixture corpus. Gate must pass in CI before Phase 3 work begins. Applies to hybrid search (`hybrid_v1`).
- D-16: Fixture data: deterministic, reproducible, no LLM-generated queries.

### Claude's Discretion

- `brain.graph.traverse` recursive CTE: `WITH RECURSIVE` PostgreSQL syntax using `links` table. Edge type filters via WHERE clause. Depth limit parameter (default 3 hops). Cycle detection via visited set.
- Entity deduplication: `canonical_slug` + `aliases` array on `entities` table. Merge operation consolidates duplicate entity rows.
- `brain.query` MCP tool and `POST /api/v1/query` REST route are agent entry points.
- `tool_traces` table or JSONB: planner decides based on query patterns.
- Agent system prompt: "brain-first" — query local knowledge before any external action.

### Deferred Ideas (OUT OF SCOPE)

- Prose relationship parsing ("X works at Y" from body text) — deferred beyond Phase 2b.
- Admin-populated golden queries (post-deploy, production vault) — not required for Phase 2b CI gate.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GRAPH-01 | Zero-LLM typed wikilink extraction on every page write | Deterministic regex `_WIKILINK_RE` already exists in `vault/parser.py`; extend `extract_wikilinks()` to handle `Alias`, `#Heading`, and typed frontmatter keys |
| GRAPH-02 | Extracted link types: wikilink, bare_slug, inferred; target entity kinds: person, company, concept, idea | `entity_kind_enum` already has the correct values; `links_source_kind_enum` has `wikilink/enrichment/inferred` — matches. `link_type` (String 64) holds `works_at/invested_in/wikilink/etc.` |
| GRAPH-03 | Wikilink graph via recursive CTEs; B-tree index on `links.src_page_id` and `links.dst_entity_id` | B-tree indexes `links_src_page_id_idx` and `links_dst_entity_id_idx` already created in migration 0001. PostgreSQL 16 `WITH RECURSIVE … CYCLE` clause available |
| GRAPH-04 | Entity deduplication with canonical slug + aliases; entity merge | `Entity.aliases ARRAY(Text)` exists; merge service needed |
| GRAPH-05 | Timeline event extraction from page timeline section | `timeline_events` table exists; `TimelineEvent` model defined. Service to parse timeline entries needed. |
| GRAPH-06 | `brain.graph.traverse` MCP/REST tool | Currently a stub in `mcp/tools/graph.py`. Phase 2b replaces stub body with recursive CTE implementation |
| AGENT-01 | 22-tool in-process ReAct loop with brain-first system prompt | `run_react_loop()` pattern fully documented in AI-SPEC; uses `litellm.acompletion()` (Phase 2a); no new framework dependency |
| AGENT-02 | Agent MUST query local brain before any external API call | Enforced by system prompt + code-level `brain_first_violation` guard in `_dispatch_tool` |
| AGENT-03 | Agent tool surface includes all 22 tools from PRD §17 | 22 tools mapped in AI-SPEC §3; `TOOL_REGISTRY` + `TOOL_SPECS` pattern |
| AGENT-04 | `skill_run` tool stub present; `jobs.submit` tool submits to APScheduler | `jobs.submit` currently a Phase 7 stub; Phase 2b wires a partial APScheduler path for `brain.query`-triggered jobs |
| AGENT-05 | Conversations table with `mcp_mode`, `web_search_enabled`; messages with citations, token usage, model tracking | `conversations` and `messages` tables exist — but: (a) `mcp_mode` enum values mismatch (see Schema Gaps), (b) `messages` table lacks `token_usage` and `model` columns |
| AGENT-06 | Golden query eval suite: tables seeded with fixture corpus; metrics computed | `GoldenQuerySuite`, `GoldenQuery`, `GoldenQueryRun` models exist but `GoldenQuery` lacks `expected_top_slug`, `expected_status`, `expected_tool_first`, `notes` fields |
| TEST-05 | Golden query eval suite for retrieval regression: Precision@K, Recall@K, MRR, nDCG@K, p95 latency | `scripts/eval_agent.py` runner; `server/tests/fixtures/` directory; metrics computed in Python from DB state |

</phase_requirements>

---

## Summary

Phase 2b builds the reasoning layer on top of Phase 2a's retrieval foundation. Three distinct subsystems must be implemented: (1) the zero-LLM wikilink extractor that runs synchronously on every page write and populates the `links` table; (2) the `brain.graph.traverse` recursive CTE replacing the current stub; and (3) the 22-tool in-process ReAct agent (`run_react_loop()`) with conversation persistence and Phoenix tracing.

The foundation is extensive but requires targeted schema surgery before any service code is written. The `links` table lacks `anchor_text`, `fragment`, `unresolved`, and `target_text` columns required by D-01/D-04. The `messages` table lacks `token_usage` and `model` columns for AGENT-05. The `mcp_mode` enum stored as `disabled/client/server` but AGENT-05 requires `disable/auto/manual`. The `GoldenQuery` model lacks several eval fields (`expected_top_slug`, `expected_status`, `notes`, etc.). All four gaps require an Alembic migration (0006 or continuation of the Phase 2a migration) before any implementation begins.

The wikilink extraction subsystem is intentionally narrow: regex-only, zero I/O for pattern matching, inline on the write path in `services/pages.py`. The graph traversal subsystem is PostgreSQL-native (WITH RECURSIVE + CYCLE clause, available in PostgreSQL 16). The agent subsystem reuses the LiteLLM `acompletion()` infrastructure from Phase 2a — no new top-level dependency. Phoenix tracing requires three PyPI packages (`openinference-instrumentation-litellm`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp`) that are legitimate Python packages from Arize AI's OpenInference project but were NOT confirmed against official documentation in this session — tagged accordingly.

**Primary recommendation:** Wave 0 = schema migration + Wave 0 test stubs. Wave 1 = wikilink extractor + graph traversal. Wave 2 = ReAct agent core. Wave 3 = conversation persistence + `brain.query` entry points. Wave 4 = golden eval suite + Phase 3 gate verification.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Wikilink extraction (regex) | API / Backend (`services/graph.py`) | — | Pure transformation, zero I/O for pattern match; called from write path |
| Typed edge frontmatter parsing | API / Backend (`services/graph.py`) | — | Reads `ParsedPage.frontmatter`; no external call |
| Link DB upsert | Database / Storage (`links` table) | API Backend (write path hook) | Persistence layer; RLS scoped per user |
| Entity deduplication + merge | API / Backend (`services/entity.py`) | Database / Storage | Merge reads `entities`, writes canonical_slug + aliases |
| Recursive CTE graph traversal | Database / Storage (PostgreSQL `WITH RECURSIVE`) | API Backend (query service) | CTE executes inside PostgreSQL; only result rows cross the wire |
| ReAct loop orchestration | API / Backend (`agent/react_loop.py`) | — | In-process, async, bounded; never exposed to frontend |
| Tool dispatch (22 tools) | API / Backend (`agent/tools/`) | — | Thin wrappers calling existing `services/` layer |
| Conversation persistence | Database / Storage (`conversations`, `messages`) | API Backend (`services/agent_service.py`) | Persistent session state; RLS per user |
| Tool traces storage | Database / Storage (`messages.tool_calls` JSONB) | — | Accessed with message; JSONB column preferred over separate table |
| Golden eval runner | API / Backend (`scripts/eval_agent.py`) | Database / Storage | Reads fixture DB, computes Python metrics, writes `golden_query_runs` |
| Agent tracing (Phoenix) | API / Backend (`app/observability/agent_spans.py`) | — | OpenTelemetry spans emitted in-process; Phoenix receives via OTLP |

---

## Standard Stack

### Core (all existing from Phase 1x + 2a)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `litellm` | ≥1.40,<2 (Phase 2a pin) | `acompletion()` for ReAct loop LLM calls; exception types for error classification | Already in requirements; Phase 2a router established |
| `pydantic` v2 | ≥2 (Phase 1a pin) | `AgentResponse`, `ToolTrace`, per-tool arg models | Already in stack; consistent validation pattern |
| `asyncpg` | ≥0.29 | Async DB access for all agent tool wrappers | Established; `session_with_rls()` pattern |
| `structlog` | ≥24 | Structured logging in `react_loop.py` and tool dispatchers | Already used everywhere |
| `python-frontmatter` | ≥1.1 | Read YAML frontmatter for typed edge extraction | Already in stack for Phase 1c parser |
| `apscheduler` | 3.11.2 (confirmed installed) | `AsyncIOScheduler` for `jobs.submit` tool in Phase 2b stub | Already running as supervisord process |

### New (observability for agent spans)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `opentelemetry-sdk` | 1.41.1 (PyPI latest) | OpenTelemetry tracer for custom agent spans | Required for Phoenix `agent.run` / `agent.iteration.{n}` / `tool.{name}` spans |
| `opentelemetry-exporter-otlp` | 1.41.1 (PyPI latest) | OTLP exporter to send spans to Phoenix at `localhost:6006` | Required to ship spans from the in-process agent to Phoenix |
| `openinference-instrumentation-litellm` | 0.1.33 (PyPI latest) | Auto-instruments every `acompletion()` call with `llm.completion` spans | Inherited from Phase 2a — verify it was added to requirements in 02A-04 |
| `pyyaml` | 6.0.3 (installed: 5.4.1) | Parse `golden_queries.yaml` fixture | Required for eval runner; already installed |

**Installation (new packages only, if not already added in Phase 2a):**
```bash
pip install \
  "opentelemetry-sdk>=1.41,<2" \
  "opentelemetry-exporter-otlp>=1.41,<2" \
  "openinference-instrumentation-litellm>=0.1.33" \
  "pyyaml>=6.0"
```

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled ReAct (LiteLLM) | LangGraph | LangGraph's checkpointing overhead unjustified for a 10-iteration bounded loop — adds complexity without benefit |
| Hand-rolled ReAct (LiteLLM) | Pydantic AI | Typed dispatch is useful but adds a new async runtime; ~200 LOC hand-rolled is simpler |
| PostgreSQL `WITH RECURSIVE` | Apache AGE / Neo4j | No external graph engine per project constraint (P3 principle) |
| JSONB on `messages.tool_calls` | Separate `tool_traces` table | JSONB preferred: traces always accessed with their message; reduces JOIN overhead for Phase 4 memory extraction |

---

## Package Legitimacy Audit

> slopcheck is npm-based and cannot evaluate Python packages (it checks npm registry). All packages verified on PyPI directly.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `opentelemetry-sdk` | PyPI | ~6 yrs (OpenTelemetry org) | Very high (standard CNCF project) | github.com/open-telemetry/opentelemetry-python | N/A (npm mismatch) | Approved [ASSUMED — PyPI verified, official CNCF project] |
| `opentelemetry-exporter-otlp` | PyPI | ~6 yrs | Very high | github.com/open-telemetry/opentelemetry-python | N/A (npm mismatch) | Approved [ASSUMED — PyPI verified, same org] |
| `openinference-instrumentation-litellm` | PyPI | ~2 yrs | Moderate | github.com/Arize-ai/openinference | N/A (npm mismatch) | Approved [ASSUMED — PyPI verified, Arize AI official] |
| `pyyaml` | PyPI | ~20 yrs | Extremely high | pyyaml.org | OK (npm confused it) | Approved — widely used YAML library |

**Packages removed due to slopcheck [SLOP] verdict:** none (slopcheck evaluates npm; all packages here are Python/PyPI)

**Note on slopcheck:** slopcheck checked npm and returned [SLOP] for the three OpenTelemetry packages because they do not exist on npm. These are Python packages on PyPI, confirmed at `pip index versions`. All three are from established OSS organizations (CNCF / Arize AI). The npm-based slopcheck result is a false positive due to ecosystem mismatch — not hallucination.

*All packages above are tagged `[ASSUMED]` because slopcheck could not confirm them via an authoritative source in the correct ecosystem. PyPI existence is confirmed but not equivalent to Context7/official-doc verification.*

---

## Architecture Patterns

### System Architecture Diagram

```
Page Write Path
───────────────
brain.put / watchdog
       │
       ▼
services/pages.py::write_page()
       │
       ├──► vault/parser.py::parse_vault_file()    ← returns ParsedPage
       │
       └──► services/graph.py::extract_and_upsert_links()  [NEW Phase 2b]
                   │
                   ├──► regex: _WIKILINK_RE on compiled_truth + timeline
                   ├──► frontmatter typed-edge parser
                   └──► asyncpg: UPSERT into links table (with entity resolution)

Agent Query Path
────────────────
MCP brain.query / POST /api/v1/query
       │
       ▼
services/agent_service.py::run_agent_query()
       │
       ├──► agent/react_loop.py::run_react_loop()
       │           │
       │           ├─[THINK]──► litellm.acompletion(tools=TOOL_SPECS, tool_choice="auto")
       │           │                   │
       │           │            ┌──────┴──────┐
       │           │          tool_calls    no tool_calls
       │           │             │              │
       │           ├─[ACT]────► _dispatch_tool()  └──[FINISH]──► AgentResponse
       │           │               │
       │           │          TOOL_REGISTRY lookup
       │           │               │
       │           │    ┌──────────┴──────────────┐
       │           │  brain.*              brain.graph.*
       │           │  tools                  tools
       │           │    │                     │
       │           │  services/              services/
       │           │  pages.py             graph.py::traverse()
       │           │    │                     │
       │           │    └─────────────────────┘
       │           │         asyncpg + RLS
       │           │
       │           └─[OBSERVE]──► append role:"tool" + observation to messages[]
       │
       ├──► persist_agent_invocation() → conversations + messages tables
       └──► agent_spans.py → Phoenix via OTLP

Graph Traversal Path
────────────────────
brain.graph.traverse(entity_slug, depth=3, edge_type_filter=[])
       │
       ▼
services/graph.py::traverse_graph()
       │
       └──► PostgreSQL WITH RECURSIVE CTE
                SELECT ... FROM links
                JOIN entities ON dst_entity_id = entities.id
                WHERE src_page_id = :start_page_id
                  AND (:edge_type IS NULL OR link_type = :edge_type)
                  AND NOT (id = ANY(visited))   ← cycle detection
                CYCLE id SET is_cycle USING path
                LIMIT depth:3 hops
```

### Recommended Project Structure (Phase 2b additions)

```
server/app/
├── agent/
│   ├── __init__.py
│   ├── react_loop.py          # run_react_loop() + _dispatch_tool() — ~200 lines
│   ├── models.py              # AgentResponse, ToolTrace Pydantic models
│   ├── prompts.py             # BRAIN_FIRST_SYSTEM_PROMPT constant
│   └── tools/
│       ├── __init__.py        # TOOL_REGISTRY dict + TOOL_SPECS list (22 entries)
│       ├── brain.py           # brain.search, brain.get, brain.put wrappers
│       ├── graph.py           # brain.graph.traverse wrapper
│       ├── entity.py          # entity.lookup, entity.enrich wrappers
│       └── jobs.py            # jobs.submit wrapper (partial APScheduler path)
├── services/
│   ├── graph.py               # NEW: extract_and_upsert_links(), traverse_graph(), merge_entity()
│   └── agent_service.py       # NEW: persist_agent_invocation(), get_or_create_conversation()
├── observability/
│   └── agent_spans.py         # NEW: agent_run_span, iteration_span, tool_span context managers
├── routes/
│   └── query.py               # NEW: POST /api/v1/query (agent entry point)
└── tests/
    ├── agent/                 # NEW: test_react_loop.py, test_tool_dispatch.py, test_agent_service.py
    ├── graph/                 # NEW: test_wikilink_extractor.py, test_graph_traversal.py
    └── eval/                  # NEW: test_golden_queries.py

server/
├── scripts/
│   └── eval_agent.py          # NEW: golden query eval runner
└── tests/
    └── fixtures/
        ├── sample_vault/      # NEW: 16 markdown fixture pages
        ├── golden_queries.yaml # NEW: 25 golden queries
        ├── expected_links.json # NEW: expected links table snapshot for extraction tests
        ├── system_prompt.sha256 # NEW: SHA-256 of BRAIN_FIRST_SYSTEM_PROMPT for drift guard
        └── eval_baseline.json  # NEW: baseline metrics (populated after first passing run)
```

### Pattern 1: Wikilink Extractor (Synchronous on Write Path)

**What:** After `parse_vault_file()` returns a `ParsedPage`, call `extract_and_upsert_links()` before returning from `write_page()`. The function (1) runs regex on body, (2) parses frontmatter typed edges, (3) resolves targets to canonical slugs via `vault/paths.py`, (4) upserts `links` rows.

**When to use:** Every page write (via `services/pages.py::write_page()` and `upsert_page()`).

**Example:**
```python
# Source: AI-SPEC §3 + CONTEXT.md D-01, D-02, D-04
# server/app/services/graph.py

import re
from app.vault.parser import _WIKILINK_RE   # reuse existing compiled regex

_FRONTMATTER_EDGE_KEYS = {
    "employer": "works_at",
    "manager": "reports_to",
    "investments": "invested_in",
    "founded": "founded",
    "investor": "invested_in",
    "partner": "partner_of",
}

_WIKILINK_FULL_RE = re.compile(
    r"\[\[(?P<target>[^\]#|]+)"    # target (required)
    r"(?:#(?P<fragment>[^\]|]+))?" # optional #Heading
    r"(?:\|(?P<alias>[^\]]+))?"    # optional |Alias
    r"\]\]"
)

async def extract_and_upsert_links(
    session: AsyncSession,
    ctx: OperationContext,
    page_id: uuid.UUID,
    parsed: ParsedPage,
    vault_id: uuid.UUID,
) -> int:
    """Extract wikilinks from body and frontmatter; upsert into links table.
    Returns count of links written. Zero I/O for pattern matching.
    """
    extracted = []

    # D-01: body wikilinks
    for m in _WIKILINK_FULL_RE.finditer(parsed.compiled_truth + "\n" + parsed.timeline):
        extracted.append({
            "target_text": m.group("target").strip(),
            "anchor_text": m.group("alias"),
            "fragment": m.group("fragment"),
            "edge_type": "wikilink",
            "confidence": 1.0,
            "source_kind": "wikilink",
        })

    # D-02: frontmatter typed edges
    for key, edge_type in _FRONTMATTER_EDGE_KEYS.items():
        val = parsed.frontmatter.get(key)
        if val is None:
            continue
        targets = val if isinstance(val, list) else [val]
        for t in targets:
            m = _WIKILINK_FULL_RE.search(str(t))
            if m:
                extracted.append({
                    "target_text": m.group("target").strip(),
                    "anchor_text": None,
                    "fragment": None,
                    "edge_type": edge_type,
                    "confidence": 1.0,
                    "source_kind": "wikilink",
                })

    # D-02: explicit edges: list
    for edge in parsed.frontmatter.get("edges", []):
        m = _WIKILINK_FULL_RE.search(str(edge.get("target", "")))
        if m:
            extracted.append({
                "target_text": m.group("target").strip(),
                "anchor_text": None,
                "fragment": None,
                "edge_type": edge.get("type", "wikilink"),
                "confidence": 1.0,
                "source_kind": "wikilink",
            })

    # Resolve targets + upsert (D-04: unresolved → target_slug=null, unresolved=true)
    written = await _upsert_links(session, ctx, page_id, vault_id, extracted)
    return written
```

### Pattern 2: Recursive CTE Graph Traversal

**What:** `WITH RECURSIVE` query traversing the `links` table from a starting entity. Uses PostgreSQL 16's `CYCLE` clause for cycle detection (no manual visited-array needed). Depth-limited via `WHERE depth < :max_depth`.

**When to use:** `brain.graph.traverse` tool call; also the fallback path in D-06 after empty `brain.search`.

**Example:**
```sql
-- Source: PostgreSQL 16 docs §7.8 + CONTEXT.md Claude's Discretion
-- B-tree indexes on links.src_page_id and links.dst_entity_id already in migration 0001

WITH RECURSIVE graph_traversal AS (
    -- Base: all links from starting page
    SELECT
        l.id, l.src_page_id, l.dst_entity_id, l.link_type, l.confidence,
        1 AS depth,
        ARRAY[l.src_page_id] AS visited_pages
    FROM links l
    JOIN pages p ON l.src_page_id = p.id
    WHERE p.slug = :start_slug
      AND p.vault_id = :vault_id
      AND p.deleted_at IS NULL
      AND (:edge_type_filter IS NULL OR l.link_type = :edge_type_filter)

    UNION ALL

    -- Recursive: follow links from destination entities back to pages
    SELECT
        l.id, l.src_page_id, l.dst_entity_id, l.link_type, l.confidence,
        g.depth + 1,
        g.visited_pages || l.src_page_id
    FROM links l
    JOIN entities e ON l.dst_entity_id = e.id
    JOIN graph_traversal g ON l.dst_entity_id = g.dst_entity_id
    WHERE g.depth < :max_depth
      AND NOT (l.src_page_id = ANY(g.visited_pages))  -- cycle guard
      AND (:edge_type_filter IS NULL OR l.link_type = :edge_type_filter)
)
CYCLE id SET is_cycle USING traversal_path  -- PostgreSQL 14+ CYCLE clause
SELECT DISTINCT
    p.slug, p.id, g.link_type, g.depth, g.confidence
FROM graph_traversal g
JOIN pages p ON g.src_page_id = p.id
WHERE NOT g.is_cycle
ORDER BY g.depth, g.confidence DESC;
```

**Python service wrapper:**
```python
# Source: AI-SPEC §3 + CONTEXT.md Claude's Discretion
async def traverse_graph(
    session: AsyncSession,
    ctx: OperationContext,
    *,
    start_slug: str,
    vault_id: uuid.UUID,
    edge_type_filter: str | None = None,
    max_depth: int = 3,
) -> list[GraphNode]:
    """Execute recursive CTE traversal. Returns list of reachable pages with edge metadata."""
    result = await session.execute(
        text(_TRAVERSE_CTE_SQL),
        {"start_slug": start_slug, "vault_id": str(vault_id),
         "edge_type_filter": edge_type_filter, "max_depth": max_depth}
    )
    return [GraphNode(slug=r.slug, page_id=r.id, link_type=r.link_type,
                      depth=r.depth, confidence=float(r.confidence))
            for r in result]
```

### Pattern 3: ReAct Loop Entry Point

**What:** Bounded `while iteration < MAX_ITERATIONS` loop calling `acompletion()` with all 22 tool specs. Tool dispatch in `_dispatch_tool()` with D-07 error classification. Full implementation documented in AI-SPEC §3.

**When to use:** Called from `services/agent_service.py::run_agent_query()` which is called by both the MCP `brain.query` tool and `POST /api/v1/query` route.

```python
# Source: AI-SPEC §3 (full implementation)
# Key invariants to preserve:
# 1. Increment iteration BEFORE acompletion() call (D-05)
# 2. Always include tool_call_id on role:"tool" observation messages
# 3. Use acompletion() not completion() (async context, uvicorn event loop already running)
# 4. TOOL_CHOICE = "auto" — never "required" (would force tool calls, risk loops)
```

### Anti-Patterns to Avoid

- **`asyncio.run()` inside a tool implementation:** FastAPI/uvicorn event loop is already running — use `await` throughout. Any `asyncio.run()` inside the ReAct loop or tools raises `RuntimeError: This event loop is already running`.
- **Streaming the ReAct loop:** Do NOT use `stream=True` with `acompletion()` in the ReAct loop. Tool calls require the complete response before dispatch. Stream only if adding a Phase 3 final-answer synthesis step.
- **Missing `tool_call_id` on observation:** Every `role:"tool"` message MUST carry `tool_call_id` matching `tc.id`. Missing it causes a 400 `BadRequestError` on the next `acompletion()` call from Anthropic and OpenAI providers.
- **Wikilink extraction as a background job (async via APScheduler):** The wikilink extractor is fast (regex only, one DB write batch). Running it as a background job would make the `links` table stale for seconds — enough for a `brain.query` immediately after a `brain.put` to miss the new links. Run it inline on the write path.
- **`dst_entity_id` NOT NULL FK for unresolved links:** The existing `links` table has `dst_entity_id` as `NOT NULL`. D-04 requires storing unresolved wikilinks where `target_slug = null`. The migration must either (a) make `dst_entity_id` nullable or (b) add `target_slug` (nullable) as an alternative — planner decides which strategy matches the query patterns for Phase 4 dead-link audit.
- **Fabricating answers when vault is empty:** The system prompt must use exact wording from BRAIN_FIRST_SYSTEM_PROMPT (AI-SPEC §4b.3). The SHA-256 hash of the constant must be captured in `tests/fixtures/system_prompt.sha256` for drift detection.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cycle detection in recursive graph | Manual visited-set tracking | PostgreSQL 16 `CYCLE id SET is_cycle USING path` | Built into the CTE; no Python post-processing needed |
| LLM exception classification | Custom HTTP status code parsing | `litellm.exceptions.AuthenticationError`, `Timeout`, `ServiceUnavailableError`, `RateLimitError` | LiteLLM maps all provider-specific errors to typed exceptions |
| Tool argument validation | `try/except KeyError` in tool wrappers | Pydantic `BaseModel` + `model_validate()` per tool | Consistent error shape; `ValidationError` surfaces as structured observation |
| YAML fixture loading | Custom YAML parser | `pyyaml` (`yaml.safe_load`) | Standard; already installed |
| Agent tracing | Custom log-parsing pipeline | OpenTelemetry `tracer.start_as_current_span()` + Phoenix OTLP | Inherited from Phase 2a; all `acompletion()` calls already auto-instrumented |
| Retrieval metrics (P@K, MRR, nDCG) | Implement from scratch | Pure Python ~30 LOC; no external library needed at this scale | Standard formulas over small fixtures; no `ranx` or `beir` dependency needed |

**Key insight:** The LiteLLM exception hierarchy is the most important "don't hand-roll" in this phase. The D-07 retryable/non-retryable classification is only safe when using LiteLLM's typed exceptions — catching raw HTTP exceptions or `Exception` base class loses the retry semantics.

---

## Schema Gaps (Critical — Require Alembic Migration 0006)

Four schema gaps between the existing Phase 1a migration and Phase 2b requirements. All must be addressed in a single migration before any service code:

### Gap 1: `links` table missing wikilink-specific columns

**Current columns:** `id, src_page_id, dst_entity_id (NOT NULL), link_type, confidence, source_kind, created_at, updated_at`

**Required additions (D-01, D-04):**
- `anchor_text` — TEXT, nullable (for `[[Target|Alias]]`)
- `fragment` — TEXT, nullable (for `[[Target#Heading]]`)
- `target_text` — TEXT, nullable (raw link text before resolution)
- `target_slug` — TEXT, nullable (resolved canonical slug, nullable until resolved)
- `unresolved` — BOOLEAN, NOT NULL, default FALSE (D-04)

**Constraint change:** `dst_entity_id` must be made NULLABLE to support unresolved links (D-04). OR the planner may choose to keep `dst_entity_id NOT NULL` and use `target_slug` / `unresolved` as an alternative path — both approaches are viable; the migration must be consistent with whichever the service uses.

### Gap 2: `mcp_mode` enum values mismatch

**Current DB enum:** `disabled`, `client`, `server` (migration 0001)
**AGENT-05 requires:** `disable`, `auto`, `manual`

**Fix:** ALTER TYPE `conversations_mcp_mode_enum` ADD VALUE for new values; drop old values (PostgreSQL enum drops require workaround — rename + recreate pattern). Update `conversation.py` model enum definition.

### Gap 3: `messages` table missing token/model columns

**Current columns:** `id, conversation_id, role, content, citations (JSONB), tool_calls (JSONB), created_at`

**Required additions (AGENT-05):**
- `token_usage` — JSONB, nullable (input/output token counts from LLM response)
- `model` — TEXT, nullable (model used for this response, e.g., `anthropic/claude-sonnet-4-6`)

### Gap 4: `GoldenQuery` model missing eval fields

**Current columns:** `id, suite_id, query, expected_slugs (ARRAY), tags (ARRAY), created_at, updated_at`

**Required additions (AGENT-06, TEST-05, AI-SPEC §5):**
- `expected_top_slug` — TEXT, nullable
- `expected_status` — TEXT, nullable (`success`, `no_local_knowledge`, `tool_error`)
- `expected_tool_first` — TEXT, nullable (`brain.search`)
- `expected_edge_type` — TEXT, nullable (for typed-edge graph queries)
- `notes` — TEXT, nullable

---

## Common Pitfalls

### Pitfall 1: `dst_entity_id` NOT NULL blocks unresolved wikilink storage

**What goes wrong:** The existing `links` table has `dst_entity_id UUID NOT NULL` with an FK to `entities`. Writing an unresolved wikilink (D-04 requires `target_slug = null`) fails with a NOT NULL constraint violation.

**Why it happens:** Phase 1a schema anticipated fully-resolved links only. D-04 adds the unresolved link requirement.

**How to avoid:** Migration 0006 must alter `dst_entity_id` to be nullable — OR — implement a "null entity" sentinel row per vault. The null-entity sentinel approach is fragile; nullable FK is cleaner.

**Warning signs:** Integration tests for unresolved links fail with `asyncpg.NotNullViolationError` before migration.

### Pitfall 2: Wikilink extractor runs on every write including no-op re-saves

**What goes wrong:** If the extractor deletes all links and re-inserts on every write, a page with 20 links re-saves 20 deletions + 20 inserts per minor edit. Worse: a content-identical re-save creates duplicate link entries if the upsert key is wrong.

**Why it happens:** Naive implementation: `DELETE FROM links WHERE src_page_id = ?` then re-insert.

**How to avoid:** Use `INSERT ... ON CONFLICT DO UPDATE` (upsert) on the natural key `(src_page_id, target_text, edge_type)`. Check `xxhash64(content)` first — if content unchanged, skip extraction entirely (reuse `content_hash` from `write_page()`).

**Warning signs:** Idempotence test (dimension 17 in AI-SPEC §5) fails — row count changes between runs.

### Pitfall 3: Missing `tool_call_id` on observation message aborts the loop

**What goes wrong:** The next `acompletion()` call receives a message history with a `role:"tool"` message missing `tool_call_id`. Anthropic and OpenAI APIs return 400 `BadRequestError`. This is classified as non-retryable (D-07) → loop aborts with `status: "tool_error"`.

**Why it happens:** Forgetting to carry `tc.id` from the assistant message's `tool_calls[i].id` to the observation dict.

**How to avoid:** Always build the observation message dict explicitly (see AI-SPEC §3 entry point pattern). Never pass the raw `ModelResponse` object to messages — reconstruct the dict.

**Warning signs:** `tool_error` status in tests when tool dispatch succeeds, `BadRequestError` in logs.

### Pitfall 4: Concurrent extraction on the same page (watchdog + MCP write race)

**What goes wrong:** The watchdog sees a file change and triggers extraction at the same time the MCP write path runs extraction. Two concurrent extractions on the same page create duplicate link rows.

**Why it happens:** Both code paths call `extract_and_upsert_links()` independently.

**How to avoid:** The watchdog path should check `content_hash` before extraction — if the hash in DB matches the file hash, skip. Additionally, use `INSERT ... ON CONFLICT DO UPDATE` (not INSERT + DELETE) so concurrent writes are idempotent.

**Warning signs:** `links` table row count is 2× expected; `links` idempotence test fails under concurrent writes.

### Pitfall 5: `mcp_mode` enum constraint blocks conversation creation

**What goes wrong:** Creating a `Conversation` with `mcp_mode = "auto"` fails with `invalid input value for enum conversations_mcp_mode_enum` because the DB enum only has `disabled/client/server` until the migration runs.

**Why it happens:** Migration 0006 hasn't run, or code deployed before migration.

**How to avoid:** Migration must run before any Phase 2b service code. Add a smoke test asserting the enum contains the new values.

**Warning signs:** `asyncpg.DataError: invalid input value for enum` on conversation creation.

### Pitfall 6: `WITH RECURSIVE` without CYCLE clause causes infinite loop on circular links

**What goes wrong:** If two pages link to each other, a recursive CTE without cycle detection runs forever (or until PostgreSQL hits max recursion limit and throws an error).

**Why it happens:** Developer writes the base + recursive case but forgets cycle detection.

**How to avoid:** Use PostgreSQL 16's `CYCLE id SET is_cycle USING path` clause — confirmed available (PostgreSQL 16 is the pinned version). Test with a fixture that has a circular link pair.

**Warning signs:** `ERROR: infinite recursion detected in rules for relation` from PostgreSQL.

---

## Code Examples

### Full wikilink regex with groups

```python
# Source: AI-SPEC §4 + CONTEXT.md D-01 + vault/parser.py pattern
_WIKILINK_FULL_RE = re.compile(
    r"\[\["
    r"(?P<target>[^\]#|]+)"          # required: target (no ] # |)
    r"(?:\#(?P<fragment>[^\]|]+))?"  # optional: #Heading
    r"(?:\|(?P<alias>[^\]]+))?"      # optional: |Display Alias
    r"\]\]"
)
# Handles: [[Target]], [[Target|Alias]], [[Target#Heading]], [[Target#Heading|Alias]]
# Does NOT handle nested brackets (intentional — Obsidian syntax does not nest)
```

### AgentResponse + ToolTrace Pydantic models

```python
# Source: AI-SPEC §4b.1 (verbatim — these are the locked models)
from typing import Any, Literal
from pydantic import BaseModel, Field

class ToolTrace(BaseModel):
    tool_call_id: str
    tool_name: str
    args: dict[str, Any]
    observation: dict[str, Any]
    retried: bool = False
    skipped: bool = False
    skip_reason: str | None = None

class AgentResponse(BaseModel):
    status: Literal[
        "success", "success_with_warnings", "tool_error",
        "max_iterations_reached", "no_local_knowledge",
    ]
    answer: str | None = None
    tool_traces: list[ToolTrace] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
```

### `golden_queries.yaml` schema (D-13 format)

```yaml
# Source: AI-SPEC §5 reference dataset + CONTEXT.md D-13
- id: q-001
  query: "where does John Smith work?"
  tags: [factual, person]
  expected_top_slug: john-smith-acme
  expected_top_k_slugs: [john-smith-acme, acme-corp]
  expected_status: success
  expected_tool_first: brain.search
  expected_min_citations: 1
  notes: "Basic entity lookup + citation. Vault has employer: [[Acme Corp]] in frontmatter."

- id: q-007
  query: "what is the latest funding round for Acme Corp?"
  tags: [empty-vault, transparency]
  expected_status: no_local_knowledge
  expected_top_k_slugs: []
  expected_tools: [brain.search, brain.graph.traverse]
  notes: "Vault has no funding info. Agent MUST NOT call web search."

- id: q-013
  query: "who works at Acme Corp?"
  tags: [graph, typed-edge, completeness]
  expected_top_slug: acme-corp
  expected_top_k_slugs: [john-smith-acme, jane-doe, kim-park]
  expected_status: success
  expected_edge_type: works_at
  notes: "Tests brain.graph.traverse + completeness across 3 typed edges."
```

### Conversation persistence (D-11, D-12)

```python
# Source: AI-SPEC §4 persist_agent_invocation() pattern
async def persist_agent_invocation(
    op_ctx: OperationContext,
    session_id: uuid.UUID | None,
    user_query: str,
    result: AgentResponse,
    model: str,
) -> uuid.UUID:
    """Write user + assistant messages to DB. Return message_id.
    D-11: only user + final assistant response. NOT intermediate ReAct steps.
    D-12: tool_calls JSONB on assistant message stores the tool_traces list.
    """
    async for session in session_with_rls(op_ctx):
        conv = await get_or_create_conversation(session, op_ctx, session_id)
        # User message
        user_msg = Message(conversation_id=conv.id, role="user", content=user_query,
                           citations=[], tool_calls=[])
        session.add(user_msg)
        await session.flush()
        # Assistant message (D-12: tool_traces in tool_calls JSONB)
        asst_msg = Message(
            conversation_id=conv.id, role="assistant",
            content=result.answer or "",
            citations=_extract_citations(result.tool_traces),
            tool_calls=[t.model_dump() for t in result.tool_traces],
            model=model,
            token_usage=_sum_token_usage(result.tool_traces),
        )
        session.add(asst_msg)
        await session.commit()
        return asst_msg.id
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual array-based cycle detection in recursive CTEs | `CYCLE id SET is_cycle USING path` clause | PostgreSQL 14 (2021) | Simpler code, DB-enforced cycle detection |
| Separate `tool_traces` table | JSONB column on `messages.tool_calls` | Design decision | Fewer JOINs for Phase 4 memory extraction; traces always fetched with their message |
| LangGraph / LlamaIndex for agents | Hand-rolled ReAct loop (~200 LOC) | Project decision | Full control over D-05/D-06/D-07 semantics; zero new framework dependency |
| `litellm.completion()` (sync) | `litellm.acompletion()` (async) | FastAPI/uvicorn context | `asyncio.run()` inside uvicorn raises `RuntimeError`; always use async variant |

**Deprecated/outdated:**
- `brain.graph.traverse` stub (`mcp/tools/graph.py`): the `_AVAILABLE_IN_PHASE = "2b"` stub is replaced in Phase 2b — do NOT re-register; replace the function body only (confirmed in CONTEXT.md code_context).
- `jobs.submit/status/cancel` stubs (`mcp/tools/jobs.py`): marked `_AVAILABLE_IN_PHASE = "7"`. Phase 2b wires only `jobs.submit` for APScheduler path from `brain.query`; the stub's phase annotation stays "7" but a partial implementation is needed.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `openinference-instrumentation-litellm` (0.1.33), `opentelemetry-sdk` (1.41.1), `opentelemetry-exporter-otlp` (1.41.1) are legitimate packages from Arize AI / OpenTelemetry CNCF projects | Package Legitimacy Audit | Low — PyPI confirmed, public GitHub orgs confirmed via WebSearch; slopcheck false-positived on npm |
| A2 | Phase 2a plans (02A-04) added `openinference-instrumentation-litellm` to `requirements.txt` for Phoenix tracing | Standard Stack | Medium — if 2a did NOT add it, Phase 2b must add it in its migration wave. Planner should grep `requirements.txt` for confirmation |
| A3 | `litellm.acompletion()` is already installed from Phase 2a execution (not just planned) | Standard Stack | Medium — litellm was NOT found when `python3 -c "import litellm"` was run (env may not have Phase 2a venv active); confirm `litellm` is in requirements.txt and installed in the Docker image |
| A4 | The `jobs.submit` stub in `mcp/tools/jobs.py` (marked Phase 7) is acceptable to partially implement in Phase 2b for APScheduler path | Don't Hand-Roll | Low — AGENT-04 explicitly says `jobs.submit` submits to APScheduler; the stub comment says "Phase 7" but the requirement is Phase 2b |
| A5 | The `messages.tool_calls JSONB` column is sufficient storage for `tool_traces` (JSONB on message, not separate table) | Architecture Patterns | Low — CONTEXT.md Claude's Discretion explicitly permits either; JSONB preferred based on access pattern |

---

## Open Questions

1. **`dst_entity_id` nullable vs. null sentinel entity**
   - What we know: D-04 requires unresolved links with `target_slug = null`. Current schema has `dst_entity_id NOT NULL`.
   - What's unclear: Does the planner prefer making `dst_entity_id` nullable in the migration (simpler, cleaner FK), or creating a sentinel `unresolved` entity per vault (avoids nullable FK but adds complexity)?
   - Recommendation: Make `dst_entity_id` nullable. Add a `CHECK` constraint that either `dst_entity_id IS NOT NULL` OR `unresolved = true` to ensure consistency.

2. **`mcp_mode` enum migration strategy**
   - What we know: PostgreSQL cannot drop enum values; only ADD new ones. The current values `disabled/client/server` must be removed and replaced with `disable/auto/manual`.
   - What's unclear: This requires the rename-and-recreate pattern: (1) add new enum type, (2) ALTER column to use new type with USING cast, (3) drop old enum.
   - Recommendation: Rename old enum to `conversations_mcp_mode_enum_old`, create new enum `conversations_mcp_mode_enum` with correct values, ALTER TABLE conversations ALTER COLUMN mcp_mode TYPE conversations_mcp_mode_enum USING 'disable'::conversations_mcp_mode_enum, then DROP TYPE old.

3. **Phoenix already running or needs setup in Phase 2b?**
   - What we know: AI-SPEC §5 says Phoenix inherited from Phase 2a. Phase 2a plan may have added Phoenix as a supervisord process.
   - What's unclear: If Phase 2a execution is not complete when Phase 2b planning starts, Phoenix may not be running.
   - Recommendation: Planner should check `02A-VALIDATION.md` for Phoenix setup status; if not yet running, add a Wave 0 task to configure Phoenix sidecar.

4. **`jobs.submit` in Phase 2b: full or stub?**
   - What we know: AGENT-04 requires `jobs.submit` tool to submit to APScheduler. Current `mcp/tools/jobs.py` stub returns `not_implemented (Phase 7)`.
   - What's unclear: Does Phase 2b need full `jobs.submit` (including the `Jobs` table write + APScheduler scheduling) or just a basic wrapper that enqueues a job kind?
   - Recommendation: Implement a minimal `jobs.submit` that writes a `Job` row with `status=pending` and hands it to APScheduler's `add_job()`. Full DAG orchestration (parent-child) remains Phase 7.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL 16 | Recursive CTE CYCLE clause, RLS | ✓ (Docker container) | 16.x (pinned in Phase 1a) | — |
| `apscheduler` | `jobs.submit` tool, embed worker | ✓ | 3.11.2 | — |
| `pydantic` | AgentResponse, ToolTrace, tool arg models | ✓ | 2.12.5 | — |
| `pyyaml` | `golden_queries.yaml` eval runner | ✓ (installed) | 5.4.1 (upgrade to 6.0.3 recommended) | — |
| `litellm` | `acompletion()` in ReAct loop | Not confirmed in dev env | Planned ≥1.40 (Phase 2a) | Phase 2a must install first |
| `opentelemetry-sdk` | Phoenix agent spans | Not confirmed | 1.41.1 (PyPI) | Skip tracing; flag in Wave 0 |
| `opentelemetry-exporter-otlp` | Phoenix OTLP export | Not confirmed | 1.41.1 (PyPI) | Skip tracing; flag in Wave 0 |
| `openinference-instrumentation-litellm` | LiteLLM auto-instrument | Not confirmed | 0.1.33 (PyPI) | Skip auto-instrument; flag in Wave 0 |
| Arize Phoenix (sidecar/supervisord) | Agent tracing | Assumed from Phase 2a | 0.x (Phase 2a) | Disable tracing; continue without |

**Missing dependencies with no fallback:**
- `litellm` — Phase 2b cannot function without it. Must be installed as part of Phase 2a execution or Wave 0 of Phase 2b.

**Missing dependencies with fallback:**
- OpenTelemetry + Phoenix — tracing can be disabled without breaking agent functionality. Add a `SMARTCOPILOT_TRACING_ENABLED` env var; skip span creation when false.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest` + `pytest-asyncio` (already established) |
| Config file | `server/pyproject.toml` (existing) |
| Quick run command | `pytest server/app/tests/agent/ server/app/tests/graph/ -x -q` |
| Full suite command | `pytest server/ -x -q` |
| Eval runner | `python server/scripts/eval_agent.py --fixture-vault server/tests/fixtures/sample_vault/ --golden-queries server/tests/fixtures/golden_queries.yaml --baseline server/tests/fixtures/eval_baseline.json` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GRAPH-01 | Wikilink extraction produces correct links rows | unit | `pytest server/app/tests/graph/test_wikilink_extractor.py -x` | ❌ Wave 0 |
| GRAPH-02 | All wikilink/typed-edge types extracted correctly | unit | `pytest server/app/tests/graph/test_wikilink_extractor.py -x -k types` | ❌ Wave 0 |
| GRAPH-03 | Recursive CTE traversal returns correct paths, cycle-safe | integration | `pytest server/app/tests/graph/test_graph_traversal.py -x` | ❌ Wave 0 |
| GRAPH-04 | Entity merge consolidates duplicates | integration | `pytest server/app/tests/graph/test_entity_merge.py -x` | ❌ Wave 0 |
| GRAPH-05 | Timeline event extraction populates `timeline_events` | integration | `pytest server/app/tests/graph/test_timeline_events.py -x` | ❌ Wave 0 |
| GRAPH-06 | `brain.graph.traverse` MCP tool returns typed traversal | integration | `pytest server/app/tests/graph/test_brain_graph_traverse.py -x` | ❌ Wave 0 |
| AGENT-01 | ReAct loop bounded at 10 iterations | unit | `pytest server/app/tests/agent/test_react_loop.py -x -k max_iterations` | ❌ Wave 0 |
| AGENT-02 | First tool call is always `brain.search` | unit | `pytest server/app/tests/agent/test_react_loop.py -x -k brain_first` | ❌ Wave 0 |
| AGENT-03 | All 22 tools registered and callable | unit | `pytest server/app/tests/agent/test_tool_registry.py -x` | ❌ Wave 0 |
| AGENT-04 | `jobs.submit` writes Job row + APScheduler enqueue | integration | `pytest server/app/tests/agent/test_jobs_tool.py -x` | ❌ Wave 0 |
| AGENT-05 | Conversation + messages created for every invocation (MCP + REST parity) | integration | `pytest server/app/tests/agent/test_conversation_persistence.py -x` | ❌ Wave 0 |
| AGENT-06 | Golden query suite tables seeded and queryable | integration | `pytest server/app/tests/eval/test_golden_suite_seed.py -x` | ❌ Wave 0 |
| TEST-05 | Precision@5 ≥ 0.7 AND MRR ≥ 0.6 on fixture corpus | e2e eval | `python server/scripts/eval_agent.py --exit-on-critical-fail` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest server/app/tests/agent/ server/app/tests/graph/ -x -q`
- **Per wave merge:** `pytest server/ -x -q`
- **Phase gate:** Full golden eval suite green (`scripts/eval_agent.py --exit-on-critical-fail`) before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `server/app/tests/graph/` directory + `__init__.py`
- [ ] `server/app/tests/graph/test_wikilink_extractor.py` — covers GRAPH-01, GRAPH-02 (dimensions 16, 17)
- [ ] `server/app/tests/graph/test_graph_traversal.py` — covers GRAPH-03, GRAPH-06
- [ ] `server/app/tests/graph/test_entity_merge.py` — covers GRAPH-04
- [ ] `server/app/tests/graph/test_timeline_events.py` — covers GRAPH-05
- [ ] `server/app/tests/agent/` directory + `__init__.py`
- [ ] `server/app/tests/agent/test_react_loop.py` — covers AGENT-01, AGENT-02 (dimensions 1–4, 9, 10, 11)
- [ ] `server/app/tests/agent/test_tool_registry.py` — covers AGENT-03
- [ ] `server/app/tests/agent/test_jobs_tool.py` — covers AGENT-04
- [ ] `server/app/tests/agent/test_conversation_persistence.py` — covers AGENT-05 (dimension 12)
- [ ] `server/app/tests/eval/` directory + `__init__.py`
- [ ] `server/app/tests/eval/test_golden_suite_seed.py` — covers AGENT-06 DB seeding
- [ ] `server/tests/fixtures/sample_vault/` — 16 markdown fixture pages (D-13, AI-SPEC §5)
- [ ] `server/tests/fixtures/golden_queries.yaml` — 25 golden queries (D-13, AI-SPEC §5)
- [ ] `server/tests/fixtures/expected_links.json` — expected links snapshot for extraction idempotence test
- [ ] `server/tests/fixtures/system_prompt.sha256` — SHA-256 of BRAIN_FIRST_SYSTEM_PROMPT
- [ ] `server/scripts/eval_agent.py` — eval runner (TEST-05)
- [ ] Alembic migration 0006 — links schema extension + mcp_mode enum fix + messages token/model + GoldenQuery fields

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | `session_with_rls()` + `OperationContext` enforced on every tool dispatch |
| V3 Session Management | yes | `session_id` UUID from caller; `conversations` table per-user RLS |
| V4 Access Control | yes | RLS on `links`, `entities`, `conversations`, `messages` tables (already enabled in migration 0001) |
| V5 Input Validation | yes | Pydantic arg models per tool; `query.strip()` non-empty check on `brain.query` |
| V6 Cryptography | no | No new crypto in Phase 2b; provider keys handled by Phase 1b Fernet |

### Known Threat Patterns for Phase 2b Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Prompt injection via wikilink target text | Tampering | Extract `target_text` verbatim; never execute or interpolate it as SQL or prompt. Store as TEXT, not as executable content |
| Vault cross-user data leak in graph traversal | Information Disclosure | `session_with_rls()` mandatory on every CTE query; `vault_id = :vault_id` in all graph queries |
| ReAct loop external API bypass | Tampering / Elevation | Brain-first gate in `_dispatch_tool()`; external tools rejected before `brain.search` called; zero-tolerance `agent_brain_first_violations_total` counter |
| Tool trace leaking provider API key | Information Disclosure | Provider keys must be scrubbed from all `ToolTrace.args` before persisting; inherit Phase 2a's `redaction.py` scrubber |
| Agent fabricating vault-absent facts | Integrity | System prompt + `no_local_knowledge` structured response; golden eval dimension 1 catches vault-gap hallucination |

---

## Sources

### Primary (HIGH confidence)

- Phase 2b `02B-CONTEXT.md` — locked decisions D-01 through D-16, canonical references, code context
- Phase 2b `02B-AI-SPEC.md` — full ReAct loop implementation, eval strategy, 21 evaluation dimensions, production monitoring
- Existing codebase: `server/app/models/` (link.py, entity.py, conversation.py, golden_eval.py), `server/alembic/versions/0001_initial_schema.py`, `server/app/vault/parser.py`, `server/app/mcp/tools/graph.py`
- PostgreSQL 16 documentation §7.8 (WITH RECURSIVE, CYCLE clause) — [https://www.postgresql.org/docs/current/queries-with.html](https://www.postgresql.org/docs/current/queries-with.html)

### Secondary (MEDIUM confidence)

- LiteLLM function calling docs — [https://docs.litellm.ai/docs/completion/function_call](https://docs.litellm.ai/docs/completion/function_call) [ASSUMED — not fetched directly]
- LiteLLM exception mapping — [https://docs.litellm.ai/docs/exception_mapping](https://docs.litellm.ai/docs/exception_mapping) [ASSUMED — referenced in AI-SPEC]
- Arize OpenInference GitHub — [https://github.com/Arize-ai/openinference](https://github.com/Arize-ai/openinference) — confirmed via WebSearch as official repository for `openinference-instrumentation-litellm`
- PyPI: `openinference-instrumentation-litellm` 0.1.33, `opentelemetry-sdk` 1.41.1, `opentelemetry-exporter-otlp` 1.41.1 — confirmed via `pip index versions`

### Tertiary (LOW confidence — training knowledge only)

- RRF metric formulas (Precision@K, Recall@K, MRR, nDCG@K) — standard IR formulas; no external library needed at this scale [ASSUMED]
- APScheduler `add_job()` for `jobs.submit` partial implementation [ASSUMED — based on existing `scheduler/run.py` pattern in codebase]

---

## Metadata

**Confidence breakdown:**
- Schema gaps: HIGH — verified by reading actual migration 0001 and comparing to CONTEXT.md decisions
- Standard stack (existing): HIGH — verified by reading `requirements.txt`, installed packages, actual code
- Standard stack (new packages): MEDIUM — PyPI confirmed, WebSearch confirmed official org; not verified via Context7
- Architecture patterns: HIGH — derived from AI-SPEC + CONTEXT.md locked decisions
- Pitfalls: HIGH (schema gaps 1-5) — verified by reading migration + model code; MEDIUM (race conditions) — reasoning-based

**Research date:** 2026-05-16
**Valid until:** 2026-06-15 (stable domain; LiteLLM updates frequently — re-verify exception class names if version changes)
