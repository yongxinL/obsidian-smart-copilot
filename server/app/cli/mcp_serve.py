"""smartcopilot mcp serve — wrapper that dispatches to app.mcp.server (D-13).

Note: this integrates with the existing `mcp` subparser owned by mcp_token.py.
Phase 1b registered `mcp token ...`; Phase 1d adds `mcp serve ...` to the
SAME `mcp` parent. We integrate via add_serve_to_mcp_subparser() which is
called from mcp_token.py after it creates the `mcp` subparser.
"""

from __future__ import annotations

import argparse
import sys

from app.mcp import server as mcp_server
from app.mcp.server import (
    main_stdio,  # noqa: E402 — imported after asyncio, not circular
)


def add_serve_to_mcp_subparser(mcp_subsubparsers: argparse._SubParsersAction) -> None:
    """Register `serve` under the existing `mcp` subparser owned by mcp_token.py."""
    sv = mcp_subsubparsers.add_parser(
        "serve", help="run the MCP server (stdio or HTTP)"
    )
    grp = sv.add_mutually_exclusive_group(required=True)
    grp.add_argument(
        "--stdio", action="store_true", help="stdio transport (Claude Code, etc.)"
    )
    grp.add_argument("--http", action="store_true", help="Streamable HTTP transport")
    sv.add_argument("--port", type=int, default=8787, help="HTTP port (default 8787)")
    sv.set_defaults(func=_handle_mcp_serve)


async def _handle_mcp_serve(args: argparse.Namespace) -> int:
    if args.stdio:
        return main_stdio()
    if args.http:
        # Replace sys.argv so the embedded argparse in mcp.server picks up --port.
        sys.argv = ["app.mcp.server", "--http", "--port", str(args.port)]
        return mcp_server.main_http()
    print("error: must specify --stdio or --http", file=sys.stderr)
    return 2
