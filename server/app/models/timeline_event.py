"""Timeline event model (REQ-310).

Per D-07, one file per domain.
"""

from __future__ import annotations

import uuid  # noqa: F401 (used in Mapped[uuid.UUID] type hints)
from datetime import datetime

from sqlalchemy import UUID, Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TimelineEvent(Base):
    """Timeline events table — below-the-line append-only event log per page."""

    __tablename__ = "timeline_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    page_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pages.id", ondelete="CASCADE"), nullable=False
    )
    event_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
