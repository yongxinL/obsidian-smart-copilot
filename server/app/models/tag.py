"""Tag models (REQ-311): tags table + page_tags join table.

Per D-07, tag.py declares multiple closely-related tables in one file.
"""

from __future__ import annotations

import uuid

from sqlalchemy import UUID, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Tag(Base, TimestampMixin):
    """Tags table — vault-scoped label namespace."""

    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("vault_id", "name", name="uq_tags_vault_name"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    vault_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vaults.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)


class PageTag(Base):
    """Page-tag join table with composite primary key."""

    __tablename__ = "page_tags"

    page_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pages.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )
