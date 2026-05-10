"""Step-up admin re-auth + role enforcement — AUTH-06/07 (Plan 07)."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.auth.context import system_operation_context
from app.dependencies import session_with_rls
from app.main import app

pytestmark = [pytest.mark.auth, pytest.mark.integration]


async def _new_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _create_user(username: str, password: str, role: str = "user"):  # type: ignore[return]
    from app.services.users import create_user

    ctx = system_operation_context()
    async for session in session_with_rls(ctx):
        user = await create_user(session, ctx, username=username, password_plain=password, role=role)
        await session.commit()
        return user.id


async def _delete_user(user_id) -> None:  # type: ignore[type-arg]
    async for session in session_with_rls(system_operation_context()):
        await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": str(user_id)})
        await session.commit()


async def _login(client: AsyncClient, username: str, password: str) -> str:
    """Login and return access_jwt."""
    r = await client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, f"login failed: {r.text}"
    return r.json()["access_jwt"]


async def test_role_enum_is_admin_or_user() -> None:
    async for session in session_with_rls(system_operation_context()):
        rows = await session.execute(
            text("SELECT enumlabel FROM pg_enum WHERE enumtypid = 'user_role_enum'::regtype ORDER BY enumlabel")
        )
        labels = {row[0] for row in rows}
        assert labels == {"admin", "user"}


async def test_non_admin_forbidden_from_admin_route() -> None:
    uid = await _create_user("basicusr", "p@ssw0rd", role="user")
    try:
        async with await _new_client() as c:
            token = await _login(c, "basicusr", "p@ssw0rd")
            r = await c.post(
                "/api/v1/admin/_demo_destructive",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert r.status_code == 403
        body = r.json()
        assert body["error"]["code"] == "forbidden"
    finally:
        await _delete_user(uid)


async def test_reauth_sets_admin_fresh_until() -> None:
    uid = await _create_user("reauthadmin", "s3cur3!", role="admin")
    try:
        async with await _new_client() as c:
            token = await _login(c, "reauthadmin", "s3cur3!")
            r = await c.post(
                "/api/v1/admin/reauth",
                json={"factor": "password", "password": "s3cur3!"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert r.status_code == 200, r.text
        # Verify admin_fresh_until is set in DB
        async for session in session_with_rls(system_operation_context()):
            row = (await session.execute(
                text("SELECT admin_fresh_until FROM sessions WHERE user_id = :uid AND admin_fresh_until IS NOT NULL"),
                {"uid": str(uid)},
            )).first()
            assert row is not None, "admin_fresh_until should be set after reauth"
    finally:
        await _delete_user(uid)


async def test_destructive_route_403_without_fresh_auth() -> None:
    uid = await _create_user("freshadmin", "p@ssw0rd", role="admin")
    try:
        async with await _new_client() as c:
            token = await _login(c, "freshadmin", "p@ssw0rd")
            # Call destructive route WITHOUT doing reauth first
            r = await c.post(
                "/api/v1/admin/_demo_destructive",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert r.status_code == 403
        body = r.json()
        assert body["error"]["code"] == "admin_reauth_required"
    finally:
        await _delete_user(uid)


async def test_admin_reauth_required_envelope_shape() -> None:
    uid = await _create_user("envadmin", "p@ssw0rd", role="admin")
    try:
        async with await _new_client() as c:
            token = await _login(c, "envadmin", "p@ssw0rd")
            r = await c.post(
                "/api/v1/admin/_demo_destructive",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert r.status_code == 403
        body = r.json()
        error = body["error"]
        assert error["code"] == "admin_reauth_required"
        assert "message" in error
        assert error["details"]["reauth_url"] == "/api/v1/admin/reauth"
        assert error["details"]["freshness_window_minutes"] == 60
    finally:
        await _delete_user(uid)


async def test_fresh_auth_expires_after_60_minutes() -> None:
    uid = await _create_user("expiredadmin", "p@ssw0rd", role="admin")
    try:
        async with await _new_client() as c:
            token = await _login(c, "expiredadmin", "p@ssw0rd")
            # Do reauth to set admin_fresh_until
            r = await c.post(
                "/api/v1/admin/reauth",
                json={"factor": "password", "password": "p@ssw0rd"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r.status_code == 200, r.text
            # Expire it by directly setting admin_fresh_until to the past
            async for session in session_with_rls(system_operation_context()):
                await session.execute(
                    text(
                        "UPDATE sessions SET admin_fresh_until = now() - interval '5 minutes' "
                        "WHERE user_id = :uid"
                    ),
                    {"uid": str(uid)},
                )
                await session.commit()
            # Should now get 403
            r2 = await c.post(
                "/api/v1/admin/_demo_destructive",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert r2.status_code == 403
        assert r2.json()["error"]["code"] == "admin_reauth_required"
    finally:
        await _delete_user(uid)


async def test_reauth_unsupported_factor_returns_not_implemented() -> None:
    uid = await _create_user("factoradmin", "p@ssw0rd", role="admin")
    try:
        async with await _new_client() as c:
            token = await _login(c, "factoradmin", "p@ssw0rd")
            r = await c.post(
                "/api/v1/admin/reauth",
                json={"factor": "mcp_token", "password": "x"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert r.status_code == 501
        assert r.json()["error"]["code"] == "not_implemented"
    finally:
        await _delete_user(uid)
