---
phase: 02B
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - server/alembic/versions/0006_phase_2b_schema.py
  - server/app/models/link.py
  - server/app/models/conversation.py
  - server/app/models/golden_eval.py
  - server/requirements.txt
autonomous: true
requirements: [GRAPH-01, GRAPH-02, AGENT-05, AGENT-06]
tags: [phase-2b, schema, migration, alembic, knowledge-graph, agent-runner, models]

must_haves:
  truths:
    - "Alembic upgrade head succeeds from migration 0005 to 0006 against the test database"
    - "links.dst_entity_id is NULLABLE in PostgreSQL after migration 0006 (D-04 unresolved wikilinks)"
    - "links table has anchor_text, fragment, target_text, target_slug, unresolved columns after migration"
    - "conversations.mcp_mode enum values are exactly disable/auto/manual (not disabled/client/server) after migration"
    - "messages table has token_usage JSONB and model TEXT columns after migration"
    - "golden_queries table has expected_top_slug, expected_status, expected_tool_first, expected_edge_type, notes columns after migration"
    - "requirements.txt contains opentelemetry-sdk, opentelemetry-exporter-otlp, openinference-instrumentation-litellm, pyyaml>=6.0"
  artifacts:
    - path: "server/alembic/versions/0006_phase_2b_schema.py"
      provides: "Alembic migration that closes the four Phase 2b schema gaps"
      contains: "0006"
    - path: "server/app/models/link.py"
      provides: "Link model with anchor_text/fragment/target_text/target_slug/unresolved fields; dst_entity_id nullable"
      contains: "anchor_text"
    - path: "server/app/models/conversation.py"
      provides: "Conversation.mcp_mode enum with disable/auto/manual; Message.token_usage + Message.model columns"
      contains: "disable"
    - path: "server/app/models/golden_eval.py"
      provides: "GoldenQuery model with expected_top_slug/expected_status/expected_tool_first/expected_edge_type/notes"
      contains: "expected_top_slug"
    - path: "server/requirements.txt"
      provides: "OpenTelemetry + Phoenix instrumentation + pyyaml pinned for Phase 2b"
      contains: "opentelemetry-sdk"
  key_links:
    - from: "server/app/models/link.py"
      to: "server/alembic/versions/0006_phase_2b_schema.py"
      via: "column definitions match migration upgrade()"
      pattern: "anchor_text"
    - from: "server/app/models/conversation.py"
      to: "server/alembic/versions/0006_phase_2b_schema.py"
      via: "enum values rename-and-recreate pattern (research lines 81-95)"
      pattern: "conversations_mcp_mode_enum_new"
---

<objective>
Close the four Phase 2b schema gaps identified in RESEARCH.md §Schema Gaps via a single Alembic migration (0006) and matching SQLAlchemy model updates. Also adds the OpenTelemetry + pyyaml dependencies to requirements.txt so Wave 2-5 plans can import them. This plan UNBLOCKS every other Phase 2b plan — without it the links/messages/conversations/golden_queries tables cannot hold Phase 2b data.

Purpose: D-04 requires storing unresolved wikilinks (`target_slug = null`, `unresolved = true`) but the existing `links` table has `dst_entity_id NOT NULL`. AGENT-05 requires `mcp_mode` values `disable/auto/manual` but the existing enum stores `disabled/client/server`. AGENT-05 requires `messages.token_usage` and `messages.model`; neither exists. AGENT-06 requires extra fields on `golden_queries`; none exist. All four gaps must be addressed before any service code can run.

Output: One migration file (0006), three modified model files, and an updated requirements.txt — all consistent with each other.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/02B-knowledge-graph-agent-runner/02B-CONTEXT.md
@.planning/phases/02B-knowledge-graph-agent-runner/02B-RESEARCH.md
@.planning/phases/02B-knowledge-graph-agent-runner/02B-PATTERNS.md
@server/alembic/versions/0003_phase_1c_vault.py
@server/alembic/versions/0004_phase_1d_search_vector.py
@server/app/models/link.py
@server/app/models/conversation.py
@server/app/models/golden_eval.py
@server/app/models/entity.py
@server/requirements.txt

<interfaces>
<!-- Schema gaps and exact column shapes from RESEARCH.md §Schema Gaps and PATTERNS.md §Pattern Assignments. -->

Existing links columns (server/app/models/link.py):
- id UUID PK, src_page_id UUID FK pages NOT NULL, dst_entity_id UUID FK entities NOT NULL,
- link_type VARCHAR(64), confidence Numeric(3,2) default 1.00,
- source_kind link_source_kind_enum ('wikilink','enrichment','inferred')
- TimestampMixin (created_at, updated_at)

Existing conversations.mcp_mode enum values (server/app/models/conversation.py): 'disabled','client','server'
Existing messages columns (server/app/models/conversation.py):
- id, conversation_id, role, content, citations JSONB, tool_calls JSONB, created_at

Existing golden_queries columns (server/app/models/golden_eval.py):
- id, suite_id, query Text, expected_slugs ARRAY(Text), tags ARRAY(Text)

Required additions (RESEARCH.md §Schema Gaps + PATTERNS.md analog 0003_phase_1c_vault.py):
- links: + anchor_text Text NULL, fragment Text NULL, target_text Text NULL, target_slug Text NULL, unresolved Boolean NOT NULL default false; dst_entity_id -> NULLABLE
- conversations.mcp_mode enum: rename-and-recreate ('disable','auto','manual'); default 'disable'
- messages: + token_usage JSONB NULL, + model Text NULL
- golden_queries: + expected_top_slug Text NULL, + expected_status VARCHAR(64) NULL, + expected_tool_first VARCHAR(128) NULL, + expected_edge_type VARCHAR(128) NULL, + notes Text NULL

Migration analog (server/alembic/versions/0003_phase_1c_vault.py): provides the `op.add_column`, `op.alter_column nullable=True`, and enum rename-and-recreate pattern (lines 30-46 for columns; lines 58-69 for enum). 0006 reuses that pattern verbatim.

Package additions to server/requirements.txt:
- opentelemetry-sdk>=1.41,<2
- opentelemetry-exporter-otlp>=1.41,<2
- openinference-instrumentation-litellm>=0.1.33
- pyyaml>=6.0
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Write Alembic migration 0006 closing four Phase 2b schema gaps</name>
  <files>server/alembic/versions/0006_phase_2b_schema.py</files>
  <read_first>
    - server/alembic/versions/0003_phase_1c_vault.py (analog for op.add_column + op.alter_column + enum rename-and-recreate)
    - server/alembic/versions/0004_phase_1d_search_vector.py (most recent migration; this becomes `down_revision`)
    - server/app/models/link.py (current Link shape — confirm dst_entity_id is NOT NULL today)
    - server/app/models/conversation.py (current mcp_mode_enum values + Message column list)
    - server/app/models/golden_eval.py (current GoldenQuery column list)
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-RESEARCH.md (Schema Gaps section lines 476-518)
  </read_first>
  <action>
    Create `server/alembic/versions/0006_phase_2b_schema.py` with `revision = "0006"`, `down_revision = "0005"` (Phase 2a Wave 1 creates 0005; this stacks on top), `branch_labels = None`, `depends_on = None`. Module docstring header named `phase_2b_schema` describes the four gaps closed (use the bullet list from RESEARCH.md Schema Gaps). Use `from __future__ import annotations` and standard imports (`sqlalchemy as sa`, `from alembic import op`, `from collections.abc import Sequence`).

    `upgrade()` must perform EXACTLY these operations in this order:
      1. `op.add_column("links", sa.Column("anchor_text", sa.Text(), nullable=True))`
      2. `op.add_column("links", sa.Column("fragment", sa.Text(), nullable=True))`
      3. `op.add_column("links", sa.Column("target_text", sa.Text(), nullable=True))`
      4. `op.add_column("links", sa.Column("target_slug", sa.Text(), nullable=True))`
      5. `op.add_column("links", sa.Column("unresolved", sa.Boolean(), nullable=False, server_default=sa.text("false")))`
      6. `op.alter_column("links", "dst_entity_id", nullable=True)` (D-04 unresolved wikilinks; resolves RESEARCH Pitfall 1)
      7. Add unique constraint `uq_links_src_target_type` on `(src_page_id, target_text, link_type)` to support `ON CONFLICT DO UPDATE` upsert (PATTERNS.md services/graph.py upsert pattern; closes RESEARCH Pitfall 2)
      8. mcp_mode enum rename-and-recreate using the 0003 pattern (RESEARCH lines 81-95):
         - `op.execute("CREATE TYPE conversations_mcp_mode_enum_new AS ENUM ('disable', 'auto', 'manual')")`
         - `op.execute("ALTER TABLE conversations ADD COLUMN mcp_mode_new conversations_mcp_mode_enum_new NOT NULL DEFAULT 'disable'::conversations_mcp_mode_enum_new")`
         - `op.execute("ALTER TABLE conversations DROP COLUMN mcp_mode")`
         - `op.execute("ALTER TABLE conversations RENAME COLUMN mcp_mode_new TO mcp_mode")`
         - `op.execute("DROP TYPE conversations_mcp_mode_enum")`
         - `op.execute("ALTER TYPE conversations_mcp_mode_enum_new RENAME TO conversations_mcp_mode_enum")`
      9. `op.add_column("messages", sa.Column("token_usage", postgresql.JSONB(), nullable=True))` (use `sqlalchemy.dialects import postgresql`)
     10. `op.add_column("messages", sa.Column("model", sa.Text(), nullable=True))`
     11. `op.add_column("golden_queries", sa.Column("expected_top_slug", sa.Text(), nullable=True))`
     12. `op.add_column("golden_queries", sa.Column("expected_status", sa.String(64), nullable=True))`
     13. `op.add_column("golden_queries", sa.Column("expected_tool_first", sa.String(128), nullable=True))`
     14. `op.add_column("golden_queries", sa.Column("expected_edge_type", sa.String(128), nullable=True))`
     15. `op.add_column("golden_queries", sa.Column("notes", sa.Text(), nullable=True))`

    `downgrade()` must reverse in opposite order: drop the new golden_queries/messages/links columns; reverse the enum rename-and-recreate (recreate old enum disabled/client/server, ALTER column back, drop new); drop the unique constraint; restore `dst_entity_id` to NOT NULL (this requires the table contain no NULL rows, so downgrade must first DELETE rows WHERE dst_entity_id IS NULL — note this in a comment but include the SQL).

    DO NOT touch the `links_source_kind_enum`, RLS policies, or B-tree indexes — those exist in migration 0001 and remain unchanged.
  </action>
  <verify>
    <automated>cd server &amp;&amp; alembic upgrade head &amp;&amp; alembic check &amp;&amp; psql "$DATABASE_URL_TEST" -tAc "SELECT column_name, is_nullable FROM information_schema.columns WHERE table_name='links' AND column_name IN ('dst_entity_id','anchor_text','fragment','target_text','target_slug','unresolved') ORDER BY column_name" | grep -E "anchor_text\|YES|dst_entity_id\|YES|fragment\|YES|target_slug\|YES|target_text\|YES|unresolved\|NO"</automated>
  </verify>
  <acceptance_criteria>
    - File `server/alembic/versions/0006_phase_2b_schema.py` exists with `revision = "0006"` and `down_revision = "0005"`
    - File contains `op.add_column("links", sa.Column("unresolved", sa.Boolean(), nullable=False, server_default=sa.text("false")))`
    - File contains `op.alter_column("links", "dst_entity_id", nullable=True)`
    - File contains `CREATE TYPE conversations_mcp_mode_enum_new AS ENUM ('disable', 'auto', 'manual')`
    - File contains `op.add_column("messages", sa.Column("token_usage"` and `op.add_column("messages", sa.Column("model"`
    - File contains all five `op.add_column("golden_queries", ...)` calls
    - File contains `op.create_unique_constraint("uq_links_src_target_type", "links", ["src_page_id", "target_text", "link_type"])`
    - `alembic upgrade head` exits 0 against the test database from a clean state
    - `alembic check` exits 0 (no pending autogen diffs after model updates below)
    - `psql -c "SELECT enum_range(NULL::conversations_mcp_mode_enum)"` returns `{disable,auto,manual}` (or equivalent set)
  </acceptance_criteria>
  <done>Migration 0006 file exists, alembic upgrade succeeds, schema reflects all four gap closures (links columns, mcp_mode enum values, messages token_usage/model, golden_queries eval fields), and downgrade path exists.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Update SQLAlchemy models to match migration 0006</name>
  <files>server/app/models/link.py, server/app/models/conversation.py, server/app/models/golden_eval.py</files>
  <read_first>
    - server/app/models/link.py (full current shape — must keep id/src_page_id/link_type/confidence/source_kind/TimestampMixin)
    - server/app/models/conversation.py (full current shape — mcp_mode_enum, Conversation, Message)
    - server/app/models/golden_eval.py (full current shape — GoldenQuerySuite, GoldenQuery, GoldenQueryRun)
    - server/app/models/entity.py (analog for ARRAY/JSONB column declaration patterns)
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-PATTERNS.md (Pattern Assignments §link.py and §conversation.py and §golden_eval.py)
  </read_first>
  <action>
    Modify `server/app/models/link.py`:
      - Change `dst_entity_id` mapped_column to `nullable=True` (D-04). Update annotation to `Mapped[uuid.UUID | None]`.
      - Add new mapped_columns after `source_kind`:
        - `anchor_text: Mapped[str | None] = mapped_column(Text, nullable=True)`
        - `fragment: Mapped[str | None] = mapped_column(Text, nullable=True)`
        - `target_text: Mapped[str | None] = mapped_column(Text, nullable=True)`
        - `target_slug: Mapped[str | None] = mapped_column(Text, nullable=True)`
        - `unresolved: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")`
      - Add the `Text` and `Boolean` imports to the existing `from sqlalchemy import ...` line.
      - Update the module docstring: append a one-line note "Phase 2b: unresolved wikilinks (D-04) supported via target_slug + unresolved fields."

    Modify `server/app/models/conversation.py`:
      - Replace mcp_mode_enum values `"disabled", "client", "server"` with `"disable", "auto", "manual"` (keep `name="conversations_mcp_mode_enum"` and `create_constraint=True`).
      - Change `Conversation.mcp_mode` server_default from `"client"` to `"disable"`.
      - Add new mapped_columns to `Message` class after `tool_calls`:
        - `token_usage: Mapped[dict | None] = mapped_column(JSONB, nullable=True)`
        - `model: Mapped[str | None] = mapped_column(Text, nullable=True)`
      - JSONB and Text imports already present.

    Modify `server/app/models/golden_eval.py`:
      - Add new mapped_columns to `GoldenQuery` class after `tags`:
        - `expected_top_slug: Mapped[str | None] = mapped_column(Text, nullable=True)`
        - `expected_status: Mapped[str | None] = mapped_column(String(64), nullable=True)`
        - `expected_tool_first: Mapped[str | None] = mapped_column(String(128), nullable=True)`
        - `expected_edge_type: Mapped[str | None] = mapped_column(String(128), nullable=True)`
        - `notes: Mapped[str | None] = mapped_column(Text, nullable=True)`
      - String and Text imports already present.

    Run `alembic check` after editing — must return zero diffs (model matches migration head).
  </action>
  <verify>
    <automated>grep -c "anchor_text\|fragment\|target_text\|target_slug\|unresolved" server/app/models/link.py | grep -v '^0$' &amp;&amp; grep -c "\"disable\"\|\"auto\"\|\"manual\"" server/app/models/conversation.py | grep -v '^0$' &amp;&amp; grep -c "token_usage\|expected_top_slug" server/app/models/conversation.py server/app/models/golden_eval.py | grep -v ':0$' &amp;&amp; cd server &amp;&amp; alembic check</automated>
  </verify>
  <acceptance_criteria>
    - `grep -v '^#' server/app/models/link.py | grep -c "anchor_text"` is at least 1
    - `grep -v '^#' server/app/models/link.py | grep -c "nullable=True"` matches dst_entity_id Mapped declaration (verify by `grep -A2 'dst_entity_id' server/app/models/link.py` showing `nullable=True`)
    - `grep -v '^#' server/app/models/conversation.py | grep -c '"disable"'` ≥ 1 AND `grep -c '"disabled"' server/app/models/conversation.py` = 0
    - `grep -v '^#' server/app/models/conversation.py | grep -c "token_usage"` ≥ 1
    - `grep -v '^#' server/app/models/conversation.py | grep -c "JSONB.*token_usage\|token_usage.*JSONB"` ≥ 1
    - `grep -v '^#' server/app/models/golden_eval.py | grep -c "expected_top_slug\|expected_status\|expected_tool_first\|expected_edge_type"` ≥ 4
    - `cd server && alembic check` exits 0 (no autogen diffs — model matches migration head)
    - `cd server && python -c "from app.models.link import Link; from app.models.conversation import Conversation, Message; from app.models.golden_eval import GoldenQuery"` imports succeed with no errors
  </acceptance_criteria>
  <done>All three model files updated to match migration 0006; alembic check returns zero diffs; model imports succeed without errors.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Pin Phase 2b OpenTelemetry + pyyaml dependencies in requirements.txt</name>
  <files>server/requirements.txt</files>
  <read_first>
    - server/requirements.txt (current pinned set — verify litellm pin from Phase 2a may already be present; do not duplicate)
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-RESEARCH.md (Standard Stack §New + Package Legitimacy Audit lines 148-163)
  </read_first>
  <action>
    Append to `server/requirements.txt` (alphabetically grouped at end of file, preserve existing pins, do NOT remove any line):
      - `opentelemetry-sdk>=1.41,<2`
      - `opentelemetry-exporter-otlp>=1.41,<2`
      - `openinference-instrumentation-litellm>=0.1.33`
      - `pyyaml>=6.0`

    These four packages are listed as `[ASSUMED — PyPI verified]` in RESEARCH §Package Legitimacy Audit. They are NOT confirmed via Context7 or slopcheck (slopcheck cannot evaluate Python packages — see RESEARCH lines 159-163). The downstream legitimacy checkpoint task in Plan 02B-05 task 0 (the legitimacy checkpoint) is the required human gate before any install instruction is executed in CI.

    Do NOT add `litellm` here — it is added by Phase 2a (02A-01-PLAN or 02A-02-PLAN). If `grep -c "^litellm" server/requirements.txt` returns 0 when Phase 2b execution starts, that is a Phase 2a gap that must be reported back to the orchestrator, not silently fixed here.

    Do NOT remove the existing `pyyaml` line if one already exists at a lower version — instead bump it. If the file already has `pyyaml==5.4.1` or similar, replace that line with `pyyaml>=6.0`.
  </action>
  <verify>
    <automated>grep -v '^#' server/requirements.txt | grep -c "^opentelemetry-sdk" | grep -v '^0$' &amp;&amp; grep -v '^#' server/requirements.txt | grep -c "^opentelemetry-exporter-otlp" | grep -v '^0$' &amp;&amp; grep -v '^#' server/requirements.txt | grep -c "^openinference-instrumentation-litellm" | grep -v '^0$' &amp;&amp; grep -v '^#' server/requirements.txt | grep -c "^pyyaml" | grep -v '^0$'</automated>
  </verify>
  <acceptance_criteria>
    - `grep -v '^#' server/requirements.txt | grep -c '^opentelemetry-sdk>=1.41'` ≥ 1
    - `grep -v '^#' server/requirements.txt | grep -c '^opentelemetry-exporter-otlp>=1.41'` ≥ 1
    - `grep -v '^#' server/requirements.txt | grep -c '^openinference-instrumentation-litellm>=0.1.33'` ≥ 1
    - `grep -v '^#' server/requirements.txt | grep -c '^pyyaml>=6'` ≥ 1
    - `grep -v '^#' server/requirements.txt | grep -c '^pyyaml==5'` = 0 (no stale pyyaml 5.x pin)
    - `grep -v '^#' server/requirements.txt | grep -c '^litellm'` ≥ 1 OR the executor surfaces a "Phase 2a gap: litellm missing from requirements.txt" warning to the orchestrator
  </acceptance_criteria>
  <done>requirements.txt contains the four new pins; pyyaml is at >=6.0; litellm presence from Phase 2a is verified (or gap reported).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| migration ↔ database | Migration runs as superuser-equivalent; must not weaken existing RLS or constraints |
| model ↔ migration | Schema drift between models and migration creates silent runtime failures |
| package install ↔ supply chain | `[ASSUMED]` packages enter the install path here; not yet human-verified |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02B-01-01 | Tampering | links.dst_entity_id nullable change | mitigate | Add UNIQUE constraint on (src_page_id, target_text, link_type) so unresolved-link inserts cannot duplicate; CHECK semantics enforced at app layer via Pydantic validation (Plan 03 owns) |
| T-02B-01-02 | Denial of Service | mcp_mode enum rename-and-recreate | mitigate | Migration runs inside a transaction (Alembic default); aborted upgrade rolls back enum + column atomically; default `disable` chosen so existing rows stay closed (least privilege) |
| T-02B-01-03 | Information Disclosure | messages.token_usage / messages.model | accept | New columns are nullable; no PII directly. token_usage is per-request stats; model name is provider-public. RLS on messages table (Phase 1b) already isolates per-user |
| T-02B-01-04 | Repudiation | golden_queries.expected_* fields | accept | Eval-only metadata; never user-facing data; per-user RLS already enforced via suite scope (Phase 1a migration 0001) |
| T-02B-01-SC | Tampering | opentelemetry-sdk + opentelemetry-exporter-otlp + openinference-instrumentation-litellm + pyyaml (PyPI installs) | mitigate | slopcheck cannot evaluate PyPI; all four tagged `[ASSUMED]` in RESEARCH §Package Legitimacy Audit. Plan 02B-05 (agent core, Wave 3) contains the blocking-human checkpoint that verifies each package on pypi.org before `pip install` executes in CI. This plan only ADDS pins to requirements.txt; no install happens during this plan |
</threat_model>

<verification>
- `alembic upgrade head` and `alembic check` both succeed against a clean test database
- All three model files import cleanly (`python -c "from app.models.link import Link"` etc.)
- requirements.txt contains the four new pins and the pyyaml pin is >=6.0
- No existing migration is modified; no existing model field is removed (only added/altered)
</verification>

<success_criteria>
- Migration 0006 exists, applies cleanly, and is reversible
- Link, Conversation/Message, and GoldenQuery models reflect the new schema
- `alembic check` reports zero diffs after model + migration updates
- `requirements.txt` has the four new pinned packages
- No downstream plan in Phase 2b is blocked by missing schema or missing models
</success_criteria>

<output>
Create `.planning/phases/02B-knowledge-graph-agent-runner/02B-01-SUMMARY.md` when done. Record: migration revision id, list of columns added per table, mcp_mode enum old→new mapping, list of packages added.
</output>
