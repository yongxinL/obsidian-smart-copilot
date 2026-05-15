---
phase: 02A
plan: 04
type: execute
wave: 4
depends_on: [02A-01, 02A-02, 02A-03]
files_modified:
  - server/app/rag/retriever.py
  - server/app/rag/reranker.py
  - server/app/rag/intent.py
  - server/app/services/search.py
  - server/app/routes/search.py
  - server/app/mcp/tools/brain.py
  - server/app/tests/rag/test_retriever.py
  - server/app/tests/rag/test_reranker.py
  - server/app/tests/rag/test_intent.py
  - server/app/tests/rag/test_search_fallback.py
  - server/app/tests/integration/test_search_route.py
autonomous: true
requirements: [RAG-03, RAG-04, RAG-05]
tags: [rag, phase-2a, retriever, reranker, intent, hybrid-search, rrf, dedup, brain-search]

must_haves:
  truths:
    - "vector_search runs `c.embedding <=> :qvec::vector` ORDER BY distance LIMIT k against chunks JOIN pages with deleted_at IS NULL; uses session_with_rls(ctx) GUCs"
    - "bm25_search runs `c.tsv @@ websearch_to_tsquery('english', :q)` with ts_rank ordering on the chunks_tsv_gin_idx GIN index"
    - "RRF score = sum(1/(k + rank_i)) for i in {vector_rank, bm25_rank}; k = settings.rrf_k (D-13)"
    - "When chunk.kind == 'truth', rrf_score adds settings.truth_boost (default 0.15) per RAG-05"
    - "4-layer dedup runs before returning: (1) chunk_id dedup keep-highest-score, (2) cosine ≥ 0.92 near-dup collapse, (3) per-page cap (max 1 chunk), (4) low-quality cutoff at top_score × 0.3 (D-14)"
    - "Stale annotation: result.is_stale = True when page.latest_timeline_ts - page.compiled_truth_updated_at > timedelta(days=settings.stale_days)"
    - "classify_intent('what does john do?') returns IntentResult(mode='hybrid', should_expand=True) (≥6 words OR question word per D-08)"
    - "classify_intent('@web foo') returns mode='web_stub'; classify_intent('see [[John Smith]]') returns mode='graph' (D-07)"
    - "Multi-query expansion only fires when classify_intent.should_expand is True (D-08); uses llm.router tier='cheap' with response_format json_object; QueryExpansion pydantic model validates exactly 3 paraphrases; ValidationError falls back to [original_query]"
    - "hybrid_search returns SearchResult with search_type='hybrid_v1' when HNSW returns ≥1 vector hit; 'fts_v1' when vector_hits is empty (cold-start fallback via search_pages_fts per D-10); 'bm25_v1' is reserved for BM25-only mode (e.g. no embedding available + BM25 still produced hits)"
    - "POST /api/v1/search and brain.search MCP tool both invoke hybrid_search and surface search_type in the response payload; existing fts_v1-only behavior is REPLACED, not duplicated"
  artifacts:
    - path: "server/app/rag/retriever.py"
      provides: "vector_search(session, ctx, *, vault_id, query_embedding, limit) and bm25_search(session, ctx, *, vault_id, query, limit) returning typed dataclass hits"
      contains: "websearch_to_tsquery"
    - path: "server/app/rag/reranker.py"
      provides: "rrf_score(), is_stale(), dedup_results(), fuse(vector_hits, bm25_hits) returning ranked list[RankedResult]"
      contains: "settings.rrf_k"
    - path: "server/app/rag/intent.py"
      provides: "classify_intent(query) returns IntentResult; expand_query(session, ctx, query) returns list[str] with 1 or 4 entries (original or original + 3 paraphrases)"
      contains: "QueryExpansion"
    - path: "server/app/services/search.py"
      provides: "hybrid_search(session, ctx, *, vault_id, query, limit) — single transport-agnostic entry point invoked by REST route and MCP tool"
      contains: "search_type"
    - path: "server/app/routes/search.py"
      provides: "POST /api/v1/search now calls hybrid_search and returns search_type in the response"
      contains: "hybrid_search"
    - path: "server/app/mcp/tools/brain.py"
      provides: "brain.search MCP tool now calls hybrid_search; description updated to mention hybrid retrieval"
      contains: "hybrid_search"
  key_links:
    - from: "server/app/rag/retriever.py"
      to: "chunks.embedding and chunks.tsv"
      via: "raw SQL via session.execute(text(...)) under session_with_rls"
      pattern: "embedding <=> :qvec"
    - from: "server/app/rag/reranker.py"
      to: "settings.rrf_k, settings.truth_boost, settings.stale_days"
      via: "from app.settings import settings"
      pattern: "settings.rrf_k"
    - from: "server/app/services/search.py"
      to: "rag.intent.classify_intent, rag.intent.expand_query, rag.retriever.vector_search, rag.retriever.bm25_search, rag.reranker.fuse, services.pages.search_pages_fts, llm.router.embed_chunks"
      via: "pipeline orchestrator"
      pattern: "search_type"
    - from: "server/app/routes/search.py"
      to: "server/app/services/search.py.hybrid_search"
      via: "endpoint body calls hybrid_search; removes direct search_pages_fts call"
      pattern: "hybrid_search"
    - from: "server/app/mcp/tools/brain.py"
      to: "server/app/services/search.py.hybrid_search"
      via: "brain.search tool body calls hybrid_search; removes direct search_pages_fts call"
      pattern: "hybrid_search"
---

<objective>
Upgrade the search surface from Phase 1d's page-level FTS to chunk-level hybrid retrieval. Three new RAG submodules — retriever (vector ANN + BM25), reranker (RRF fusion + truth boost + 4-layer dedup + stale annotation), and intent (rule-based classifier + threshold-gated multi-query expansion) — assemble in a single transport-agnostic service hybrid_search(). The REST route POST /api/v1/search and the MCP tool brain.search both replace their search_pages_fts calls with hybrid_search, surfacing search_type so callers can detect which path ran (hybrid_v1 / fts_v1 / bm25_v1).

Purpose: This is the user-visible payoff of Phase 2a. Plan 03 populated the HNSW index; Plan 04 makes the agents query it. Cold-start fallback (D-10) preserves UX during the indexing window.

Output: rag/{retriever,reranker,intent}.py, services/search.py orchestrator, upgraded routes/search.py and mcp/tools/brain.py, and real tests replacing every remaining Plan 01 stub for RAG-03, RAG-04, RAG-05.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/REQUIREMENTS.md
@.planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-CONTEXT.md
@.planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-RESEARCH.md
@.planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-PATTERNS.md
@.planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-AI-SPEC.md
@.planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-01-SUMMARY.md
@.planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-02-SUMMARY.md
@.planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-03-SUMMARY.md

<interfaces>
<!-- Contracts the executor uses without rediscovery -->

From server/app/models/chunk.py (post Plan 01 migration 0005):
- Chunk columns: id, page_id, chunk_index, kind, text, enriched_content, tsv (Computed), embedding VECTOR(1536)

From server/app/models/page.py (post Plan 01 migration 0005):
- Page columns include: id, vault_id, slug, type, note_type, frontmatter, compiled_truth, timeline, content_hash, compiled_truth_updated_at, latest_timeline_ts, deleted_at, updated_at

From server/alembic/versions/0001_initial_schema.py:
- HNSW index: chunks_embedding_hnsw_idx ON chunks USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64)
- GIN index: chunks_tsv_gin_idx ON chunks USING gin (tsv)
- These exist; retriever must NOT create new indexes

From server/app/services/pages.py:
- async def search_pages_fts(session, ctx, *, vault_id, query, limit, namespace) returns list[SearchHit] — Phase 1d cold-start fallback per D-10
- SearchHit dataclass with fields: page_id, slug, title, note_type, score, snippet, matched_fields, updated_at

From server/app/routes/search.py (current):
- SearchIn with query/limit/namespace; SearchResultItem with chunk_hits=Field(default_factory=list) forward-compat hook; SearchResponse with search_type="fts_v1" default
- Plan 04 fills SearchResultItem.chunk_hits with a list of chunk-level hits and sets SearchResponse.search_type to the actual path

From server/app/mcp/tools/brain.py (brain.search around line 162):
- Existing tool body calls search_pages_fts and returns search_type="fts_v1"; description string says "Phase 1d: page-level only"; replace the body

From server/app/llm/router.py (Plan 02):
- async def embed_chunks(texts, *, op_ctx, session) returns list[list[float]]
- async def llm_complete(session, ctx, *, prompt, tier, response_format) returns str

From server/app/settings.py (Plan 01):
- settings.rrf_k (int, default 60), settings.truth_boost (float, default 0.15), settings.stale_days (int, default 30)

From server/app/auth/context.py + dependencies.py:
- OperationContext, session_with_rls(ctx)

Pgvector SQL pattern (RESEARCH §Pattern 3):
- ORDER BY c.embedding <=> :qvec::vector ASC LIMIT :lim
- Cast list[float] to pgvector format via str(list_of_floats) — register_vector is already active on the pool so the asyncpg driver accepts list[float] directly for parameterized queries (verify before adopting ::vector cast)

BM25 SQL pattern (RESEARCH §Pattern 4):
- WHERE c.tsv @@ websearch_to_tsquery('english', :q) ORDER BY ts_rank(c.tsv, websearch_to_tsquery('english', :q)) DESC LIMIT :lim
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Retriever — vector ANN + BM25 SQL (rag/retriever.py)</name>
  <files>server/app/rag/retriever.py, server/app/tests/rag/test_retriever.py</files>
  <read_first>
    - server/app/services/pages.py (search_pages_fts SQL shape and SearchHit dataclass)
    - server/app/models/chunk.py (column names referenced in SQL)
    - server/app/models/page.py (vault_id and deleted_at columns)
    - server/alembic/versions/0001_initial_schema.py lines around HNSW + GIN index creation (confirm index names)
    - server/app/database.py (register_vector pool init — confirms asyncpg can pass list[float] params)
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-PATTERNS.md §rag/retriever.py
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-RESEARCH.md §Pattern 3, §Pattern 4
  </read_first>
  <behavior>
    - vector_search(session, ctx, *, vault_id, query_embedding, limit) returns list[VectorHit] dataclass entries with fields chunk_id, page_id, page_slug, chunk_index, kind, text, enriched_content, distance (float, lower = more similar), updated_at (page.updated_at), note_type
    - bm25_search(session, ctx, *, vault_id, query, limit) returns list[BM25Hit] dataclass entries with fields chunk_id, page_id, page_slug, chunk_index, kind, text, enriched_content, rank (float, higher = more relevant), updated_at, note_type
    - Both queries JOIN chunks → pages and filter pages.vault_id = :vid AND pages.deleted_at IS NULL
    - Both queries are parameterized; no string concatenation of the user query into the SQL
    - bm25_search uses websearch_to_tsquery('english', :q); empty query (after normalization) returns []
    - When vault has zero chunks with embeddings, vector_search returns []; when GIN index has no matches, bm25_search returns []
  </behavior>
  <action>
    Create server/app/rag/retriever.py per PATTERNS §rag/retriever.py. Imports: from __future__ import annotations; import uuid; from dataclasses import dataclass; from datetime import datetime; from sqlalchemy import text; from sqlalchemy.ext.asyncio import AsyncSession; from app.auth.context import OperationContext.

    Define dataclasses:
    - @dataclass(frozen=True, slots=True) class VectorHit: chunk_id: uuid.UUID; page_id: uuid.UUID; page_slug: str; chunk_index: int; kind: str; text: str; enriched_content: str | None; distance: float; updated_at: datetime; note_type: str
    - @dataclass(frozen=True, slots=True) class BM25Hit: chunk_id: uuid.UUID; page_id: uuid.UUID; page_slug: str; chunk_index: int; kind: str; text: str; enriched_content: str | None; rank: float; updated_at: datetime; note_type: str

    Define async def vector_search(session: AsyncSession, ctx: OperationContext, *, vault_id: uuid.UUID, query_embedding: list[float], limit: int = 20) returns list[VectorHit]:
    - Guard: if not query_embedding or len(query_embedding) != 1536: raise ValueError(f"query_embedding must be 1536-dim, got {len(query_embedding) if query_embedding else 0}")
    - limit = max(1, min(int(limit), 100))
    - SQL: SELECT c.id, c.page_id, c.chunk_index, c.kind, c.text, c.enriched_content, p.slug as page_slug, p.updated_at, p.note_type, c.embedding <=> CAST(:qvec AS vector) AS distance FROM chunks c JOIN pages p ON p.id = c.page_id WHERE p.vault_id = :vid AND p.deleted_at IS NULL AND c.embedding IS NOT NULL ORDER BY distance ASC LIMIT :lim
    - Pass parameters: {"qvec": query_embedding, "vid": str(vault_id), "lim": limit} — asyncpg pgvector codec accepts list[float] directly because register_vector is wired in database.py
    - rows = (await session.execute(text(sql), params)).mappings().all()
    - Build VectorHit list from rows; return

    Define async def bm25_search(session: AsyncSession, ctx: OperationContext, *, vault_id: uuid.UUID, query: str, limit: int = 20) returns list[BM25Hit]:
    - if not query or not query.strip(): return []
    - limit = max(1, min(int(limit), 100))
    - SQL: SELECT c.id, c.page_id, c.chunk_index, c.kind, c.text, c.enriched_content, p.slug as page_slug, p.updated_at, p.note_type, ts_rank(c.tsv, websearch_to_tsquery('english', :q)) AS rank FROM chunks c JOIN pages p ON p.id = c.page_id WHERE p.vault_id = :vid AND p.deleted_at IS NULL AND c.tsv @@ websearch_to_tsquery('english', :q) ORDER BY rank DESC LIMIT :lim
    - Pass parameters: {"q": query, "vid": str(vault_id), "lim": limit}
    - Build BM25Hit list from rows; return

    Replace Plan 01 xfail stubs in server/app/tests/rag/test_retriever.py with real integration tests (pytestmark = [pytest.mark.rag, pytest.mark.integration]):
    - test_vector_search_empty_returns_empty_list: empty chunks table → empty list
    - test_vector_search_returns_hits_when_chunks_exist: seed a vault + 3 chunks with known embedding vectors; call vector_search with one of those vectors; assert at least one hit with distance close to 0.0
    - test_vector_search_rejects_wrong_dim_query: pass [0.0]*1024; assert ValueError
    - test_vector_search_limit_enforced: seed 5 chunks; call with limit=2; assert exactly 2 hits returned
    - test_vector_search_excludes_soft_deleted_pages: seed chunks, soft-delete the page; assert vector_search returns no hits for that page
    - test_bm25_search_empty_query_returns_empty: bm25_search with query="" → []
    - test_bm25_search_matches_tsvector: seed a chunk with text "PostgreSQL hybrid retrieval"; query="hybrid"; assert hit returned
    - test_bm25_search_websearch_syntax: seed chunks; query='"exact phrase" -excluded'; assert no error (websearch_to_tsquery semantics)
    - test_bm25_search_excludes_soft_deleted_pages: same as vector test but for BM25 path
    - test_vector_and_bm25_return_chunk_index_and_kind: verify chunk_index and kind fields populated on hits
  </action>
  <verify>
    <automated>cd server && pytest app/tests/rag/test_retriever.py -q -m "rag" 2>&1 | tail -10 && cd server && python -c "from app.rag.retriever import VectorHit, BM25Hit, vector_search, bm25_search; import inspect; assert inspect.iscoroutinefunction(vector_search) and inspect.iscoroutinefunction(bm25_search)"</automated>
  </verify>
  <acceptance_criteria>
    - server/app/rag/retriever.py source contains async def vector_search(, async def bm25_search(, class VectorHit, class BM25Hit
    - server/app/rag/retriever.py SQL uses CAST(:qvec AS vector) for the vector ANN query (or registers a parameterized vector cast via the asyncpg codec)
    - server/app/rag/retriever.py SQL uses websearch_to_tsquery('english', :q) for BM25
    - server/app/rag/retriever.py SQL filters on pages.vault_id = :vid AND pages.deleted_at IS NULL (grep -E "deleted_at IS NULL" returns ≥ 2 matches, one per query)
    - server/app/rag/retriever.py contains NO string concatenation of user input into SQL (grep -E "\".*\+.*query.*\"" returns empty)
    - cd server && pytest app/tests/rag/test_retriever.py -q exits 0 with at least 9 passing tests
    - cd server && ruff check app/rag/retriever.py --select TID exits 0
  </acceptance_criteria>
  <done>
    Retriever queries both pgvector HNSW and BM25 GIN under session_with_rls. RAG-03 (BM25) satisfied. Vector path ready for RAG-04 fusion. Reranker (Task 2) consumes the typed hit dataclasses.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Reranker — RRF fusion + dedup + stale annotation (rag/reranker.py)</name>
  <files>server/app/rag/reranker.py, server/app/tests/rag/test_reranker.py</files>
  <read_first>
    - server/app/rag/retriever.py (Task 1 output: VectorHit, BM25Hit shapes)
    - server/app/settings.py (post-Plan-01: rrf_k, truth_boost, stale_days)
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-CONTEXT.md (D-13, D-14 — verbatim formulas)
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-PATTERNS.md §rag/reranker.py
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-RESEARCH.md §Pattern 5
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-AI-SPEC.md (Stale annotation logic, dedup behavior, RRF k calibration eval dimension)
  </read_first>
  <behavior>
    - rrf_score(vector_rank=1, bm25_rank=None, is_truth=False) returns 1 / (settings.rrf_k + 1) = approx 0.0164
    - rrf_score(vector_rank=1, bm25_rank=1, is_truth=True) returns 2/(rrf_k+1) + truth_boost
    - rrf_score(vector_rank=None, bm25_rank=None, is_truth=False) returns 0.0
    - is_stale(compiled_truth_updated_at=t0, latest_timeline_ts=t0 + 31 days) returns True when stale_days=30
    - is_stale(None, anything) returns False (incomplete data); is_stale(anything, None) returns False
    - fuse(vector_hits, bm25_hits) returns list[RankedResult] with: chunk_id, page_id, page_slug, chunk_index, kind, text, score (RRF), retrieval_paths (list of "vector"/"bm25"), is_stale, stale_days (int | None), distance (vector only), bm25_rank_value (bm25 only)
    - dedup_results(candidates, top_k=20) executes the four layers in CONTEXT D-14 order:
      Layer 1: dedupe by chunk_id keeping the highest-score row; merge retrieval_paths set
      Layer 2: drop a row when its chunk text is a substring of an earlier higher-scoring row's text, OR when the two share normalized whitespace-stripped content (proxy for cosine >= 0.92; the real cosine compare is deferred until production tuning — keep the substring-and-normalized-equals heuristic and surface a `# TODO(Phase 2a polish): proxy heuristic for cosine ≥ 0.92 from CONTEXT D-14 (full cosine compare deferred); see RESEARCH §Pitfall handling.` comment so the heuristic is auditable)
      Layer 3: at most 1 chunk per page_id (per-page cap = 1); keep highest-scoring chunk per page
      Layer 4: drop rows with score < top_score * 0.3 (low-quality cutoff α=0.3)
      Return top_k entries after layers 1–4
  </behavior>
  <action>
    Create server/app/rag/reranker.py. Imports: from __future__ import annotations; import uuid; from dataclasses import dataclass, field; from datetime import datetime, timedelta; from typing import Iterable; from app.rag.retriever import BM25Hit, VectorHit; from app.settings import settings.

    Define @dataclass(slots=True) class RankedResult:
    - chunk_id: uuid.UUID
    - page_id: uuid.UUID
    - page_slug: str
    - chunk_index: int
    - kind: str
    - text: str
    - score: float
    - retrieval_paths: list[str] (default factory list)
    - is_stale: bool = False
    - stale_days: int | None = None
    - vector_distance: float | None = None
    - bm25_rank_value: float | None = None
    - updated_at: datetime | None = None

    Define def rrf_score(vector_rank: int | None, bm25_rank: int | None, is_truth: bool) -> float:
    - k = settings.rrf_k
    - score = 0.0
    - if vector_rank is not None: score += 1.0 / (k + vector_rank)
    - if bm25_rank is not None: score += 1.0 / (k + bm25_rank)
    - if is_truth: score += settings.truth_boost
    - return score

    Define def is_stale(compiled_truth_updated_at: datetime | None, latest_timeline_ts: datetime | None) -> tuple[bool, int | None]:
    - if compiled_truth_updated_at is None or latest_timeline_ts is None: return (False, None)
    - delta = latest_timeline_ts - compiled_truth_updated_at
    - is_st = delta > timedelta(days=settings.stale_days)
    - days = max(0, delta.days)
    - return (is_st, days if is_st else None)

    Define def fuse(vector_hits: list[VectorHit], bm25_hits: list[BM25Hit], page_meta: dict[uuid.UUID, tuple[datetime | None, datetime | None]] | None = None) -> list[RankedResult]:
    - page_meta maps page_id to (compiled_truth_updated_at, latest_timeline_ts) tuples for stale annotation; if None, all results are is_stale=False
    - Build vector_rank_by_chunk: dict[chunk_id, (rank_int, hit)] where rank_int is 1-based position in vector_hits
    - Build bm25_rank_by_chunk: dict[chunk_id, (rank_int, hit)] same for bm25
    - all_chunk_ids = union of both keys
    - For each chunk_id in all_chunk_ids: pick reference hit (prefer vector hit if present, else bm25 hit) for text/kind/chunk_index/page_slug; compute rrf_score(v_rank, b_rank, is_truth=(kind=='truth')); paths = ["vector"] if vector present + ["bm25"] if bm25 present; if page_meta provided, compute (is_st, days) via is_stale(compiled_truth_updated_at, latest_timeline_ts) for ref_hit.page_id, default tuple (None, None) if missing
    - Return list[RankedResult] sorted by score descending

    Define def dedup_results(candidates: list[RankedResult], top_k: int = 20) -> list[RankedResult]:
    - Layer 1: chunk_id dedup; sorted by score desc; first occurrence wins, merge retrieval_paths from later duplicates
    - Layer 2: near-duplicate content proxy. Insert a top-of-function comment "# TODO(Phase 2a polish): proxy for cosine ≥ 0.92 from CONTEXT D-14 (full cosine compare deferred); see RESEARCH §Pitfall handling." Build a list of kept rows; for each candidate in score-desc order, normalize text via " ".join(text.lower().split()); skip if normalized equals or is a substring of any normalized text already in the kept list AND scores are within 10% of each other
    - Layer 3: per-page cap; iterate score-desc; allow at most 1 chunk per page_id
    - Layer 4: low-quality cutoff. If kept is non-empty, threshold = kept[0].score * 0.3; drop any kept row with score < threshold
    - Return kept[:top_k]

    Replace Plan 01 stubs in server/app/tests/rag/test_reranker.py with real assertions (pytestmark = [pytest.mark.rag, pytest.mark.unit]):
    - test_rrf_formula_basic: rrf_score(1, None, False) == 1/(60+1); rrf_score(1, 1, False) == 2/(60+1)
    - test_rrf_truth_boost: rrf_score(1, 1, True) == rrf_score(1, 1, False) + 0.15
    - test_rrf_both_none_zero: rrf_score(None, None, False) == 0.0
    - test_is_stale_within_window: compiled t0; timeline t0 + 5 days; with stale_days=30 returns (False, None)
    - test_is_stale_beyond_window: compiled t0; timeline t0 + 31 days; returns (True, 31)
    - test_is_stale_missing_data: is_stale(None, t0) returns (False, None); is_stale(t0, None) returns (False, None)
    - test_fuse_truth_chunk_outranks_event_with_same_ranks: two chunks at vector_rank=1 each; one kind="truth", one kind="event"; assert truth chunk has higher score
    - test_fuse_merges_retrieval_paths: same chunk_id in both vector_hits[0] and bm25_hits[0]; assert returned RankedResult.retrieval_paths == ["vector","bm25"]
    - test_fuse_stale_annotation_propagated: pass page_meta with compiled_truth_updated_at and latest_timeline_ts beyond stale window; assert is_stale=True on resulting RankedResult
    - test_dedup_layer1_chunk_id: two identical chunk_ids; assert one row returned
    - test_dedup_layer2_near_duplicate: two rows with same normalized text and similar scores; assert one removed
    - test_dedup_layer3_per_page_cap: 3 chunks on same page_id with different scores; assert only the highest-score chunk remains
    - test_dedup_layer4_low_quality_cutoff: scores [1.0, 0.5, 0.2]; assert rows with score < 0.3 dropped (0.2 dropped because 1.0 * 0.3 = 0.3)
    - test_dedup_top_k_truncates: 25 rows; top_k=10; assert exactly 10 returned
    - test_dedup_empty_input: dedup_results([]) returns []
  </action>
  <verify>
    <automated>cd server && pytest app/tests/rag/test_reranker.py -q -m "rag" 2>&1 | tail -10 && cd server && python -c "from app.rag.reranker import rrf_score, is_stale, fuse, dedup_results, RankedResult; from app.settings import settings; assert abs(rrf_score(1, 1, True) - (2/(settings.rrf_k+1) + settings.truth_boost)) < 1e-9"</automated>
  </verify>
  <acceptance_criteria>
    - server/app/rag/reranker.py source contains def rrf_score(, def is_stale(, def fuse(, def dedup_results(, class RankedResult
    - server/app/rag/reranker.py imports settings (grep -q "from app.settings import settings")
    - server/app/rag/reranker.py references settings.rrf_k, settings.truth_boost, settings.stale_days (grep returns each)
    - server/app/rag/reranker.py dedup_results contains a "# TODO" comment naming D-14 (heuristic disclosure)
    - cd server && pytest app/tests/rag/test_reranker.py -q exits 0 with at least 14 passing tests
    - cd server && ruff check app/rag/reranker.py --select TID exits 0
    - server/app/rag/reranker.py contains no SQLAlchemy/asyncpg/FastAPI imports (grep -E "from (sqlalchemy|asyncpg|fastapi)" returns empty — pure transform)
  </acceptance_criteria>
  <done>
    Reranker is a pure transform that fuses vector + BM25 hits via RRF (D-13), applies the 4-layer dedup (D-14), and annotates stale pages. RAG-04 (RRF) and RAG-05 (dedup + stale) requirements satisfied. Service orchestrator (Task 4) consumes fuse() + dedup_results().
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Intent classifier + query expansion (rag/intent.py)</name>
  <files>server/app/rag/intent.py, server/app/tests/rag/test_intent.py</files>
  <read_first>
    - server/app/llm/router.py (Plan 02: llm_complete signature; response_format kwarg)
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-CONTEXT.md (D-07, D-08, D-09)
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-PATTERNS.md §rag/intent.py
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-AI-SPEC.md §4b (Pydantic QueryExpansion validator, prompt discipline)
  </read_first>
  <behavior>
    - classify_intent(query) returns IntentResult(mode in {"hybrid","graph","web_stub","exact"}, should_expand: bool) based ONLY on regex rules; no LLM call
    - "@web foo" → mode="web_stub", should_expand=False
    - "see [[John Smith]]" → mode="graph", should_expand=False
    - "what does john do today?" (≥6 words OR contains question word) → mode="hybrid", should_expand=True
    - "John Smith" → mode="hybrid", should_expand=False (short and no question word)
    - "[[brackets]] in literal text body that is also long enough" → still mode="graph" because the regex matches; documented false-positive per AI-SPEC Section 1b (intent classifier false positives)
    - expand_query(session, ctx, query): if classify_intent says should_expand=False, return [query] immediately (no LLM call). If should_expand=True: call llm_complete(tier="cheap", response_format={"type":"json_object"}, prompt=EXPANSION_USER.format(query=query)); parse response with QueryExpansion pydantic model; on ValidationError or count != 3, return [query]; on success return [query, *paraphrases]
  </behavior>
  <action>
    Create server/app/rag/intent.py. Imports: from __future__ import annotations; import re; from dataclasses import dataclass; from typing import Literal; from pydantic import BaseModel, ValidationError, field_validator; from sqlalchemy.ext.asyncio import AsyncSession; from app.auth.context import OperationContext; from app.llm.router import llm_complete.

    Module-level constants:
    - _QUESTION_WORDS = re.compile(r"\b(what|how|why|when|who|where)\b", re.IGNORECASE)
    - _GRAPH_INTENT = re.compile(r"\[\[.+?\]\]")
    - _WEB_PREFIX = re.compile(r"^@web\b", re.IGNORECASE)
    - EXPANSION_SYSTEM (constant string from AI-SPEC §4b — defines task contract, JSON output format, max 20 words per paraphrase)
    - EXPANSION_USER (template "{query}")

    Define @dataclass(frozen=True, slots=True) class IntentResult: mode: Literal["hybrid","graph","web_stub","exact"]; should_expand: bool

    Define def classify_intent(query: str) -> IntentResult per CONTEXT D-07:
    - if _WEB_PREFIX.match(query): return IntentResult(mode="web_stub", should_expand=False)
    - if _GRAPH_INTENT.search(query): return IntentResult(mode="graph", should_expand=False)
    - words = query.split()
    - should_expand = len(words) >= 6 or bool(_QUESTION_WORDS.search(query))
    - return IntentResult(mode="hybrid", should_expand=should_expand)

    Define class QueryExpansion(BaseModel): paraphrases: list[str]; with @field_validator("paraphrases") def exactly_three(cls, v) that raises ValueError(f"Expected 3 paraphrases, got {len(v)}") if len(v) != 3

    Define async def expand_query(session: AsyncSession, ctx: OperationContext, query: str) -> list[str]:
    - intent = classify_intent(query)
    - if not intent.should_expand: return [query]
    - prompt = EXPANSION_SYSTEM + "\n\n" + EXPANSION_USER.format(query=query)
    - try: raw = await llm_complete(session, ctx, prompt=prompt, tier="cheap", response_format={"type":"json_object"})
    - except Exception: return [query]  # graceful degradation on LLM failure
    - try: data = QueryExpansion.model_validate_json(raw); return [query, *data.paraphrases]
    - except (ValidationError, ValueError): return [query]

    Replace Plan 01 stubs in server/app/tests/rag/test_intent.py with real tests:
    - test_classify_web_prefix: classify_intent("@web foo bar") returns mode="web_stub", should_expand=False
    - test_classify_graph_intent: classify_intent("tell me about [[John Smith]]") returns mode="graph"
    - test_classify_question_word_short: classify_intent("what is X?") returns mode="hybrid", should_expand=True
    - test_classify_long_query_expand: classify_intent("one two three four five six") returns should_expand=True (6 words exactly)
    - test_classify_short_no_question: classify_intent("John Smith") returns mode="hybrid", should_expand=False
    - test_classify_brackets_false_positive_documented: classify_intent("paper [[brackets]] are literal") returns mode="graph" (documented false-positive)
    - test_expand_query_skips_when_no_expand: mock llm_complete to fail loudly if called; pass classify_intent-skipping query "John"; assert returns ["John"] and llm_complete not called
    - test_expand_query_returns_query_plus_paraphrases: patch app.rag.intent.llm_complete with AsyncMock returning '{"paraphrases":["A","B","C"]}'; assert returns ["original", "A", "B", "C"]
    - test_expand_query_wrong_count_falls_back: mock returns '{"paraphrases":["only one"]}'; assert returns [original_query]
    - test_expand_query_invalid_json_falls_back: mock returns 'not json'; assert returns [original_query]
    - test_expand_query_llm_exception_falls_back: mock raises ValueError; assert returns [original_query]
  </action>
  <verify>
    <automated>cd server && pytest app/tests/rag/test_intent.py -q -m "rag" 2>&1 | tail -10 && cd server && python -c "from app.rag.intent import classify_intent, expand_query, IntentResult, QueryExpansion; r = classify_intent('what is foo bar?'); assert r.should_expand"</automated>
  </verify>
  <acceptance_criteria>
    - server/app/rag/intent.py source contains def classify_intent(, async def expand_query(, class IntentResult, class QueryExpansion, EXPANSION_SYSTEM (constant)
    - server/app/rag/intent.py source contains the three regex patterns: _WEB_PREFIX, _GRAPH_INTENT, _QUESTION_WORDS
    - server/app/rag/intent.py imports llm_complete from app.llm.router (NOT litellm directly)
    - cd server && ruff check app/rag/intent.py --select TID exits 0
    - cd server && pytest app/tests/rag/test_intent.py -q exits 0 with at least 11 passing tests
  </acceptance_criteria>
  <done>
    Intent classifier (D-07) and threshold-gated multi-query expansion (D-08) are pure-Python services. Expansion fires only when classify_intent says should_expand=True. Service orchestrator (Task 4) consumes both. RAG-05 (intent + expansion) requirement partially satisfied (the compiled-truth boost + dedup + stale annotation are in Task 2).
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 4: Hybrid search orchestrator + route + MCP tool upgrade</name>
  <files>server/app/services/search.py, server/app/routes/search.py, server/app/mcp/tools/brain.py, server/app/tests/rag/test_search_fallback.py, server/app/tests/integration/test_search_route.py</files>
  <read_first>
    - server/app/rag/retriever.py (Task 1: VectorHit, BM25Hit, vector_search, bm25_search)
    - server/app/rag/reranker.py (Task 2: fuse, dedup_results, RankedResult)
    - server/app/rag/intent.py (Task 3: classify_intent, expand_query)
    - server/app/llm/router.py (Plan 02: embed_chunks)
    - server/app/services/pages.py (search_pages_fts; cold-start fallback per D-10)
    - server/app/routes/search.py (current SearchIn/Out shapes)
    - server/app/mcp/tools/brain.py (brain.search tool body around line 162)
    - server/app/services/vault_resolver.py (resolve_user_vault_id)
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-CONTEXT.md (D-10, D-11 — cold-start + search_type values)
    - server/app/tests/integration/test_search_route.py (existing search-route test; extend rather than replace)
  </read_first>
  <behavior>
    - hybrid_search(session, ctx, *, vault_id, query, limit) is the single orchestrator: classify_intent → optional expand_query → embed each query (original + paraphrases) → vector_search + bm25_search per query → flatten and dedupe by chunk_id keeping highest score within each query channel → fuse (RRF) → load page_meta for stale annotation → dedup_results → if no chunks resulted, call search_pages_fts as cold-start fallback
    - Returns SearchResult dataclass: items (list[SearchHitOut]), search_type (str: "hybrid_v1" | "bm25_v1" | "fts_v1"), total (int), query (str)
    - SearchHitOut maps RankedResult to a transport-neutral structure with: page_slug (=slug), page_id, chunk_id, chunk_index, kind, text (snippet), score, retrieval_paths, is_stale, stale_days, note_type, updated_at
    - When intent.mode == "graph": Phase 2a stubs graph traversal as a no-op (empty list); falls through to hybrid path per CONTEXT D-09 second sentence (graph-first, blend if low confidence). Search_type still "hybrid_v1" because graph stub returns [] which is treated as low-confidence.
    - When intent.mode == "web_stub": Phase 2a returns search_type="hybrid_v1" with no special branch — Phase 5 wires web search; document with a # NOTE comment
    - Cold-start: vector_search returns 0 hits AND bm25_search returns 0 hits → fall back to search_pages_fts(vault_id, query) returning page-level hits with search_type="fts_v1"
    - When vector_search returns 0 AND bm25_search > 0 → search_type="bm25_v1"; bm25 hits are fed through fuse() and dedup with vector_rank=None
    - Route POST /api/v1/search and MCP tool brain.search both call hybrid_search and return the same SearchResult shape; the route maps SearchResult → SearchResponse Pydantic model; MCP tool maps to dict
  </behavior>
  <action>
    Create server/app/services/search.py. Imports: from __future__ import annotations; import uuid; from dataclasses import dataclass; from datetime import datetime; from sqlalchemy import select; from sqlalchemy.ext.asyncio import AsyncSession; from app.auth.context import OperationContext; from app.llm.router import embed_chunks; from app.models.page import Page; from app.rag.intent import classify_intent, expand_query; from app.rag.retriever import bm25_search, vector_search; from app.rag.reranker import RankedResult, dedup_results, fuse; from app.services.pages import search_pages_fts.

    Define @dataclass(frozen=True, slots=True) class SearchHitOut: slug: str; title: str | None; note_type: str; score: float; snippet: str; matched_fields: list[str]; page_id: uuid.UUID; chunk_id: uuid.UUID | None; chunk_index: int | None; kind: str | None; retrieval_paths: list[str]; is_stale: bool; stale_days: int | None; updated_at: datetime | None

    Define @dataclass(frozen=True, slots=True) class SearchResult: items: list[SearchHitOut]; total: int; query: str; search_type: str

    Define async def hybrid_search(session: AsyncSession, ctx: OperationContext, *, vault_id: uuid.UUID, query: str, limit: int = 20) returns SearchResult:
    - if not query or not query.strip(): raise ValueError("query must be non-empty")
    - limit = max(1, min(int(limit), 100))
    - intent = classify_intent(query)
    - queries = await expand_query(session, ctx, query)  # always list, length 1 or 4
    - all_vector_hits: list[VectorHit] = []; all_bm25_hits: list[BM25Hit] = []
    - for q in queries:
        - try: embeddings = await embed_chunks([q], op_ctx=ctx, session=session); qvec = embeddings[0]
        - except Exception as exc: log.warning("hybrid_search_embed_failed", error=str(exc)); qvec = None
        - if qvec is not None: vhits = await vector_search(session, ctx, vault_id=vault_id, query_embedding=qvec, limit=limit); all_vector_hits.extend(vhits)
        - bhits = await bm25_search(session, ctx, vault_id=vault_id, query=q, limit=limit); all_bm25_hits.extend(bhits)
    - Cold-start fallback: if not all_vector_hits and not all_bm25_hits: fts_hits = await search_pages_fts(session, ctx, vault_id=vault_id, query=query, limit=limit, namespace="private"); return SearchResult(items=[SearchHitOut(slug=h.slug, title=h.title, note_type=h.note_type, score=h.score, snippet=h.snippet, matched_fields=h.matched_fields, page_id=h.page_id, chunk_id=None, chunk_index=None, kind=None, retrieval_paths=["fts"], is_stale=False, stale_days=None, updated_at=h.updated_at) for h in fts_hits], total=len(fts_hits), query=query, search_type="fts_v1")
    - search_type: "hybrid_v1" if all_vector_hits else "bm25_v1"
    - Load page_meta for stale annotation: page_ids = {h.page_id for h in all_vector_hits + all_bm25_hits}; rows = await session.execute(select(Page.id, Page.compiled_truth_updated_at, Page.latest_timeline_ts).where(Page.id.in_(page_ids))); page_meta = {row.id: (row.compiled_truth_updated_at, row.latest_timeline_ts) for row in rows}
    - candidates = fuse(all_vector_hits, all_bm25_hits, page_meta=page_meta)
    - ranked = dedup_results(candidates, top_k=limit)
    - Build title from page slug → frontmatter title lookup: query selected pages and frontmatter title; or just pass slug as both slug and title (titles are populated by routes/pages.py already)
    - items = [SearchHitOut(slug=r.page_slug, title=None, note_type="unknown", score=r.score, snippet=r.text[:200], matched_fields=r.retrieval_paths, page_id=r.page_id, chunk_id=r.chunk_id, chunk_index=r.chunk_index, kind=r.kind, retrieval_paths=r.retrieval_paths, is_stale=r.is_stale, stale_days=r.stale_days, updated_at=r.updated_at) for r in ranked]
    - return SearchResult(items=items, total=len(items), query=query, search_type=search_type)

    Edit server/app/routes/search.py:
    - Add field to SearchResultItem: chunk_id: uuid.UUID | None = None; chunk_index: int | None = None; kind: str | None = None; is_stale: bool = False; stale_days: int | None = None; retrieval_paths: list[str] = Field(default_factory=list)
    - Remove import of search_pages_fts; add from app.services.search import hybrid_search, SearchHitOut, SearchResult
    - Replace search_endpoint body: vault_id = await resolve_user_vault_id(session, ctx.user_id); result = await hybrid_search(session, ctx, vault_id=vault_id, query=payload.query, limit=payload.limit)
    - Build SearchResultItem list from result.items; pass title=item.title or None (titles can be enriched in a follow-up plan); set SearchResponse.search_type = result.search_type

    Edit server/app/mcp/tools/brain.py:
    - In the brain.search tool body: remove the search_pages_fts call and the hard-coded search_type="fts_v1"
    - Add from app.services.search import hybrid_search at the top of the module
    - Replace tool body with: vault_id = await resolve_user_vault_id(session, ctx.user_id); result = await hybrid_search(session, ctx, vault_id=vault_id, query=query, limit=limit); return {"results": [{"slug": h.slug, "title": h.title, "note_type": h.note_type, "score": h.score, "snippet": h.snippet, "matched_fields": h.matched_fields, "page_id": str(h.page_id), "chunk_id": str(h.chunk_id) if h.chunk_id else None, "chunk_index": h.chunk_index, "kind": h.kind, "retrieval_paths": h.retrieval_paths, "is_stale": h.is_stale, "stale_days": h.stale_days, "updated_at": h.updated_at.isoformat() if h.updated_at else None} for h in result.items], "total": result.total, "query": result.query, "search_type": result.search_type}
    - Update the @mcp.tool description string to mention hybrid retrieval (replace "Phase 1d: page-level only" with "Hybrid retrieval: pgvector HNSW + BM25 tsvector + RRF fusion with compiled-truth boost; cold-start fallback to FTS")

    Replace Plan 01 xfail stub server/app/tests/rag/test_search_fallback.py with real integration tests:
    - test_cold_start_returns_fts_v1: seed pages but zero chunks (so HNSW and BM25 both empty); patch embed_chunks to return canned 1536-dim vector; call hybrid_search; assert result.search_type == "fts_v1" and result.items > 0 because search_pages_fts returns the seeded pages
    - test_chunks_with_embeddings_returns_hybrid_v1: seed pages + chunks with embeddings + BM25 matches; patch embed_chunks to return matching vector; assert search_type="hybrid_v1"
    - test_chunks_only_bm25_returns_bm25_v1: seed chunks where embedding IS NULL but tsv matches; patch embed_chunks to return any vec; vector_search returns []; assert search_type="bm25_v1"

    Extend server/app/tests/integration/test_search_route.py (do NOT delete existing tests):
    - test_post_search_returns_chunk_hits_when_chunks_exist: seed a vault + page + chunk with known embedding + matching BM25 text; patch app.services.search.embed_chunks to return that vector; POST /api/v1/search with the matching query; assert response 200; assert response.json()["search_type"] in {"hybrid_v1","bm25_v1"}; assert results[0]["chunk_id"] is not None
    - test_post_search_cold_start_uses_fts_v1: seed page-level data but no chunks; assert response 200 and search_type="fts_v1"
    - test_post_search_returns_stale_annotation: seed page with compiled_truth_updated_at far behind latest_timeline_ts + matching chunk; assert response item has is_stale=True
    - test_post_search_400_on_empty_query: POST /api/v1/search with query=""; assert 422 with code="validation_error" (Pydantic min_length=1 covers this)
  </action>
  <verify>
    <automated>cd server && pytest app/tests/rag/test_search_fallback.py app/tests/integration/test_search_route.py -q 2>&1 | tail -15 && cd server && python -c "from app.services.search import hybrid_search, SearchResult, SearchHitOut; import inspect; assert inspect.iscoroutinefunction(hybrid_search)" && cd server && ruff check app/ --select TID 2>&1 | tail -5 && grep -q "hybrid_search" server/app/routes/search.py && grep -q "hybrid_search" server/app/mcp/tools/brain.py</automated>
  </verify>
  <acceptance_criteria>
    - server/app/services/search.py source contains async def hybrid_search( and references intent.classify_intent, intent.expand_query, retriever.vector_search, retriever.bm25_search, reranker.fuse, reranker.dedup_results, embed_chunks, search_pages_fts (all six dependencies wired)
    - server/app/services/search.py contains the literal strings "hybrid_v1", "fts_v1", and "bm25_v1" (D-11 search_type discipline)
    - server/app/routes/search.py source contains from app.services.search import hybrid_search and hybrid_search( call inside search_endpoint
    - server/app/routes/search.py SearchResultItem source contains chunk_id, chunk_index, kind, is_stale, stale_days, retrieval_paths fields
    - server/app/routes/search.py no longer imports search_pages_fts at module level (grep -E "from app\.services\.pages import .*search_pages_fts" returns empty for routes/search.py specifically — the import moved to services/search.py)
    - server/app/mcp/tools/brain.py source contains hybrid_search( and no longer contains "Phase 1d: page-level only" description; mentions "Hybrid retrieval" in the description string
    - server/app/services/search.py does NOT import litellm directly (Ruff TID gate)
    - cd server && pytest app/tests/rag/ app/tests/integration/test_search_route.py -q exits 0 (all RAG tests + route tests pass)
    - cd server && ruff check app/ --select TID exits 0
    - REST↔MCP parity: cd server && pytest app/tests/integration/test_rest_mcp_parity.py -q exits 0 (existing parity test still green after both surfaces upgrade together)
  </acceptance_criteria>
  <done>
    The hybrid search pipeline is end-to-end: intent classification → optional multi-query expansion via cheap LLM → vector ANN over pgvector HNSW + BM25 over tsvector GIN → RRF fusion with compiled-truth boost → 4-layer dedup → stale annotation. Both the REST route and MCP tool consume the same hybrid_search service and surface search_type. Cold-start fallback (D-10) preserves UX when HNSW is empty. RAG-03, RAG-04, and RAG-05 are all satisfied. Plan 05 wires the embedding migration endpoints + Phase 2a acceptance test.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Caller (route/MCP) -> hybrid_search | User query is untrusted text; all SQL parameterized; query length cap (512) enforced by Pydantic SearchIn |
| hybrid_search -> llm.router.embed_chunks | Each query string sent to OpenAI embedding API; per-call api_key + metadata user_id from Plan 02 |
| Retriever SQL -> pgvector + tsvector | Both queries filter pages.vault_id and deleted_at; session_with_rls(ctx) sets RLS GUC; RLS policies on chunks/pages enforce cross-user isolation |
| Reranker (pure transform) -> SearchHitOut | Output text is verbatim chunk.text; no LLM synthesis (faithfulness invariant from AI-SPEC) |
| Multi-query expansion -> cheap-tier LLM | Threshold-gated (D-08) so short queries never touch LLM; per-query LLM cost capped via UsageRecorder cost recording |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02A-04-01 | Information Disclosure | Cross-user chunk retrieval | mitigate | Both vector_search and bm25_search filter pages.vault_id and deleted_at IS NULL; session_with_rls(ctx) sets app.current_user_id GUC; RLS policies authored in Phase 1b (migration 0002) on chunks/pages enforce per-user isolation |
| T-02A-04-02 | Tampering | SQL injection via query string | mitigate | All SQL uses sqlalchemy text() with bind parameters; websearch_to_tsquery accepts user query as a parameter not concatenated; acceptance grep enforces |
| T-02A-04-03 | Integrity | Fabricated content in SearchResultItem | mitigate | hybrid_search ONLY surfaces verbatim chunk.text (or page snippet from search_pages_fts); no LLM synthesis path in Phase 2a (deferred to Phase 2b/3 answer synthesis); AI-SPEC critical failure mode #1 (hallucinated chunk attribution) addressed by no-synthesis design |
| T-02A-04-04 | Denial of Service | Cost runaway via unbounded expansion | mitigate | D-08 threshold gate in classify_intent (no expansion on short queries); expand_query falls back to original on any LLM error; cheap-tier model only; UsageRecorder records cost per-call (operator can spot regressions) |
| T-02A-04-05 | Information Disclosure | Stale content surfaced without flag | mitigate | is_stale() compares page.latest_timeline_ts vs page.compiled_truth_updated_at against settings.stale_days; fuse() attaches is_stale + stale_days to RankedResult; route + MCP tool surface them in payload |
| T-02A-04-06 | Tampering | Cold-start blind spot returns empty silently | mitigate | When vector_search and bm25_search both return [], hybrid_search falls back to search_pages_fts (D-10); search_type="fts_v1" surfaces the path to caller so operator can detect index lag |
| T-02A-04-SC | Tampering | npm/pip/cargo installs | mitigate | All packages pinned in Plan 01; no new installs in Plan 04 |
</threat_model>

<verification>
- All four RAG submodule tests: cd server && pytest app/tests/rag/ -q
- Search route + parity tests: cd server && pytest app/tests/integration/test_search_route.py app/tests/integration/test_rest_mcp_parity.py -q
- Phase 1d MCP tools regression: cd server && pytest app/tests/integration/test_mcp_tools.py -q
- TID gate: cd server && ruff check app/ --select TID
- No direct litellm imports outside llm/: grep -rE "^(import litellm|from litellm)" server/app/ --include="*.py" | grep -vE "/llm/(router|tiers|keys|usage)\.py:" | grep -v "/tests/" returns empty
- Full suite: cd server && pytest app/tests/ -q
</verification>

<success_criteria>
1. POST /api/v1/search and brain.search MCP tool both return search_type="hybrid_v1" when chunks have embeddings; both return identical hit data via shared hybrid_search service (REST↔MCP parity preserved)
2. Multi-query expansion fires only when classify_intent.should_expand is True; LLM call count is 0 for short queries (RAG-05 D-08)
3. RRF formula score = Σ 1/(k + rank_i) implemented with k=settings.rrf_k; compiled-truth chunks get +settings.truth_boost (RAG-04, RAG-05)
4. 4-layer dedup removes duplicates by chunk_id, normalized-content near-dups, per-page cap=1, low-quality cutoff α=0.3 (RAG-05 D-14)
5. Stale annotation surfaces is_stale + stale_days on results from pages with compiled_truth_updated_at lagging latest_timeline_ts > stale_days (RAG-05 D-13)
6. Cold-start: empty HNSW + empty BM25 → search_type="fts_v1" with page-level hits from search_pages_fts (RAG-05 D-10)
</success_criteria>

<output>
Create .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-04-SUMMARY.md when done.
</output>
