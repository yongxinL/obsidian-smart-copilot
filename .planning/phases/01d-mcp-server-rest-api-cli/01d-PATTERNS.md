# Phase 1d: MCP Server + REST API + CLI - Pattern Map

**Mapped:** 2026-05-09
**Files analyzed:** 14 new/modified files
**Analogs found:** 13 / 14

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `server/app/mcp/server.py` | provider | request-response | `server/app/vault/watcher.py` (async main + SIGTERM) | role-match |
| `server/app/mcp/tools/__init__.py` | config | — | `server/app/cli/__init__.py` | role-match |
| `server/app/mcp/tools/brain.py` | service | request-response | `server/app/routes/admin.py` + `services/pages.py` | role-match |
| `server/app/mcp/tools/capability.py` | service | request-response | `server/app/routes/health.py` | role-match |
| `server/app/mcp/tools/ingest.py` (stub) | service | request-response | `server/app/routes/admin.py` (stub pattern) | role-match |
| `server/app/routes/pages.py` | controller | CRUD | `server/app/routes/auth.py` + `routes/admin.py` | exact |
| `server/app/routes/search.py` | controller | request-response | `server/app/routes/auth.py` | role-match |
| `server/app/routes/vault.py` | controller | request-response | `server/app/routes/admin.py` | role-match |
| `server/app/routes/ws.py` | controller | event-driven | `server/app/routes/auth.py` (auth pattern) | partial |
| `server/app/services/pages.py` (extend) | service | CRUD | itself — already exists | exact |
| `server/app/cli/main.py` (extend) | utility | request-response | itself + `cli/mcp_token.py` | exact |
| `server/app/cli/page.py` (new subcommand) | utility | CRUD | `server/app/cli/mcp_token.py` | exact |
| `server/app/cli/doctor.py` | utility | request-response | `server/app/cli/user.py` | role-match |
| `server/alembic/versions/0004_phase_1d_search_vector.py` | migration | batch | `server/alembic/versions/0003_phase_1c_vault.py` | exact |

---

## Pattern Assignments

### `server/app/mcp/server.py` (MCP stdio + Streamable HTTP entry point)

**Analog:** `server/app/vault/watcher.py` (async main with SIGTERM), `server/app/routes/auth.py` (Bearer validation)

**Imports pattern** (from watcher.py lines 1–14, core.py lines 1–13):
```python
from __future__ import annotations

import asyncio
import os
import signal
import sys

import structlog

from app.auth.core import validate_bearer
from app.auth.context import OperationContext
from app.logging.redaction import configure_logging
from app.settings import settings
```

**Async main + SIGTERM pattern** (watcher.py lines 263–315):
```python
async def _amain() -> int:
    configure_logging()
    stop_event = asyncio.Event()

    def _stop(signum, _frame) -> None:
        stop_event.set()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    # ... setup mcp server ...

    await stop_event.wait()
    return 0


def main() -> int:
    return asyncio.run(_amain())


if __name__ == "__main__":
    sys.exit(main())
```

**MCP Bearer auth pattern** (from CLAUDE.md + core.py validate_bearer lines 94–123):
```python
# STDIO: read env var at startup; validate ONCE before entering tool loop
# Never write to stdout in stdio mode — any non-JSON-RPC output corrupts framing
token = os.environ.get("SMARTCOPILOT_MCP_TOKEN")
result = await validate_bearer(token)
if result.error is not None:
    print(f"AUTH ERROR: {result.error}", file=sys.stderr)
    return 1

# Build OperationContext from AuthResult (transport="mcp_stdio", remote=False)
ctx = OperationContext(
    user_id=result.user_id,
    role=result.role,
    transport="mcp_stdio",
    remote=False,
    client_name="mcp_stdio",
    request_id="mcp-stdio",
    mcp_token_id=result.mcp_token_id,
)
```

**HTTP entry point pattern** (CLAUDE.md notes):
```python
# stateless_http=True required for multi-worker-safe deployment
# json_response=True for broad MCP client compatibility
# Authorization: Bearer header validated per request
```

---

### `server/app/mcp/tools/brain.py` (real MCP tool implementations)

**Analog:** `server/app/routes/admin.py` (route→service call pattern), `server/app/services/pages.py` (service functions)

**Imports pattern** (admin.py lines 1–10, pages.py lines 1–31):
```python
from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import OperationContext
from app.db_session import session_with_rls
from app.services.pages import (
    PageNotFound,
    TimelineViolation,
    append_timeline,
    read_page,
    soft_delete_page,
    write_page,
)
```

**MCP tool → service call pattern** (mirrors admin.py lines 37–79 structure):
```python
# Tool function: validate inputs → build ctx → session_with_rls → call service → return dict
async def brain_put(ctx: OperationContext, *, slug: str, content: str, vault_id: uuid.UUID) -> dict:
    async for session in session_with_rls(ctx):
        try:
            page = await write_page(
                session, ctx,
                slug=slug,
                raw_content=content.encode("utf-8"),
                vault_id=vault_id,
            )
            await session.commit()
        except PageNotFound:
            return {"error": {"code": "not_found", "message": f"page {slug!r} not found"}}
        except TimelineViolation as exc:
            return {"error": {"code": "timeline_violation", "message": str(exc)}}
    return {"slug": page.slug, "status": "ok"}
```

**Structured stub pattern** (D-05 — registered tool returns not_implemented, not protocol error):
```python
# All stub modules (ingest.py, enrich.py, etc.) use this exact shape:
async def stub_tool(ctx: OperationContext, **kwargs) -> dict:
    return {
        "error": {
            "code": "not_implemented",
            "message": "tool available in Phase 2a",
            "available_in_phase": "2a",
        }
    }
```

**Error handling pattern** (admin.py lines 44–79):
```python
# Services raise domain exceptions; MCP layer catches and returns structured error dicts
# Never raise protocol-level errors for expected failures — only for truly unknown tools
try:
    result = await some_service_call(session, ctx, ...)
    await session.commit()
except SomeDomainError as exc:
    return {"error": {"code": "domain_error_code", "message": str(exc)}}
```

---

### `server/app/mcp/tools/capability.py` (capability_discovery tool)

**Analog:** `server/app/routes/health.py` (simple static-data endpoint)

**Pattern** (health.py lines 1–17):
```python
from __future__ import annotations

from app.auth.context import OperationContext

# capability_discovery and GET /api/v1/capabilities share ONE service function
def get_capabilities() -> dict:
    return {
        "transports": ["stdio", "http"],
        "ingestion_limits": {},
        "clipboard_available": False,
        "phase": "1d",
    }

async def capability_discovery(ctx: OperationContext) -> dict:  # noqa: ARG001
    return get_capabilities()
```

---

### `server/app/routes/pages.py` (page CRUD REST routes)

**Analog:** `server/app/routes/auth.py` (request→service→response pattern), `server/app/routes/admin.py` (Depends guards)

**Imports pattern** (auth.py lines 1–34, admin.py lines 1–10):
```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import OperationContext
from app.auth.deps import require_user
from app.dependencies import get_db_session, get_operation_context
from app.services.pages import (
    PageNotFound,
    TimelineViolation,
    append_timeline,
    read_page,
    soft_delete_page,
    write_page,
)

router = APIRouter(prefix="/api/v1/pages", tags=["pages"])
```

**Core CRUD pattern** (admin.py lines 37–79, auth.py lines 67–128):
```python
# PUT /api/v1/pages/{slug} — maps to brain.put
@router.put("/{slug}", response_model=PageResponse)
async def put_page(
    slug: str,
    payload: PageWriteIn,
    ctx: OperationContext = Depends(require_user),      # noqa: B008
    session: AsyncSession = Depends(get_db_session),    # noqa: B008
) -> PageResponse:
    try:
        page = await write_page(
            session, ctx,
            slug=slug,
            raw_content=payload.content.encode("utf-8"),
            vault_id=ctx.user_id,  # Phase 1d: vault_id resolved from ctx
        )
        await session.commit()
    except PageNotFound:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"page {slug!r} not found"}},
        )
    except TimelineViolation as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "timeline_violation", "message": str(exc)}},
        )
    return PageResponse.model_validate(page)
```

**Error envelope pattern** (admin.py lines 47–52, auth.py lines 100–108):
```python
# ALL HTTPException detail must use: {"error": {"code": "...", "message": "..."}}
# main.py _flatten_http_error handler removes the {"detail": ...} wrapper
raise HTTPException(
    status_code=404,
    detail={"error": {"code": "not_found", "message": "..."}},
)
```

**Pydantic response model pattern** (auth.py lines 41–49):
```python
class PageResponse(BaseModel):
    page_id: uuid.UUID
    slug: str
    title: str | None
    note_type: str
    compiled_truth: str | None
    timeline: str | None
    updated_at: datetime
    # encrypted_key fields: Field(exclude=True) — not applicable here
    # but: never leak frontmatter._resolved_links or internal system keys
```

---

### `server/app/routes/search.py` (POST /api/v1/search)

**Analog:** `server/app/routes/auth.py` (POST handler pattern)

**Imports pattern** (auth.py lines 1–33):
```python
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import OperationContext
from app.auth.deps import require_user
from app.dependencies import get_db_session

router = APIRouter(prefix="/api/v1", tags=["search"])
```

**POST handler with response shape** (auth.py lines 67–128):
```python
class SearchIn(BaseModel):
    query: str = Field(..., min_length=1, max_length=512)
    limit: int = Field(default=20, ge=1, le=100)
    namespace: str = Field(default="private")  # "private" | "shared" | "all"

class SearchResult(BaseModel):
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
    results: list[SearchResult]
    total: int
    query: str
    search_type: str = "fts_v1"  # D-02: forward-compat hook; Phase 2a changes to "hybrid_v1"

@router.post("/search", response_model=SearchResponse)
async def search_pages(
    payload: SearchIn,
    ctx: OperationContext = Depends(require_user),    # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> SearchResponse:
    results = await search_pages_fts(session, ctx, query=payload.query, limit=payload.limit)
    return SearchResponse(results=results, total=len(results), query=payload.query)
```

---

### `server/app/routes/vault.py` (vault-level REST operations)

**Analog:** `server/app/routes/admin.py` (prefixed router, Depends guards)

**Router setup pattern** (admin.py lines 28–29):
```python
router = APIRouter(prefix="/api/v1/vault", tags=["vault"])
```

**GET /api/v1/capabilities** shares payload with `capability_discovery` MCP tool:
```python
from app.mcp.tools.capability import get_capabilities

@router.get("/capabilities")
async def get_capabilities_endpoint() -> dict:
    return get_capabilities()
```

---

### `server/app/routes/ws.py` (WebSocket /api/v1/ws)

**Analog:** `server/app/auth/core.py` (validate_bearer for first-frame JWT auth — D-09), `server/app/models/index_event.py` (event payload shape)

**No existing WebSocket analog in codebase.** Use CLAUDE.md patterns + D-07/D-08/D-09 from CONTEXT.md.

**First-frame auth pattern** (D-09, derived from auth/core.py validate_bearer):
```python
# WebSocket: Depends() is NOT usable for upgrade; auth is first-frame
from fastapi import WebSocket, WebSocketDisconnect
from app.auth.core import validate_jwt  # JWT for WS (not bearer — D-09 uses access_jwt)

@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    try:
        # First frame MUST be {"type": "auth", "data": {"token": "<access_jwt>"}}
        frame = await asyncio.wait_for(ws.receive_json(), timeout=10.0)
        if frame.get("type") != "auth":
            await ws.send_json({"type": "auth_error",
                                "error": {"code": "unauthorized", "message": "first frame must be auth"}})
            await ws.close()
            return
        result = validate_jwt(frame.get("data", {}).get("token"))
        if result.error or not result.user_id:
            await ws.send_json({"type": "auth_error",
                                "error": {"code": "unauthorized", "message": "invalid token"}})
            await ws.close()
            return
        # Build OperationContext (transport="rest", remote=True for WS per CONTEXT.md)
        ctx = OperationContext(user_id=result.user_id, role=result.role,
                               transport="rest", remote=True,
                               client_name="ws", request_id="ws")
        # Subscribe to LISTEN/NOTIFY on 'index_events' channel via raw asyncpg connection
        # Route events to this socket filtered by user_id == ctx.user_id (D-08)
    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
```

**LISTEN/NOTIFY pattern** (D-07, asyncpg raw connection — NOT SQLAlchemy):
```python
# asyncpg LISTEN/NOTIFY must use a raw asyncpg connection, not SQLAlchemy session
import asyncpg
conn = await asyncpg.connect(settings.database_url_asyncpg)
await conn.add_listener("index_events", callback)
```

---

### `server/app/services/pages.py` (extend with search_pages_fts + backlinks + history + diff + revert)

**Analog:** itself — same transport-agnostic service pattern already established (lines 1–31)

**Existing pattern to preserve** (pages.py lines 1–34):
```python
# NO FastAPI imports — only OperationContext + AsyncSession in, domain objects out
from app.auth.context import OperationContext
from sqlalchemy.ext.asyncio import AsyncSession

# tsvector FTS query pattern for brain_search (D-01, D-02, D-03):
from sqlalchemy import text

async def search_pages_fts(
    session: AsyncSession,
    ctx: OperationContext,
    *,
    query: str,
    limit: int = 20,
    namespace: str = "private",
) -> list[SearchHit]:
    # websearch_to_tsquery for natural language; plainto_tsquery as fallback
    rows = await session.execute(
        text("""
            SELECT id, slug, title, note_type, updated_at,
                   ts_rank(search_vector, websearch_to_tsquery('english', :q)) AS score,
                   ts_headline('english', coalesce(compiled_truth,''), websearch_to_tsquery('english', :q),
                               'MaxFragments=1,MaxWords=20') AS snippet,
                   (search_vector @@ websearch_to_tsquery('english', :q)) AS matched
            FROM pages
            WHERE vault_id = :vid
              AND deleted_at IS NULL
              AND search_vector @@ websearch_to_tsquery('english', :q)
            ORDER BY score DESC
            LIMIT :lim
        """),
        {"q": query, "vid": str(ctx.user_id), "lim": limit},
    )
    ...
```

**History/diff/revert pattern** (page_version.py model lines 27–56 — query page_versions table):
```python
# brain.history: SELECT * FROM page_versions WHERE page_id = :pid ORDER BY version DESC
# brain.diff: fetch two specific versions, return unified diff of compiled_truth
# brain.revert: call upsert_page with ParsedPage built from the target version row
```

---

### `server/app/cli/main.py` (extend with new subcommands)

**Analog:** itself (lines 1–40)

**Extension pattern** (cli/main.py lines 1–40):
```python
# Add new subcommand modules following existing pattern:
from app.cli import doctor as doctor_cmd
from app.cli import page as page_cmd

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="smartcopilot")
    sub = p.add_subparsers(dest="command", required=True)

    user_cmd.add_subparser(sub)
    mcp_token_cmd.add_subparser(sub)
    provider_key_cmd.add_subparser(sub)
    page_cmd.add_subparser(sub)     # NEW Phase 1d
    doctor_cmd.add_subparser(sub)   # NEW Phase 1d

    return p
```

**MCP serve subcommand pattern** (cli/main.py asyncio.run style):
```python
# mcp serve --stdio / --http: just exec the mcp.server main functions
from app.mcp import server as mcp_server

def _handle_mcp_serve(args: argparse.Namespace) -> int:
    if args.transport == "stdio":
        return mcp_server.main_stdio()
    return mcp_server.main_http()
```

---

### `server/app/cli/page.py` (vault CRUD CLI commands)

**Analog:** `server/app/cli/mcp_token.py` (exact pattern — add_subparser + async handlers)

**Imports pattern** (mcp_token.py lines 1–11):
```python
from __future__ import annotations

import argparse

from app.auth.context import OperationContext, system_operation_context
from app.dependencies import session_with_rls
from app.services.pages import PageNotFound, read_page, write_page, soft_delete_page
```

**Subparser + async handler pattern** (mcp_token.py lines 13–61):
```python
def add_subparser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("page", help="vault page CRUD")
    psub = p.add_subparsers(dest="page_command", required=True)

    get = psub.add_parser("get", help="get a page by slug")
    get.add_argument("--slug", required=True)
    get.add_argument("--vault-id", required=True)
    get.set_defaults(func=_handle_get)
    # ... put, delete, list, search ...


async def _handle_get(args: argparse.Namespace) -> int:
    ctx = system_operation_context(client_name="cli", request_id="cli-page-get")
    async for session in session_with_rls(ctx):
        try:
            page = await read_page(session, vault_id=uuid.UUID(args.vault_id), slug=args.slug)
        except PageNotFound as e:
            print(f"error: {e}", flush=True)
            return 2
    print(f"slug={page.slug}\ntitle={page.frontmatter.get('title')}", flush=True)
    return 0
```

---

### `server/app/cli/doctor.py` (system health checks)

**Analog:** `server/app/cli/user.py` (async handler, no DB writes needed)

**Pattern** (user.py lines 25–45):
```python
from __future__ import annotations

import argparse
import os

from app.auth.context import system_operation_context
from app.db_session import session_with_rls
from app.encryption import FernetKeyMissing, fernet
from app.settings import settings


def add_subparser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("doctor", help="report system health")
    p.set_defaults(func=_handle_doctor)


async def _handle_doctor(args: argparse.Namespace) -> int:  # noqa: ARG001
    # Check Fernet key
    try:
        fernet()
        print("fernet_key: OK")
    except FernetKeyMissing:
        print("fernet_key: MISSING — set SMARTCOPILOT_FERNET_KEY")
        return 1

    # Check inotify limit (D-14)
    try:
        watches = int(Path("/proc/sys/fs/inotify/max_user_watches").read_text())
        print(f"inotify_max_user_watches: {watches}")
    except OSError:
        print("inotify_max_user_watches: (unreadable — not Linux?)")

    # Check DB connectivity
    ctx = system_operation_context(client_name="cli", request_id="doctor")
    async for session in session_with_rls(ctx):
        from sqlalchemy import text
        await session.execute(text("SELECT 1"))
        print("db_connection: OK")

    return 0
```

---

### `server/alembic/versions/0004_phase_1d_search_vector.py` (tsvector column + GIN index)

**Analog:** `server/alembic/versions/0003_phase_1c_vault.py` (exact migration structure)

**Migration header + upgrade pattern** (0003 lines 1–46):
```python
"""phase_1d_search_vector

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-09

Phase 1d adds:
  * pages.search_vector TSVECTOR GENERATED ALWAYS AS (...) STORED (D-03)
  * GIN index on pages.search_vector for fast FTS queries
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # GENERATED ALWAYS AS requires raw SQL — SQLAlchemy has no ORM abstraction for it
    op.execute(
        """
        ALTER TABLE pages
        ADD COLUMN search_vector tsvector
            GENERATED ALWAYS AS (
                to_tsvector('english',
                    coalesce(title, '') || ' ' || coalesce(compiled_truth, ''))
            ) STORED
        """
    )
    op.execute(
        "CREATE INDEX ix_pages_search_vector ON pages USING GIN (search_vector)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_pages_search_vector")
    op.execute("ALTER TABLE pages DROP COLUMN IF EXISTS search_vector")
```

**Important:** `title` column does NOT exist on the `Page` model yet (only `slug`, `frontmatter`, `compiled_truth`). The GENERATED expression should use `coalesce(frontmatter->>'title', '') || ' ' || coalesce(compiled_truth, '')` unless a `title` column is added in this same migration.

---

## Shared Patterns

### Authentication — require_user dependency
**Source:** `server/app/auth/deps.py` lines 38–42, `server/app/dependencies.py` lines 39–73
**Apply to:** All `routes/pages.py`, `routes/search.py`, `routes/vault.py` handlers
```python
from app.auth.deps import require_user
from app.dependencies import get_db_session

@router.get("/{slug}")
async def handler(
    ctx: OperationContext = Depends(require_user),      # noqa: B008
    session: AsyncSession = Depends(get_db_session),    # noqa: B008
) -> ...:
```

### RLS Session Discipline
**Source:** `server/app/db_session.py` lines 24–62
**Apply to:** All service functions called from MCP tools AND all CLI handlers
```python
# Always via session_with_rls — never raw async_session_factory
async for session in session_with_rls(ctx):
    # ... do work ...
    await session.commit()
# RESET GUC is in finally: block inside session_with_rls — never manually RESET
```

### Error Envelope
**Source:** `server/app/main.py` lines 70–77
**Apply to:** ALL `routes/` handlers — every HTTPException must use this shape
```python
raise HTTPException(
    status_code=NNN,
    detail={"error": {"code": "snake_case_code", "message": "human readable"}},
)
# main.py exception handler flattens {"detail": {"error": ...}} to {"error": ...}
```

### Transport-Agnostic Services
**Source:** `server/app/services/pages.py` lines 1–9, `server/app/services/users.py` lines 1–5
**Apply to:** All new service functions; MCP tool implementations
```python
# NO FastAPI imports anywhere in services/
# NO HTTPException in services/
# Signature: (session: AsyncSession, ctx: OperationContext, *, ...) -> DomainObject
# Raise domain exceptions (PageNotFound, TimelineViolation) — never HTTP exceptions
```

### Structlog Logging
**Source:** `server/app/services/pages.py` line 34, `server/app/vault/watcher.py` line 40
**Apply to:** All new service and MCP tool modules
```python
import structlog
log = structlog.get_logger("smart_copilot.<module_name>")
# Usage: log.info("event_name", key=value, ...) — structured key=value, never f-strings in log calls
```

### OperationContext Transport Values
**Source:** `server/app/auth/context.py` lines 31–46 (D-22)
**Apply to:** MCP tool handlers, WebSocket handler, CLI handlers
```python
# transport="mcp_http",  remote=True   — MCP Streamable HTTP callers
# transport="mcp_stdio", remote=False  — MCP stdio callers
# transport="rest",      remote=True   — REST + WebSocket callers
# transport="cli",       remote=False  — CLI subcommands
# transport="system",    remote=False  — APScheduler / internal
```

### Route Registration in `main.py`
**Source:** `server/app/main.py` lines 79–82
**Apply to:** All new routes in Phase 1d
```python
# In create_app(), after existing routers:
from app.routes.pages import router as pages_router
from app.routes.search import router as search_router
from app.routes.vault import router as vault_router

app.include_router(pages_router)
app.include_router(search_router)
app.include_router(vault_router)
# WebSocket route: app.add_websocket_route("/api/v1/ws", ws_endpoint)
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `server/app/routes/ws.py` | controller | event-driven | No WebSocket or LISTEN/NOTIFY pattern exists in codebase yet |

---

## Metadata

**Analog search scope:** `server/app/routes/`, `server/app/services/`, `server/app/cli/`, `server/app/auth/`, `server/app/mcp/`, `server/alembic/versions/`, `server/app/vault/`
**Files scanned:** 19 source files read
**Pattern extraction date:** 2026-05-09
