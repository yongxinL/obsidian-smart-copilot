"""Index event model (REQ-367).

Per D-07, one file per domain.
"""

from __future__ import annotations

import uuid  # noqa: F401
from datetime import datetime

from sqlalchemy import UUID, BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

index_event_type_enum = PG_ENUM(
    "created",
    "updated",
    "deleted",
    "re_indexed",
    "error",
    name="index_events_event_type_enum",
    create_constraint=True,
)


class IndexEvent(Base):
    """Index events table — per-page index lifecycle tracking."""

    __tablename__ = "index_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(index_event_type_enum, nullable=False)
    page_slug: Mapped[str | None] = mapped_column(String(256), nullable=True)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
