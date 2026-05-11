"""Regenerate docs/openapi.json via FastAPI TestClient (D-12/D-13).

Requires SMARTCOPILOT_FERNET_KEY and JWT_SIGNING_KEY in environment.
These must match the format expected by app.main startup guards.

Run:
    cd server && SMARTCOPILOT_FERNET_KEY=... JWT_SIGNING_KEY=... python ../scripts/regen_openapi.py

Pre-commit hook: see .pre-commit-config.yaml (repo root) — triggers on route/service/model changes.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Pitfall 7 in RESEARCH.md: check required env vars BEFORE importing app.main.
# The startup guard (_fail_startup_if_missing_secrets) runs at import time.
_REQUIRED_VARS = ("SMARTCOPILOT_FERNET_KEY", "JWT_SIGNING_KEY")
for _var in _REQUIRED_VARS:
    if not os.environ.get(_var):
        print(
            f"ERROR: {_var} not set. "
            "Set required env vars before running this script.\n"
            "See .env.example for values.",
            file=sys.stderr,
        )
        sys.exit(1)

# Must import AFTER env var checks above.
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parent.parent  # project root (smart-copilot/)
_OUT_PATH = _REPO_ROOT / "docs" / "openapi.json"

client = TestClient(app, raise_server_exceptions=True)
resp = client.get("/openapi.json")
if resp.status_code != 200:
    print(
        f"ERROR: GET /openapi.json returned {resp.status_code}: {resp.text}",
        file=sys.stderr,
    )
    sys.exit(1)

_OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
_OUT_PATH.write_text(json.dumps(resp.json(), indent=2) + "\n")
print(f"Written: {_OUT_PATH}")
