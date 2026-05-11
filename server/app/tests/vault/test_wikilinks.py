"""Wikilink resolution tests — VAULT-09.

Tests resolve_and_store_wikilinks and write_page wikilink integration.
Uses direct test factory sessions (RLS bypassed) and session_with_rls for reads.

Vault fixture issue: seed_vault is session-scoped but lives in a different event loop
than the test. The vault's DB inserts from the session fixture are NOT visible to
session_with_rls in the tests because the vault was seeded in the session fixture loop.
Workaround: tests use direct test factory sessions (RLS bypassed) for writes.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.auth.context import OperationContext
from app.services.pages import resolve_and_store_wikilinks, upsert_page, write_page
from app.vault.parser import parse_vault_file

pytestmark = [pytest.mark.vault, pytest.mark.integration]


def _ctx_for(user_id: uuid.UUID, role: str = "user") -> OperationContext:
    return OperationContext(
        user_id=user_id,
        role=role,
        transport="rest",
        remote=True,
        client_name="test",
        request_id="test",
    )


def _factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def _seed_user_vault(engine: AsyncEngine) -> tuple[uuid.UUID, uuid.UUID]:
    """Seed a user and private vault. Returns (user_id, vault_id)."""
    uid = uuid.uuid4()
    vid = uuid.uuid4()
    f = _factory(engine)
    async with f() as session:
        await session.execute(
            text(
                "INSERT INTO users (id, username, role, password_hash, is_active, created_at, updated_at) "
                "VALUES (:id, :u, :r, '$argon2id$v=19$m=65536,t=3,p=1$placeholder', true, now(), now())"
            ),
            {"id": uid, "u": f"wikilink-u-{uid.hex[:8]}", "r": "user"},
        )
        await session.execute(
            text(
                "INSERT INTO vaults (id, owner_user_id, kind, path, created_at, updated_at) "
                "VALUES (:id, :uid, 'private', :path, now(), now())"
            ),
            {"id": vid, "uid": uid, "path": f"/vaults/private/wikilink-{uid.hex[:8]}/"},
        )
        await session.commit()
    return uid, vid


@pytest.mark.asyncio
async def test_resolved_links_stored_in_frontmatter_jsonb(test_engine: AsyncEngine):
    """write_page populates frontmatter._resolved_links with resolved wikilinks."""
    f = _factory(test_engine)
    uid, vid = await _seed_user_vault(test_engine)
    ctx = _ctx_for(uid)

    # Write target page via test factory (RLS bypassed)
    async with f() as session:
        await upsert_page(
            session, ctx,
            vault_id=vid,
            slug="target-note",
            parsed=parse_vault_file(b"---\ntitle: Target Note\n---\nThe target page content."),
        )
        await session.commit()

    # Write linker page that references the target
    async with f() as session:
        page = await write_page(
            session, ctx,
            slug="linker-note",
            raw_content=b"---\ntitle: Linker\n---\nThis links to [[Target Note]] here.",
            vault_id=vid,
        )
        await session.commit()
        # Verify _resolved_links was populated
        resolved = page.frontmatter.get("_resolved_links", [])
        assert isinstance(resolved, list)
        assert len(resolved) >= 1
        entry = next((e for e in resolved if "Target" in e.get("target_text", "")), None)
        assert entry is not None
        assert entry["unresolved"] is False
        assert entry["resolved_slug"] == "target-note"


@pytest.mark.asyncio
async def test_unresolved_forward_reference_allowed(test_engine: AsyncEngine):
    """write_page succeeds even when [[...]] has no matching page (D-11)."""
    f = _factory(test_engine)
    uid, vid = await _seed_user_vault(test_engine)
    ctx = _ctx_for(uid)

    async with f() as session:
        page = await write_page(
            session, ctx,
            slug="forward-ref",
            raw_content=b"---\ntitle: Forward Ref\n---\nLinks to [[Does Not Exist Yet]].",
            vault_id=vid,
        )
        await session.commit()

        resolved = page.frontmatter.get("_resolved_links", [])
        assert len(resolved) == 1
        entry = resolved[0]
        assert entry["unresolved"] is True
        assert entry["target_text"] == "Does Not Exist Yet"
        assert entry["resolved_slug"] is None
        assert entry["page_id"] is None


@pytest.mark.asyncio
async def test_display_alias_parsed(test_engine: AsyncEngine):
    """[[Target|Display Text]] parses correctly: target_text='Target'."""
    f = _factory(test_engine)
    uid, vid = await _seed_user_vault(test_engine)
    ctx = _ctx_for(uid)

    async with f() as session:
        page = await write_page(
            session, ctx,
            slug="alias-test",
            raw_content=b"---\ntitle: Alias Test\n---\nSee [[Some Page|Display Label]].",
            vault_id=vid,
        )
        await session.commit()

        resolved = page.frontmatter.get("_resolved_links", [])
        assert len(resolved) == 1
        entry = resolved[0]
        assert entry["target_text"] == "Some Page"  # display alias stripped
        assert "Display" in entry["raw"]  # raw still contains full [[...]]


@pytest.mark.asyncio
async def test_shortest_unique_path_alphabetical_tie(test_engine: AsyncEngine):
    """Multiple matches: alphabetically-first slug wins (D-11)."""
    f = _factory(test_engine)
    uid, vid = await _seed_user_vault(test_engine)
    ctx = _ctx_for(uid)

    async with f() as session:
        # Write two target pages
        await upsert_page(
            session, ctx,
            vault_id=vid,
            slug="projects/alpha-note",
            parsed=parse_vault_file(b"---\ntitle: Alpha\n---\nAlpha content."),
        )
        await session.commit()
        await upsert_page(
            session, ctx,
            vault_id=vid,
            slug="projects/zulu-note",
            parsed=parse_vault_file(b"---\ntitle: Zulu\n---\nZulu content."),
        )
        await session.commit()

        # Write linker
        page = await write_page(
            session, ctx,
            slug="linker-alpha",
            raw_content=b"---\ntitle: Linker\n---\nLinks to [[alpha-note]].",
            vault_id=vid,
        )
        await session.commit()

        resolved = page.frontmatter.get("_resolved_links", [])
        entry = resolved[0]
        assert entry["unresolved"] is False
        assert "alpha" in entry["resolved_slug"]


@pytest.mark.asyncio
async def test_resolve_and_store_wikilinks_alone(test_engine: AsyncEngine):
    """resolve_and_store_wikilinks can be called standalone after upsert."""
    f = _factory(test_engine)
    uid, vid = await _seed_user_vault(test_engine)
    ctx = _ctx_for(uid)

    async with f() as session:
        # Write target page
        await upsert_page(
            session, ctx,
            vault_id=vid,
            slug="standalone-target",
            parsed=parse_vault_file(b"---\ntitle: Standalone Target\n---\nContent."),
        )
        await session.commit()

        # Write a page without wikilinks
        page = await upsert_page(
            session, ctx,
            vault_id=vid,
            slug="no-links",
            parsed=parse_vault_file(b"---\ntitle: No Links\n---\nContent with no links."),
        )
        await session.commit()

        # Resolve wikilinks separately
        await resolve_and_store_wikilinks(
            session, page,
            "Content with [[standalone-target]] link.",
            user_vault_id=vid,
        )
        await session.commit()

        resolved = page.frontmatter.get("_resolved_links", [])
        assert len(resolved) == 1
        entry = resolved[0]
        assert entry["resolved_slug"] == "standalone-target"
        assert entry["unresolved"] is False
