---
phase: 02B
plan: 02
type: execute
wave: 0
depends_on: []
files_modified:
  - server/app/tests/graph/__init__.py
  - server/app/tests/graph/test_wikilink_extractor.py
  - server/app/tests/graph/test_graph_traversal.py
  - server/app/tests/graph/test_entity_merge.py
  - server/app/tests/graph/test_timeline_events.py
  - server/app/tests/graph/test_brain_graph_traverse.py
  - server/app/tests/agent/__init__.py
  - server/app/tests/agent/test_react_loop.py
  - server/app/tests/agent/test_tool_registry.py
  - server/app/tests/agent/test_jobs_tool.py
  - server/app/tests/agent/test_conversation_persistence.py
  - server/app/tests/eval/__init__.py
  - server/app/tests/eval/test_golden_suite_seed.py
  - server/tests/fixtures/sample_vault/john-smith-acme.md
  - server/tests/fixtures/sample_vault/john-smith-beta.md
  - server/tests/fixtures/sample_vault/jane-doe.md
  - server/tests/fixtures/sample_vault/kim-park.md
  - server/tests/fixtures/sample_vault/durga-dasari.md
  - server/tests/fixtures/sample_vault/acme-corp.md
  - server/tests/fixtures/sample_vault/beta-corp.md
  - server/tests/fixtures/sample_vault/startup-a.md
  - server/tests/fixtures/sample_vault/acme-meeting-2024-q1.md
  - server/tests/fixtures/sample_vault/acme-meeting-2025-q1.md
  - server/tests/fixtures/sample_vault/machine-learning-notes-2025-04.md
  - server/tests/fixtures/sample_vault/machine-learning-notes-2025-05.md
  - server/tests/fixtures/sample_vault/idea-vault-search-improvement.md
  - server/tests/fixtures/sample_vault/idea-graph-traversal-ux.md
  - server/tests/fixtures/sample_vault/project-smart-copilot-launch.md
  - server/tests/fixtures/sample_vault/concept-rag.md
  - server/tests/fixtures/golden_queries.yaml
  - server/tests/fixtures/expected_links.json
  - server/tests/fixtures/system_prompt.sha256
autonomous: true
requirements: [TEST-05]
tags: [phase-2b, wave-0, test-scaffolding, fixtures, golden-eval]

must_haves:
  truths:
    - "All 11 Wave 0 test files are importable and pytest-discoverable"
    - "pytest collects every Wave 0 stub test as skip with reason 'pending plan 02B-XX'"
    - "server/tests/fixtures/sample_vault/ contains 16 markdown pages covering persons, companies, meetings, concepts, ideas, project"
    - "server/tests/fixtures/golden_queries.yaml contains 25 queries across the six tag categories"
    - "server/tests/fixtures/expected_links.json is a placeholder snapshot the wikilink extractor will overwrite on first bless"
    - "server/tests/fixtures/system_prompt.sha256 contains a 64-hex-char SHA-256 placeholder"
  artifacts:
    - path: "server/app/tests/graph/__init__.py"
      provides: "pytest package marker for new graph tests"
    - path: "server/app/tests/agent/__init__.py"
      provides: "pytest package marker for new agent tests"
    - path: "server/app/tests/eval/__init__.py"
      provides: "pytest package marker for new eval tests"
    - path: "server/tests/fixtures/sample_vault/"
      provides: "Reference vault for golden eval (D-13)"
    - path: "server/tests/fixtures/golden_queries.yaml"
      provides: "Golden query suite for retrieval regression gate (D-13, D-15)"
    - path: "server/tests/fixtures/expected_links.json"
      provides: "Wikilink extractor idempotence snapshot (dimension 17)"
    - path: "server/tests/fixtures/system_prompt.sha256"
      provides: "Brain-first system prompt drift guard hash (dimension 18)"
  key_links:
    - from: "server/tests/fixtures/sample_vault/*.md"
      to: "server/tests/fixtures/golden_queries.yaml"
      via: "expected_top_slug references match filename stems"
      pattern: "john-smith-acme|acme-corp|jane-doe|kim-park"
    - from: "server/tests/fixtures/golden_queries.yaml"
      to: "server/scripts/eval_agent.py (created in Plan 02B-07)"
      via: "yaml.safe_load schema matches AI-SPEC §5"
      pattern: "expected_top_slug.*expected_top_k_slugs.*expected_status"
---

<objective>
Create every Wave 0 file declared MISSING in VALIDATION.md: 12 test stub files plus 16 fixture vault pages, the golden_queries.yaml, expected_links.json, and system_prompt.sha256 placeholder. The test stubs must be pytest-discoverable so the Nyquist gate stops returning MISSING for every Phase 2b task. The fixture vault is the ground truth corpus the retrieval pipeline runs against; the golden queries are the regression gate for Phase 3 entry.

Purpose: AI-SPEC §5 Reference Dataset locks the exact composition (16 pages, 25 queries) and dimension coverage. Every Wave 1-5 task references one or more of these files in its automated verify command. Without this plan landing first, every other Wave 0 test command returns MISSING and the gate fails.

Output: A discoverable test surface (pytest collects with zero errors), a hand-authored fixture vault with deliberate name collisions (john-smith-acme + john-smith-beta) and date pairs (acme-meeting-2024-q1 + acme-meeting-2025-q1), 25 yaml queries covering the six golden-eval tag categories, and three small placeholder/snapshot files.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/02B-knowledge-graph-agent-runner/02B-CONTEXT.md
@.planning/phases/02B-knowledge-graph-agent-runner/02B-RESEARCH.md
@.planning/phases/02B-knowledge-graph-agent-runner/02B-PATTERNS.md
@.planning/phases/02B-knowledge-graph-agent-runner/02B-AI-SPEC.md
@.planning/phases/02B-knowledge-graph-agent-runner/02B-VALIDATION.md
@server/app/tests/vault/test_parser.py
@server/app/tests/vault/test_pages_service.py
@server/app/tests/vault/test_wikilinks.py
@server/app/tests/conftest.py

<interfaces>
Test stub pattern (unit, from server/app/tests/vault/test_parser.py): `from __future__ import annotations` + `import pytest` + `pytestmark = [pytest.mark.graph, pytest.mark.unit]` + skip-marked test functions.

Test stub pattern (integration, from server/app/tests/vault/test_pages_service.py): adds `pytest.mark.integration`, `pytest.mark.asyncio`, and `db_session: AsyncSession` + `seed_user_for_vault` + `seed_vault` fixtures.

golden_queries.yaml schema (AI-SPEC §5 lines 936-963): each query has id, query, tags, expected_top_slug, expected_top_k_slugs, expected_status, expected_tool_first, expected_min_citations, notes. Empty-vault queries also carry expected_tools (list of allowed tool names — must be subset of brain.* and graph.*). Graph queries carry expected_edge_type.

Tag categories (AI-SPEC §5 Reference Dataset lines 1008-1017):
- factual (6 queries)
- completeness (3 queries)
- typed-edge / graph (3 queries)
- empty-vault / transparency (3 queries)
- conflation (2 queries)
- stale-note (2 queries)
- tool-error / failure-injection (3 queries)
- mcp-rest-parity (2 queries)
- wikilink-snapshot (1 query)

system_prompt.sha256 format: single line of 64 hex characters followed by a newline. Placeholder for this plan is 64 zeros; Plan 02B-05 will overwrite with the real digest after BRAIN_FIRST_SYSTEM_PROMPT is finalised.

expected_links.json schema: JSON array of objects each containing src_slug, target_text, edge_type, target_slug, anchor_text, fragment, unresolved, confidence. This plan emits empty array placeholder; Plan 02B-03 will bless it on the first passing run.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Create three test directory packages with 12 skip-marked stub test files</name>
  <files>server/app/tests/graph/__init__.py, server/app/tests/graph/test_wikilink_extractor.py, server/app/tests/graph/test_graph_traversal.py, server/app/tests/graph/test_entity_merge.py, server/app/tests/graph/test_timeline_events.py, server/app/tests/graph/test_brain_graph_traverse.py, server/app/tests/agent/__init__.py, server/app/tests/agent/test_react_loop.py, server/app/tests/agent/test_tool_registry.py, server/app/tests/agent/test_jobs_tool.py, server/app/tests/agent/test_conversation_persistence.py, server/app/tests/eval/__init__.py, server/app/tests/eval/test_golden_suite_seed.py</files>
  <read_first>
    - server/app/tests/vault/test_parser.py (unit-test pattern — imports, pytestmark, function signature)
    - server/app/tests/vault/test_pages_service.py (integration-test pattern — db_session + seed fixtures)
    - server/app/tests/vault/test_wikilinks.py (DB-factory pattern for tests that need engine-level access)
    - server/app/tests/conftest.py (existing pytest markers and fixtures — confirm graph/agent/unit/integration markers exist)
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-RESEARCH.md (Wave 0 Gaps lines 810-827 — definitive file list)
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-VALIDATION.md (Per-Task Verification Map lines 38-55 — definitive test names per requirement)
  </read_first>
  <action>
    Create three empty `__init__.py` files (one per directory: `server/app/tests/graph/__init__.py`, `server/app/tests/agent/__init__.py`, `server/app/tests/eval/__init__.py`). Each is a single newline character — Python package marker only.

    Create 12 stub test files, each containing `from __future__ import annotations`, a `pytestmark` list with `pytest.mark.{domain}` and `pytest.mark.{unit|integration}`, and one or more skip-marked test functions. Test function names MUST match the VALIDATION.md Per-Task Verification Map automated commands so `pytest -k <name>` succeeds.

    Per-file stub specs (function names are normative — they back the verify commands in plans 02B-03 through 02B-07):

    test_wikilink_extractor.py (markers: graph, unit) — 5 stub tests:
      - test_simple_wikilink_extracted — covers GRAPH-01 baseline `[[Target]]`
      - test_aliased_wikilink_extracted — covers `[[Target|Alias]]` with anchor_text
      - test_fragment_wikilink_extracted — covers `[[Target#Heading]]`
      - test_typed_frontmatter_edge_extracted — covers GRAPH-02 mapped keys (`employer: [[Acme]]`)
      - test_wikilink_idempotence — covers dimension 17 (running extractor twice yields identical rows)

    test_graph_traversal.py (markers: graph, integration, asyncio) — 4 stub tests:
      - test_graph_traversal_follows_links — base recursive CTE
      - test_graph_traversal_cycle_safe — CYCLE clause prevents infinite loop
      - test_graph_traversal_depth_limit — max_depth=3 enforced
      - test_graph_traversal_edge_type_filter — edge_type_filter='works_at' only returns works_at edges

    test_entity_merge.py (markers: graph, integration, asyncio) — 2 stub tests:
      - test_entity_merge_consolidates_duplicates
      - test_entity_merge_preserves_canonical_slug

    test_timeline_events.py (markers: graph, integration, asyncio) — 2 stub tests:
      - test_timeline_event_extracted_from_page
      - test_timeline_event_ordered_by_date

    test_brain_graph_traverse.py (markers: graph, integration, asyncio) — 2 stub tests:
      - test_brain_graph_traverse_returns_typed_nodes — covers GRAPH-06 MCP tool surface
      - test_brain_graph_traverse_rls_enforced — covers T-rls-01

    test_react_loop.py (markers: agent, unit, asyncio) — 6 stub tests:
      - test_react_loop_max_iterations — D-05 hard cap
      - test_react_loop_brain_first_first_tool_is_search — D-06 ordering
      - test_react_loop_no_local_knowledge_returns_canonical — D-06 empty-vault path
      - test_react_loop_non_retryable_aborts — D-07 AuthenticationError abort
      - test_react_loop_retryable_retries_once — D-07 Timeout retry path
      - test_react_loop_non_critical_tool_skip — D-07 graph.traverse failure → continue

    test_tool_registry.py (markers: agent, unit) — 2 stub tests:
      - test_tool_registry_has_22_tools
      - test_tool_specs_match_registry

    test_jobs_tool.py (markers: agent, integration, asyncio) — 2 stub tests:
      - test_jobs_submit_writes_job_row
      - test_jobs_submit_enqueues_apscheduler

    test_conversation_persistence.py (markers: agent, integration, asyncio) — 4 stub tests:
      - test_brain_query_creates_conversation_new_session
      - test_brain_query_appends_to_existing_session
      - test_brain_query_mcp_rest_parity — D-08 parity test
      - test_message_token_usage_persisted

    test_golden_suite_seed.py (markers: eval, integration, asyncio) — 2 stub tests:
      - test_golden_suite_loaded_from_yaml
      - test_golden_query_fields_match_yaml

    Every test body is a single statement: `pass  # implementation lands in plan 02B-NN` (NN = 03 for graph extraction; 04 for graph traversal and MCP; 05 for react_loop and tool registry; 06 for jobs and conversation; 07 for golden suite seed). EVERY test function is decorated with `@pytest.mark.skip(reason="pending plan 02B-NN")`. Integration/async tests additionally carry `@pytest.mark.asyncio` even though skipped.

    If `server/pyproject.toml` does not already register the `graph`, `agent`, `eval` pytest markers under `[tool.pytest.ini_options].markers`, add them: one line each — `graph: graph extraction/traversal tests`, `agent: agent runner tests`, `eval: golden eval tests`. Inspect the file first via Read before editing.
  </action>
  <verify>
    <automated>cd server &amp;&amp; pytest app/tests/graph/ app/tests/agent/ app/tests/eval/ --collect-only -q 2&gt;&amp;1 | tail -5 | grep -E "[0-9]+ tests collected" | head -1</automated>
  </verify>
  <acceptance_criteria>
    - `find server/app/tests/graph server/app/tests/agent server/app/tests/eval -name __init__.py | wc -l` equals 3
    - `find server/app/tests/graph server/app/tests/agent server/app/tests/eval -name 'test_*.py' | wc -l` equals 12
    - `cd server && pytest app/tests/graph/ app/tests/agent/ app/tests/eval/ --collect-only -q` exits 0
    - `cd server && pytest app/tests/graph/ app/tests/agent/ app/tests/eval/ -q` reports zero failures and at least 33 SKIPPED tests
    - `cd server && pytest app/tests/agent/test_react_loop.py -k max_iterations --collect-only -q` collects at least 1 test
    - `cd server && pytest app/tests/agent/test_react_loop.py -k brain_first --collect-only -q` collects at least 1 test
    - `cd server && pytest app/tests/graph/test_wikilink_extractor.py -k types --collect-only -q` collects at least 1 test
    - Every test file contains `from __future__ import annotations` as the first import line
  </acceptance_criteria>
  <done>All 12 stub test files plus 3 __init__.py files exist, pytest collects them with zero errors, every test function name referenced by VALIDATION.md is discoverable.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Hand-author the 16-page fixture vault under server/tests/fixtures/sample_vault/</name>
  <files>server/tests/fixtures/sample_vault/john-smith-acme.md, server/tests/fixtures/sample_vault/john-smith-beta.md, server/tests/fixtures/sample_vault/jane-doe.md, server/tests/fixtures/sample_vault/kim-park.md, server/tests/fixtures/sample_vault/durga-dasari.md, server/tests/fixtures/sample_vault/acme-corp.md, server/tests/fixtures/sample_vault/beta-corp.md, server/tests/fixtures/sample_vault/startup-a.md, server/tests/fixtures/sample_vault/acme-meeting-2024-q1.md, server/tests/fixtures/sample_vault/acme-meeting-2025-q1.md, server/tests/fixtures/sample_vault/machine-learning-notes-2025-04.md, server/tests/fixtures/sample_vault/machine-learning-notes-2025-05.md, server/tests/fixtures/sample_vault/idea-vault-search-improvement.md, server/tests/fixtures/sample_vault/idea-graph-traversal-ux.md, server/tests/fixtures/sample_vault/project-smart-copilot-launch.md, server/tests/fixtures/sample_vault/concept-rag.md</files>
  <read_first>
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-AI-SPEC.md (§5 Reference Dataset lines 997-1018 — definitive composition)
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-CONTEXT.md (D-01, D-02 — wikilink + frontmatter edge syntax)
    - server/app/vault/parser.py (compiled-truth/timeline horizontal-rule convention; frontmatter YAML format)
    - server/tests/fixtures/ (existing fixture directory layout if any)
  </read_first>
  <action>
    Hand-author each fixture page in the compiled-truth/timeline convention (Phase 1c VAULT-04): YAML frontmatter delimited by `---`, then compiled-truth section above a second `---` horizontal-rule separator, then timeline section below it. Per D-16, NO LLM-generated content — every page is human-written. Per AI-SPEC §5, every page slug matches its filename stem (no trailing `.md`).

    PERSON PAGES (5 — every person page has type: person, employer wikilink, manager wikilink in frontmatter):
      - john-smith-acme.md — type:person, employer:[[Acme Corp]], manager:[[Durga Dasari]]. Body cites a meeting wikilink [[acme-meeting-2024-q1|Acme Q1 review]]. Timeline: 2024-03-15 joined Acme as Senior Engineer.
      - john-smith-beta.md — type:person, employer:[[Beta Corp]], manager:[[Jane Doe]]. SAME display name "John Smith" but distinct slug (D-13 conflation guard). Timeline: 2023-09-01 joined Beta.
      - jane-doe.md — type:person, employer:[[Beta Corp]]. Manages john-smith-beta. Body links [[Beta Corp#Engineering Team]] (fragment syntax test).
      - kim-park.md — type:person, employer:[[Acme Corp]]. Aliased link [[Acme Corp|Acme]].
      - durga-dasari.md — type:person, employer:[[Acme Corp]]. Manages john-smith-acme.

    COMPANY PAGES (3):
      - acme-corp.md — type:company, founded:[[Durga Dasari]]. Compiled-truth describes the company. Timeline has three entries: 2018 founding, 2024 meeting, 2025 meeting.
      - beta-corp.md — type:company, founded:[[Jane Doe]]. Has partner:[[Acme Corp]] edge (typed edge test).
      - startup-a.md — type:company, investor:[[Project Smart Copilot Launch]] — exercises the invested_in reverse path.

    MEETING PAGES (2 — same topic, different ages, for stale-note awareness dimension 15):
      - acme-meeting-2024-q1.md — type:meeting, links to [[John Smith Acme]] and [[Acme Corp]]. Timeline dated 2024-03-15. OLDER page.
      - acme-meeting-2025-q1.md — type:meeting, links to [[John Smith Acme]] and [[Acme Corp]]. Timeline dated 2025-03-15. NEWER page.

    CONCEPT PAGES (3 total — two ML notes for completeness dimension 7 plus one RAG concept):
      - machine-learning-notes-2025-04.md — type:concept, tags:[ml]. Timeline 2025-04.
      - machine-learning-notes-2025-05.md — type:concept, tags:[ml]. Timeline 2025-05.
      - concept-rag.md — type:concept. Compiled-truth defines RAG. Body has [[idea-vault-search-improvement|the search idea]] wikilink.

    IDEA PAGES (2):
      - idea-vault-search-improvement.md — type:idea. Links to [[concept-rag]].
      - idea-graph-traversal-ux.md — type:idea. Links to [[machine-learning-notes-2025-05]].

    PROJECT PAGE (1):
      - project-smart-copilot-launch.md — type:project, investments YAML list containing a single wikilink [[Startup A]] (AI-SPEC frontmatter edge list test).

    Every page must include at minimum: YAML frontmatter with type key, a one-paragraph compiled-truth section, a horizontal rule separator (`---` on its own line), and a `## Timeline` section with at least one ISO-dated event. Body content is short (3-5 sentences each) — these are test fixtures, not training data.

    The vault explicitly CONTAINS ZERO pages about "Acme funding round" or "latest Acme funding" — this absence is what AI-SPEC §5 calls out as the empty-vault transparency test (golden query q-007 in the YAML written in Task 3).

    Filenames are slugs (lower-kebab-case). Display titles in body content may differ (e.g., "John Smith" in body, slug john-smith-acme). The slug is the canonical id used by golden_queries.yaml.
  </action>
  <verify>
    <automated>ls server/tests/fixtures/sample_vault/*.md | wc -l | awk '$1 == 16 {exit 0} {exit 1}'</automated>
  </verify>
  <acceptance_criteria>
    - Exactly 16 markdown files exist under `server/tests/fixtures/sample_vault/`
    - Every page begins with a `---` line on line 1 (YAML frontmatter open delimiter)
    - Every page has a `## Timeline` heading
    - `grep -l 'type: person' server/tests/fixtures/sample_vault/*.md | wc -l` equals 5
    - `grep -l 'type: company' server/tests/fixtures/sample_vault/*.md | wc -l` equals 3
    - `grep -l 'type: meeting' server/tests/fixtures/sample_vault/*.md | wc -l` equals 2
    - `grep -l 'type: concept' server/tests/fixtures/sample_vault/*.md | wc -l` equals 3
    - `grep -l 'type: idea' server/tests/fixtures/sample_vault/*.md | wc -l` equals 2
    - `grep -l 'type: project' server/tests/fixtures/sample_vault/*.md | wc -l` equals 1
    - `grep -l 'John Smith' server/tests/fixtures/sample_vault/john-smith-acme.md server/tests/fixtures/sample_vault/john-smith-beta.md | wc -l` equals 2 (deliberate conflation pair)
    - `grep -l '\[\[Acme Corp|Acme\]\]' server/tests/fixtures/sample_vault/kim-park.md` matches (aliased link test)
    - `grep -l 'Beta Corp#Engineering Team' server/tests/fixtures/sample_vault/jane-doe.md` matches (fragment link test)
    - `grep -L 'funding round' server/tests/fixtures/sample_vault/*.md | wc -l` equals 16 (vault has zero funding pages — empty-vault probe)
  </acceptance_criteria>
  <done>Sixteen hand-authored fixture pages exist with the correct type distribution and the required name/date collision pairs; vault contains zero "funding round" mentions.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Write golden_queries.yaml (25 queries), expected_links.json placeholder, system_prompt.sha256 placeholder</name>
  <files>server/tests/fixtures/golden_queries.yaml, server/tests/fixtures/expected_links.json, server/tests/fixtures/system_prompt.sha256</files>
  <read_first>
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-AI-SPEC.md (§5 Reference Dataset lines 1008-1017 — tag categories; lines 936-963 — YAML schema)
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-RESEARCH.md (Code Examples lines 629-659 — three concrete golden_queries.yaml examples)
    - server/tests/fixtures/sample_vault/ (just written in Task 2 — every expected_top_slug MUST match a filename stem)
  </read_first>
  <action>
    Write `server/tests/fixtures/golden_queries.yaml` as a YAML array of 25 query objects matching the AI-SPEC §5 schema. Each object has the fields: id (q-001 through q-025 zero-padded), query (natural language), tags (list of strings), expected_top_slug (string slug or null for empty-vault), expected_top_k_slugs (list, may be empty), expected_status (one of: success, no_local_knowledge, tool_error), expected_tool_first (always brain.search per D-06), expected_min_citations (integer, 0 for empty-vault), notes (string). Graph queries additionally have expected_edge_type. Empty-vault queries additionally have expected_tools (a list constraining the set of allowed tool names — must be subset of brain.search and brain.graph.traverse). Failure-injection queries additionally have an inject_failure key naming the tool to mock-fail.

    Distribution (totalling exactly 25 — AI-SPEC §5 lines 1008-1017):
      - 6 factual queries (q-001 to q-006) — single-entity lookups against the person/company pages
      - 3 completeness queries (q-007 to q-009) — concept queries spanning multiple ml notes pages
      - 3 typed-edge graph queries (q-010 to q-012) — exercise brain.graph.traverse with expected_edge_type (works_at, founded, invested_in)
      - 3 empty-vault transparency queries (q-013 to q-015) — including the funding-round probe (vault has zero funding pages)
      - 2 entity conflation queries (q-016, q-017) — ambiguous "John Smith" queries; expected_status either success with both slugs OR no_local_knowledge
      - 2 stale-note queries (q-018, q-019) — same-topic different-age queries; expected_top_slug is the newer page
      - 3 failure-injection queries (q-020 to q-022) — inject_failure naming brain.graph.traverse (non-critical), brain.search (critical), entity.enrich (non-critical)
      - 2 mcp-rest parity queries (q-023, q-024) — identical query text to be issued via both transports
      - 1 wikilink-snapshot query (q-025) — exercises dimension 16/17 wikilink-extraction precision and idempotence

    Concrete query text uses the fixture vault: e.g., q-001 query="where does John Smith work?" with notes flagging the conflation; q-007 query="what is the latest funding round for Acme Corp?" with expected_status=no_local_knowledge and expected_tools=[brain.search, brain.graph.traverse]; q-010 query="who works at Acme Corp?" with expected_edge_type=works_at and expected_top_k_slugs=[john-smith-acme, kim-park, durga-dasari]; q-011 query="what did Project Smart Copilot Launch invest in?" with expected_edge_type=invested_in and expected_top_k_slugs=[startup-a].

    YAML file MUST be parseable by `python -c "import yaml; yaml.safe_load(open('server/tests/fixtures/golden_queries.yaml'))"`. Top-level structure is a list of mappings; no anchors, no aliases (keep it simple — D-16 reproducibility).

    Write `server/tests/fixtures/expected_links.json` as `[]` (single line — empty JSON array). This is overwritten by Plan 02B-03 on first bless. The empty placeholder lets `test_wikilink_idempotence` exist as a discoverable test.

    Write `server/tests/fixtures/system_prompt.sha256` as a single line of 64 zeros (`0000000000000000000000000000000000000000000000000000000000000000`) followed by a newline. Plan 02B-05 will overwrite with the real SHA-256 of BRAIN_FIRST_SYSTEM_PROMPT.
  </action>
  <verify>
    <automated>python3 -c "import yaml,json; q=yaml.safe_load(open('server/tests/fixtures/golden_queries.yaml')); assert len(q)==25, len(q); assert all('expected_status' in i for i in q); l=json.load(open('server/tests/fixtures/expected_links.json')); assert l==[]; s=open('server/tests/fixtures/system_prompt.sha256').read().strip(); assert len(s)==64 and all(c in '0123456789abcdef' for c in s)"</automated>
  </verify>
  <acceptance_criteria>
    - `python3 -c "import yaml; q=yaml.safe_load(open('server/tests/fixtures/golden_queries.yaml')); print(len(q))"` outputs 25
    - Every YAML object contains keys: id, query, tags, expected_status
    - `python3 -c "import yaml; q=yaml.safe_load(open('server/tests/fixtures/golden_queries.yaml')); print(sum(1 for i in q if 'empty-vault' in (i.get('tags') or [])))"` outputs 3
    - `python3 -c "import yaml; q=yaml.safe_load(open('server/tests/fixtures/golden_queries.yaml')); print(sum(1 for i in q if 'graph' in (i.get('tags') or []) or i.get('expected_edge_type')))"` outputs at least 3
    - `python3 -c "import yaml; q=yaml.safe_load(open('server/tests/fixtures/golden_queries.yaml')); print(sum(1 for i in q if i.get('inject_failure')))"` outputs 3
    - `python3 -c "import json; print(json.load(open('server/tests/fixtures/expected_links.json')))"` outputs `[]`
    - `wc -c server/tests/fixtures/system_prompt.sha256` reports 65 bytes (64 hex chars plus newline)
    - `grep -E '^[0-9a-f]{64}$' server/tests/fixtures/system_prompt.sha256` matches
    - Every `expected_top_slug` value in golden_queries.yaml that is non-null corresponds to an existing file under `server/tests/fixtures/sample_vault/{slug}.md` (verify with: `python3 -c "import yaml,os; q=yaml.safe_load(open('server/tests/fixtures/golden_queries.yaml')); missing=[i['expected_top_slug'] for i in q if i.get('expected_top_slug') and not os.path.exists(f\"server/tests/fixtures/sample_vault/{i['expected_top_slug']}.md\")]; assert not missing, missing"`)
  </acceptance_criteria>
  <done>golden_queries.yaml has 25 valid queries with correct tag distribution and slug references; expected_links.json is empty array placeholder; system_prompt.sha256 is 64-zero placeholder.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| fixture vault ↔ test DB | Fixture content is loaded into the test database by the eval runner; must not contain injection payloads that could compromise the DB |
| golden_queries.yaml ↔ pytest | YAML loaded via yaml.safe_load (never yaml.load) to prevent code execution |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02B-02-01 | Tampering | server/tests/fixtures/golden_queries.yaml | mitigate | YAML loaded only via yaml.safe_load throughout the codebase; no yaml.unsafe_load anywhere in eval_agent.py (Plan 02B-07) |
| T-02B-02-02 | Tampering | server/tests/fixtures/sample_vault/*.md | mitigate | Fixture content is hand-authored, deterministic, and reviewed at commit time; D-16 forbids LLM-generated content; markdown rendering is sanitized through Phase 1c parser which is the same code path production uses |
| T-02B-02-03 | Information Disclosure | test stub files | accept | Stubs contain only function signatures and skip markers; no secrets or PII; check-in safe |
</threat_model>

<verification>
- `pytest --collect-only` against the three new test directories returns zero errors
- The 16 fixture pages parse correctly through `server/app/vault/parser.py::parse_vault_file` (smoke verification only — not asserted in this plan)
- `yaml.safe_load(open(golden_queries.yaml))` returns a list of 25 dicts
- Every golden query's `expected_top_slug` (if non-null) corresponds to an existing fixture file
- `system_prompt.sha256` and `expected_links.json` are valid placeholders the downstream plans can overwrite
</verification>

<success_criteria>
- 12 stub test files exist and are discoverable (33+ SKIPPED tests collected)
- 16 hand-authored fixture pages exist with correct type distribution and required name/date collision pairs
- golden_queries.yaml has 25 valid queries spanning all required tag categories
- expected_links.json placeholder and system_prompt.sha256 placeholder exist and are valid
- Plan 02B-03 through 02B-07 can reference these test names and fixture files in their verify commands without MISSING gates
</success_criteria>

<output>
Create `.planning/phases/02B-knowledge-graph-agent-runner/02B-02-SUMMARY.md` when done. Record: count of stub tests per directory, list of 16 fixture filenames + page types, golden query count per tag category, location of placeholder files.
</output>
