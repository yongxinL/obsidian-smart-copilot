"""AUTH-02 / AUTH-03 integration — /auth/login + /auth/refresh + rate limit."""

from __future__ import annotations

import hashlib

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.auth.context import system_operation_context
from app.dependencies import session_with_rls
from app.main import app

pytestmark = [pytest.mark.auth, pytest.mark.integration]


async def _new_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _create_user_via_service(username: str, password: str, role: str = "user"):  # type: ignore[return]
    from app.auth.context import system_operation_context
    from app.services.users import create_user

    ctx = system_operation_context()
    async for session in session_with_rls(ctx):
        user = await create_user(
            session, ctx, username=username, password_plain=password, role=role
        )
        await session.commit()
        return user.id


async def _delete_user(user_id) -> None:  # type: ignore[type-arg]
    async for session in session_with_rls(system_operation_context()):
        await session.execute(
            text("DELETE FROM users WHERE id = :id"), {"id": str(user_id)}
        )
        await session.commit()


async def test_login_returns_jwt_pair() -> None:
    uid = await _create_user_via_service("loginuser1", "p@ssw0rd")
    try:
        async with await _new_client() as c:
            r = await c.post(
                "/auth/login", json={"username": "loginuser1", "password": "p@ssw0rd"}
            )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "access_jwt" in body and "refresh_token" in body
        assert body["token_type"] == "Bearer"
    finally:
        await _delete_user(uid)


async def test_login_invalid_credentials_returns_401() -> None:
    uid = await _create_user_via_service("loginuser2", "p@ssw0rd")
    try:
        async with await _new_client() as c:
            r = await c.post(
                "/auth/login", json={"username": "loginuser2", "password": "WRONG"}
            )
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "unauthorized"
    finally:
        await _delete_user(uid)


async def test_refresh_token_stored_as_hash() -> None:
    uid = await _create_user_via_service("refreshuser", "p@ssw0rd")
    try:
        async with await _new_client() as c:
            r = await c.post(
                "/auth/login", json={"username": "refreshuser", "password": "p@ssw0rd"}
            )
        assert r.status_code == 200, r.text
        refresh = r.json()["refresh_token"]
        expected_hash = hashlib.sha256(refresh.encode()).hexdigest()
        async for s in session_with_rls(system_operation_context()):
            row = (
                await s.execute(
                    text("SELECT token_hash FROM sessions WHERE token_hash = :h"),
                    {"h": expected_hash},
                )
            ).first()
            assert row is not None, "refresh stored as sha256 hex matching client value"
    finally:
        await _delete_user(uid)


async def test_refresh_rotation_revokes_old() -> None:
    uid = await _create_user_via_service("rotuser", "p@ssw0rd")
    try:
        async with await _new_client() as c:
            r = await c.post(
                "/auth/login", json={"username": "rotuser", "password": "p@ssw0rd"}
            )
            assert r.status_code == 200, r.text
            old_refresh = r.json()["refresh_token"]
            r2 = await c.post("/auth/refresh", json={"refresh_token": old_refresh})
            assert r2.status_code == 200
            new_refresh = r2.json()["refresh_token"]
            assert new_refresh != old_refresh
    finally:
        await _delete_user(uid)


async def test_old_refresh_replay_rejected() -> None:
    uid = await _create_user_via_service("replayuser", "p@ssw0rd")
    try:
        async with await _new_client() as c:
            r = await c.post(
                "/auth/login", json={"username": "replayuser", "password": "p@ssw0rd"}
            )
            assert r.status_code == 200, r.text
            old_refresh = r.json()["refresh_token"]
            # First rotate succeeds
            ok = await c.post("/auth/refresh", json={"refresh_token": old_refresh})
            assert ok.status_code == 200
            # Replay of old refresh now fails
            bad = await c.post("/auth/refresh", json={"refresh_token": old_refresh})
            assert bad.status_code == 401
            assert bad.json()["error"]["code"] == "unauthorized"
    finally:
        await _delete_user(uid)


async def test_rate_limit_after_10_failures() -> None:
    uid = await _create_user_via_service("rluser", "p@ssw0rd")
    try:
        async with await _new_client() as c:
            # 10 failed attempts
            for _ in range(10):
                await c.post(
                    "/auth/login", json={"username": "rluser", "password": "WRONG"}
                )
            # 11th should be rate-limited
            r = await c.post(
                "/auth/login", json={"username": "rluser", "password": "WRONG"}
            )
            assert r.status_code == 429
            body = r.json()
            assert body["error"]["code"] == "rate_limited"
            assert "retry_after_seconds" in body["error"]["details"]
    finally:
        # cleanup login_attempts
        async for s in session_with_rls(system_operation_context()):
            await s.execute(
                text("DELETE FROM login_attempts WHERE username = :u"), {"u": "rluser"}
            )
            await s.commit()
        await _delete_user(uid)


async def test_rate_limit_response_envelope() -> None:
    # Ensures the envelope shape is exactly {error: {code, message, details: {retry_after_seconds}}}
    uid = await _create_user_via_service("envuser", "p@ssw0rd")
    try:
        async with await _new_client() as c:
            for _ in range(10):
                await c.post(
                    "/auth/login", json={"username": "envuser", "password": "X"}
                )
            r = await c.post(
                "/auth/login", json={"username": "envuser", "password": "X"}
            )
        body = r.json()
        assert set(body["error"].keys()) >= {"code", "message", "details"}
        assert body["error"]["code"] == "rate_limited"
        assert isinstance(body["error"]["details"]["retry_after_seconds"], int)
    finally:
        async for s in session_with_rls(system_operation_context()):
            await s.execute(
                text("DELETE FROM login_attempts WHERE username = :u"), {"u": "envuser"}
            )
            await s.commit()
        await _delete_user(uid)


async def test_successful_login_wipes_attempts() -> None:
    uid = await _create_user_via_service("wipeuser", "p@ssw0rd")
    try:
        async with await _new_client() as c:
            await c.post(
                "/auth/login", json={"username": "wipeuser", "password": "WRONG"}
            )
            await c.post(
                "/auth/login", json={"username": "wipeuser", "password": "WRONG"}
            )
            ok = await c.post(
                "/auth/login", json={"username": "wipeuser", "password": "p@ssw0rd"}
            )
            assert ok.status_code == 200
        # Attempts should be wiped
        async for s in session_with_rls(system_operation_context()):
            cnt = (
                await s.execute(
                    text("SELECT count(*) FROM login_attempts WHERE username = :u"),
                    {"u": "wipeuser"},
                )
            ).scalar_one()
            assert cnt == 0
    finally:
        await _delete_user(uid)


async def test_sliding_window_ages_out() -> None:
    # Seed an attempt 16 minutes ago (> 15 min window) and verify it doesn't count
    uid = await _create_user_via_service("agingouser", "p@ssw0rd")
    try:
        async for s in session_with_rls(system_operation_context()):
            await s.execute(
                text(
                    "INSERT INTO login_attempts (username, ip, attempted_at) "
                    "SELECT 'agingouser', '127.0.0.1', now() - make_interval(mins => 16) "
                    "FROM generate_series(1, 12)"
                ),
            )
            await s.commit()
        async with await _new_client() as c:
            # Should NOT be rate-limited because seeded rows are >15 min old
            r = await c.post(
                "/auth/login", json={"username": "agingouser", "password": "p@ssw0rd"}
            )
            assert r.status_code == 200, (
                f"sliding window should age out — got {r.status_code}: {r.text}"
            )
    finally:
        async for s in session_with_rls(system_operation_context()):
            await s.execute(
                text("DELETE FROM login_attempts WHERE username = :u"),
                {"u": "agingouser"},
            )
            await s.commit()
        await _delete_user(uid)
