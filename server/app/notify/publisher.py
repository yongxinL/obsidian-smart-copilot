"""Atomic publisher for index events: row insert + pg_notify in one txn (D-07)."""

from __future__ import annotations

import json
from datetime import UTC, datetime

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
    await session.flush()  # populates row.id

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
