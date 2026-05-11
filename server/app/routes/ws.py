"""WebSocket /api/v1/ws — first-frame JWT auth + per-user filtered events (REST-03).

D-07: events arrive via PostgreSQL LISTEN/NOTIFY; this handler subscribes to
the per-user queue exposed by app.state.index_event_listener.
D-08: events are filtered by user_id; a socket only sees its owner's events.
D-09: auth via first frame {"type":"auth","data":{"token":"<jwt>"}}; token in
query string is IGNORED.
"""

from __future__ import annotations

import asyncio
import contextlib

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.auth.context import OperationContext
from app.auth.core import validate_jwt
from app.settings import settings

log = structlog.get_logger("smart_copilot.ws")

router = APIRouter()


def _auth_error(code: str, message: str) -> dict:
    return {"type": "auth_error", "error": {"code": code, "message": message}}


@router.websocket("/api/v1/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    listener = ws.app.state.index_event_listener
    queue = None
    user_id = None
    try:
        try:
            frame = await asyncio.wait_for(
                ws.receive_json(),
                timeout=settings.ws_first_frame_timeout_seconds,
            )
        except (TimeoutError, ValueError):
            await ws.send_json(
                _auth_error("unauthorized", "first frame missing or invalid")
            )
            await ws.close(code=1008)
            return

        if not isinstance(frame, dict) or frame.get("type") != "auth":
            await ws.send_json(_auth_error("unauthorized", "first frame must be auth"))
            await ws.close(code=1008)
            return

        token = (
            ((frame.get("data") or {}).get("token"))
            if isinstance(frame.get("data"), dict)
            else None
        )
        result = validate_jwt(token)
        if result.error is not None or result.user_id is None:
            await ws.send_json(
                _auth_error("unauthorized", result.error or "invalid token")
            )
            await ws.close(code=1008)
            return

        user_id = result.user_id
        # Build OperationContext for downstream usage (audit/log only — WS path doesn't touch DB here).
        ctx = OperationContext(
            user_id=result.user_id,
            role=result.role or "user",
            transport="rest",
            remote=True,
            client_name="ws",
            request_id="ws",
            session_id=result.session_id,
        )
        log.info("ws_authenticated", user_id=str(ctx.user_id))

        await ws.send_json({"type": "auth_ok", "data": {"user_id": str(ctx.user_id)}})

        queue = await listener.subscribe(user_id)

        # Pump events until the client disconnects.
        while True:
            event = await queue.get()
            if ws.client_state != WebSocketState.CONNECTED:
                break
            await ws.send_json({"type": "index_event", "data": event})
    except WebSocketDisconnect:
        pass
    finally:
        if queue is not None and user_id is not None:
            with contextlib.suppress(Exception):
                await listener.unsubscribe(user_id, queue)
