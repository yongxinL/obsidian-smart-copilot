"""CLI page CRUD integration tests (D-13)."""

from __future__ import annotations

import asyncio
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import pytest

from app.auth.context import system_operation_context
from app.dependencies import session_with_rls
from app.models.vault import Vault

pytestmark = pytest.mark.integration


def _run_page_cli(
    argv: list[str],
    *,
    fernet_key: str,
    jwt_key: str,
    db_url: str | None = None,
    timeout: int = 30,
) -> subprocess.CompletedProcess:
    env = __import__("os").environ.copy()
    env["SMARTCOPILOT_FERNET_KEY"] = fernet_key
    env["JWT_SIGNING_KEY"] = jwt_key
    if db_url:
        env["DATABASE_URL"] = db_url
    return subprocess.run(
        [sys.executable, "-m", "app.cli.main"] + argv,
        env=env,
        capture_output=True,
        timeout=timeout,
        cwd="server",
    )


def _run_in_thread(cli_fn, *args, **kwargs):
    result = {"rc": -1, "exc": None}

    def _target():
        try:
            result["rc"] = cli_fn(*args, **kwargs)
        except Exception as exc:
            result["exc"] = exc

    t = threading.Thread(target=_target)
    t.start()
    t.join()
    if result["exc"]:
        raise result["exc"]
    return result["rc"]


async def _create_test_user_vault(username: str) -> str:
    """Create a test user and their private vault; return the username."""
    import uuid

    from app.auth.password import hash_password
    from app.models.user import User

    norm = username.strip().casefold()
    ctx = system_operation_context(client_name="cli", request_id="test-setup")
    async for session in session_with_rls(ctx):
        user = User(
            id=uuid.uuid4(),
            username=norm,
            password_hash=await hash_password("testpass"),
            role="user",
            is_active=True,
        )
        session.add(user)
        await session.flush()
        vault = Vault(
            id=uuid.uuid4(),
            owner_user_id=user.id,
            kind="private",
            name="test-vault",
            path=f"/tmp/vault_{norm}",
        )
        session.add(vault)
        await session.commit()
        return norm


async def _delete_test_user(username: str) -> None:
    from sqlalchemy import text

    norm = username.strip().casefold()
    ctx = system_operation_context(client_name="cli", request_id="test-teardown")
    async for session in session_with_rls(ctx):
        await session.execute(
            text(
                "DELETE FROM pages WHERE vault_id IN (SELECT id FROM vaults WHERE owner_user_id IN (SELECT id FROM users WHERE username = :u))"
            ),
            {"u": norm},
        )
        await session.execute(
            text(
                "DELETE FROM vaults WHERE owner_user_id IN (SELECT id FROM users WHERE username = :u)"
            ),
            {"u": norm},
        )
        await session.execute(
            text("DELETE FROM users WHERE username = :u"), {"u": norm}
        )
        await session.commit()


@pytest.mark.integration
def test_cli_page_put_then_get(postgres_container) -> None:
    fernet = "T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU="
    jwt = "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa"
    sync_url = postgres_container.get_connection_url()
    raw_dsn = sync_url.replace("postgresql+psycopg2://", "postgresql://", 1)
    db_url = raw_dsn.replace("postgresql://", "postgresql+asyncpg://", 1)

    username = "cli_page_user1"
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_create_test_user_vault(username))
    finally:
        loop.close()

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("---\ntitle: Test Page\n---\n# Test\n\nHello world.")
            f.flush()
            tf_path = f.name

        # put
        proc = _run_page_cli(
            [
                "page",
                "put",
                "--user",
                username,
                "--slug",
                "test-page",
                "--file",
                tf_path,
            ],
            fernet_key=fernet,
            jwt_key=jwt,
            db_url=db_url,
        )
        assert proc.returncode == 0, f"put failed: {proc.stderr.decode()}"
        out = proc.stdout.decode()
        assert "slug=test-page" in out

        # get
        proc = _run_page_cli(
            ["page", "get", "--user", username, "--slug", "test-page"],
            fernet_key=fernet,
            jwt_key=jwt,
            db_url=db_url,
        )
        assert proc.returncode == 0, f"get failed: {proc.stderr.decode()}"
        out = proc.stdout.decode()
        assert "slug=test-page" in out
        assert "compiled_truth:" in out
    finally:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_delete_test_user(username))
        finally:
            loop.close()
        Path(tf_path).unlink(missing_ok=True)


@pytest.mark.integration
def test_cli_page_put_unknown_user_returns_2(postgres_container) -> None:
    fernet = "T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU="
    jwt = "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa"
    sync_url = postgres_container.get_connection_url()
    raw_dsn = sync_url.replace("postgresql+psycopg2://", "postgresql://", 1)
    db_url = raw_dsn.replace("postgresql://", "postgresql+asyncpg://", 1)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("---\ntitle: Test\n---\n# Test\n")
        f.flush()
        tf_path = f.name

    try:
        proc = _run_page_cli(
            [
                "page",
                "put",
                "--user",
                "nonexistent_user_xyz",
                "--slug",
                "test",
                "--file",
                tf_path,
            ],
            fernet_key=fernet,
            jwt_key=jwt,
            db_url=db_url,
        )
        assert proc.returncode == 2
        assert b"user not found" in proc.stderr or b"error:" in proc.stderr
    finally:
        Path(tf_path).unlink(missing_ok=True)


@pytest.mark.integration
def test_cli_page_list_returns_seeded_pages(postgres_container) -> None:
    fernet = "T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU="
    jwt = "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa"
    sync_url = postgres_container.get_connection_url()
    raw_dsn = sync_url.replace("postgresql+psycopg2://", "postgresql://", 1)
    db_url = raw_dsn.replace("postgresql://", "postgresql+asyncpg://", 1)

    username = "cli_page_list_user"
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_create_test_user_vault(username))
    finally:
        loop.close()

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(
                "---\ntitle: ListTest\nnote_type: permanent\n---\n# ListTest\nContent here"
            )
            f.flush()
            tf_path = f.name

        _run_page_cli(
            [
                "page",
                "put",
                "--user",
                username,
                "--slug",
                "list-test-page",
                "--file",
                tf_path,
            ],
            fernet_key=fernet,
            jwt_key=jwt,
            db_url=db_url,
        )
        Path(tf_path).unlink(missing_ok=True)

        proc = _run_page_cli(
            ["page", "list", "--user", username],
            fernet_key=fernet,
            jwt_key=jwt,
            db_url=db_url,
        )
        assert proc.returncode == 0
        out = proc.stdout.decode()
        assert "list-test-page" in out
    finally:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_delete_test_user(username))
        finally:
            loop.close()


@pytest.mark.integration
def test_cli_page_search_returns_match(postgres_container) -> None:
    fernet = "T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU="
    jwt = "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa"
    sync_url = postgres_container.get_connection_url()
    raw_dsn = sync_url.replace("postgresql+psycopg2://", "postgresql://", 1)
    db_url = raw_dsn.replace("postgresql://", "postgresql+asyncpg://", 1)

    username = "cli_page_search_user"
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_create_test_user_vault(username))
    finally:
        loop.close()

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(
                "---\ntitle: Searchable Doc\n---\n# Searchable\n\nThis is a document about wizards."
            )
            f.flush()
            tf_path = f.name

        _run_page_cli(
            [
                "page",
                "put",
                "--user",
                username,
                "--slug",
                "searchable-doc",
                "--file",
                tf_path,
            ],
            fernet_key=fernet,
            jwt_key=jwt,
            db_url=db_url,
        )
        Path(tf_path).unlink(missing_ok=True)

        proc = _run_page_cli(
            ["page", "search", "--user", username, "--query", "wizards"],
            fernet_key=fernet,
            jwt_key=jwt,
            db_url=db_url,
        )
        assert proc.returncode == 0
        out = proc.stdout.decode()
        assert "searchable-doc" in out
    finally:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_delete_test_user(username))
        finally:
            loop.close()


@pytest.mark.integration
def test_cli_page_delete_then_get_returns_2(postgres_container) -> None:
    fernet = "T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU="
    jwt = "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa"
    sync_url = postgres_container.get_connection_url()
    raw_dsn = sync_url.replace("postgresql+psycopg2://", "postgresql://", 1)
    db_url = raw_dsn.replace("postgresql://", "postgresql+asyncpg://", 1)

    username = "cli_page_delete_user"
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_create_test_user_vault(username))
    finally:
        loop.close()

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("---\ntitle: DeleteMe\n---\n# DeleteMe\n")
            f.flush()
            tf_path = f.name

        _run_page_cli(
            [
                "page",
                "put",
                "--user",
                username,
                "--slug",
                "delete-me",
                "--file",
                tf_path,
            ],
            fernet_key=fernet,
            jwt_key=jwt,
            db_url=db_url,
        )
        Path(tf_path).unlink(missing_ok=True)

        proc = _run_page_cli(
            ["page", "delete", "--user", username, "--slug", "delete-me"],
            fernet_key=fernet,
            jwt_key=jwt,
            db_url=db_url,
        )
        assert proc.returncode == 0, proc.stderr.decode()

        proc = _run_page_cli(
            ["page", "get", "--user", username, "--slug", "delete-me"],
            fernet_key=fernet,
            jwt_key=jwt,
            db_url=db_url,
        )
        assert proc.returncode == 2
    finally:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_delete_test_user(username))
        finally:
            loop.close()


@pytest.mark.integration
def test_cli_stats_returns_count(postgres_container) -> None:
    fernet = "T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU="
    jwt = "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa"
    sync_url = postgres_container.get_connection_url()
    raw_dsn = sync_url.replace("postgresql+psycopg2://", "postgresql://", 1)
    db_url = raw_dsn.replace("postgresql://", "postgresql+asyncpg://", 1)

    username = "cli_stats_user"
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_create_test_user_vault(username))
    finally:
        loop.close()

    try:
        proc = _run_page_cli(
            ["stats", "--user", username],
            fernet_key=fernet,
            jwt_key=jwt,
            db_url=db_url,
        )
        assert proc.returncode == 0, proc.stderr.decode()
        out = proc.stdout.decode()
        assert "page_count=" in out
        assert "deleted_page_count=" in out
        assert "total_compiled_truth_bytes=" in out
    finally:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_delete_test_user(username))
        finally:
            loop.close()
