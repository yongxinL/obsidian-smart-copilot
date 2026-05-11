"""REST routes for pages (D-10) — REST-01 parity with MCP brain.* tools.

Uses httpx.AsyncClient to test routes directly against the FastAPI app.
The test DB is provided by conftest.py via testcontainer PostgreSQL.
"""

from __future__ import annotations

import uuid

import pytest

from app.auth.tokens import issue_access_jwt
from app.models.user import User
from app.models.vault import Vault
from app.settings import settings

# The app_client fixture is injected by conftest.py via the
# `pytest_plugins = ["app.tests.conftest"]` mechanism.
# We access it through the test function parameters.


async def _seed_user_with_vault(
    user_id: uuid.UUID,
    vault_id: uuid.UUID,
    session,
) -> tuple[uuid.UUID, str]:
    """Seed a user + private vault, return (user_id, jwt)."""
    session.add(
        User(
            id=user_id,
            username=f"user_{user_id.hex[:8]}",
            email=f"{user_id}@test.local",
            password_hash="x",
            role="user",
            is_active=True,
        )
    )
    session.add(
        Vault(
            id=vault_id,
            owner_user_id=user_id,
            kind="private",
            path=f"/vaults/{user_id}",
        )
    )
    await session.commit()

    jwt = issue_access_jwt(
        user_id=user_id,
        role="user",
        signing_key=settings.jwt_signing_key,
        ttl_seconds=300,
    )
    return user_id, jwt


@pytest.mark.integration
async def test_put_page_creates_and_get_returns_it(db_session, app_client) -> None:
    """Happy-path round-trip: PUT creates a page, GET retrieves it."""
    user_id = uuid.uuid4()
    vault_id = uuid.uuid4()
    _, jwt = await _seed_user_with_vault(user_id, vault_id, db_session)

    slug = f"test-page-{uuid.uuid4().hex[:8]}"
    content = "---\ntitle: Test Page\n---\nThis is test content."

    # PUT
    put_resp = await app_client.put(
        f"/api/v1/pages/{slug}",
        json={"content": content},
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert put_resp.status_code == 200, put_resp.json()
    put_body = put_resp.json()
    assert put_body["slug"] == slug
    assert put_body["status"] == "ok"
    assert "page_id" in put_body

    # GET
    get_resp = await app_client.get(
        f"/api/v1/pages/{slug}",
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert get_resp.status_code == 200, get_resp.json()
    get_body = get_resp.json()
    assert get_body["slug"] == slug
    assert get_body["note_type"] == "fleeting"


@pytest.mark.integration
async def test_put_page_with_timeline_mutation_returns_422(
    db_session, app_client
) -> None:
    """Timeline mutation on API write path returns 422 with timeline_violation envelope."""
    user_id = uuid.uuid4()
    vault_id = uuid.uuid4()
    _, jwt = await _seed_user_with_vault(user_id, vault_id, db_session)

    slug = f"tl-test-{uuid.uuid4().hex[:8]}"

    # v1 with a timeline entry
    await app_client.put(
        f"/api/v1/pages/{slug}",
        json={
            "content": "---\ntitle: TL Test\n---\nContent here\n---\n2024-01-01: First entry"
        },
        headers={"Authorization": f"Bearer {jwt}"},
    )

    # v2 mutates the existing timeline entry — should be rejected
    put_resp = await app_client.put(
        f"/api/v1/pages/{slug}",
        json={
            "content": "---\ntitle: TL Test\n---\nContent here\n---\n2024-01-01: MODIFIED entry"
        },
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert put_resp.status_code == 422, put_resp.json()
    body = put_resp.json()
    assert body["error"]["code"] == "timeline_violation"


@pytest.mark.integration
async def test_get_unknown_page_returns_404(db_session, app_client) -> None:
    """Unknown slug returns 404 with not_found envelope."""
    user_id = uuid.uuid4()
    vault_id = uuid.uuid4()
    _, jwt = await _seed_user_with_vault(user_id, vault_id, db_session)

    resp = await app_client.get(
        "/api/v1/pages/nonexistent-page-xyz",
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert resp.status_code == 404, resp.json()
    body = resp.json()
    assert body["error"]["code"] == "not_found"


@pytest.mark.integration
async def test_unauthenticated_request_returns_401_envelope(
    db_session, app_client
) -> None:
    """No Authorization header returns 401 with unauthorized envelope."""
    # No Authorization header
    resp = await app_client.get("/api/v1/pages/some-page")
    assert resp.status_code == 401, resp.json()
    body = resp.json()
    assert body["error"]["code"] == "unauthorized"


@pytest.mark.integration
async def test_list_pages_returns_count_and_pagination_window(
    db_session, app_client
) -> None:
    """Seed 3 pages; GET ?limit=2 returns 2 items."""
    user_id = uuid.uuid4()
    vault_id = uuid.uuid4()
    _, jwt = await _seed_user_with_vault(user_id, vault_id, db_session)

    # Create 3 pages
    for i in range(3):
        slug = f"list-page-{uuid.uuid4().hex[:8]}"
        await app_client.put(
            f"/api/v1/pages/{slug}",
            json={"content": f"---\ntitle: Page {i}\n---\nContent {i}"},
            headers={"Authorization": f"Bearer {jwt}"},
        )

    resp = await app_client.get(
        "/api/v1/pages?limit=2&offset=0",
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert resp.status_code == 200, resp.json()
    body = resp.json()
    assert len(body["pages"]) == 2
    assert body["total"] == 2  # clamped to limit


@pytest.mark.integration
async def test_delete_page_then_get_returns_404(db_session, app_client) -> None:
    """DELETE returns 200; subsequent GET returns 404."""
    user_id = uuid.uuid4()
    vault_id = uuid.uuid4()
    _, jwt = await _seed_user_with_vault(user_id, vault_id, db_session)

    slug = f"delete-test-{uuid.uuid4().hex[:8]}"
    await app_client.put(
        f"/api/v1/pages/{slug}",
        json={"content": "---\ntitle: Delete Me\n---\nContent"},
        headers={"Authorization": f"Bearer {jwt}"},
    )

    del_resp = await app_client.delete(
        f"/api/v1/pages/{slug}",
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert del_resp.status_code == 200, del_resp.json()
    assert del_resp.json()["status"] == "deleted"

    get_resp = await app_client.get(
        f"/api/v1/pages/{slug}",
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert get_resp.status_code == 404, get_resp.json()


@pytest.mark.integration
async def test_history_diff_revert_flow(db_session, app_client) -> None:
    """Write v1 -> write v2 -> history shows 2 entries -> diff returns diffs -> revert to v1."""
    user_id = uuid.uuid4()
    vault_id = uuid.uuid4()
    _, jwt = await _seed_user_with_vault(user_id, vault_id, db_session)

    slug = f"version-test-{uuid.uuid4().hex[:8]}"

    # v1
    v1_resp = await app_client.put(
        f"/api/v1/pages/{slug}",
        json={"content": "---\ntitle: Version 1\n---\nContent V1"},
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert v1_resp.status_code == 200
    v1_ver = v1_resp.json()["version"]

    # v2
    v2_resp = await app_client.put(
        f"/api/v1/pages/{slug}",
        json={"content": "---\ntitle: Version 2\n---\nContent V2"},
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert v2_resp.status_code == 200
    v2_ver = v2_resp.json()["version"]

    # history
    hist_resp = await app_client.get(
        f"/api/v1/pages/{slug}/history",
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert hist_resp.status_code == 200
    hist_body = hist_resp.json()
    assert len(hist_body["versions"]) == 2

    # diff
    diff_resp = await app_client.get(
        f"/api/v1/pages/{slug}/diff?from_version={v1_ver}&to_version={v2_ver}",
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert diff_resp.status_code == 200, diff_resp.json()
    diff_body = diff_resp.json()
    assert "compiled_truth_diff" in diff_body
    assert diff_body["from_version"] == v1_ver
    assert diff_body["to_version"] == v2_ver

    # revert to v1
    revert_resp = await app_client.post(
        f"/api/v1/pages/{slug}/revert",
        json={"target_version": v1_ver},
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert revert_resp.status_code == 200, revert_resp.json()
    revert_body = revert_resp.json()
    assert revert_body["reverted_to"] == v1_ver
    assert revert_body["new_version"] > v2_ver  # new snapshot created
