"""WebSocket auth tests (D-09)."""

from __future__ import annotations

import uuid

import pytest

from app.auth.tokens import issue_access_jwt
from app.models.user import User
from app.models.vault import Vault
from app.settings import settings


async def _seed_user_with_vault(
    user_id: uuid.UUID,
    vault_id: uuid.UUID,
    session,
) -> tuple[uuid.UUID, str]:
    """Seed a user + private vault, return (user_id, jwt)."""
    session.add(
        User(
            id=user_id,
            username=f"user_{user_id.hex[:8]}",
            email=f"{user_id}@test.local",
            password_hash="x",
            role="user",
            is_active=True,
        )
    )
    session.add(
        Vault(
            id=vault_id,
            owner_user_id=user_id,
            kind="private",
            path=f"/vaults/{user_id}",
        )
    )
    await session.commit()

    jwt = issue_access_jwt(
        user_id=user_id,
        role="user",
        signing_key=settings.jwt_signing_key,
        ttl_seconds=300,
    )
    return user_id, jwt


@pytest.mark.integration
async def test_ws_close_when_first_frame_missing(db_session) -> None:
    """No first frame → server sends auth_error then closes with 1008."""
    from app.main import app

    class _Stub:
        async def start(self): ...
        async def stop(self): ...
        async def subscribe(self, _):
            from asyncio import Queue

            return Queue()

        async def unsubscribe(self, _u, _q): ...

    app.state.index_event_listener = _Stub()
    from fastapi.testclient import TestClient

    with TestClient(app).websocket_connect("/api/v1/ws") as ws:
        # Don't send any frame — server must time out and close with auth_error.
        msg = ws.receive_json()
        assert msg["type"] == "auth_error"
        assert msg["error"]["code"] == "unauthorized"


@pytest.mark.integration
async def test_ws_close_when_invalid_token(db_session) -> None:
    """Invalid JWT → server sends auth_error then closes with 1008."""
    from app.main import app

    class _Stub:
        async def start(self): ...
        async def stop(self): ...
        async def subscribe(self, _):
            from asyncio import Queue

            return Queue()

        async def unsubscribe(self, _u, _q): ...

    app.state.index_event_listener = _Stub()
    from fastapi.testclient import TestClient

    with TestClient(app).websocket_connect("/api/v1/ws") as ws:
        ws.send_json({"type": "auth", "data": {"token": "not-a-real-jwt"}})
        msg = ws.receive_json()
        assert msg["type"] == "auth_error"
        assert msg["error"]["code"] == "unauthorized"


@pytest.mark.integration
async def test_ws_token_in_query_string_is_ignored(db_session) -> None:
    """D-09: query-string token must be ignored; only first-frame auth supported."""
    from app.main import app

    class _Stub:
        async def start(self): ...
        async def stop(self): ...
        async def subscribe(self, _):
            from asyncio import Queue

            return Queue()

        async def unsubscribe(self, _u, _q): ...

    app.state.index_event_listener = _Stub()
    from fastapi.testclient import TestClient

    # Seed a real user so we can get a real JWT
    user_id = uuid.uuid4()
    vault_id = uuid.uuid4()
    _, jwt = await _seed_user_with_vault(user_id, vault_id, db_session)

    # Pass valid JWT in query string — should be IGNORED
    with TestClient(app).websocket_connect(f"/api/v1/ws?token={jwt}") as ws:
        # Send a NON-auth first frame; server must reject because query string is ignored.
        ws.send_json({"type": "ping"})
        msg = ws.receive_json()
        assert msg["type"] == "auth_error"
