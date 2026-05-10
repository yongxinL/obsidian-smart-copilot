"""Memory model (REQ-362).

Per D-07, one file per domain.
"""

from __future__ import annotations

import uuid  # noqa: F401

from sqlalchemy import UUID, Boolean, ForeignKey, Text
from sqlalchemy import false as sql_false
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Memory(Base, TimestampMixin):
    """Memories table — consolidated conversation insights."""

    __tablename__ = "memories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=sql_false()
    )
