"""smartcopilot mcp serve tests (D-13 / CLI-01)."""

from __future__ import annotations

import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration


def _env(extra: dict | None = None) -> dict:
    env = __import__("os").environ.copy()
    env.setdefault(
        "SMARTCOPILOT_FERNET_KEY", "T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU="
    )
    env.setdefault(
        "JWT_SIGNING_KEY", "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa"
    )
    if extra:
        env.update(extra)
    return env


def test_smartcopilot_help_lists_all_subcommands() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "app.cli.main", "--help"],
        env=_env(),
        capture_output=True,
        timeout=10,
        cwd="server",
    )
    out = proc.stdout.decode()
    for token in (
        "user",
        "mcp",
        "provider_key",
        "page",
        "doctor",
        "check-resolvable",
        "reconcile",
        "stats",
    ):
        assert token in out, f"missing subcommand in --help: {token}"
    assert proc.returncode == 0


def test_mcp_serve_stdio_with_bad_token_exits_1() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "app.cli.main", "mcp", "serve", "--stdio"],
        env=_env({"SMARTCOPILOT_MCP_TOKEN": "definitely-not-a-real-token-zzz"}),
        capture_output=True,
        timeout=10,
        cwd="server",
    )
    assert proc.returncode == 1
    assert b"AUTH ERROR" in proc.stderr
    # Per TEST-03: stdout must be empty (stdio clean before tool loop).
    assert proc.stdout == b""


def test_mcp_serve_requires_transport_flag() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "app.cli.main", "mcp", "serve"],
        env=_env(),
        capture_output=True,
        timeout=10,
        cwd="server",
    )
    # argparse mutually_exclusive_group(required=True) → exit code 2.
    assert proc.returncode == 2
