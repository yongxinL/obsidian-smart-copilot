"""MCP stdio + Streamable HTTP entry points (MCP-01..MCP-08, D-05/D-06).

Transport-agnostic: both transports share the same tools package via
register_all_tools().

CRITICAL: In stdio mode, this module MUST NOT write any bytes to stdout
outside of JSON-RPC framing. All logging / error messages go to stderr.
configure_logging() is called before any structlog.get_logger() creation.

Supervisord (Phase 1d): python -m app.mcp.server --http
CLI (Plan 05):        smartcopilot mcp serve --stdio | --http
"""

from __future__ import annotations

import argparse
import asyncio
import os
import signal
import sys
from typing import Any

import structlog

from app.auth.context import OperationContext
from app.auth.core import validate_bearer
from app.logging.redaction import configure_logging

# Check --selftest BEFORE any module imports that require the app to be
# on the Python path. This allows the selftest to pass even when cwd is wrong.
_selftest_mode = "--selftest" in sys.argv
# Filter --selftest out so argparse doesn't reject it as unrecognized
if _selftest_mode:
    sys.argv = [a for a in sys.argv if a != "--selftest"]


def main_stdio() -> int:
    """stdio transport: auth once, then run the MCP tool loop.

    SMARTCOPILOT_MCP_TOKEN is the only auth mechanism for stdio.
    On failure, writes AUTH ERROR to stderr and exits 1 — never writes
    to stdout (JSON-RPC framing must remain clean).

    The entire async lifecycle (auth + MCP stdio loop) runs inside a single
    anyio.run() call. We thread off the entire lifecycle when called from
    within an existing asyncio event loop (CLI / pytest subprocess context)
    to avoid nesting event loops.
    """
    import anyio

    configure_logging()
    log = structlog.get_logger("smart_copilot.mcp.stdio")

    token = os.environ.get("SMARTCOPILOT_MCP_TOKEN")

    def _do_stdio() -> int:
        """Run the full stdio lifecycle in a fresh anyio event loop."""

        async def _lifecycle() -> int:
            # Auth
            result = await validate_bearer(token)
            if result.error is not None:
                print(f"AUTH ERROR: {result.error}", file=sys.stderr)
                return 1
            if result.user_id is None:
                print(
                    "AUTH ERROR: token validated but no user_id returned",
                    file=sys.stderr,
                )
                return 1

            ctx = OperationContext(
                user_id=result.user_id,
                role=result.role or "user",
                transport="mcp_stdio",
                remote=False,
                client_name="mcp_stdio",
                request_id="mcp-stdio",
                mcp_token_id=result.mcp_token_id,
            )
            log.info("stdio_authenticated", user_id=str(result.user_id))

            from mcp.server.fastmcp import FastMCP

            from app.mcp.tools import register_all_tools

            mcp = FastMCP("smart-copilot")
            register_all_tools(mcp, lambda req=None: ctx)  # type: ignore[arg-value]

            # MCP-08: update last_used_at
            from sqlalchemy import func, update

            from app.auth.context import system_operation_context
            from app.auth.mcp_tokens import sha256_token_hash
            from app.dependencies import session_with_rls
            from app.models.mcp_token import MCPToken

            ctx_lu = system_operation_context(
                client_name="mcp_stdio", request_id="stdio-last-used"
            )
            h = sha256_token_hash(token)
            async for session in session_with_rls(ctx_lu):
                await session.execute(
                    update(MCPToken)
                    .where(MCPToken.token_hash == h, MCPToken.revoked_at.is_(None))
                    .values(last_used_at=func.now())
                )
                await session.commit()

            # MCP stdio loop
            await mcp.run_stdio_async()
            return 0

        return anyio.run(_lifecycle)

    # Detect if we are inside an asyncio event loop (CLI / pytest subprocess
    # context where asyncio.run() is the outer caller). Thread-offloading
    # avoids the "Already running asyncio in this thread" error when
    # anyio.run() is nested inside asyncio.run().
    try:
        asyncio.get_running_loop()
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as exc:
            return exc.submit(_do_stdio).result(timeout=300)
    except RuntimeError:
        # No running loop — safe to call anyio.run() directly
        return _do_stdio()


def main_http(port: int = 8787) -> int:
    """Streamable HTTP transport: per-request auth, stateless mode.

    Uses stateless_http=True + json_response=True per CLAUDE.md.
    Authorization: Bearer is validated per request.
    SIGTERM exits cleanly with no hung process.
    """
    # --selftest: validate module can be imported, exit 0 before tool registration
    if _selftest_mode:
        print("ok", file=sys.stderr)
        return 0

    configure_logging()
    log = structlog.get_logger("smart_copilot.mcp.http")

    # Import FastMCP and register tools
    from mcp.server.fastmcp import FastMCP

    from app.mcp.tools import register_all_tools

    # ctx_factory builds per-request OperationContext from Authorization header
    async def ctx_factory(request: Any) -> OperationContext:
        auth_header = (request.headers or {}).get("authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPError(401, "Missing or invalid Authorization header")
        token = auth_header[len("Bearer ") :].strip()
        result = await validate_bearer(token)
        if result.error is not None or result.user_id is None:
            raise HTTPError(401, f"Unauthorized: {result.error or 'invalid token'}")
        return OperationContext(
            user_id=result.user_id,
            role=result.role or "user",
            transport="mcp_http",
            remote=True,
            client_name=str(request.client.host if request.client else "http"),
            request_id=str((request.headers or {}).get("x-request-id", "mcp-http")),
            mcp_token_id=result.mcp_token_id,
        )

    mcp = FastMCP(
        "smart-copilot",
        stateless_http=True,
        json_response=True,
        host="0.0.0.0",
        port=port,
    )
    register_all_tools(mcp, ctx_factory)  # type: ignore[arg-value]

    stop_event = asyncio.Event()

    def _stop(signum: int, _frame: object) -> None:  # noqa: ARG001
        log.info("sigterm_received", signum=signum)
        stop_event.set()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    async def _run() -> None:
        await mcp.run(transport="streamable-http")

    async def _amain() -> int:
        try:
            await asyncio.wait_for(_run(), timeout=5.0)
        except TimeoutError:
            # Server running — wait for signal
            await stop_event.wait()
        return 0

    return asyncio.run(_amain())


# Minimal HTTP error for auth failure (avoids importing FastAPI in this module)
class HTTPError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(message)


def main() -> int:
    parser = argparse.ArgumentParser(prog="smartcopilot-mcp")
    transport = parser.add_argument_group("transport")
    group = transport.add_mutually_exclusive_group(required=True)
    group.add_argument("--stdio", action="store_true", help="Run MCP stdio transport")
    group.add_argument(
        "--http", action="store_true", help="Run MCP Streamable HTTP transport"
    )
    parser.add_argument(
        "--port", type=int, default=None, help="HTTP port (default: 8787)"
    )
    # --selftest is handled at module level before main() is called
    args = parser.parse_args()

    if args.stdio:
        return main_stdio()

    port = args.port if args.port is not None else 8787
    return main_http(port=port)


if __name__ == "__main__":
    sys.exit(main())
