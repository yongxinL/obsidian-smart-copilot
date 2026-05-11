"""smartcopilot check-resolvable tests (CLI-03)."""

from __future__ import annotations

import subprocess
import sys
import tempfile

import pytest

pytestmark = pytest.mark.integration


def _run_check_resolvable(skills_dir: str | None = None) -> subprocess.CompletedProcess:
    env = __import__("os").environ.copy()
    env.setdefault(
        "SMARTCOPILOT_FERNET_KEY", "T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU="
    )
    env.setdefault(
        "JWT_SIGNING_KEY", "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa"
    )
    argv = [sys.executable, "-m", "app.cli.main", "check-resolvable"]
    if skills_dir:
        argv += ["--skills-dir", skills_dir]
    return subprocess.run(
        argv,
        env=env,
        capture_output=True,
        timeout=10,
        cwd="server",
    )


def test_check_resolvable_passes_when_dir_missing() -> None:
    proc = _run_check_resolvable(skills_dir="/nonexistent/path/zzz_01d05")
    assert proc.returncode == 0, proc.stderr.decode()
    assert b"no skills directory" in proc.stdout
    assert b"check: OK" in proc.stdout


def test_check_resolvable_passes_when_dir_empty() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        proc = _run_check_resolvable(skills_dir=tmp)
        assert proc.returncode == 0, proc.stderr.decode()
        assert b"check: OK" in proc.stdout
