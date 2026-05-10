"""Page model (REQ-305, REQ-305A, VAULT-04, VAULT-06, VAULT-08).

Per D-07, one file per domain.
Phase 1c: VAULT-04 (timeline), VAULT-06 (note_type lifecycle enum),
VAULT-08 (deleted_by).
"""

from __future__ import annotations

import uuid  # noqa: F401 (used in Mapped[uuid.UUID] type hints)
from datetime import datetime

from sqlalchemy import UUID, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

page_type_enum = PG_ENUM(
    "person",
    "company",
    "concept",
    "idea",
    "project",
    "meeting",
    "note",
    "media",
    "inbox",
    "system",
    name="pages_type_enum",
    create_constraint=True,
)

page_note_type_enum = PG_ENUM(
    "fleeting",
    "literature",
    "permanent",
    "archived_fleeting",
    "skill",
    "moc",
    name="pages_note_type_enum",
    create_constraint=True,
)


class Page(Base, TimestampMixin):
    """Pages table — core content unit with compiled-truth convention."""

    __tablename__ = "pages"
    __table_args__ = (UniqueConstraint("vault_id", "slug", name="uq_pages_vault_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    vault_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vaults.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(String(256), nullable=False)
    type: Mapped[str] = mapped_column(page_type_enum, nullable=False)
    note_type: Mapped[str] = mapped_column(
        page_note_type_enum, nullable=False, server_default="fleeting"
    )
    frontmatter: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    compiled_truth: Mapped[str] = mapped_column(Text, server_default="")
    timeline: Mapped[str | None] = mapped_column(Text, nullable=True, server_default="")
    content_hash: Mapped[str] = mapped_column(String(32), nullable=False)
    enrichment_hash: Mapped[str | None] = mapped_column(String(32), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delete_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
