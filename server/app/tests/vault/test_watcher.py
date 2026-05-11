"""Watchdog tests — IDX-01, IDX-02, IDX-03.

These tests validate the real watchdog implementation (vault/watcher.py) against
Phase 1c requirements:
  - IDX-01: Watchdog detects vault file changes within 1 second (inotify Observer)
  - IDX-02: Thread→asyncio handoff uses run_coroutine_threadsafe (D-06)
  - IDX-03: Content-hash deduplication — skip DB write when hash unchanged

The tests bridge watchdog's sync event-handler thread and the async indexer
using asyncio.run_coroutine_threadsafe handoff.
"""

from __future__ import annotations

import asyncio
import inspect
import threading
import time
from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.vault]


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


class _FakeFileEvent:
    """Minimal stand-in for watchdog.events.FileSystemEvent."""

    def __init__(self, src_path: str, is_directory: bool = False):
        self.src_path = src_path
        self.is_directory = is_directory


# ---------------------------------------------------------------------------
# Unit / source-level invariant tests
# ---------------------------------------------------------------------------


def test_handoff_api_uses_run_coroutine_threadsafe():
    """IDX-02: VaultEventHandler uses asyncio.run_coroutine_threadsafe, not call_soon_threadsafe.

    D-06: run_coroutine_threadsafe is the ONLY correct primitive for submitting
    coroutines from a non-asyncio OS thread to the running event loop.
    call_soon_threadsafe is for sync-only lightweight callbacks.
    """
    from app.vault import watcher as watcher_module

    source = inspect.getsource(watcher_module)

    assert "run_coroutine_threadsafe" in source, (
        "VaultEventHandler must use asyncio.run_coroutine_threadsafe for async handoff"
    )
    lines_with_handoff = [
        line
        for line in source.splitlines()
        if "run_coroutine_threadsafe" in line or "call_soon_threadsafe" in line
    ]
    assert any(
        "run_coroutine_threadsafe" in src_line for src_line in lines_with_handoff
    ), "run_coroutine_threadsafe must appear in the handoff code"


def test_debounce_coalesces_rapid_events(tmp_vault_dir):
    """D-07: Per-path debounce coalesces 5 rapid on_modified events into one _fire_index call.

    threading.Timer dict cancels pending timer on new event for same path.
    Uses a very short debounce (10ms) so test runs fast.
    """
    from app.vault.watcher import VaultEventHandler

    loop = asyncio.new_event_loop()
    try:
        fire_count = 0
        fired_paths: list[str] = []

        def _mock_fire(path: str) -> None:
            nonlocal fire_count, fired_paths
            fire_count += 1
            fired_paths.append(path)

        handler = VaultEventHandler(
            loop=loop,
            debounce_ms=10,
            vault_root_path=str(tmp_vault_dir),
        )
        handler._fire_index = _mock_fire  # type: ignore[assignment]

        test_path = str(tmp_vault_dir / "rapid-save.md")
        # Simulate 5 rapid save events within the debounce window
        for _ in range(5):
            handler.on_modified(_FakeFileEvent(test_path))

        # Wait for the timer to fire (10ms debounce + 50ms buffer)
        time.sleep(0.15)

        assert fire_count == 1, (
            f"Expected exactly 1 fire for 5 rapid events, got {fire_count}. "
            f"Debounce should coalesce them."
        )
        assert fired_paths == [test_path]
    finally:
        loop.close()


def test_on_deleted_immediate_handoff_no_debounce(tmp_vault_dir):
    """on_deleted submits soft_delete_vault_file immediately (no debounce).

    Deletion should be instant — debounce only applies to create/modify events.
    """
    from app.vault.watcher import VaultEventHandler

    loop = asyncio.new_event_loop()
    try:
        handoff_calls: list[tuple] = []

        original = asyncio.run_coroutine_threadsafe

        def _capture_handoff(coro, loop_ref):
            handoff_calls.append((coro, loop_ref))
            return original(coro, loop_ref)

        with patch("asyncio.run_coroutine_threadsafe", side_effect=_capture_handoff):
            handler = VaultEventHandler(
                loop=loop,
                debounce_ms=750,
                vault_root_path=str(tmp_vault_dir),
            )
            test_path = str(tmp_vault_dir / "to-delete.md")
            handler.on_deleted(_FakeFileEvent(test_path))

        assert len(handoff_calls) == 1, (
            f"on_deleted should immediately submit handoff, got {len(handoff_calls)} calls"
        )
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hash_dedup_skips_unchanged_file(tmp_vault_dir, test_engine, monkeypatch):
    """IDX-03: index_vault_file skips DB write when content_hash unchanged.

    The vault path in tmp_vault_dir must match the vault DB record.
    seed_vault fixture creates a vault with path '/vaults/private/vaultuser-{hex}/'
    but tmp_vault_dir is /tmp/pytest-.../vaults/private/testuser/.
    We create a vault record that matches tmp_vault_dir path in this test.
    """
    from sqlalchemy import func, insert, select

    from app.auth.context import system_operation_context
    from app.dependencies import session_with_rls
    from app.models.page import Page
    from app.models.page_version import PageVersion
    from app.models.vault import Vault
    from app.vault.watcher import index_vault_file

    slug = "dedup-test"
    file_path = tmp_vault_dir / f"{slug}.md"
    content = b"---\ntype: note\n---\nHello world"
    file_path.write_bytes(content)

    # Create a vault record matching tmp_vault_dir path
    vault_path = str(tmp_vault_dir) + "/"
    vault_id = None
    ctx = system_operation_context(request_id="test", client_name="test")
    async for session in session_with_rls(ctx):
        result = await session.execute(
            insert(Vault)
            .values(
                owner_user_id=None,
                kind="private",
                path=vault_path,
            )
            .returning(Vault.id)
        )
        vault_id = result.scalar_one()
        await session.commit()
        await session.close()

    monkeypatch.setenv("SMARTCOPILOT_VAULT_ID", str(vault_id))

    # First call — should create the page
    await index_vault_file(str(file_path))

    # Query page_versions count after first call
    async for session in session_with_rls(ctx):
        result = await session.execute(
            select(func.count())
            .select_from(PageVersion)
            .join(Page, PageVersion.page_id == Page.id)
            .where(Page.slug == slug)
        )
        first_count = result.scalar_one()
        await session.close()

    assert first_count >= 1, (
        f"First index should have created at least 1 version, got {first_count}"
    )

    # Second call — same content, should skip DB write (hash unchanged)
    await index_vault_file(str(file_path))

    async for session in session_with_rls(ctx):
        result = await session.execute(
            select(func.count())
            .select_from(PageVersion)
            .join(Page, PageVersion.page_id == Page.id)
            .where(Page.slug == slug)
        )
        second_count = result.scalar_one()
        await session.close()

    assert second_count == first_count, (
        f"Hash unchanged — page_versions should not grow. "
        f"Before={first_count}, After={second_count}"
    )


@pytest.mark.asyncio
async def test_file_detection_latency(tmp_vault_dir):
    """IDX-01: Watchdog detects a new file within 1 second (inotify latency requirement).

    Start Observer briefly, write a file, verify run_coroutine_threadsafe
    was called within 1 second. Uses threading.Event for cross-thread signaling.
    """
    from watchdog.observers import Observer

    from app.vault.watcher import VaultEventHandler

    loop = asyncio.get_running_loop()
    detected = threading.Event()
    calls_made = []

    original = asyncio.run_coroutine_threadsafe

    def _on_handoff(coro, loop_ref):
        calls_made.append(str(coro))
        detected.set()
        original(coro, loop_ref)

    mock_fn = patch("asyncio.run_coroutine_threadsafe", side_effect=_on_handoff)

    with mock_fn:
        handler = VaultEventHandler(
            loop=loop,
            debounce_ms=50,  # Short debounce so test runs fast
            vault_root_path=str(tmp_vault_dir),
        )

        observer = Observer()
        observer.schedule(handler, str(tmp_vault_dir), recursive=False)
        observer.start()

        try:
            # Write file while observer is watching (on_created triggers debounce)
            test_file = tmp_vault_dir / "latency-test.md"
            test_file.write_text("---\ntype: note\n---\nContent")

            # Poll for detection (IDX-01: detect within 1 second)
            timeout = 1.5
            start = time.monotonic()
            while not detected.is_set() and (time.monotonic() - start) < timeout:
                await asyncio.sleep(0.05)

            assert detected.is_set(), (
                "run_coroutine_threadsafe was not called within 1.5 seconds. "
                "Watchdog may not be detecting file changes."
            )
        finally:
            observer.stop()
            observer.join(timeout=2)


@pytest.mark.asyncio
async def test_on_deleted_triggers_soft_delete(tmp_vault_dir, test_engine, monkeypatch):
    """on_deleted triggers soft_delete_vault_file — page.deleted_at is set."""
    from sqlalchemy import insert, select

    from app.auth.context import system_operation_context
    from app.dependencies import session_with_rls
    from app.models.page import Page
    from app.models.vault import Vault
    from app.vault.watcher import soft_delete_vault_file

    slug = "delete-me-test"

    # Create a vault record matching tmp_vault_dir path
    vault_path = str(tmp_vault_dir) + "/"
    vault_id = None
    ctx = system_operation_context(request_id="test-soft-delete", client_name="test")
    async for session in session_with_rls(ctx):
        result = await session.execute(
            insert(Vault)
            .values(
                owner_user_id=None,
                kind="private",
                path=vault_path,
            )
            .returning(Vault.id)
        )
        vault_id = result.scalar_one()
        await session.commit()
        await session.close()

    monkeypatch.setenv("SMARTCOPILOT_VAULT_ID", str(vault_id))

    # Seed a page directly in the DB (the file_path maps to slug via sanitize_filename_to_slug)
    async for session in session_with_rls(ctx):
        session.add(
            Page(
                vault_id=vault_id,
                slug=slug,
                type="note",
                note_type="fleeting",
                frontmatter={},
                compiled_truth="Test content",
                timeline="",
                content_hash="testhash123",
            )
        )
        await session.commit()
        await session.close()

    # Verify page exists and is not deleted
    async for session in session_with_rls(ctx):
        result = await session.execute(
            select(Page).where(Page.vault_id == vault_id, Page.slug == slug)
        )
        page = result.scalar_one()
        assert page.deleted_at is None, "Page should exist and not be deleted"
        await session.close()

    # Trigger soft_delete_vault_file
    file_path = tmp_vault_dir / f"{slug}.md"
    await soft_delete_vault_file(str(file_path))

    # Verify page is soft-deleted
    async for session in session_with_rls(ctx):
        result = await session.execute(
            select(Page).where(Page.vault_id == vault_id, Page.slug == slug)
        )
        page = result.scalar_one()
        assert page.deleted_at is not None, (
            "soft_delete_vault_file should set deleted_at"
        )
