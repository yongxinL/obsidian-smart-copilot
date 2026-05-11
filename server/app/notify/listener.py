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
                        await self._conn.remove_listener(
                            "index_events", self._on_notify
                        )
                        await self._conn.close()
                self._conn = None

    def _on_notify(self, connection, pid, channel, payload: str) -> None:  # noqa: ARG002
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
