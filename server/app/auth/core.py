"""Transport-neutral auth validators (D-17).

Pure: returns AuthResult dataclass. Never raises HTTP exceptions.
Imported by every transport adapter (REST middleware, MCP HTTP token verifier,
MCP stdio bootstrap, CLI). The transport translates AuthResult.error to the
appropriate response shape.

DB lookups for refresh / bearer go through `session_with_rls(system_operation_context())`
so 0002's RLS POLICY system-bypass OR clause admits the read — refresh and
bearer validation run BEFORE the caller's identity is known and so cannot
use a per-user GUC.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from jose import JWTError
from sqlalchemy import select

from app.auth.context import AuthResult, system_operation_context
from app.auth.mcp_tokens import sha256_token_hash
from app.auth.tokens import decode_access_jwt
from app.dependencies import session_with_rls
from app.models.mcp_token import MCPToken
from app.models.session import Session as SessionModel
from app.models.user import User
from app.settings import settings


def validate_jwt(token: str | None) -> AuthResult:
    """Decode an HS256 access JWT and project to AuthResult.

    Reads the optional `sid` claim (refresh-issued tokens carry it) and
    populates AuthResult.session_id so downstream require_fresh_auth can
    load sessions.admin_fresh_until.
    """
    if not token:
        return AuthResult(error="missing_auth")
    try:
        claims = decode_access_jwt(token, settings.jwt_signing_key)
    except JWTError:
        return AuthResult(error="invalid_token")
    try:
        user_id = uuid.UUID(claims["sub"])
    except (KeyError, ValueError):
        return AuthResult(error="invalid_token")
    role = claims.get("role")
    if role not in ("admin", "user"):
        return AuthResult(error="invalid_token")
    session_id: uuid.UUID | None = None
    sid_claim = claims.get("sid")
    if sid_claim:
        try:
            session_id = uuid.UUID(sid_claim)
        except (ValueError, TypeError):
            return AuthResult(error="invalid_token")
    return AuthResult(user_id=user_id, role=role, session_id=session_id)


async def validate_refresh(refresh_token: str | None) -> AuthResult:
    """Look up a refresh token by SHA-256 hash; verify not expired.

    Does NOT delete the row — that's services/sessions.rotate_refresh's job.
    Runs under system context so 0002's RLS system-bypass OR clause admits
    the SELECT (we don't yet know whose row this is).
    """
    if not refresh_token:
        return AuthResult(error="missing_auth")
    h = sha256_token_hash(refresh_token)
    async for session in session_with_rls(system_operation_context()):
        result = await session.execute(
            select(SessionModel, User)
            .join(User, User.id == SessionModel.user_id)
            .where(SessionModel.token_hash == h)
        )
        row = result.first()
        if row is None:
            return AuthResult(error="invalid_token")
        sess, user = row
        if sess.expires_at is not None and sess.expires_at < datetime.now(UTC):
            return AuthResult(error="invalid_token")
        if not user.is_active:
            return AuthResult(error="invalid_token")
        return AuthResult(
            user_id=sess.user_id,
            role=user.role,
            session_id=sess.id,
        )
    return AuthResult(error="invalid_token")  # unreachable; satisfies type checker


async def validate_bearer(bearer_token: str | None) -> AuthResult:
    """Verify an MCP bearer token by SHA-256 hash; reject if revoked.

    Does NOT update last_used_at — that's services/mcp_tokens.verify_token's
    job (in the request transaction). Plan 06.

    Runs under system context so 0002's RLS system-bypass OR clause admits
    the SELECT.
    """
    if not bearer_token:
        return AuthResult(error="missing_auth")
    h = sha256_token_hash(bearer_token)
    async for session in session_with_rls(system_operation_context()):
        result = await session.execute(
            select(MCPToken, User)
            .join(User, User.id == MCPToken.user_id)
            .where(MCPToken.token_hash == h, MCPToken.revoked_at.is_(None))
        )
        row = result.first()
        if row is None:
            return AuthResult(error="invalid_token")
        mcp, user = row
        if not user.is_active:
            return AuthResult(error="invalid_token")
        return AuthResult(
            user_id=mcp.user_id,
            role=user.role,
            mcp_token_id=mcp.id,
        )
    return AuthResult(error="invalid_token")  # unreachable; satisfies type checker
