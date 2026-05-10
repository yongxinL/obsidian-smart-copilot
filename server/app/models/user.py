"""User model (REQ-300).

Per D-07, one file per domain.
"""

from __future__ import annotations

import uuid  # noqa: F401 (used in Mapped[uuid.UUID] type hints)

from sqlalchemy import UUID, Boolean, String, Text
from sqlalchemy import true as sql_true
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

user_role_enum = PG_ENUM(
    "admin", "user", name="users_role_enum", create_constraint=True
)


class User(Base, TimestampMixin):
    """Users table — primary identity model."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(
        user_role_enum, nullable=False, server_default="user"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=sql_true()
    )
