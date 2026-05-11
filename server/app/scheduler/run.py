"""APScheduler process entry point.

Phase 1b: registers the hourly prune_login_attempts job (D-09).
Phase 4 will swap the default in-memory store for SQLAlchemyJobStore for
cross-restart durability. Supervisord program priority 40 invokes this as:
    python -m app.scheduler.run
"""

from __future__ import annotations

import asyncio
import signal
import sys

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.scheduler.jobs.prune_login_attempts import prune_login_attempts
from app.scheduler.jobs.reconcile_vault import reconcile_vault


async def _amain() -> int:
    import logging

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [scheduler.run] %(message)s"
    )
    log = logging.getLogger("smart_copilot.scheduler")
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        prune_login_attempts,
        "interval",
        hours=1,
        id="prune_login_attempts",
        replace_existing=True,
        coalesce=True,
    )
    scheduler.add_job(
        reconcile_vault,
        "interval",
        minutes=5,
        id="reconcile_vault",
        replace_existing=True,
        coalesce=True,  # D-08: prevent pile-up after outage
        max_instances=1,  # D-08: only one reconciliation at a time
    )
    scheduler.start()
    log.info(
        "scheduler started",
        jobs=["prune_login_attempts (hourly)", "reconcile_vault (5-min)"],
    )
    stop_event = asyncio.Event()

    def _stop(signum, _frame):  # noqa: ARG001
        log.info("received signal %s; shutting down", signum)
        stop_event.set()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    await stop_event.wait()
    scheduler.shutdown(wait=False)
    log.info("scheduler shutdown complete")
    return 0


def main() -> int:
    return asyncio.run(_amain())


if __name__ == "__main__":
    sys.exit(main())
