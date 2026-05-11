---
phase: 01d
plan: 04
type: execute
wave: 4
depends_on:
  - "01d-03"
files_modified:
  - server/app/notify/__init__.py
  - server/app/notify/listener.py
  - server/app/notify/publisher.py
  - server/app/routes/ws.py
  - server/app/vault/watcher.py
  - server/app/main.py
  - server/app/tests/integration/test_ws_auth.py
  - server/app/tests/integration/test_ws_index_events.py
  - server/app/tests/integration/test_pg_notify_publisher.py
autonomous: true
requirements:
  - REST-03
  - REST-04

must_haves:
  truths:
    - "WebSocket /api/v1/ws accepts only the {type:'auth', data:{token:'<access_jwt>'}} first frame; closes socket on missing/invalid token (D-09)"
    - "Server sends {type:'auth_error', error:{code:'unauthorized', message:...}} before close on auth failure"
    - "Each FastAPI worker keeps a dedicated asyncpg listener connection on the 'index_events' channel started during lifespan (D-07)"
    - "Watchdog and service mutations call notify.publisher.publish_index_event which writes index_events row AND pg_notify('index_events', payload) in the same transaction (D-07)"
    - "Events filtered by user_id — private vault events only sent to the owning user's sockets (D-08)"
    - "Listener routes events to in-process subscribers via asyncio.Queue per socket"
    - "Closing a WebSocket cleanly removes the subscriber from the listener registry (no leak)"
    - "Token in query string is REJECTED — only first frame auth supported (D-09)"
  artifacts:
    - path: "server/app/notify/listener.py"
      provides: "IndexEventListener class — manages the asyncpg LISTEN connection and per-socket asyncio.Queue subscribers"
      contains: "class IndexEventListener"
    - path: "server/app/notify/publisher.py"
      provides: "publish_index_event(session, ctx, *, event_type, page_slug, details) — single helper that writes the IndexEvent row and pg_notify('index_events', payload)"
      contains: "pg_notify('index_events'"
    - path: "server/app/routes/ws.py"
      provides: "WebSocket /api/v1/ws endpoint with first-frame JWT auth + per-user filtered event stream"
      contains: "@router.websocket(\"/api/v1/ws\")"
    - path: "server/app/vault/watcher.py"
      provides: "Updated index_vault_file / soft_delete_vault_file to call publish_index_event (replaces inline IndexEvent inserts in services/pages.py for the watchdog path)"
    - path: "server/app/main.py"
      provides: "Lifespan starts/stops the IndexEventListener; ws_router mounted via app.include_router"
  key_links:
    - from: "server/app/notify/publisher.py"
      to: "server/app/notify/listener.py"
      via: "PostgreSQL channel 'index_events' — publisher writes pg_notify, every worker's listener consumes"
      pattern: "pg_notify\\('index_events'"
    - from: "server/app/routes/ws.py"
      to: "server/app/notify/listener.py"
      via: "WS handler subscribes to listener's per-user queue, forwards events to the socket"
      pattern: "listener.subscribe"
    - from: "server/app/main.py"
      to: "server/app/notify/listener.py"
      via: "Lifespan creates one listener per worker; stores on app.state; closes on shutdown"
      pattern: "IndexEventListener"
---

<objective>
Wire the real-time event surface for Phase 1d:

1. `server/app/notify/publisher.py` — single helper that writes `index_events` AND emits `pg_notify('index_events', json_payload)` in the same transaction. Replaces the inline `IndexEvent` inserts scattered across the watchdog code.
2. `server/app/notify/listener.py` — per-worker asyncpg LISTEN connection that fans out to per-socket asyncio.Queue subscribers, filtered by `user_id` (D-07/D-08).
3. `server/app/routes/ws.py` — WebSocket endpoint at `/api/v1/ws` with first-frame JWT auth (D-09); closes socket on invalid auth.
4. Wire the listener lifecycle into FastAPI's `lifespan` (start on startup, close on shutdown).
5. Update `server/app/vault/watcher.py` to call `publish_index_event` instead of inserting `IndexEvent` rows directly (so the pg_notify side-effect happens on every watchdog mutation).

Purpose: REST-03 deliverable — WebSocket streams indexing events. The listener architecture (one connection per worker) is the multi-worker-safe pattern documented in CLAUDE.md.

Output: 3 new modules in `server/app/notify/`, new `routes/ws.py`, watcher.py edited, main.py lifespan extended, 3 new integration test files.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/01d-mcp-rest-api-cli/01d-CONTEXT.md
@.planning/phases/01d-mcp-rest-api-cli/01d-PATTERNS.md
@.planning/phases/01d-mcp-rest-api-cli/01d-03-PLAN.md
@CLAUDE.md
@server/app/main.py
@server/app/auth/core.py
@server/app/vault/watcher.py
@server/app/services/pages.py
@server/app/models/index_event.py
@server/app/settings.py

<interfaces>
<!-- asyncpg LISTEN/NOTIFY pattern (CLAUDE.md): MUST use a raw asyncpg connection,
     NOT a SQLAlchemy session — SQLAlchemy 2.0 has no built-in support for the
     LISTEN command. -->
```python
import asyncpg
conn: asyncpg.Connection = await asyncpg.connect(dsn)

async def _on_notify(connection, pid, channel, payload: str) -> None:
    # payload is the string passed to pg_notify; parse JSON.
    ...

await conn.add_listener("index_events", _on_notify)
# ... await indefinitely; on shutdown: await conn.remove_listener('index_events', _on_notify); await conn.close()
```

<!-- pg_notify is a normal SQL function — emit it from any session: -->
```sql
SELECT pg_notify('index_events', :payload::text);
-- Payload limit: 8000 bytes pre-PG14; 8000 bytes still recommended; keep under 4 KB.
```

<!-- IndexEvent shape (server/app/models/index_event.py): -->
```python
class IndexEvent(Base):
    id: int                 # bigserial PK
    user_id: uuid.UUID | None
    event_type: str | None  # enum: created, updated, deleted, re_indexed, error
    page_slug: str | None
    details: dict           # jsonb
    created_at: datetime    # default now()
```

<!-- Existing places that already INSERT IndexEvent rows (must be migrated to publisher): -->
```python
# server/app/services/pages.py — upsert_page (lines 184-192) and soft_delete_page (lines 304-313)
# These continue to write the IndexEvent row but ALSO emit pg_notify in the same transaction.
# This plan changes the call site to publish_index_event() which encapsulates both side-effects.
```

<!-- Settings additions for this plan: -->
```python
# server/app/settings.py — append (or extend in same module):
notify_dsn_asyncpg: str = Field(default="")  # raw asyncpg DSN; default falls back to database_url
                                             # validation_alias="SMARTCOPILOT_NOTIFY_DSN"
ws_first_frame_timeout_seconds: float = Field(default=10.0)
```

<!-- WebSocket auth-failure frame shape (D-09): -->
```python
{"type": "auth_error", "error": {"code": "unauthorized", "message": "<reason>"}}
# Server then closes the socket with code 1008 (policy violation).
```

<!-- WebSocket event frame shape (REST-03): -->
```python
{"type": "index_event",
 "data": {"id": int, "event_type": "created"|"updated"|"deleted"|"re_indexed"|"error",
          "page_slug": str|None, "details": dict, "created_at": "<iso8601>"}}
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: notify package — publisher + listener with multi-worker LISTEN/NOTIFY</name>
  <files>server/app/notify/__init__.py, server/app/notify/publisher.py, server/app/notify/listener.py, server/app/settings.py, server/app/tests/integration/test_pg_notify_publisher.py</files>
  <read_first>
    - server/app/services/pages.py lines 184-192 (existing IndexEvent insert in upsert_page)
    - server/app/services/pages.py lines 304-313 (existing IndexEvent insert in soft_delete_page)
    - server/app/models/index_event.py (column types)
    - server/app/settings.py (existing fields — append, do not rewrite)
    - CLAUDE.md (LISTEN/NOTIFY via raw asyncpg, NOT SQLAlchemy)
  </read_first>
  <behavior>
    - `publish_index_event(session, ctx, *, event_type, page_slug, details)` writes one IndexEvent row AND issues `SELECT pg_notify('index_events', :payload)` inside the same SQLAlchemy transaction. Payload JSON: `{"id": <id>, "user_id": "<uuid>", "event_type": "<enum>", "page_slug": "<slug>", "details": {...}, "created_at": "<iso8601>"}`.
    - Payload size capped at 4000 bytes; if larger, `details` is truncated to `{"truncated": true, "id": <id>}` so the listener can fetch full row from the table.
    - `IndexEventListener.start(dsn)` opens an asyncpg connection, registers a listener on the `index_events` channel, loops forever consuming notifications.
    - Each notification is parsed (JSON) and dispatched to all `asyncio.Queue` instances registered under that `user_id`.
    - `subscribe(user_id) -> asyncio.Queue` returns a fresh queue and stores it in a registry keyed by user_id.
    - `unsubscribe(user_id, queue)` removes the queue and prevents leak.
    - Listener handles asyncpg connection drops by reconnecting with exponential backoff (max 30s).
  </behavior>
  <action>
First, EXTEND `server/app/settings.py` by appending these fields inside the `Settings` class (DO NOT rewrite the file — use Edit to add lines after the last existing field):

```python
    # --- Phase 1d: WebSocket + LISTEN/NOTIFY ---
    notify_dsn_asyncpg: str = Field(
        default="",
        validation_alias="SMARTCOPILOT_NOTIFY_DSN",
    )
    ws_first_frame_timeout_seconds: float = Field(default=10.0)
```

Add a derived helper at module bottom (after `settings = Settings()`):

```python
def get_notify_dsn() -> str:
    """Return raw asyncpg DSN for LISTEN/NOTIFY connection.

    Prefers SMARTCOPILOT_NOTIFY_DSN if set; otherwise derives from settings.database_url
    by stripping the '+asyncpg' driver suffix (asyncpg.connect takes a bare DSN).
    """
    if settings.notify_dsn_asyncpg:
        return settings.notify_dsn_asyncpg
    url = settings.database_url
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)
```

Create `server/app/notify/__init__.py`:

```python
"""LISTEN/NOTIFY plumbing for real-time vault events (D-07/D-08)."""
from app.notify.listener import IndexEventListener
from app.notify.publisher import publish_index_event

__all__ = ["IndexEventListener", "publish_index_event"]
```

Create `server/app/notify/publisher.py`:

```python
"""Atomic publisher for index events: row insert + pg_notify in one txn (D-07)."""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import OperationContext
from app.models.index_event import IndexEvent

log = structlog.get_logger("smart_copilot.notify")

_MAX_PAYLOAD_BYTES = 4000


async def publish_index_event(
    session: AsyncSession,
    ctx: OperationContext,
    *,
    event_type: str,
    page_slug: str | None,
    details: dict | None = None,
) -> IndexEvent:
    """Write one IndexEvent row + emit pg_notify('index_events', payload).

    Both operations are in the SAME SQLAlchemy transaction; the caller must
    `await session.commit()` for the notification to be visible to listeners
    (PostgreSQL flushes pg_notify only on commit).
    """
    row = IndexEvent(
        user_id=ctx.user_id,
        event_type=event_type,
        page_slug=page_slug,
        details=details or {},
    )
    session.add(row)
    await session.flush()                                   # populates row.id

    payload = {
        "id": row.id,
        "user_id": str(ctx.user_id),
        "event_type": event_type,
        "page_slug": page_slug,
        "details": details or {},
        "created_at": (row.created_at or datetime.now(UTC)).isoformat(),
    }
    encoded = json.dumps(payload, default=str)
    if len(encoded.encode("utf-8")) > _MAX_PAYLOAD_BYTES:
        # Truncate details; listener will SELECT the full row by id if needed.
        payload["details"] = {"truncated": True, "id": row.id}
        encoded = json.dumps(payload, default=str)

    await session.execute(
        text("SELECT pg_notify('index_events', :p)"),
        {"p": encoded},
    )
    log.debug("index_event_published", id=row.id, event_type=event_type, slug=page_slug)
    return row
```

Create `server/app/notify/listener.py`:

```python
"""Per-worker asyncpg LISTEN connection + per-user subscriber registry (D-07/D-08).

CLAUDE.md mandates raw asyncpg for LISTEN/NOTIFY — SQLAlchemy 2.0 has no built-in
support. The listener owns its own connection (NOT borrowed from the pool).
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import uuid

import asyncpg
import structlog

log = structlog.get_logger("smart_copilot.notify.listener")

_MAX_QUEUE_SIZE = 1000
_BACKOFF_INITIAL_S = 1.0
_BACKOFF_MAX_S = 30.0


class IndexEventListener:
    """One instance per FastAPI worker; subscribers register by user_id.

    Lifecycle (called from app.main lifespan):
        listener = IndexEventListener(dsn)
        await listener.start()
        ...
        await listener.stop()
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._conn: asyncpg.Connection | None = None
        self._task: asyncio.Task | None = None
        self._subscribers: dict[uuid.UUID, set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()
        self._stop_evt = asyncio.Event()

    async def start(self) -> None:
        self._stop_evt.clear()
        self._task = asyncio.create_task(self._run(), name="index-event-listener")

    async def stop(self) -> None:
        self._stop_evt.set()
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        if self._conn is not None and not self._conn.is_closed():
            await self._conn.close()

    async def subscribe(self, user_id: uuid.UUID) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=_MAX_QUEUE_SIZE)
        async with self._lock:
            self._subscribers.setdefault(user_id, set()).add(q)
        return q

    async def unsubscribe(self, user_id: uuid.UUID, queue: asyncio.Queue) -> None:
        async with self._lock:
            qs = self._subscribers.get(user_id)
            if qs is not None:
                qs.discard(queue)
                if not qs:
                    self._subscribers.pop(user_id, None)

    async def _run(self) -> None:
        backoff = _BACKOFF_INITIAL_S
        while not self._stop_evt.is_set():
            try:
                self._conn = await asyncpg.connect(self._dsn)
                await self._conn.add_listener("index_events", self._on_notify)
                log.info("index_event_listener_connected")
                backoff = _BACKOFF_INITIAL_S
                # Block until shutdown
                await self._stop_evt.wait()
            except (OSError, asyncpg.PostgresError) as exc:
                log.warning("index_event_listener_disconnected", error=str(exc))
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _BACKOFF_MAX_S)
            finally:
                if self._conn is not None and not self._conn.is_closed():
                    with contextlib.suppress(Exception):
                        await self._conn.remove_listener("index_events", self._on_notify)
                        await self._conn.close()
                self._conn = None

    def _on_notify(self, connection, pid, channel, payload: str) -> None:    # noqa: ARG002
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            log.warning("index_event_notify_parse_error", error=str(exc))
            return
        try:
            uid = uuid.UUID(data.get("user_id", ""))
        except (TypeError, ValueError):
            return
        # Schedule the dispatch on the current event loop.
        loop = asyncio.get_running_loop()
        loop.create_task(self._dispatch(uid, data))

    async def _dispatch(self, user_id: uuid.UUID, data: dict) -> None:
        async with self._lock:
            queues = list(self._subscribers.get(user_id, set()))
        for q in queues:
            try:
                q.put_nowait(data)
            except asyncio.QueueFull:
                log.warning("index_event_subscriber_queue_full", user_id=str(user_id))
```

Create `server/app/tests/integration/test_pg_notify_publisher.py`:

```python
"""Test publish_index_event writes IndexEvent + emits pg_notify in same txn."""
from __future__ import annotations

import asyncio
import json
import uuid

import asyncpg
import pytest

from app.auth.context import system_operation_context
from app.notify.publisher import publish_index_event
from app.db_session import session_with_rls


@pytest.mark.integration
async def test_publish_emits_pg_notify(test_engine, postgres_container) -> None:
    # Open a raw asyncpg listener connection to the same test DB.
    sync_url = postgres_container.get_connection_url()
    raw_dsn = sync_url.replace("postgresql+psycopg2://", "postgresql://", 1)
    if raw_dsn.startswith("postgresql+asyncpg://"):
        raw_dsn = raw_dsn.replace("postgresql+asyncpg://", "postgresql://", 1)

    received: asyncio.Queue = asyncio.Queue()

    def _cb(_conn, _pid, _ch, payload: str) -> None:
        received.put_nowait(payload)

    listener_conn = await asyncpg.connect(raw_dsn)
    await listener_conn.add_listener("index_events", _cb)

    try:
        ctx = system_operation_context(request_id="t", client_name="t")
        async for session in session_with_rls(ctx):
            await publish_index_event(
                session, ctx,
                event_type="created", page_slug="t-slug",
                details={"foo": "bar"},
            )
            await session.commit()
        # Wait for notify to arrive.
        payload_str = await asyncio.wait_for(received.get(), timeout=5.0)
        data = json.loads(payload_str)
        assert data["event_type"] == "created"
        assert data["page_slug"] == "t-slug"
        assert data["details"] == {"foo": "bar"}
    finally:
        await listener_conn.close()
```
  </action>
  <verify>
    <automated>cd server && SMARTCOPILOT_FERNET_KEY=T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU= JWT_SIGNING_KEY=test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa pytest -x app/tests/integration/test_pg_notify_publisher.py -v</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "pg_notify('index_events'" server/app/notify/publisher.py` >= 1
    - `grep -c "asyncpg.connect" server/app/notify/listener.py` >= 1
    - `grep -c "add_listener" server/app/notify/listener.py` >= 1
    - `grep -c "remove_listener" server/app/notify/listener.py` >= 1
    - `grep -c "notify_dsn_asyncpg" server/app/settings.py` >= 1
    - `grep -c "ws_first_frame_timeout_seconds" server/app/settings.py` >= 1
    - `grep -c "def get_notify_dsn" server/app/settings.py` == 1
    - `cd server && ruff check app/notify/ app/settings.py` exits 0.
    - The pg_notify integration test passes.
  </acceptance_criteria>
  <done>publisher + listener modules ship; pg_notify side-effect proven by integration test.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: WebSocket route /api/v1/ws + main.py lifespan wiring</name>
  <files>server/app/routes/ws.py, server/app/main.py, server/app/tests/integration/test_ws_auth.py, server/app/tests/integration/test_ws_index_events.py</files>
  <read_first>
    - server/app/main.py (lifespan + create_app — extend, don't rewrite)
    - server/app/auth/core.py (validate_jwt signature)
    - server/app/auth/context.py (OperationContext fields)
    - server/app/notify/listener.py (subscribe / unsubscribe API just added)
    - .planning/phases/01d-mcp-rest-api-cli/01d-CONTEXT.md (D-09 first-frame auth)
    - .planning/phases/01d-mcp-rest-api-cli/01d-PATTERNS.md (lines 363-401 for the WS pattern)
  </read_first>
  <behavior>
    - WebSocket connect to `/api/v1/ws`: server `await ws.accept()`, then `await ws.receive_json()` with `asyncio.wait_for(timeout=ws_first_frame_timeout_seconds)`.
    - Frame must equal `{"type": "auth", "data": {"token": "<access_jwt>"}}`. Anything else → send auth_error frame, close with code 1008.
    - Token validated via `validate_jwt`. On error: send auth_error frame, close.
    - On success: subscribe to listener, build OperationContext (transport="rest", remote=True), then loop forwarding events from queue to socket.
    - Token in query string (e.g. `/api/v1/ws?token=xxx`): IGNORED — only first frame is read. Test asserts that connecting with `?token=valid-jwt` and sending NO frame still times out.
    - On WebSocketDisconnect or shutdown: unsubscribe and close.
  </behavior>
  <action>
Create `server/app/routes/ws.py`:

```python
"""WebSocket /api/v1/ws — first-frame JWT auth + per-user filtered events (REST-03).

D-07: events arrive via PostgreSQL LISTEN/NOTIFY; this handler subscribes to
the per-user queue exposed by app.state.index_event_listener.
D-08: events are filtered by user_id; a socket only sees its owner's events.
D-09: auth via first frame {"type":"auth","data":{"token":"<jwt>"}}; token in
query string is IGNORED.
"""
from __future__ import annotations

import asyncio
import contextlib

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.auth.context import OperationContext
from app.auth.core import validate_jwt
from app.settings import settings

log = structlog.get_logger("smart_copilot.ws")

router = APIRouter()


def _auth_error(code: str, message: str) -> dict:
    return {"type": "auth_error", "error": {"code": code, "message": message}}


@router.websocket("/api/v1/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    listener = ws.app.state.index_event_listener
    queue = None
    user_id = None
    try:
        try:
            frame = await asyncio.wait_for(
                ws.receive_json(),
                timeout=settings.ws_first_frame_timeout_seconds,
            )
        except (asyncio.TimeoutError, ValueError):
            await ws.send_json(_auth_error("unauthorized", "first frame missing or invalid"))
            await ws.close(code=1008)
            return

        if not isinstance(frame, dict) or frame.get("type") != "auth":
            await ws.send_json(_auth_error("unauthorized", "first frame must be auth"))
            await ws.close(code=1008)
            return

        token = ((frame.get("data") or {}).get("token")) if isinstance(frame.get("data"), dict) else None
        result = validate_jwt(token)
        if result.error is not None or result.user_id is None:
            await ws.send_json(_auth_error("unauthorized", result.error or "invalid token"))
            await ws.close(code=1008)
            return

        user_id = result.user_id
        # Build OperationContext for downstream usage (audit/log only — WS path doesn't touch DB here).
        ctx = OperationContext(
            user_id=result.user_id, role=result.role or "user",
            transport="rest", remote=True,
            client_name="ws", request_id="ws",
            session_id=result.session_id,
        )
        log.info("ws_authenticated", user_id=str(ctx.user_id))

        await ws.send_json({"type": "auth_ok", "data": {"user_id": str(ctx.user_id)}})

        queue = await listener.subscribe(user_id)

        # Pump events until the client disconnects.
        while True:
            event = await queue.get()
            if ws.client_state != WebSocketState.CONNECTED:
                break
            await ws.send_json({"type": "index_event", "data": event})
    except WebSocketDisconnect:
        pass
    finally:
        if queue is not None and user_id is not None:
            with contextlib.suppress(Exception):
                await listener.unsubscribe(user_id, queue)
```

Edit `server/app/main.py` (use Edit tool — preserve existing logic):

1. Add imports near the top:
```python
from app.notify.listener import IndexEventListener
from app.routes.ws import router as ws_router
from app.settings import get_notify_dsn
```

2. Replace the existing `lifespan` body to start/stop the listener:
```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    _fail_startup_if_missing_secrets()
    listener = IndexEventListener(get_notify_dsn())
    app.state.index_event_listener = listener
    await listener.start()
    try:
        yield
    finally:
        await listener.stop()
        await engine.dispose()
```

3. Inside `create_app()`, AFTER existing `app.include_router(...)` calls (the ones added in Plan 03 too), add:
```python
    app.include_router(ws_router)
```

Create `server/app/tests/integration/test_ws_auth.py`:

```python
"""WebSocket auth tests (D-09)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.integration
def test_ws_close_when_first_frame_missing(monkeypatch) -> None:
    # Stub the listener to a minimal shim — auth happens before subscribe.
    class _Stub:
        async def start(self): ...
        async def stop(self): ...
        async def subscribe(self, _): return None
        async def unsubscribe(self, _u, _q): ...
    app.state.index_event_listener = _Stub()
    client = TestClient(app)
    with client.websocket_connect("/api/v1/ws") as ws:
        # Don't send any frame — server must time out and close with auth_error.
        msg = ws.receive_json()
        assert msg["type"] == "auth_error"
        assert msg["error"]["code"] == "unauthorized"


@pytest.mark.integration
def test_ws_close_when_invalid_token(monkeypatch) -> None:
    class _Stub:
        async def start(self): ...
        async def stop(self): ...
        async def subscribe(self, _): return None
        async def unsubscribe(self, _u, _q): ...
    app.state.index_event_listener = _Stub()
    client = TestClient(app)
    with client.websocket_connect("/api/v1/ws") as ws:
        ws.send_json({"type": "auth", "data": {"token": "not-a-real-jwt"}})
        msg = ws.receive_json()
        assert msg["type"] == "auth_error"
        assert msg["error"]["code"] == "unauthorized"


@pytest.mark.integration
def test_ws_token_in_query_string_is_ignored(seeded_user_jwt) -> None:
    """D-09: query-string token must be ignored; only first-frame auth supported."""
    class _Stub:
        async def start(self): ...
        async def stop(self): ...
        async def subscribe(self, _): return None
        async def unsubscribe(self, _u, _q): ...
    app.state.index_event_listener = _Stub()
    client = TestClient(app)
    with client.websocket_connect(f"/api/v1/ws?token={seeded_user_jwt}") as ws:
        # Send a NON-auth first frame; server must reject because we're not honouring the query token.
        ws.send_json({"type": "ping"})
        msg = ws.receive_json()
        assert msg["type"] == "auth_error"
```

Create `server/app/tests/integration/test_ws_index_events.py`:

```python
"""End-to-end WS event delivery: pg_notify → listener → socket."""
from __future__ import annotations

import asyncio
import uuid

import pytest

from app.auth.context import OperationContext
from app.notify.listener import IndexEventListener
from app.notify.publisher import publish_index_event
from app.db_session import session_with_rls


@pytest.mark.integration
async def test_pg_notify_event_reaches_subscriber(test_engine, postgres_container) -> None:
    sync_url = postgres_container.get_connection_url()
    raw_dsn = sync_url.replace("postgresql+psycopg2://", "postgresql://", 1)
    if raw_dsn.startswith("postgresql+asyncpg://"):
        raw_dsn = raw_dsn.replace("postgresql+asyncpg://", "postgresql://", 1)

    listener = IndexEventListener(raw_dsn)
    await listener.start()
    try:
        # Wait for listener to actually establish the LISTEN — small grace period.
        await asyncio.sleep(0.5)

        uid = uuid.uuid4()
        # Seed a user row so RLS doesn't block the IndexEvent insert.
        # (test fixture for seeded user could be reused; keep self-contained for clarity.)

        ctx = OperationContext(
            user_id=uid, role="user", transport="system", remote=False,
            client_name="t", request_id="t",
        )
        # NOTE: this test exercises the listener path; ctx needn't be a real DB user
        # because the listener only reads pg_notify payloads — no FK enforcement on
        # the listener side. The publisher INSERT will fail FK, so we instead emit a
        # raw pg_notify directly:
        from sqlalchemy import text
        async for session in session_with_rls(ctx):
            await session.execute(
                text("SELECT pg_notify('index_events', :p)"),
                {"p": '{"id":1,"user_id":"' + str(uid) + '","event_type":"created",'
                       '"page_slug":"x","details":{},"created_at":"2026-05-09T00:00:00+00:00"}'},
            )
            await session.commit()

        q = await listener.subscribe(uid)
        # We may not capture the first emit (subscribed AFTER), so emit again:
        async for session in session_with_rls(ctx):
            await session.execute(
                text("SELECT pg_notify('index_events', :p)"),
                {"p": '{"id":2,"user_id":"' + str(uid) + '","event_type":"updated",'
                       '"page_slug":"y","details":{},"created_at":"2026-05-09T00:00:01+00:00"}'},
            )
            await session.commit()
        evt = await asyncio.wait_for(q.get(), timeout=5.0)
        assert evt["event_type"] == "updated"
        assert evt["page_slug"] == "y"
        await listener.unsubscribe(uid, q)
    finally:
        await listener.stop()


@pytest.mark.integration
async def test_unsubscribe_removes_subscriber() -> None:
    listener = IndexEventListener("")
    uid = uuid.uuid4()
    q = await listener.subscribe(uid)
    assert uid in listener._subscribers
    await listener.unsubscribe(uid, q)
    assert uid not in listener._subscribers
```

A `seeded_user_jwt` fixture must be added to `server/app/tests/integration/__init__.py` or a conftest — reuse if Plan 03 already created one for `test_pages_routes.py`.
  </action>
  <verify>
    <automated>cd server && SMARTCOPILOT_FERNET_KEY=T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU= JWT_SIGNING_KEY=test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa pytest -x app/tests/integration/test_ws_auth.py app/tests/integration/test_ws_index_events.py -v</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "@router.websocket" server/app/routes/ws.py` >= 1
    - `grep -c "/api/v1/ws" server/app/routes/ws.py` >= 1
    - `grep -c "first frame must be auth\|first frame missing or invalid" server/app/routes/ws.py` >= 1
    - `grep -c "code=1008" server/app/routes/ws.py` >= 1
    - `grep -c "IndexEventListener" server/app/main.py` >= 1
    - `grep -c "app.state.index_event_listener" server/app/main.py` >= 1
    - `grep -c "app.include_router(ws_router)" server/app/main.py` == 1
    - All 4 tests in test_ws_auth.py + test_ws_index_events.py pass.
    - `cd server && ruff check app/routes/ws.py app/main.py` exits 0.
  </acceptance_criteria>
  <done>WebSocket /api/v1/ws live with first-frame JWT auth; listener lifecycle managed by FastAPI lifespan.</done>
</task>

<task type="auto">
  <name>Task 3: Migrate watchdog + service IndexEvent inserts to publish_index_event</name>
  <files>server/app/vault/watcher.py, server/app/services/pages.py</files>
  <read_first>
    - server/app/services/pages.py (current direct IndexEvent inserts at upsert_page lines 184-192 + soft_delete_page lines 304-313)
    - server/app/vault/watcher.py (calls upsert_page / soft_delete_page; both writes happen inside services already, so no changes here unless watcher writes IndexEvent directly — confirm via grep)
    - server/app/notify/publisher.py (just added)
  </read_first>
  <behavior>
    - In `services/pages.py` `upsert_page`, the existing `session.add(IndexEvent(...))` block is replaced by `await publish_index_event(session, ctx, event_type=event_type, page_slug=slug, details={"vault_id": str(vault_id), "version": version_num})`.
    - In `services/pages.py` `soft_delete_page`, the existing `session.add(IndexEvent(...))` block is replaced by `await publish_index_event(session, ctx, event_type="deleted", page_slug=page_slug, details={"page_id": str(page_id), "reason": reason})`.
    - All Phase 1c tests for upsert_page / soft_delete_page still pass (existing test assertions on IndexEvent rows must continue to hold — IndexEvent is still inserted via publish_index_event).
    - Watchdog calls upsert_page → side-effect is now both row + pg_notify. Existing watcher tests stay green.
  </behavior>
  <action>
Edit `server/app/services/pages.py` using the Edit tool (do NOT rewrite — preserve all other logic).

1. Add this import at the top alongside existing imports:
```python
from app.notify.publisher import publish_index_event
```

2. In `upsert_page`, replace the explicit IndexEvent insert block (currently lines 184-192) — `session.add(IndexEvent(...))` followed by `await session.flush()` — with:
```python
    await publish_index_event(
        session, ctx,
        event_type=event_type,
        page_slug=slug,
        details={"vault_id": str(vault_id), "version": version_num},
    )
```

3. In `soft_delete_page`, replace the explicit IndexEvent insert block (currently lines 304-313) — `session.add(IndexEvent(...))` followed by `await session.flush()` — with:
```python
    await publish_index_event(
        session, ctx,
        event_type="deleted",
        page_slug=page_slug,
        details={"page_id": str(page_id), "reason": reason},
    )
```

4. Remove the now-unused `from app.models.index_event import IndexEvent` import IF and only IF no other reference remains in the file (verify with `grep -c IndexEvent server/app/services/pages.py` — if the count is exactly equal to the number of references in the lines being deleted, remove the import; else keep it).

`server/app/vault/watcher.py` does NOT directly insert IndexEvent rows (it calls `upsert_page` / `soft_delete_page` which now route through the publisher). Verify with `grep -c "session.add(IndexEvent" server/app/vault/watcher.py` — must be 0. If non-zero, identify the call site and replace with `publish_index_event` analogously.

Run all Phase 1c vault tests to confirm no regressions:
```bash
cd server && pytest -x app/tests/vault/ -v
```
  </action>
  <verify>
    <automated>cd server && SMARTCOPILOT_FERNET_KEY=T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU= JWT_SIGNING_KEY=test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa pytest -x app/tests/vault/ app/tests/integration/test_pg_notify_publisher.py -v</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "publish_index_event" server/app/services/pages.py` >= 2 (upsert_page + soft_delete_page)
    - `grep -c "session.add(IndexEvent" server/app/services/pages.py` == 0
    - `grep -c "session.add(IndexEvent" server/app/vault/watcher.py` == 0
    - All Phase 1c vault tests still pass (no regression).
    - The pg_notify publisher integration test still passes.
  </acceptance_criteria>
  <done>Single source of truth for IndexEvent emission: every mutation goes through publish_index_event; pg_notify is automatic.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| WebSocket client → FastAPI WS handler | Untrusted bytes; first-frame auth only — no token in query string |
| Listener thread → in-process subscribers | Each subscriber sees only its own user_id events |
| Watchdog process → DB → other workers | pg_notify is the cross-process signaling mechanism (single PG instance) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-01d04-01 | Spoofing | WS auth via query-string token | mitigate | Server explicitly ignores query string; `test_ws_token_in_query_string_is_ignored` enforces. |
| T-01d04-02 | Spoofing | replayed/expired JWT on WS | mitigate | `validate_jwt` checks expiry; expired tokens fail validation and trigger close(1008). |
| T-01d04-03 | Information Disclosure | cross-user event leakage | mitigate | Listener dispatch keys on `user_id` from notify payload; subscribers indexed by user_id. Test `test_pg_notify_event_reaches_subscriber` proves filtering. |
| T-01d04-04 | DoS | one socket starves others | mitigate | Per-socket bounded `asyncio.Queue(maxsize=1000)`; `put_nowait` raises QueueFull; listener logs and drops to avoid back-pressure on the LISTEN connection. |
| T-01d04-05 | DoS | unbounded subscribers | accept | Phase 1d: 3-10 user homelab; max ~30 concurrent sockets. Phase 6 adds rate-limit middleware. |
| T-01d04-06 | Tampering | malformed pg_notify payload | mitigate | Listener `_on_notify` wraps `json.loads` in try/except; bad payloads logged and dropped. |
| T-01d04-07 | Information Disclosure | pg_notify payload >4KB leaking via PG truncation | mitigate | Publisher truncates `details` to `{"truncated": true, "id": <id>}` when payload exceeds 4000 bytes; listener can fetch full row via SELECT. |
| T-01d04-08 | Repudiation | events not durable | accept | IndexEvent row is the durable record; pg_notify is the live broadcast. Receiver-side reconciliation via GET /api/v1/vault/index/events?since=... covers missed events on reconnect. |
| T-01d04-09 | DoS | listener disconnect without recovery | mitigate | `_run` reconnects with exponential backoff up to 30s; logged at WARN level. |
| T-01d04-10 | Information Disclosure | publisher emits before commit | mitigate | PostgreSQL guarantees pg_notify is delivered ONLY after the emitting transaction commits. The publisher's `await session.flush()` populates `row.id`; the COMMIT happens at the caller's `await session.commit()` boundary, which is also when notify becomes visible. Listener never sees a phantom event. |
</threat_model>

<verification>
After all 3 tasks:
1. `cd server && pytest -x app/tests/integration/test_pg_notify_publisher.py app/tests/integration/test_ws_auth.py app/tests/integration/test_ws_index_events.py app/tests/vault/ -v` — all pass.
2. `cd server && ruff check app/notify/ app/routes/ws.py app/main.py app/services/pages.py app/settings.py` exits 0.
3. End-to-end smoke (manual; not a test): start app + watchdog, write a vault file, observe corresponding `index_event` frame on a connected WebSocket. Defer formal smoke to Plan 06 acceptance test.
</verification>

<success_criteria>
- `server/app/notify/publisher.py` and `listener.py` ship; pg_notify integration test green.
- WebSocket `/api/v1/ws` handles first-frame JWT auth; closes socket on missing/invalid auth.
- Listener lifecycle wired into FastAPI's lifespan; reconnects on connection loss.
- Watchdog mutations (via service layer) emit pg_notify automatically; WebSocket subscribers receive events filtered by user_id.
- REST-03 satisfied; REST-04 envelope used for auth_error frames.
</success_criteria>

<output>
After completion, create `.planning/phases/01d-mcp-rest-api-cli/01d-04-SUMMARY.md` listing notify-package modules, WS test count, any deviations.
</output>
