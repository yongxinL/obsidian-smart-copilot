"""Trusted-proxy XFF integration — AUTH-08 (Plan 07)."""
from __future__ import annotations

import pytest
<<<<<<< HEAD
from app.routes.admin import router as admin_router
from app.routes.auth import router as auth_router
=======
>>>>>>> worktree-agent-ab6ce35163019e143
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.auth.context import system_operation_context
from app.auth.middleware import TrustedProxyMiddleware
from app.dependencies import session_with_rls
<<<<<<< HEAD
=======
from app.routes.admin import router as admin_router
from app.routes.auth import router as auth_router
>>>>>>> worktree-agent-ab6ce35163019e143

pytestmark = [pytest.mark.auth, pytest.mark.integration]


def _build_app(trust: bool, cidrs: list[str]) -> FastAPI:
    """Build a minimal app with the given proxy settings for testing."""
    from fastapi import HTTPException, Request
    from fastapi.responses import JSONResponse

    a = FastAPI()
    a.add_middleware(TrustedProxyMiddleware, trust_proxy=trust, allowlist_cidrs=cidrs)

    @a.exception_handler(HTTPException)
    async def _flatten(request: Request, exc: HTTPException) -> JSONResponse:  # noqa: ARG001
        payload = exc.detail
        if not isinstance(payload, dict):
            payload = {"detail": payload}
        return JSONResponse(status_code=exc.status_code, content=payload)

    a.include_router(auth_router)
    a.include_router(admin_router)
    return a


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
        await session.execute(text("DELETE FROM login_attempts WHERE username LIKE 'xff%'"))
        await session.commit()


async def test_xff_used_when_peer_trusted() -> None:
    """When peer is in trust CIDR, rate-limit row ip = left-most XFF."""
    uid = await _create_user("xffuser1", "p@ssw0rd")
    try:
        # 127.0.0.1 is in 127.0.0.0/8 so XFF should be trusted
        test_app = _build_app(trust=True, cidrs=["127.0.0.0/8"])
        xff_ip = "1.2.3.4"
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
            for _ in range(10):
                await c.post(
                    "/auth/login",
                    json={"username": "xffuser1", "password": "WRONG"},
                    headers={"X-Forwarded-For": xff_ip},
                )
        # Check that login_attempts rows have ip='1.2.3.4'
        async for session in session_with_rls(system_operation_context()):
            row = (await session.execute(
                text("SELECT count(*) FROM login_attempts WHERE username='xffuser1' AND ip = :ip"),
                {"ip": xff_ip},
            )).scalar_one()
            assert row > 0, f"Expected login_attempts rows with ip={xff_ip}"
    finally:
        async for s in session_with_rls(system_operation_context()):
            await s.execute(text("DELETE FROM login_attempts WHERE username='xffuser1'"))
            await s.commit()
        await _delete_user(uid)


async def test_xff_ignored_when_untrusted_peer() -> None:
    """When peer is NOT in trust CIDR, use peer IP regardless of XFF."""
    uid = await _create_user("xffuser2", "p@ssw0rd")
    try:
        # 10.0.0.0/8 does NOT include 127.0.0.1 (the test client peer)
        test_app = _build_app(trust=True, cidrs=["10.0.0.0/8"])
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
            await c.post(
                "/auth/login",
                json={"username": "xffuser2", "password": "WRONG"},
                headers={"X-Forwarded-For": "203.0.113.10"},
            )
        # Row should have ip=127.0.0.1 (peer wins, XFF ignored)
        async for session in session_with_rls(system_operation_context()):
            row = (await session.execute(
                text("SELECT ip FROM login_attempts WHERE username='xffuser2' LIMIT 1"),
            )).first()
            assert row is not None
            assert str(row[0]) == "127.0.0.1", f"Expected peer IP 127.0.0.1, got {row[0]}"
    finally:
        async for s in session_with_rls(system_operation_context()):
            await s.execute(text("DELETE FROM login_attempts WHERE username='xffuser2'"))
            await s.commit()
        await _delete_user(uid)


async def test_rate_limit_keys_on_xff_when_trusted() -> None:
    """Rate limit keys on XFF IP when trusted; different XFF IP is not limited."""
    uid = await _create_user("xffuser3", "p@ssw0rd")
    try:
        test_app = _build_app(trust=True, cidrs=["127.0.0.0/8"])
        xff_ip = "1.2.3.4"
        other_xff = "5.6.7.8"
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
            # 10 failures with xff=1.2.3.4
            for _ in range(10):
                await c.post(
                    "/auth/login",
                    json={"username": "xffuser3", "password": "WRONG"},
                    headers={"X-Forwarded-For": xff_ip},
                )
            # 11th with same XFF — should be rate-limited
            r_limited = await c.post(
                "/auth/login",
                json={"username": "xffuser3", "password": "WRONG"},
                headers={"X-Forwarded-For": xff_ip},
            )
            assert r_limited.status_code == 429, f"Expected 429, got {r_limited.status_code}: {r_limited.text}"
            # Same user but different XFF — should NOT be rate-limited (different (ip,username) key)
            r_ok = await c.post(
                "/auth/login",
                json={"username": "xffuser3", "password": "WRONG"},
                headers={"X-Forwarded-For": other_xff},
            )
            assert r_ok.status_code == 401, f"Different XFF should not be rate-limited, got {r_ok.status_code}"
    finally:
        async for s in session_with_rls(system_operation_context()):
            await s.execute(text("DELETE FROM login_attempts WHERE username='xffuser3'"))
            await s.commit()
        await _delete_user(uid)
