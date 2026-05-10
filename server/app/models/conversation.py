"""Conversation models (REQ-360, REQ-361): conversations + messages.

Per D-07, conversation.py declares multiple closely-related tables in one file.
"""

from __future__ import annotations

import uuid
from datetime import datetime  # noqa: F401

from sqlalchemy import UUID, Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy import false as sql_false
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

mcp_mode_enum = PG_ENUM(
    "disabled",
    "client",
    "server",
    name="conversations_mcp_mode_enum",
    create_constraint=True,
)

message_role_enum = PG_ENUM(
    "system",
    "user",
    "assistant",
    "tool",
    name="messages_role_enum",
    create_constraint=True,
)


class Conversation(Base, TimestampMixin):
    """Conversations table — agent chat sessions."""

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    mcp_mode: Mapped[str] = mapped_column(
        mcp_mode_enum, nullable=False, server_default="client"
    )
    web_search_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=sql_false()
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )


class Message(Base):
    """Messages table — conversation turns with citations."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(message_role_enum, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="[]")
    tool_calls: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
