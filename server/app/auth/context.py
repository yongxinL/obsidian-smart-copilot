"""Frozen dataclasses for transport-neutral auth (D-17, D-19, D-22).

NO FastAPI imports. NO SQLAlchemy imports. Imported by:
  * auth/core.py — pure validators (returns AuthResult)
  * routes/* + middleware — build OperationContext from AuthResult
  * services/* — consume OperationContext (transport-agnostic)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class AuthResult:
    """Pure transport-neutral result of token validation. NO FastAPI here.

    On success: user_id + role (+ session_id for refresh path, + mcp_token_id for bearer).
    On failure: error in {"invalid_token", "missing_auth", "service_unavailable"}.
    """

    user_id: uuid.UUID | None = None
    role: str | None = None
    session_id: uuid.UUID | None = None
    mcp_token_id: uuid.UUID | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class OperationContext:
    """REQ-520. Built by transport adapter from AuthResult (D-18).

    D-22: remote is transport-driven only — never derived from CWD or any heuristic.
      rest -> True, mcp_http -> True, mcp_stdio -> False, cli -> False, system -> False
    """

    user_id: uuid.UUID
    role: Literal["admin", "user"]
    transport: Literal["rest", "mcp_http", "mcp_stdio", "cli", "system"]
    remote: bool
    client_name: str
    request_id: str
    session_id: uuid.UUID | None = None
    mcp_token_id: uuid.UUID | None = None


# System user UUID — must match alembic 0002 SYSTEM_USER_ID seed (Plan 02)
SYSTEM_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def system_operation_context(
    *,
    request_id: str = "system",
    client_name: str = "system",
) -> OperationContext:
    """OperationContext for APScheduler/Alembic/CLI-system contexts (D-22).

    Used by session_with_rls(ctx) in dependencies.py (Plan 05) to set
    app.current_user_id = SYSTEM_USER_ID. RLS policies authored in 0002
    treat the system user as a regular user that owns no per-user data —
    for tables genuinely needed cross-user (audit_log, login_attempts) the
    table is excluded from RLS_TABLES.
    """
    return OperationContext(
        user_id=SYSTEM_USER_ID,
        role="admin",
        transport="system",
        remote=False,
        client_name=client_name,
        request_id=request_id,
    )
