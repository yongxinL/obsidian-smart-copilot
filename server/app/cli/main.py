"""smartcopilot CLI entrypoint (Phase 1b stub).

Subcommands:
  user create
  mcp token create / list / revoke
  provider key set

Each subcommand builds an OperationContext(transport='cli', remote=False, ...)
and calls services/* via session_with_rls. The full Phase 1d CLI extends this.
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from app.cli import mcp_token as mcp_token_cmd
from app.cli import provider_key as provider_key_cmd
from app.cli import user as user_cmd


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="smartcopilot")
    sub = p.add_subparsers(dest="command", required=True)

    user_cmd.add_subparser(sub)
    mcp_token_cmd.add_subparser(sub)
    provider_key_cmd.add_subparser(sub)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return asyncio.run(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
