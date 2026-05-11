"""Integration tests for vault routes (capabilities + index events).

Uses httpx.AsyncClient to test routes directly against the FastAPI app.
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio

from app.auth.tokens import issue_access_jwt
from app.models.user import User
from app.models.vault import Vault
from app.services.capabilities import get_capabilities
from app.settings import settings


async def _seed_user_with_vault(
    user_id: uuid.UUID, vault_id: uuid.UUID, session,
) -> tuple[uuid.UUID, str]:
    """Seed a user + private vault, return (user_id, jwt)."""
    session.add(User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id}@test.local",
        password_hash="x",
        role="user",
        is_active=True,
    ))
    session.add(Vault(
        id=vault_id,
        owner_user_id=user_id,
        kind="private",
        path=f"/vaults/{user_id}",
    ))
    await session.commit()

    jwt = issue_access_jwt(
        user_id=user_id,
        role="user",
        signing_key=settings.jwt_signing_key,
        ttl_seconds=300,
    )
    return user_id, jwt


@pytest.mark.integration
async def test_capabilities_returns_phase_1d_payload(app_client) -> None:
    """GET /api/v1/capabilities returns the Phase 1d capability payload."""
    resp = await app_client.get("/api/v1/capabilities")
    assert resp.status_code == 200, resp.json()
    body = resp.json()
    assert body["transports"] == ["stdio", "http"]
    assert body["ingestion_limits"] == {}
    assert body["clipboard_available"] is False
    assert body["phase"] == "1d"


@pytest.mark.integration
async def test_capabilities_does_not_require_auth(app_client) -> None:
    """Capability discovery is public — no Authorization header required (REST-05)."""
    resp = await app_client.get("/api/v1/capabilities")
    assert resp.status_code == 200


@pytest.mark.integration
async def test_index_events_returns_user_filtered_events(db_session, app_client) -> None:
    """User A's /vault/index/events returns only A's events (RLS isolation)."""
    user_a_id = uuid.uuid4()
    user_a_vault_id = uuid.uuid4()
    _, jwt_a = await _seed_user_with_vault(user_a_id, user_a_vault_id, db_session)

    user_b_id = uuid.uuid4()
    user_b_vault_id = uuid.uuid4()
    _, jwt_b = await _seed_user_with_vault(user_b_id, user_b_vault_id, db_session)

    # Create pages to generate index events for both users
    await app_client.put(
        "/api/v1/pages/event-user-a",
        json={"content": "---\ntitle: Event A\n---\nContent A"},
        headers={"Authorization": f"Bearer {jwt_a}"},
    )
    await app_client.put(
        "/api/v1/pages/event-user-b",
        json={"content": "---\ntitle: Event B\n---\nContent B"},
        headers={"Authorization": f"Bearer {jwt_b}"},
    )

    # User A queries their events
    events_resp = await app_client.get(
        "/api/v1/vault/index/events",
        headers={"Authorization": f"Bearer {jwt_a}"},
    )
    assert events_resp.status_code == 200, events_resp.json()
    body = events_resp.json()
    assert "events" in body
    # All events returned should belong to user A
    for event in body["events"]:
        # page_slug should not contain "user-b" — user A should only see their own events
        # Note: if events are ordered desc by created_at, user-b events might not appear at all
        # We verify by checking the page slugs are from user A's vault
        assert "user-b" not in (event.get("page_slug") or "")


@pytest.mark.integration
async def test_index_events_invalid_limit_returns_422(db_session, app_client) -> None:
    """limit=999 returns 422 with validation_error."""
    user_id = uuid.uuid4()
    vault_id = uuid.uuid4()
    _, jwt = await _seed_user_with_vault(user_id, vault_id, db_session)

    resp = await app_client.get(
        "/api/v1/vault/index/events?limit=999",
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert resp.status_code == 422, resp.json()
    body = resp.json()
    assert body["error"]["code"] == "validation_error"