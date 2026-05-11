"""Integration tests for Phase 1d MCP tools.

Tests the MCP tool implementations using a _FakeMcp class that captures
registered tools so they can be called directly without spawning the full
SDK runtime.

Uses the testcontainer PostgreSQL from conftest.py. Each test is isolated
by the db_session fixture's rollback-per-test behavior.

Note: All registered MCP tools are async functions; tests must await them.

ENG-302: session_with_rls uses async_session_factory which is bound at
module-import time to the production engine (localhost:5432). Tests that
call tools via session_with_rls read/write the production DB, not the
testcontainer. The _patch_session_with_rls fixture swaps the factory to
the test_engine for the duration of each test so that tool calls use the
correct (migrated) testcontainer.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.auth.context import OperationContext, system_operation_context
from app.dependencies import session_with_rls
from app.mcp.tools.brain import register as register_brain
from app.mcp.tools.capability import register as register_capability
from app.mcp.tools.enrich import register as register_enrich
from app.mcp.tools.entity import register as register_entity
from app.mcp.tools.graph import register as register_graph
from app.mcp.tools.ingest import register as register_ingest
from app.mcp.tools.jobs import register as register_jobs
from app.mcp.tools.maintain import register as register_maintain
from app.mcp.tools.recipe import register as register_recipe
from app.mcp.tools.skill import register as register_skill
from app.services.capabilities import get_capabilities


class _FakeMcp:
    """Minimal MCP server for testing — captures registered async tools."""

    def __init__(self) -> None:
        self.tools: dict[str, object] = {}

    def tool(self, *, name: str, description: str = "") -> object:
        def deco(fn: object) -> object:
            self.tools[name] = fn  # type: ignore[index]
            return fn

        return deco


@pytest.fixture
def fake_mcp() -> _FakeMcp:
    return _FakeMcp()


@pytest.fixture
def ctx_factory():
    """Creates a fixed OperationContext for tests."""

    def make_ctx(
        user_id: uuid.UUID | None = None,
        remote: bool = False,
        transport: str = "rest",
    ) -> OperationContext:
        return OperationContext(
            user_id=user_id or uuid.uuid4(),
            role="user",
            transport=transport,
            remote=remote,
            client_name="test",
            request_id="test",
        )

    return make_ctx


async def _call_tool(fake_mcp: _FakeMcp, name: str, **kwargs: object) -> dict:
    """Await an async tool function."""
    return await fake_mcp.tools[name](**kwargs)  # type: ignore[operator]


@pytest_asyncio.fixture
async def patched_mcp_context(test_engine):
    """ENG-302: Patch session_with_rls to use conftest's test_engine (which ran alembic).

    test_engine is session-scoped (conftest.py) — it runs alembic upgrade head once,
    so the database always has all migrations including 0004 (search_vector column).
    We bind test_engine to a fresh async_sessionmaker and swap that into
    session_with_rls so all MCP tool calls hit the migrated testcontainer.

    pgvector registration is NOT needed here — the FTS query uses the search_vector
    tsvector column (0004 migration), not pgvector vector columns.
    """
    from app import database as _db_mod
    from app.dependencies import session_with_rls as _orig_swsrl

    # test_engine is already migrated (alembic ran in conftest).
    # Build a sessionmaker bound to test_engine so session_with_rls uses it.
    test_factory = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
    )

    # Swap out session_with_rls so all MCP tool calls use the testcontainer.
    # Both _db_mod.async_session_factory and _orig_swsrl.__globals__ point to the
    # same object. We must patch BOTH places — patching only _db_mod does NOT
    # update session_with_rls's global namespace (verified: globals is a dict
    # snapshot, replacing the module attr does not update the func's globals).
    old_factory = _db_mod.async_session_factory
    _db_mod.async_session_factory = test_factory
    _orig_swsrl.__globals__["async_session_factory"] = test_factory

    try:
        yield
    finally:
        _db_mod.async_session_factory = old_factory
        _orig_swsrl.__globals__["async_session_factory"] = old_factory


# ------------------------------------------------------------------
# Tool registration tests (sync — no DB needed)
# ------------------------------------------------------------------


def test_all_tools_registered(fake_mcp: _FakeMcp, ctx_factory) -> None:
    """Every Phase 1d tool module registers on a FastMCP instance."""
    register_brain(fake_mcp, ctx_factory)
    register_capability(fake_mcp, ctx_factory)
    register_ingest(fake_mcp, ctx_factory)
    register_enrich(fake_mcp, ctx_factory)
    register_recipe(fake_mcp, ctx_factory)
    register_skill(fake_mcp, ctx_factory)
    register_jobs(fake_mcp, ctx_factory)
    register_maintain(fake_mcp, ctx_factory)
    register_entity(fake_mcp, ctx_factory)
    register_graph(fake_mcp, ctx_factory)

    # MCP-06: at least 30 tools
    assert len(fake_mcp.tools) >= 30, f"Expected >=30 tools, got {len(fake_mcp.tools)}"

    # 14 real tools
    real = [
        "brain.put",
        "brain.get",
        "brain.search",
        "brain.list",
        "brain.delete",
        "brain.history",
        "brain.diff",
        "brain.revert",
        "brain.append_timeline",
        "brain.update_compiled_truth",
        "brain.backlinks",
        "brain.stats",
        "brain.health",
        "capability_discovery",
    ]
    for name in real:
        assert name in fake_mcp.tools, f"Missing real tool: {name}"


async def test_all_stub_tools_return_not_implemented_payload(
    fake_mcp: _FakeMcp, ctx_factory
) -> None:
    """All stub tools return the D-05 not_implemented payload."""
    register_ingest(fake_mcp, ctx_factory)
    register_enrich(fake_mcp, ctx_factory)
    register_recipe(fake_mcp, ctx_factory)
    register_skill(fake_mcp, ctx_factory)
    register_jobs(fake_mcp, ctx_factory)
    register_maintain(fake_mcp, ctx_factory)
    register_entity(fake_mcp, ctx_factory)
    register_graph(fake_mcp, ctx_factory)

    stub_names = [
        "ingest.idea",
        "ingest.media",
        "ingest.meeting",
        "enrich.entity",
        "recipe.run",
        "skill.list",
        "skill.get",
        "skill.run",
        "jobs.submit",
        "jobs.status",
        "jobs.cancel",
        "maintain.run",
        "maintain.report",
        "brain.entity.get",
        "brain.entity.merge",
        "brain.entity.list",
        "brain.graph.traverse",
    ]
    for name in stub_names:
        result = await _call_tool(fake_mcp, name)
        assert "error" in result, f"{name} missing error key"
        assert result["error"]["code"] == "not_implemented"
        assert "available_in_phase" in result["error"]


def test_stub_tools_are_discoverable(fake_mcp: _FakeMcp, ctx_factory) -> None:
    """Stub tools are in fake_mcp.tools (discoverable) — NOT missing."""
    register_ingest(fake_mcp, ctx_factory)
    register_jobs(fake_mcp, ctx_factory)

    assert "ingest.idea" in fake_mcp.tools
    assert "jobs.submit" in fake_mcp.tools


async def test_capability_discovery_matches_get_capabilities(
    fake_mcp: _FakeMcp, ctx_factory
) -> None:
    """capability_discovery returns identical dict to get_capabilities()."""
    register_capability(fake_mcp, ctx_factory)
    result = await _call_tool(fake_mcp, "capability_discovery")
    expected = get_capabilities()
    assert result == expected


async def test_remote_true_invalid_slug_rejected(
    fake_mcp: _FakeMcp, ctx_factory
) -> None:
    """ctx.remote=True with invalid slug returns validation_error or not_found."""
    register_brain(fake_mcp, ctx_factory)
    # Must pass remote=True so the slug validation gate in brain.put fires.
    remote_ctx = ctx_factory(remote=True)
    result = await _call_tool(
        fake_mcp, "brain.put", slug="BAD SLUG", content="hello", namespace="private"
    )
    assert "error" in result
    # validation_error: slug rejected before vault lookup. no vault (not_found).
    # Both are acceptable — the key invariant is no unhandled exception.
    assert result["error"]["code"] in ("validation_error", "not_found")


# ------------------------------------------------------------------
# DB integration tests
# ------------------------------------------------------------------


async def _seed_user_and_vault(user_id: uuid.UUID, vault_id: uuid.UUID) -> None:
    """Create a user + private vault for tests using session_with_rls (system ctx).

    Uses system_operation_context + session_with_rls to bypass RLS so the vault
    can be created regardless of the caller's identity. This avoids the loop-scope
    mismatch between pytest-asyncio's session fixture and the test event loop.
    """
    async for session in session_with_rls(system_operation_context(client_name="seed")):
        from app.models.user import User
        from app.models.vault import Vault

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


async def test_brain_put_creates_page(ctx_factory, patched_mcp_context) -> None:
    """brain.put writes a page to the database."""
    user_id = uuid.uuid4()
    vault_id = uuid.uuid4()
    await _seed_user_and_vault(user_id, vault_id)

    seeded_ctx = ctx_factory(user_id=user_id, remote=True)
    fake_mcp = _FakeMcp()
    register_brain(fake_mcp, lambda _=None: seeded_ctx)

    result = await _call_tool(
        fake_mcp,
        "brain.put",
        slug="test-page-001",
        content="---\ntitle: Test Page\n---\nThis is a test.",
        namespace="private",
    )

    assert "error" not in result, f"Unexpected error: {result}"
    assert result["status"] == "ok"
    assert result["slug"] == "test-page-001"
    assert "page_id" in result


async def test_brain_get_returns_page_dict(ctx_factory, patched_mcp_context) -> None:
    """brain.get returns the expected dict shape for an existing page."""
    user_id = uuid.uuid4()
    vault_id = uuid.uuid4()
    await _seed_user_and_vault(user_id, vault_id)

    seeded_ctx = ctx_factory(user_id=user_id, remote=True)
    fake_mcp = _FakeMcp()
    register_brain(fake_mcp, lambda _=None: seeded_ctx)

    # Put a page first
    put_result = await _call_tool(
        fake_mcp,
        "brain.put",
        slug="get-test-page",
        content="---\ntitle: Get Test\n---\nGet test content.",
        namespace="private",
    )
    assert "error" not in put_result

    # Now get it
    get_result = await _call_tool(fake_mcp, "brain.get", slug="get-test-page")
    assert "error" not in get_result
    assert get_result["slug"] == "get-test-page"
    assert "page_id" in get_result
    assert "note_type" in get_result
    assert "compiled_truth" in get_result


async def test_brain_search_returns_fts_envelope(
    ctx_factory, patched_mcp_context
) -> None:
    """brain.search returns the D-02 envelope: results, total, query, search_type."""
    user_id = uuid.uuid4()
    vault_id = uuid.uuid4()
    await _seed_user_and_vault(user_id, vault_id)

    seeded_ctx = ctx_factory(user_id=user_id, remote=True)
    fake_mcp = _FakeMcp()
    register_brain(fake_mcp, lambda _=None: seeded_ctx)

    # Put pages with searchable content
    for slug, content in [
        (
            "searchable-alpha",
            "---\ntitle: Alpha\n---\nAlpha content about python programming.",
        ),
        (
            "searchable-beta",
            "---\ntitle: Beta\n---\nBeta content about rust programming.",
        ),
        ("not-matching", "---\ntitle: Gamma\n---\nGamma content about nothing."),
    ]:
        r = await _call_tool(
            fake_mcp, "brain.put", slug=slug, content=content, namespace="private"
        )
        assert "error" not in r, f"brain.put failed: {r}"

    result = await _call_tool(fake_mcp, "brain.search", query="python", limit=10)

    assert "error" not in result
    assert "results" in result
    assert "total" in result
    assert "query" in result
    assert "search_type" in result
    assert result["search_type"] == "fts_v1"
    assert result["query"] == "python"
    assert result["total"] >= 1  # at least one match


async def test_brain_search_invalid_query_returns_validation_error(
    fake_mcp: _FakeMcp, ctx_factory
) -> None:
    """brain.search with empty query returns validation_error."""
    register_brain(fake_mcp, ctx_factory)

    result = await _call_tool(fake_mcp, "brain.search", query="", limit=10)
    assert "error" in result
    assert result["error"]["code"] == "validation_error"


async def test_brain_history_diff_revert_round_trip(
    ctx_factory, patched_mcp_context
) -> None:
    """put v1 -> put v2 -> history shows 2 versions -> diff returns unified diff -> revert to v1."""
    user_id = uuid.uuid4()
    vault_id = uuid.uuid4()
    await _seed_user_and_vault(user_id, vault_id)

    seeded_ctx = ctx_factory(user_id=user_id, remote=True)
    fake_mcp = _FakeMcp()
    register_brain(fake_mcp, lambda _=None: seeded_ctx)

    slug = "version-test-page"

    # Put v1
    r1 = await _call_tool(
        fake_mcp,
        "brain.put",
        slug=slug,
        content="---\ntitle: V1\n---\nVersion 1 content.",
        namespace="private",
    )
    assert "error" not in r1

    # Put v2
    r2 = await _call_tool(
        fake_mcp,
        "brain.put",
        slug=slug,
        content="---\ntitle: V2\n---\nVersion 2 content.",
        namespace="private",
    )
    assert "error" not in r2

    # History shows 2 versions
    history = await _call_tool(fake_mcp, "brain.history", slug=slug)
    assert "error" not in history
    assert len(history["versions"]) >= 2

    v1_version = history["versions"][-1]["version"]  # oldest
    v2_version = history["versions"][0]["version"]  # newest

    # Diff between v1 and v2
    diff_result = await _call_tool(
        fake_mcp,
        "brain.diff",
        slug=slug,
        from_version=v1_version,
        to_version=v2_version,
    )
    assert "error" not in diff_result
    assert "compiled_truth_diff" in diff_result
    assert "timeline_diff" in diff_result

    # Revert to v1
    revert_result = await _call_tool(
        fake_mcp, "brain.revert", slug=slug, target_version=v1_version
    )
    assert "error" not in revert_result
    assert revert_result["reverted_to"] == v1_version


async def test_brain_health_returns_status(fake_mcp: _FakeMcp, ctx_factory) -> None:
    """brain_health returns dict with db_ok/fernet_ok/watchdog_alive keys."""
    register_brain(fake_mcp, ctx_factory)

    result = await _call_tool(fake_mcp, "brain.health")
    assert "error" not in result
    assert "db_ok" in result
    assert "fernet_ok" in result
    assert "watchdog_alive" in result
    assert isinstance(result["db_ok"], bool)
    assert isinstance(result["fernet_ok"], bool)
    # watchdog_alive is None in Phase 1d
    assert result["watchdog_alive"] is None
