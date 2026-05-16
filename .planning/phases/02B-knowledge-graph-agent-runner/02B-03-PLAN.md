---
phase: 02B
plan: 03
type: execute
wave: 1
depends_on: ["02B-01", "02B-02"]
files_modified:
  - server/app/services/graph.py
  - server/app/services/entity.py
  - server/app/services/pages.py
  - server/tests/fixtures/expected_links.json
  - server/app/tests/graph/test_wikilink_extractor.py
  - server/app/tests/graph/test_entity_merge.py
  - server/app/tests/graph/test_timeline_events.py
autonomous: true
requirements: [GRAPH-01, GRAPH-02, GRAPH-04, GRAPH-05]
tags: [phase-2b, wave-1, knowledge-graph, wikilink-extraction, entity-merge, timeline]

must_haves:
  truths:
    - "Writing a page that contains [[John Smith]] triggers deterministic zero-LLM link extraction synchronously inside services/pages.py.upsert_page (D-01, GRAPH-01)"
    - "Wikilink regex extracts all four syntactic forms: [[T]], [[T|A]], [[T#H]], [[T#H|A]] with correct anchor_text and fragment fields"
    - "Frontmatter typed-edge keys (employer, manager, investments, founded, investor, partner) produce links with the mapped edge_type (works_at, reports_to, invested_in, founded, invested_in, partner_of) (D-02, GRAPH-02)"
    - "Explicit `edges:` YAML list in frontmatter produces links with the user-supplied type"
    - "Unresolved wikilinks store target_slug=null + unresolved=true + dst_entity_id=null (D-04)"
    - "Re-running the extractor on identical content produces zero net changes to the links table (idempotence dimension 17)"
    - "Entity merge consolidates two duplicate entity rows into one canonical row with aliases preserved (GRAPH-04)"
    - "Timeline events extracted from a page populate the timeline_events table with date, source page_id, detail (GRAPH-05)"
  artifacts:
    - path: "server/app/services/graph.py"
      provides: "Knowledge graph services: extract_wikilinks_from_content, extract_and_upsert_links, extract_timeline_events, merge_entity, _resolve_target_slug"
      min_lines: 200
    - path: "server/app/services/entity.py"
      provides: "Entity deduplication and merge service (canonical_slug + aliases array)"
      min_lines: 40
    - path: "server/app/services/pages.py"
      provides: "Modified upsert_page() that calls extract_and_upsert_links and extract_timeline_events synchronously inside the same DB session"
      contains: "extract_and_upsert_links"
    - path: "server/tests/fixtures/expected_links.json"
      provides: "Blessed snapshot of expected links extracted from the 16-page fixture vault"
      contains: "john-smith-acme"
  key_links:
    - from: "server/app/services/pages.py upsert_page"
      to: "server/app/services/graph.py extract_and_upsert_links"
      via: "synchronous call after ParsedPage construction, before commit"
      pattern: "extract_and_upsert_links"
    - from: "server/app/services/graph.py"
      to: "server/app/models/link.py Link"
      via: "INSERT ... ON CONFLICT (src_page_id, target_text, link_type) DO UPDATE"
      pattern: "ON CONFLICT.*src_page_id.*target_text.*link_type"
    - from: "server/app/services/graph.py"
      to: "server/app/vault/paths.py shortest-unique-path resolver"
      via: "resolve_target_to_slug call inside _resolve_target_slug"
      pattern: "resolve_target_to_slug"
---

<objective>
Implement the zero-LLM wikilink extractor (D-01, D-02, D-04), the entity merge service (GRAPH-04), and the timeline event extractor (GRAPH-05). Wire the extractors into the page write path inside services/pages.py so every page upsert produces the expected rows in `links` and `timeline_events`. Bless the expected_links.json snapshot after the first passing run.

Purpose: GRAPH-01 to GRAPH-05 are the deterministic graph layer the agent depends on. Without this plan, brain.graph.traverse (Plan 04) has nothing to traverse. The extractor runs SYNCHRONOUSLY inside the same DB transaction as page upsert — async deferral would create a window where brain.query immediately after brain.put misses the new links (Pitfall RESEARCH §Common Pitfalls — wikilink extractor as a background job).

Output: A pure-function regex extractor for content + frontmatter wikilinks; a service-layer upsert that uses INSERT ... ON CONFLICT to be idempotent; an entity merge operation; a timeline event extractor; the write-path hook in services/pages.py; and the blessed snapshot in expected_links.json.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/02B-knowledge-graph-agent-runner/02B-CONTEXT.md
@.planning/phases/02B-knowledge-graph-agent-runner/02B-RESEARCH.md
@.planning/phases/02B-knowledge-graph-agent-runner/02B-PATTERNS.md
@.planning/phases/02B-knowledge-graph-agent-runner/02B-AI-SPEC.md
@.planning/phases/02B-knowledge-graph-agent-runner/02B-01-SUMMARY.md
@.planning/phases/02B-knowledge-graph-agent-runner/02B-02-SUMMARY.md
@server/app/services/pages.py
@server/app/vault/parser.py
@server/app/vault/paths.py
@server/app/models/link.py
@server/app/models/entity.py
@server/app/models/timeline_event.py
@server/app/auth/context.py

<interfaces>
Existing parser (server/app/vault/parser.py): exports `_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")` and `ParsedPage` dataclass containing `frontmatter: dict`, `compiled_truth: str`, `timeline: str`, `note_type: str|None`. This is the simple regex — Phase 2b needs the full 4-form regex below.

Full wikilink regex (RESEARCH §Code Examples lines 590-600):
```
_WIKILINK_FULL_RE = re.compile(
    r"\[\["
    r"(?P<target>[^\]#|]+)"
    r"(?:\#(?P<fragment>[^\]|]+))?"
    r"(?:\|(?P<alias>[^\]]+))?"
    r"\]\]"
)
```

Frontmatter edge key mapping (RESEARCH §Code Examples lines 290-297):
- employer -> works_at
- manager -> reports_to
- investments -> invested_in
- founded -> founded
- investor -> invested_in
- partner -> partner_of

Link upsert SQL pattern (PATTERNS.md §services/graph.py Upsert pattern lines 211-228):
- INSERT INTO links (id, src_page_id, dst_entity_id, link_type, confidence, source_kind, anchor_text, fragment, target_text, target_slug, unresolved, created_at, updated_at) VALUES (...)
- ON CONFLICT (src_page_id, target_text, link_type) DO UPDATE SET anchor_text=EXCLUDED.anchor_text, fragment=EXCLUDED.fragment, target_slug=EXCLUDED.target_slug, unresolved=EXCLUDED.unresolved, updated_at=now()

Entity model (server/app/models/entity.py): canonical_slug TEXT, aliases ARRAY(Text), kind entity_kind_enum (person|company|concept|idea|...).

TimelineEvent model (server/app/models/timeline_event.py): src_page_id FK pages, event_date Date, source TEXT, detail TEXT.

Slug resolver (server/app/vault/paths.py): exports `resolve_target_to_slug(target_text: str, vault_id: uuid.UUID, session: AsyncSession) -> str | None` — shortest-unique-path match (Phase 1c). Returns None on unresolved.

Existing services/pages.py upsert_page: writes page row, parses content via parse_vault_file, increments version. Plan 03 adds two post-parse calls inside the same session before the final commit.

RLS: graph.py and entity.py services do NOT open their own session. They accept (session, ctx) from the caller — services/pages.py opens the session via session_with_rls(ctx).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Write wikilink extractor (regex + frontmatter) and link upsert in services/graph.py</name>
  <files>server/app/services/graph.py, server/app/tests/graph/test_wikilink_extractor.py</files>
  <read_first>
    - server/app/services/pages.py (existing service file structure, imports, _err helper, RLS pattern lines 149-167)
    - server/app/vault/parser.py (ParsedPage dataclass and `_WIKILINK_RE`)
    - server/app/vault/paths.py (resolve_target_to_slug interface — confirm signature)
    - server/app/models/link.py (current schema after Plan 02B-01 — confirm new fields exist)
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-PATTERNS.md (§services/graph.py pattern lines 170-237)
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-RESEARCH.md (Pattern 1 Wikilink Extractor lines 282-363; Code Examples lines 586-600)
    - server/app/tests/graph/test_wikilink_extractor.py (stub test names from Plan 02B-02 — unskip and implement)
  </read_first>
  <behavior>
    - test_simple_wikilink_extracted: `extract_wikilinks_from_content("See [[Target Page]] here.")` returns one dict with target_text="Target Page", edge_type="wikilink", confidence=1.0, anchor_text=None, fragment=None.
    - test_aliased_wikilink_extracted: `extract_wikilinks_from_content("See [[Target|My Alias]].")` returns one dict with anchor_text="My Alias".
    - test_fragment_wikilink_extracted: `extract_wikilinks_from_content("See [[Target#Section A]].")` returns one dict with fragment="Section A".
    - test_typed_frontmatter_edge_extracted: `extract_wikilinks_from_frontmatter({"employer": "[[Acme Corp]]"})` returns one dict with edge_type="works_at" and target_text="Acme Corp".
    - test_typed_frontmatter_edge_extracted (extension): `extract_wikilinks_from_frontmatter({"edges": [{"target": "[[Acme Corp]]", "type": "supplier_of"}]})` returns one dict with edge_type="supplier_of".
    - test_wikilink_idempotence: running the integration-level `extract_and_upsert_links` twice on the same parsed page yields the same `links` row count (and no duplicates) after both calls.
  </behavior>
  <action>
    Create `server/app/services/graph.py` with module docstring "Knowledge graph services — zero-LLM wikilink extraction + entity resolution + timeline events (Phase 2b GRAPH-01..05)." First line is `from __future__ import annotations`. Imports follow the pattern from `server/app/services/pages.py` (lines 22-48): re, uuid, structlog, `from sqlalchemy import text`, `AsyncSession`, `OperationContext`, the new Link/Entity models, `ParsedPage` from `app.vault.parser`, and `resolve_target_to_slug` from `app.vault.paths`.

    Define module-level constants:
      - `_WIKILINK_FULL_RE` — the four-form regex per RESEARCH §Code Examples lines 590-600.
      - `_FRONTMATTER_EDGE_KEYS` — dict mapping employer→works_at, manager→reports_to, investments→invested_in, founded→founded, investor→invested_in, partner→partner_of.

    Pure (no-DB) functions:
      - `extract_wikilinks_from_content(content: str) -> list[dict]` — iterates `_WIKILINK_FULL_RE.finditer(content)` and emits `{target_text, anchor_text, fragment, edge_type: "wikilink", confidence: 1.0, source_kind: "wikilink"}`.
      - `extract_wikilinks_from_frontmatter(frontmatter: dict) -> list[dict]` — handles both mapped keys (employer, manager, investments, founded, investor, partner — values may be a single string or a YAML list of strings) and the explicit `edges` list (each item is a dict with target + type keys). edge_type from the mapping table or the user-supplied `type`. confidence=1.0, source_kind="wikilink".
      - These two functions are unit-testable (zero I/O) — used in test_wikilink_extractor.py.

    DB function:
      - `extract_and_upsert_links(session: AsyncSession, ctx: OperationContext, *, page_id: uuid.UUID, parsed: ParsedPage, vault_id: uuid.UUID) -> int`
      - Calls both pure extractors on parsed.compiled_truth + parsed.timeline (body) and parsed.frontmatter, deduplicates the list on (target_text, edge_type) keys to avoid double-inserts within one call, then resolves each target_text to a canonical slug via `resolve_target_to_slug(target_text, vault_id, session)`. If resolved → set target_slug, set dst_entity_id from entities table lookup by canonical_slug, set unresolved=False. If unresolved → set target_slug=None, dst_entity_id=None, unresolved=True (D-04).
      - Performs a single batched `INSERT ... ON CONFLICT (src_page_id, target_text, link_type) DO UPDATE SET anchor_text=EXCLUDED.anchor_text, fragment=EXCLUDED.fragment, target_slug=EXCLUDED.target_slug, dst_entity_id=EXCLUDED.dst_entity_id, unresolved=EXCLUDED.unresolved, updated_at=now()`. Use `session.execute(text(...), [list of params dicts])` — one parameterised statement per row, NEVER string-interpolated values (T-wikilink-01 mitigation).
      - Returns the count of rows affected.
      - Wraps in try/except: log via `structlog.get_logger("smart_copilot.services.graph")` exception and re-raise. Service does NOT swallow errors.

    Idempotence via the UNIQUE constraint on (src_page_id, target_text, link_type) from Plan 02B-01 migration. Re-running extract_and_upsert_links on an unchanged page must produce zero net inserts (every row hits ON CONFLICT DO UPDATE which is a no-op when EXCLUDED values match existing).

    Unskip the 5 stub tests in `server/app/tests/graph/test_wikilink_extractor.py` and implement the test bodies per the `<behavior>` block above. Use the unit-test pattern from `server/app/tests/vault/test_parser.py`. For test_wikilink_idempotence, use the integration pattern (db_session fixture from server/app/tests/conftest.py) — set up a single page in the test DB, call extract_and_upsert_links twice, assert the count of rows for that src_page_id is unchanged after the second call.
  </action>
  <verify>
    <automated>cd server &amp;&amp; pytest app/tests/graph/test_wikilink_extractor.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - File `server/app/services/graph.py` exists with `from __future__ import annotations` as line 1
    - `grep -v '^#' server/app/services/graph.py | grep -c "_WIKILINK_FULL_RE"` is at least 1
    - `grep -v '^#' server/app/services/graph.py | grep -c "_FRONTMATTER_EDGE_KEYS"` is at least 1
    - `grep -v '^#' server/app/services/graph.py | grep -c "def extract_wikilinks_from_content"` equals 1
    - `grep -v '^#' server/app/services/graph.py | grep -c "def extract_wikilinks_from_frontmatter"` equals 1
    - `grep -v '^#' server/app/services/graph.py | grep -c "async def extract_and_upsert_links"` equals 1
    - `grep -v '^#' server/app/services/graph.py | grep -c "ON CONFLICT.*src_page_id.*target_text.*link_type\|ON CONFLICT (src_page_id, target_text, link_type)"` is at least 1
    - `grep -v '^#' server/app/services/graph.py | grep -c "unresolved=True\|\"unresolved\": True"` is at least 1
    - `cd server && pytest app/tests/graph/test_wikilink_extractor.py -x -q` exits 0 with at least 5 PASSED
    - `cd server && pytest app/tests/graph/test_wikilink_extractor.py -k idempotence -x -q` exits 0 (the idempotence test passes)
    - No `pytest.mark.skip` decorator remains on any test in test_wikilink_extractor.py
  </acceptance_criteria>
  <done>services/graph.py exports the three extraction functions; all 5 wikilink tests pass; INSERT ... ON CONFLICT upsert and parameterized SQL confirmed by grep.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Entity merge service + timeline event extractor</name>
  <files>server/app/services/entity.py, server/app/services/graph.py, server/app/tests/graph/test_entity_merge.py, server/app/tests/graph/test_timeline_events.py</files>
  <read_first>
    - server/app/services/graph.py (just-created file — extend it; do not create a separate timeline service)
    - server/app/models/entity.py (canonical_slug, aliases ARRAY, kind enum)
    - server/app/models/timeline_event.py (src_page_id, event_date Date, source Text, detail Text — confirm columns)
    - server/app/vault/parser.py (ParsedPage.timeline string format — Plan 1c documents this; timeline section is markdown lines below the horizontal rule, each line starts with an ISO date)
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-PATTERNS.md (§services/graph.py upsert pattern; §test_entity_merge analog)
  </read_first>
  <behavior>
    - test_entity_merge_consolidates_duplicates: given two entities A and B with same kind but different canonical_slug, calling `merge_entity(session, ctx, primary=A.id, secondary=B.id)` deletes B, adds B.canonical_slug to A.aliases, and updates every links row with dst_entity_id=B.id to point to A.id.
    - test_entity_merge_preserves_canonical_slug: A.canonical_slug is unchanged after merge.
    - test_timeline_event_extracted_from_page: given a ParsedPage whose timeline section is "2024-03-15: Joined company\n2024-04-01: Promoted", `extract_timeline_events(session, ctx, page_id, parsed)` writes 2 rows to timeline_events with the correct dates and details.
    - test_timeline_event_ordered_by_date: events are stored with their event_date; querying ORDER BY event_date returns them oldest-first.
  </behavior>
  <action>
    Create `server/app/services/entity.py` with module docstring "Entity deduplication and merge service (Phase 2b GRAPH-04)." Imports follow the same pattern as services/graph.py.

    Function `merge_entity(session: AsyncSession, ctx: OperationContext, *, primary_id: uuid.UUID, secondary_id: uuid.UUID) -> int`:
      - Load both entity rows; raise ValueError if either is missing or if kinds differ.
      - Append secondary.canonical_slug to primary.aliases array (use PostgreSQL `array_append`, preserve existing aliases).
      - Append every secondary.aliases element to primary.aliases (deduplicate within the function in Python before the UPDATE).
      - Execute `UPDATE links SET dst_entity_id = :primary WHERE dst_entity_id = :secondary` — repoint links.
      - DELETE the secondary entity row.
      - Return the number of links rows repointed.
      - Use parameterised SQL via `session.execute(text(...), {...})`; no string interpolation.

    Extend `server/app/services/graph.py` with `extract_timeline_events(session: AsyncSession, ctx: OperationContext, *, page_id: uuid.UUID, parsed: ParsedPage) -> int`:
      - Parse the `parsed.timeline` string line by line. Each line that matches `^(\d{4}-\d{2}-\d{2})[:\s]\s*(.+)$` becomes a timeline event (date, detail). Lines that do not match are skipped (no exception — relaxed parsing per Phase 1c convention).
      - DELETE existing timeline_events WHERE src_page_id = :page_id before insert (timeline is the authoritative source on each write — re-running yields the same set).
      - Bulk-INSERT the parsed events using parameterised SQL.
      - Set `source` column to the page slug (read from `parsed.frontmatter.get("slug")` if present, else derive from page_id lookup).
      - Return the count of events written.

    Unskip the two entity tests in `server/app/tests/graph/test_entity_merge.py` and the two timeline tests in `server/app/tests/graph/test_timeline_events.py`. Implement them following the `<behavior>` block above. Use db_session + seed fixtures for integration tests (server/app/tests/conftest.py pattern).
  </action>
  <verify>
    <automated>cd server &amp;&amp; pytest app/tests/graph/test_entity_merge.py app/tests/graph/test_timeline_events.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - File `server/app/services/entity.py` exists with `from __future__ import annotations` as line 1
    - `grep -v '^#' server/app/services/entity.py | grep -c "async def merge_entity"` equals 1
    - `grep -v '^#' server/app/services/entity.py | grep -c "UPDATE links SET dst_entity_id"` is at least 1
    - `grep -v '^#' server/app/services/graph.py | grep -c "async def extract_timeline_events"` equals 1
    - `grep -v '^#' server/app/services/graph.py | grep -c "timeline_events"` is at least 1
    - `cd server && pytest app/tests/graph/test_entity_merge.py -x -q` exits 0 with at least 2 PASSED
    - `cd server && pytest app/tests/graph/test_timeline_events.py -x -q` exits 0 with at least 2 PASSED
    - No `pytest.mark.skip` decorator remains on any test in either file
  </acceptance_criteria>
  <done>entity.py implements merge_entity; graph.py adds extract_timeline_events; all four entity+timeline tests pass.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Wire extractors into services/pages.py write path + bless expected_links.json snapshot</name>
  <files>server/app/services/pages.py, server/tests/fixtures/expected_links.json, server/app/tests/graph/test_wikilink_extractor.py</files>
  <read_first>
    - server/app/services/pages.py (current upsert_page function — full body, line numbers, return path)
    - server/app/services/graph.py (just-completed file — extract_and_upsert_links + extract_timeline_events signatures)
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-CONTEXT.md (D-04 — side-effect-free on write path; no auto-stub entity creation)
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-RESEARCH.md (Common Pitfalls 2, 4 — idempotent upsert, watchdog race)
  </read_first>
  <action>
    Modify `server/app/services/pages.py::upsert_page` (the existing function). After `parse_vault_file()` returns the ParsedPage and after the page row is inserted/updated in the same session but BEFORE `session.commit()`, add two awaits:
      - `await extract_and_upsert_links(session, ctx, page_id=page.id, parsed=parsed, vault_id=vault_id)`
      - `await extract_timeline_events(session, ctx, page_id=page.id, parsed=parsed)`

    Import these from `app.services.graph` at the top of pages.py. Both calls are inside the same DB session and same transaction — if either raises, the entire upsert_page rolls back (the existing try/except already covers this; no new exception handling needed).

    Skip the extractor if the page is `archived_fleeting` or `skill` note_type (matches Phase 2a RAG-01 — chunker also skips these). Use a simple guard: `if parsed.note_type in {"archived_fleeting", "skill"}: return page`.

    Add a content_hash short-circuit: if the existing DB page row's `content_hash` equals the newly computed hash AND the page is not being created (this is an update of an unchanged file), skip both extractor calls (Pitfall 4 mitigation — watchdog/MCP race on no-op resaves). The content_hash logic already exists in upsert_page from Phase 1c; reuse it.

    Bless `server/tests/fixtures/expected_links.json`: write a small one-off helper script (or use `python -c`) that:
      1. Loads the 16 fixture vault pages,
      2. Parses each through parse_vault_file,
      3. Collects the expected wikilink+frontmatter extractions per page,
      4. Writes a sorted JSON array (sorted by src_slug, then target_text, then edge_type) to `server/tests/fixtures/expected_links.json`.

    Each JSON object has keys: src_slug, target_text, edge_type, target_slug (null if unresolved), anchor_text, fragment, unresolved (bool), confidence (1.0). Run this once and check the result into the repo — it becomes the snapshot the idempotence test validates against.

    Add a new test `test_expected_links_snapshot` in `server/app/tests/graph/test_wikilink_extractor.py` (graph, integration, asyncio markers). The test loads the fixture vault, runs the extractor through the page write path against a clean DB, queries the links table, normalises the rows into the same shape as expected_links.json, and asserts deep equality against the JSON snapshot. This is dimension 16 (extraction precision).

    Update VALIDATION.md status for tasks 02B-graph-01, 02B-graph-02, 02B-graph-04, 02B-graph-05 from `⬜ pending` to `✅ green` only if all pytest commands pass.
  </action>
  <verify>
    <automated>cd server &amp;&amp; pytest app/tests/graph/ -x -q &amp;&amp; python3 -c "import json; l=json.load(open('server/tests/fixtures/expected_links.json')); assert len(l) &gt; 0, 'expected_links.json still empty after bless'; assert all('src_slug' in i and 'target_text' in i and 'edge_type' in i for i in l)"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -v '^#' server/app/services/pages.py | grep -c "extract_and_upsert_links"` is at least 1
    - `grep -v '^#' server/app/services/pages.py | grep -c "extract_timeline_events"` is at least 1
    - `grep -v '^#' server/app/services/pages.py | grep -c "from app.services.graph"` is at least 1
    - `grep -v '^#' server/app/services/pages.py | grep -c "archived_fleeting\|skill"` is at least 1 (note_type skip guard)
    - `python3 -c "import json; l=json.load(open('server/tests/fixtures/expected_links.json')); print(len(l))"` outputs an integer >= 15 (at least one expected link per non-trivial fixture page)
    - Every element of expected_links.json contains the keys src_slug, target_text, edge_type, target_slug, anchor_text, fragment, unresolved, confidence
    - `cd server && pytest app/tests/graph/ -x -q` exits 0 with all tests PASSED (5 wikilink + 2 entity + 2 timeline + 1 snapshot = 10 PASSED in the graph directory minus the brain_graph_traverse tests which are still skip-pending Plan 04)
    - `cd server && pytest app/tests/graph/test_wikilink_extractor.py::test_expected_links_snapshot -x` exits 0
  </acceptance_criteria>
  <done>upsert_page calls both graph extractors synchronously; expected_links.json blessed snapshot is non-empty and matches actual extraction output; idempotence + snapshot tests pass.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| user-written wikilink target text ↔ database | target_text is verbatim user content; never interpolated as SQL or executed as code |
| frontmatter YAML ↔ extractor | YAML parsed by Phase 1c parser (yaml.safe_load); extractor reads dict only |
| page write path ↔ link upsert transaction | Both must commit together; race between watchdog + MCP write paths must not duplicate rows |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02B-03-01 | Tampering (prompt-injection via wikilink target) | extract_wikilinks_from_content | mitigate | target_text stored as TEXT column verbatim; never interpolated into SQL strings or LLM prompts; all DB writes use parameterised SQL via session.execute(text(...), {...}) |
| T-02B-03-02 | Information Disclosure (cross-user link leak) | extract_and_upsert_links | mitigate | services/graph.py never opens its own session — it inherits the session from upsert_page which is opened via session_with_rls(ctx); RLS policy on links table (migration 0001) filters by user_id; vault_id parameter bound, never user-supplied via string concat |
| T-02B-03-03 | Tampering (race condition duplicate rows) | concurrent watchdog + MCP write | mitigate | UNIQUE constraint on (src_page_id, target_text, link_type) from Plan 02B-01 + ON CONFLICT DO UPDATE — concurrent inserts are idempotent at the DB layer; content_hash short-circuit also prevents the no-op race |
| T-02B-03-04 | Tampering (frontmatter YAML injection) | extract_wikilinks_from_frontmatter | mitigate | yaml.safe_load only (Phase 1c parser convention); never yaml.load; extractor reads frontmatter dict and treats every value as a string for regex matching |
</threat_model>

<verification>
- All 10 tests under server/app/tests/graph/ that this plan touches (5 wikilink + 2 entity + 2 timeline + 1 snapshot) pass.
- `grep -v '^#' server/app/services/graph.py | grep -c "EXECUTE\|exec(\|eval("` equals 0 (no dynamic code execution).
- `cd server && pytest server/ -x -q -m "not slow"` does not regress any previously passing test from Phase 1.
</verification>

<success_criteria>
- services/graph.py + services/entity.py exist and implement the four extraction/merge functions
- services/pages.py.upsert_page calls both extractors synchronously inside the same transaction
- expected_links.json is blessed and non-empty
- All 10 graph tests pass (excluding brain_graph_traverse which is Plan 04)
- Idempotence dimension 17 verified: running extractor twice produces zero net changes
</success_criteria>

<output>
Create `.planning/phases/02B-knowledge-graph-agent-runner/02B-03-SUMMARY.md` when done. Record: line count of graph.py + entity.py, count of links rows produced from fixture vault bless, count of timeline_events rows from fixture vault, test counts, any unresolved wikilinks discovered.
</output>
