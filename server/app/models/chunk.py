"""Chunk model (REQ-307).

Per D-07, one file per domain.
embedding MUST be VECTOR(1536) — text-embedding-3-small dimension per CLAUDE.md.
tsv MUST be TSVECTOR — BM25 column for Phase 2a hybrid retrieval.
"""

from __future__ import annotations

import uuid  # noqa: F401 (used in Mapped[uuid.UUID] type hints)

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import UUID, Computed, ForeignKey, Text
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

chunk_kind_enum = PG_ENUM(
    "summary",
    "detail",
    "truth",
    "event",
    "enrichment",
    name="chunks_kind_enum",
    create_constraint=True,
)


class Chunk(Base, TimestampMixin):
    """Chunks table — vector + BM25 search units per page."""

    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    page_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pages.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(chunk_kind_enum, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    enriched_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    tsv: Mapped[object] = mapped_column(
        TSVECTOR,
        nullable=True,
        server_default=Computed(
            "to_tsvector('english', coalesce(enriched_content, text))",
            persisted=True,
        ),
    )
    embedding: Mapped[list[float] | None] = mapped_column(VECTOR(1536), nullable=True)
