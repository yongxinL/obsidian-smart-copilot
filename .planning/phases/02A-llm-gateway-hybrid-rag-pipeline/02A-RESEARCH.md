# Phase 02A: LLM Gateway + Hybrid RAG Pipeline - Research

**Researched:** 2026-05-15
**Domain:** LiteLLM 1.x library mode, pgvector HNSW, BM25 tsvector, RRF fusion, APScheduler
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Chunk Boundary Strategy**
- D-01: 512-token chunks, 50-token sliding-window overlap
- D-02: Timeline events: one chunk per event (kind=`event`); pad short events to ~50 tokens
- D-03: Compiled-truth: 512-token window, 50-token overlap (kind=`truth`)
- D-04: Frontmatter: single chunk per page (kind=`summary`)
- D-05: `enriched_content` fallback: when enrichment has not run, `enriched_content = text`; embedder always reads `enriched_content`
- D-06: `archived_fleeting` and `skill` page types skip chunk/embed pipeline entirely

**Intent Classifier + Query Expansion**
- D-07: Intent classifier is rule-based patterns only (no LLM call)
- D-08: Multi-query expansion threshold: fires when query length >= 6 words OR query contains question word (what/how/why/when)
- D-09: Graph-intent routing: graph-first, blend if graph returns <3 results

**Cold-Start Search Behavior**
- D-10: When HNSW is empty or embedding queue lags, fall back to Phase 1d FTS path; return page-level hits with `search_type="fts_v1"`
- D-11: `search_type` encodes actual retrieval path: `"hybrid_v1"`, `"fts_v1"`, `"bm25_v1"`
- D-12: Embedding triggered async via APScheduler job (never sync inline on page write)

**RRF Scoring + Deduplication**
- D-13: RRF constants are env-var configurable at startup: `SMARTCOPILOT_RRF_K` (default 60, clamp [10,200]); `SMARTCOPILOT_TRUTH_BOOST` (default 0.15, clamp [0.0,0.5]); `SMARTCOPILOT_STALE_DAYS` (default 30, clamp [1,365])
- D-14: 4-layer deduplication: (1) exact chunk_id dedup, (2) near-duplicate cosine ≥ 0.92, (3) per-page cap (max 1 chunk), (4) low-quality cutoff

### Claude's Discretion
- Chunker tokenizer: tiktoken (consistent with text-embedding-3-small); fallback: 4 chars/token
- HNSW params: m=16, ef_construction=64; `pgvector.register_vector` on every pool connection
- LLM tier models: cheap=GPT-4o-mini/DeepSeek-V3, balanced=GPT-4o/Sonnet, strong=o3/Opus
- Embedding batch size: 100 chunks per batch
- Embedding migration: add column → backfill concurrently → CREATE INDEX CONCURRENTLY → atomic rename; progress tracked in `system_config` table
- LiteLLM in-memory cache for query expansion (ttl=3600); no Redis dependency
- Dedup layer 2 similarity threshold: 0.92 cosine
- Per-page cap default: max 1; low-quality cutoff `α`: ~0.3

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LLM-01 | LiteLLM used as in-process Python library (never proxy) | Verified: litellm 1.83.14 installed; `acompletion`, `aembedding`, `CustomLogger` all importable |
| LLM-02 | Three model tiers: cheap/balanced/strong | `TIER_MODELS` dict in `llm/tiers.py`; resolved from settings at startup |
| LLM-03 | Cost tracking per-request via `llm_usage` table | `LLMUsage` model exists; `CustomLogger.async_log_success_event` + `completion_cost()` is the pattern |
| LLM-04 | Supported providers: OpenAI, Anthropic, Gemini, DeepSeek, OpenRouter, Ollama | LiteLLM 1.x supports all; model string format: `provider/model-id` |
| LLM-05 | Per-user encrypted keys + system fallback; resolution order per PRD §24.2 | `ProviderKey` model + `encryption.py` (Fernet) already built; `llm/keys.py` reads and decrypts |
| RAG-01 | Content-kind-aware chunking; `archived_fleeting`/`skill` skip embed | `Chunk` model fully defined; D-06 locked; `rag/chunker.py` implements |
| RAG-02 | Embeddings in pgvector HNSW at 1536 dims; `enriched_content` for embedding | HNSW index already created in migration 0001 (m=16, ef_construction=64); `register_vector` already in `database.py` |
| RAG-03 | BM25 via `tsvector` + `websearch_to_tsquery`; GIN index on `chunks.tsv` | GIN index `chunks_tsv_gin_idx` already created in migration 0001; tsv is Computed column |
| RAG-04 | Hybrid retrieval: vector + BM25 + graph via RRF `score = sum(1/(60+rank))` | `rag/reranker.py` implements; graph component is stub (Phase 2b wires graph) |
| RAG-05 | Intent classifier, multi-query expansion, compiled-truth boost, stale annotation, 4-layer dedup | `rag/intent.py` + `rag/reranker.py` |
| RAG-06 | LLM router enforced; no direct LiteLLM calls in routes/services | Ruff TID251 `banned-api` rule enforces this; `llm/router.py` is sole entry point |
| RAG-07 | Embedding migration: estimate/start/status/cancel endpoints | `routes/migration.py`; progress tracked in `system_config` JSONB |

</phase_requirements>

---

## Summary

Phase 2a activates the intelligence layer atop the Phase 1a–1d foundation. Three independent subsystems wire together: (1) the LLM router (`llm/router.py`) provides a single choke-point for all LiteLLM calls with cost tracking and per-user key injection; (2) the chunker/embedder pipeline splits vault pages into typed chunks and stores embeddings via APScheduler; (3) the hybrid retrieval pipeline upgrades the existing `brain.search` / `POST /api/v1/search` path from page-level FTS to chunk-level RRF fusion.

The foundation is already deeper than most phases start with. The `Chunk` model, `LLMUsage` model, HNSW index, and GIN BM25 index were all created in migration 0001. The `pgvector.register_vector` hook is already live in `database.py`. The `SearchResponse` model already carries a `search_type` forward-compat hook. `session_with_rls()` and `OperationContext` patterns are established. This phase writes the services that activate these dormant structures.

The primary risk is operational correctness rather than technical novelty: RLS must be enforced on every new code path (chunker, embedder, retriever, reranker); provider API keys must never leak into logs; the async/sync boundary with LiteLLM's `CustomLogger` must use `async_log_success_event` for DB writes; and Ruff TID251 must be added to pyproject.toml to gate direct LiteLLM imports at CI time.

**Primary recommendation:** Build in wave order — (Wave 0) settings + Ruff enforcement, (Wave 1) LLM router + cost tracking, (Wave 2) chunker + embedder + embed worker, (Wave 3) retriever + reranker + intent + upgraded search, (Wave 4) migration endpoints. Each wave is independently testable.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| LLM routing + cost attribution | API / Backend (`llm/router.py`) | — | All LLM calls are server-side; no client-side LLM access |
| Provider key resolution + decryption | API / Backend (`llm/keys.py`) | — | Encrypted keys live in PostgreSQL; decryption must be server-side |
| Chunk splitting + tokenization | API / Backend (`rag/chunker.py`) | — | Pure transformation; runs in embed worker and on-write path |
| Embedding generation + pgvector write | Database / Storage (`chunks.embedding`) | API Backend (embed worker) | pgvector is the store; embedding worker is the writer |
| BM25 retrieval | Database / Storage (PostgreSQL `tsvector`) | — | Computed column + GIN index; query is SQL only |
| Vector ANN retrieval | Database / Storage (pgvector HNSW) | — | PostgreSQL `<=>` operator query |
| RRF fusion + reranking | API / Backend (`rag/reranker.py`) | — | Pure Python; runs in-process after both retrieval paths return |
| Intent classification | API / Backend (`rag/intent.py`) | — | Rule-based; no external dependency; runs in API request path |
| Multi-query expansion | API / Backend (`rag/intent.py` calling `llm/router.py`) | — | LLM call gates on threshold; result feeds retriever |
| Embedding migration (online) | API / Backend (`routes/migration.py`) | Database / Storage | HTTP endpoints drive concurrent backfill; index created concurrently |
| Usage cost tracking | Database / Storage (`llm_usage` table) | API Backend (callback) | Persistent per-request record; callback writes to PostgreSQL |
| Cold-start FTS fallback | Database / Storage (PostgreSQL FTS) | API Backend | Existing `search_pages_fts()` service; triggered when HNSW empty |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `litellm` | `>=1.40,<2.0` (installed: 1.83.14) [VERIFIED: PyPI] | Multi-provider LLM routing, cost tracking, async completion/embedding | Project-locked; only new AI dependency needed |
| `tiktoken` | `>=0.7` (installed: 0.12.0) [VERIFIED: PyPI] | Tokenizer for chunk boundary calculation | Consistent with `text-embedding-3-small` (cl100k_base encoding) |
| `pgvector` | `0.4.2` [VERIFIED: PyPI] | pgvector Python bindings; `register_vector` for asyncpg | Already installed; HNSW and GIN indexes exist |
| `apscheduler` | `3.x` (installed: 3.11.2) [VERIFIED: PyPI] | Async embed worker job | Already installed; existing scheduler pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `tiktoken` fallback | N/A | Character estimate (4 chars/token) | Only when tiktoken fails for non-OpenAI content |
| LiteLLM in-memory `Cache` | built-in | Query expansion response caching | Enable for repeated identical queries; no Redis needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `litellm.CustomLogger` (callbacks) | Direct INSERT after every call | Callbacks decouple cost tracking from call sites; prefer callbacks |
| tiktoken | `len(text) / 4` estimate | tiktoken is exact; estimate is fallback only |
| APScheduler async job | Celery/background task | No Redis/Celery per project constraint; APScheduler already in use |

**Installation (new packages only):**
```bash
# litellm and tiktoken are the only new dependencies for Phase 2a
# pgvector and apscheduler already installed
pip install "litellm>=1.40,<2.0" "tiktoken>=0.7"
```

---

## Package Legitimacy Audit

> slopcheck v0.6.1 installed and run. Note: slopcheck checks npm by default; these are Python packages (PyPI). Cross-ecosystem results noted below.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `litellm` | PyPI | ~3 yrs | Very high | github.com/BerriAI/litellm | npm:OK (Python package, not npm — cross-ecosystem confusion noted) | Approved — verified via pip show (BerriAI/litellm) |
| `tiktoken` | PyPI | ~3 yrs | Very high | github.com/openai/tiktoken | npm:OK (cross-ecosystem) | Approved — official OpenAI tokenizer |
| `pgvector` | PyPI | ~3 yrs | High | github.com/pgvector/pgvector-python | npm:OK (cross-ecosystem) | Approved — official pgvector Python bindings |
| `apscheduler` | PyPI | ~14 yrs | Very high | github.com/agronholm/apscheduler | npm:SLOP (not on npm — correct, it's Python-only) | Approved — well-established Python scheduler, already installed |

**Packages removed due to slopcheck [SLOP] verdict:** none (apscheduler SLOP verdict is a false positive from wrong ecosystem — package is a legitimate PyPI package installed and in use)

**Packages flagged as suspicious [SUS]:** none

*All four packages are established Python packages verified on PyPI. slopcheck's SLOP flag on apscheduler is a cross-ecosystem false positive (npm vs. PyPI); the package has 14+ years on PyPI with very high download counts.*

---

## Architecture Patterns

### System Architecture Diagram

```
Query from MCP/REST
        │
        ▼
┌─────────────────────────────────────────┐
│         intent.py (rule-based)          │
│  ┌─────────────┬──────────────────────┐  │
│  │ short/exact │ question/long query  │  │
│  └──────┬──────┴───────────┬──────────┘  │
│         │                  │ expand      │
│         │           ┌──────▼──────────┐  │
│         │           │ llm/router.py   │  │
│         │           │ cheap tier      │  │
│         │           │ 3 paraphrases   │  │
│         │           └──────┬──────────┘  │
└─────────┼─────────────────┼─────────────┘
          │   (original +   │ paraphrases)
          ▼                 ▼
┌─────────────────────────────────────────┐
│         rag/retriever.py                │
│  ┌──────────────┐  ┌──────────────────┐ │
│  │ pgvector ANN │  │ BM25 tsvector    │ │
│  │ cosine HNSW  │  │ websearch_to_    │ │
│  │ chunks table │  │ tsquery + GIN    │ │
│  └──────┬───────┘  └────────┬─────────┘ │
│         │                   │           │
│         ▼                   ▼           │
│  ┌──────────────────────────────────┐   │
│  │ graph stub (Phase 2b wires here) │   │
│  └──────────────────────────────────┘   │
└─────────┬────────────────────────────── ┘
          │ (ranked candidates from each path)
          ▼
┌─────────────────────────────────────────┐
│         rag/reranker.py                 │
│  RRF score = Σ 1/(k + rank_i)          │
│  + 0.15 boost if chunk.kind == "truth" │
│  4-layer dedup → stale annotation      │
│  cold-start: HNSW empty? → FTS path    │
└─────────┬───────────────────────────────┘
          ▼
   SearchResponse (hybrid_v1 | fts_v1 | bm25_v1)
```

**Embed pipeline (async, not in query path):**
```
APScheduler embed_worker.py
        │
        ├─ poll chunks WHERE embedding IS NULL
        ├─ batch 100 chunks
        ├─ llm/router.py → aembedding(model="openai/text-embedding-3-small")
        ├─ assert len(vec) == 1536 before INSERT
        └─ UPDATE chunks SET embedding = $1 WHERE id = $2
```

### Recommended Project Structure
```
server/app/
├── llm/
│   ├── __init__.py
│   ├── router.py          # acompletion + aembedding wrappers; tier resolution; usage recording
│   ├── tiers.py           # TIER_MODELS dict resolved from settings at startup
│   └── keys.py            # Per-user key decryption via encryption.py + system fallback
├── rag/
│   ├── __init__.py
│   ├── chunker.py         # Content-kind-aware splitter; tiktoken boundary calc
│   ├── embedder.py        # Batch embed write; dimension assert before INSERT
│   ├── retriever.py       # Vector ANN + BM25 SQL queries (session_with_rls)
│   ├── reranker.py        # RRF fusion + truth boost + dedup + stale annotation
│   └── intent.py          # Rule-based classifier + multi-query expansion gating
├── scheduler/
│   └── jobs/
│       └── embed_worker.py  # APScheduler async job: poll + batch embed
└── routes/
    └── migration.py         # RAG-07: estimate/start/status/cancel endpoints
```

### Pattern 1: LLM Router with Cost Callback

All LiteLLM calls funnel through `llm/router.py`. The `UsageRecorder` callback writes to `llm_usage` via `async_log_success_event` (async variant required for SQLAlchemy async I/O).

```python
# Source: litellm docs + AI-SPEC §3
import litellm
from litellm import acompletion, aembedding, completion_cost
from litellm.integrations.custom_logger import CustomLogger

class UsageRecorder(CustomLogger):
    async def async_log_success_event(
        self, kwargs, response_obj, start_time, end_time
    ) -> None:
        # kwargs["metadata"]["user_id"] carries the user_id for RLS-safe attribution
        # Never log kwargs["api_key"]
        cost = completion_cost(completion_response=response_obj)
        # INSERT into llm_usage via session_with_rls(system_ctx)

# Register ONCE at app startup (lifespan):
litellm.callbacks = [UsageRecorder()]
```

**Key: use `async_log_success_event` for DB writes, NOT `log_success_event`** — the sync variant blocks the event loop when it does async SQLAlchemy I/O.

### Pattern 2: Per-Call API Key Injection (Never Global)

```python
# Source: AI-SPEC §3, CONTEXT.md D-05 (AUTH-09 pattern)
# WRONG — sets global env var, crosses user boundaries:
#   os.environ["OPENAI_API_KEY"] = decrypted_key  # NEVER
# RIGHT — per-call injection:
response = await acompletion(
    model="openai/gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}],
    api_key=decrypted_key,            # per-call, never global
    metadata={"user_id": str(user_id)},  # for cost callback
)
```

### Pattern 3: pgvector HNSW Query

```sql
-- Source: pgvector docs / existing migration 0001
-- ANN cosine similarity search (top-k = 20)
SELECT c.id, c.page_id, c.kind, c.text, c.enriched_content,
       c.embedding <=> $1::vector AS distance
FROM chunks c
WHERE c.page_id IN (
    SELECT id FROM pages WHERE vault_id = $2 AND deleted_at IS NULL
)
ORDER BY distance ASC
LIMIT $3;
```

The `<=>` operator is cosine distance (lower = more similar). The HNSW index `chunks_embedding_hnsw_idx` (m=16, ef_construction=64) was created in migration 0001 — no new migration needed for the index itself.

### Pattern 4: BM25 via tsvector

```sql
-- Source: PostgreSQL docs + existing GIN index chunks_tsv_gin_idx
SELECT c.id, c.page_id, c.kind, c.text,
       ts_rank(c.tsv, websearch_to_tsquery('english', $1)) AS rank
FROM chunks c
WHERE c.tsv @@ websearch_to_tsquery('english', $1)
  AND c.page_id IN (
      SELECT id FROM pages WHERE vault_id = $2 AND deleted_at IS NULL
  )
ORDER BY rank DESC
LIMIT $3;
```

The `tsv` column is `Computed` (`to_tsvector('english', coalesce(enriched_content, text))`). The GIN index `chunks_tsv_gin_idx` was created in migration 0001.

### Pattern 5: RRF Fusion Formula

```python
# Source: CONTEXT.md D-13; AI-SPEC §3
# RRF: score = Σ 1/(k + rank_i) where k = settings.rrf_k (default 60)
# + truth_boost when chunk.kind == "truth"
def rrf_score(
    vector_rank: int | None,
    bm25_rank: int | None,
    k: int,
    is_truth: bool,
    truth_boost: float,
) -> float:
    score = 0.0
    if vector_rank is not None:
        score += 1.0 / (k + vector_rank)
    if bm25_rank is not None:
        score += 1.0 / (k + bm25_rank)
    if is_truth:
        score += truth_boost
    return score
```

### Pattern 6: tiktoken Chunk Boundary

```python
# Source: AI-SPEC §4b; CONTEXT.md D-01
import tiktoken
_ENC = tiktoken.get_encoding("cl100k_base")  # text-embedding-3-small uses cl100k_base

def count_tokens(text: str) -> int:
    try:
        return len(_ENC.encode(text))
    except Exception:
        return len(text) // 4  # fallback: 4 chars/token

def split_into_chunks(text: str, max_tokens: int = 512, overlap: int = 50) -> list[str]:
    tokens = _ENC.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunks.append(_ENC.decode(tokens[start:end]))
        if end == len(tokens):
            break
        start = end - overlap  # sliding window
    return chunks
```

### Pattern 7: Ruff TID251 to Ban Direct LiteLLM Imports (RAG-06)

```toml
# server/pyproject.toml — add to [tool.ruff.lint]
[tool.ruff.lint]
select = ["E", "F", "UP", "B", "I", "TID"]   # add TID

[tool.ruff.lint.flake8-tidy-imports.banned-api]
"litellm" = {msg = "Import litellm only via app.llm.router — direct calls bypass cost tracking and key injection."}
"litellm.completion" = {msg = "Use app.llm.router.llm_complete instead."}
"litellm.acompletion" = {msg = "Use app.llm.router.llm_complete instead."}
"litellm.embedding" = {msg = "Use app.llm.router.embed_chunks instead."}
"litellm.aembedding" = {msg = "Use app.llm.router.embed_chunks instead."}
```

The `llm/router.py` module itself is exempt (it is the sole allowed importer) via `per-file-ignores`.

### Anti-Patterns to Avoid

- **Sync `completion()` inside async def:** Blocks the uvicorn event loop. Always use `acompletion()`/`aembedding()` in async contexts. [VERIFIED: AI-SPEC §4b]
- **Global `os.environ["OPENAI_API_KEY"]`:** Sets a process-global key that crosses user boundaries. Pass `api_key=` per-call. [VERIFIED: AI-SPEC §3 pitfall 1]
- **`log_success_event` for DB writes:** The sync callback variant blocks async I/O. Use `async_log_success_event`. [VERIFIED: litellm CustomLogger API]
- **Inline embedding on page write:** Embedding must be async via APScheduler, not blocking the write path (D-12). The cold-start fallback (D-10) handles the latency window.
- **Missing `session_with_rls()` in retriever/chunker/embedder:** RLS requires `SET app.current_user_id` on every DB session. The embed worker must use `system_operation_context` + `session_with_rls`.
- **`CREATE INDEX` (not CONCURRENTLY) for migration backfill:** Locks the table. Always `CREATE INDEX CONCURRENTLY` for the migration path.
- **Embedding without dimension assert:** Insert `assert len(embedding) == 1536` before writing to prevent dimension mismatch errors. [VERIFIED: success criterion 3]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-provider LLM routing | Custom provider dispatcher | `litellm.acompletion` / `litellm.aembedding` | Handles auth, retries, model string normalization, rate limit mapping across 100+ providers |
| LLM cost calculation | Token-count × price table | `litellm.completion_cost(response)` | LiteLLM maintains provider pricing tables; custom table is stale within weeks |
| Provider rate-limit backoff | Custom retry loop | `litellm.exceptions.RateLimitError` + exponential backoff | LiteLLM maps provider-specific HTTP 429 to a single exception type |
| Token counting for chunk boundaries | Regex/split heuristic | `tiktoken.get_encoding("cl100k_base")` | Exact BPE tokenization; heuristics drift from actual embedding model tokenizer |
| Query expansion output validation | Ad-hoc JSON parsing | `pydantic.BaseModel.model_validate_json()` | Handles malformed JSON gracefully; validates paraphrase count exactly 3 |
| pgvector codec registration | Manual asyncpg type codec | `pgvector.asyncpg.register_vector` | Already wired in `database.py`; do not duplicate |

**Key insight:** The retrieval pipeline (chunking, RRF, dedup, intent) is custom by design — but the LLM I/O layer (routing, cost, rate limits) must use LiteLLM to avoid rebuilding infrastructure that changes per provider.

---

## Common Pitfalls

### Pitfall 1: Sync CustomLogger callback blocks async event loop
**What goes wrong:** `UsageRecorder.log_success_event` (sync) does an async SQLAlchemy INSERT into `llm_usage`. The call succeeds in testing but deadlocks in production under load.
**Why it happens:** LiteLLM calls `log_success_event` from within an async context (after `await acompletion`). A sync method that internally does `asyncio.run()` or uses `async_session_factory()` directly will re-enter the event loop.
**How to avoid:** Override `async_log_success_event` instead of `log_success_event`. The `async_log_success_event(self, kwargs, response_obj, start_time, end_time)` signature is confirmed available in litellm 1.83.14.
**Warning signs:** `RuntimeError: This event loop is already running` in logs; `llm_usage` table never gets populated.

### Pitfall 2: Global API key set via `os.environ` leaks across users
**What goes wrong:** `os.environ["OPENAI_API_KEY"] = user_key` is process-global. Concurrent requests from user A and user B race; user B's request may use user A's key.
**Why it happens:** LiteLLM documentation examples often show global env var setup for simplicity. Correct pattern for multi-user is per-call `api_key=`.
**How to avoid:** Pass `api_key=` as a kwarg to every `acompletion` / `aembedding` call. Never set `os.environ["*_API_KEY"]` at runtime.
**Warning signs:** `llm_usage` records show one user's key used for another user's request; provider billing attributed to wrong user.

### Pitfall 3: Embedding dimension mismatch crashes pgvector INSERT
**What goes wrong:** A future embedding model with a different dimension (e.g., 3072 for `text-embedding-3-large`) produces vectors that silently truncate or error on INSERT into `VECTOR(1536)`.
**Why it happens:** pgvector enforces dimension at INSERT time but the error is opaque: `ERROR: expected 1536 dimensions, not 3072`.
**How to avoid:** Assert `len(embedding) == 1536` before INSERT in `embedder.py`. Log a clear error and skip the chunk rather than crashing the embed worker.
**Warning signs:** APScheduler embed worker job failure logs with pgvector dimension errors; chunks stuck with `embedding IS NULL`.

### Pitfall 4: Missing `session_with_rls` in embed worker crosses user data
**What goes wrong:** Embed worker runs as system context but writes to `chunks` for a specific user's page. Without RLS GUC set, the `SET app.current_user_id` is missing and `RESET` on pool return may leave a stale GUC.
**Why it happens:** Background jobs don't go through FastAPI's `get_db_session` dependency, so RLS discipline must be applied manually.
**How to avoid:** Use `session_with_rls(ctx)` in the embed worker just as in API routes. The `system_operation_context` bypasses RLS policy checks (the 0002 migration allows system role). The `database.py` pool reset listener (`_on_pool_reset`) is the fail-safe.
**Warning signs:** `rls_violation_count > 0` in monitoring (P1 alert).

### Pitfall 5: Ruff TID banned-api is per-module, not whole-package
**What goes wrong:** Adding `"litellm"` to `banned-api` bans ALL imports of litellm, including inside `llm/router.py` itself.
**How to avoid:** Add a `per-file-ignores` exception for `app/llm/router.py`, `app/llm/tiers.py`, and `app/llm/keys.py`. These are the only allowed importers of litellm.
**Warning signs:** Ruff CI fails on the router module itself.

### Pitfall 6: BM25 `websearch_to_tsquery` vs `to_tsquery` behavior difference
**What goes wrong:** `websearch_to_tsquery('english', 'foo bar')` does NOT require both tokens — it treats them as `foo | bar`. Direct `to_tsquery` with `&` is stricter.
**Why it happens:** `websearch_to_tsquery` matches PostgreSQL's websearch semantics (Google-like), which may return more results than expected.
**How to avoid:** Use `websearch_to_tsquery` (project-decided per RAG-03) and let RRF ranking sort quality. The wider recall benefits hybrid retrieval.
**Warning signs:** BM25 results seem noisier than expected — this is expected behavior; RRF suppresses low-quality BM25 hits.

### Pitfall 7: LiteLLM in-memory Cache is per-process
**What goes wrong:** Enabling `litellm.cache = Cache()` works in single-process mode but the APScheduler process and uvicorn process have separate in-memory caches.
**Why it happens:** Two supervisord processes → two Python processes → no shared memory.
**How to avoid:** Enable cache only for identical query expansion calls within a single uvicorn process (acceptable for the homelab use case). Do not rely on cache hits across processes. For the embed worker, caching is irrelevant (no repeated queries).
**Warning signs:** Cache hit rates appear 0% in Phoenix traces — expected; per-process cache only helps same-process repeated queries.

### Pitfall 8: `CREATE INDEX CONCURRENTLY` inside a migration transaction
**What goes wrong:** `CREATE INDEX CONCURRENTLY` cannot run inside a transaction block. Alembic wraps migrations in transactions by default.
**Why it happens:** Alembic's default `op.execute()` runs inside a transaction.
**How to avoid:** For the migration endpoint (RAG-07), execute `CREATE INDEX CONCURRENTLY` outside Alembic — use a raw asyncpg connection with `await conn.execute(...)` outside any transaction. The migration endpoint is not an Alembic migration; it's a live API endpoint.
**Warning signs:** `ERROR: CREATE INDEX CONCURRENTLY cannot run inside a transaction block`.

---

## Code Examples

### LLM Router Entry Point
```python
# Source: AI-SPEC §3 (verified: acompletion signature, CustomLogger API)
from litellm import acompletion, aembedding
from app.llm.tiers import TIER_MODELS
from app.llm.keys import resolve_api_key

async def llm_complete(
    prompt: str,
    tier: Literal["cheap", "balanced", "strong"],
    op_ctx: OperationContext,
    response_format: dict | None = None,
) -> str:
    model_id = TIER_MODELS[tier]
    provider = model_id.split("/")[0]
    api_key = await resolve_api_key(op_ctx.user_id, provider)
    kwargs: dict = dict(
        model=model_id,
        messages=[{"role": "user", "content": prompt}],
        api_key=api_key,                          # per-call; never global env
        metadata={"user_id": str(op_ctx.user_id)},
        caching=True,
        ttl=3600,                                 # in-memory cache for repeated expansion
    )
    if response_format:
        kwargs["response_format"] = response_format
    response = await acompletion(**kwargs)
    return response.choices[0].message.content
```

### Query Expansion with Pydantic Validation
```python
# Source: AI-SPEC §4b
from pydantic import BaseModel, field_validator, ValidationError

class QueryExpansion(BaseModel):
    paraphrases: list[str]

    @field_validator("paraphrases")
    @classmethod
    def exactly_three(cls, v: list[str]) -> list[str]:
        if len(v) != 3:
            raise ValueError(f"Expected 3 paraphrases, got {len(v)}")
        return v

async def expand_query(query: str, op_ctx: OperationContext) -> list[str]:
    raw = await llm_complete(
        prompt=EXPANSION_USER.format(query=query),
        tier="cheap",
        op_ctx=op_ctx,
        response_format={"type": "json_object"},
    )
    try:
        return QueryExpansion.model_validate_json(raw).paraphrases
    except (ValidationError, ValueError):
        return [query]   # graceful degradation: use original query only
```

### Stale Annotation Logic
```python
# Source: CONTEXT.md D-13
from datetime import UTC, datetime, timedelta

def is_stale(
    compiled_truth_updated_at: datetime | None,
    latest_timeline_ts: datetime | None,
    stale_days: int,
) -> bool:
    if compiled_truth_updated_at is None or latest_timeline_ts is None:
        return False
    delta = latest_timeline_ts - compiled_truth_updated_at
    return delta > timedelta(days=stale_days)
```

### Embedding Worker APScheduler Job (follows reconcile_vault.py pattern)
```python
# Source: server/app/scheduler/jobs/reconcile_vault.py (existing pattern)
# APScheduler module-level function; no closures; coalesce=True, max_instances=1

async def embed_pending_chunks() -> None:
    """Batch-embed chunks with embedding IS NULL (100 per batch)."""
    ctx = system_operation_context(request_id="embed_worker", client_name="scheduler")
    async for session in session_with_rls(ctx):
        rows = await session.execute(
            select(Chunk).where(Chunk.embedding.is_(None)).limit(100)
        )
        chunks = rows.scalars().all()
        if not chunks:
            return
        texts = [c.enriched_content or c.text for c in chunks]
        embeddings = await embed_chunks(texts, op_ctx=ctx)
        for chunk, vec in zip(chunks, embeddings, strict=True):
            assert len(vec) == 1536, f"Dimension mismatch: {len(vec)}"
            chunk.embedding = vec
        await session.commit()
```

---

## Existing Infrastructure — No Rebuild Needed

These items are **already live** from Phases 1a–1d. The planner must NOT create tasks to build them:

| Item | Location | Status |
|------|----------|--------|
| `Chunk` model (VECTOR, tsv, kind enum) | `server/app/models/chunk.py` | Built |
| `LLMUsage` model | `server/app/models/llm_usage.py` | Built |
| HNSW index (m=16, ef_construction=64) | migration 0001 | Created |
| GIN index on `chunks.tsv` | migration 0001 | Created |
| `pgvector.register_vector` on pool connect | `database.py` | Active |
| `SearchResponse` with `search_type` | `routes/search.py` | Forward-compat hook present |
| `SearchResultItem` with `chunk_hits=[]` | `routes/search.py` | Forward-compat hook present |
| `session_with_rls()` + `OperationContext` | `dependencies.py` | Active; use in all new services |
| `encrypt_provider_key` / `decrypt_provider_key` | `encryption.py` | Active; use in `llm/keys.py` |
| `ProviderKey` model | `models/provider_key.py` | Built |
| `SystemConfig` model (JSONB) | `models/system_config.py` | Built; use for migration progress |
| `search_pages_fts()` service | `services/pages.py` | Active; cold-start fallback (D-10) |
| APScheduler `run.py` + `AsyncIOScheduler` | `scheduler/run.py` | Active; add embed_worker job here |

---

## Migration Considerations

**Phase 2a requires one new Alembic migration (0005):**
- The `chunks` table and its indexes already exist (migration 0001).
- However, there may be a need to add `chunk_index` column (for `page_slug+chunk_index` dedup key per D-14) and `compiled_truth_updated_at` denorm on pages (for stale annotation per D-13).

**Check pages model for compiled_truth_updated_at:**
The pages table was built in migration 0003. The planner must verify whether `compiled_truth_updated_at` and `latest_timeline_ts` columns exist. If missing, migration 0005 adds them.

**Embedding migration endpoints (RAG-07) are NOT Alembic migrations** — they are live API endpoints that perform: `ALTER TABLE chunks ADD COLUMN embedding_new VECTOR(N)` → concurrent backfill → `CREATE INDEX CONCURRENTLY` → `ALTER TABLE chunks RENAME COLUMN` → drop old column. Progress tracked in `system_config` table (JSONB value with `{status, total, done, started_at}`).

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LiteLLM proxy (separate process) | LiteLLM library mode (in-process) | v1.0+ stable | No extra port, no proxy startup, no network hop; same API |
| `log_success_event` (sync callback) | `async_log_success_event` (async callback) | LiteLLM added async variant in 1.x | Prevents event loop blocking for DB write callbacks |
| `litellm.callbacks` string names only | `litellm.callbacks = [CustomLoggerInstance()]` | Current 1.x docs | Class instances allow custom logic per-call |
| pgvector IVFFlat index | HNSW index | pgvector 0.5.0+ | HNSW provides better recall at lower query latency; no training step needed |
| `CREATE INDEX` (locks table) | `CREATE INDEX CONCURRENTLY` | PostgreSQL 9.2+ | Zero-downtime index creation for migration path |
| Flat embedding storage | `VECTOR(1536)` column with HNSW | pgvector 0.4.0+ | Native ANN operator `<=>` with index support |

**Deprecated/outdated:**
- LiteLLM proxy mode: never used in this project per project constraint (LLM-01). Do not import `litellm.proxy`.
- IVFFlat index: replaced by HNSW for better performance. Already HNSW in migration 0001.
- `tiktoken` `encoding_for_model("text-embedding-ada-002")`: predecessor model. Use `get_encoding("cl100k_base")` directly — `text-embedding-3-small` uses the same encoding.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `latest_timeline_ts` and `compiled_truth_updated_at` columns exist on the `pages` table from Phase 1c | Migration Considerations | Migration 0005 must add them; stale annotation cannot work without them |
| A2 | The `page` model has a `note_type` field (not `page_type`) for the `archived_fleeting` / `skill` skip check | Existing Infrastructure | Embed worker skip logic uses wrong field name; test will catch this |
| A3 | LiteLLM 1.83.14's `completion_cost()` returns 0.0 for models not in its pricing table (not None/exception) | Pattern 1 | `cost_usd` stored as 0.0 for unknown models rather than error |

**If this table is empty... it is not.** A1 and A2 require verification during Wave 0 by reading the `Page` model and migration 0003 in detail.

---

## Open Questions

1. **Does `pages` have `compiled_truth_updated_at` and `latest_timeline_ts`?**
   - What we know: stale annotation (D-13) requires comparing these two timestamps per page
   - What's unclear: migration 0003 built the pages table for Phase 1c; it may or may not have added these columns
   - Recommendation: planner's Wave 0 task reads `models/page.py` and migration 0003; if missing, migration 0005 adds them

2. **How does `brain.search` upgrade interact with the existing MCP tool signature?**
   - What we know: `brain.search` in `mcp/tools/brain.py` currently calls `search_pages_fts()`; Phase 2a replaces this with `hybrid_search_service()`
   - What's unclear: the MCP tool description string says "Phase 1d: page-level only" — needs updating
   - Recommendation: Phase 2a rewrites the `brain_search` function body; the tool name/params stay identical for backward compat

3. **Graph component in RRF (RAG-04): stub or omit?**
   - What we know: RAG-04 specifies "vector + BM25 + graph via RRF" but graph traversal is Phase 2b
   - What's unclear: should Phase 2a include a 0-result graph path as a stub, or simply omit the graph term from RRF?
   - Recommendation: Per D-09, graph-intent routing routes to `brain.graph.traverse` — Phase 2a includes an empty stub return (`[]`) so the RRF formula compiles; Phase 2b replaces the stub

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | All | ✓ | 3.12.13 | — |
| `litellm` | LLM router | ✓ | 1.83.14 | — |
| `tiktoken` | Chunker | ✓ | 0.12.0 | char/4 estimate |
| `pgvector` Python | Embedder | ✓ | 0.4.2 | — |
| `apscheduler` | Embed worker | ✓ | 3.11.2 | — |
| `pytest` | Test suite | ✓ | (installed) | — |
| `testcontainers` | Integration tests | ✓ | 4.14.2 | — |
| `pytest-asyncio` | Async tests | ✓ | 1.3.0 | — |
| PostgreSQL + pgvector ext | All DB ops | ✓ (via testcontainers `pgvector/pgvector:pg16`) | pg16 | — |
| OpenAI API key (live) | Embed + expansion | ✗ (test env) | — | Mock in unit tests; integration test uses recorded fixtures or skip marker |

**Missing dependencies with no fallback:** None that block implementation.

**Missing dependencies with fallback:** Live OpenAI API key — integration tests use `pytest.mark.skip` or recorded VCR cassettes for embedding calls. Unit tests mock `aembedding`/`acompletion`.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio 1.3.0 |
| Config file | `server/pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `pytest server/app/tests/rag/ -x -m "unit"` |
| Full suite command | `pytest server/app/tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LLM-01 | LiteLLM imported only via router; no direct imports elsewhere | unit (Ruff lint) | `ruff check server/app/ --select TID` | ❌ Wave 0 (pyproject.toml change) |
| LLM-02 | Tier resolution returns correct model ID per tier name | unit | `pytest tests/llm/test_router.py::test_tier_resolution -x` | ❌ Wave 0 |
| LLM-03 | `llm_usage` row created after every `llm_complete` call | integration | `pytest tests/llm/test_router.py::test_cost_recorded -x` | ❌ Wave 1 |
| LLM-04 | Router accepts DeepSeek/Ollama model strings without error | unit (mock) | `pytest tests/llm/test_router.py::test_provider_routing -x` | ❌ Wave 1 |
| LLM-05 | User key used when present; system fallback when absent | unit | `pytest tests/llm/test_keys.py -x` | ❌ Wave 1 |
| RAG-01 | Chunker skips `archived_fleeting`/`skill`; produces typed chunks | unit | `pytest tests/rag/test_chunker.py -x` | ❌ Wave 2 |
| RAG-02 | Embed worker writes 1536-dim vector; dimension assert fires on wrong dim | unit + integration | `pytest tests/rag/test_embedder.py -x` | ❌ Wave 2 |
| RAG-03 | BM25 query returns results; GIN index used | integration | `pytest tests/rag/test_retriever.py::test_bm25 -x` | ❌ Wave 3 |
| RAG-04 | RRF fusion produces ranked results; truth chunks rank higher | unit | `pytest tests/rag/test_reranker.py::test_rrf_truth_boost -x` | ❌ Wave 3 |
| RAG-05 | 4-layer dedup removes near-duplicates; stale pages annotated | unit | `pytest tests/rag/test_reranker.py::test_dedup -x` | ❌ Wave 3 |
| RAG-05 | Cold-start: HNSW empty → search_type=fts_v1 | integration | `pytest tests/rag/test_search_fallback.py -x` | ❌ Wave 3 |
| RAG-06 | Direct `import litellm` in non-router modules fails Ruff | unit (lint) | `ruff check server/app/ --select TID` | ❌ Wave 0 |
| RAG-07 | Migration start/status/cancel endpoints return correct schema | integration | `pytest tests/routes/test_migration.py -x` | ❌ Wave 4 |
| SC-2a | `brain.search` with semantic query returns `search_type=hybrid_v1` | integration | `pytest tests/integration/test_phase_2a_acceptance.py -x` | ❌ Wave 4 |

### Sampling Rate
- **Per task commit:** `pytest server/app/tests/rag/ -x -m "unit"` (< 10s)
- **Per wave merge:** `pytest server/app/tests/ -x` (full suite)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `server/app/tests/llm/__init__.py` + `test_router.py` — covers LLM-01, LLM-02, LLM-03
- [ ] `server/app/tests/llm/test_keys.py` — covers LLM-05
- [ ] `server/app/tests/rag/__init__.py` + `test_chunker.py` — covers RAG-01
- [ ] `server/app/tests/rag/test_embedder.py` — covers RAG-02
- [ ] `server/app/tests/rag/test_retriever.py` — covers RAG-03
- [ ] `server/app/tests/rag/test_reranker.py` — covers RAG-04, RAG-05
- [ ] `server/app/tests/rag/test_search_fallback.py` — covers RAG-05 cold-start
- [ ] `server/app/tests/routes/test_migration.py` — covers RAG-07
- [ ] `server/app/tests/integration/test_phase_2a_acceptance.py` — phase acceptance
- [ ] `server/pyproject.toml` TID rule addition — covers RAG-06 lint gate

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No (no new auth paths) | — |
| V3 Session Management | No | — |
| V4 Access Control | Yes | `session_with_rls()` + `SET app.current_user_id` on every DB path in chunker/embedder/retriever |
| V5 Input Validation | Yes | Pydantic `QueryExpansion` validator; `SearchIn` already validated; chunk text validated via tiktoken |
| V6 Cryptography | Yes | Provider keys decrypted via Fernet in `llm/keys.py`; never logged; `api_key=` passed per-call only |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Provider API key in logs | Information Disclosure | Scrub `api_key` from all LiteLLM kwargs before logging; CustomLogger callback must NOT log `kwargs["api_key"]` |
| Cross-user chunk retrieval via missing RLS | Tampering + Info Disclosure | `SET app.current_user_id` in every DB session; `RESET` in finally; pool reset listener as fail-safe |
| Cost runaway via unbounded multi-query expansion | Denial of Service (financial) | D-08 threshold gate (rule-based, no LLM call); D-13 per-query cost ceiling at $0.01 |
| Embedding dimension confusion (model swap) | Tampering | `assert len(vec) == 1536` before INSERT; fail-fast rather than corrupt index |
| Fabricated chunk content in search results | Integrity | Context faithfulness: all `SearchResultItem.content` must be verbatim from `chunks` table (no LLM synthesis in Phase 2a) |

---

## Sources

### Primary (HIGH confidence)
- `server/app/models/chunk.py` — Chunk model with VECTOR(1536), tsv Computed, kind enum [VERIFIED: codebase read]
- `server/app/models/llm_usage.py` — LLMUsage model columns [VERIFIED: codebase read]
- `server/app/database.py` — register_vector already wired via pool event [VERIFIED: codebase read]
- `server/alembic/versions/0001_initial_schema.py` — HNSW and GIN indexes created [VERIFIED: codebase read]
- `server/app/routes/search.py` — SearchResponse with search_type forward-compat hook [VERIFIED: codebase read]
- `server/app/scheduler/jobs/reconcile_vault.py` — APScheduler job pattern [VERIFIED: codebase read]
- litellm 1.83.14 installed [VERIFIED: pip show]
- `CustomLogger.async_log_success_event(self, kwargs, response_obj, start_time, end_time)` signature [VERIFIED: Python introspection]
- `litellm.completion_cost()` signature [VERIFIED: Python introspection]
- `litellm.caching.Cache` importable [VERIFIED: Python import]
- tiktoken `cl100k_base` encoding for `text-embedding-3-small` [VERIFIED: Python test]
- Ruff TID251 (`banned-api`) rule available [VERIFIED: ruff rule TID251]
- pgvector 0.4.2 installed [VERIFIED: pip show]
- apscheduler 3.11.2 installed [VERIFIED: pip show]

### Secondary (MEDIUM confidence)
- LiteLLM library mode docs: https://docs.litellm.ai/docs/completion/input [CITED: AI-SPEC]
- LiteLLM custom callbacks: https://docs.litellm.ai/docs/observability/custom_callback [CITED: AI-SPEC]
- LiteLLM cost tracking: https://docs.litellm.ai/docs/completion/token_usage [CITED: AI-SPEC]
- pgvector HNSW docs: `CREATE INDEX ... USING hnsw (...) WITH (m=16, ef_construction=64)` [CITED: existing migration confirms syntax]
- Hybrid RRF NDCG benchmarks: arxiv.org/html/2604.01733v1 [CITED: AI-SPEC §1b]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified installed and importable
- Architecture: HIGH — existing codebase read confirms all integration points; patterns match Phase 1a–1d conventions
- Pitfalls: HIGH — 7 of 8 pitfalls verified against actual codebase or official API introspection; 1 (BM25 behavior) is documented PostgreSQL behavior
- Test infrastructure: HIGH — existing conftest.py and testcontainers pattern confirmed

**Research date:** 2026-05-15
**Valid until:** 2026-06-15 (stable ecosystem; litellm releases frequently but 1.x API is stable)
