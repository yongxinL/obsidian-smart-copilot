"""Vault watchdog process entry point.

Phase 1a: STUB — starts, logs a banner, blocks until SIGTERM. Real watchdog
inotify -> asyncio handoff lands in Phase 1c (REQ VAULT-09 / IDX-01).
Supervisord program priority 50 invokes this as: python -m app.vault.watcher
"""

from __future__ import annotations

import logging
import signal
import sys
import time

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [vault.watcher] %(message)s"
)
log = logging.getLogger("smart_copilot.vault")

_running = True


def _handle_signal(signum: int, frame) -> None:  # noqa: ARG001
    global _running
    log.info("received signal %s; shutting down", signum)
    _running = False


def main() -> int:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    log.info("STUB starting; real watchdog impl in Phase 1c")
    while _running:
        time.sleep(1)
    log.info("STUB exiting cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
