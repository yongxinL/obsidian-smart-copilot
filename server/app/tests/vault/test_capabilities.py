"""Unit tests for services/capabilities.py — REST-05 parity (Plan 01)."""

from __future__ import annotations

import pytest

from app.services.capabilities import get_capabilities

pytestmark = pytest.mark.unit


def test_get_capabilities_returns_phase_1d_payload() -> None:
    """get_capabilities() returns the Phase 1d capability dict."""
    payload = get_capabilities()
    assert payload == {
        "transports": ["stdio", "http"],
        "ingestion_limits": {},
        "clipboard_available": False,
        "phase": "1d",
    }


def test_get_capabilities_does_not_import_fastapi() -> None:
    """Module has no runtime import of fastapi/starlette."""
    import ast
    import app.services.capabilities as cap_module

    src = open(cap_module.__file__).read()
    tree = ast.parse(src, filename=cap_module.__file__)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name.split(".")[0]
                assert name not in ("fastapi", "starlette"), f"unexpected import: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            name = (node.module or "").split(".")[0]
            assert name not in ("fastapi", "starlette"), f"unexpected from import: {node.module}"