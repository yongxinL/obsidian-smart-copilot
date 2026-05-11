"""End-to-end WS event delivery: pg_notify -> listener -> socket."""

from __future__ import annotations

import asyncio
import uuid

import pytest
from sqlalchemy import text

from app.auth.context import OperationContext
from app.models.user import User
from app.models.vault import Vault
from app.notify.listener import IndexEventListener
from app.notify.publisher import publish_index_event


@pytest.mark.integration
async def test_pg_notify_event_reaches_subscriber(
    test_engine, postgres_container, db_session, patch_async_session_factory
) -> None:
    """Listener receives pg_notify and fans out to per-user subscriber queue."""
    sync_url = postgres_container.get_connection_url()
    raw_dsn = sync_url.replace("postgresql+psycopg2://", "postgresql://", 1)
    if raw_dsn.startswith("postgresql+asyncpg://"):
        raw_dsn = raw_dsn.replace("postgresql+asyncpg://", "postgresql://", 1)

    # Seed a real user so the IndexEvent insert won't FK-reject
    uid = uuid.uuid4()
    vid = uuid.uuid4()
    db_session.add(
        User(
            id=uid,
            username=f"user_{uid.hex[:8]}",
            email=f"{uid}@test.local",
            password_hash="x",
            role="user",
            is_active=True,
        )
    )
    db_session.add(
        Vault(
            id=vid,
            owner_user_id=uid,
            kind="private",
            path=f"/vaults/{uid}",
        )
    )
    await db_session.commit()

    listener = IndexEventListener(raw_dsn)
    await listener.start()
    try:
        # Wait for listener to establish the LISTEN
        await asyncio.sleep(0.5)

        ctx = OperationContext(
            user_id=uid,
            role="user",
            transport="system",
            remote=False,
            client_name="t",
            request_id="t",
        )
        # Subscribe FIRST — we only care about events received after subscription
        q = await listener.subscribe(uid)

        # Emit notify AFTER subscribing — must arrive in queue
        await publish_index_event(
            db_session,
            ctx,
            event_type="updated",
            page_slug="y",
            details={},
        )
        await db_session.commit()

        evt = await asyncio.wait_for(q.get(), timeout=5.0)
        assert evt["event_type"] == "updated"
        assert evt["page_slug"] == "y"
        await listener.unsubscribe(uid, q)
    finally:
        await listener.stop()


@pytest.mark.integration
async def test_unsubscribe_removes_subscriber() -> None:
    """Unsubscribe cleans up the subscriber registry (no leak)."""
    listener = IndexEventListener("")
    uid = uuid.uuid4()
    q = await listener.subscribe(uid)
    assert uid in listener._subscribers
    await listener.unsubscribe(uid, q)
    assert uid not in listener._subscribers


@pytest.mark.integration
async def test_raw_pg_notify_fanout(
    postgres_container, db_session, patch_async_session_factory
) -> None:
    """Listener fans out raw pg_notify to the correct user queue."""
    sync_url = postgres_container.get_connection_url()
    raw_dsn = sync_url.replace("postgresql+psycopg2://", "postgresql://", 1)
    if raw_dsn.startswith("postgresql+asyncpg://"):
        raw_dsn = raw_dsn.replace("postgresql+asyncpg://", "postgresql://", 1)

    uid = uuid.uuid4()
    db_session.add(
        User(
            id=uid,
            username=f"user_{uid.hex[:8]}",
            email=f"{uid}@test.local",
            password_hash="x",
            role="user",
            is_active=True,
        )
    )
    db_session.add(
        Vault(
            id=uid,
            owner_user_id=uid,
            kind="private",
            path=f"/vaults/{uid}",
        )
    )
    await db_session.commit()

    listener = IndexEventListener(raw_dsn)
    await listener.start()
    try:
        await asyncio.sleep(0.5)

        q = await listener.subscribe(uid)

        # Emit raw pg_notify
        payload = (
            '{"id":9,"user_id":"' + str(uid) + '","event_type":"re_indexed",'
            '"page_slug":"z","details":{},"created_at":"2026-05-11T00:00:00+00:00"}'
        )
        await db_session.execute(
            text("SELECT pg_notify('index_events', :p)"), {"p": payload}
        )
        await db_session.commit()

        evt = await asyncio.wait_for(q.get(), timeout=5.0)
        assert evt["event_type"] == "re_indexed"
        assert evt["page_slug"] == "z"
        await listener.unsubscribe(uid, q)
    finally:
        await listener.stop()
