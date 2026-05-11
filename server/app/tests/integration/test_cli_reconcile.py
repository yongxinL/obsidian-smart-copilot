"""smartcopilot reconcile tests (CLI-01)."""

from __future__ import annotations

import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration


def _env(db_url: str | None = None) -> dict:
    env = __import__("os").environ.copy()
    env.setdefault(
        "SMARTCOPILOT_FERNET_KEY", "T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU="
    )
    env.setdefault(
        "JWT_SIGNING_KEY", "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa"
    )
    if db_url:
        env["DATABASE_URL"] = db_url
    return env


def test_reconcile_runs_and_exits_0(postgres_container) -> None:
    sync_url = postgres_container.get_connection_url()
    raw_dsn = sync_url.replace("postgresql+psycopg2://", "postgresql://", 1)
    db_url = raw_dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
    proc = subprocess.run(
        [sys.executable, "-m", "app.cli.main", "reconcile"],
        env=_env(db_url=db_url),
        capture_output=True,
        timeout=30,
        cwd="server",
    )
    assert proc.returncode == 0, f"stderr={proc.stderr.decode()!r}"
    assert b"reconcile_vault_complete" in proc.stdout
