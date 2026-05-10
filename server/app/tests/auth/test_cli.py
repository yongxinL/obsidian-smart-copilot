"""CLI integration tests — drives the smartcopilot binary via app.cli.main:main."""

from __future__ import annotations

import asyncio
import threading

import pytest
from sqlalchemy import text

from app.auth.context import system_operation_context
from app.cli.main import main as cli_main
from app.dependencies import session_with_rls

pytestmark = [pytest.mark.auth, pytest.mark.integration]


async def _delete_user(username: str) -> None:
    async for session in session_with_rls(system_operation_context()):
        await session.execute(
            text("DELETE FROM users WHERE username = :u"), {"u": username}
        )
        await session.commit()


def _run_cli(argv: list[str], capsys) -> tuple[int, str]:
    """Run CLI in a fresh event loop thread (avoids asyncio.run conflict with session loop)."""
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
    captured = capsys.readouterr()
    return result["rc"], captured.out


def test_cli_user_create_succeeds(capsys, monkeypatch) -> None:
    # WR-01: supply password via env var (--password flag removed)
    monkeypatch.setenv("SMARTCOPILOT_NEW_PASSWORD", "p@ss")
    try:
        rc, out = _run_cli(
            ["user", "create", "--username", "cli_alice", "--role", "admin"],
            capsys,
        )
        assert rc == 0
        assert "created user cli_alice" in out
    finally:
        asyncio.get_event_loop().run_until_complete(_delete_user("cli_alice"))


def test_cli_user_create_rejects_duplicate(capsys, monkeypatch) -> None:
    # WR-01: supply password via env var (--password flag removed)
    monkeypatch.setenv("SMARTCOPILOT_NEW_PASSWORD", "p")
    # First create
    _run_cli(
        ["user", "create", "--username", "cli_dup"],
        capsys,
    )
    try:
        rc, out = _run_cli(
            ["user", "create", "--username", "cli_dup"],
            capsys,
        )
        assert rc == 2
        assert "username exists" in out
    finally:
        asyncio.get_event_loop().run_until_complete(_delete_user("cli_dup"))


def test_cli_mcp_token_create_prints_plaintext_once(capsys, monkeypatch) -> None:
    # WR-01: supply password via env var (--password flag removed)
    monkeypatch.setenv("SMARTCOPILOT_NEW_PASSWORD", "p")
    # First create a user
    rc1, _ = _run_cli(
        ["user", "create", "--username", "cli_tok_user"],
        capsys,
    )
    assert rc1 == 0
    try:
        rc, out = _run_cli(
            ["mcp", "token", "create", "--user", "cli_tok_user", "--name", "ci"],
            capsys,
        )
        assert rc == 0, out
        # Plaintext appears with scmcp_ prefix; warning includes "will not be shown again"
        assert "token=scmcp_" in out
        assert "will not be shown again" in out
    finally:
        asyncio.get_event_loop().run_until_complete(_delete_user("cli_tok_user"))
