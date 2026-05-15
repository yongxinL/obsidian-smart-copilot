# Phase 2a: LLM Gateway + Hybrid RAG Pipeline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-15
**Phase:** 2a — LLM Gateway + Hybrid RAG Pipeline
**Areas discussed:** Chunk boundary strategy, Intent classifier + query expansion, Cold-start search behavior, RRF boost & score configurability

---

## Chunk Boundary Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| 512 tokens | Industry standard for RAG. Balances precision vs. context per chunk. | ✓ |
| 256 tokens | Finer granularity — better for specific facts, may split context. | |
| 1024 tokens | Larger context per chunk — better for long blocks, precision suffers. | |

**User's choice:** 512 tokens

| Option | Description | Selected |
|--------|-------------|----------|
| Overlap 50 tokens | Standard sliding-window overlap. Prevents boundary splits. | ✓ |
| No overlap | Clean splits only. Simpler but risks splitting at boundaries. | |
| Overlap 128 tokens | More generous — useful for dense summaries, increases index size ~25%. | |

**User's choice:** Overlap 50 tokens

| Option | Description | Selected |
|--------|-------------|----------|
| One chunk per event | Each timeline entry = own "event" kind chunk. Max retrieval precision. | ✓ |
| Sliding window over timeline | Treat timeline same as compiled_truth. Simpler, loses per-event granularity. | |
| Group events by date | Same-day events clustered. Good for meetings but adds complexity. | |

**User's choice:** One chunk per event

| Option | Description | Selected |
|--------|-------------|----------|
| Fall back to raw text | enriched_content = text when enrichment hasn't run. No null-check needed. | ✓ |
| Null until enriched | Separate code path for unenriched. More explicit but adds branching. | |
| You decide | Planner handles per model schema. | |

**User's choice:** Fall back to raw text

---

## Intent Classifier + Query Expansion

| Option | Description | Selected |
|--------|-------------|----------|
| Rule-based patterns | Regex/keyword. Zero latency/cost, deterministic. Covers 90%+ of vault queries. | ✓ |
| Cheap LLM classifier | Single LLM call. More accurate on ambiguous queries; adds ~200-500ms + cost. | |
| Hybrid: rules + LLM on ambiguous | Best of both, more complex to implement. | |

**User's choice:** Rule-based patterns

| Option | Description | Selected |
|--------|-------------|----------|
| Threshold-gated | Expansion fires only on long/ambiguous queries. Short precise queries skip. | ✓ |
| Always on | Every search gets 3 paraphrases. Maximizes recall but adds 1 LLM call always. | |
| User-opt-in expand=true | Caller explicitly requests expansion. Client-side knowledge required. | |

**User's choice:** Threshold-gated

| Option | Description | Selected |
|--------|-------------|----------|
| Query length ≥ 6 words | Simple, fast, no ambiguity. | |
| ≥ 6 words OR question word | Also catches short questions like "Why did X fail?" | ✓ |
| You decide | Planner picks threshold. | |

**User's choice:** Query length ≥ 6 words OR contains question word (what/how/why/when)

| Option | Description | Selected |
|--------|-------------|----------|
| Graph-first, blend if low confidence | Graph first; fall back to hybrid RAG if <3 results. Optimizes common case. | ✓ |
| Always parallel: run both | Graph + hybrid concurrent, merge by RRF. Max recall but doubles DB work. | |
| Strict routing: graph OR hybrid | One path only. Simple but empty graph = no results even when hybrid finds something. | |

**User's choice:** Graph-first, blend if low confidence

---

## Cold-Start Search Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Fall back to Phase 1d FTS | Degrade to search_vector FTS when HNSW empty. Results, not an error. | ✓ |
| Return BM25-only results | BM25 tsvector path over chunks.tsv. Works before embeddings computed. | |
| Return empty + status flag | Empty results + {status: 'indexing', estimated_ready_at}. Clear but bad UX. | |

**User's choice:** Fall back to Phase 1d FTS

| Option | Description | Selected |
|--------|-------------|----------|
| search_type: hybrid_v1 \| fts_v1 \| bm25_v1 | Extend existing forward-compat field. No schema break. | ✓ |
| Add retrieval_mode enum | New separate field. More explicit but adds field not in Phase 1d schema. | |
| Always return hybrid_v1 | Simpler but misleading — caller can't detect fallback. | |

**User's choice:** search_type field: 'hybrid_v1' | 'fts_v1' | 'bm25_v1'

| Option | Description | Selected |
|--------|-------------|----------|
| Always async via APScheduler | Consistent with existing pattern. Cold-start fallback handles delay. | ✓ |
| Sync inline for small pages, async for large | Faster availability but adds latency to page writes. | |
| You decide | Planner picks based on APScheduler patterns. | |

**User's choice:** Always async via APScheduler job

---

## RRF Boost & Score Configurability

**User's choice (freeform):**
> Make RRF constants configurable via env vars (no DB reads). Defaults (must match PRD): RRF k=60, compiled_truth_boost=0.15 (apply when chunk.kind=="truth"). Env overrides: SMARTCOPILOT_RRF_K (int), SMARTCOPILOT_TRUTH_BOOST (float). Validation (clamp + warn): k in [10,200], boost in [0.0,0.5]. Ranker must use settings.

**User's choice (stale threshold, freeform):**
> Make stale threshold configurable via env var. SMARTCOPILOT_STALE_DAYS, default 30, clamp [1,365]. Stale when: latest_timeline_ts - compiled_truth_updated_at > stale_days.

**User's choice (4-layer dedup, freeform):**
> 1) Exact identity dedup: by chunk_id, keep highest score, merge retrieval_paths. 2) Near-duplicate content: by normalized content hash or similarity >= 0.92, keep highest score. 3) Per-page diversity cap: max 1 chunk per page in top-K (optionally 2 later). 4) Low-quality cutoff: drop below minimum score threshold or top_score × α. If all removed, return empty with status/meta.

---

## Claude's Discretion

- Chunker tokenizer: `tiktoken` consistent with text-embedding-3-small
- HNSW index params: m=16, ef_construction=64 (per RAG-02)
- LLM router tier model IDs: resolved from provider keys at runtime
- Embedding batch size: 100 chunks per batch
- Dedup similarity threshold (layer 2): 0.92 cosine
- Per-page cap default: max 1 chunk per page; α for low-quality cutoff: planner's discretion

## Deferred Ideas

None — discussion stayed within phase scope.
