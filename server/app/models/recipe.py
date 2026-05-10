"""Recipe model (REQ-315).

Per D-07, one file per domain.
"""

from __future__ import annotations

import uuid  # noqa: F401

from sqlalchemy import UUID, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

recipe_namespace_enum = PG_ENUM(
    "system", "user", name="recipes_namespace_enum", create_constraint=True
)


class Recipe(Base, TimestampMixin):
    """Recipes table — YAML workflow definitions with namespace scoping."""

    __tablename__ = "recipes"
    __table_args__ = (
        UniqueConstraint(
            "namespace", "user_id", "name", name="uq_recipes_namespace_user_name"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    namespace: Mapped[str] = mapped_column(recipe_namespace_enum, nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    yaml: Mapped[str] = mapped_column(Text, nullable=False)
