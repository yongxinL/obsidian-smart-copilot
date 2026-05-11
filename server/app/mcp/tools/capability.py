"""capability_discovery MCP tool — REST-05 parity (D-15, 01d-CONTEXT.md).

Imported by: register_all_tools() in __init__.py.

Shares get_capabilities() with server/app/routes/vault.py (Plan 03) — REST-05
invariant: single source of truth, no duplication.
"""
from __future__ import annotations

from collections.abc import Callable

from app.auth.context import OperationContext
from app.services.capabilities import get_capabilities


def register(mcp: Any, ctx_factory: Callable[..., OperationContext]) -> None:
    """Register capability_discovery MCP tool."""

    @mcp.tool(
        name="capability_discovery",
        description="Return server capabilities: transports, ingestion limits, "
        "clipboard availability, and phase identifier. Identical to "
        "GET /api/v1/capabilities REST endpoint.",
    )
    async def capability_discovery() -> dict:
        _ = ctx_factory()  # noqa: F841 — auth still required; value is ignored
        return get_capabilities()