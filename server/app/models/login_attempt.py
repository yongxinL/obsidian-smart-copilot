"""Login attempt domain model — REQ-402 / D-05.

Table: login_attempts
System-internal table for sliding-window login throttling. Per D-06, NOT under
user RLS — written by the auth path regardless of who is authenticated.
Per D-07, one file per domain.
"""

from __future__ import annotations

from sqlalchemy import BigInteger, DateTime, String, Text
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LoginAttempt(Base):
    """Append-only record of a failed login attempt (sliding-window rate limit)."""

    __tablename__ = "login_attempts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # No FK — usernames may not match an existing user (D-06)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    ip: Mapped[object] = mapped_column(INET, nullable=False)
    attempted_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
