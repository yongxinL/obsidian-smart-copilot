# Phase 2a: LLM Gateway + Hybrid RAG Pipeline - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire the intelligence layer on top of the Phase 1a–1d foundation:

- **LLM Router** (`llm/router.py`): All embedding and LLM completion calls go through the router. LiteLLM imported as library (no proxy process). Three model tiers: cheap/balanced/strong. Per-user encrypted provider keys with system fallback. Every call records to `llm_usage` table (provider, model, tokens, cost_usd). Direct LiteLLM calls from services or routes fail Ruff lint enforcement.
- **Chunker/Embedder**: Content-kind-aware chunking pipeline splits page content into typed chunks (`Chunk.kind`: truth/event/summary/detail/enrichment). Embeddings stored in `chunks.embedding` VECTOR(1536) via pgvector HNSW index. `archived_fleeting` and `skill` page types skip the embed pipeline entirely.
- **BM25**: `chunks.tsv TSVECTOR` (already defined as `Computed` column) used for BM25 retrieval via `websearch_to_tsquery`. GIN index on `chunks.tsv`.
- **Hybrid RRF Fusion**: Vector + BM25 + graph results fused via Reciprocal Rank Fusion; compiled-truth boost; stale-page annotation; 4-layer deduplication.
- **Intent Classifier**: Rule-based pattern matching routes queries to retrieval mode. Multi-query expansion (3 paraphrases via cheap LLM tier) fires on threshold.
- **Embedding Migration**: RAG-07 endpoints (estimate/start/status/cancel) for dimension-change migration with concurrent backfill.

**Not in this phase:** Typed wikilink extraction (Phase 2b), knowledge graph traversal (Phase 2b), ReAct agent (Phase 2b), skills runtime (Phase 3), projects/workspaces (Phase 5).

</domain>

<decisions>
## Implementation Decisions

### Chunk Boundary Strategy

- **D-01:** Target 512 tokens per chunk with 50-token sliding-window overlap. Prevents context split at boundaries without doubling chunk count.
- **D-02:** Timeline events (below-the-line section): one chunk per event (kind=`event`). Each timeline entry is its own chunk. Very short events padded to minimum ~50 tokens.
- **D-03:** Compiled-truth section: 512-token sliding window with 50-token overlap (kind=`truth`).
- **D-04:** Frontmatter: single chunk per page (kind=`summary`). Short; never split.
- **D-05:** `enriched_content` fallback: when enrichment has not yet run, `enriched_content = text` (raw chunk text). Embedder always reads `enriched_content`; no null-path needed. Enrichment overwrites it later without re-chunking.
- **D-06:** Pages with `note_type` = `archived_fleeting` or page_type = `skill` are skipped by the chunk/embed pipeline entirely (per RAG-01).

### Intent Classifier + Query Expansion

- **D-07:** Intent classifier is **rule-based patterns only** (no LLM call). Rules: `@web` prefix → web search mode (Phase 5 stub); `[[Entity]]` in query → graph-intent; question words (what/how/why/when) or ≥6 word query → candidate for expansion; entity name patterns → factual lookup.
- **D-08:** Multi-query expansion (3 paraphrases via cheap LLM tier) is **threshold-gated**: fires when query length ≥ 6 words OR query contains a question word (what/how/why/when). Short/precise queries (e.g., "John Smith") skip expansion.
- **D-09:** Graph-intent routing: **graph-first, blend if low confidence**. For clear graph queries, run `brain.graph.traverse` first. If graph returns <3 results, fall back to hybrid RAG and blend. Optimizes the common case while preserving coverage.

### Cold-Start Search Behavior

- **D-10:** When HNSW index is empty or embedding queue is lagging, `brain.search` **falls back to Phase 1d's `pages.search_vector` FTS path**. Returns page-level hits with `search_type="fts_v1"`. User gets results, not an error.
- **D-11:** The `search_type` field in `SearchResponse` encodes actual retrieval path: `"hybrid_v1"` (vector+BM25+graph), `"fts_v1"` (page-level FTS fallback), `"bm25_v1"` (BM25-only). Caller can detect which path ran.
- **D-12:** Embedding always triggered **async via APScheduler job** (never sync inline on page write). Consistent with the existing supervisord/APScheduler pattern. Cold-start fallback handles the indexing delay window.

### RRF Scoring + Deduplication

- **D-13:** RRF constants are **env-var configurable**, read at startup into `settings.py`, no DB reads on search:
  - `SMARTCOPILOT_RRF_K` (int, default 60, clamp [10, 200])
  - `SMARTCOPILOT_TRUTH_BOOST` (float, default 0.15, clamp [0.0, 0.5]) — applied when `chunk.kind == "truth"`
  - `SMARTCOPILOT_STALE_DAYS` (int, default 30, clamp [1, 365]) — page annotated stale when `latest_timeline_ts - compiled_truth_updated_at > stale_days`
  - Out-of-range values → clamp + log warning at startup
- **D-14:** 4-layer deduplication runs before returning `SearchResponse`:
  1. **Exact identity dedup**: dedupe by `chunk_id` (or `page_slug+chunk_index`); keep highest score, merge `retrieval_paths`.
  2. **Near-duplicate content dedup**: dedupe by normalized content hash or cosine similarity ≥ 0.92; keep highest score.
  3. **Per-page diversity cap**: max 1 chunk per page in top-K results (optionally 2 in later tuning); keep highest-scoring chunk(s) per page.
  4. **Low-quality cutoff**: drop results below minimum fused/lexical score threshold OR below `top_score × α`; if all removed, return empty with `status/meta`.

### Claude's Discretion

- Chunker tokenizer: use `tiktoken` (consistent with `text-embedding-3-small`'s tokenizer). Fallback: character-based estimate at 4 chars/token.
- HNSW index params: `m=16, ef_construction=64` per RAG-02; `pgvector.register_vector` on every new pool connection.
- LLM router tier assignment: cheap=GPT-4o-mini/DeepSeek-V3, balanced=GPT-4o/Sonnet, strong=o3/Opus. Exact model IDs resolved from provider keys at runtime.
- Embedding batch size: 100 chunks per batch to stay within OpenAI API limits.
- Embedding migration (RAG-07): add column → backfill concurrently → `CREATE INDEX CONCURRENTLY` → atomic rename. Progress tracked in `system_config` table.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product Requirements
- `docs/product_requirements_document_v26.05.md` — authoritative PRD (v26.05.1). Phase 2a directly implements: §14 (LLM Gateway + LiteLLM), §15 (Hybrid RAG Pipeline), §16 (Embedding migration), §24.2 (Provider key resolution order). Requirements: LLM-01–LLM-05, RAG-01–RAG-07.

### Planning Artifacts
- `.planning/REQUIREMENTS.md` — structured requirements for LLM-01–05, RAG-01–07 scoped to Phase 2a
- `.planning/ROADMAP.md` — Phase 2a goal, 5 success criteria, dependency on Phase 1d
- `.planning/phases/01d-mcp-server-rest-api-cli/01d-CONTEXT.md` — Phase 1d decisions. Key inheritances: `SearchResponse.search_type` forward-compat hook (D-02 there → `search_type` extended in D-11 here); `OperationContext` + `session_with_rls()` discipline; services transport-agnostic.

### Existing Models (inherit, don't rewrite)
- `server/app/models/chunk.py` — `Chunk` model with `VECTOR(1536)`, `tsv TSVECTOR (Computed)`, kind enum. Phase 2a activates this.
- `server/app/models/llm_usage.py` — `LLMUsage` model. Phase 2a populates it.
- `server/app/routes/search.py` — existing `SearchResponse` with `search_type="fts_v1"`. Phase 2a upgrades to hybrid, extends `search_type`.

### Technology
- pgvector Python docs — `register_vector` on pool init, HNSW creation syntax, `CREATE INDEX CONCURRENTLY`
- LiteLLM Python docs — in-process library import usage, provider key injection, cost tracking hooks

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server/app/routes/search.py` — `SearchResponse`, `SearchResultItem`, `SearchIn` Pydantic models. Phase 2a extends `search_type` field and fills `chunk_hits` (was empty list in Phase 1d).
- `server/app/services/pages.py` — `search_pages_fts()` is the cold-start fallback. Phase 2a calls this when HNSW is empty.
- `server/app/models/chunk.py` — `Chunk` model fully defined. Phase 2a writes to it.
- `server/app/models/llm_usage.py` — `LLMUsage` fully defined. Phase 2a writes to it via `llm/router.py`.
- `server/app/scheduler/` — APScheduler job pattern (existing `reconcile_vault.py`). Embedding job follows same structure.
- `server/app/database.py` — pool `init` callback. Add `register_vector` here for pgvector.

### Established Patterns
- `session_with_rls()` + `SET app.current_user_id` + `RESET in finally:` — **mandatory for all DB ops** including chunker, embedder, and search paths.
- Services are transport-agnostic: `OperationContext` in, domain objects out — no FastAPI types in `services/`.
- Routes are thin: validate input → call service → return Pydantic response model.
- APScheduler jobs in dedicated supervisord process (never inside uvicorn). Embedding job follows this pattern.
- Settings via env vars read at startup into `server/app/settings.py` (`Settings` Pydantic model). D-13 constants extend `Settings`.

### Integration Points
- `server/app/mcp/tools/brain.py` — `brain.search` tool currently calls `search_pages_fts`. Phase 2a replaces with hybrid retrieval service (same tool interface).
- `server/app/routes/search.py` — `POST /api/v1/search` route. Same upgrade: calls hybrid retrieval instead of FTS.
- `server/app/main.py` — `create_app()`: add new Phase 2a routes (embedding migration endpoints RAG-07).
- `supervisord.conf` — embedding worker may run as separate process or inside APScheduler. Follow existing pattern.

</code_context>

<specifics>
## Specific Ideas

- `search_type` enum values: `"hybrid_v1"` (full hybrid), `"fts_v1"` (Phase 1d FTS fallback), `"bm25_v1"` (BM25-only). Return in every `SearchResponse`.
- RRF formula: `score = Σ 1/(k + rank_i)` where k=60 (SMARTCOPILOT_RRF_K). Plus compiled-truth boost of +0.15 (SMARTCOPILOT_TRUTH_BOOST) when chunk.kind="truth".
- Stale annotation: `{stale: true, stale_days: N}` in search result metadata when condition met.
- Dedup layer 2 similarity threshold: 0.92 cosine (configurable as Claude discretion, not a user-facing setting).
- Per-page cap default: max 1 chunk per page in top-K; `α` for low-quality cutoff: Claude's discretion (e.g., 0.3).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 2a — LLM Gateway + Hybrid RAG Pipeline*
*Context gathered: 2026-05-15*
