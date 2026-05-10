"""Entity model (REQ-308).

Per D-07, one file per domain.
"""

from __future__ import annotations

import uuid  # noqa: F401 (used in Mapped[uuid.UUID] type hints)

from sqlalchemy import UUID, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

entity_kind_enum = PG_ENUM(
    "person",
    "company",
    "concept",
    "idea",
    "project",
    name="entities_kind_enum",
    create_constraint=True,
)


class Entity(Base, TimestampMixin):
    """Entities table — typed graph nodes (people, companies, concepts)."""

    __tablename__ = "entities"
    __table_args__ = (
        UniqueConstraint("vault_id", "canonical_slug", name="uq_entities_vault_slug"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    vault_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vaults.id"), nullable=False
    )
    kind: Mapped[str] = mapped_column(entity_kind_enum, nullable=False)
    canonical_slug: Mapped[str] = mapped_column(String(256), nullable=False)
    aliases: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )
