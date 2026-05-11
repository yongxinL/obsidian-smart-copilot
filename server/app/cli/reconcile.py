"""smartcopilot reconcile — synchronous vault reconciliation (D-13)."""

from __future__ import annotations

import argparse
import sys

from app.scheduler.jobs.reconcile_vault import reconcile_vault


def add_subparser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("reconcile", help="reconcile filesystem ↔ database (Phase 1c)")
    p.set_defaults(func=_handle_reconcile)


async def _handle_reconcile(args: argparse.Namespace) -> int:  # noqa: ARG001
    try:
        await reconcile_vault()
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print("reconcile_vault_complete: True")
    return 0
