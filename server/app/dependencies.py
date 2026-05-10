"""FastAPI dependencies. D-09: this module owns get_db_session + RLS GUC.

CLAUDE.md mandates SET app.current_user_id (NOT SET LOCAL) and always RESET
in finally. Phase 1a defensively RESET only; Phase 1b adds the SET path
after Depends(get_operation_context) authenticates the caller.

Landmine #5: SET ... = $1 is illegal SQL — utility statements don't accept
bind parameters. Use SELECT set_config(name, value, is_local=false) instead,
which IS a normal function and parameter-binds the value.

Landmine #1: PoolEvents.reset listener in database.py is the fail-safe; this
finally:-block is the primary scrub.

`session_with_rls(ctx)` is the canonical non-FastAPI alternate constructor.
It is exported and consumed by APScheduler jobs, the CLI, AND auth/core.py
(validate_refresh / validate_bearer call it under system context). Importing
it from dependencies.py is intentional even though dependencies.py imports
fastapi — `session_with_rls` itself does NOT depend on FastAPI types and
auth/core.py imports only that symbol.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import OperationContext
from app.database import async_session_factory

if TYPE_CHECKING:
    pass


async def get_operation_context(request: Request) -> OperationContext:
    """REST adapter: extract Authorization: Bearer <jwt>, validate, build OperationContext.

    Returns 401 if missing/invalid; the route never sees an unauthenticated request.
    Trusted-proxy XFF parsing populates request.state.client_ip in Plan 07.
    Reads the optional `sid` JWT claim (emitted by Plan 04 task 04-03 issue_access_jwt)
    into OperationContext.session_id so require_fresh_auth (Plan 06) can load
    sessions.admin_fresh_until.
    """
    # Local import — auth.core depends on this module (session_with_rls), so
    # we cannot top-level import to avoid a circular import.
    from app.auth.core import validate_jwt

    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    token: str | None = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):].strip()
    result = validate_jwt(token)
    if result.error is not None or result.user_id is None:
        raise HTTPException(status_code=401, detail={
            "error": {"code": "unauthorized", "message": "valid bearer token required"}
        })
    request_id = request.headers.get("x-request-id") or "unset"
    client_ip = getattr(request.state, "client_ip", None) or (request.client.host if request.client else "")
    # session_id is populated by validate_jwt from the optional sid claim
    session_id: uuid.UUID | None = result.session_id
    return OperationContext(
        user_id=result.user_id,
        role=result.role or "user",
        transport="rest",
        remote=True,
        client_name=client_ip,
        request_id=request_id,
        session_id=session_id,
    )


async def get_db_session(
    ctx: OperationContext = Depends(get_operation_context),
) -> AsyncIterator[AsyncSession]:
    """Open an async session, SET 3 GUCs, yield, RESET in finally."""
    async with async_session_factory() as session:
        try:
            # Landmine #5 — set_config(name, value, is_local=false), NOT SET ... = $1
            await session.execute(
                text("SELECT set_config('app.current_user_id', :uid, false)"),
                {"uid": str(ctx.user_id)},
            )
            await session.execute(
                text("SELECT set_config('app.current_user_role', :role, false)"),
                {"role": ctx.role},
            )
            await session.execute(
                text("SELECT set_config('app.request_id', :rid, false)"),
                {"rid": ctx.request_id},
            )
            yield session
        finally:
            # Canonical Phase 1a defensive cleanup, extended to all 3 GUCs
            try:
                await session.execute(text("RESET app.current_user_id"))
                await session.execute(text("RESET app.current_user_role"))
                await session.execute(text("RESET app.request_id"))
            except Exception:  # noqa: BLE001 — defensive cleanup only
                pass
            await session.close()


async def session_with_rls(ctx: OperationContext) -> AsyncIterator[AsyncSession]:
    """Non-FastAPI alternate constructor of get_db_session.

    Used by APScheduler jobs, the CLI, AND auth/core.py (validate_refresh /
    validate_bearer call this under system_operation_context() — the 0002
    RLS POLICY system-bypass OR clause is what admits those reads).

    Caller drives lifecycle:

        async for session in session_with_rls(ctx):
            # ... do work ...
    """
    async with async_session_factory() as session:
        try:
            await session.execute(
                text("SELECT set_config('app.current_user_id', :uid, false)"),
                {"uid": str(ctx.user_id)},
            )
            await session.execute(
                text("SELECT set_config('app.current_user_role', :role, false)"),
                {"role": ctx.role},
            )
            await session.execute(
                text("SELECT set_config('app.request_id', :rid, false)"),
                {"rid": ctx.request_id},
            )
            yield session
        finally:
            try:
                await session.execute(text("RESET app.current_user_id"))
                await session.execute(text("RESET app.current_user_role"))
                await session.execute(text("RESET app.request_id"))
            except Exception:  # noqa: BLE001
                pass
            await session.close()
