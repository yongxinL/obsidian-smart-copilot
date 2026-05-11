"""CLI page CRUD integration tests (D-13)."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.context import system_operation_context
from app.auth.password import hash_password
from app.models.user import User
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


@pytest_asyncio.fixture(loop_scope="session")
async def _page_cli_session(test_engine) -> tuple[async_sessionmaker, str]:
    """Return a sessionmaker bound to test_engine and the async DB URL."""
    factory = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=AsyncSession
    )
    sync_url = test_engine.sync_engine.url.render_as_string(hide_password=False)
    async_url = sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return factory, async_url


async def _create_test_user_vault(factory: async_sessionmaker, username: str) -> str:
    """Create a test user and their private vault; return the username."""
    norm = username.strip().casefold()
    ctx = system_operation_context(client_name="cli", request_id="test-setup")
    async with factory() as session:
        async with session.begin():
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
                path=f"/tmp/vault_{norm}",
            )
            session.add(vault)
    return norm


async def _delete_test_user(factory: async_sessionmaker, username: str) -> None:
    """Delete test user and their vault/pages."""
    norm = username.strip().casefold()
    async with factory() as session:
        async with session.begin():
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


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_cli_page_put_then_get(test_engine) -> None:
    fernet = "T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU="
    jwt = "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa"
    sync_url = test_engine.sync_engine.url.render_as_string(hide_password=False)
    db_url = sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    factory = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=AsyncSession
    )

    username = "cli_page_user1"
    await _create_test_user_vault(factory, username)

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("---\ntitle: Test Page\n---\n# Test\n\nHello world.")
            f.flush()
            tf_path = f.name

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
        await _delete_test_user(factory, username)
        Path(tf_path).unlink(missing_ok=True)


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_cli_page_put_unknown_user_returns_2(test_engine) -> None:
    fernet = "T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU="
    jwt = "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa"
    sync_url = test_engine.sync_engine.url.render_as_string(hide_password=False)
    db_url = sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)

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
@pytest.mark.asyncio(loop_scope="session")
async def test_cli_page_list_returns_seeded_pages(test_engine) -> None:
    fernet = "T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU="
    jwt = "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa"
    sync_url = test_engine.sync_engine.url.render_as_string(hide_password=False)
    db_url = sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    factory = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=AsyncSession
    )

    username = "cli_page_list_user"
    await _create_test_user_vault(factory, username)

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
        await _delete_test_user(factory, username)


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_cli_page_search_returns_match(test_engine) -> None:
    fernet = "T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU="
    jwt = "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa"
    sync_url = test_engine.sync_engine.url.render_as_string(hide_password=False)
    db_url = sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    factory = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=AsyncSession
    )

    username = "cli_page_search_user"
    await _create_test_user_vault(factory, username)

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
        await _delete_test_user(factory, username)


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_cli_page_delete_then_get_returns_2(test_engine) -> None:
    fernet = "T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU="
    jwt = "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa"
    sync_url = test_engine.sync_engine.url.render_as_string(hide_password=False)
    db_url = sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    factory = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=AsyncSession
    )

    username = "cli_page_delete_user"
    await _create_test_user_vault(factory, username)

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
        await _delete_test_user(factory, username)


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_cli_stats_returns_count(test_engine) -> None:
    fernet = "T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU="
    jwt = "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa"
    sync_url = test_engine.sync_engine.url.render_as_string(hide_password=False)
    db_url = sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    factory = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=AsyncSession
    )

    username = "cli_stats_user"
    await _create_test_user_vault(factory, username)

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
        await _delete_test_user(factory, username)
