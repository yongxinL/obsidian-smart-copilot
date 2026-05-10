"""Vault model (REQ-304).

Per D-07, one file per domain.
"""

from __future__ import annotations

import uuid  # noqa: F401 (used in Mapped[uuid.UUID] type hints)

from sqlalchemy import UUID, ForeignKey, Text
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

vault_kind_enum = PG_ENUM(
    "private", "shared", name="vaults_kind_enum", create_constraint=True
)


class Vault(Base, TimestampMixin):
    """Vaults table — one or more vault directories per user."""

    __tablename__ = "vaults"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    kind: Mapped[str] = mapped_column(vault_kind_enum, nullable=False)
    path: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
