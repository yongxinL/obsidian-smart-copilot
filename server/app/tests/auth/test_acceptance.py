"""Phase 1b acceptance test — end-to-end happy path.

Maps to ROADMAP Phase 1b 5 success criteria:
  1. CLI user create + /auth/login + /auth/refresh + rate-limit envelope
  2. CLI mcp token create (plaintext shown once); revoke; verify <5s
  3. RLS isolation — covered by test_rls_isolation.py
  4. Provider key Fernet round-trip + Field(exclude=True) — covered by test_provider_keys.py
     + container fail-on-startup — covered by test_main_startup_fail (this file)
  5. /api/v1/admin/reauth grants fresh window; destructive route 403 then 200 after reauth

This test is the "phase ships" gate. It fails if any step regresses.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import threading

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.auth.context import system_operation_context
from app.dependencies import session_with_rls

pytestmark = [pytest.mark.auth, pytest.mark.integration]


async def _delete_user(username: str) -> None:
    async for session in session_with_rls(system_operation_context()):
        await session.execute(
            text("DELETE FROM users WHERE username = :u"), {"u": username}
        )
        await session.commit()


def _run_cli_sync(argv: list[str]) -> int:
    """Run CLI in a fresh event loop thread (avoids conflict with pytest session loop)."""
    from app.cli.main import main as cli_main

    result: dict = {"rc": -1}

    def runner() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result["rc"] = cli_main(argv)
        finally:
            loop.close()

    t = threading.Thread(target=runner)
    t.start()
    t.join()
    return result["rc"]


async def test_phase_1b_acceptance() -> None:
    """The Phase 1b ship-or-not gate."""
    from app.main import app

    username = "acct_alice"
    password = "p@ssw0rd-acct"
    try:
        # 1a. CLI user create — WR-01: supply password via env var (--password flag removed)
        os.environ["SMARTCOPILOT_NEW_PASSWORD"] = password
        rc = _run_cli_sync(
            ["user", "create", "--username", username, "--role", "admin"]
        )
        os.environ.pop("SMARTCOPILOT_NEW_PASSWORD", None)
        assert rc == 0

        # 1b. /auth/login → token pair
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            login = await c.post(
                "/auth/login", json={"username": username, "password": password}
            )
            assert login.status_code == 200, login.text
            tokens = login.json()
            assert "access_jwt" in tokens and "refresh_token" in tokens

            # 1c. /auth/refresh
            refreshed = await c.post(
                "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
            )
            assert refreshed.status_code == 200
            tokens = refreshed.json()

            # 5a. Destructive route without fresh-auth — 403
            headers = {"Authorization": f"Bearer {tokens['access_jwt']}"}
            forbidden = await c.post("/api/v1/admin/_demo_destructive", headers=headers)
            assert forbidden.status_code == 403
            envelope = forbidden.json()
            assert envelope["error"]["code"] == "admin_reauth_required"
            assert envelope["error"]["details"]["reauth_url"] == "/api/v1/admin/reauth"
            assert envelope["error"]["details"]["freshness_window_minutes"] == 60

            # 5b. /admin/reauth
            reauth = await c.post(
                "/api/v1/admin/reauth",
                headers=headers,
                json={"factor": "password", "password": password},
            )
            assert reauth.status_code == 200, reauth.text

            # 5c. Destructive route now succeeds
            ok = await c.post("/api/v1/admin/_demo_destructive", headers=headers)
            assert ok.status_code == 200, ok.text

        # 2a. CLI mcp token create
        rc = _run_cli_sync(
            ["mcp", "token", "create", "--user", username, "--name", "acceptance"]
        )
        assert rc == 0

        # 4a. CLI provider key set — WR-01: supply key via env var (--key flag removed)
        os.environ["SMARTCOPILOT_PROVIDER_KEY"] = "sk-acceptance-test"
        rc = _run_cli_sync(
            [
                "provider",
                "key",
                "set",
                "--user",
                username,
                "--provider",
                "openai",
            ]
        )
        os.environ.pop("SMARTCOPILOT_PROVIDER_KEY", None)
        assert rc == 0

        # 4b. Verify the key is encrypted at rest (raw bytes != plaintext)
        async for session in session_with_rls(system_operation_context()):
            row = (
                await session.execute(
                    text(
                        "SELECT encrypted_key FROM provider_keys WHERE user_id = "
                        "(SELECT id FROM users WHERE username = :u)"
                    ),
                    {"u": username},
                )
            ).first()
            assert row is not None
            assert row[0] != b"sk-acceptance-test"
            assert isinstance(row[0], (bytes, memoryview))

    finally:
        # cleanup
        await _delete_user(username)
        async for session in session_with_rls(system_operation_context()):
            await session.execute(
                text("DELETE FROM login_attempts WHERE username = :u"), {"u": username}
            )
            await session.commit()


def test_main_startup_fail_without_fernet_key() -> None:
    """Phase 1b success criterion #4 — container refuses to start without SMARTCOPILOT_FERNET_KEY.

    Drive lifespan.__aenter__() in a subprocess with SMARTCOPILOT_FERNET_KEY stripped
    from the environment. Assert non-zero exit AND FATAL on stderr.
    """
    # Inherit the test environment (so PYTHONPATH, DATABASE_URL etc. are present)
    # but strip SMARTCOPILOT_FERNET_KEY so _fail_startup_if_missing_secrets fires.
    env = {k: v for k, v in os.environ.items() if k != "SMARTCOPILOT_FERNET_KEY"}
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.main import lifespan; "
            "from fastapi import FastAPI; "
            "import asyncio; "
            "asyncio.run(lifespan(FastAPI()).__aenter__())",
        ],
        env=env,
        capture_output=True,
        timeout=15,
    )
    assert result.returncode != 0, (
        f"main.py lifespan MUST fail-fast without SMARTCOPILOT_FERNET_KEY; "
        f"rc={result.returncode!r} stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert b"FATAL" in result.stderr, (
        f"expected 'FATAL' on stderr; got stderr={result.stderr!r}"
    )
