"""Integration tests for REST search route.

Uses httpx.AsyncClient to test routes directly against the FastAPI app.
The test DB is provided by conftest.py via testcontainer PostgreSQL.
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio

from app.auth.tokens import issue_access_jwt
from app.models.user import User
from app.models.vault import Vault
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
async def test_search_returns_fts_envelope(db_session, app_client) -> None:
    """POST /api/v1/search returns the D-02 envelope: results, total, query, search_type."""
    user_id = uuid.uuid4()
    vault_id = uuid.uuid4()
    _, jwt = await _seed_user_with_vault(user_id, vault_id, db_session)

    # Create two pages with distinct compiled_truth
    for slug, content in [
        ("search-alpha", "---\ntitle: Alpha\n---\nAlpha content about python programming."),
        ("search-beta", "---\ntitle: Beta\n---\nBeta content about rust programming."),
        ("search-gamma", "---\ntitle: Gamma\n---\nGamma content about nothing."),
    ]:
        resp = await app_client.put(
            f"/api/v1/pages/{slug}",
            json={"content": content},
            headers={"Authorization": f"Bearer {jwt}"},
        )
        assert resp.status_code == 200, resp.json()

    # Search for python
    search_resp = await app_client.post(
        "/api/v1/search",
        json={"query": "python", "limit": 10, "namespace": "private"},
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert search_resp.status_code == 200, search_resp.json()
    body = search_resp.json()
    assert body["search_type"] == "fts_v1"
    assert body["query"] == "python"
    assert body["total"] >= 1
    assert len(body["results"]) >= 1
    assert all("slug" in r for r in body["results"])
    assert all("score" in r for r in body["results"])


@pytest.mark.integration
async def test_search_empty_query_returns_422(db_session, app_client) -> None:
    """Empty query string returns 422 with validation_error envelope."""
    user_id = uuid.uuid4()
    vault_id = uuid.uuid4()
    _, jwt = await _seed_user_with_vault(user_id, vault_id, db_session)

    resp = await app_client.post(
        "/api/v1/search",
        json={"query": "", "limit": 10},
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert resp.status_code == 422, resp.json()
    body = resp.json()
    assert body["error"]["code"] == "validation_error"


@pytest.mark.integration
async def test_search_filters_by_user_vault(db_session, app_client) -> None:
    """User A's search must NOT return User B's page (RLS isolation)."""
    user_a_id = uuid.uuid4()
    user_a_vault_id = uuid.uuid4()
    _, jwt_a = await _seed_user_with_vault(user_a_id, user_a_vault_id, db_session)

    user_b_id = uuid.uuid4()
    user_b_vault_id = uuid.uuid4()
    _, jwt_b = await _seed_user_with_vault(user_b_id, user_b_vault_id, db_session)

    # User A creates a private page
    await app_client.put(
        "/api/v1/pages/user-a-private",
        json={"content": "---\ntitle: User A Private\n---\nUser A only content."},
        headers={"Authorization": f"Bearer {jwt_a}"},
    )

    # User B creates their own page
    await app_client.put(
        "/api/v1/pages/user-b-private",
        json={"content": "---\ntitle: User B Private\n---\nUser B only content."},
        headers={"Authorization": f"Bearer {jwt_b}"},
    )

    # User A searches for "private" — should only see their own page
    search_resp = await app_client.post(
        "/api/v1/search",
        json={"query": "private", "limit": 10},
        headers={"Authorization": f"Bearer {jwt_a}"},
    )
    assert search_resp.status_code == 200
    body = search_resp.json()
    slugs = [r["slug"] for r in body["results"]]
    assert "user-a-private" in slugs
    assert "user-b-private" not in slugs