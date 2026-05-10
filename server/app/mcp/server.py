"""MCP HTTP / stdio entry point.

Phase 1b: minimal stub. Imports `validate_bearer` from app.auth.core to prove
the D-21 "MCP HTTP shares auth_core by import" seam is in place. Phase 1d wires
the actual MCP SDK + AuthSettings + Streamable HTTP server.

Supervisord priority 30 invokes:
    python -m app.mcp.server --http
Until Phase 1d ships, that exits non-zero with NotImplementedError — which
is the desired behavior (the MCP HTTP process is not part of the Phase 1b
success criteria; it must just not break the container BUILD/IMPORT).
"""
from __future__ import annotations

from app.auth.core import validate_bearer  # noqa: F401 — D-21 seam


def main_http() -> int:
    raise NotImplementedError("Phase 1d wires MCP SDK")


def main_stdio() -> int:
    raise NotImplementedError("Phase 1d wires MCP SDK")


if __name__ == "__main__":
    import sys
    sys.exit(main_http())