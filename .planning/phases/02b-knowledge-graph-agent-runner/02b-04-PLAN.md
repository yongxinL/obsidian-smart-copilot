---
phase: 02B
plan: 04
type: execute
wave: 2
depends_on: ["02B-03"]
files_modified:
  - server/app/services/graph.py
  - server/app/mcp/tools/graph.py
  - server/app/tests/graph/test_graph_traversal.py
  - server/app/tests/graph/test_brain_graph_traverse.py
autonomous: true
requirements: [GRAPH-03, GRAPH-06]
tags: [phase-2b, wave-2, knowledge-graph, recursive-cte, postgresql, mcp-tool]

must_haves:
  truths:
    - "brain.graph.traverse MCP tool returns real recursive-CTE traversal results (not the not_implemented stub)"
    - "traverse_graph uses PostgreSQL WITH RECURSIVE + CYCLE clause; no manual visited-array tracking required at Python level"
    - "Default max_depth = 3; user-supplied depth respected; query plan uses the B-tree indexes on links.src_page_id and links.dst_entity_id (GRAPH-03)"
    - "Edge-type filter via WHERE link_type = :edge_type_filter (parameter bound, never string-interpolated)"
    - "Cycle detection works: a fixture with john-smith-acme → acme-corp → durga-dasari → john-smith-acme returns each node at most once"
    - "RLS enforced: session_with_rls(ctx) used on every traversal; vault_id bound parameter prevents cross-vault leak (T-rls-01)"
  artifacts:
    - path: "server/app/services/graph.py"
      provides: "Extended with traverse_graph() recursive-CTE service function and GraphNode Pydantic return model"
      contains: "WITH RECURSIVE"
    - path: "server/app/mcp/tools/graph.py"
      provides: "Replaced brain.graph.traverse stub body with real implementation calling services/graph.py::traverse_graph"
      contains: "traverse_graph"
  key_links:
    - from: "server/app/mcp/tools/graph.py brain.graph.traverse"
      to: "server/app/services/graph.py traverse_graph"
      via: "async tool function calls service via session_with_rls(ctx)"
      pattern: "traverse_graph\\(session"
    - from: "server/app/services/graph.py traverse_graph"
      to: "links table B-tree indexes"
      via: "WITH RECURSIVE CTE binding vault_id + edge_type_filter as parameters"
      pattern: "WITH RECURSIVE"
---

<objective>
Replace the Phase 1d `brain.graph.traverse` not_implemented stub with a real recursive-CTE implementation backed by PostgreSQL 16's `WITH RECURSIVE ... CYCLE` clause. Add a `traverse_graph()` service function in `services/graph.py`. The MCP tool body changes from `return _stub()` to a real call into the service via session_with_rls.

Purpose: GRAPH-03 + GRAPH-06 — the graph traversal layer that the agent uses for "who works at X" / "what did Y invest in" patterns (per Phase ROADMAP and CONTEXT D-06 fallback path). Without this, the agent has no graph fallback when brain.search returns empty.

Output: A parameterised CTE that the agent and any MCP/REST caller can invoke; a registered MCP tool that returns structured graph nodes. Test fixtures from Plan 02B-02 + 02B-03 already contain a cyclic edge (john-smith-acme reports_to durga-dasari, durga-dasari manages john-smith-acme could produce a cycle when traversed) so the CYCLE clause is genuinely exercised.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/02B-knowledge-graph-agent-runner/02B-CONTEXT.md
@.planning/phases/02B-knowledge-graph-agent-runner/02B-RESEARCH.md
@.planning/phases/02B-knowledge-graph-agent-runner/02B-PATTERNS.md
@.planning/phases/02B-knowledge-graph-agent-runner/02B-03-SUMMARY.md
@server/app/services/graph.py
@server/app/mcp/tools/graph.py
@server/app/mcp/tools/brain.py
@server/app/services/vault_resolver.py
@server/app/dependencies.py

<interfaces>
PostgreSQL 16 recursive CTE pattern (RESEARCH §Pattern 2 lines 365-410):
- Base case: SELECT links rows WHERE src_page_id = (start page) AND vault_id = :vault_id AND deleted_at IS NULL
- Recursive case: JOIN entities ON l.dst_entity_id = e.id, JOIN graph_traversal g ON l.dst_entity_id = g.dst_entity_id, WHERE g.depth < :max_depth
- CYCLE id SET is_cycle USING traversal_path  ← PostgreSQL 14+ cycle clause; no manual visited-array
- Final SELECT joins pages and entities to return slug/name/edge_type/depth/confidence

Service function signature (RESEARCH §Pattern 2 lines 415-433):
```
async def traverse_graph(
    session: AsyncSession,
    ctx: OperationContext,
    *,
    start_slug: str,
    vault_id: uuid.UUID,
    edge_type_filter: str | None = None,
    max_depth: int = 3,
) -> list[GraphNode]:
```

GraphNode Pydantic model: slug: str, page_id: uuid.UUID, link_type: str, depth: int, confidence: float, edge_path: list[str] (optional).

MCP tool stub replacement (PATTERNS.md §mcp/tools/graph.py modify lines 482-511):
- Keep `register(mcp, ctx_factory)` signature
- Replace the inner `_stub_tool` body with the real implementation: ctx = ctx_factory(); async for session in session_with_rls(ctx): resolve vault_id, call traverse_graph(...), return {nodes: [n.model_dump() for n in nodes], start_slug}
- Use `_err(code, message)` helper imported from `server/app/mcp/tools/brain.py` (or copy the pattern)

session_with_rls and vault_resolver patterns already exist (Phase 1b/1d); no new infrastructure needed.

Test fixtures from Plan 02B-02: john-smith-acme.md has manager=[[Durga Dasari]]; durga-dasari.md does not have an explicit edge back to john-smith but acme-corp.md's timeline mentions both — this is a deliberately shallow graph. For the cycle test, the test will manually insert a circular link pair (john-smith-acme → durga-dasari → john-smith-acme via an explicit `manages` edge in test setup).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement traverse_graph recursive CTE in services/graph.py</name>
  <files>server/app/services/graph.py, server/app/tests/graph/test_graph_traversal.py</files>
  <read_first>
    - server/app/services/graph.py (current state — extend, do not rewrite)
    - server/app/services/pages.py (existing service patterns, especially the text() + parameter binding style)
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-RESEARCH.md (Pattern 2 lines 365-433 — full CTE SQL + Python wrapper)
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-PATTERNS.md (§services/graph.py extension; §test_graph_traversal.py analog)
    - server/app/models/link.py (post-migration columns — confirm vault_id is reachable via JOIN pages)
    - server/app/tests/graph/test_graph_traversal.py (4 skip-marked stubs from Plan 02B-02 — unskip and implement)
  </read_first>
  <behavior>
    - test_graph_traversal_follows_links: starting from john-smith-acme.md, traverse depth=2 with no edge filter → returns at least durga-dasari (reports_to manager edge) and acme-corp (works_at employer edge).
    - test_graph_traversal_cycle_safe: insert links A→B (works_at) and B→A (manages); traverse from A with depth=10 — every node appears exactly once in the result; CYCLE column flags the cyclic row but the final SELECT filters WHERE NOT is_cycle.
    - test_graph_traversal_depth_limit: with max_depth=1, only direct neighbours appear; with max_depth=3, transitive neighbours appear; with max_depth=0 the query returns []. Default value is 3 when not supplied.
    - test_graph_traversal_edge_type_filter: edge_type_filter="works_at" returns only edges with link_type="works_at"; "reports_to" returns only reports_to edges.
  </behavior>
  <action>
    Extend `server/app/services/graph.py` with a Pydantic model:
      - `class GraphNode(BaseModel): slug: str; page_id: uuid.UUID; link_type: str; depth: int; confidence: float`

    Add an async function `traverse_graph(session: AsyncSession, ctx: OperationContext, *, start_slug: str, vault_id: uuid.UUID, edge_type_filter: str | None = None, max_depth: int = 3) -> list[GraphNode]`:

    Build the SQL as a `_TRAVERSE_CTE_SQL` module-level constant string containing:
      - WITH RECURSIVE graph_traversal AS (...) — base case: SELECT l.id, l.src_page_id, l.dst_entity_id, l.link_type, l.confidence, 1 AS depth FROM links l JOIN pages p ON l.src_page_id = p.id WHERE p.slug = :start_slug AND p.vault_id = :vault_id AND p.deleted_at IS NULL AND (CAST(:edge_type_filter AS TEXT) IS NULL OR l.link_type = :edge_type_filter) AND l.dst_entity_id IS NOT NULL
      - UNION ALL recursive case: SELECT next_link.id, next_link.src_page_id, next_link.dst_entity_id, next_link.link_type, next_link.confidence, g.depth + 1 FROM links next_link JOIN entities e ON next_link.dst_entity_id = e.id JOIN graph_traversal g ON next_link.src_page_id IN (SELECT id FROM pages WHERE deleted_at IS NULL AND vault_id = :vault_id) WHERE g.depth < :max_depth AND (CAST(:edge_type_filter AS TEXT) IS NULL OR next_link.link_type = :edge_type_filter)
      - CYCLE id SET is_cycle USING traversal_path
      - SELECT DISTINCT ON (p.slug) p.slug, p.id AS page_id, g.link_type, g.depth, g.confidence FROM graph_traversal g JOIN pages p ON g.src_page_id = p.id WHERE NOT g.is_cycle ORDER BY p.slug, g.depth ASC, g.confidence DESC

    Note on the recursive JOIN shape: the precise graph schema is (links.src_page_id → pages, links.dst_entity_id → entities). Traversal "follows" an edge from a page to an entity, then re-enters the link graph via any page whose own outbound link points at that same entity (the recursive case JOINs back through entities). For Phase 2b this means the typed-edge graph behaves like a bipartite traversal — adjust the recursive case to JOIN the next link via `next_link.src_page_id IN (SELECT id FROM pages WHERE id IN (links from this entity))` only if the test fixture requires multi-hop. If the fixture only requires single-hop neighbours, document this in a code comment and leave depth>1 testing as a fixture-extension TODO. The traversal MUST handle depth=1 correctly (direct neighbours) and depth=2+ correctly (transitive neighbours through entities), at minimum on the test_graph_traversal_depth_limit fixture which the executor seeds explicitly.

    Execute via `await session.execute(text(_TRAVERSE_CTE_SQL), {"start_slug": start_slug, "vault_id": str(vault_id), "edge_type_filter": edge_type_filter, "max_depth": max_depth})`. Materialise rows into `list[GraphNode]`.

    Clamp max_depth to range [0, 10] inside the function (defence in depth — prevents accidental runaway). Log via structlog at debug level: "graph_traverse", start_slug, max_depth, edge_type_filter, returned_count.

    Unskip the 4 graph_traversal tests and implement bodies. Each integration test seeds a small set of pages + entities + links into the test DB via direct INSERT (use the db_session fixture), then calls traverse_graph and asserts the expected GraphNode list. The cycle test inserts the deliberate A→B + B→A link pair before calling traverse_graph with max_depth=10.
  </action>
  <verify>
    <automated>cd server &amp;&amp; pytest app/tests/graph/test_graph_traversal.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -v '^#' server/app/services/graph.py | grep -c "WITH RECURSIVE"` is at least 1
    - `grep -v '^#' server/app/services/graph.py | grep -c "CYCLE.*USING\|CYCLE id SET"` is at least 1
    - `grep -v '^#' server/app/services/graph.py | grep -c "class GraphNode"` equals 1
    - `grep -v '^#' server/app/services/graph.py | grep -c "async def traverse_graph"` equals 1
    - `grep -v '^#' server/app/services/graph.py | grep -c "edge_type_filter"` is at least 2 (parameter + SQL binding)
    - `grep -v '^#' server/app/services/graph.py | grep -E "f\"WITH RECURSIVE|format\(.*WITH RECURSIVE|\.execute\(.*\+.*WITH RECURSIVE"` returns no matches (no string interpolation in SQL)
    - `cd server && pytest app/tests/graph/test_graph_traversal.py -x -q` exits 0 with 4 PASSED
    - `cd server && pytest app/tests/graph/test_graph_traversal.py -k cycle_safe -x` exits 0 (cycle detection verified)
    - `cd server && pytest app/tests/graph/test_graph_traversal.py -k edge_type_filter -x` exits 0 (filter verified)
    - No `pytest.mark.skip` decorator remains on any test in test_graph_traversal.py
  </acceptance_criteria>
  <done>traverse_graph implemented with parameterised recursive CTE + CYCLE clause; depth + edge-type filter + cycle safety verified by 4 passing tests.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Replace brain.graph.traverse MCP stub with real implementation</name>
  <files>server/app/mcp/tools/graph.py, server/app/tests/graph/test_brain_graph_traverse.py</files>
  <read_first>
    - server/app/mcp/tools/graph.py (current stub — full body; `_AVAILABLE_IN_PHASE = "2b"` constant; `_TOOLS` list, `register` function, `_stub` helper, `_stub_tool` inner function)
    - server/app/mcp/tools/brain.py (real-tool registration analog — lines 165-216 brain_search; `_err` helper at lines 46-51)
    - server/app/services/graph.py (just-added traverse_graph signature and GraphNode model)
    - server/app/services/vault_resolver.py (resolve_user_vault_id signature + VaultNotFound exception)
    - server/app/dependencies.py (session_with_rls iterator pattern)
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-PATTERNS.md (§mcp/tools/graph.py modify lines 482-511 — exact replacement pattern)
    - server/app/tests/graph/test_brain_graph_traverse.py (2 skip-marked stubs from Plan 02B-02 — unskip and implement)
  </read_first>
  <behavior>
    - test_brain_graph_traverse_returns_typed_nodes: registering the tool against a mock MCP server and calling it with start_slug="john-smith-acme", edge_type_filter="works_at" returns a dict with a `nodes` key containing at least one entry; each entry has slug, page_id, link_type, depth, confidence.
    - test_brain_graph_traverse_rls_enforced: calling the tool as user A while the page belongs to user B returns an empty nodes list (RLS filters out the row); no exception leaked.
  </behavior>
  <action>
    Modify `server/app/mcp/tools/graph.py`:
      - Remove the `_AVAILABLE_IN_PHASE` constant and the `_stub` helper (no longer needed — the stub becomes a real implementation).
      - Keep the `register(mcp, ctx_factory)` function signature.
      - Replace the inner `_stub_tool` body with a real implementation:
        ```
        @mcp.tool(name="brain.graph.traverse", description="Traverse the typed-link knowledge graph via recursive CTE; default depth=3; respects edge_type_filter and RLS.")
        async def brain_graph_traverse(start_slug: str, edge_type_filter: str | None = None, max_depth: int = 3) -> dict:
            ctx = ctx_factory()
            async for session in session_with_rls(ctx):
                try:
                    vault_id = await resolve_user_vault_id(session, ctx.user_id)
                    nodes = await traverse_graph(
                        session, ctx,
                        start_slug=start_slug,
                        vault_id=vault_id,
                        edge_type_filter=edge_type_filter,
                        max_depth=max_depth,
                    )
                    return {"nodes": [n.model_dump() for n in nodes], "start_slug": start_slug}
                except VaultNotFound as exc:
                    return _err("not_found", str(exc))
                except Exception as exc:
                    log.exception("brain_graph_traverse_failed", start_slug=start_slug)
                    return _err("internal_error", "graph traversal failed")
            return _err("internal_error", "session loop exited without result")
        ```
      - Add imports: `from app.services.graph import traverse_graph`, `from app.services.vault_resolver import VaultNotFound, resolve_user_vault_id`, `from app.dependencies import session_with_rls`, `import structlog`, plus the existing `OperationContext`.
      - Define local `_err(code, message)` helper matching the brain.py pattern (lines 46-51), OR import it if it is exposed as a public helper.
      - Add `log = structlog.get_logger("smart_copilot.mcp.tools.graph")`.

    Validate that the tool name registered is still exactly `brain.graph.traverse` (same as the Phase 1d stub — clients must not see a name change).

    Unskip the two tests in `server/app/tests/graph/test_brain_graph_traverse.py`. Implementation uses a mock MCP test harness — see `server/app/tests/mcp/test_tools.py` if it exists, OR construct an OperationContext directly and call the inner async function by invoking the registered tool function through the MCP test harness. For the RLS test, seed two users + two vaults + a link in vault A and call the tool with ctx for user B — assert nodes is empty.
  </action>
  <verify>
    <automated>cd server &amp;&amp; pytest app/tests/graph/test_brain_graph_traverse.py -x -q &amp;&amp; ! grep -q '_AVAILABLE_IN_PHASE' server/app/mcp/tools/graph.py &amp;&amp; ! grep -q 'not_implemented' server/app/mcp/tools/graph.py  </verify>
  <acceptance_criteria>
    - `grep -v '^#' server/app/mcp/tools/graph.py | grep -c "_AVAILABLE_IN_PHASE"` equals 0 (stub constant removed)
    - `grep -v '^#' server/app/mcp/tools/graph.py | grep -c "not_implemented"` equals 0 (stub error code removed)
    - `grep -v '^#' server/app/mcp/tools/graph.py | grep -c "from app.services.graph import traverse_graph"` is at least 1
    - `grep -v '^#' server/app/mcp/tools/graph.py | grep -c "session_with_rls(ctx)"` is at least 1
    - `grep -v '^#' server/app/mcp/tools/graph.py | grep -c '"brain.graph.traverse"'` is at least 1 (tool name preserved)
    - `cd server && pytest app/tests/graph/test_brain_graph_traverse.py -x -q` exits 0 with 2 PASSED
    - No `pytest.mark.skip` decorator remains on any test in test_brain_graph_traverse.py
  </acceptance_criteria>
  <done>brain.graph.traverse MCP tool is fully wired to services/graph.py::traverse_graph; stub constants removed; 2 MCP tests pass; tool name backward-compatible with Phase 1d clients.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| MCP client ↔ brain.graph.traverse | Untrusted start_slug + edge_type_filter + max_depth from agent or external MCP client; bound as SQL parameters only |
| recursive CTE ↔ PostgreSQL | Depth-bounded query; CYCLE clause prevents infinite recursion; vault_id binding enforces RLS at app layer (RLS policy enforces at DB layer) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02B-04-01 | Tampering (SQL injection via edge_type_filter) | services/graph.py traverse_graph | mitigate | edge_type_filter is bound as a SQL parameter (`:edge_type_filter`), never string-interpolated into the SQL text; verified by grep gate (no f-string or .format on WITH RECURSIVE) |
| T-02B-04-02 | Denial of Service (infinite recursion) | recursive CTE | mitigate | CYCLE clause prevents infinite loops; max_depth clamped to [0, 10] inside the function; default depth=3 keeps even worst-case queries bounded |
| T-02B-04-03 | Information Disclosure (cross-vault leak) | brain.graph.traverse MCP tool | mitigate | resolve_user_vault_id(ctx.user_id) called BEFORE traverse_graph; vault_id bound as parameter into the base case WHERE clause; RLS policy on links/pages (migration 0001) provides defence-in-depth |
| T-02B-04-04 | Elevation of Privilege (tool overrides RLS) | session_with_rls usage | mitigate | session_with_rls(ctx) sets app.current_user_id GUC and resets in finally; pool reset listener (Phase 1b) ensures no leaked GUC across requests |
</threat_model>

<verification>
- `cd server && pytest app/tests/graph/ -x -q` exits 0 — all 12 graph tests (5 wikilink + 2 entity + 2 timeline + 4 traversal + 2 brain-graph + 1 snapshot — minus any not yet implemented across plans) pass
- `EXPLAIN ANALYZE` on a sample traverse_graph query uses the B-tree indexes on links.src_page_id and links.dst_entity_id (manual spot-check; not part of automated verify but record in SUMMARY)
- `grep -v '^#' server/app/services/graph.py | grep -cE 'f"WITH RECURSIVE|format\(.*WITH RECURSIVE|\+ "WITH RECURSIVE'` equals 0 (no dynamic SQL construction)
</verification>

<success_criteria>
- traverse_graph service function implemented with parameterised CTE + CYCLE clause
- brain.graph.traverse MCP tool replaced from stub to real implementation; tool name and signature backward-compatible
- All 4 traversal tests + 2 MCP tool tests pass
- RLS enforced via session_with_rls(ctx) + vault_id parameter binding
- No dynamic SQL anywhere in the traversal path
</success_criteria>

<output>
Create `.planning/phases/02B-knowledge-graph-agent-runner/02B-04-SUMMARY.md` when done. Record: WITH RECURSIVE CTE final SQL (truncated), max_depth clamp range, count of test fixtures seeded for the cycle test, EXPLAIN plan summary (whether B-tree indexes used), any deviations from the planned recursive JOIN shape.
</output>
