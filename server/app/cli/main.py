"""smartcopilot CLI entrypoint (Phase 1d expansion of D-13)."""

from __future__ import annotations

import argparse
import asyncio
import sys

from app.cli import (
    check_resolvable,
    doctor,
    mcp_token,
    page,
    provider_key,
    reconcile,
    stats,
    user,
)

# Import check_resolvable under a valid Python identifier
check_resolvable_cmd = check_resolvable


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="smartcopilot")
    sub = p.add_subparsers(dest="command", required=True)

    user.add_subparser(sub)
    mcp_token.add_subparser(sub)  # registers `mcp token` AND (Phase 1d) `mcp serve`
    provider_key.add_subparser(sub)
    page.add_subparser(sub)  # NEW Phase 1d
    doctor.add_subparser(sub)  # NEW Phase 1d
    check_resolvable_cmd.add_subparser(sub)  # NEW Phase 1d
    reconcile.add_subparser(sub)  # NEW Phase 1d
    stats.add_subparser(sub)  # NEW Phase 1d

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return asyncio.run(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
