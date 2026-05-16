# Phase 2b: Knowledge Graph + Agent Runner - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-15
**Phase:** 2b — Knowledge Graph + Agent Runner
**Areas discussed:** Wikilink extraction scope, ReAct loop limits & failure behavior, Conversation persistence scope, Golden eval corpus initialization

---

## Wikilink Extraction Scope

| Option | Description | Selected |
|--------|-------------|----------|
| [[bracket]] syntax only | Explicit wikilinks only. Deterministic, no false positives. | |
| [[brackets]] + relationship verb patterns | Also scan prose for "works at", "invested in". More links but false-positive risk. | |
| [[brackets]] + frontmatter entity fields | Brackets + typed edges from YAML frontmatter. Structured and deterministic. | ✓ (via freeform) |

**User's choice (freeform, very detailed):**
> Extract all [[...]] wikilinks from body (Target, Target|Alias, Target#Heading, Target#Heading|Alias forms). Extract typed edges ONLY from YAML frontmatter — via mapped keys (employer, manager, investments) OR explicit `edges:` list with edge_type. Do NOT extract from prose. Unresolved targets: target_slug=null, unresolved=true, store target_text, no auto-stub. Extraction is side-effect-free.

**Notes:** User specified full normalization rules: preserve folder paths (shared/Topic), normalize whitespace, resolve to canonical slug using Phase 1c's shortest-unique-path rules.

| Option | Description | Selected |
|--------|-------------|----------|
| Record as unresolved, no auto-stub | Link row with target_slug=null + unresolved=true. Phase 4 audits. | ✓ (via freeform) |
| Auto-create stub entity page | Minimal stub created on first encounter. More graph data immediately. | |

**User's choice (freeform):** Record as unresolved, no auto-stub. target_text stored for future resolution. Extraction must be side-effect-free.

---

## ReAct Loop Limits & Failure Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| 10 iterations | Industry standard. Enough for complex multi-hop, prevents runaway loops. | ✓ (via freeform) |
| 5 iterations | Aggressive limit — good for latency, may cut off multi-hop reasoning. | |
| 15 iterations | More headroom for deep research. Higher max latency. | |

**User's choice (freeform):** Max 10 iterations. Hard stop. On reaching limit: return best available partial answer with "max_iterations_reached" flag.

| Option | Description | Selected |
|--------|-------------|----------|
| Try graph traversal, then admit no local knowledge | brain.search → graph.traverse → no_local_knowledge structured response. | ✓ (via freeform) |
| Proceed to external tools automatically | Auto-invoke web search on empty. Violates brain-first constraint. | |
| Return empty immediately | Simplest but wastes 21 other tools. | |

**User's choice (freeform):** brain.search → graph.traverse → structured {status: "no_local_knowledge", message: ...}. Never auto-call external APIs. Provide helpful next steps.

| Option | Description | Selected |
|--------|-------------|----------|
| Retry once, then skip tool and continue | Retry retryable errors once; skip non-critical; abort critical. | ✓ (via freeform) |
| Abort the loop on any tool failure | Any error terminates loop. Unhelpful when non-critical tool fails. | |
| You decide | Standard ReAct error recovery. | |

**User's choice (freeform):** Classify errors retryable vs non-retryable. Retry once for retryable. Skip non-critical (graph.traverse, query expansion, enrichment). Abort for critical (brain.search, required read/write, auth/integrity). Return success/success_with_warnings/tool_error status with warnings[].

---

## Conversation Persistence Scope

| Option | Description | Selected |
|--------|-------------|----------|
| All agent invocations via MCP + REST | Every agent call creates/extends conversation. Consistent. | ✓ (via freeform) |
| Only explicit session-scoped calls | Only when session_id provided. Misses single-turn queries for Phase 4. | |
| MCP only, not REST | REST stateless. Parity gap between transports. | |

**User's choice (freeform):** ALL agent invocations (MCP + REST). session_id appends; no session_id creates new. CLI: optional --session-id. Do NOT store: background jobs, ingestion, internal tool-to-tool calls.

| Option | Description | Selected |
|--------|-------------|----------|
| Final response + tool trace reference | messages table clean; traces in tool_traces table/JSONB by message_id. | ✓ (via freeform) |
| Full ReAct trace inline in messages | Each thought/action/observation is a row. Complete but 10x table inflation. | |
| Final response only | Simplest; loses debugging visibility. | |

**User's choice (freeform):** messages = user message + final response only. Tool traces in separate tool_traces table or JSONB column, referenced by message_id.

---

## Golden Eval Corpus Initialization

| Option | Description | Selected |
|--------|-------------|----------|
| Fixture corpus checked into repo | server/tests/fixtures/ — 10-20 pages + 20-30 golden queries. Zero dependency on user data. | ✓ (via freeform) |
| Admin-populated post-deploy | golden_queries starts empty. Flexible but Phase 2b acceptance test can't run. | |
| Auto-generated from first N pages | Template-based generation on boot. Eliminates fixtures but quality varies. | |

**User's choice (freeform):** server/tests/fixtures/sample_vault/ (10-20 markdown pages) + server/tests/fixtures/golden_queries.yaml (20-30 queries). CI loads fixture vault, runs pipeline, evaluates. Deterministic and reproducible.

| Option | Description | Selected |
|--------|-------------|----------|
| Precision@5 ≥ 0.7 AND MRR ≥ 0.6 | Realistic baseline. Achievable on fixture corpus. | ✓ (via freeform) |
| Precision@5 ≥ 0.8 AND nDCG@10 ≥ 0.7 | Higher bar — good aspirational but may be too strict for Phase 2 fixture data. | |
| You decide | Researcher/planner define per RAG benchmarking best practices. | |

**User's choice (freeform):** Phase 3 gate: Precision@5 ≥ 0.7 AND MRR ≥ 0.6 on fixture corpus. Must pass in CI before Phase 3 begins.

---

## Claude's Discretion

- `brain.graph.traverse` CTE implementation details (depth limit, cycle detection)
- Entity deduplication merge operation design
- `tool_traces` table vs JSONB column decision (based on query patterns)
- Agent system prompt wording (brain-first principle)

## Deferred Ideas

- Prose relationship parsing ("X works at Y" from body text) — deferred beyond Phase 2b
- Admin-populated golden queries for production vault — optional future enhancement
