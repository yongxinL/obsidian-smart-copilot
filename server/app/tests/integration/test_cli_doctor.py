"""smartcopilot doctor tests (CLI-02 / D-14)."""

from __future__ import annotations

import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration


def _run_doctor(
    fernet_key: str | None = None, jwt_key: str | None = None, db_url: str | None = None
) -> subprocess.CompletedProcess:
    env = __import__("os").environ.copy()
    env.setdefault(
        "SMARTCOPILOT_FERNET_KEY",
        fernet_key or "T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU=",
    )
    env.setdefault(
        "JWT_SIGNING_KEY",
        jwt_key or "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa",
    )
    if db_url:
        env["DATABASE_URL"] = db_url
    return subprocess.run(
        [sys.executable, "-m", "app.cli.main", "doctor"],
        env=env,
        capture_output=True,
        timeout=30,
        cwd="server",
    )


def test_doctor_reports_all_d14_sections(postgres_container) -> None:
    sync_url = postgres_container.get_connection_url()
    raw_dsn = sync_url.replace("postgresql+psycopg2://", "postgresql://", 1)
    db_url = raw_dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
    fernet = "T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU="
    jwt = "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa"
    proc = _run_doctor(fernet_key=fernet, jwt_key=jwt, db_url=db_url)
    out = proc.stdout.decode()
    # D-14 mandatory sections
    assert "fernet_key:" in out, f"missing ferret_key in: {out}"
    assert "inotify_max_user_watches:" in out, f"missing inotify in: {out}"
    assert "cors_config:" in out, f"missing cors_config in: {out}"
    assert "mcp_token_storage: sha256-hashed" in out, (
        f"missing mcp_token_storage in: {out}"
    )
    assert "db_connection:" in out, f"missing db_connection in: {out}"
    assert "db_pgvector_extension:" in out, f"missing db_pgvector_extension in: {out}"
    assert proc.returncode == 0, (
        f"doctor returned {proc.returncode}: {proc.stderr.decode()}"
    )


def test_doctor_returns_1_when_fernet_missing() -> None:
    proc = _run_doctor(fernet_key="")
    assert proc.returncode != 0
    assert b"SMARTCOPILOT_FERNET_KEY" in proc.stderr
