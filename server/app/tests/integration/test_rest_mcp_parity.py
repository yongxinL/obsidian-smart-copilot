"""REST-01 parity: every Phase 1d real MCP tool has a 1:1 REST counterpart.

D-12: REST↔MCP parity is phase-aware — only Phase 1d real tools are tested.
brain.stats and brain.health have no REST counterpart in Phase 1d (documented in test).

Uses httpx.AsyncClient (conftest.py app_client fixture) for REST calls.
MCP tools are called directly via _FakeMcp + register functions.
The patch_async_session_factory fixture in conftest ensures both paths
use the testcontainer DB with proper session bindings.
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio

from app.auth.context import OperationContext
from app.auth.tokens import issue_access_jwt
from app.mcp.tools.brain import register as register_brain
from app.mcp.tools.capability import register as register_capability
from app.models.user import User
from app.models.vault import Vault
from app.settings import settings

from app.tests.integration.test_mcp_tools import _FakeMcp as FakeMcp


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


def _make_ctx(user_id: uuid.UUID) -> OperationContext:
    return OperationContext(
        user_id=user_id, role="user",
        transport="rest", remote=True,
        client_name="parity-test", request_id="parity-test",
    )


# ── Capability discovery parity ──────────────────────────────────────────────


@pytest.mark.integration
async def test_capability_discovery_matches_rest_get_capabilities(
    db_session, app_client,
) -> None:
    """capability_discovery and GET /api/v1/capabilities return identical payloads (D-15)."""
    # REST path
    rest_resp = await app_client.get("/api/v1/capabilities")
    assert rest_resp.status_code == 200
    rest_payload = rest_resp.json()

    # MCP path — call the service function directly (same source as MCP tool)
    from app.services.capabilities import get_capabilities
    mcp_payload = get_capabilities()

    assert rest_payload == mcp_payload
    assert mcp_payload["phase"] == "1d"
    assert mcp_payload["transports"] == ["stdio", "http"]


# ── brain.put / PUT /api/v1/pages/{slug} ─────────────────────────────────────


@pytest.mark.integration
async def test_brain_put_and_rest_put_return_same_status(
    db_session, app_client,
) -> None:
    """brain.put and PUT /api/v1/pages/{slug} both return status=ok for the same slug."""
    user_id = uuid.uuid4()
    vault_id = uuid.uuid4()
    _, jwt = await _seed_user_with_vault(user_id, vault_id, db_session)

    slug = f"parity-put-{uuid.uuid4().hex[:8]}"
    content = "---\ntitle: Parity Test\n---\nParity test content."

    fake_mcp = FakeMcp()
    register_brain(fake_mcp, lambda _=None: _make_ctx(user_id))

    # MCP path
    mcp_result = await fake_mcp.tools["brain.put"](
        slug=slug, content=content, namespace="private"
    )

    # REST path — use a different slug to avoid conflict
    slug_rest = f"{slug}-rest"
    rest_resp = await app_client.put(
        f"/api/v1/pages/{slug_rest}",
        json={"content": content},
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert rest_resp.status_code == 200, rest_resp.json()
    rest_result = rest_resp.json()

    # Both succeed and report status ok
    assert mcp_result.get("status") == "ok", mcp_result
    assert rest_result.get("status") == "ok", rest_result
    assert mcp_result["slug"] == slug
    assert rest_result["slug"] == slug_rest


# ── brain.get / GET /api/v1/pages/{slug} ───────────────────────────────────────


@pytest.mark.integration
async def test_brain_get_and_rest_get_return_same_fields(
    db_session, app_client,
) -> None:
    """brain.get and GET /api/v1/pages/{slug} return equivalent essential fields."""
    user_id = uuid.uuid4()
    vault_id = uuid.uuid4()
    _, jwt = await _seed_user_with_vault(user_id, vault_id, db_session)

    slug = f"parity-get-{uuid.uuid4().hex[:8]}"
    content = "---\ntitle: Get Parity\n---\nGet parity content."

    # Create via REST first
    await app_client.put(
        f"/api/v1/pages/{slug}",
        json={"content": content},
        headers={"Authorization": f"Bearer {jwt}"},
    )

    # REST path
    rest_resp = await app_client.get(
        f"/api/v1/pages/{slug}",
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert rest_resp.status_code == 200
    rest_result = rest_resp.json()

    # MCP path
    fake_mcp = FakeMcp()
    register_brain(fake_mcp, lambda _=None: _make_ctx(user_id))
    mcp_result = await fake_mcp.tools["brain.get"](slug=slug)

    assert mcp_result.get("error") is None, mcp_result
    assert mcp_result["slug"] == rest_result["slug"]
    assert mcp_result["page_id"] == str(rest_result["page_id"])
    assert mcp_result["note_type"] == rest_result["note_type"]


# ── brain.list / GET /api/v1/pages ───────────────────────────────────────────


@pytest.mark.integration
async def test_brain_list_and_rest_list_match(
    db_session, app_client,
) -> None:
    """brain.list and GET /api/v1/pages both return pages list for the same user."""
    user_id = uuid.uuid4()
    vault_id = uuid.uuid4()
    _, jwt = await _seed_user_with_vault(user_id, vault_id, db_session)

    # Create two pages
    for i in range(2):
        slug = f"parity-list-{uuid.uuid4().hex[:8]}"
        await app_client.put(
            f"/api/v1/pages/{slug}",
            json={"content": f"---\ntitle: List {i}\n---\nContent {i}"},
            headers={"Authorization": f"Bearer {jwt}"},
        )

    # REST path
    rest_resp = await app_client.get(
        "/api/v1/pages?limit=50",
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert rest_resp.status_code == 200
    rest_body = rest_resp.json()
    rest_slugs = {p["slug"] for p in rest_body["pages"]}

    # MCP path
    fake_mcp = FakeMcp()
    register_brain(fake_mcp, lambda _=None: _make_ctx(user_id))
    mcp_result = await fake_mcp.tools["brain.list"](limit=50)

    assert mcp_result.get("error") is None, mcp_result
    mcp_slugs = {item["slug"] for item in mcp_result["pages"]}

    # Both return the same set of slugs (user's own vault)
    assert rest_slugs == mcp_slugs


# ── brain.search / POST /api/v1/search ─────────────────────────────────────────


@pytest.mark.integration
async def test_brain_search_and_rest_search_return_same_envelope(
    db_session, app_client,
) -> None:
    """brain.search and POST /api/v1/search return the same D-02 envelope shape."""
    user_id = uuid.uuid4()
    vault_id = uuid.uuid4()
    _, jwt = await _seed_user_with_vault(user_id, vault_id, db_session)

    # Create pages with searchable content
    await app_client.put(
        "/api/v1/pages/parity-search-001",
        json={"content": "---\ntitle: Search Parity\n---\nPython programming language."},
        headers={"Authorization": f"Bearer {jwt}"},
    )

    # REST path
    rest_resp = await app_client.post(
        "/api/v1/search",
        json={"query": "python", "limit": 10},
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert rest_resp.status_code == 200
    rest_body = rest_resp.json()

    # MCP path
    fake_mcp = FakeMcp()
    register_brain(fake_mcp, lambda _=None: _make_ctx(user_id))
    mcp_result = await fake_mcp.tools["brain.search"](query="python", limit=10)

    assert mcp_result.get("error") is None, mcp_result
    # Both have the same envelope shape
    assert rest_body["search_type"] == mcp_result["search_type"] == "fts_v1"
    assert rest_body["query"] == mcp_result["query"]
    assert "results" in rest_body
    assert "results" in mcp_result
    assert rest_body["total"] == mcp_result["total"]


# ── brain.delete / DELETE /api/v1/pages/{slug} ───────────────────────────────


@pytest.mark.integration
async def test_brain_delete_and_rest_delete_return_same_status(
    db_session, app_client,
) -> None:
    """brain.delete and DELETE /api/v1/pages/{slug} both return status=deleted."""
    user_id = uuid.uuid4()
    vault_id = uuid.uuid4()
    _, jwt = await _seed_user_with_vault(user_id, vault_id, db_session)

    slug = f"parity-del-{uuid.uuid4().hex[:8]}"

    # Create page
    await app_client.put(
        f"/api/v1/pages/{slug}",
        json={"content": "---\ntitle: Delete Parity\n---\nContent"},
        headers={"Authorization": f"Bearer {jwt}"},
    )

    # REST path
    rest_resp = await app_client.delete(
        f"/api/v1/pages/{slug}",
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert rest_resp.status_code == 200
    rest_result = rest_resp.json()
    assert rest_result["status"] == "deleted"

    # MCP path — use a fresh slug
    slug_mcp = f"parity-del-mcp-{uuid.uuid4().hex[:8]}"
    await app_client.put(
        f"/api/v1/pages/{slug_mcp}",
        json={"content": "---\ntitle: Delete MCP\n---\nContent"},
        headers={"Authorization": f"Bearer {jwt}"},
    )
    fake_mcp = FakeMcp()
    register_brain(fake_mcp, lambda _=None: _make_ctx(user_id))
    mcp_result = await fake_mcp.tools["brain.delete"](slug=slug_mcp)

    assert mcp_result.get("status") == "deleted", mcp_result


# ── brain.history / GET /api/v1/pages/{slug}/history ─────────────────────────


@pytest.mark.integration
async def test_brain_history_and_rest_history_return_same_versions(
    db_session, app_client,
) -> None:
    """brain.history and GET /api/v1/pages/{slug}/history return the same version list."""
    user_id = uuid.uuid4()
    vault_id = uuid.uuid4()
    _, jwt = await _seed_user_with_vault(user_id, vault_id, db_session)

    slug = f"parity-hist-{uuid.uuid4().hex[:8]}"

    # Create v1 and v2
    await app_client.put(
        f"/api/v1/pages/{slug}",
        json={"content": "---\ntitle: V1\n---\nContent V1"},
        headers={"Authorization": f"Bearer {jwt}"},
    )
    await app_client.put(
        f"/api/v1/pages/{slug}",
        json={"content": "---\ntitle: V2\n---\nContent V2"},
        headers={"Authorization": f"Bearer {jwt}"},
    )

    # REST path
    rest_resp = await app_client.get(
        f"/api/v1/pages/{slug}/history",
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert rest_resp.status_code == 200
    rest_body = rest_resp.json()
    rest_versions = [v["version"] for v in rest_body["versions"]]

    # MCP path
    fake_mcp = FakeMcp()
    register_brain(fake_mcp, lambda _=None: _make_ctx(user_id))
    mcp_result = await fake_mcp.tools["brain.history"](slug=slug)

    assert mcp_result.get("error") is None, mcp_result
    mcp_versions = [v["version"] for v in mcp_result["versions"]]

    assert rest_versions == mcp_versions
    assert len(rest_versions) == 2


# ── brain.diff / GET /api/v1/pages/{slug}/diff ─────────────────────────────────


@pytest.mark.integration
async def test_brain_diff_and_rest_diff_return_same_diffs(
    db_session, app_client,
) -> None:
    """brain.diff and GET /api/v1/pages/{slug}/diff return the same compiled_truth_diff."""
    user_id = uuid.uuid4()
    vault_id = uuid.uuid4()
    _, jwt = await _seed_user_with_vault(user_id, vault_id, db_session)

    slug = f"parity-diff-{uuid.uuid4().hex[:8]}"

    # Create two versions
    await app_client.put(
        f"/api/v1/pages/{slug}",
        json={"content": "---\ntitle: Diff V1\n---\nContent V1"},
        headers={"Authorization": f"Bearer {jwt}"},
    )
    await app_client.put(
        f"/api/v1/pages/{slug}",
        json={"content": "---\ntitle: Diff V2\n---\nContent V2"},
        headers={"Authorization": f"Bearer {jwt}"},
    )

    # Get versions
    hist_resp = await app_client.get(
        f"/api/v1/pages/{slug}/history",
        headers={"Authorization": f"Bearer {jwt}"},
    )
    v1 = hist_resp.json()["versions"][1]["version"]  # oldest
    v2 = hist_resp.json()["versions"][0]["version"]   # newest

    # REST path
    rest_resp = await app_client.get(
        f"/api/v1/pages/{slug}/diff?from_version={v1}&to_version={v2}",
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert rest_resp.status_code == 200
    rest_body = rest_resp.json()

    # MCP path
    fake_mcp = FakeMcp()
    register_brain(fake_mcp, lambda _=None: _make_ctx(user_id))
    mcp_result = await fake_mcp.tools["brain.diff"](
        slug=slug, from_version=v1, to_version=v2
    )

    assert mcp_result.get("error") is None, mcp_result
    assert rest_body["compiled_truth_diff"] == mcp_result["compiled_truth_diff"]
    assert rest_body["timeline_diff"] == mcp_result["timeline_diff"]


# ── brain.revert / POST /api/v1/pages/{slug}/revert ──────────────────────────


@pytest.mark.integration
async def test_brain_revert_and_rest_revert_same_result(
    db_session, app_client,
) -> None:
    """brain.revert and POST /api/v1/pages/{slug}/revert both succeed for the same target."""
    user_id = uuid.uuid4()
    vault_id = uuid.uuid4()
    _, jwt = await _seed_user_with_vault(user_id, vault_id, db_session)

    slug = f"parity-revert-{uuid.uuid4().hex[:8]}"

    # Create v1 and v2
    await app_client.put(
        f"/api/v1/pages/{slug}",
        json={"content": "---\ntitle: Rev V1\n---\nContent V1"},
        headers={"Authorization": f"Bearer {jwt}"},
    )
    await app_client.put(
        f"/api/v1/pages/{slug}",
        json={"content": "---\ntitle: Rev V2\n---\nContent V2"},
        headers={"Authorization": f"Bearer {jwt}"},
    )

    # Get v1 version number
    hist_resp = await app_client.get(
        f"/api/v1/pages/{slug}/history",
        headers={"Authorization": f"Bearer {jwt}"},
    )
    v1 = hist_resp.json()["versions"][1]["version"]  # oldest

    # REST path
    rest_resp = await app_client.post(
        f"/api/v1/pages/{slug}/revert",
        json={"target_version": v1},
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert rest_resp.status_code == 200
    rest_body = rest_resp.json()
    assert rest_body["reverted_to"] == v1

    # MCP path — revert to the same version
    fake_mcp = FakeMcp()
    register_brain(fake_mcp, lambda _=None: _make_ctx(user_id))
    mcp_result = await fake_mcp.tools["brain.revert"](slug=slug, target_version=v1)

    assert mcp_result.get("error") is None, mcp_result
    assert mcp_result["reverted_to"] == v1


# ── brain.append_timeline / POST /api/v1/pages/{slug}/timeline ──────────────


@pytest.mark.integration
async def test_brain_append_timeline_and_rest_append_timeline_match(
    db_session, app_client,
) -> None:
    """brain.append_timeline and POST /api/v1/pages/{slug}/timeline both return status=appended."""
    user_id = uuid.uuid4()
    vault_id = uuid.uuid4()
    _, jwt = await _seed_user_with_vault(user_id, vault_id, db_session)

    slug = f"parity-tl-{uuid.uuid4().hex[:8]}"

    # Create page first
    await app_client.put(
        f"/api/v1/pages/{slug}",
        json={"content": "---\ntitle: TL\n---\nContent"},
        headers={"Authorization": f"Bearer {jwt}"},
    )

    # REST path
    rest_resp = await app_client.post(
        f"/api/v1/pages/{slug}/timeline",
        json={"entry": "2025-01-01: Timeline entry from REST"},
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert rest_resp.status_code == 200
    rest_body = rest_resp.json()
    assert rest_body["status"] == "appended"

    # MCP path
    fake_mcp = FakeMcp()
    register_brain(fake_mcp, lambda _=None: _make_ctx(user_id))
    mcp_result = await fake_mcp.tools["brain.append_timeline"](
        slug=slug, entry="2025-01-01: Timeline entry from MCP"
    )

    assert mcp_result.get("status") == "appended", mcp_result


# ── brain.backlinks / GET /api/v1/pages/{slug}/backlinks ──────────────────────


@pytest.mark.integration
async def test_brain_backlinks_and_rest_backlinks_match(
    db_session, app_client,
) -> None:
    """brain.backlinks and GET /api/v1/pages/{slug}/backlinks return same backlink list."""
    user_id = uuid.uuid4()
    vault_id = uuid.uuid4()
    _, jwt = await _seed_user_with_vault(user_id, vault_id, db_session)

    target_slug = f"parity-target-{uuid.uuid4().hex[:8]}"
    source_slug = f"parity-source-{uuid.uuid4().hex[:8]}"

    # Create target page
    await app_client.put(
        f"/api/v1/pages/{target_slug}",
        json={"content": "---\ntitle: Target\n---\nTarget content."},
        headers={"Authorization": f"Bearer {jwt}"},
    )

    # Create source page with wikilink to target
    await app_client.put(
        f"/api/v1/pages/{source_slug}",
        json={
            "content": f"---\ntitle: Source\n---\nLinking to [[{target_slug}]]"
        },
        headers={"Authorization": f"Bearer {jwt}"},
    )

    # REST path
    rest_resp = await app_client.get(
        f"/api/v1/pages/{target_slug}/backlinks",
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert rest_resp.status_code == 200
    rest_body = rest_resp.json()
    rest_slugs = {b["slug"] for b in rest_body["backlinks"]}

    # MCP path
    fake_mcp = FakeMcp()
    register_brain(fake_mcp, lambda _=None: _make_ctx(user_id))
    mcp_result = await fake_mcp.tools["brain.backlinks"](slug=target_slug)

    assert mcp_result.get("error") is None, mcp_result
    mcp_slugs = {item["slug"] for item in mcp_result["backlinks"]}

    assert rest_slugs == mcp_slugs
    # Note: Phase 1d wikilink resolution stores links in frontmatter._resolved_links
    # but get_backlinks_for_page reads that field. Phase 2b will wire links table reads.
    # For now, both paths return the same empty set (link resolution is forward-compatible).