"""Repository-wide security invariant tests (Landmine #1, #2, #4, #5; D-17, D-28).

Each test runs grep -r over server/app/ and asserts the bad pattern is absent.
CI runs these tests on every PR.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.auth, pytest.mark.unit]

SERVER_APP = Path(__file__).resolve().parents[2]  # server/app


def _grep(pattern: str, *, ext: str = "py") -> list[str]:
    """Recursive grep over server/app/. Returns matching lines."""
    try:
        result = subprocess.run(
            ["grep", "-rEn", "--include", f"*.{ext}", pattern, str(SERVER_APP)],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        pytest.skip("grep not available")
    return result.stdout.strip().splitlines()


# ---- Landmine #2: jwt.decode without explicit algorithms allowlist ----


def test_no_jwt_decode_without_algorithms_list() -> None:
    """Every jwt.decode call MUST include algorithms=[. CVE-2024-33663 + CVE-2025-61152."""
    hits = _grep(r"jwt\.decode\(")
    # Filter: lines that have jwt.decode( BUT lack algorithms=[
    bad = [
        line
        for line in hits
        if "algorithms=[" not in line
        # exclude test files that narrate this pattern
        and "test_security_invariants.py" not in line
        and "test_jwt_tokens.py" not in line
    ]
    assert not bad, "jwt.decode without algorithms=[ — Landmine #2:\n" + "\n".join(bad)


# ---- Landmine #4: Fernet ttl= ----


def test_no_fernet_decrypt_with_ttl() -> None:
    """Provider keys are at-rest with no expiry; ttl= would silently expire them."""
    hits = _grep(r"\.decrypt\([^)]*ttl=")
    bad = [line for line in hits if "test_" not in line]
    assert not bad, "Fernet.decrypt(...,ttl=) — Landmine #4:\n" + "\n".join(bad)


# ---- Landmine #5: SET ... = $1 binding (illegal SQL) ----


def test_no_text_set_app_with_bind() -> None:
    """SET ... = $1 is illegal SQL; use set_config(name, value, false) instead."""
    hits = _grep(r'text\("SET app\.')
    bad = [line for line in hits if "test_" not in line]
    assert not bad, 'text("SET app.* — Landmine #5:\n' + "\n".join(bad)


# ---- D-28: encrypted_key Pydantic field MUST have Field(exclude=True) ----


def test_encrypted_key_is_field_excluded() -> None:
    """Every Pydantic model declaring encrypted_key must use Field(exclude=True)."""
    hits = _grep(r"encrypted_key:.*bytes")
    bad: list[str] = []
    for hit in hits:
        # Skip ORM model declarations (mapped_column-based — not Pydantic)
        if "mapped_column" in hit:
            continue
        # The line itself must contain Field(exclude=True)
        if "Field(exclude=True)" not in hit:
            bad.append(hit)
    assert not bad, "Pydantic encrypted_key without Field(exclude=True) — D-28:\n" + "\n".join(bad)


# ---- D-17: services/* must NOT import FastAPI types ----


def test_services_does_not_import_fastapi() -> None:
    result = subprocess.run(
        [
            "grep",
            "-rEn",
            r"^(from|import) (fastapi|starlette)",
            str(SERVER_APP / "services"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    bad = result.stdout.strip().splitlines()
    assert not bad, "services/ MUST NOT import FastAPI/starlette — D-17:\n" + "\n".join(bad)


# ---- D-17: auth/{context,core,password,tokens,mcp_tokens,audit}.py must NOT import FastAPI ----


def test_pure_auth_modules_do_not_import_fastapi() -> None:
    targets = ["context.py", "core.py", "password.py", "tokens.py", "mcp_tokens.py", "audit.py"]
    bad: list[str] = []
    for t in targets:
        f = SERVER_APP / "auth" / t
        if not f.exists():
            continue
        content = f.read_text()
        for line in content.splitlines():
            if line.startswith("from fastapi") or line.startswith("import fastapi") or line.startswith("from starlette") or line.startswith("import starlette"):
                bad.append(f"{f}: {line}")
    assert not bad, "pure auth/* modules MUST NOT import FastAPI/starlette — D-17:\n" + "\n".join(bad)


# ---- Phase 1b success criterion #4 — main.py startup-fail source check ----


def test_main_has_startup_fail_check() -> None:
    """Phase 1b success criterion #4 — main.py MUST call fernet() and check jwt_signing_key in lifespan."""
    main_py = (SERVER_APP / "main.py").read_text()
    assert "FernetKeyMissing" in main_py
    assert "jwt_signing_key" in main_py
    assert "sys.exit(1)" in main_py
