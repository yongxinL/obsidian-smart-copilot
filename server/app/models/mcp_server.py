"""MCP server model (REQ-370).

Per D-07, one file per domain.
"""

from __future__ import annotations

import uuid  # noqa: F401

from sqlalchemy import UUID, Boolean, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

mcp_server_type_enum = PG_ENUM(
    "stdio",
    "streamable_http",
    name="mcp_servers_type_enum",
    create_constraint=True,
)


class MCPServer(Base, TimestampMixin):
    """MCP servers table — external MCP server registry."""

    __tablename__ = "mcp_servers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(mcp_server_type_enum, nullable=False)
    command: Mapped[str | None] = mapped_column(String(256), nullable=True)
    args: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )
    always_allow: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
