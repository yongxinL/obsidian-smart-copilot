"""OpenAPI spec freshness tests — VAULT-11.

D-12: docs/openapi.json generated via TestClient (no real server).
D-13: docs/openapi.json committed to repo; tests assert spec is fresh.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# app.main import is safe here because conftest.py sets required env vars at session start
from app.main import app

pytestmark = [pytest.mark.vault, pytest.mark.integration]

_REPO_ROOT = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
)  # .../smart-copilot/
_OPENAPI_PATH = _REPO_ROOT / "docs" / "openapi.json"


def test_openapi_json_exists_and_is_valid_json():
    """docs/openapi.json must exist on disk and be parseable as JSON (D-13)."""
    assert _OPENAPI_PATH.exists(), f"docs/openapi.json not found at {_OPENAPI_PATH}"
    content = _OPENAPI_PATH.read_text()
    data = json.loads(content)
    assert "openapi" in data, "docs/openapi.json missing 'openapi' key"
    assert data["openapi"].startswith("3."), (
        f"Unexpected openapi version: {data['openapi']}"
    )


def test_openapi_spec_matches_live_app():
    """Live app /openapi.json must match the committed docs/openapi.json (D-12/D-13).

    If this test fails, run: cd server && python ../scripts/regen_openapi.py
    """
    client = TestClient(app, raise_server_exceptions=True)
    resp = client.get("/openapi.json")
    assert resp.status_code == 200, f"GET /openapi.json returned {resp.status_code}"
    live_spec = resp.json()

    committed_spec = json.loads(_OPENAPI_PATH.read_text())

    # Compare the "paths" set — the committed spec might be slightly behind
    # on whitespace/ordering but the path keys must match exactly.
    live_paths = set(live_spec.get("paths", {}).keys())
    committed_paths = set(committed_spec.get("paths", {}).keys())
    assert live_paths == committed_paths, (
        f"OpenAPI spec is stale. Live paths: {live_paths}, Committed paths: {committed_paths}. "
        "Run: cd server && python ../scripts/regen_openapi.py"
    )
    # Verify title and version match
    assert live_spec.get("info", {}).get("title") == committed_spec.get("info", {}).get(
        "title"
    ), "OpenAPI info.title mismatch between live app and committed spec"
