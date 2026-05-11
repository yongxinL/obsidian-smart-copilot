"""Capability discovery — REST-05 / D-15 parity.

Single source of truth for the capability payload. Imported by:
  - server/app/mcp/tools/capability.py (capability_discovery MCP tool — Plan 02)
  - server/app/routes/vault.py          (GET /api/v1/capabilities — Plan 03)

NO FastAPI imports — this module is transport-agnostic per REST-06.
"""

from __future__ import annotations


def get_capabilities() -> dict:
    """Phase 1d capability payload (REST-05).

    transports         — Phase 1d wires both MCP transports.
    ingestion_limits   — empty in Phase 1d (ingest tools are stubs; D-04, D-05).
    clipboard_available — False; client-side feature, deferred to Phase 8.
    phase               — coarse phase identifier consumed by clients for
                          feature gating during the 1.x rollout.
    """
    return {
        "transports": ["stdio", "http"],
        "ingestion_limits": {},
        "clipboard_available": False,
        "phase": "1d",
    }