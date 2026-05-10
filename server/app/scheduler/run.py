"""APScheduler process entry point.

Phase 1a: STUB — starts, logs a banner, blocks until SIGTERM. Real APScheduler
3.x SQLAlchemyJobStore wiring lands in Phase 4. Supervisord program priority
40 invokes this as: python -m app.scheduler.run
"""

from __future__ import annotations

import logging
import signal
import sys
import time

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [scheduler.run] %(message)s"
)
log = logging.getLogger("smart_copilot.scheduler")

_running = True


def _handle_signal(signum: int, frame) -> None:  # noqa: ARG001
    global _running
    log.info("received signal %s; shutting down", signum)
    _running = False


def main() -> int:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    log.info("STUB starting; real APScheduler 3.x impl in Phase 4")
    while _running:
        time.sleep(1)
    log.info("STUB exiting cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
