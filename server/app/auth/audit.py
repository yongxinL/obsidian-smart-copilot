"""Audit log writer (AUTH-06, D-25, D-26).

audit_log is NOT in 0001's RLS_TABLES list — writes succeed regardless of
the current_setting('app.current_user_id') GUC (Phase 6 will gate reads).
Used by routes/auth.py (refresh rotation events), routes/admin.py
(admin_reauth success/failure), and any future admin mutation.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import OperationContext


async def write_audit_log(
    session: AsyncSession,
    ctx: OperationContext,
    *,
    action: str,
    target_kind: str | None = None,
    target_id: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Append an audit_log row.

    Caller is responsible for committing the surrounding transaction.
    details is currently ignored — audit_log doesn't have a JSONB column
    in the 0001 schema; if needed, append a JSON-serialized blob into
    target_id or wait for a Phase 6 schema extension.
    """
    await session.execute(
        text(
            "INSERT INTO audit_log "
            "(user_id, action, target_kind, target_id, request_id, ip, user_agent, created_at) "
            "VALUES (:user_id, :action, :target_kind, :target_id, :request_id, :ip, :user_agent, now())"
        ),
        {
            "user_id": str(ctx.user_id) if ctx.user_id else None,
            "action": action,
            "target_kind": target_kind,
            "target_id": target_id,
            "request_id": ctx.request_id,
            "ip": ip,
            "user_agent": user_agent,
        },
    )
