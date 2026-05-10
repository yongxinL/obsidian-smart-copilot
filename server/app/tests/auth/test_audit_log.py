"""audit_log emission for admin + auth events — AUTH-06 (Plan 05/07)."""

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


async def _login(client: AsyncClient, username: str, password: str) -> str:
    r = await client.post(
        "/auth/login", json={"username": username, "password": password}
    )
    assert r.status_code == 200, f"login failed: {r.text}"
    return r.json()["access_jwt"]


async def test_admin_op_writes_audit_log() -> None:
    uid = await _create_user("auditadmin1", "p@ssw0rd", role="admin")
    try:
        async with await _new_client() as c:
            token = await _login(c, "auditadmin1", "p@ssw0rd")
            r = await c.post(
                "/api/v1/admin/reauth",
                json={"factor": "password", "password": "p@ssw0rd"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r.status_code == 200, r.text
        async for session in session_with_rls(system_operation_context()):
            row = (
                await session.execute(
                    text(
                        "SELECT action FROM audit_log WHERE user_id = :uid AND action = 'admin_reauth'"
                    ),
                    {"uid": str(uid)},
                )
            ).first()
            assert row is not None, "audit_log row with action='admin_reauth' expected"
    finally:
        await _delete_user(uid)


async def test_admin_reauth_success_writes_audit_log() -> None:
    uid = await _create_user("auditadmin2", "s3cr3t!", role="admin")
    try:
        async with await _new_client() as c:
            token = await _login(c, "auditadmin2", "s3cr3t!")
            r = await c.post(
                "/api/v1/admin/reauth",
                json={"factor": "password", "password": "s3cr3t!"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r.status_code == 200, r.text
        async for session in session_with_rls(system_operation_context()):
            cnt = (
                await session.execute(
                    text(
                        "SELECT count(*) FROM audit_log WHERE user_id = :uid AND action = 'admin_reauth'"
                    ),
                    {"uid": str(uid)},
                )
            ).scalar_one()
            assert cnt >= 1, "admin_reauth audit row expected"
    finally:
        await _delete_user(uid)


async def test_admin_reauth_failure_writes_audit_log_with_reason() -> None:
    uid = await _create_user("auditfailadmin", "p@ssw0rd", role="admin")
    try:
        async with await _new_client() as c:
            token = await _login(c, "auditfailadmin", "p@ssw0rd")
            r = await c.post(
                "/api/v1/admin/reauth",
                json={"factor": "password", "password": "WRONG"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r.status_code == 401
        async for session in session_with_rls(system_operation_context()):
            row = (
                await session.execute(
                    text(
                        "SELECT action FROM audit_log WHERE user_id = :uid AND action = 'admin_reauth_failed'"
                    ),
                    {"uid": str(uid)},
                )
            ).first()
            assert row is not None, (
                "audit_log row with action='admin_reauth_failed' expected"
            )
    finally:
        await _delete_user(uid)


async def test_refresh_rotation_audit_logged() -> None:
    uid = await _create_user("auditrefresh", "p@ssw0rd")
    try:
        async with await _new_client() as c:
            r = await c.post(
                "/auth/login", json={"username": "auditrefresh", "password": "p@ssw0rd"}
            )
            assert r.status_code == 200, r.text
            old_refresh = r.json()["refresh_token"]
            r2 = await c.post("/auth/refresh", json={"refresh_token": old_refresh})
            assert r2.status_code == 200, r2.text
        # rotate_refresh runs under system_operation_context so audit_log user_id is SYSTEM_USER_ID
        async for session in session_with_rls(system_operation_context()):
            row = (
                await session.execute(
                    text(
                        "SELECT action FROM audit_log WHERE action = 'refresh_rotated' ORDER BY created_at DESC LIMIT 1"
                    ),
                )
            ).first()
            assert row is not None, (
                "audit_log row with action='refresh_rotated' expected"
            )
    finally:
        await _delete_user(uid)
