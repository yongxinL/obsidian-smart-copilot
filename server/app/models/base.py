"""SQLAlchemy 2.0 declarative base + shared column mixins.

Per D-07, one file per domain. This module provides the shared `Base`
declarative class and timestamp mixin imported by every model file.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Root declarative class for all ORM models.

    Every model module (user.py, page.py, ...) inherits from this Base
    so that `Base.metadata` enumerates the complete schema for Alembic
    autogenerate (D-05, D-06).
    """


class TimestampMixin:
    """Standard created_at/updated_at columns (server-side defaults)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
