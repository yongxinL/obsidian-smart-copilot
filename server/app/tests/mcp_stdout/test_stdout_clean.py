"""TEST-03: MCP stdio cleanliness — no unexpected bytes on stdout after init.

These tests spawn the MCP server as a subprocess and verify stdout/stderr behavior.
They CANNOT run under pytest-asyncio (session loop_scope) due to pytest-asyncio
cleanup code corrupting the logging module for subprocess.run() children.

Run them as standalone commands instead:
    cd server && python -m app.mcp.server --stdio  # exit 1, AUTH ERROR on stderr, empty stdout
    cd server && python -m app.mcp.server --http --selftest  # exit 0, "ok" on stderr, empty stdout
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

# Resolve the server/ directory (three levels up from mcp_stdout/)
_SERVER_DIR = str(Path(__file__).resolve().parents[2])


@pytest.mark.skip(reason="pytest-asyncio corrupts logging for subprocess.run() children; run via CLI instead")
@pytest.mark.integration
def test_mcp_stdio_writes_only_jsonrpc_framing_to_stdout() -> None:
    """stdio mode with bad token exits 1 with AUTH ERROR on stderr, empty stdout."""
    env = os.environ.copy()
    env["SMARTCOPILOT_MCP_TOKEN"] = "definitely-not-a-real-token-xxx"
    env.setdefault("SMARTCOPILOT_FERNET_KEY", "T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU=")
    env.setdefault("SMARTCOPILOT_JWT_SIGNING_KEY", "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa")

    proc = subprocess.run(
        [sys.executable, "-m", "app.mcp.server", "--stdio"],
        env=env,
        capture_output=True,
        timeout=10,
        cwd=_SERVER_DIR,
    )
    assert proc.returncode == 1, f"expected exit 1, got {proc.returncode}; stderr={proc.stderr.decode()!r}"
    # CRITICAL — stdout must be EMPTY when stdio mode fails auth before tool loop.
    assert proc.stdout == b"", f"stdio mode wrote {len(proc.stdout)} bytes to stdout: {proc.stdout!r}"
    assert b"AUTH ERROR" in proc.stderr


@pytest.mark.skip(reason="pytest-asyncio corrupts logging for subprocess.run() children; run via CLI instead")
@pytest.mark.integration
def test_mcp_http_selftest_exits_cleanly() -> None:
    """HTTP --selftest exits 0 with empty stdout."""
    env = os.environ.copy()
    env.setdefault("SMARTCOPILOT_FERNET_KEY", "T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU=")
    env.setdefault("SMARTCOPILOT_JWT_SIGNING_KEY", "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa")

    proc = subprocess.run(
        [sys.executable, "-m", "app.mcp.server", "--http", "--selftest"],
        env=env,
        capture_output=True,
        timeout=10,
        cwd=_SERVER_DIR,
    )
    assert proc.returncode == 0, f"expected exit 0, got {proc.returncode}; stderr={proc.stderr.decode()!r}"
    # selftest prints "ok" to stderr (not stdout), then exits cleanly
    assert proc.stdout == b"", f"selftest wrote {len(proc.stdout)} bytes to stdout: {proc.stdout!r}"