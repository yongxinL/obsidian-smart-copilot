# Phase 2a: LLM Gateway + Hybrid RAG Pipeline - Pattern Map

**Mapped:** 2026-05-15
**Files analyzed:** 14 new/modified files
**Analogs found:** 14 / 14

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `server/app/llm/__init__.py` | config | — | `server/app/auth/__init__.py` | exact (empty init) |
| `server/app/llm/router.py` | service | request-response | `server/app/services/provider_keys.py` | role-match |
| `server/app/llm/tiers.py` | config | — | `server/app/settings.py` | role-match |
| `server/app/llm/keys.py` | service | request-response | `server/app/services/provider_keys.py` | exact |
| `server/app/rag/__init__.py` | config | — | `server/app/auth/__init__.py` | exact (empty init) |
| `server/app/rag/chunker.py` | service | transform | `server/app/vault/parser.py` | role-match |
| `server/app/rag/embedder.py` | service | batch | `server/app/scheduler/jobs/reconcile_vault.py` | role-match |
| `server/app/rag/retriever.py` | service | CRUD | `server/app/services/pages.py` (`search_pages_fts`) | exact |
| `server/app/rag/reranker.py` | service | transform | `server/app/services/pages.py` | role-match |
| `server/app/rag/intent.py` | service | request-response | `server/app/services/pages.py` | role-match |
| `server/app/scheduler/jobs/embed_worker.py` | scheduler | batch | `server/app/scheduler/jobs/reconcile_vault.py` | exact |
| `server/app/routes/migration.py` | route | request-response | `server/app/routes/pages.py` | exact |
| `server/app/routes/search.py` | route | request-response | `server/app/routes/search.py` (modified) | exact (self) |
| `server/pyproject.toml` | config | — | `server/pyproject.toml` (modified) | exact (self) |

---

## Pattern Assignments

### `server/app/llm/router.py` (service, request-response)

**Analog:** `server/app/services/provider_keys.py`

**Imports pattern** (`provider_keys.py` lines 1-19):
```python
from __future__ import annotations

import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import SYSTEM_USER_ID, OperationContext
from app.encryption import decrypt_provider_key, encrypt_provider_key
from app.models.provider_key import ProviderKey
```

For `llm/router.py`, adapt to:
```python
from __future__ import annotations

from typing import Literal

import litellm
from litellm import acompletion, aembedding, completion_cost
from litellm.integrations.custom_logger import CustomLogger

from app.auth.context import OperationContext
from app.llm.keys import resolve_api_key
from app.llm.tiers import TIER_MODELS
```

**Core pattern — service function signature** (`provider_keys.py` lines 45-51):
```python
async def set_provider_key(
    session: AsyncSession,
    ctx: OperationContext,
    *,
    provider: str,
    plaintext: str,
) -> ProviderKey:
```

For `llm/router.py`, signature follows the same `(session, ctx, *, keyword_args)` convention:
```python
async def llm_complete(
    session: AsyncSession,
    ctx: OperationContext,
    *,
    prompt: str,
    tier: Literal["cheap", "balanced", "strong"],
    response_format: dict | None = None,
) -> str:
    model_id = TIER_MODELS[tier]
    provider = model_id.split("/")[0]
    api_key = await resolve_api_key(session, ctx, provider=provider)
    response = await acompletion(
        model=model_id,
        messages=[{"role": "user", "content": prompt}],
        api_key=api_key,                          # per-call; NEVER os.environ
        metadata={"user_id": str(ctx.user_id)},  # for UsageRecorder callback
        caching=True,
        ttl=3600,
    )
    return response.choices[0].message.content
```

**Cost-callback pattern** (RESEARCH.md Pattern 1):
```python
class UsageRecorder(CustomLogger):
    async def async_log_success_event(
        self, kwargs, response_obj, start_time, end_time
    ) -> None:
        # MUST be async_log_success_event, NOT log_success_event (Pitfall 1)
        # kwargs["api_key"] MUST NOT be logged (security)
        cost = completion_cost(completion_response=response_obj)
        metadata = kwargs.get("metadata") or {}
        user_id = metadata.get("user_id")
        # INSERT into llm_usage via session_with_rls(system_ctx)

# Register ONCE at app startup (main.py lifespan):
litellm.callbacks = [UsageRecorder()]
```

**Error handling pattern** (`provider_keys.py` lines 20-23):
```python
class MissingProviderKey(Exception):
    def __init__(self, provider: str) -> None:
        self.provider = provider
```
For router: define `LLMRouterError(Exception)` similarly — one typed exception per failure mode.

---

### `server/app/llm/keys.py` (service, request-response)

**Analog:** `server/app/services/provider_keys.py` — exact match

**Imports pattern** (lines 1-19 of `provider_keys.py`):
```python
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import SYSTEM_USER_ID, OperationContext
from app.encryption import decrypt_provider_key
from app.models.provider_key import ProviderKey
```

**Core pattern — PRD §24.2 resolution order** (`provider_keys.py` lines 114-133):
```python
async def resolve_key(
    session: AsyncSession,
    ctx: OperationContext,
    *,
    provider: str,
) -> str:
    """AUTH-10 / PRD §24.2: per-user key first, system shared key fallback, else error."""
    # 1. Per-user
    user_row = await get_for_user(session, user_id=ctx.user_id, provider=provider)
    if user_row is not None:
        return decrypt_provider_key(user_row.encrypted_key)
    # 2. System shared (system user owns the fallback row)
    sys_row = await get_for_user(session, user_id=SYSTEM_USER_ID, provider=provider)
    if sys_row is not None:
        return decrypt_provider_key(sys_row.encrypted_key)
    # 3. Neither — error envelope
    raise MissingProviderKey(provider)
```

`llm/keys.py` wraps `resolve_key` from `provider_keys.py` (or imports it directly) and is named `resolve_api_key` to match `llm/router.py`'s call site.

---

### `server/app/llm/tiers.py` (config)

**Analog:** `server/app/settings.py`

**Settings pattern** (lines 1-87 of `settings.py`):
```python
from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )
    # Phase section comment per convention (lines 52-68):
    # --- Phase 2a: LLM Gateway + Hybrid RAG ---
    llm_tier_cheap: str = Field(default="openai/gpt-4o-mini")
    llm_tier_balanced: str = Field(default="anthropic/claude-sonnet-4-5")
    llm_tier_strong: str = Field(default="openai/o3")
```

`tiers.py` builds `TIER_MODELS` dict from `settings` at module load, e.g.:
```python
from app.settings import settings

TIER_MODELS: dict[str, str] = {
    "cheap": settings.llm_tier_cheap,
    "balanced": settings.llm_tier_balanced,
    "strong": settings.llm_tier_strong,
}
```

RRF constants (`settings.py` extension, D-13 — add to `Settings` class):
```python
# --- Phase 2a: RRF + RAG ---
rrf_k: int = Field(default=60)
truth_boost: float = Field(default=0.15)
stale_days: int = Field(default=30)

@field_validator("rrf_k")
@classmethod
def clamp_rrf_k(cls, v: int) -> int:
    clamped = max(10, min(200, v))
    if clamped != v:
        warnings.warn(f"SMARTCOPILOT_RRF_K {v} out of range [10,200]; clamped to {clamped}", ...)
    return clamped
```
Pattern for field validators with clamp+warn: `settings.py` lines 70-83 (`validate_fernet_key`).

---

### `server/app/rag/chunker.py` (service, transform)

**Analog:** `server/app/vault/parser.py` — pure transform, no DB I/O

**Imports pattern** (vault/parser.py, typical transform module):
```python
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal
```

For `chunker.py`:
```python
from __future__ import annotations

import tiktoken
from dataclasses import dataclass
from typing import Literal

from app.models.chunk import Chunk  # kind enum reference

_ENC = tiktoken.get_encoding("cl100k_base")  # module-level singleton (D-01)
```

**Core transform pattern** (RESEARCH.md Pattern 6):
```python
def count_tokens(text: str) -> int:
    try:
        return len(_ENC.encode(text))
    except Exception:
        return len(text) // 4  # fallback: 4 chars/token (D-Claude discretion)

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

**Skip-check pattern** (mirrors D-06, analogous to reconciler's `continue` guards):
```python
_SKIP_NOTE_TYPES = frozenset({"archived_fleeting", "skill"})

def should_skip_page(note_type: str) -> bool:
    """D-06: archived_fleeting and skill pages skip chunk/embed pipeline."""
    return note_type in _SKIP_NOTE_TYPES
```

**Error handling:** pure transform; raises `ValueError` for invalid inputs (no try/except at module level). Caller (embed_worker) wraps in `except Exception` per reconcile_vault pattern (line 102).

---

### `server/app/rag/embedder.py` (service, batch)

**Analog:** `server/app/scheduler/jobs/reconcile_vault.py` — batch DB write pattern

**Imports pattern** (`reconcile_vault.py` lines 1-28):
```python
from __future__ import annotations

import structlog
from sqlalchemy import select

from app.auth.context import system_operation_context
from app.dependencies import session_with_rls
from app.models.page import Page
```

For `embedder.py`:
```python
from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import OperationContext
from app.llm.router import embed_chunks
from app.models.chunk import Chunk

log = structlog.get_logger("smart_copilot.embedder")
```

**Core batch pattern** (RESEARCH.md — Embedding Worker pattern):
```python
async def embed_batch(
    session: AsyncSession,
    ctx: OperationContext,
    chunks: list[Chunk],
) -> int:
    """Embed a batch of chunks and write vectors to DB. Returns count written."""
    texts = [c.enriched_content or c.text for c in chunks]
    embeddings = await embed_chunks(texts, op_ctx=ctx)
    written = 0
    for chunk, vec in zip(chunks, embeddings, strict=True):
        assert len(vec) == 1536, f"Dimension mismatch: expected 1536, got {len(vec)}"
        chunk.embedding = vec
        written += 1
    await session.flush()
    return written
```

**Error handling** (`reconcile_vault.py` lines 102-103, 117-122):
```python
except Exception as exc:  # noqa: BLE001
    log.error("embed_batch_failed", chunk_id=str(chunk.id), error=str(exc))
    # Skip individual chunk; do not crash the batch
```

---

### `server/app/rag/retriever.py` (service, CRUD)

**Analog:** `server/app/services/pages.py` (`search_pages_fts`, lines 500-574) — exact same SQL query pattern with `session_with_rls`

**Imports pattern** (`pages.py` lines 1-48):
```python
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import OperationContext
```

For `retriever.py`:
```python
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import OperationContext
```

**Vector ANN query pattern** (RESEARCH.md Pattern 3):
```python
@dataclass(frozen=True, slots=True)
class VectorHit:
    chunk_id: uuid.UUID
    page_id: uuid.UUID
    kind: str
    text: str
    enriched_content: str | None
    distance: float

async def vector_search(
    session: AsyncSession,
    ctx: OperationContext,
    *,
    vault_id: uuid.UUID,
    query_embedding: list[float],
    limit: int = 20,
) -> list[VectorHit]:
    sql = """
        SELECT c.id, c.page_id, c.kind, c.text, c.enriched_content,
               c.embedding <=> :qvec::vector AS distance
        FROM chunks c
        WHERE c.page_id IN (
            SELECT id FROM pages WHERE vault_id = :vid AND deleted_at IS NULL
        )
        ORDER BY distance ASC
        LIMIT :lim
    """
    rows = (
        (await session.execute(text(sql), {"qvec": str(query_embedding), "vid": str(vault_id), "lim": limit}))
        .mappings().all()
    )
    return [VectorHit(...) for r in rows]
```

**BM25 query pattern** (RESEARCH.md Pattern 4):
```python
@dataclass(frozen=True, slots=True)
class BM25Hit:
    chunk_id: uuid.UUID
    page_id: uuid.UUID
    kind: str
    text: str
    rank: float

async def bm25_search(
    session: AsyncSession,
    ctx: OperationContext,
    *,
    vault_id: uuid.UUID,
    query: str,
    limit: int = 20,
) -> list[BM25Hit]:
    sql = """
        SELECT c.id, c.page_id, c.kind, c.text,
               ts_rank(c.tsv, websearch_to_tsquery('english', :q)) AS rank
        FROM chunks c
        WHERE c.tsv @@ websearch_to_tsquery('english', :q)
          AND c.page_id IN (
              SELECT id FROM pages WHERE vault_id = :vid AND deleted_at IS NULL
          )
        ORDER BY rank DESC
        LIMIT :lim
    """
    rows = (
        (await session.execute(text(sql), {"q": query, "vid": str(vault_id), "lim": limit}))
        .mappings().all()
    )
    return [BM25Hit(...) for r in rows]
```

**Cold-start fallback pattern** — when HNSW index returns 0 results:
```python
# mirrors search_endpoint in routes/search.py calling search_pages_fts as fallback
from app.services.pages import search_pages_fts

if not vector_hits:
    return await search_pages_fts(session, ctx, vault_id=vault_id, query=query, limit=limit)
```

---

### `server/app/rag/reranker.py` (service, transform)

**Analog:** `server/app/services/pages.py` — pure in-process transform, dataclass results

**Dataclass pattern** (`pages.py` lines 439-497, frozen dataclasses):
```python
@dataclass(frozen=True, slots=True)
class RankedResult:
    chunk_id: uuid.UUID
    page_id: uuid.UUID
    page_slug: str
    kind: str
    text: str
    rrf_score: float
    retrieval_paths: list[str]
    is_stale: bool
    stale_days: int | None
```

**RRF formula** (RESEARCH.md Pattern 5):
```python
from app.settings import settings

def rrf_score(
    vector_rank: int | None,
    bm25_rank: int | None,
    is_truth: bool,
) -> float:
    k = settings.rrf_k
    score = 0.0
    if vector_rank is not None:
        score += 1.0 / (k + vector_rank)
    if bm25_rank is not None:
        score += 1.0 / (k + bm25_rank)
    if is_truth:
        score += settings.truth_boost
    return score
```

**Stale annotation** (RESEARCH.md code example):
```python
from datetime import UTC, datetime, timedelta

def is_stale(
    compiled_truth_updated_at: datetime | None,
    latest_timeline_ts: datetime | None,
) -> bool:
    if compiled_truth_updated_at is None or latest_timeline_ts is None:
        return False
    delta = latest_timeline_ts - compiled_truth_updated_at
    return delta > timedelta(days=settings.stale_days)
```

**Deduplication pattern** (D-14, implemented as pure in-process transform):
```python
def dedup_results(candidates: list[RankedResult], top_k: int = 20) -> list[RankedResult]:
    # Layer 1: exact chunk_id dedup (keep highest score)
    seen_chunks: dict[uuid.UUID, RankedResult] = {}
    for r in sorted(candidates, key=lambda x: x.rrf_score, reverse=True):
        if r.chunk_id not in seen_chunks:
            seen_chunks[r.chunk_id] = r

    # Layer 2: near-duplicate content hash (cosine >= 0.92 handled in retriever)
    # Layer 3: per-page cap (max 1 chunk per page)
    seen_pages: dict[uuid.UUID, RankedResult] = {}
    for r in seen_chunks.values():
        if r.page_id not in seen_pages:
            seen_pages[r.page_id] = r

    # Layer 4: low-quality cutoff (drop below top_score * 0.3)
    ranked = sorted(seen_pages.values(), key=lambda x: x.rrf_score, reverse=True)
    if ranked:
        threshold = ranked[0].rrf_score * 0.3
        ranked = [r for r in ranked if r.rrf_score >= threshold]

    return ranked[:top_k]
```

---

### `server/app/rag/intent.py` (service, request-response)

**Analog:** `server/app/services/pages.py` — transport-agnostic service with `OperationContext`

**Imports pattern** (`pages.py` lines 1-48):
```python
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ValidationError, field_validator

from app.auth.context import OperationContext
from app.llm.router import llm_complete
```

**Pydantic validation pattern for query expansion** (RESEARCH.md code example):
```python
class QueryExpansion(BaseModel):
    paraphrases: list[str]

    @field_validator("paraphrases")
    @classmethod
    def exactly_three(cls, v: list[str]) -> list[str]:
        if len(v) != 3:
            raise ValueError(f"Expected 3 paraphrases, got {len(v)}")
        return v

async def expand_query(
    session: AsyncSession,
    query: str,
    op_ctx: OperationContext,
) -> list[str]:
    raw = await llm_complete(
        session, op_ctx,
        prompt=EXPANSION_PROMPT.format(query=query),
        tier="cheap",
        response_format={"type": "json_object"},
    )
    try:
        return QueryExpansion.model_validate_json(raw).paraphrases
    except (ValidationError, ValueError):
        return [query]  # graceful degradation
```

**Rule-based classifier pattern** (D-07, no LLM call):
```python
import re

_QUESTION_WORDS = re.compile(r"\b(what|how|why|when|who|where)\b", re.IGNORECASE)
_GRAPH_INTENT = re.compile(r"\[\[.+?\]\]")
_WEB_PREFIX = re.compile(r"^@web\b", re.IGNORECASE)

@dataclass(frozen=True, slots=True)
class IntentResult:
    mode: Literal["hybrid", "graph", "web_stub", "exact"]
    should_expand: bool

def classify_intent(query: str) -> IntentResult:
    """D-07: rule-based only, no LLM call."""
    if _WEB_PREFIX.match(query):
        return IntentResult(mode="web_stub", should_expand=False)
    if _GRAPH_INTENT.search(query):
        return IntentResult(mode="graph", should_expand=False)
    words = query.split()
    should_expand = len(words) >= 6 or bool(_QUESTION_WORDS.search(query))
    return IntentResult(mode="hybrid", should_expand=should_expand)
```

---

### `server/app/scheduler/jobs/embed_worker.py` (scheduler, batch)

**Analog:** `server/app/scheduler/jobs/reconcile_vault.py` — exact structural match

**Full pattern** (`reconcile_vault.py` lines 1-131):

**Module docstring pattern** (lines 1-10):
```python
"""IDX-04: Lightweight vault reconciliation job (D-08).

Runs every 5 minutes via APScheduler. ...

CLAUDE.md: module-level function, no closures — APScheduler pickles job args.
D-08: coalesce=True, max_instances=1 — one run at a time.
"""
```

**Imports pattern** (lines 12-28):
```python
from __future__ import annotations

import structlog
from sqlalchemy import select

from app.auth.context import system_operation_context
from app.dependencies import session_with_rls
from app.models.chunk import Chunk
```

**Core job function pattern** (lines 31-131):
```python
async def embed_pending_chunks() -> None:
    """Batch-embed chunks with embedding IS NULL (100 per batch)."""
    ctx = system_operation_context(
        request_id="embed_worker", client_name="scheduler"
    )
    async for session in session_with_rls(ctx):
        try:
            rows = await session.execute(
                select(Chunk).where(Chunk.embedding.is_(None)).limit(100)
            )
            chunks = rows.scalars().all()
            if not chunks:
                return
            await embed_batch(session, ctx, chunks)
            await session.commit()
        except Exception as exc:  # noqa: BLE001
            log.error("embed_worker_failed", error=str(exc))
            await session.rollback()
    log.info("embed_worker_complete")
```

**Registration in `scheduler/run.py`** (lines 37-45 pattern):
```python
scheduler.add_job(
    embed_pending_chunks,
    "interval",
    minutes=1,
    id="embed_pending_chunks",
    replace_existing=True,
    coalesce=True,      # prevent pile-up
    max_instances=1,    # only one run at a time
)
```

---

### `server/app/routes/migration.py` (route, request-response)

**Analog:** `server/app/routes/pages.py` — thin route, Pydantic response models, `_http_error` helper

**Imports pattern** (`pages.py` lines 1-38):
```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import OperationContext
from app.auth.deps import require_user
from app.dependencies import get_db_session
```

**Response model pattern** (`pages.py` lines 43-112):
```python
class MigrationEstimateOut(BaseModel):
    total_chunks: int
    embedded_chunks: int
    pending_chunks: int
    estimated_minutes: float

class MigrationStatusOut(BaseModel):
    status: str  # "idle" | "running" | "complete" | "failed"
    total: int
    done: int
    started_at: str | None
    error: str | None
```

**`_http_error` helper pattern** (`pages.py` lines 131-135):
```python
def _http_error(status_code: int, code: str, message: str, **details) -> HTTPException:
    detail = {"error": {"code": code, "message": message}}
    if details:
        detail["error"]["details"] = details
    return HTTPException(status_code=status_code, detail=detail)
```

**Admin-only guard pattern** (`pages.py` line 143):
```python
ctx: OperationContext = Depends(require_user),  # noqa: B008
```
For migration endpoints (admin-only), use `Depends(require_admin)` from `app.auth.deps`.

**Thin endpoint body pattern** (`pages.py` lines 139-153):
```python
@router.post("/migration/start", response_model=MigrationStatusOut)
async def migration_start(
    ctx: OperationContext = Depends(require_user),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> MigrationStatusOut:
    try:
        result = await migration_service.start_migration(session, ctx)
    except SomeServiceError as exc:
        raise _http_error(409, "conflict", str(exc)) from None
    return MigrationStatusOut(...)
```

---

### `server/app/routes/search.py` (route, request-response — MODIFIED)

**Analog:** `server/app/routes/search.py` (self — existing file to modify)

**Existing `SearchIn`, `SearchResultItem`, `SearchResponse`** (lines 21-43):
```python
class SearchIn(BaseModel):
    query: str = Field(..., min_length=1, max_length=512)
    limit: int = Field(default=20, ge=1, le=100)
    namespace: Literal["private", "shared", "all"] = "private"

class SearchResultItem(BaseModel):
    slug: str
    title: str | None
    note_type: str
    score: float
    snippet: str
    matched_fields: list[str]
    page_id: uuid.UUID
    updated_at: datetime
    chunk_hits: list = Field(default_factory=list)  # forward-compat: Phase 2a fills this

class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    total: int
    query: str
    search_type: str = "fts_v1"  # D-02 forward-compat hook
```

**Phase 2a extends `SearchResultItem.chunk_hits`** to a typed list, and extends `search_type` to return `"hybrid_v1"` or `"bm25_v1"`. The endpoint body replaces `search_pages_fts` with `hybrid_search_service`.

**Endpoint upgrade pattern** (lines 46-78):
```python
@router.post("/search", response_model=SearchResponse)
async def search_endpoint(
    payload: SearchIn,
    ctx: OperationContext = Depends(require_user),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> SearchResponse:
    try:
        vault_id = await resolve_user_vault_id(session, ctx.user_id)
    except VaultNotFound as exc:
        raise HTTPException(status_code=404, detail={...}) from None
    try:
        # Phase 2a: replace search_pages_fts with hybrid_search_service
        result = await hybrid_search_service(session, ctx, vault_id=vault_id, ...)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={...}) from None
    return SearchResponse(
        results=[...],
        total=len(result.items),
        query=payload.query,
        search_type=result.search_type,  # "hybrid_v1" | "fts_v1" | "bm25_v1"
    )
```

---

### `server/pyproject.toml` (config — MODIFIED)

**Analog:** `server/pyproject.toml` (self — existing file to modify)

**Current `[tool.ruff.lint]` block** (lines 20-21):
```toml
[tool.ruff.lint]
select = ["E", "F", "UP", "B", "I"]
ignore = ["E501"]
```

**Phase 2a adds TID rule** (RESEARCH.md Pattern 7):
```toml
[tool.ruff.lint]
select = ["E", "F", "UP", "B", "I", "TID"]
ignore = ["E501"]

[tool.ruff.lint.flake8-tidy-imports.banned-api]
"litellm" = {msg = "Import litellm only via app.llm.router — direct calls bypass cost tracking and key injection."}
"litellm.completion" = {msg = "Use app.llm.router.llm_complete instead."}
"litellm.acompletion" = {msg = "Use app.llm.router.llm_complete instead."}
"litellm.embedding" = {msg = "Use app.llm.router.embed_chunks instead."}
"litellm.aembedding" = {msg = "Use app.llm.router.embed_chunks instead."}
```

**`per-file-ignores` extension** (lines 24-27 — extend existing block):
```toml
[tool.ruff.lint.per-file-ignores]
"alembic/versions/*.py" = ["E402"]
"app/tests/**/*.py" = ["B904", "E402", "E902", "F841", "S101"]
"app/models/*.py" = ["F821"]
"app/llm/router.py" = ["TID251"]   # sole allowed litellm importer
"app/llm/tiers.py" = ["TID251"]    # resolves model IDs from settings
"app/llm/keys.py" = ["TID251"]     # may import litellm.exceptions
```

**pytest markers extension** (lines 41-47 — extend existing markers list):
```toml
markers = [
    "integration: ...",
    "unit: ...",
    "auth: ...",
    "vault: ...",
    "rag: Phase 2a RAG pipeline tests (covers RAG-01..07, LLM-01..05)",
    "llm: Phase 2a LLM router + cost tracking tests",
]
```

---

### Test Files

#### `server/app/tests/llm/test_router.py` (test, unit+integration)

**Analog:** `server/app/tests/auth/test_provider_keys.py` — same service test pattern

**Test structure pattern** (`tests/vault/test_pages_service.py` lines 1-37):
```python
"""Phase 2a LLM router tests — LLM-01, LLM-02, LLM-03."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

pytestmark = [pytest.mark.llm, pytest.mark.unit]

def _ctx_for(user_id, role="user"):
    from app.auth.context import OperationContext
    return OperationContext(
        user_id=user_id, role=role, transport="rest", remote=True,
        client_name="test", request_id="test",
    )
```

**Async mock pattern** (for mocking `acompletion`/`aembedding`):
```python
@pytest.mark.asyncio
async def test_tier_resolution(db_session, seed_user):
    with patch("app.llm.router.acompletion", new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = _mock_response(content="hello")
        ctx = _ctx_for(seed_user)
        result = await llm_complete(db_session, ctx, prompt="test", tier="cheap")
        assert result == "hello"
        call_kwargs = mock_complete.call_args.kwargs
        assert "gpt-4o-mini" in call_kwargs["model"]
```

#### `server/app/tests/rag/test_chunker.py` (test, unit)

**Analog:** `server/app/tests/vault/test_parser.py` — pure transform unit tests, no DB

```python
"""Phase 2a chunker unit tests — RAG-01."""
from __future__ import annotations
import pytest
pytestmark = [pytest.mark.rag, pytest.mark.unit]

from app.rag.chunker import split_into_chunks, should_skip_page, count_tokens
```

#### `server/app/tests/integration/test_phase_2a_acceptance.py` (test, integration)

**Analog:** `server/app/tests/integration/test_phase_1d_acceptance.py` — integration acceptance

```python
"""Phase 2a acceptance gate — SC-2a: brain.search returns search_type=hybrid_v1."""
from __future__ import annotations
import pytest
pytestmark = [pytest.mark.rag, pytest.mark.integration]
```

---

## Shared Patterns

### RLS Session Discipline
**Source:** `server/app/dependencies.py` lines 106-140 (`session_with_rls`)
**Apply to:** `llm/router.py` (UsageRecorder callback), `rag/retriever.py`, `rag/embedder.py`, `scheduler/jobs/embed_worker.py`, `routes/migration.py`

```python
# ALL DB operations — mandatory pattern (even in background jobs):
async for session in session_with_rls(ctx):
    try:
        # ... DB work ...
        await session.commit()
    except Exception as exc:  # noqa: BLE001
        log.error("operation_failed", error=str(exc))
        await session.rollback()
```

For background jobs: use `system_operation_context(request_id="...", client_name="scheduler")`.

### Structlog Logging
**Source:** `server/app/scheduler/jobs/reconcile_vault.py` line 28
**Apply to:** All new service files (`llm/router.py`, `rag/*.py`, `scheduler/jobs/embed_worker.py`)

```python
import structlog
log = structlog.get_logger("smart_copilot.<module_name>")
# Usage: log.info("event_name", key=value, ...)
# Never log kwargs["api_key"] or any plaintext secret
```

### OperationContext Service Signature
**Source:** `server/app/services/pages.py` lines 149-156
**Apply to:** All new service functions in `rag/` and `llm/`

```python
async def service_function(
    session: AsyncSession,
    ctx: OperationContext,
    *,
    # keyword-only args follow
) -> ReturnType:
```

No FastAPI types (`Request`, `Response`, `Depends`) in service files. Services are transport-agnostic.

### Error Envelope
**Source:** `server/app/mcp/tools/brain.py` lines 46-50 (`_err`)
**Apply to:** MCP tool (`brain.search` upgrade), route helpers

```python
def _err(code: str, message: str, **details) -> dict:
    payload: dict = {"error": {"code": code, "message": message}}
    if details:
        payload["error"]["details"] = details
    return payload
```

For routes, use `_http_error` from `pages.py` lines 131-135.

### Pydantic Response Models
**Source:** `server/app/routes/pages.py` lines 43-112; `server/app/routes/search.py` lines 21-43
**Apply to:** `routes/migration.py` response models, `SearchResultItem` extension

```python
class SomeOut(BaseModel):
    field: type
    optional_field: type | None = None
```

`model_config = ConfigDict(from_attributes=True)` only needed when building from ORM objects (see `provider_keys.py` lines 28-29).

### `from __future__ import annotations`
**Source:** Every existing source file in the codebase
**Apply to:** All new files — first line after module docstring (if any)

---

## Model Observations (no rebuild needed)

### Confirmed existing columns
- `Chunk` model (`server/app/models/chunk.py` lines 31-53): `id`, `page_id`, `kind`, `text`, `enriched_content`, `tsv` (Computed), `embedding VECTOR(1536)`, `created_at`, `updated_at` from TimestampMixin. **Missing `chunk_index`** — D-14 dedup by `page_slug+chunk_index` requires adding this column; migration 0005 must add it.
- `Page` model (`server/app/models/page.py` lines 47-80): **Missing `compiled_truth_updated_at` and `latest_timeline_ts`** — stale annotation (D-13) requires both. Migration 0005 must add them (A1 assumption confirmed by model inspection).
- `Page.note_type` field (line 61): confirmed as `note_type`, not `page_type` — D-06 skip check must use `page.note_type` (A2 confirmed).
- `LLMUsage` model (`server/app/models/llm_usage.py`): `id`, `user_id`, `provider`, `model`, `input_tokens`, `output_tokens`, `cost_usd`, `conversation_id`, `created_at`. No `request_id` column — UsageRecorder may need to use `metadata["user_id"]` only for attribution.
- `SystemConfig` model (`server/app/models/system_config.py`): `key TEXT PK`, `value JSONB`, `updated_at`. Migration progress stored as `{"status": "running", "total": N, "done": N, "started_at": "ISO"}`.

---

## No Analog Found

All Phase 2a files have close analogs. No files are in this category.

---

## Metadata

**Analog search scope:** `server/app/` (all subdirectories)
**Files scanned:** 15 source files read in full
**Pattern extraction date:** 2026-05-15
