# Phase 02B: Knowledge Graph + Agent Runner - Pattern Map

**Mapped:** 2026-05-16
**Files analyzed:** 18 new/modified files
**Analogs found:** 16 / 18

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `server/alembic/versions/0006_phase_2b_schema.py` | migration | transform | `server/alembic/versions/0003_phase_1c_vault.py` | exact |
| `server/app/models/link.py` (modify) | model | CRUD | `server/app/models/entity.py` | exact |
| `server/app/models/conversation.py` (modify) | model | CRUD | `server/app/models/golden_eval.py` | exact |
| `server/app/models/golden_eval.py` (modify) | model | CRUD | `server/app/models/golden_eval.py` | exact |
| `server/app/services/graph.py` | service | CRUD | `server/app/services/pages.py` | role-match |
| `server/app/services/agent_service.py` | service | request-response | `server/app/services/pages.py` | role-match |
| `server/app/agent/__init__.py` | utility | — | `server/app/mcp/tools/__init__.py` | role-match |
| `server/app/agent/react_loop.py` | service | request-response | `server/app/scheduler/jobs/reconcile_vault.py` | partial |
| `server/app/agent/models.py` | model | transform | `server/app/models/base.py` | partial |
| `server/app/agent/prompts.py` | utility | — | none | no-analog |
| `server/app/agent/tools/__init__.py` | utility | — | `server/app/mcp/tools/__init__.py` | role-match |
| `server/app/agent/tools/brain.py` | middleware | request-response | `server/app/mcp/tools/brain.py` | exact |
| `server/app/agent/tools/graph.py` | middleware | request-response | `server/app/mcp/tools/graph.py` | exact |
| `server/app/agent/tools/entity.py` | middleware | request-response | `server/app/mcp/tools/entity.py` | exact |
| `server/app/agent/tools/jobs.py` | middleware | request-response | `server/app/mcp/tools/jobs.py` | exact |
| `server/app/mcp/tools/graph.py` (modify) | middleware | request-response | `server/app/mcp/tools/brain.py` | exact |
| `server/app/mcp/tools/brain.py` (modify — add brain.query) | middleware | request-response | `server/app/mcp/tools/brain.py` | exact |
| `server/app/observability/agent_spans.py` | utility | event-driven | `server/app/logging/redaction.py` | partial |
| `server/app/routes/query.py` | route | request-response | `server/app/routes/search.py` | exact |
| `server/app/tests/graph/test_wikilink_extractor.py` | test | CRUD | `server/app/tests/vault/test_parser.py` | exact |
| `server/app/tests/graph/test_graph_traversal.py` | test | CRUD | `server/app/tests/vault/test_pages_service.py` | exact |
| `server/app/tests/graph/test_entity_merge.py` | test | CRUD | `server/app/tests/vault/test_pages_service.py` | role-match |
| `server/app/tests/agent/test_react_loop.py` | test | request-response | `server/app/tests/vault/test_pages_service.py` | role-match |
| `server/app/tests/agent/test_tool_registry.py` | test | — | `server/app/tests/vault/test_parser.py` | role-match |
| `server/app/tests/agent/test_conversation_persistence.py` | test | CRUD | `server/app/tests/vault/test_wikilinks.py` | exact |
| `server/tests/fixtures/golden_queries.yaml` | config | — | none | no-analog |
| `server/scripts/eval_agent.py` | utility | batch | `server/app/scheduler/jobs/reconcile_vault.py` | partial |

---

## Pattern Assignments

### `server/alembic/versions/0006_phase_2b_schema.py` (migration, transform)

**Analog:** `server/alembic/versions/0003_phase_1c_vault.py`

**Imports pattern** (lines 1-22):
```python
"""phase_2b_schema

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-XX

Phase 2b adds:
  * links: anchor_text, fragment, target_text, target_slug columns; dst_entity_id nullable
  * messages: token_usage JSONB, model TEXT columns
  * conversations_mcp_mode_enum: rename-and-recreate from disabled/client/server to disable/auto/manual
  * golden_queries: expected_top_slug, expected_status, expected_tool_first, expected_edge_type, notes
"""
from __future__ import annotations
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op
```

**Core pattern for ALTER TABLE + nullable FK** (0003 lines 30-46):
```python
def upgrade() -> None:
    op.add_column("links", sa.Column("anchor_text", sa.Text(), nullable=True))
    op.add_column("links", sa.Column("fragment", sa.Text(), nullable=True))
    op.add_column("links", sa.Column("target_text", sa.Text(), nullable=True))
    op.add_column("links", sa.Column("target_slug", sa.Text(), nullable=True))
    op.add_column("links", sa.Column("unresolved", sa.Boolean(), nullable=False, server_default="false"))
    # Make dst_entity_id nullable (D-04 unresolved wikilinks)
    op.alter_column("links", "dst_entity_id", nullable=True)
```

**Enum rename-and-recreate pattern** (0003 lines 58-69 — exact strategy for mcp_mode enum fix):
```python
    # PostgreSQL cannot DROP VALUE from ENUM — must rename+recreate
    op.execute(
        "CREATE TYPE conversations_mcp_mode_enum_new AS ENUM ('disable', 'auto', 'manual')"
    )
    op.execute(
        "ALTER TABLE conversations ADD COLUMN mcp_mode_new conversations_mcp_mode_enum_new "
        "NOT NULL DEFAULT 'disable'::conversations_mcp_mode_enum_new"
    )
    op.execute("ALTER TABLE conversations DROP COLUMN mcp_mode")
    op.execute("ALTER TABLE conversations RENAME COLUMN mcp_mode_new TO mcp_mode")
    op.execute("DROP TYPE conversations_mcp_mode_enum")
    op.execute("ALTER TYPE conversations_mcp_mode_enum_new RENAME TO conversations_mcp_mode_enum")
```

---

### `server/app/models/link.py` (modify — add wikilink columns, make dst_entity_id nullable)

**Analog:** `server/app/models/entity.py` + existing `server/app/models/link.py`

**Current state** (link.py lines 1-47):
`dst_entity_id` is `nullable=False` — must be changed to `nullable=True`. Missing: `anchor_text`, `fragment`, `target_text`, `target_slug`, `unresolved`.

**Imports pattern** (link.py lines 1-16):
```python
from __future__ import annotations
import uuid
from decimal import Decimal
from sqlalchemy import UUID, Boolean, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin
```

**New fields to add** (modeled on entity.py ARRAY + link.py pattern):
```python
# Add after source_kind field:
anchor_text: Mapped[str | None] = mapped_column(Text, nullable=True)
fragment: Mapped[str | None] = mapped_column(Text, nullable=True)
target_text: Mapped[str | None] = mapped_column(Text, nullable=True)
target_slug: Mapped[str | None] = mapped_column(Text, nullable=True)
unresolved: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
# Change dst_entity_id to nullable=True (D-04)
```

---

### `server/app/models/conversation.py` (modify — add token_usage, model; fix mcp_mode enum)

**Analog:** `server/app/models/conversation.py` (self-reference) + `server/app/models/golden_eval.py`

**Existing mcp_mode_enum** (conversation.py lines 19-25) — values must become `disable/auto/manual`:
```python
mcp_mode_enum = PG_ENUM(
    "disable",
    "auto",
    "manual",
    name="conversations_mcp_mode_enum",
    create_constraint=True,
)
```

**New Message columns to add** (modeled on golden_eval.py JSONB pattern, lines 74-75):
```python
# Add to Message model after tool_calls:
token_usage: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
model: Mapped[str | None] = mapped_column(Text, nullable=True)
```

---

### `server/app/models/golden_eval.py` (modify — add eval fields to GoldenQuery)

**Analog:** `server/app/models/golden_eval.py` (self-reference)

**Fields pattern** (golden_eval.py lines 39-58):
```python
# Add after tags column in GoldenQuery:
expected_top_slug: Mapped[str | None] = mapped_column(Text, nullable=True)
expected_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
expected_tool_first: Mapped[str | None] = mapped_column(String(128), nullable=True)
expected_edge_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
notes: Mapped[str | None] = mapped_column(Text, nullable=True)
```

---

### `server/app/services/graph.py` (service, CRUD)

**Analog:** `server/app/services/pages.py`

**Imports pattern** (pages.py lines 22-48):
```python
from __future__ import annotations
import re
import uuid
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.context import OperationContext
from app.models.entity import Entity
from app.models.link import Link
from app.vault.parser import ParsedPage, _WIKILINK_RE
from app.vault.paths import validate_slug
```

**Service function signature pattern** (pages.py lines 149-157):
```python
async def extract_and_upsert_links(
    session: AsyncSession,
    ctx: OperationContext,
    *,
    page_id: uuid.UUID,
    parsed: ParsedPage,
    vault_id: uuid.UUID,
) -> int:
    """Extract wikilinks from body and frontmatter; upsert into links table.
    Returns count of links written. Side-effect-free for pattern matching.
    """
```

**RLS session pattern** (pages.py lines 149-167, schedler/reconcile_vault.py lines 38-44):
```python
# NOTE: graph.py is called FROM an already-open session (not using session_with_rls directly).
# The session is opened by the caller (pages.py write_page or MCP tool).
# graph.py only receives session + ctx — it does NOT open its own session.
```

**Upsert pattern** (pages.py upsert_page — use INSERT ... ON CONFLICT DO UPDATE):
```python
await session.execute(
    text("""
        INSERT INTO links (id, src_page_id, dst_entity_id, link_type, confidence,
                          source_kind, anchor_text, fragment, target_text, target_slug, unresolved,
                          created_at, updated_at)
        VALUES (:id, :src_page_id, :dst_entity_id, :link_type, :confidence,
                :source_kind, :anchor_text, :fragment, :target_text, :target_slug, :unresolved,
                now(), now())
        ON CONFLICT (src_page_id, target_text, link_type) DO UPDATE SET
            anchor_text = EXCLUDED.anchor_text,
            fragment = EXCLUDED.fragment,
            target_slug = EXCLUDED.target_slug,
            unresolved = EXCLUDED.unresolved,
            updated_at = now()
    """),
    {...},
)
```

**Error handling pattern** (pages.py lines 107-109):
```python
except Exception as exc:  # noqa: BLE001
    log.exception("extract_links_failed", page_id=str(page_id))
    raise
```

---

### `server/app/services/agent_service.py` (service, request-response)

**Analog:** `server/app/services/pages.py`

**Imports pattern** (pages.py lines 22-48 — adapt):
```python
from __future__ import annotations
import uuid
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.context import OperationContext
from app.dependencies import session_with_rls
from app.models.conversation import Conversation, Message
```

**Session-with-RLS pattern for standalone service function** (reconcile_vault.py lines 37-44):
```python
async def persist_agent_invocation(
    op_ctx: OperationContext,
    session_id: uuid.UUID | None,
    user_query: str,
    result,  # AgentResponse
    model: str,
) -> uuid.UUID:
    async for session in session_with_rls(op_ctx):
        conv = await _get_or_create_conversation(session, op_ctx, session_id)
        # ...build and add user_msg, asst_msg...
        await session.commit()
        return asst_msg.id
```

**get_or_create pattern** (modeled on pages.py `_next_version` query):
```python
async def _get_or_create_conversation(
    session: AsyncSession,
    ctx: OperationContext,
    session_id: uuid.UUID | None,
) -> Conversation:
    if session_id:
        result = await session.execute(
            select(Conversation).where(
                Conversation.id == session_id,
                Conversation.user_id == ctx.user_id,
            )
        )
        conv = result.scalar_one_or_none()
        if conv:
            return conv
    # Create new single-turn conversation (D-09)
    conv = Conversation(user_id=ctx.user_id, mcp_mode="disable", web_search_enabled=False)
    session.add(conv)
    await session.flush()
    return conv
```

---

### `server/app/agent/react_loop.py` (service, request-response)

**Analog:** `server/app/scheduler/jobs/reconcile_vault.py` (async loop with structlog + error handling) + research patterns from RESEARCH.md

**Imports pattern** (reconcile_vault.py lines 1-28):
```python
from __future__ import annotations
import asyncio
import uuid
from typing import Any, Literal
import structlog
import litellm
from app.auth.context import OperationContext
from app.agent.models import AgentResponse, ToolTrace
from app.agent.tools import TOOL_REGISTRY, TOOL_SPECS
from app.agent.prompts import BRAIN_FIRST_SYSTEM_PROMPT
```

**Bounded async loop with structlog** (reconcile_vault.py lines 32-131 pattern):
```python
log = structlog.get_logger("smart_copilot.agent.react_loop")

MAX_ITERATIONS = 10
TOOL_CHOICE = "auto"

async def run_react_loop(
    ctx: OperationContext,
    user_query: str,
    vault_id: uuid.UUID,
) -> AgentResponse:
    """Bounded ReAct loop: up to MAX_ITERATIONS thought→action→observation cycles.
    D-05: returns best partial answer with status='max_iterations_reached' on limit.
    D-06: brain-first — brain.search before any external tool.
    D-07: retryable vs non-retryable error classification via LiteLLM exceptions.
    """
    messages = [
        {"role": "system", "content": BRAIN_FIRST_SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ]
    tool_traces: list[ToolTrace] = []
    iteration = 0

    while iteration < MAX_ITERATIONS:
        iteration += 1
        log.info("react_iteration", iteration=iteration, ctx_user=str(ctx.user_id))
        try:
            response = await litellm.acompletion(
                model=...,
                messages=messages,
                tools=TOOL_SPECS,
                tool_choice=TOOL_CHOICE,
            )
        except litellm.exceptions.AuthenticationError as exc:
            # Non-retryable (D-07)
            return AgentResponse(status="tool_error", error=str(exc))
        except litellm.exceptions.Timeout:
            # Retryable once (D-07)
            ...
        # Check for finish (no tool calls)
        choice = response.choices[0]
        if not choice.message.tool_calls:
            return AgentResponse(status="success", answer=choice.message.content, tool_traces=tool_traces)
        # Dispatch tools
        messages.append(choice.message.model_dump())
        for tc in choice.message.tool_calls:
            observation = await _dispatch_tool(ctx, vault_id, tc)
            tool_traces.append(ToolTrace(
                tool_call_id=tc.id,
                tool_name=tc.function.name,
                args=...,
                observation=observation,
            ))
            # CRITICAL: tool_call_id must be set (Pitfall 3)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": str(observation)})

    return AgentResponse(status="max_iterations_reached", tool_traces=tool_traces)
```

**Error handling / structlog pattern** (reconcile_vault.py lines 101-130):
```python
    except Exception as exc:  # noqa: BLE001
        log.error("react_loop_failed", error=str(exc), iteration=iteration)
        return AgentResponse(status="tool_error", error=str(exc), tool_traces=tool_traces)
```

---

### `server/app/agent/models.py` (model, transform)

**Analog:** No direct analog — Pydantic-only models. Use `server/app/models/base.py` for naming conventions. Verbatim from RESEARCH.md AI-SPEC §4b.1.

**Pattern** (RESEARCH.md lines 609-626):
```python
from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

class ToolTrace(BaseModel):
    tool_call_id: str
    tool_name: str
    args: dict[str, Any]
    observation: dict[str, Any]
    retried: bool = False
    skipped: bool = False
    skip_reason: str | None = None

class AgentResponse(BaseModel):
    status: Literal[
        "success", "success_with_warnings", "tool_error",
        "max_iterations_reached", "no_local_knowledge",
    ]
    answer: str | None = None
    tool_traces: list[ToolTrace] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
```

---

### `server/app/agent/tools/__init__.py` (utility — TOOL_REGISTRY + TOOL_SPECS)

**Analog:** `server/app/mcp/tools/__init__.py` (pattern reference) and `server/app/mcp/tools/brain.py` for tool registration style.

**Pattern** (brain.py lines 54-56 adapted):
```python
from __future__ import annotations
from collections.abc import Callable
from typing import Any
# TOOL_REGISTRY: dict mapping tool name -> async callable
# TOOL_SPECS: list of OpenAI/Anthropic tool dicts (name, description, input_schema)
TOOL_REGISTRY: dict[str, Callable[..., Any]] = {}
TOOL_SPECS: list[dict] = []
```

---

### `server/app/agent/tools/brain.py` (middleware, request-response)

**Analog:** `server/app/mcp/tools/brain.py` — exact structural mirror.

**Imports pattern** (brain.py lines 1-43):
```python
from __future__ import annotations
import uuid
from typing import Any
import structlog
from app.auth.context import OperationContext
from app.dependencies import session_with_rls
from app.services.pages import read_page, search_pages_fts, upsert_page
from app.services.vault_resolver import VaultNotFound, resolve_user_vault_id
```

**Tool wrapper pattern** (brain.py lines 62-116 — use as template for each of the 22 tool wrappers):
```python
async def brain_search_tool(
    ctx: OperationContext,
    vault_id: uuid.UUID,
    *,
    query: str,
    limit: int = 20,
) -> dict:
    """Agent-internal brain.search wrapper. Calls service directly — no MCP overhead."""
    if not query or not query.strip():
        return _err("validation_error", "query must be non-empty")
    async for session in session_with_rls(ctx):
        try:
            hits = await search_pages_fts(session, ctx, vault_id=vault_id, query=query, limit=limit)
            return {"results": [...], "total": len(hits)}
        except VaultNotFound as exc:
            return _err("not_found", str(exc))
    return _err("internal_error", "session loop exited without result")
```

**Error helper pattern** (brain.py lines 46-51):
```python
def _err(code: str, message: str, **details: Any) -> dict:
    """Structured error dict matching D-05 convention."""
    payload: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details:
        payload["error"]["details"] = details
    return payload
```

---

### `server/app/mcp/tools/graph.py` (modify — replace stub body)

**Analog:** `server/app/mcp/tools/brain.py` — real tool implementation pattern.

**Key rule (CONTEXT.md code_context):** Do NOT re-register the tool. Replace the stub body only. The `register()` function signature stays the same; the inner async function body changes from `return _stub()` to a real `session_with_rls(ctx)` call into `services/graph.py::traverse_graph()`.

**Real implementation pattern** (brain.py brain_search lines 165-216):
```python
def register(mcp: Any, ctx_factory: Callable[..., OperationContext]) -> None:
    @mcp.tool(name="brain.graph.traverse", description="...")
    async def brain_graph_traverse(
        start_slug: str,
        edge_type_filter: str | None = None,
        max_depth: int = 3,
    ) -> dict:
        ctx = ctx_factory()
        async for session in session_with_rls(ctx):
            try:
                vault_id = await resolve_user_vault_id(session, ctx.user_id)
                nodes = await traverse_graph(
                    session, ctx,
                    start_slug=start_slug,
                    vault_id=vault_id,
                    edge_type_filter=edge_type_filter,
                    max_depth=max_depth,
                )
                return {"nodes": [n.model_dump() for n in nodes], "start_slug": start_slug}
            except VaultNotFound as exc:
                return _err("not_found", str(exc))
        return _err("internal_error", "session loop exited without result")
```

---

### `server/app/routes/query.py` (route, request-response)

**Analog:** `server/app/routes/search.py` — exact structural mirror.

**Imports pattern** (search.py lines 1-17):
```python
from __future__ import annotations
import uuid
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.context import OperationContext
from app.auth.deps import require_user
from app.dependencies import get_db_session
from app.services.agent_service import persist_agent_invocation, run_agent_query
from app.services.vault_resolver import VaultNotFound, resolve_user_vault_id

router = APIRouter(prefix="/api/v1", tags=["query"])
```

**Request/response models pattern** (search.py lines 22-43):
```python
class QueryIn(BaseModel):
    query: str = Field(..., min_length=1, max_length=4096)
    session_id: uuid.UUID | None = None  # D-09: optional for multi-turn

class QueryResponse(BaseModel):
    status: str
    answer: str | None
    tool_traces: list
    warnings: list[str]
    message_id: uuid.UUID
    conversation_id: uuid.UUID
```

**Route handler pattern** (search.py lines 46-78):
```python
@router.post("/query", response_model=QueryResponse)
async def query_endpoint(
    payload: QueryIn,
    ctx: OperationContext = Depends(require_user),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> QueryResponse:
    try:
        vault_id = await resolve_user_vault_id(session, ctx.user_id)
    except VaultNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": str(exc)}},
        ) from None
    result = await run_agent_query(ctx, vault_id, payload.query, payload.session_id)
    return QueryResponse(...)
```

---

### `server/app/observability/agent_spans.py` (utility, event-driven)

**Analog:** `server/app/logging/redaction.py` — structlog processor pattern; OpenTelemetry is new but follows context-manager idiom.

**Imports pattern** (redaction.py lines 1-16 adapted):
```python
from __future__ import annotations
from contextlib import contextmanager
from typing import Any
import structlog
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

log = structlog.get_logger("smart_copilot.observability")
```

**Context manager span pattern** (new — no existing analog; follow OTel standard):
```python
@contextmanager
def agent_run_span(query: str, user_id: str):
    """Context manager for agent.run span. SMARTCOPILOT_TRACING_ENABLED guard."""
    if not _tracing_enabled():
        yield None
        return
    tracer = trace.get_tracer("smart_copilot.agent")
    with tracer.start_as_current_span("agent.run") as span:
        span.set_attribute("query", query[:200])
        span.set_attribute("user_id", user_id)
        yield span
```

---

### `server/app/tests/graph/test_wikilink_extractor.py` (test, CRUD)

**Analog:** `server/app/tests/vault/test_parser.py` — unit test pattern (no DB, no FastAPI).

**Imports + markers pattern** (test_parser.py lines 1-19):
```python
from __future__ import annotations
import pytest
from app.services.graph import extract_wikilinks_from_content, _FRONTMATTER_EDGE_KEYS

pytestmark = [pytest.mark.graph, pytest.mark.unit]
```

**Test function pattern** (test_parser.py lines 35-43):
```python
def test_simple_wikilink_extracted() -> None:
    """[[Target]] produces one link with edge_type='wikilink', confidence=1.0."""
    content = "See [[Target Page]] here."
    links = extract_wikilinks_from_content(content)
    assert len(links) == 1
    assert links[0]["target_text"] == "Target Page"
    assert links[0]["edge_type"] == "wikilink"
    assert links[0]["confidence"] == 1.0
    assert links[0]["anchor_text"] is None
    assert links[0]["fragment"] is None
```

---

### `server/app/tests/graph/test_graph_traversal.py` (test, CRUD)

**Analog:** `server/app/tests/vault/test_pages_service.py` — integration test with DB session.

**Imports + markers pattern** (test_pages_service.py lines 1-25):
```python
from __future__ import annotations
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.context import OperationContext
from app.services.graph import traverse_graph

pytestmark = [pytest.mark.graph, pytest.mark.integration]
```

**Async integration test pattern** (test_pages_service.py lines 40-56):
```python
@pytest.mark.asyncio
async def test_graph_traversal_follows_links(
    db_session: AsyncSession,
    seed_user_for_vault,
    seed_vault,
):
    """traverse_graph returns connected pages up to depth 3."""
    ctx = _ctx_for(seed_user_for_vault)
    # Seed pages + links in DB...
    nodes = await traverse_graph(db_session, ctx, start_slug="...", vault_id=seed_vault)
    assert len(nodes) > 0
```

---

### `server/app/tests/agent/test_conversation_persistence.py` (test, CRUD)

**Analog:** `server/app/tests/vault/test_wikilinks.py` — integration test using direct DB factory sessions.

**DB factory session pattern** (test_wikilinks.py lines 38-63):
```python
from __future__ import annotations
import uuid
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from app.auth.context import OperationContext
from app.services.agent_service import persist_agent_invocation

pytestmark = [pytest.mark.agent, pytest.mark.integration]

def _ctx_for(user_id: uuid.UUID, role: str = "user") -> OperationContext:
    return OperationContext(
        user_id=user_id, role=role, transport="rest",
        remote=True, client_name="test", request_id="test",
    )

@pytest.mark.asyncio
async def test_agent_invocation_creates_conversation(test_engine: AsyncEngine):
    """Every brain.query invocation creates or appends to a conversation (D-08)."""
    # Seed user, call persist_agent_invocation, assert DB rows
```

---

### `server/scripts/eval_agent.py` (utility, batch)

**Analog:** `server/app/scheduler/jobs/reconcile_vault.py` — async batch runner with structlog and `session_with_rls`.

**Entry point pattern** (scheduler/run.py lines 65-70):
```python
import asyncio, sys

async def _amain() -> int:
    # Load golden_queries.yaml with yaml.safe_load
    # For each query: run agent, compare results, compute Precision@K + MRR
    # Write eval_baseline.json
    return 0

def main() -> int:
    return asyncio.run(_amain())

if __name__ == "__main__":
    sys.exit(main())
```

**structlog pattern** (reconcile_vault.py lines 29-30):
```python
import structlog
log = structlog.get_logger("smart_copilot.eval_agent")
```

---

## Shared Patterns

### RLS Session Pattern
**Source:** `server/app/dependencies.py` (lines 106-141) — `session_with_rls(ctx)`
**Apply to:** `services/graph.py`, `services/agent_service.py`, `mcp/tools/graph.py` (modified), `agent/tools/*.py`
```python
async for session in session_with_rls(ctx):
    try:
        # DB work here — GUCs already set by session_with_rls
        ...
        await session.commit()
    except SomeException:
        ...
    # finally: session.close() handled by session_with_rls
```

### Structured Error Envelope
**Source:** `server/app/mcp/tools/brain.py` (lines 46-51)
**Apply to:** All MCP tool files, `routes/query.py`, `services/agent_service.py`
```python
def _err(code: str, message: str, **details: Any) -> dict:
    payload: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details:
        payload["error"]["details"] = details
    return payload
```

### OperationContext Pattern
**Source:** `server/app/auth/context.py` (lines 29-43)
**Apply to:** All service files, all MCP tool files, all agent tool files
```python
# Services take (session: AsyncSession, ctx: OperationContext, *, ...) as positional args
# ctx carries user_id, role, transport, remote, request_id
# Never import FastAPI in services — transport-agnostic by design
```

### Transport-Agnostic Services
**Source:** `server/app/services/pages.py` (docstring lines 1-21) — "no FastAPI imports"
**Apply to:** `services/graph.py`, `services/agent_service.py`
```
- No FastAPI imports in services/ — services take OperationContext + AsyncSession
- Routes are thin: validate → service → response model (search.py lines 46-78)
- MCP tools call services/ via session_with_rls(ctx) (brain.py lines 62-116)
```

### structlog Logging
**Source:** `server/app/mcp/tools/brain.py` (line 43), `server/app/scheduler/jobs/reconcile_vault.py` (line 29)
**Apply to:** `services/graph.py`, `agent/react_loop.py`, `routes/query.py`, `scripts/eval_agent.py`
```python
import structlog
log = structlog.get_logger("smart_copilot.<module_name>")
# Usage: log.info("event_name", key=value, ...)
# Usage: log.exception("event_name_failed", slug=slug) — inside except
```

### TimestampMixin + Base
**Source:** `server/app/models/base.py` (lines 1-36)
**Apply to:** All new model files (none in Phase 2b — all models modify existing files)
```python
from app.models.base import Base, TimestampMixin
class NewModel(Base, TimestampMixin):  # gets created_at + updated_at automatically
    __tablename__ = "new_table"
```

### `from __future__ import annotations`
**Source:** Every existing file in the codebase
**Apply to:** All new files — mandatory first line
```python
from __future__ import annotations
```

### Test Markers + pytest-asyncio
**Source:** `server/app/tests/vault/test_parser.py` (lines 19-20), `server/app/tests/vault/test_pages_service.py` (lines 25, 40)
**Apply to:** All new test files
```python
import pytest
pytestmark = [pytest.mark.<domain>, pytest.mark.<unit|integration>]

@pytest.mark.asyncio
async def test_something(db_session: AsyncSession, seed_user_for_vault, seed_vault):
    ...
```

### `_ctx_for` Test Helper
**Source:** `server/app/tests/vault/test_pages_service.py` (lines 28-37), `server/app/tests/vault/test_wikilinks.py` (lines 27-35)
**Apply to:** All new integration test files
```python
def _ctx_for(user_id: uuid.UUID, role: str = "user") -> OperationContext:
    return OperationContext(
        user_id=user_id, role=role, transport="rest",
        remote=True, client_name="test", request_id="test",
    )
```

---

## No Analog Found

Files with no close match in the codebase (planner should use RESEARCH.md patterns and AI-SPEC):

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `server/app/agent/prompts.py` | utility | — | No existing prompt constants in codebase — purely new content (`BRAIN_FIRST_SYSTEM_PROMPT` from AI-SPEC §4b.3) |
| `server/tests/fixtures/golden_queries.yaml` | config | — | No YAML fixtures exist in codebase yet — use RESEARCH.md lines 629-659 for schema |
| `server/tests/fixtures/sample_vault/*.md` | config | — | No fixture vault pages exist yet — follow RESEARCH.md D-13 (10-20 markdown pages) |
| `server/tests/fixtures/system_prompt.sha256` | config | — | New file type — SHA-256 digest of BRAIN_FIRST_SYSTEM_PROMPT constant |
| `server/tests/fixtures/expected_links.json` | config | — | New JSON snapshot — planner designs schema based on `Link` model fields |

---

## Metadata

**Analog search scope:** `server/app/services/`, `server/app/mcp/tools/`, `server/app/models/`, `server/app/routes/`, `server/app/tests/`, `server/alembic/versions/`, `server/app/scheduler/`, `server/app/logging/`, `server/app/auth/`
**Files scanned:** 27
**Pattern extraction date:** 2026-05-16
