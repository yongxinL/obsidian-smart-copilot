"""Vault watchdog process entry point (IDX-01, IDX-02, IDX-03).

Phase 1c: real inotify-based watchdog replacing the Phase 1a stub.
Supervisord program priority 50 invokes this as: python -m app.vault.watcher

D-06: use asyncio.run_coroutine_threadsafe exclusively for async handoff.
D-07: per-path 750ms debounce with cancellable threading.Timer dict.
D-03: watchdog bypasses timeline enforcement (enforce_timeline=False).
IDX-03: upsert_page skips DB write when content_hash unchanged.
Pitfall 2: loop obtained INSIDE _amain via asyncio.get_running_loop().
Pitfall 6: cancel all pending timers in shutdown sequence.
"""

from __future__ import annotations

import asyncio
import os
import signal
import sys
import threading
import uuid
from pathlib import Path

import structlog
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from app.auth.context import system_operation_context
from app.dependencies import session_with_rls
from app.logging.redaction import configure_logging
from app.services.pages import soft_delete_page, upsert_page
from app.settings import settings
from app.vault.parser import parse_vault_file
from app.vault.paths import sanitize_filename_to_slug

log = structlog.get_logger("smart_copilot.watchdog")


async def index_vault_file(path: str) -> None:
    """Read vault file, parse, upsert page (IDX-03 dedup handled inside upsert_page).

    D-03: enforce_timeline=False — watchdog never rejects filesystem edits.
    Log a warning if the existing page has a timeline (filesystem change may
    have mutated it — human filesystem access is trusted).
    """
    ctx = system_operation_context(request_id="watchdog", client_name="watcher")
    async for session in session_with_rls(ctx):
        file_path = Path(path)
        if not file_path.exists():
            return  # File was deleted between event and index call

        raw = file_path.read_bytes()
        slug = sanitize_filename_to_slug(file_path.name)

        vault_id_str = os.environ.get("SMARTCOPILOT_VAULT_ID", "")
        if not vault_id_str:
            log.warning("watchdog_vault_id_not_set", path=path)
            return
        vault_id = uuid.UUID(vault_id_str)

        # Check existing page for D-03 maintenance warning
        from sqlalchemy import select

        from app.models.page import Page

        existing_result = await session.execute(
            select(Page).where(
                Page.vault_id == vault_id,
                Page.slug == slug,
                Page.deleted_at.is_(None),
            )
        )
        existing_page = existing_result.scalar_one_or_none()
        if existing_page is not None and existing_page.timeline:
            # D-03: filesystem change may have mutated timeline — emit warning
            log.warning(
                "timeline_mutated_by_filesystem",
                slug=slug,
                file_path=path,
            )

        try:
            parsed = parse_vault_file(raw)
            await upsert_page(
                session,
                ctx,
                vault_id=vault_id,
                slug=slug,
                parsed=parsed,
                enforce_timeline=False,  # D-03: watchdog bypasses timeline enforcement
            )
            await session.commit()
            log.info("indexed_vault_file", slug=slug, path=path)
        except Exception as exc:  # noqa: BLE001
            log.error("index_vault_file_failed", path=path, error=str(exc))


async def soft_delete_vault_file(path: str) -> None:
    """Soft-delete the page corresponding to the given vault file path.

    on_deleted triggers this immediately (no debounce on delete).
    """
    ctx = system_operation_context(request_id="watchdog", client_name="watcher")
    async for session in session_with_rls(ctx):
        file_path = Path(path)
        slug = sanitize_filename_to_slug(file_path.name)

        vault_id_str = os.environ.get("SMARTCOPILOT_VAULT_ID", "")
        if not vault_id_str:
            log.warning("soft_delete_vault_id_not_set", path=path)
            return
        vault_id = uuid.UUID(vault_id_str)

        from sqlalchemy import select

        from app.models.page import Page

        page_result = await session.execute(
            select(Page).where(
                Page.vault_id == vault_id,
                Page.slug == slug,
                Page.deleted_at.is_(None),
            )
        )
        page = page_result.scalar_one_or_none()
        if page is None:
            log.debug("soft_delete_page_not_found", slug=slug)
            return

        try:
            await soft_delete_page(
                session,
                ctx,
                page_id=page.id,
                reason="file_deleted",
            )
            await session.commit()
            log.info("soft_deleted_vault_file", slug=slug, path=path)
        except Exception as exc:  # noqa: BLE001
            log.error("soft_delete_vault_file_failed", path=path, error=str(exc))


class VaultEventHandler(FileSystemEventHandler):
    """Watchdog event handler with per-path debounce (D-07, Pitfall 6).

    Uses asyncio.run_coroutine_threadsafe (D-06) to submit work to the
    running asyncio event loop from the watchdog OS thread.
    """

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        debounce_ms: int,
        vault_root_path: str,
    ) -> None:
        super().__init__()
        self._loop = loop
        self._debounce_s = debounce_ms / 1000.0
        self._vault_root_path = vault_root_path
        self._timers: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    def _schedule_index(self, path: str) -> None:
        """Per-path debounce: cancel pending timer for same path, schedule new one (D-07)."""
        with self._lock:
            if path in self._timers:
                self._timers[path].cancel()
            timer = threading.Timer(
                self._debounce_s,
                self._fire_index,
                args=(path,),
            )
            self._timers[path] = timer
            timer.start()

    def _fire_index(self, path: str) -> None:
        """Called by Timer thread after debounce — submit to asyncio loop (D-06)."""
        with self._lock:
            self._timers.pop(path, None)
        asyncio.run_coroutine_threadsafe(index_vault_file(path), self._loop)

    def on_modified(self, event: object) -> None:
        if not getattr(event, "is_directory", False):
            src_path = getattr(event, "src_path", None)
            if src_path:
                self._schedule_index(src_path)

    def on_created(self, event: object) -> None:
        if not getattr(event, "is_directory", False):
            src_path = getattr(event, "src_path", None)
            if src_path:
                self._schedule_index(src_path)

    def on_deleted(self, event: object) -> None:
        if not getattr(event, "is_directory", False):
            src_path = getattr(event, "src_path", None)
            if src_path:
                asyncio.run_coroutine_threadsafe(
                    soft_delete_vault_file(src_path), self._loop
                )

    def cancel_all_timers(self) -> None:
        """Cancel all pending debounce timers (Pitfall 6 — shutdown cleanup)."""
        with self._lock:
            for timer in self._timers.values():
                timer.cancel()
            self._timers.clear()


async def _amain() -> int:
    """Async entry point: configure logging, start inotify observer, handle signals."""
    configure_logging()
    log.info("watchdog_starting")

    loop = asyncio.get_running_loop()
    vault_root = os.environ.get("SMARTCOPILOT_VAULT_ROOT", "/vaults")
    debounce_ms = settings.vault_watch_debounce_ms

    log.info(
        "watchdog_config",
        vault_root=vault_root,
        debounce_ms=debounce_ms,
    )

    event_handler = VaultEventHandler(
        loop=loop,
        debounce_ms=debounce_ms,
        vault_root_path=vault_root,
    )
    observer = Observer()
    observer.schedule(event_handler, vault_root, recursive=True)
    observer.start()
    log.info("inotify_observer_started", watched=vault_root)

    stop_event = asyncio.Event()

    def _stop(signum: int, _frame: object) -> None:  # noqa: ARG001
        log.info("received_signal", signum=signum)
        stop_event.set()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    await stop_event.wait()

    # Pitfall 6: cancel all pending timers before stopping observer
    event_handler.cancel_all_timers()
    observer.stop()
    observer.join()
    log.info("watchdog_shutdown_complete")
    return 0


def main() -> int:
    return asyncio.run(_amain())


if __name__ == "__main__":
    sys.exit(main())
