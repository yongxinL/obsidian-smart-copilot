"""Test publish_index_event writes IndexEvent + emits pg_notify in same txn."""

from __future__ import annotations

import asyncio
import json

import asyncpg
import pytest

from app.auth.context import system_operation_context
from app.notify.publisher import publish_index_event


@pytest.mark.integration
async def test_publish_emits_pg_notify(
    test_engine, postgres_container, db_session, patch_async_session_factory
) -> None:
    """publish_index_event() writes the row AND emits pg_notify in same txn."""
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
        await publish_index_event(
            db_session,
            ctx,
            event_type="created",
            page_slug="t-slug",
            details={"foo": "bar"},
        )
        await db_session.commit()

        # Wait for notify to arrive.
        payload_str = await asyncio.wait_for(received.get(), timeout=5.0)
        data = json.loads(payload_str)
        assert data["event_type"] == "created"
        assert data["page_slug"] == "t-slug"
        assert data["details"] == {"foo": "bar"}
    finally:
        await listener_conn.close()
