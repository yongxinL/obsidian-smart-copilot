"""MCP tools package — D-06 per-domain organisation.

Phase 1d ships REAL implementations for brain.* and capability_discovery.
All other tool modules contain STRUCTURED STUBS returning the D-05 payload.
Both transports (stdio + HTTP) call register_all_tools(mcp, ctx_factory)
to wire the same Pydantic-typed surface.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.auth.context import OperationContext


def register_all_tools(
    mcp: Any,
    ctx_factory: Callable[..., OperationContext],
) -> None:
    """Register every Phase 1d tool on the FastMCP server.

    ctx_factory is invoked per-tool-call: it returns the OperationContext for
    the current caller. For stdio it returns the same module-level ctx; for
    HTTP it builds a per-request ctx from Authorization headers.
    """
    from app.mcp.tools import (
        brain,
        capability,
        ingest,
        enrich,
        recipe,
        skill,
        jobs,
        maintain,
        entity,
        graph,
    )

    brain.register(mcp, ctx_factory)
    capability.register(mcp, ctx_factory)
    ingest.register(mcp, ctx_factory)
    enrich.register(mcp, ctx_factory)
    recipe.register(mcp, ctx_factory)
    skill.register(mcp, ctx_factory)
    jobs.register(mcp, ctx_factory)
    maintain.register(mcp, ctx_factory)
    entity.register(mcp, ctx_factory)
    graph.register(mcp, ctx_factory)