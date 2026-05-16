---
phase: 02A
plan: 03
type: execute
wave: 3
depends_on: [02A-01, 02A-02]
files_modified:
  - server/app/rag/__init__.py
  - server/app/rag/chunker.py
  - server/app/rag/embedder.py
  - server/app/scheduler/jobs/embed_worker.py
  - server/app/scheduler/run.py
  - server/app/services/pages.py
  - server/app/tests/rag/test_chunker.py
  - server/app/tests/rag/test_embedder.py
  - server/app/tests/rag/test_embed_worker.py
autonomous: true
requirements: [RAG-01, RAG-02]
tags: [rag, phase-2a, chunker, embedder, apscheduler, tiktoken, pgvector]

must_haves:
  truths:
    - "chunk_for_page(page) returns at least one Chunk row when page.note_type is not in {archived_fleeting, skill}; returns an empty list for the two skip note types (D-06)"
    - "Compiled-truth chunks have kind='truth'; timeline-event chunks have kind='event' (one chunk per event, D-02); frontmatter produces exactly one kind='summary' chunk per page (D-04)"
    - "Each chunk.text encodes to <= 512 tokens via tiktoken cl100k_base; sliding window overlap is 50 tokens (D-01, D-03)"
    - "chunk.enriched_content is populated from page.compiled_truth/timeline text when page enrichment has not run (D-05); equals chunk.text in that fallback path"
    - "chunk.chunk_index is monotonically increasing per page starting at 0; used as part of the D-14 dedup key"
    - "embed_batch asserts len(embedding) == 1536 BEFORE writing to chunk.embedding; mismatch raises an AssertionError caught by the worker so the batch continues with remaining chunks"
    - "embed_pending_chunks scheduler job runs every minute, claims up to 100 chunks WHERE embedding IS NULL, calls embed_chunks(texts, op_ctx=system, session=session), writes vectors, and commits"
    - "Embedding is NEVER triggered inline on page write (D-12); upsert_page in services/pages.py only enqueues new chunk rows with embedding=NULL, then the APScheduler job consumes them"
    - "The watcher and reconciler invoke chunker on page upsert; pre-existing chunks for a page are deleted and re-created on content_hash change so chunk_index is stable per page version"
  artifacts:
    - path: "server/app/rag/__init__.py"
      provides: "Package init"
      contains: "rag"
    - path: "server/app/rag/chunker.py"
      provides: "split_into_chunks(text, max_tokens=512, overlap=50), count_tokens(text), should_skip_page(note_type), chunk_for_page(page) returning list[ChunkDraft]"
      contains: "tiktoken"
    - path: "server/app/rag/embedder.py"
      provides: "embed_batch(session, ctx, chunks) writes 1536-dim vectors; dimension assert before INSERT"
      contains: "assert len(vec) == 1536"
    - path: "server/app/scheduler/jobs/embed_worker.py"
      provides: "embed_pending_chunks() APScheduler job; module-level function; coalesce=True, max_instances=1"
      contains: "system_operation_context"
    - path: "server/app/scheduler/run.py"
      provides: "Registers embed_pending_chunks job (interval=minutes=1)"
      contains: "embed_pending_chunks"
    - path: "server/app/services/pages.py"
      provides: "upsert_page also (re)creates Chunk rows via chunk_for_page; embedding is left NULL"
      contains: "chunk_for_page"
  key_links:
    - from: "server/app/services/pages.py"
      to: "server/app/rag/chunker.py"
      via: "upsert_page imports chunk_for_page and creates Chunk ORM rows after content_hash change"
      pattern: "chunk_for_page"
    - from: "server/app/scheduler/jobs/embed_worker.py"
      to: "server/app/rag/embedder.py"
      via: "embed_pending_chunks calls embed_batch"
      pattern: "embed_batch"
    - from: "server/app/rag/embedder.py"
      to: "server/app/llm/router.py"
      via: "embed_chunks(texts, op_ctx, session) — sole LiteLLM call"
      pattern: "embed_chunks"
    - from: "server/app/scheduler/run.py"
      to: "server/app/scheduler/jobs/embed_worker.py"
      via: "scheduler.add_job(embed_pending_chunks, 'interval', minutes=1, coalesce=True, max_instances=1)"
      pattern: "embed_pending_chunks"
---

<objective>
Wire the content-kind-aware chunking pipeline (D-01..D-06) and the async embedding worker (D-12). The chunker splits each Page into typed Chunk rows (truth / event / summary) at 512-token boundaries with 50-token overlap. The pages service upsert path drops + recreates chunks on content_hash change, leaving Chunk.embedding=NULL. The APScheduler job embed_pending_chunks polls 100 NULL-embedding chunks per minute, calls llm.router.embed_chunks (which records cost via UsageRecorder from Plan 02), asserts 1536-dim, and writes the vectors. archived_fleeting and skill note_types skip the pipeline entirely (D-06).

Purpose: Activates the HNSW index that migration 0001 created but Phase 1d never populated. Plan 04's retriever has chunks to query.

Output: rag/{chunker,embedder}.py, scheduler/jobs/embed_worker.py, scheduler/run.py registration, upsert_page chunker hook, and real tests replacing Plan 01 stubs for RAG-01 and RAG-02.
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

<interfaces>
<!-- Reuse without rediscovering -->

From server/app/models/chunk.py (post Plan 01 migration 0005):
- Chunk columns: id (UUID PK, default uuid4), page_id (UUID FK pages.id ON DELETE CASCADE), chunk_index (int default 0), kind (enum: summary/detail/truth/event/enrichment), text (TEXT not null), enriched_content (TEXT nullable), tsv (Computed TSVECTOR — never write to this), embedding (VECTOR(1536) nullable)

From server/app/models/page.py (post Plan 01 migration 0005):
- Page columns include: id, vault_id, slug, type, note_type (fleeting/literature/permanent/archived_fleeting/skill/moc), frontmatter (JSONB), compiled_truth (TEXT), timeline (TEXT nullable), content_hash, enrichment_hash, compiled_truth_updated_at, latest_timeline_ts, deleted_at

From server/app/services/pages.py:
- async def upsert_page(session, ctx, *, vault_id, slug, parsed, enforce_timeline) — single insertion point invoked by routes, watcher, and reconciler. Plan 03 extends this function to (re)create chunks AFTER the page row is committed/flushed.
- Existing logic uses content_hash comparison to detect unchanged content; chunking must only fire when content_hash actually changed (mirror IDX-03 discipline)

From server/app/scheduler/jobs/reconcile_vault.py (analog):
- Module-level async def reconcile_vault(); APScheduler-pickleable; uses system_operation_context + session_with_rls
- Per-vault try/except with rollback so one failure does not break others; commits inside the loop

From server/app/scheduler/run.py:
- Current: registers prune_login_attempts (hourly) and reconcile_vault (5-min). Plan 03 adds a third add_job for embed_pending_chunks (1-min).

From server/app/llm/router.py (Plan 02 output):
- async def embed_chunks(texts: list[str], *, op_ctx: OperationContext, session: AsyncSession) returns list[list[float]] — sole LiteLLM entry point. Plan 03 calls it from embedder.py.

From tiktoken (version 0.12.0 installed):
- import tiktoken; _ENC = tiktoken.get_encoding("cl100k_base"); _ENC.encode(text) returns list[int]; _ENC.decode(tokens) returns str

From server/app/vault/parser.py (analog for chunker):
- Pure transform module; from __future__ import annotations; dataclasses; no DB I/O. Chunker follows the same shape.

Page parser timeline format (from VAULT-04 / Phase 1c):
- Compiled truth is page.compiled_truth (above the horizontal-rule separator)
- Timeline is page.timeline text (below the line); each event is delimited by a date line at column 0 (regex: ^\d{4}-\d{2}-\d{2}); D-02 says one chunk per event
- Frontmatter is page.frontmatter dict (JSONB); rendered as deterministic key: value lines for the summary chunk per D-04
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Chunker — split into typed chunks (rag/chunker.py)</name>
  <files>server/app/rag/__init__.py, server/app/rag/chunker.py, server/app/tests/rag/test_chunker.py</files>
  <read_first>
    - server/app/vault/parser.py (transform analog; no DB)
    - server/app/models/page.py (current Page columns; note_type values)
    - server/app/models/chunk.py (Chunk columns; kind enum values)
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-CONTEXT.md (D-01..D-06)
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-RESEARCH.md §Pattern 6 (tiktoken chunk boundary)
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-PATTERNS.md §rag/chunker.py
    - server/app/tests/rag/test_chunker.py (Plan 01 Wave 0 stubs to flip to real tests)
  </read_first>
  <behavior>
    - should_skip_page("archived_fleeting") returns True; should_skip_page("skill") returns True; should_skip_page("fleeting"/"literature"/"permanent"/"moc") returns False
    - count_tokens("hello world") returns 2 via tiktoken cl100k_base; on tiktoken failure returns len(text) // 4 fallback
    - split_into_chunks(text="x" * 10000, max_tokens=512, overlap=50) returns multiple chunks; each encodes to <= 512 tokens; consecutive chunks share 50 tokens of overlap; final chunk may be shorter
    - chunk_for_page(page) returns a list of ChunkDraft dataclass instances (chunk_index, kind, text, enriched_content)
    - For a page with non-empty frontmatter: exactly one ChunkDraft with kind="summary", chunk_index=0
    - For a page with non-empty compiled_truth: split into kind="truth" chunks per D-03 sliding window; chunk_index continues after summary
    - For a page with non-empty timeline: one ChunkDraft per event (delimited by lines matching ^\d{4}-\d{2}-\d{2}); short events (< 50 tokens) padded by repeating their content until ~50 tokens reached; kind="event"
    - chunk_for_page(page where note_type in {archived_fleeting, skill}) returns []
    - ChunkDraft.enriched_content equals ChunkDraft.text (D-05 fallback: enrichment has not run)
  </behavior>
  <action>
    Create server/app/rag/__init__.py with a docstring "Phase 2a hybrid RAG package — chunker, embedder, retriever, reranker, intent."

    Create server/app/rag/chunker.py per PATTERNS §rag/chunker.py. Imports: from __future__ import annotations; import re; from dataclasses import dataclass; from typing import Literal; import tiktoken; from app.models.page import Page.

    Module-level: _ENC = tiktoken.get_encoding("cl100k_base"); _SKIP_NOTE_TYPES = frozenset({"archived_fleeting", "skill"}); _EVENT_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}", re.MULTILINE); _MIN_EVENT_TOKENS = 50.

    Define:
    - def count_tokens(text: str) -> int: try return len(_ENC.encode(text)); except Exception return len(text) // 4
    - def split_into_chunks(text: str, max_tokens: int = 512, overlap: int = 50) -> list[str]: tokens = _ENC.encode(text); if no tokens, return []. Loop: end = min(start + max_tokens, len(tokens)); append _ENC.decode(tokens[start:end]); if end == len(tokens) break; start = end - overlap. Returns list[str].
    - def should_skip_page(note_type: str) -> bool: return note_type in _SKIP_NOTE_TYPES
    - def render_frontmatter(frontmatter: dict) -> str: deterministic key: value lines sorted by key; one line per top-level key; nested dicts serialized as JSON one-liners. Return "" if empty.
    - def split_timeline(timeline: str) -> list[str]: split text on event date boundaries (lines matching _EVENT_DATE_RE at column 0); preserve the date line in each event chunk; filter empty events. Pad events shorter than _MIN_EVENT_TOKENS by repeating their non-empty content (with a single trailing newline separator) until count_tokens(padded) >= _MIN_EVENT_TOKENS.

    Define @dataclass(frozen=True, slots=True) class ChunkDraft: chunk_index: int; kind: Literal["summary","truth","event","detail","enrichment"]; text: str; enriched_content: str.

    Define def chunk_for_page(page: Page) -> list[ChunkDraft]:
    - if should_skip_page(page.note_type): return []
    - drafts: list[ChunkDraft] = []
    - idx = 0
    - frontmatter_text = render_frontmatter(page.frontmatter or {})
    - if frontmatter_text: append ChunkDraft(idx, "summary", frontmatter_text, frontmatter_text); idx += 1
    - for truth_text in split_into_chunks(page.compiled_truth or "", 512, 50): if truth_text.strip(): append ChunkDraft(idx, "truth", truth_text, truth_text); idx += 1
    - for event_text in split_timeline(page.timeline or ""): append ChunkDraft(idx, "event", event_text, event_text); idx += 1
    - return drafts

    Replace Plan 01 xfail stubs in server/app/tests/rag/test_chunker.py with real assertions:
    - test_skip_archived_fleeting: build a stub Page-like object (or use a dataclass shim) with note_type="archived_fleeting"; assert chunk_for_page returns []
    - test_skip_skill: same with note_type="skill"
    - test_compiled_truth_produces_truth_chunks: page with compiled_truth = "lorem " * 800; assert at least 2 chunks with kind="truth"; each chunk count_tokens <= 512
    - test_frontmatter_produces_one_summary: page with non-empty frontmatter dict; assert exactly one chunk with kind="summary" at chunk_index=0
    - test_timeline_one_chunk_per_event: timeline string with two dated events; assert exactly two chunks with kind="event"
    - test_short_event_padded: timeline with a 5-word event line; assert resulting event chunk count_tokens >= 50
    - test_chunk_index_monotonic: page with frontmatter + 2 truth + 1 event; assert chunk_index sequence is [0,1,2,3]
    - test_enriched_content_equals_text_fallback: any chunk; assert draft.enriched_content == draft.text (D-05 fallback)
    - test_count_tokens_tiktoken_path: count_tokens("hello world") returns a positive int
    - test_should_skip_page_returns_false_for_normal_types: each of fleeting/literature/permanent/moc returns False

    Tests are pure unit tests; no DB needed. Use a simple module-level dataclass FakePage with the four fields the chunker reads (note_type, frontmatter, compiled_truth, timeline).
  </action>
  <verify>
    <automated>cd server && pytest app/tests/rag/test_chunker.py -q -m "rag" 2>&1 | tail -10 && cd server && python -c "from app.rag.chunker import split_into_chunks, count_tokens, should_skip_page, chunk_for_page, ChunkDraft, render_frontmatter, split_timeline; assert len(split_into_chunks('x' * 10000)) > 1 and count_tokens('hello world') > 0 and should_skip_page('skill') and not should_skip_page('fleeting')"</automated>
  </verify>
  <acceptance_criteria>
    - server/app/rag/__init__.py exists
    - server/app/rag/chunker.py source contains import tiktoken, _ENC = tiktoken.get_encoding("cl100k_base"), def split_into_chunks(, def count_tokens(, def should_skip_page(, def chunk_for_page(, @dataclass and class ChunkDraft, def render_frontmatter(, def split_timeline(
    - server/app/rag/chunker.py source contains the literal string "archived_fleeting" AND "skill" in the _SKIP_NOTE_TYPES definition
    - server/app/rag/chunker.py does NOT import from sqlalchemy or fastapi (grep -E "from (sqlalchemy|fastapi)" returns empty — pure transform)
    - cd server && pytest app/tests/rag/test_chunker.py -q exits 0 with at least 10 passing tests
    - cd server && python -c "from app.rag.chunker import split_into_chunks; chunks = split_into_chunks('hello ' * 1000); assert all(len(__import__('tiktoken').get_encoding('cl100k_base').encode(c)) <= 512 for c in chunks)" exits 0
  </acceptance_criteria>
  <done>
    Chunker is a pure transform satisfying D-01..D-06 (RAG-01). Real tests replace Plan 01 xfail stubs. Embedder (Task 2) and pages service (Task 3) consume it.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Embedder — batch embed with dimension assert (rag/embedder.py)</name>
  <files>server/app/rag/embedder.py, server/app/tests/rag/test_embedder.py</files>
  <read_first>
    - server/app/rag/chunker.py (Task 1 output: ChunkDraft, chunk_for_page)
    - server/app/llm/router.py (Plan 02: embed_chunks signature)
    - server/app/models/chunk.py (Chunk ORM)
    - server/app/scheduler/jobs/reconcile_vault.py (batch error-handling pattern)
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-PATTERNS.md §rag/embedder.py
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-RESEARCH.md §Pitfall 3, §Pitfall 4
  </read_first>
  <behavior>
    - embed_batch(session, ctx, chunks=[Chunk, Chunk, ...]) reads chunk.enriched_content (fallback chunk.text), calls embed_chunks(texts, op_ctx=ctx, session=session) from llm.router, asserts each returned vector has exactly 1536 dims, assigns chunk.embedding = vec, flushes the session, returns number of chunks successfully embedded
    - If a returned vector has wrong dimension, the function raises an AssertionError with a message containing both expected and actual dim; caller (worker) catches and continues
    - If LiteLLM raises (MissingProviderKey, LLMRouterError), embed_batch lets the exception propagate; the worker catches and rolls back
    - Embedder writes only to chunk.embedding; never modifies text, enriched_content, kind, chunk_index, or tsv (Computed column)
  </behavior>
  <action>
    Create server/app/rag/embedder.py per PATTERNS §rag/embedder.py. Imports: from __future__ import annotations; import structlog; from sqlalchemy.ext.asyncio import AsyncSession; from app.auth.context import OperationContext; from app.llm.router import embed_chunks; from app.models.chunk import Chunk.

    log = structlog.get_logger("smart_copilot.rag.embedder")

    Define async def embed_batch(session: AsyncSession, ctx: OperationContext, chunks: list[Chunk]) -> int:
    - if not chunks: return 0
    - texts = [c.enriched_content or c.text for c in chunks]
    - embeddings = await embed_chunks(texts, op_ctx=ctx, session=session)
    - written = 0
    - for chunk, vec in zip(chunks, embeddings, strict=True): assert len(vec) == 1536, f"Dimension mismatch on chunk_id={chunk.id}: expected 1536, got {len(vec)}"; chunk.embedding = vec; written += 1
    - await session.flush()
    - log.info("embed_batch_complete", count=written)
    - return written

    Replace Plan 01 stubs in server/app/tests/rag/test_embedder.py with real tests using mock for embed_chunks:
    - test_embed_batch_writes_vectors: build a stub list of 3 Chunk-shaped objects (use a SimpleNamespace or dataclass shim — the assignment chunk.embedding = vec works on any object); patch app.rag.embedder.embed_chunks with AsyncMock returning [[0.0]*1536]*3; call embed_batch; assert each chunk.embedding has length 1536; assert returned count == 3
    - test_embed_batch_dimension_mismatch_raises: patch embed_chunks to return [[0.0]*1024]; assert AssertionError raised and message contains "Dimension mismatch" and "1024"
    - test_embed_batch_empty_input_returns_zero: pass []; assert returns 0 and embed_chunks not called
    - test_embed_batch_uses_enriched_content_when_set: stub chunk has enriched_content="ENR" and text="TXT"; capture the texts kwarg passed to embed_chunks; assert texts == ["ENR"]
    - test_embed_batch_falls_back_to_text_when_enriched_none: stub chunk has enriched_content=None and text="TXT"; assert texts == ["TXT"] in the mocked call
  </action>
  <verify>
    <automated>cd server && pytest app/tests/rag/test_embedder.py -q -m "rag" 2>&1 | tail -10 && cd server && python -c "from app.rag.embedder import embed_batch; import inspect; assert inspect.iscoroutinefunction(embed_batch)"</automated>
  </verify>
  <acceptance_criteria>
    - server/app/rag/embedder.py source contains async def embed_batch( and assert len(vec) == 1536 (the literal assert text)
    - server/app/rag/embedder.py imports embed_chunks from app.llm.router (NOT from litellm directly — RAG-06 gate)
    - cd server && ruff check app/rag/embedder.py --select TID exits 0 (no direct litellm import)
    - cd server && pytest app/tests/rag/test_embedder.py -q exits 0 with at least 5 passing tests
    - grep -E "import litellm|from litellm" server/app/rag/embedder.py returns empty (no direct LiteLLM import — uses router only)
  </acceptance_criteria>
  <done>
    Embedder writes 1536-dim vectors via the LLM router. Dimension assert prevents Pitfall 3. Pure async function; no scheduler logic. Worker (Task 3) wraps the batch + session lifecycle.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Embed worker job + scheduler registration + pages service hook</name>
  <files>server/app/scheduler/jobs/embed_worker.py, server/app/scheduler/run.py, server/app/services/pages.py, server/app/tests/rag/test_embed_worker.py</files>
  <read_first>
    - server/app/scheduler/jobs/reconcile_vault.py (full pattern; coalesce=True, max_instances=1, per-iteration try/except)
    - server/app/scheduler/run.py (current job registration pattern)
    - server/app/services/pages.py (upsert_page current body; find the content_hash compare branch where chunking should fire)
    - server/app/rag/chunker.py (Task 1 output: chunk_for_page, ChunkDraft)
    - server/app/rag/embedder.py (Task 2 output: embed_batch)
    - server/app/models/chunk.py (Chunk ORM; chunk_index column)
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-PATTERNS.md §scheduler/jobs/embed_worker.py
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-CONTEXT.md (D-12: embedding async via APScheduler, never inline)
  </read_first>
  <behavior>
    - embed_pending_chunks() is a module-level async function (APScheduler-pickleable); uses system_operation_context(request_id="embed_worker", client_name="scheduler") and session_with_rls
    - Each invocation: SELECT Chunk WHERE embedding IS NULL LIMIT 100; if rows: call embed_batch(session, ctx, chunks), commit; else: return
    - On exception inside the batch (AssertionError from dimension mismatch, MissingProviderKey, LLMRouterError, network error): roll back the session, log the error with chunk_ids (NOT api_key), return (next interval retries)
    - Registered in scheduler/run.py via scheduler.add_job(embed_pending_chunks, "interval", minutes=1, id="embed_pending_chunks", replace_existing=True, coalesce=True, max_instances=1)
    - upsert_page in services/pages.py: AFTER a page row is updated/inserted AND its content_hash actually changed, delete existing Chunk rows WHERE page_id=page.id, then bulk-insert new Chunk rows from chunk_for_page(page) with embedding=NULL. If chunk_for_page returns [] (skip note type), do NOT delete pre-existing chunks (no-op so re-typing a page to skip doesn't lose history; in practice these note types start that way)
  </behavior>
  <action>
    Create server/app/scheduler/jobs/embed_worker.py mirroring reconcile_vault.py shape. Module docstring describes D-12 (async only), RAG-02 (1536 dim), batch size 100. Imports: from __future__ import annotations; import structlog; from sqlalchemy import select; from app.auth.context import system_operation_context; from app.dependencies import session_with_rls; from app.models.chunk import Chunk; from app.rag.embedder import embed_batch.

    log = structlog.get_logger("smart_copilot.embed_worker")

    Define async def embed_pending_chunks() returns None:
    - ctx = system_operation_context(request_id="embed_worker", client_name="scheduler")
    - async for session in session_with_rls(ctx):
        - try:
            - rows = await session.execute(select(Chunk).where(Chunk.embedding.is_(None)).limit(100))
            - chunks = rows.scalars().all()
            - if not chunks: log.debug("embed_worker_no_pending"); return
            - written = await embed_batch(session, ctx, chunks)
            - await session.commit()
            - log.info("embed_worker_commit", written=written)
        - except Exception as exc: log.error("embed_worker_failed", error=str(exc), chunk_count=len(chunks) if 'chunks' in dir() else 0); await session.rollback()
    - log.info("embed_worker_complete")

    Edit server/app/scheduler/run.py to import embed_pending_chunks and register the job (interval=minutes=1, id="embed_pending_chunks", replace_existing=True, coalesce=True, max_instances=1). Update the log line at scheduler.start to mention the new job.

    Edit server/app/services/pages.py upsert_page:
    - At the top of the function, add a local helper import: from app.rag.chunker import chunk_for_page (top-of-module import is fine; chunker has no DB import)
    - Find the branch that fires when content_hash has changed (where the page row is updated/inserted). After the page row is flushed and the new content_hash committed to the ORM object, AND before the function returns:
        - drafts = chunk_for_page(page)
        - if drafts:
            - delete existing chunks: await session.execute(delete(Chunk).where(Chunk.page_id == page.id))
            - bulk insert: for d in drafts: session.add(Chunk(page_id=page.id, chunk_index=d.chunk_index, kind=d.kind, text=d.text, enriched_content=d.enriched_content))  # embedding left NULL on purpose
            - await session.flush()
        - Add a log line "page_chunked" with page_id, slug, count=len(drafts)
    - Import delete from sqlalchemy if not already imported

    Replace Plan 01 xfail stub server/app/tests/rag/test_embed_worker.py with real integration tests (pytestmark = [pytest.mark.rag, pytest.mark.integration]):
    - test_worker_processes_pending: seed a page through upsert_page (or directly insert Chunk rows with embedding=NULL); patch app.rag.embedder.embed_chunks to return [[0.0]*1536]*N; call await embed_pending_chunks(); assert chunks now have embedding NOT NULL; assert llm_usage row exists (UsageRecorder fired)
    - test_worker_no_pending_returns_quickly: empty chunks table; assert embed_pending_chunks() returns within < 1 second and writes no rows
    - test_worker_dimension_mismatch_rolls_back: patch embed_chunks to return [[0.0]*1024]; call worker; assert chunks still have embedding IS NULL after the call; assert session rolled back (no partial commit)
    - test_upsert_page_creates_chunks: seed a vault+user; upsert_page with parsed content for a "permanent" note_type page; query Chunk WHERE page_id; assert at least one chunk row exists with chunk_index=0 and kind in {summary, truth, event}
    - test_upsert_page_skip_note_type_creates_no_chunks: upsert_page with note_type="archived_fleeting" content; assert zero Chunk rows for that page
    - test_upsert_page_content_hash_change_replaces_chunks: upsert page twice with different compiled_truth; assert old chunks are gone and new chunks exist; chunk_index restarts at 0
  </action>
  <verify>
    <automated>cd server && pytest app/tests/rag/test_embed_worker.py -q -m "rag" 2>&1 | tail -10 && cd server && python -c "from app.scheduler.jobs.embed_worker import embed_pending_chunks; import inspect; assert inspect.iscoroutinefunction(embed_pending_chunks)" && grep -q "embed_pending_chunks" server/app/scheduler/run.py && grep -q "coalesce=True" server/app/scheduler/run.py</automated>
  </verify>
  <acceptance_criteria>
    - server/app/scheduler/jobs/embed_worker.py source contains async def embed_pending_chunks( and system_operation_context( and session_with_rls( and select(Chunk) and embed_batch(
    - server/app/scheduler/run.py source contains scheduler.add_job(embed_pending_chunks AND coalesce=True AND max_instances=1 AND minutes=1
    - server/app/services/pages.py source contains from app.rag.chunker import chunk_for_page and references chunk_for_page(page) inside upsert_page; also contains delete(Chunk).where(Chunk.page_id == page.id)
    - server/app/services/pages.py upsert_page does NOT call any LiteLLM function (grep -E "embed_chunks|acompletion|aembedding" server/app/services/pages.py returns empty — embedding is strictly async/scheduler-driven per D-12)
    - cd server && pytest app/tests/rag/test_embed_worker.py -q exits 0 with at least 6 passing tests
    - cd server && ruff check app/scheduler/jobs/embed_worker.py app/services/pages.py app/rag/embedder.py --select TID exits 0
    - cd server && python -c "from app.scheduler import run; assert 'embed_pending_chunks' in run.__dict__ or hasattr(__import__('app.scheduler.jobs.embed_worker', fromlist=['embed_pending_chunks']), 'embed_pending_chunks')"
    - Existing tests still pass: cd server && pytest app/tests/vault/ -q
  </acceptance_criteria>
  <done>
    Async embed pipeline is live. APScheduler invokes embed_pending_chunks every minute. upsert_page creates Chunk rows with embedding=NULL on content_hash change; the worker fills them in. Plan 04's retriever has populated HNSW data to query. Both RAG-01 (chunking) and RAG-02 (1536-dim embeddings via HNSW) requirements are satisfied. Watcher and reconciler inherit chunking automatically because they both call upsert_page.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Page write (route/watcher/reconciler) -> upsert_page chunker hook | User-controlled text reaches chunker; chunker must not invoke LLM (D-12); embedding is deferred to scheduler |
| Embed worker (system context) -> llm.router.embed_chunks | System RLS context bypasses per-user policy; only safe because embedding writes target the original chunk row (already linked to the originating page/user) |
| Chunk.embedding write -> pgvector HNSW index | Wrong-dim vector silently corrupts index; dimension assert is the only guard |
| chunk_for_page output -> session.add(Chunk) -> chunks table | Untrusted page text becomes searchable; OK because the existing page authorization already scoped the write |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02A-03-01 | Tampering | chunks.embedding wrong-dim INSERT | mitigate | assert len(vec) == 1536 in embed_batch before assigning to chunk.embedding; worker catches AssertionError, rolls back, logs chunk_id (covers Pitfall 3) |
| T-02A-03-02 | Information Disclosure | Cross-user chunk access via missing RLS | mitigate | embed_worker uses system_operation_context + session_with_rls (Pitfall 4); upsert_page is already RLS-scoped from caller's ctx; chunks inherit page authorization via FK cascade |
| T-02A-03-03 | Denial of Service | Synchronous embed on page write blocks watcher loop | mitigate | D-12: embedding is NEVER called from upsert_page; only APScheduler embed_worker calls embed_batch. Acceptance grep on services/pages.py for embed_chunks/acompletion/aembedding returns empty |
| T-02A-03-04 | Denial of Service | Embed worker overlap floods OpenAI rate limits | mitigate | scheduler.add_job(..., coalesce=True, max_instances=1) prevents pile-up; batch capped at 100; RateLimitError from LLMRouterError causes worker rollback + next-interval retry |
| T-02A-03-05 | Tampering | archived_fleeting/skill pages accidentally embedded | mitigate | D-06 should_skip_page guard in chunk_for_page; test_skip_archived_fleeting + test_skip_skill enforce |
| T-02A-03-SC | Tampering | npm/pip/cargo installs | mitigate | tiktoken pinned in Plan 01; pgvector pre-existing; apscheduler pre-existing; all Approved in RESEARCH §Package Legitimacy Audit |
</threat_model>

<verification>
- Unit tests for chunker: cd server && pytest app/tests/rag/test_chunker.py -q
- Unit tests for embedder: cd server && pytest app/tests/rag/test_embedder.py -q
- Integration tests for worker + upsert_page: cd server && pytest app/tests/rag/test_embed_worker.py -q
- TID gate still passes: cd server && ruff check app/ --select TID
- No direct LiteLLM in rag/services: grep -rE "^(import litellm|from litellm)" server/app/rag/ server/app/services/ returns empty
- Existing vault tests still green: cd server && pytest app/tests/vault/ -q
- Full suite: cd server && pytest app/tests/ -q
</verification>

<success_criteria>
1. chunk_for_page produces correctly-typed chunks for compiled_truth, timeline, and frontmatter sections; archived_fleeting and skill skip the pipeline (RAG-01)
2. embed_batch writes 1536-dim vectors via embed_chunks; mismatched dim raises AssertionError (RAG-02)
3. embed_pending_chunks runs as a separate APScheduler job (1-min interval, coalesce, max_instances=1); embeds NULL-embedding chunks 100 at a time (RAG-02 backend)
4. upsert_page creates Chunk rows with embedding=NULL when content_hash changes; never calls LiteLLM directly (D-12)
5. UsageRecorder fires on each embed_batch call; llm_usage row populated for system user (LLM-03 wiring through to embedder)
</success_criteria>

<output>
Create .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-03-SUMMARY.md when done.
</output>
