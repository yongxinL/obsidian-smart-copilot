"""brain.entity stubs — D-05 not_implemented payload, registered + discoverable.

Phase 1d does NOT implement these tools; they ship as stubs so MCP clients can
discover the full surface and surface a useful error rather than NOT_FOUND.
NOT_FOUND is reserved for unregistered tools (D-05).
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.auth.context import OperationContext

_AVAILABLE_IN_PHASE = "3"

_TOOLS: tuple[tuple[str, str], ...] = (
    (
        "brain.entity.get",
        "Retrieve a typed entity (person, company, concept) by ID. "
        "Available in Phase 3.",
    ),
    (
        "brain.entity.merge",
        "Merge two entity records (duplicate detection). "
        "Available in Phase 3.",
    ),
    (
        "brain.entity.list",
        "List entities of a given type with optional filters. "
        "Available in Phase 3.",
    ),
)


def _stub() -> dict:
    return {
        "error": {
            "code": "not_implemented",
            "message": f"tool available in Phase {_AVAILABLE_IN_PHASE}",
            "available_in_phase": _AVAILABLE_IN_PHASE,
        }
    }


def register(mcp: Any, ctx_factory: Callable[..., OperationContext]) -> None:  # noqa: ARG001
    for name, desc in _TOOLS:

        @mcp.tool(name=name, description=desc)
        async def _stub_tool(**kwargs: Any) -> dict:  # noqa: ARG001
            return _stub()