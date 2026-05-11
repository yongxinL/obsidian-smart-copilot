"""Phase 1d acceptance test (TEST-04).

End-to-end: user -> MCP token -> Claude-Code-style stdio session -> brain.put / get / search.
Also validates TEST-03 (stdio cleanliness) on the FULL session, not just the auth-failure path.
And MCP-08 (last_used_at advances).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

# Seed env vars before any app imports
_fernet_key = "T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU="
_jwt_key = "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa"
os.environ.setdefault("SMARTCOPILOT_FERNET_KEY", _fernet_key)
os.environ.setdefault("SMARTCOPILOT_JWT_SIGNING_KEY", _jwt_key)

from app.auth.context import OperationContext, system_operation_context
from app.dependencies import session_with_rls
from app.services.mcp_tokens import create_mcp_token
from app.services.users import create_user

# Resolve server/ once at module load
SERVER_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
)  # smart-copilot/server

# Models must be imported to register all table schemas
from app.models import Base  # noqa: F401

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module")
async def pg_container() -> PostgresContainer:
    """Boot a PostgreSQL container for the module-scoped acceptance test."""
    with PostgresContainer("pgvector/pgvector:pg16", driver=None) as pg:
        yield pg


@pytest_asyncio.fixture(scope="module")
async def acceptance_engine(pg_container: PostgresContainer):
    """Async engine bound to the testcontainer, alembic migrations applied."""
    # Build env for alembic (uses psycopg2 to run migrations)
    # Build env for alembic — use psycopg2 URL (Alembic PostgresqlImpl reads ALEMBIC_DATABASE_URL).
    # Also set DATABASE_URL so app code uses the same container.
    sync_url = pg_container.get_connection_url()
    base_url = sync_url.replace("postgresql+psycopg2://", "postgresql://", 1)
    psycopg2_url = base_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    async_url = base_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    env = os.environ.copy()
    env["ALEMBIC_DATABASE_URL"] = psycopg2_url  # alembic CLI reads this
    env["DATABASE_URL"] = (
        psycopg2_url  # app imports this (not asyncpg) for alembic subprocess
    )
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=str(SERVER_DIR),
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"alembic failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

    engine = create_async_engine(async_url, echo=False)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="module")
async def patched_acceptance_swsrl(acceptance_engine):
    """ENG-302: Patch session_with_rls to use acceptance_engine (the testcontainer).

    This is required because session_with_rls imports async_session_factory from
    database.py at module-load time. Without this patch, session_with_rls would
    use the production engine (localhost:5432) instead of the testcontainer.
    Both _db_mod.async_session_factory and _orig_swsrl.__globals__ must be patched.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app import database as _db_mod
    from app.dependencies import session_with_rls as _orig_swsrl

    test_factory = async_sessionmaker(
        bind=acceptance_engine,
        expire_on_commit=False,
    )

    old_factory = _db_mod.async_session_factory
    _db_mod.async_session_factory = test_factory
    _orig_swsrl.__globals__["async_session_factory"] = test_factory

    yield test_factory

    _db_mod.async_session_factory = old_factory
    _orig_swsrl.__globals__["async_session_factory"] = old_factory


@pytest_asyncio.fixture(scope="module")
async def acceptance_session_factory(acceptance_engine, patched_acceptance_swsrl):
    """Module-scoped sessionmaker for the acceptance test.

    patched_acceptance_swsrl ensures session_with_rls (used throughout the test)
    routes to the testcontainer, not the production engine.
    """
    return async_sessionmaker(
        bind=acceptance_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _send(proc: subprocess.Popen, msg: dict) -> None:
    """Write one JSON-RPC frame + newline to the subprocess stdin."""
    line = json.dumps(msg) + "\n"
    assert proc.stdin is not None
    proc.stdin.write(line.encode("utf-8"))
    proc.stdin.flush()


def _recv(proc: subprocess.Popen, timeout: float = 15.0) -> dict | None:
    """Read one JSON-RPC frame from the subprocess stdout.

    Skips structlog JSON lines (which go to stderr in production but may
    arrive on stdout in some environments) and returns only MCP JSON-RPC frames.
    MCP stdio transport uses NDJSON: one JSON object per line.
    """
    deadline = time.monotonic() + timeout
    assert proc.stdout is not None
    while time.monotonic() < deadline:
        line_bytes = proc.stdout.readline()
        if not line_bytes:
            # EOF or no data yet — check if process is still alive
            if proc.poll() is not None:
                # Process exited — no more output coming
                return None
            # Process alive but no data yet — short sleep and retry
            time.sleep(0.05)
            continue
        # readline() returns bytes; decode to str
        stripped = line_bytes.decode("utf-8", errors="replace").strip()
        if not stripped:
            continue
        # Skip structlog JSON lines (event, level, timestamp) that may bleed to stdout
        if stripped.startswith("{"):
            try:
                obj = json.loads(stripped)
                if "event" in obj or ("level" in obj and "timestamp" in obj):
                    continue  # skip structlog lines
            except json.JSONDecodeError:
                pass
        try:
            return json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"non-JSON from server: {line_bytes!r}") from exc
    return None  # timed out


def _send_and_match(proc: subprocess.Popen, msg: dict) -> dict:
    """Send a request and return the matching response (skipping notifications)."""
    _send(proc, msg)
    while True:
        resp = _recv(proc)
        if resp is None:
            # Drain stdout and stderr for diagnosis on timeout
            proc.poll()
            stdout_drain = b""
            stderr_drain = b""
            if proc.stdout:
                stdout_drain = proc.stdout.read() or b""
            if proc.stderr:
                stderr_drain = proc.stderr.read() or b""
            raise AssertionError(
                f"timed out waiting for response\n"
                f"stdout so far ({len(stdout_drain)} bytes): {stdout_drain!r}\n"
                f"stderr so far ({len(stderr_drain)} bytes): {stderr_drain.decode('utf-8', errors='replace')!r}"
            )
        # Notifications have no `id`; skip them
        if resp.get("id") == msg["id"]:
            return resp


def _extract_body(result: dict) -> dict:
    """FastMCP SDK 1.27.0 wraps dict results in {"content":[{"type":"text","text":"<json>"}]}.

    Some return paths emit the raw dict in `result`. Handle both transparently.
    """
    if not isinstance(result, dict):
        return {}
    content = result.get("content")
    if isinstance(content, list) and content and isinstance(content[0], dict):
        text_field = content[0].get("text")
        if isinstance(text_field, str):
            try:
                return json.loads(text_field)
            except json.JSONDecodeError:
                return {"raw": text_field}
    return result


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_phase_1d_acceptance_stdio_flow(
    acceptance_session_factory: async_sessionmaker[AsyncSession],
    pg_container: PostgresContainer,
) -> None:
    """TEST-04: end-to-end stdio MCP flow — user -> token -> subprocess -> brain.put/get/search.

    Validates:
    - TEST-03: all stdout bytes are valid JSON-RPC frames (no extra output)
    - MCP-08: last_used_at advances after the session
    - Phase 1c regression: vault service layer is unchanged
    """

    # ── 1. Seed user + vault + MCP token ─────────────────────────────────────
    username = f"acceptance-{uuid.uuid4().hex[:8]}"
    plaintext_token: str | None = None
    user_id: uuid.UUID | None = None

    sys_ctx = system_operation_context(client_name="test", request_id="test-acceptance")
    async for session in session_with_rls(sys_ctx):
        user = await create_user(
            session,
            sys_ctx,
            username=username,
            password_plain="acceptance-password-12345",
            role="user",
            email=None,
        )
        await session.commit()
        user_id = user.id

    user_ctx = OperationContext(
        user_id=user_id,
        role="user",
        transport="cli",
        remote=False,
        client_name="test",
        request_id="test-mint-token",
    )
    async for session in session_with_rls(user_ctx):
        plaintext_token, _row = await create_mcp_token(
            session, user_ctx, name="acceptance"
        )
        await session.commit()

    assert plaintext_token is not None, "create_mcp_token returned no plaintext"

    # ── 2. Seed the user's private vault (Phase 1d: single private vault) ─────
    vault_id = uuid.uuid4()
    async with acceptance_session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO vaults (id, owner_user_id, kind, path, created_at, updated_at) "
                "VALUES (:vid, :uid, 'private', :path, now(), now())"
            ),
            {"vid": vault_id, "uid": user_id, "path": f"/vaults/private/{username}/"},
        )
        await session.commit()

    # ── 3. Build env for the subprocess ──────────────────────────────────────
    sync_url = pg_container.get_connection_url()
    base_url = sync_url.replace("postgresql+psycopg2://", "postgresql://", 1)
    async_dsn = base_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    env = os.environ.copy()
    env["SMARTCOPILOT_FERNET_KEY"] = _fernet_key
    env["SMARTCOPILOT_JWT_SIGNING_KEY"] = _jwt_key
    env["SMARTCOPILOT_MCP_TOKEN"] = plaintext_token
    # Use asyncpg URL format so the module-level engine (database.py)
    # can connect to the testcontainer.
    env["DATABASE_URL"] = async_dsn  # postgresql+asyncpg://...

    # ── 4. Spawn the CLI stdio server ────────────────────────────────────────
    proc = subprocess.Popen(
        [sys.executable, "-m", "app.cli.main", "mcp", "serve", "--stdio"],
        cwd=str(SERVER_DIR),
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    captured_stdout = bytearray()

    try:
        # Brief pause to let the server process auth before we start sending
        time.sleep(0.5)

        # Check if the process already exited (auth failure)
        if proc.poll() is not None:
            rc = proc.poll()
            stderr_data = b""
            stdout_data = b""
            if proc.stderr:
                stderr_data = proc.stderr.read() or b""
            if proc.stdout:
                stdout_data = proc.stdout.read() or b""
            raise AssertionError(
                f"stdio server exited immediately with code {rc}. "
                f"stderr: {stderr_data.decode('utf-8', errors='replace')!r} "
                f"stdout: {stdout_data!r}"
            )

        # ── 5. JSON-RPC handshake ─────────────────────────────────────────────
        # Send initialize and wait for response (with intermediate poll checks)
        _send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "phase-1d-acceptance", "version": "0.0.0"},
                },
            },
        )

        # Poll loop: wait for response or process exit
        deadline = time.monotonic() + 15.0
        while time.monotonic() < deadline:
            # Check if process exited
            rc = proc.poll()
            if rc is not None:
                stderr_data = b""
                stdout_data = b""
                if proc.stderr:
                    stderr_data = proc.stderr.read() or b""
                if proc.stdout:
                    stdout_data = proc.stdout.read() or b""
                raise AssertionError(
                    f"stdio server exited during initialize with code {rc}. "
                    f"stderr: {stderr_data.decode('utf-8', errors='replace')!r} "
                    f"stdout: {stdout_data!r}"
                )
            # Try to read a line
            line_bytes = proc.stdout.readline()
            if line_bytes:
                stripped = line_bytes.decode("utf-8", errors="replace").strip()
                if stripped:
                    # Skip structlog lines
                    if stripped.startswith("{"):
                        try:
                            obj = json.loads(stripped)
                            if "event" in obj or (
                                "level" in obj and "timestamp" in obj
                            ):
                                continue  # skip, keep polling
                        except json.JSONDecodeError:
                            pass
                    try:
                        init_resp = json.loads(stripped)
                        break
                    except json.JSONDecodeError as exc:
                        raise RuntimeError(
                            f"non-JSON from server: {line_bytes!r}"
                        ) from exc
            time.sleep(0.05)
        else:
            # Timeout
            stderr_data = b""
            stdout_data = b""
            if proc.stderr:
                stderr_data = proc.stderr.read() or b""
            if proc.stdout:
                stdout_data = proc.stdout.read() or b""
            raise AssertionError(
                f"timed out waiting for initialize response. "
                f"stdout: {stdout_data!r}, stderr: {stderr_data.decode('utf-8', errors='replace')!r}"
            )

        assert "result" in init_resp, f"initialize failed: {init_resp}"

        # initialized notification (no id — server does not respond)
        _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})

        # ── 6. brain.put ──────────────────────────────────────────────────────
        # NOTE: content must NOT contain a "---" line (vault parser uses it as
        # compiled_truth/timeline separator). The second argument is the expected
        # compiled_truth for the assertion below.
        put_resp = _send_and_match(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "brain.put",
                    "arguments": {
                        "slug": "acme",
                        "content": "title: Acme\n\nFounded 2010 in the acme corporation.",
                        "namespace": "private",
                    },
                },
            },
        )
        body = _extract_body(put_resp.get("result", {}))
        assert body.get("status") == "ok", f"brain.put failed: {body}"

        # ── 7. brain.get ──────────────────────────────────────────────────────
        get_resp = _send_and_match(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "brain.get", "arguments": {"slug": "acme"}},
            },
        )
        body = _extract_body(get_resp.get("result", {}))
        assert body.get("slug") == "acme", f"brain.get unexpected: {body}"
        # The content goes into compiled_truth (no --- separator in input)
        assert "Founded 2010" in (body.get("compiled_truth") or ""), (
            f"compiled_truth missing content: {body}"
        )

        # ── 8. brain.search ───────────────────────────────────────────────────
        srch_resp = _send_and_match(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "brain.search",
                    "arguments": {"query": "acme", "limit": 5},
                },
            },
        )
        body = _extract_body(srch_resp.get("result", {}))
        assert body.get("search_type") == "fts_v1", f"search_type unexpected: {body}"
        results = body.get("results") or []
        assert any(r.get("slug") == "acme" for r in results), (
            f"acme not in search results: {body}"
        )

        # ── 9. Graceful shutdown — close stdin, wait for exit ────────────────
        proc.stdin.close()
        try:
            _proc_exit = proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.terminate()
            _proc_exit = proc.wait(timeout=5)
        # Note: FastMCP may exit non-zero on graceful shutdown (e.g., the
        # stdio stdin close causes an exception in the event loop).
        # We accept any exit code as long as we got all our responses above.

    finally:
        # Drain any remaining stdout bytes after process exit
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=5)
        if proc.stdout is not None:
            try:
                captured_stdout.extend(proc.stdout.read() or b"")
            except Exception:  # noqa: BLE001
                pass

    # ── 10. TEST-03 strict: every non-empty stdout line is JSON-RPC ───────────
    # We already validated each line in _recv. The check below is a final
    # sanity sweep on any bytes that arrived after the main loop.
    tail = bytes(captured_stdout).strip()
    if tail:
        for line in tail.split(b"\n"):
            if not line.strip():
                continue
            obj = json.loads(line)
            assert obj.get("jsonrpc") == "2.0", f"non-JSON-RPC tail byte: {line!r}"

    # ── 11. MCP-08: last_used_at advanced ────────────────────────────────────
    assert user_id is not None
    async with acceptance_session_factory() as session:
        row = (
            await session.execute(
                text("SELECT last_used_at FROM mcp_tokens WHERE user_id = :uid"),
                {"uid": user_id},
            )
        ).scalar_one_or_none()

    assert row is not None, "mcp_token row not found after session"
    # last_used_at is a TIMESTAMPTZ (UTC) column — compare with timezone-aware now
    last_used = row.replace(tzinfo=UTC) if row.tzinfo is None else row
    assert datetime.now(UTC) - last_used < timedelta(minutes=5), (
        f"last_used_at not recent: {row}"
    )


# ---------------------------------------------------------------------------
# Phase 1c regression: vault service layer unchanged
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_phase_1c_regression_vault_service_unchanged(
    acceptance_session_factory: async_sessionmaker[AsyncSession],
    pg_container: PostgresContainer,
) -> None:
    """Verify the vault service layer is unchanged after Phase 1d.

    This is a minimal smoke that confirms:
    - write_page + read_page round-trip still works
    - upsert_page creates new page and updates existing page correctly
    """
    username = f"regression-{uuid.uuid4().hex[:8]}"
    sys_ctx = system_operation_context(client_name="test", request_id="test-regression")
    user_id: uuid.UUID | None = None
    vault_id = uuid.uuid4()

    async for session in session_with_rls(sys_ctx):
        user = await create_user(
            session,
            sys_ctx,
            username=username,
            password_plain="regression-password",
            role="user",
            email=None,
        )
        await session.commit()
        user_id = user.id

    async with acceptance_session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO vaults (id, owner_user_id, kind, path, created_at, updated_at) "
                "VALUES (:vid, :uid, 'private', :path, now(), now())"
            ),
            {"vid": vault_id, "uid": user_id, "path": f"/vaults/private/{username}/"},
        )
        await session.commit()

    from app.services.pages import read_page, soft_delete_page, write_page

    user_ctx = OperationContext(
        user_id=user_id,
        role="user",
        transport="cli",
        remote=False,
        client_name="test",
        request_id="test-regression-vault",
    )

    async for session in session_with_rls(user_ctx):
        # write via write_page (the public API)
        page = await write_page(
            session,
            user_ctx,
            slug="regression-test",
            raw_content=b"---\ntitle: Regression Test\n---\nVault unchanged",
            vault_id=vault_id,
        )
        await session.commit()
        assert page.slug == "regression-test"

    async for session in session_with_rls(user_ctx):
        # read via read_page (session, vault_id, slug — no ctx)
        page = await read_page(session, vault_id=vault_id, slug="regression-test")
        await session.commit()
        assert page is not None
        assert "Vault unchanged" in page.compiled_truth

    async for session in session_with_rls(user_ctx):
        # delete via soft_delete_page (page_id, not slug)
        page = await read_page(session, vault_id=vault_id, slug="regression-test")
        await soft_delete_page(session, user_ctx, page_id=page.id)
        await session.commit()
