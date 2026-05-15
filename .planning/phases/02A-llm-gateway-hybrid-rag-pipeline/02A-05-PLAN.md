---
phase: 02A
plan: 05
type: execute
wave: 5
depends_on: [02A-01, 02A-02, 02A-03, 02A-04]
files_modified:
  - server/app/routes/migration.py
  - server/app/services/migration.py
  - server/app/main.py
  - server/app/tests/routes/test_migration.py
  - server/app/tests/integration/test_phase_2a_acceptance.py
  - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-VALIDATION.md
autonomous: false
requirements: [RAG-07, LLM-01, LLM-02, LLM-03, LLM-04, LLM-05, RAG-01, RAG-02, RAG-03, RAG-04, RAG-05, RAG-06]
tags: [rag, phase-2a, embedding-migration, admin, acceptance, human-verify]

must_haves:
  truths:
    - "GET /api/v1/admin/embedding-migration/estimate returns {total_chunks, embedded_chunks, pending_chunks, estimated_minutes} for the current user's scope; admin-only"
    - "POST /api/v1/admin/embedding-migration/start (with body {target_model, target_dim}) initiates an online dimension-change migration: writes a SystemConfig row with status='running', total, done=0, started_at, target_model, target_dim; admin + fresh-auth required"
    - "GET /api/v1/admin/embedding-migration/status returns the SystemConfig row (status in {idle, running, complete, failed, cancelled}) — admin-only"
    - "POST /api/v1/admin/embedding-migration/cancel sets status='cancelled' and stops the in-flight worker; admin + fresh-auth required"
    - "Migration uses asyncpg connection OUTSIDE any Alembic transaction to run CREATE INDEX CONCURRENTLY (Pitfall 8); progress tracked in system_config JSONB"
    - "Phase 2a acceptance test passes: seed a vault + page + chunk with known embedding; via REST POST /api/v1/search with a semantic query, response has search_type='hybrid_v1' and at least one result; via MCP brain.search same shape"
    - "Phase 2a VALIDATION.md is populated (replacing the draft template) with the per-task verification map, sampling rate, Wave 0 status, and nyquist_compliant=true frontmatter"
  artifacts:
    - path: "server/app/routes/migration.py"
      provides: "RAG-07 endpoints: /estimate, /start, /status, /cancel under /api/v1/admin/embedding-migration"
      contains: "embedding-migration"
    - path: "server/app/services/migration.py"
      provides: "estimate_migration, start_migration, get_migration_status, cancel_migration service functions backed by SystemConfig JSONB key 'embedding_migration'"
      contains: "embedding_migration"
    - path: "server/app/main.py"
      provides: "migration router registered after the search router"
      contains: "migration_router"
    - path: "server/app/tests/integration/test_phase_2a_acceptance.py"
      provides: "Phase 2a acceptance gate (SC-2a)"
      contains: "hybrid_v1"
    - path: ".planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-VALIDATION.md"
      provides: "Populated validation contract with per-task verification map and sampling rate"
      contains: "nyquist_compliant: true"
  key_links:
    - from: "server/app/routes/migration.py"
      to: "server/app/services/migration.py"
      via: "thin route → service pattern (REST-06)"
      pattern: "migration"
    - from: "server/app/services/migration.py"
      to: "system_config JSONB key 'embedding_migration'"
      via: "SystemConfig row with key='embedding_migration' value={status, total, done, started_at, target_model, target_dim, error}"
      pattern: "embedding_migration"
    - from: "server/app/main.py"
      to: "server/app/routes/migration.py.router"
      via: "app.include_router(migration_router)"
      pattern: "include_router"
---

<objective>
Close Phase 2a with two deliverables: (1) the RAG-07 embedding-migration admin endpoints that allow an operator to estimate, start, monitor, and cancel a dimension-change embedding migration without taking the system down; (2) the Phase 2a acceptance integration test that proves a semantic query returns search_type="hybrid_v1" through both the REST and MCP surfaces. A blocking human-verify checkpoint completes the phase against the AI-SPEC §5 evaluation dimensions (retrieval coverage, RRF rank quality, stale annotation, cold-start fallback).

Purpose: Without the migration endpoints, Phase 2a's embedding column is frozen at 1536 dims forever (RAG-07). Without the acceptance test + human-verify, ROADMAP success criterion #1 ("brain.search with a semantic query returns top-k results ranked by RRF") has no enforcement gate.

Output: routes/migration.py + services/migration.py implementing the four endpoints, the Phase 2a acceptance test, populated VALIDATION.md, and a human-verify checkpoint exercising the AI-SPEC eval dimensions.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-CONTEXT.md
@.planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-RESEARCH.md
@.planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-PATTERNS.md
@.planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-AI-SPEC.md
@.planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-01-SUMMARY.md
@.planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-02-SUMMARY.md
@.planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-03-SUMMARY.md
@.planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-04-SUMMARY.md

<interfaces>
<!-- Contracts the executor uses without rediscovery -->

From server/app/models/system_config.py:
- SystemConfig: key TEXT PK, value JSONB, updated_at. Use key="embedding_migration" for a singleton row holding {status, total, done, started_at, target_model, target_dim, error}.

From server/app/models/chunk.py:
- Chunk: id, page_id, chunk_index, kind, text, enriched_content, tsv, embedding VECTOR(1536). Migration adds a new column embedding_new VECTOR(target_dim), backfills, swaps.

From server/app/auth/deps.py:
- require_user, require_admin, require_fresh_auth — Plan 05 uses require_admin for /estimate + /status (read-only), require_fresh_auth for /start + /cancel (destructive — CLI-05 / AUTH-07 pattern)

From server/app/database.py + dependencies.py:
- async_session_factory, session_with_rls, engine — engine.connect() gives an asyncpg connection that can run CREATE INDEX CONCURRENTLY outside any transaction context (Pitfall 8)

From server/app/llm/router.py (Plan 02):
- embed_chunks(texts, op_ctx, session) — used by the migration backfill worker

From server/app/routes/pages.py:
- _http_error(status_code, code, message) helper pattern; thin route shape with Depends(require_*) and Depends(get_db_session)

From server/app/main.py:
- create_app() builds the FastAPI app; Plan 05 inserts app.include_router(migration_router) after the search router include
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Migration service + admin routes (services/migration.py, routes/migration.py)</name>
  <files>server/app/services/migration.py, server/app/routes/migration.py, server/app/main.py, server/app/tests/routes/test_migration.py</files>
  <read_first>
    - server/app/models/system_config.py (SystemConfig: key/value JSONB/updated_at)
    - server/app/models/chunk.py (chunks.embedding VECTOR(1536))
    - server/app/auth/deps.py (require_admin, require_fresh_auth)
    - server/app/routes/pages.py (_http_error helper, thin route shape)
    - server/app/database.py (engine; needed to grab asyncpg connection for CREATE INDEX CONCURRENTLY)
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-CONTEXT.md (Claude's discretion: add column → backfill concurrently → CREATE INDEX CONCURRENTLY → atomic rename; progress in system_config)
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-RESEARCH.md (§Pitfall 8 — CREATE INDEX CONCURRENTLY not inside transaction)
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-PATTERNS.md §routes/migration.py
  </read_first>
  <behavior>
    - estimate_migration(session, ctx) returns dataclass MigrationEstimate(total_chunks, embedded_chunks, pending_chunks, estimated_minutes); estimated_minutes = pending_chunks / 6000 (OpenAI embedding throughput ≈ 6000 chunks/min at batch 100)
    - start_migration(session, ctx, *, target_model: str, target_dim: int) writes/updates SystemConfig row key='embedding_migration' to value={"status":"running","total":N,"done":0,"started_at":ISO,"target_model":target_model,"target_dim":target_dim,"error":null}; raises ServiceError if a migration is already running (idempotency)
    - start_migration also schedules a background task (asyncio.create_task) that drives the actual migration: ALTER TABLE chunks ADD COLUMN embedding_new VECTOR(:target_dim); loop over pending chunks in batches of 100 calling embed_chunks with the new model; UPDATE chunks SET embedding_new = $1; CREATE INDEX CONCURRENTLY on embedding_new via a fresh asyncpg connection outside any SQLAlchemy transaction; on completion: ALTER TABLE chunks DROP COLUMN embedding; ALTER TABLE chunks RENAME COLUMN embedding_new TO embedding; update SystemConfig status='complete'; on error: status='failed' with error message
    - get_migration_status(session, ctx) returns SystemConfig.value or {"status":"idle"} if row missing
    - cancel_migration(session, ctx) sets SystemConfig.value.status='cancelled'; the background task polls this status between batches and exits when it sees 'cancelled'
    - All four service functions use OperationContext from caller; SystemConfig writes use the system context (cross-user singleton row)
  </behavior>
  <action>
    Create server/app/services/migration.py. Imports: from __future__ import annotations; import asyncio; import uuid; from dataclasses import dataclass; from datetime import UTC, datetime; from typing import Any; import structlog; from sqlalchemy import func, insert, select, text, update; from sqlalchemy.dialects.postgresql import insert as pg_insert; from sqlalchemy.ext.asyncio import AsyncSession; from app.auth.context import OperationContext, system_operation_context; from app.database import async_session_factory, engine; from app.dependencies import session_with_rls; from app.llm.router import embed_chunks; from app.models.chunk import Chunk; from app.models.system_config import SystemConfig.

    log = structlog.get_logger("smart_copilot.migration")
    MIGRATION_KEY = "embedding_migration"

    Define class MigrationConflict(Exception): pass; class MigrationNotRunning(Exception): pass.

    Define @dataclass(frozen=True, slots=True) class MigrationEstimate: total_chunks: int; embedded_chunks: int; pending_chunks: int; estimated_minutes: float.

    Define async def estimate_migration(session: AsyncSession, ctx: OperationContext) returns MigrationEstimate:
    - total = (await session.execute(select(func.count(Chunk.id)))).scalar() or 0
    - embedded = (await session.execute(select(func.count(Chunk.id)).where(Chunk.embedding.is_not(None)))).scalar() or 0
    - pending = total - embedded
    - estimated_minutes = pending / 6000.0
    - return MigrationEstimate(total_chunks=total, embedded_chunks=embedded, pending_chunks=pending, estimated_minutes=round(estimated_minutes, 2))

    Define async def start_migration(session: AsyncSession, ctx: OperationContext, *, target_model: str, target_dim: int) returns dict:
    - Validate: target_dim must be in {1536, 3072, 768} (reject others to prevent typo-driven schema mistakes; document via error message)
    - Read current SystemConfig row; if status=="running", raise MigrationConflict("a migration is already running")
    - total = (await session.execute(select(func.count(Chunk.id)))).scalar() or 0
    - value = {"status":"running","total":int(total),"done":0,"started_at":datetime.now(UTC).isoformat(),"target_model":target_model,"target_dim":int(target_dim),"error":None}
    - Upsert SystemConfig via pg_insert(...).on_conflict_do_update(index_elements=["key"], set_={"value": value, "updated_at": func.now()})
    - await session.commit()
    - Schedule background task: task = asyncio.create_task(_run_migration_loop(target_model=target_model, target_dim=target_dim)); log.info("migration_started", target_model=target_model, target_dim=target_dim, total=total)
    - return value

    Define async def _run_migration_loop(*, target_model: str, target_dim: int) -> None (module-level coroutine, no closures so unit tests can monkeypatch the embedding call):
    - ctx = system_operation_context(request_id="embedding_migration", client_name="migration_worker")
    - try:
        - Acquire a fresh asyncpg connection via engine.connect() AND begin a NON-DDL setup transaction with the SQLAlchemy session for the ALTER ADD COLUMN — wrap in autocommit via session.execute(text("COMMIT")) before DDL if needed, OR run the DDL via engine.begin() with isolation_level="AUTOCOMMIT": prefer the latter; document the choice with an inline comment citing Pitfall 8
        - async with engine.connect() as conn: await conn.execution_options(isolation_level="AUTOCOMMIT"); await conn.execute(text(f"ALTER TABLE chunks ADD COLUMN IF NOT EXISTS embedding_new VECTOR({target_dim})"))
        - Loop:
            - Check status: async for s in session_with_rls(ctx): row = (await s.execute(select(SystemConfig).where(SystemConfig.key==MIGRATION_KEY))).scalar_one_or_none(); if row is None or row.value.get("status") == "cancelled": log.info("migration_cancelled"); return
            - Batch: pending_rows = (await s.execute(select(Chunk).where(Chunk.embedding.is_not(None)).where(text("embedding_new IS NULL")).limit(100))).scalars().all()
            - if not pending_rows: break  # done
            - texts_to_embed = [c.enriched_content or c.text for c in pending_rows]
            - new_vecs = await embed_chunks(texts_to_embed, op_ctx=ctx, session=s)
            - for chunk, vec in zip(pending_rows, new_vecs, strict=True): assert len(vec) == target_dim; await s.execute(text("UPDATE chunks SET embedding_new = :v WHERE id = :id"), {"v": vec, "id": str(chunk.id)})
            - # Update progress
            - new_done = row.value.get("done", 0) + len(pending_rows); new_value = {**row.value, "done": new_done}
            - await s.execute(pg_insert(SystemConfig).values(key=MIGRATION_KEY, value=new_value).on_conflict_do_update(index_elements=["key"], set_={"value": new_value, "updated_at": func.now()}))
            - await s.commit()
        - Final swap (DDL outside transaction):
            - async with engine.connect() as conn: await conn.execution_options(isolation_level="AUTOCOMMIT"); await conn.execute(text(f"CREATE INDEX CONCURRENTLY IF NOT EXISTS chunks_embedding_new_hnsw_idx ON chunks USING hnsw (embedding_new vector_cosine_ops) WITH (m=16, ef_construction=64)")); await conn.execute(text("ALTER TABLE chunks DROP COLUMN embedding")); await conn.execute(text("ALTER TABLE chunks RENAME COLUMN embedding_new TO embedding")); await conn.execute(text("ALTER INDEX chunks_embedding_new_hnsw_idx RENAME TO chunks_embedding_hnsw_idx"))
        - async for s in session_with_rls(ctx): final_value = {"status":"complete","total":row.value.get("total",0),"done":row.value.get("done",0),"started_at":row.value.get("started_at"),"target_model":target_model,"target_dim":target_dim,"error":None}; await s.execute(pg_insert(SystemConfig).values(key=MIGRATION_KEY, value=final_value).on_conflict_do_update(index_elements=["key"], set_={"value": final_value, "updated_at": func.now()})); await s.commit(); log.info("migration_complete")
    - except Exception as exc:  # noqa: BLE001
        - log.error("migration_failed", error=str(exc))
        - async for s in session_with_rls(ctx):
            - try: row = (await s.execute(select(SystemConfig).where(SystemConfig.key==MIGRATION_KEY))).scalar_one_or_none(); base = row.value if row else {"status":"failed","total":0,"done":0,"started_at":None,"target_model":target_model,"target_dim":target_dim}; failure_value = {**base, "status":"failed", "error": str(exc)}; await s.execute(pg_insert(SystemConfig).values(key=MIGRATION_KEY, value=failure_value).on_conflict_do_update(index_elements=["key"], set_={"value": failure_value, "updated_at": func.now()})); await s.commit()
            - except Exception: pass

    Define async def get_migration_status(session: AsyncSession, ctx: OperationContext) -> dict:
    - row = (await session.execute(select(SystemConfig).where(SystemConfig.key==MIGRATION_KEY))).scalar_one_or_none()
    - if row is None: return {"status":"idle","total":0,"done":0,"started_at":None,"target_model":None,"target_dim":None,"error":None}
    - return row.value

    Define async def cancel_migration(session: AsyncSession, ctx: OperationContext) -> dict:
    - row = (await session.execute(select(SystemConfig).where(SystemConfig.key==MIGRATION_KEY))).scalar_one_or_none()
    - if row is None or row.value.get("status") not in {"running"}: raise MigrationNotRunning("no migration is currently running")
    - new_value = {**row.value, "status":"cancelled"}
    - await session.execute(update(SystemConfig).where(SystemConfig.key==MIGRATION_KEY).values(value=new_value))
    - await session.commit()
    - return new_value

    Create server/app/routes/migration.py per PATTERNS §routes/migration.py. Imports: from __future__ import annotations; from fastapi import APIRouter, Depends, HTTPException; from pydantic import BaseModel, Field; from sqlalchemy.ext.asyncio import AsyncSession; from app.auth.context import OperationContext; from app.auth.deps import require_admin, require_fresh_auth; from app.dependencies import get_db_session; from app.services.migration import MigrationConflict, MigrationEstimate, MigrationNotRunning, cancel_migration, estimate_migration, get_migration_status, start_migration.

    router = APIRouter(prefix="/api/v1/admin/embedding-migration", tags=["admin","embedding-migration"])

    Pydantic models:
    - MigrationEstimateOut: total_chunks: int, embedded_chunks: int, pending_chunks: int, estimated_minutes: float
    - MigrationStartIn: target_model: str = Field(..., min_length=1, max_length=128); target_dim: int = Field(..., ge=1, le=8192)
    - MigrationStatusOut: status: str; total: int; done: int; started_at: str | None; target_model: str | None; target_dim: int | None; error: str | None

    Define _http_error helper (or import from app.routes.pages if exported there; otherwise copy the same pattern).

    Define four endpoints:
    - @router.get("/estimate", response_model=MigrationEstimateOut): require_admin; calls estimate_migration
    - @router.post("/start", response_model=MigrationStatusOut): require_fresh_auth; body MigrationStartIn; calls start_migration; catches MigrationConflict → 409 conflict; catches ValueError (target_dim validation) → 422 validation_error
    - @router.get("/status", response_model=MigrationStatusOut): require_admin; calls get_migration_status; returns the dict directly (Pydantic coerces)
    - @router.post("/cancel", response_model=MigrationStatusOut): require_fresh_auth; calls cancel_migration; catches MigrationNotRunning → 409 conflict

    Register router in server/app/main.py: import from app.routes.migration import router as migration_router; add app.include_router(migration_router) after app.include_router(search_router).

    Replace Plan 01 stubs server/app/tests/routes/test_migration.py with real integration tests (pytestmark = [pytest.mark.rag, pytest.mark.integration]):
    - test_estimate_requires_admin: non-admin user → 403
    - test_estimate_returns_counts: admin user; seed 5 chunks (3 with embeddings, 2 NULL); GET /estimate → total_chunks=5, embedded_chunks=3, pending_chunks=2
    - test_start_requires_fresh_auth: admin without fresh auth → 403 admin_reauth_required
    - test_start_creates_running_row: admin + fresh; POST /start with valid body → 200 + SystemConfig row exists with status="running"
    - test_start_rejects_concurrent: status="running" already; POST /start → 409 conflict
    - test_status_returns_idle_when_no_row: clean DB; GET /status → status="idle"
    - test_cancel_sets_cancelled: seed SystemConfig status="running"; POST /cancel → 200 + status="cancelled"
    - test_cancel_when_idle_returns_409: no migration → 409 conflict
    - test_start_invalid_target_dim: target_dim=0 → 422 validation_error
    For tests that would otherwise trigger the background task: monkeypatch app.services.migration._run_migration_loop with an async no-op so DDL is not issued during unit tests.
  </action>
  <verify>
    <automated>cd server && pytest app/tests/routes/test_migration.py -q -m "rag" 2>&1 | tail -10 && cd server && python -c "from app.services.migration import estimate_migration, start_migration, get_migration_status, cancel_migration, MigrationConflict, MigrationNotRunning, MIGRATION_KEY; from app.routes.migration import router; assert router.prefix == '/api/v1/admin/embedding-migration'" && cd server && python -c "from app.main import create_app; app = create_app(); paths = [r.path for r in app.routes]; assert any('embedding-migration' in p for p in paths), f'migration router not registered: {paths}'"</automated>
  </verify>
  <acceptance_criteria>
    - server/app/services/migration.py source contains async def estimate_migration(, async def start_migration(, async def get_migration_status(, async def cancel_migration(, async def _run_migration_loop(, class MigrationConflict, class MigrationNotRunning, MIGRATION_KEY = "embedding_migration"
    - server/app/services/migration.py contains the literal "isolation_level=" and "AUTOCOMMIT" (Pitfall 8 — CREATE INDEX CONCURRENTLY outside transaction)
    - server/app/services/migration.py contains assert len(vec) == target_dim (dimension safety during backfill)
    - server/app/routes/migration.py contains four route decorators: @router.get("/estimate"), @router.post("/start"), @router.get("/status"), @router.post("/cancel")
    - server/app/routes/migration.py uses require_admin on /estimate and /status; require_fresh_auth on /start and /cancel (grep returns each)
    - server/app/main.py source contains from app.routes.migration import and app.include_router(migration_router)
    - cd server && pytest app/tests/routes/test_migration.py -q exits 0 with at least 9 passing tests
    - cd server && ruff check app/services/migration.py app/routes/migration.py --select TID exits 0
    - server/app/services/migration.py does NOT import litellm directly (uses embed_chunks via app.llm.router)
  </acceptance_criteria>
  <done>
    RAG-07 endpoints (/estimate, /start, /status, /cancel) live under /api/v1/admin/embedding-migration with admin + fresh-auth gates per CLI-05 / AUTH-07. The migration worker performs add-column → backfill → CREATE INDEX CONCURRENTLY → atomic rename outside any Alembic transaction (Pitfall 8). Progress persists in system_config.embedding_migration JSONB so a container restart can resume polling status.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Phase 2a acceptance test + VALIDATION.md population</name>
  <files>server/app/tests/integration/test_phase_2a_acceptance.py, .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-VALIDATION.md</files>
  <read_first>
    - server/app/tests/integration/test_phase_1d_acceptance.py (acceptance test shape — fixtures, asserts, RLS context)
    - server/app/tests/integration/test_search_route.py (REST search test pattern)
    - server/app/tests/integration/test_rest_mcp_parity.py (parity test pattern; identical service calls)
    - server/app/services/search.py (Plan 04: hybrid_search signature, SearchResult shape)
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-AI-SPEC.md §5 (eval dimensions for human-verify task; reference dataset spec)
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-VALIDATION.md (current draft to populate)
    - .planning/ROADMAP.md Phase 2a success criteria 1–5
  </read_first>
  <behavior>
    - test_acceptance_brain_search_returns_hybrid_v1: seed a vault + page + chunk row with a known 1536-dim embedding and BM25-matching text; patch app.services.search.embed_chunks to return that same vector; POST /api/v1/search with a query that matches the text; assert response 200, search_type="hybrid_v1", results length ≥ 1, results[0]["chunk_id"] is not None
    - test_acceptance_mcp_brain_search_returns_hybrid_v1: same seed; invoke brain.search MCP tool through an in-process MCP client (or equivalent helper from the existing parity test); assert the same shape
    - test_acceptance_truth_chunk_ranks_first: seed 2 chunks on the same page, one kind="truth" and one kind="event", both BM25-matching the query; query; assert results[0]["kind"] == "truth" because of +settings.truth_boost
    - test_acceptance_stale_annotation_surfaces: seed page with compiled_truth_updated_at far behind latest_timeline_ts; query; assert results[0]["is_stale"] is True and stale_days >= settings.stale_days + 1
    - test_acceptance_cold_start_fts_v1: seed only pages (no chunks at all); query; assert search_type="fts_v1" and results returned from search_pages_fts
    - test_acceptance_llm_usage_records_embedding_cost: after running test_acceptance_brain_search_returns_hybrid_v1, query the llm_usage table; assert at least one row exists for the embedding call with provider="openai" and model="openai/text-embedding-3-small"
    - test_acceptance_ruff_tid_gate: subprocess.run(["ruff", "check", "--select", "TID", "app/"]) returns rc==0
    - VALIDATION.md frontmatter status flips to "approved"; nyquist_compliant: true; wave_0_complete: true; per-task verification map filled for each task across the five plans; sampling rate section lists `pytest app/tests/rag/ app/tests/llm/ -q -m "rag or llm"` (< 30s) as the per-task command and `pytest app/tests/ -q` as the per-wave command
  </behavior>
  <action>
    Replace server/app/tests/integration/test_phase_2a_acceptance.py with the seven tests in <behavior>. Use existing testcontainers fixtures (db_session, seed_user, seed_vault) and the FastAPI TestClient from the Phase 1d acceptance test. For MCP parity, follow the in-process invocation pattern from test_rest_mcp_parity.py. Pytestmark: [pytest.mark.rag, pytest.mark.integration].

    Each test should:
    - Use real DB fixtures (no mocks for chunks/pages)
    - Mock only the OpenAI HTTP egress by patching app.services.search.embed_chunks (or app.rag.embedder.embed_chunks for the worker) with AsyncMock returning a canned 1536-dim vector
    - Mock only the OpenAI HTTP egress on the embedding-migration worker as well (start_migration test path)
    - Assert at the SearchResponse / dict level (not at the SQL level) so the test reflects what an agent actually sees

    Populate .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-VALIDATION.md:
    - Frontmatter: status: approved; nyquist_compliant: true; wave_0_complete: true; created date preserved
    - Test Infrastructure table: Framework = "pytest 7.x + pytest-asyncio 1.3.0"; Config file = "server/pyproject.toml"; Quick run command = `cd server && pytest app/tests/rag/ app/tests/llm/ -q -m "rag or llm"`; Full suite command = `cd server && pytest app/tests/ -q`; Estimated runtime = ~60s
    - Sampling Rate section: per-task = quick run; per-wave = full suite; before /gsd:verify-work = full suite green; max feedback latency = 60s
    - Per-Task Verification Map: one row per task across plans 01–05. For each row: task ID (e.g., 02A-01-01 = Plan 01 Task 1), plan, wave, requirement, threat ref, expected secure behavior (short), test type (unit/integration/lint), automated command, file exists (✅ post-Plan-01 for all stubs), status (⬜ pending until execution). Include all 12 tasks from all five plans.
    - Wave 0 Requirements: list the eleven test files Plan 01 authored as ✅; otherwise list as ❌ if any unintended omission was discovered during execution.
    - Manual-Only Verifications: list one row — "Human review of AI-SPEC §5 eval dimensions (retrieval coverage / RRF rank quality / stale annotation visibility / cold-start fallback / provider key safety)". Manual reason: "Subjective rubric scoring per AI-SPEC Section 5.1 dimensions". Test instructions: "Run the Phase 2a integration suite, inspect three saved sample queries' raw JSON output, score each dimension Pass/Fail per AI-SPEC §5 rubric, approve if all five dimensions Pass or document accepted deviations".
    - Validation Sign-Off checklist: tick all 6 boxes; set Approval = "approved 2026-05-15"
  </action>
  <verify>
    <automated>cd server && pytest app/tests/integration/test_phase_2a_acceptance.py -q 2>&1 | tail -10 && cd server && pytest app/tests/ -q 2>&1 | tail -10 && grep -q "nyquist_compliant: true" .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-VALIDATION.md && grep -q "approved" .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-VALIDATION.md</automated>
  </verify>
  <acceptance_criteria>
    - server/app/tests/integration/test_phase_2a_acceptance.py contains at least seven test_ functions; each references a Phase 2a success criterion or AI-SPEC eval dimension in its docstring
    - test_acceptance_brain_search_returns_hybrid_v1 exists and asserts search_type=="hybrid_v1"
    - test_acceptance_cold_start_fts_v1 exists and asserts search_type=="fts_v1"
    - test_acceptance_truth_chunk_ranks_first exists and asserts results[0].kind=="truth"
    - test_acceptance_stale_annotation_surfaces exists and asserts is_stale is True
    - cd server && pytest app/tests/integration/test_phase_2a_acceptance.py -q exits 0 (all 7 tests pass)
    - cd server && pytest app/tests/ -q exits 0 (full suite green)
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-VALIDATION.md frontmatter contains nyquist_compliant: true AND wave_0_complete: true AND status: approved
    - VALIDATION.md Per-Task Verification Map table contains at least 12 task rows (one per task across plans 01–05)
    - VALIDATION.md Sampling Rate section names a quick-run command containing "pytest" and "rag or llm" or similar marker filter
    - VALIDATION.md Validation Sign-Off section has at least 6 checked boxes
  </acceptance_criteria>
  <done>
    Phase 2a acceptance criterion 1 ("brain.search with a semantic query returns top-k results ranked by RRF") is enforced by automated tests on BOTH the REST and MCP surfaces. Truth boost, stale annotation, and cold-start fallback are each enforced by dedicated tests. llm_usage cost recording is verified end-to-end. VALIDATION.md is populated for the verifier and operator audit trail. Full suite green; ready for human-verify checkpoint.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: Human verify — AI-SPEC §5 evaluation dimensions</name>
  <what-built>
    Phase 2a delivers:
    - LLM router (llm/router.py) routing all completion/embedding calls; UsageRecorder writes llm_usage rows under system RLS (Plans 01, 02)
    - Chunker + async embed worker; HNSW now populated for any non-skip note_type page (Plan 03)
    - Hybrid retriever (vector + BM25) + RRF fusion + 4-layer dedup + stale annotation; intent classifier with threshold-gated multi-query expansion (Plan 04)
    - brain.search (MCP) and POST /api/v1/search (REST) now return search_type ∈ {hybrid_v1, fts_v1, bm25_v1} (Plan 04)
    - Admin embedding-migration endpoints with estimate/start/status/cancel (Plan 05)
    - Phase 2a acceptance suite green (Plan 05 Task 2); VALIDATION.md populated
  </what-built>
  <how-to-verify>
    1. Boot the stack: `docker compose -f docker-compose.dev.yml up -d` (or local equivalent); wait for `/health` to return 200.
    2. Seed: create a user via `smartcopilot user create --username verifier --role admin`; log in to grab a JWT.
    3. Write three pages with varied content:
       a. A "person" page about "Jane Doe" with rich compiled_truth and 2 timeline events (e.g., 2024-01-15: joined NewCo; 2025-06-01: promoted to CTO).
       b. A "concept" page with a long compiled_truth section (≥ 1000 words) so it splits into multiple truth chunks.
       c. A page marked note_type="archived_fleeting" with random text (D-06 skip target).
    4. Wait ~90 seconds for the APScheduler embed_worker to embed the first two pages; verify via `psql` or `smartcopilot stats`: `SELECT count(*) FROM chunks WHERE embedding IS NULL;` should drop to zero for the two non-skip pages and stay > 0 if you intentionally leave skip-page rows (they should be zero entirely because the chunker skipped them).
    5. Run six probe queries via `curl -X POST http://localhost:8000/api/v1/search -H "Authorization: Bearer $JWT" -H "Content-Type: application/json" -d '{"query": "...", "limit": 10}'`:
       - "Jane Doe" (short, no expansion expected; should return hybrid_v1 with truth chunks ranked first)
       - "what did Jane do in 2025?" (≥6 words trigger; expansion fires; results include the 2025-06-01 timeline event chunk; check llm_usage table for a new row in tier="cheap" model)
       - "@web Tesla stock" (web_stub mode; Phase 5 deferred — should still return a non-500 response with search_type set)
       - "see [[Jane Doe]]" (graph-intent; Phase 2b deferred — Phase 2a falls through to hybrid; verify no 500)
       - One probe with intentionally non-existent text ("zxcvbnm12345") to exercise the empty-result envelope (should return results=[] not 500)
       - One probe right after writing a fresh page (cold-start window) BEFORE the embed worker runs — expect search_type="fts_v1" if the chunker created chunks but the embed worker hasn't run yet for this batch
    6. Score each AI-SPEC §5 evaluation dimension Pass/Fail by inspecting the raw JSON responses:
       - **Retrieval coverage**: query #1 returns ≥ 1 hit with chunk_id; query #6 returns ≥ 1 hit even if search_type="fts_v1"
       - **RRF rank quality + compiled-truth priority**: query #1 has a kind="truth" result at position 0 or 1
       - **Stale annotation**: if you manually backdate `pages.compiled_truth_updated_at` for page 3a and re-query, results carry is_stale=true with stale_days populated
       - **Cold-start fallback**: query #6 returns search_type="fts_v1" (or "bm25_v1") not an empty-results-with-no-fallback envelope
       - **Provider key safety**: `docker logs $container 2>&1 | grep -E "sk-[A-Za-z0-9]{20,}"` returns empty (no real key fragments leaked)
    7. Trigger the admin embedding-migration estimate endpoint with `curl -X GET http://localhost:8000/api/v1/admin/embedding-migration/estimate -H "Authorization: Bearer $ADMIN_JWT"` and confirm the response shape matches `{total_chunks, embedded_chunks, pending_chunks, estimated_minutes}`.
    8. Confirm `cd server && pytest app/tests/ -q` exits 0 against the running container (or equivalent local test DB).
  </how-to-verify>
  <resume-signal>
    Type "approved" with a one-line note for each of the 5 AI-SPEC §5 dimensions (Pass/Fail + observed evidence), or describe any failure with the exact request body and response payload that triggered it.
  </resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Admin caller -> /embedding-migration endpoints | require_admin gates read; require_fresh_auth gates destructive operations (start/cancel) per AUTH-07 |
| Migration worker (asyncio.create_task) -> chunks table | Runs under system_operation_context with session_with_rls; DDL bypasses any user-scoped RLS by design (chunks add/drop column is global) |
| CREATE INDEX CONCURRENTLY -> chunks_embedding_new_hnsw_idx | Long-running DDL acquires SHARE UPDATE EXCLUSIVE lock; cannot run inside a transaction (Pitfall 8); explicit AUTOCOMMIT connection isolates it |
| system_config.embedding_migration JSONB -> background task progress | Singleton row updated under system context; cancel_migration writes status="cancelled" which the worker polls each batch |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02A-05-01 | Elevation of Privilege | Non-admin starts embedding migration | mitigate | require_fresh_auth on /start and /cancel; require_admin on /estimate and /status; tested by test_start_requires_fresh_auth |
| T-02A-05-02 | Tampering | CREATE INDEX CONCURRENTLY inside transaction | mitigate | async with engine.connect() as conn: await conn.execution_options(isolation_level="AUTOCOMMIT"); inline comment cites Pitfall 8; acceptance grep verifies AUTOCOMMIT string |
| T-02A-05-03 | Denial of Service | Two concurrent /start calls double-run the migration | mitigate | start_migration reads SystemConfig; raises MigrationConflict if status=="running"; route returns 409 conflict |
| T-02A-05-04 | Tampering | Wrong target_dim corrupts pgvector column | mitigate | start_migration validates target_dim ∈ {768, 1536, 3072}; backfill loop asserts len(vec) == target_dim before INSERT; reject otherwise |
| T-02A-05-05 | Information Disclosure | api_key leaked through migration worker logs | mitigate | embed_chunks already strips api_key from kwargs (Plan 02); migration worker logs only chunk_ids/counts |
| T-02A-05-06 | Repudiation | No record of who started a migration | accept | system_config row records started_at but not user_id; Plan 5 does not add audit_log entry; deferred to Phase 6 OBS-03 (audit log API). Documented accepted risk |
| T-02A-05-SC | Tampering | npm/pip/cargo installs | mitigate | No new packages installed in Plan 05; all dependencies pinned in Plan 01 |
</threat_model>

<verification>
- Migration endpoint tests: cd server && pytest app/tests/routes/test_migration.py -q
- Acceptance suite: cd server && pytest app/tests/integration/test_phase_2a_acceptance.py -q
- Full server suite green: cd server && pytest app/tests/ -q
- TID gate: cd server && ruff check app/ --select TID
- Direct litellm import grep: grep -rE "^(import litellm|from litellm)" server/app/ --include="*.py" | grep -vE "/llm/(router|tiers|keys|usage)\.py:" | grep -v "/tests/" returns empty
- Human-verify checkpoint completed with five dimension scores recorded
</verification>

<success_criteria>
1. GET/POST /api/v1/admin/embedding-migration/{estimate,start,status,cancel} all return the documented payloads with correct auth gates (RAG-07)
2. Phase 2a acceptance suite (7 tests) passes green
3. Full server pytest suite passes; no regressions in Phase 1a/1b/1c/1d tests
4. Human-verify checkpoint approved with five AI-SPEC §5 dimension scores
5. VALIDATION.md frontmatter shows nyquist_compliant: true, wave_0_complete: true, status: approved
</success_criteria>

<output>
Create .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-05-SUMMARY.md when done.
</output>
