"""Page version model (REQ-306, VAULT-08).

Per D-07, one file per domain.
Phase 1c: VAULT-08 adds timeline column for compiled-truth/timeline snapshot.
"""

from __future__ import annotations

import uuid  # noqa: F401 (used in Mapped[uuid.UUID] type hints)
from datetime import datetime

from sqlalchemy import (
    UUID,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PageVersion(Base):
    """Page versions table — history of page content snapshots."""

    __tablename__ = "page_versions"
    __table_args__ = (
        UniqueConstraint("page_id", "version", name="uq_page_versions_page_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    page_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pages.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    frontmatter: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    compiled_truth: Mapped[str] = mapped_column(Text, server_default="")
    timeline: Mapped[str | None] = mapped_column(Text, nullable=True, server_default="")
    content_hash: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
