"""MCP HTTP server entry point.

Phase 1a: STUB — starts, logs a banner, blocks until SIGTERM. Real MCP
Streamable HTTP implementation lands in Phase 1d (REQ MCP-01..MCP-08).
Supervisord program priority 30 invokes this as: python -m app.mcp.server --http
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [mcp.server] %(message)s")
log = logging.getLogger("smart_copilot.mcp")

_running = True


def _handle_signal(signum: int, frame) -> None:  # noqa: ARG001
    global _running
    log.info("received signal %s; shutting down", signum)
    _running = False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Smart Copilot MCP server (Phase 1a stub)"
    )
    parser.add_argument("--http", action="store_true", help="HTTP mode (Phase 1d)")
    parser.add_argument("--stdio", action="store_true", help="stdio mode (Phase 1d)")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    log.info(
        "STUB starting (mode=%s, port=%d); real impl in Phase 1d",
        "http" if args.http else "stdio",
        args.port,
    )
    while _running:
        time.sleep(1)
    log.info("STUB exiting cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
