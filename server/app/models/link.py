"""Link model (REQ-309).

Per D-07, one file per domain.
"""

from __future__ import annotations

import uuid  # noqa: F401 (used in Mapped[uuid.UUID] type hints)
from decimal import Decimal

from sqlalchemy import UUID, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

link_source_kind_enum = PG_ENUM(
    "wikilink",
    "enrichment",
    "inferred",
    name="links_source_kind_enum",
    create_constraint=True,
)


class Link(Base, TimestampMixin):
    """Links table — page-to-entity connections with provenance."""

    __tablename__ = "links"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    src_page_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pages.id", ondelete="CASCADE"), nullable=False
    )
    dst_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
    )
    link_type: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), nullable=False, server_default="1.00"
    )
    source_kind: Mapped[str] = mapped_column(link_source_kind_enum, nullable=False)
