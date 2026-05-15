---
phase: 02A
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - server/pyproject.toml
  - server/requirements.txt
  - server/app/settings.py
  - server/alembic/versions/0005_phase_2a_rag.py
  - server/app/models/page.py
  - server/app/models/chunk.py
  - server/app/tests/conftest.py
  - server/app/tests/llm/__init__.py
  - server/app/tests/llm/test_router.py
  - server/app/tests/llm/test_keys.py
  - server/app/tests/rag/__init__.py
  - server/app/tests/rag/test_chunker.py
  - server/app/tests/rag/test_embedder.py
  - server/app/tests/rag/test_retriever.py
  - server/app/tests/rag/test_reranker.py
  - server/app/tests/rag/test_intent.py
  - server/app/tests/rag/test_search_fallback.py
  - server/app/tests/routes/__init__.py
  - server/app/tests/routes/test_migration.py
  - server/app/tests/integration/test_phase_2a_acceptance.py
autonomous: true
requirements: [LLM-01, RAG-06]
tags: [rag, phase-2a, foundation, settings, alembic, ruff-tid, test-scaffold]

must_haves:
  truths:
    - "Importing `litellm` (or `litellm.acompletion`, `litellm.aembedding`, `litellm.completion`, `litellm.embedding`) from any module other than `app/llm/router.py`, `app/llm/tiers.py`, or `app/llm/keys.py` fails Ruff lint with rule TID251"
    - "Settings exposes `rrf_k` (default 60, clamp [10,200]), `truth_boost` (default 0.15, clamp [0.0,0.5]), `stale_days` (default 30, clamp [1,365]), `llm_tier_cheap`, `llm_tier_balanced`, `llm_tier_strong` env-var driven values"
    - "`pages` table has `compiled_truth_updated_at TIMESTAMPTZ NULL` and `latest_timeline_ts TIMESTAMPTZ NULL` columns after migration 0005"
    - "`chunks` table has `chunk_index INTEGER NOT NULL DEFAULT 0` column after migration 0005 (used by D-14 dedup key)"
    - "All Wave 0 test files exist and import the symbols they will exercise (xfail/skip stubs allowed) so downstream plans satisfy Nyquist verify requirement"
  artifacts:
    - path: "server/pyproject.toml"
      provides: "Ruff TID251 banned-api for litellm + per-file-ignores for llm/ submodule + pytest markers `rag` and `llm`"
      contains: "TID"
    - path: "server/requirements.txt"
      provides: "Pins for litellm>=1.40,<2.0 and tiktoken>=0.7"
      contains: "litellm"
    - path: "server/app/settings.py"
      provides: "rrf_k, truth_boost, stale_days, llm_tier_cheap/balanced/strong fields with clamp+warn validators"
      contains: "rrf_k"
    - path: "server/alembic/versions/0005_phase_2a_rag.py"
      provides: "Migration adding pages.compiled_truth_updated_at, pages.latest_timeline_ts, chunks.chunk_index"
      contains: "compiled_truth_updated_at"
    - path: "server/app/models/page.py"
      provides: "Page model exposing compiled_truth_updated_at and latest_timeline_ts ORM attributes"
      contains: "compiled_truth_updated_at"
    - path: "server/app/models/chunk.py"
      provides: "Chunk model exposing chunk_index ORM attribute"
      contains: "chunk_index"
    - path: "server/app/tests/rag/test_chunker.py"
      provides: "Wave 0 RAG-01 test scaffold"
      contains: "pytest.mark.rag"
    - path: "server/app/tests/llm/test_router.py"
      provides: "Wave 0 LLM-01/02/03 test scaffold"
      contains: "pytest.mark.llm"
  key_links:
    - from: "server/app/settings.py"
      to: "server/app/rag/reranker.py (Plan 04)"
      via: "settings.rrf_k, settings.truth_boost, settings.stale_days import"
      pattern: "from app.settings import settings"
    - from: "server/pyproject.toml"
      to: "All non-router/non-tiers/non-keys modules"
      via: "Ruff CLI TID251 check"
      pattern: "ruff check"
    - from: "server/alembic/versions/0005_phase_2a_rag.py"
      to: "server/app/rag/reranker.py is_stale() (Plan 04)"
      via: "pages.compiled_truth_updated_at and pages.latest_timeline_ts columns referenced by stale annotation SQL"
      pattern: "compiled_truth_updated_at"
---

<objective>
Lay the Phase 2a foundation in a single autonomous wave: install the LiteLLM/tiktoken pins (RESEARCH §Standard Stack), extend `Settings` with the env-var configurable RRF/tier knobs locked by CONTEXT D-13, add the Alembic migration that supplies the columns required by stale annotation (D-13) and chunk-index dedup key (D-14), wire the Ruff TID251 banned-api rule that enforces RAG-06 across the codebase, and author the Wave 0 test scaffolds so downstream plans have failing tests to make green.

Purpose: Plans 02..05 must not touch settings, the database schema, the Ruff config, or the test layout. By front-loading every cross-cutting change here, Waves 2–5 can run as focused, deterministic implementation work without revisiting infrastructure.

Output: Migration 0005, updated `settings.py`, updated `pyproject.toml` (Ruff + pytest markers), updated `requirements.txt`, updated `Page`/`Chunk` ORM models, and 11 test files (10 stubs + 1 conftest extension) covering every Phase 2a requirement at xfail/skip level.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-CONTEXT.md
@.planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-RESEARCH.md
@.planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-PATTERNS.md
@.planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-AI-SPEC.md

<interfaces>
<!-- Settings pattern executors should match -->

From server/app/settings.py (current Settings class — extend, do not rewrite):
- `Settings(BaseSettings)` with `model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)`
- Existing fields use `Field(default=...)` and `@field_validator` decorators (see `validate_fernet_key` for the clamp+warn pattern Plan 01 must mirror for `rrf_k`, `truth_boost`, `stale_days`).
- Module-level singleton: `settings = Settings()`

From server/alembic/versions/0004_phase_1d_search_vector.py (predecessor migration — read for revision id chain + `op.add_column` style):
- `revision: str = "0004_phase_1d_search_vector"`
- `down_revision: str = "0003_phase_1c_vault"` style
- Use `op.add_column("table", sa.Column(...))` and `op.execute("...")` for raw SQL.

From server/app/models/page.py (current Page — extend, do not rewrite):
- `class Page(Base, TimestampMixin)` already has `compiled_truth`, `timeline`, `content_hash`, `enrichment_hash`. Add `compiled_truth_updated_at: Mapped[datetime | None]` and `latest_timeline_ts: Mapped[datetime | None]` columns.

From server/app/models/chunk.py (current Chunk — extend, do not rewrite):
- `class Chunk(Base, TimestampMixin)` already has `id`, `page_id`, `kind`, `text`, `enriched_content`, `tsv`, `embedding`. Add `chunk_index: Mapped[int]` with default 0.

From server/pyproject.toml (current Ruff block — extend, do not rewrite):
- `[tool.ruff.lint] select = ["E", "F", "UP", "B", "I"]` → add `"TID"`.
- `[tool.ruff.lint.per-file-ignores]` already covers `alembic/versions/*.py`, `app/tests/**/*.py`, `app/models/*.py`. Plan adds three lines for `app/llm/router.py`, `app/llm/tiers.py`, `app/llm/keys.py`.
- `[tool.pytest.ini_options] markers = [...]` already contains `integration`, `unit`, `auth`, `vault`. Plan extends with `rag` and `llm`.

From server/app/tests/conftest.py (existing global conftest — extend if needed; do not duplicate testcontainers wiring):
- Plan 01 only adds an empty `server/app/tests/rag/__init__.py` and `server/app/tests/llm/__init__.py` plus `server/app/tests/routes/__init__.py` (if missing) — the global testcontainers `db_session`/`seed_user` fixtures are reused as-is.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Settings extension + Ruff TID gate + requirements pin</name>
  <files>server/app/settings.py, server/pyproject.toml, server/requirements.txt</files>
  <read_first>
    - server/app/settings.py (current Settings class; mirror `validate_fernet_key` clamp+warn pattern)
    - server/pyproject.toml (current `[tool.ruff.lint]`, `[tool.ruff.lint.per-file-ignores]`, `[tool.pytest.ini_options]` blocks)
    - server/requirements.txt (current pin format; preserve existing line ordering)
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-CONTEXT.md (D-13 clamp ranges)
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-RESEARCH.md (Pattern 7 Ruff TID config; Standard Stack pin versions)
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-PATTERNS.md (`server/app/llm/tiers.py` section showing Settings field block format)
  </read_first>
  <behavior>
    - settings.rrf_k clamps out-of-range int input to [10, 200] and emits a UserWarning identifying the original value and clamped value
    - settings.truth_boost clamps out-of-range float input to [0.0, 0.5] with the same UserWarning shape
    - settings.stale_days clamps out-of-range int input to [1, 365] with the same UserWarning shape
    - settings.llm_tier_cheap defaults to "openai/gpt-4o-mini"; llm_tier_balanced defaults to "anthropic/claude-sonnet-4-5"; llm_tier_strong defaults to "openai/o3"
    - `ruff check server/app/` exits 0 with `select = [..., "TID"]` because no non-router module yet imports litellm
    - `ruff check server/app/llm/router.py` would NOT raise TID251 once Plan 02 creates that file (per-file-ignores covers it)
  </behavior>
  <action>
    In `server/app/settings.py`, append (do not rewrite) a new "## --- Phase 2a: LLM Gateway + Hybrid RAG ---" comment section after the existing Phase 1d block. Add six fields to the `Settings` class: `rrf_k: int = Field(default=60, validation_alias="SMARTCOPILOT_RRF_K")`, `truth_boost: float = Field(default=0.15, validation_alias="SMARTCOPILOT_TRUTH_BOOST")`, `stale_days: int = Field(default=30, validation_alias="SMARTCOPILOT_STALE_DAYS")`, `llm_tier_cheap: str = Field(default="openai/gpt-4o-mini")`, `llm_tier_balanced: str = Field(default="anthropic/claude-sonnet-4-5")`, `llm_tier_strong: str = Field(default="openai/o3")`. Add three `@field_validator("rrf_k")`, `@field_validator("truth_boost")`, `@field_validator("stale_days")` classmethods that clamp to the ranges in `<behavior>` and emit `warnings.warn(...)` (mirror `validate_fernet_key` UserWarning shape). Tier fields do not need validators.

    In `server/pyproject.toml`, modify `[tool.ruff.lint]` to read `select = ["E", "F", "UP", "B", "I", "TID"]`. Add a new `[tool.ruff.lint.flake8-tidy-imports.banned-api]` section with exactly five entries (per RESEARCH Pattern 7): `"litellm"`, `"litellm.completion"`, `"litellm.acompletion"`, `"litellm.embedding"`, `"litellm.aembedding"` — each with a `msg` field pointing callers to `app.llm.router`. Extend `[tool.ruff.lint.per-file-ignores]` with three lines: `"app/llm/router.py" = ["TID251"]`, `"app/llm/tiers.py" = ["TID251"]`, `"app/llm/keys.py" = ["TID251"]`. Extend `[tool.pytest.ini_options].markers` array with two new entries: `"rag: Phase 2a RAG pipeline tests (covers RAG-01..07)"` and `"llm: Phase 2a LLM router + cost tracking tests (covers LLM-01..05)"` — preserve all existing markers verbatim.

    In `server/requirements.txt`, add two pinned lines after the existing `pgvector>=0.3` line: `litellm>=1.40,<2.0` and `tiktoken>=0.7`. Preserve all other lines and ordering.
  </action>
  <verify>
    <automated>cd server && python -c "from app.settings import settings; assert settings.rrf_k == 60 and settings.truth_boost == 0.15 and settings.stale_days == 30 and settings.llm_tier_cheap.startswith('openai/') and settings.llm_tier_balanced.startswith('anthropic/') and settings.llm_tier_strong, 'settings RAG fields missing or wrong defaults'" && cd server && python -c "import warnings; warnings.filterwarnings('error'); import os; os.environ['SMARTCOPILOT_RRF_K']='5'; from importlib import reload; import app.settings as s; reload(s); assert s.settings.rrf_k == 10, 'clamp did not engage'" 2>&1 | grep -v "Warning" || cd server && SMARTCOPILOT_RRF_K=5 python -c "from app.settings import Settings; s = Settings(); assert s.rrf_k == 10" && cd server && ruff check --select TID app/ 2>&1 | tee /tmp/ruff.log && grep -q "TID" /tmp/ruff.log -v && grep -E "^litellm>=1\.40" server/requirements.txt && grep -E "^tiktoken>=" server/requirements.txt</automated>
  </verify>
  <acceptance_criteria>
    - `server/app/settings.py` contains `rrf_k:` `truth_boost:` `stale_days:` `llm_tier_cheap:` `llm_tier_balanced:` `llm_tier_strong:` definitions
    - `server/app/settings.py` contains three new `@field_validator` decorators for `rrf_k`, `truth_boost`, `stale_days`
    - `SMARTCOPILOT_RRF_K=300 python -c "from app.settings import Settings; s=Settings(); assert s.rrf_k==200"` exits 0 (upper clamp)
    - `SMARTCOPILOT_TRUTH_BOOST=-0.1 python -c "from app.settings import Settings; s=Settings(); assert s.truth_boost==0.0"` exits 0 (lower clamp)
    - `server/pyproject.toml` contains `"TID"` inside the `select` array under `[tool.ruff.lint]`
    - `server/pyproject.toml` contains `[tool.ruff.lint.flake8-tidy-imports.banned-api]` section with exactly five entries matching `"litellm"`, `"litellm.completion"`, `"litellm.acompletion"`, `"litellm.embedding"`, `"litellm.aembedding"`
    - `server/pyproject.toml` `[tool.ruff.lint.per-file-ignores]` contains `"app/llm/router.py" = ["TID251"]`, `"app/llm/tiers.py" = ["TID251"]`, `"app/llm/keys.py" = ["TID251"]`
    - `server/pyproject.toml` `[tool.pytest.ini_options].markers` contains lines whose first colon-separated token equals `rag` and `llm`
    - `server/requirements.txt` contains exact pin `litellm>=1.40,<2.0`
    - `server/requirements.txt` contains pin starting `tiktoken>=0.7`
    - `cd server && ruff check --select TID app/` exits 0 (no pre-existing direct litellm imports in tree before Plan 02 creates router)
  </acceptance_criteria>
  <done>
    Settings extended with six locked Phase 2a fields and three clamp+warn validators. Ruff TID251 banned-api rule active with five litellm targets and three per-file-ignores. Requirements file pins litellm and tiktoken. pytest gains `rag` and `llm` markers. Existing tests still pass.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Alembic 0005 migration + ORM column extensions</name>
  <files>server/alembic/versions/0005_phase_2a_rag.py, server/app/models/page.py, server/app/models/chunk.py</files>
  <read_first>
    - server/alembic/versions/0004_phase_1d_search_vector.py (predecessor revision id chain; `op.add_column` style)
    - server/alembic/versions/0003_phase_1c_vault.py (last migration to touch `pages` table; replicate timestamp column style)
    - server/app/models/page.py (current Page columns; preserve TimestampMixin ordering)
    - server/app/models/chunk.py (current Chunk columns; preserve `tsv` Computed clause; chunk_index goes before `tsv` column)
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-RESEARCH.md (Migration Considerations section, A1/A2 assumptions confirming columns are missing)
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-PATTERNS.md (Model Observations section confirming `note_type` not `page_type`)
  </read_first>
  <behavior>
    - Running `alembic upgrade head` after this plan applies cleanly: `pages.compiled_truth_updated_at`, `pages.latest_timeline_ts`, `chunks.chunk_index` all exist
    - `alembic downgrade -1` from 0005 to 0004 drops those three columns and leaves the schema in the same state as before
    - `from app.models.page import Page; Page.compiled_truth_updated_at` resolves to a Mapped[datetime | None] attribute
    - `from app.models.chunk import Chunk; Chunk.chunk_index` resolves to a Mapped[int] attribute with default 0
    - Existing `pages` rows retain `NULL` in the two new columns; existing `chunks` rows receive default `0` for `chunk_index`
  </behavior>
  <action>
    Create `server/alembic/versions/0005_phase_2a_rag.py` with `revision = "0005_phase_2a_rag"`, `down_revision = "0004_phase_1d_search_vector"`. In `upgrade()`: `op.add_column("pages", sa.Column("compiled_truth_updated_at", sa.DateTime(timezone=True), nullable=True))`; `op.add_column("pages", sa.Column("latest_timeline_ts", sa.DateTime(timezone=True), nullable=True))`; `op.add_column("chunks", sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"))`. In `downgrade()`: drop the three columns in reverse order. Do NOT add indexes — stale annotation reads denormalized columns directly and chunk_index dedup is in-process. Do NOT touch the HNSW/GIN indexes (already in 0001).

    Extend `server/app/models/page.py` Page class: add `compiled_truth_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)` and `latest_timeline_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)` immediately after `enrichment_hash` and before the soft-delete columns. Preserve the TimestampMixin inheritance order.

    Extend `server/app/models/chunk.py` Chunk class: add `chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")` immediately after `page_id` and before `kind`. Import `Integer` from sqlalchemy if not already imported.
  </action>
  <verify>
    <automated>cd server && alembic upgrade head && python -c "from sqlalchemy import inspect; from app.database import engine; import asyncio; cols = asyncio.run(engine.connect().__aenter__().run_sync(lambda c: [r['name'] for r in inspect(c).get_columns('pages')])); assert 'compiled_truth_updated_at' in cols and 'latest_timeline_ts' in cols, f'pages missing columns: {cols}'" 2>&1 | tail -5 && cd server && python -c "from app.models.page import Page; from app.models.chunk import Chunk; assert hasattr(Page, 'compiled_truth_updated_at') and hasattr(Page, 'latest_timeline_ts') and hasattr(Chunk, 'chunk_index')" && cd server && alembic downgrade -1 && alembic upgrade head</automated>
  </verify>
  <acceptance_criteria>
    - `server/alembic/versions/0005_phase_2a_rag.py` exists
    - File contains `revision = "0005_phase_2a_rag"` and `down_revision = "0004_phase_1d_search_vector"`
    - `upgrade()` body calls `op.add_column("pages", ...)` twice and `op.add_column("chunks", ...)` once
    - `downgrade()` body calls `op.drop_column` three times in reverse order
    - `server/app/models/page.py` source contains `compiled_truth_updated_at: Mapped[datetime | None]` and `latest_timeline_ts: Mapped[datetime | None]`
    - `server/app/models/chunk.py` source contains `chunk_index: Mapped[int]` and `Integer` is imported from sqlalchemy
    - `cd server && alembic upgrade head` exits 0 against the project's test database (CI runs against testcontainers pgvector/pg16)
    - `cd server && python -c "from app.models.page import Page; from app.models.chunk import Chunk; assert hasattr(Page,'compiled_truth_updated_at') and hasattr(Page,'latest_timeline_ts') and hasattr(Chunk,'chunk_index')"` exits 0
  </acceptance_criteria>
  <done>
    Migration 0005 created and applies cleanly on top of 0004. ORM models updated to expose the three new columns. Downgrade reverses cleanly. Reranker (Plan 04) can read the new stale-annotation columns; embedder/chunker (Plan 03) can write chunk_index.
  </done>
</task>

<task type="auto">
  <name>Task 3: Wave 0 test scaffolds for every Phase 2a requirement</name>
  <files>server/app/tests/llm/__init__.py, server/app/tests/llm/test_router.py, server/app/tests/llm/test_keys.py, server/app/tests/rag/__init__.py, server/app/tests/rag/test_chunker.py, server/app/tests/rag/test_embedder.py, server/app/tests/rag/test_retriever.py, server/app/tests/rag/test_reranker.py, server/app/tests/rag/test_intent.py, server/app/tests/rag/test_search_fallback.py, server/app/tests/routes/__init__.py, server/app/tests/routes/test_migration.py, server/app/tests/integration/test_phase_2a_acceptance.py</files>
  <read_first>
    - server/app/tests/conftest.py (existing global fixtures: `db_session`, `seed_user`)
    - server/app/tests/vault/test_parser.py (pure-transform unit test analog for chunker/intent/reranker)
    - server/app/tests/integration/test_phase_1d_acceptance.py (phase acceptance test structure)
    - server/app/tests/integration/test_search_route.py (existing search route integration test — Phase 2a acceptance test follows same shape)
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-RESEARCH.md (Validation Architecture table for the exact test cases each file must cover)
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-VALIDATION.md (per-task verification map)
  </read_first>
  <behavior>
    - Every test file imports the symbols it will exercise behind a `pytest.importorskip` or `try/except ImportError + pytestmark = pytest.mark.skip(reason="Wave N awaiting Plan NN")` so the collection step succeeds today
    - Each test file has at least one `xfail`-marked or `skip`-marked test stub per requirement listed in its RESEARCH.md row, naming the requirement in the docstring (e.g., `"""LLM-02: tier resolution returns model id"""`)
    - `pytest server/app/tests/llm/ server/app/tests/rag/ server/app/tests/routes/test_migration.py server/app/tests/integration/test_phase_2a_acceptance.py --collect-only` exits 0
    - Running `pytest -m "rag or llm" -q` exits 0 (all stubs are skipped/xfailed; nothing actually runs yet)
  </behavior>
  <action>
    Create all 13 files listed in `<files>`. The two `__init__.py` files (`tests/llm/`, `tests/rag/`) are empty. `tests/routes/__init__.py` is empty if missing.

    Each test file uses this exact skeleton (substitute requirement IDs and import target per RESEARCH.md Validation Architecture table):

    ```
    """Phase 2a {requirement IDs} — Wave 0 scaffold authored by Plan 01."""
    from __future__ import annotations

    import pytest

    pytestmark = [pytest.mark.{rag|llm}, pytest.mark.{unit|integration}]

    try:
        from app.{module path} import {symbol}  # noqa: F401
    except ImportError:
        pytestmark.append(pytest.mark.skip(reason="Plan {NN} authors {module path}"))


    @pytest.mark.xfail(reason="Plan {NN} implements {requirement ID}")
    def test_{requirement_id_lowercased}_{behavior_short}():
        """{REQ-ID}: {behavior}."""
        raise NotImplementedError
    ```

    Specific mappings (one test stub per row from RESEARCH §Validation Architecture):
    - `tests/llm/test_router.py` (markers: llm, unit) — import `from app.llm.router import llm_complete`; stubs for LLM-01, LLM-02, LLM-03, LLM-04
    - `tests/llm/test_keys.py` (markers: llm, unit) — import `from app.llm.keys import resolve_api_key`; stub for LLM-05
    - `tests/rag/test_chunker.py` (markers: rag, unit) — import `from app.rag.chunker import split_into_chunks, should_skip_page`; stubs for RAG-01 (kind=truth, kind=event, kind=summary, skip archived_fleeting, skip skill)
    - `tests/rag/test_embedder.py` (markers: rag, unit) — import `from app.rag.embedder import embed_batch`; stubs for RAG-02 (1536-dim assert, dimension mismatch raises)
    - `tests/rag/test_retriever.py` (markers: rag, integration) — import `from app.rag.retriever import vector_search, bm25_search`; stubs for RAG-03 (BM25), and vector ANN smoke
    - `tests/rag/test_reranker.py` (markers: rag, unit) — import `from app.rag.reranker import rrf_score, is_stale, dedup_results`; stubs for RAG-04 (RRF formula, truth boost), RAG-05 (4-layer dedup, stale annotation)
    - `tests/rag/test_intent.py` (markers: rag, unit) — import `from app.rag.intent import classify_intent, expand_query`; stubs for RAG-05 (rule-based classifier, D-07 — `[[Entity]]` → graph, `@web` → web_stub, ≥6 words → expand=True, short query → expand=False)
    - `tests/rag/test_search_fallback.py` (markers: rag, integration) — import `from app.services.search import hybrid_search`; stub for RAG-05 cold-start (HNSW empty → search_type=fts_v1)
    - `tests/routes/test_migration.py` (markers: rag, integration) — import `from app.routes.migration import router`; stubs for RAG-07 estimate/start/status/cancel
    - `tests/integration/test_phase_2a_acceptance.py` (markers: rag, integration) — imports as needed; one stub `test_acceptance_brain_search_returns_hybrid_v1` covering SC-2a

    Total stubs: 4 (router) + 1 (keys) + 5 (chunker) + 2 (embedder) + 2 (retriever) + 4 (reranker) + 4 (intent) + 1 (fallback) + 4 (migration) + 1 (acceptance) = 28 xfail/skip stubs. Downstream plans flip xfail → real assertion.
  </action>
  <verify>
    <automated>cd server && pytest --collect-only app/tests/llm/ app/tests/rag/ app/tests/routes/test_migration.py app/tests/integration/test_phase_2a_acceptance.py 2>&1 | tail -10 && cd server && pytest -m "rag or llm" -q --no-header 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - All 13 files in `<files>` exist
    - `server/app/tests/llm/__init__.py`, `server/app/tests/rag/__init__.py`, `server/app/tests/routes/__init__.py` are empty or contain only a docstring
    - Each non-init test file contains the literal string `pytestmark = [pytest.mark.` followed by either `rag` or `llm`
    - Each non-init test file contains at least one `@pytest.mark.xfail` or `pytest.mark.skip` decorator
    - `cd server && pytest --collect-only app/tests/llm/ app/tests/rag/ app/tests/routes/test_migration.py app/tests/integration/test_phase_2a_acceptance.py` exits 0
    - `cd server && pytest -m "rag or llm" -q` exits 0 (all stubs are xfail/skip; net result is green)
    - `grep -c "REQ-\|RAG-\|LLM-\|SC-2a" server/app/tests/llm/*.py server/app/tests/rag/*.py server/app/tests/routes/test_migration.py server/app/tests/integration/test_phase_2a_acceptance.py | awk -F: '{s+=$2} END {print s}'` ≥ 12 (every requirement docstring referenced at least once)
  </acceptance_criteria>
  <done>
    Twenty-eight Wave 0 stubs across 10 test files exist; pytest collects them without error and reports them as xfail/skip. Downstream plans (02 LLM router, 03 chunker/embedder, 04 retriever/reranker/intent/search, 05 migration) have failing tests waiting to be flipped to passing as their real code lands. Phase 2a acceptance test stub exists for the final Wave 5 wire-up.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Plan author → Settings constants | Out-of-range env var values must be clamped at startup, not at call site (D-13) |
| Plan author → Ruff CI gate | Any future module importing `litellm` directly bypasses cost tracking and key injection unless TID251 blocks it |
| Migration author → live database | New columns must default to nullable / nullable-with-server-default so existing rows survive without backfill |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02A-01-01 | Tampering | `Settings.rrf_k`, `Settings.truth_boost`, `Settings.stale_days` | mitigate | clamp validators reject out-of-range integers/floats and emit `UserWarning` so operators see misconfigurations at startup; out-of-range value is silently corrected to the boundary instead of being honoured |
| T-02A-01-02 | Elevation of Privilege | RAG-06 router choke-point | mitigate | Ruff TID251 banned-api fails CI on any direct `litellm` / `litellm.acompletion` / `litellm.aembedding` / `litellm.completion` / `litellm.embedding` import outside `app/llm/{router,tiers,keys}.py`; CI gate blocks merge |
| T-02A-01-03 | Tampering | Alembic 0005 column adds | mitigate | New columns are nullable (`pages.compiled_truth_updated_at`, `pages.latest_timeline_ts`) or have `server_default="0"` (`chunks.chunk_index`) so the migration is reversible and does not corrupt existing data |
| T-02A-01-SC | Tampering | npm/pip/cargo installs | mitigate | RESEARCH §Package Legitimacy Audit verified `litellm`, `tiktoken`, `pgvector`, `apscheduler` against PyPI; all four marked Approved; no `[ASSUMED]`/`[SUS]`/`[SLOP]` requires per-package checkpoint |
</threat_model>

<verification>
- Full server test suite passes: `cd server && pytest app/tests/ -q`
- Ruff full-tree clean: `cd server && ruff check app/`
- Alembic round-trip: `cd server && alembic upgrade head && alembic downgrade -1 && alembic upgrade head` returns to head cleanly
- Settings clamp behavior: invoke with `SMARTCOPILOT_RRF_K=5`, `SMARTCOPILOT_TRUTH_BOOST=2.0`, `SMARTCOPILOT_STALE_DAYS=0` and assert clamped values
</verification>

<success_criteria>
1. `cd server && ruff check app/` exits 0 with TID rule enabled
2. `cd server && alembic upgrade head` applies migration 0005 against the testcontainers pgvector/pg16 image
3. `cd server && pytest -m "rag or llm" --collect-only` reports ≥ 28 collected items, ≥ 28 deselected/xfailed
4. `from app.settings import settings` exposes `rrf_k`, `truth_boost`, `stale_days`, `llm_tier_cheap`, `llm_tier_balanced`, `llm_tier_strong` with documented defaults
5. `from app.models.page import Page; Page.compiled_truth_updated_at` and `Page.latest_timeline_ts` are valid attributes; `from app.models.chunk import Chunk; Chunk.chunk_index` is a valid attribute
</success_criteria>

<output>
Create `.planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-01-SUMMARY.md` when done.
</output>
