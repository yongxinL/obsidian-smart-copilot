"""Session, refresh-token, and login-attempt service (transport-agnostic).

D-03: refresh rotation is rotate-and-revoke in a single transaction.
D-07/D-08: sliding-window rate limit; wipe attempts on successful login.
D-26: audit_log entries on rotation success/failure.
Landmine #9: record_login_attempt INSERTs in its OWN transaction so a
downstream rollback cannot erase the failure record.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.audit import write_audit_log
from app.auth.context import OperationContext
from app.auth.mcp_tokens import sha256_token_hash
from app.auth.tokens import issue_access_jwt
from app.models.login_attempt import LoginAttempt
from app.models.session import Session as SessionModel
from app.models.user import User
from app.settings import settings


class InvalidToken(Exception):
    ...


class RateLimited(Exception):
    def __init__(self, retry_after_seconds: int):
        self.retry_after_seconds = retry_after_seconds


def _now() -> datetime:
    return datetime.now(UTC)


async def record_login_attempt(
    session: AsyncSession, *, ip: str, username: str, request_id: str | None = None, user_agent: str | None = None
) -> None:
    """Landmine #9: INSERT in own transaction; commit before password verify."""
    async with session.begin():
        session.add(LoginAttempt(
            ip=ip,
            username=username,
            user_agent=user_agent,
            request_id=request_id,
        ))


async def check_rate_limit(
    session: AsyncSession, *, ip: str, username: str
) -> int | None:
    """Sliding window. Returns retry_after_seconds if rate-limited, else None."""
    window = settings.login_rate_limit_window_seconds
    max_fail = settings.login_rate_limit_max_failures
    row = (await session.execute(
        text(
            "SELECT count(*) AS cnt, "
            "EXTRACT(epoch FROM (now() - min(attempted_at)))::int AS oldest_age_s "
            "FROM login_attempts "
            "WHERE ip = :ip AND username = :u "
            "AND attempted_at >= now() - make_interval(secs => :window)"
        ),
        {"ip": ip, "u": username, "window": window},
    )).first()
    cnt = int(row[0] or 0)
    oldest_age = int(row[1] or 0)
    if cnt < max_fail:
        return None
    retry_after = max(1, window - oldest_age)
    return retry_after


async def wipe_login_attempts(
    session: AsyncSession, *, ip: str, username: str
) -> None:
    """D-08: clear (ip, username) attempts on successful login."""
    await session.execute(
        delete(LoginAttempt).where(
            LoginAttempt.ip == ip,
            LoginAttempt.username == username,
        )
    )


async def issue_session_pair(
    session: AsyncSession, ctx: OperationContext, *, user: User
) -> tuple[str, str, uuid.UUID]:
    """Mint a new (access_jwt, refresh_token, session_id) triple."""
    refresh_raw = secrets.token_urlsafe(32)
    refresh_hash = sha256_token_hash(refresh_raw)
    sess_id = uuid.uuid4()
    sess_row = SessionModel(
        id=sess_id,
        user_id=user.id,
        token_hash=refresh_hash,
        expires_at=_now() + timedelta(seconds=settings.jwt_refresh_ttl_seconds),
    )
    session.add(sess_row)
    await session.flush()
    # Thread session_id into the JWT as `sid` claim — Plan 04 task 04-03 emits
    # it, Plan 05 task 05-01 parses it into AuthResult.session_id.
    access = issue_access_jwt(
        user_id=user.id,
        role=user.role,
        signing_key=settings.jwt_signing_key,
        ttl_seconds=settings.jwt_access_ttl_seconds,
        session_id=sess_id,
    )
    return access, refresh_raw, sess_id


async def rotate_refresh(
    session: AsyncSession, ctx: OperationContext, *, raw_refresh: str
) -> tuple[str, str]:
    """D-03: atomic rotate-and-revoke in a single transaction.

    Replay of an old refresh hash → row not found → InvalidToken (theft signal).
    Writes audit_log on success (D-26) and failure.
    """
    rh = sha256_token_hash(raw_refresh)
    async with session.begin():
        existing = (
            await session.execute(
                select(SessionModel, User)
                .join(User, User.id == SessionModel.user_id)
                .where(SessionModel.token_hash == rh)
                .with_for_update()
            )
        ).first()
        if existing is None:
            # Theft signal — log even though session is unknown
            await write_audit_log(
                session, ctx, action="refresh_rotate_failed",
                target_kind="session", target_id=None,
            )
            raise InvalidToken("refresh not found")
        old_sess, user = existing
        if old_sess.expires_at is not None and old_sess.expires_at < _now():
            await write_audit_log(
                session, ctx, action="refresh_rotate_failed",
                target_kind="session", target_id=str(old_sess.id),
            )
            raise InvalidToken("refresh expired")
        # DELETE old
        await session.execute(delete(SessionModel).where(SessionModel.id == old_sess.id))
        # INSERT new
        new_refresh = secrets.token_urlsafe(32)
        new_id = uuid.uuid4()
        session.add(SessionModel(
            id=new_id,
            user_id=user.id,
            token_hash=sha256_token_hash(new_refresh),
            expires_at=_now() + timedelta(seconds=settings.jwt_refresh_ttl_seconds),
        ))
        access = issue_access_jwt(
            user_id=user.id,
            role=user.role,
            signing_key=settings.jwt_signing_key,
            ttl_seconds=settings.jwt_access_ttl_seconds,
            session_id=new_id,
        )
        await write_audit_log(
            session, ctx, action="refresh_rotated",
            target_kind="session", target_id=str(new_id),
        )
    return access, new_refresh


async def revoke_session(
    session: AsyncSession, *, session_id: uuid.UUID
) -> None:
    await session.execute(delete(SessionModel).where(SessionModel.id == session_id))


async def set_admin_fresh(
    session: AsyncSession, *, session_id: uuid.UUID, minutes: int
) -> None:
    """D-12: stamp admin_fresh_until = now() + interval 'X minutes'."""
    await session.execute(
        update(SessionModel)
        .where(SessionModel.id == session_id)
        .values(admin_fresh_until=_now() + timedelta(minutes=minutes))
    )