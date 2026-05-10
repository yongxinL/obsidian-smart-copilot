"""Skill model (REQ-314).

Per D-07, one file per domain.
"""

from __future__ import annotations

import uuid  # noqa: F401

from sqlalchemy import UUID, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

skill_namespace_enum = PG_ENUM(
    "system", "user", name="skills_namespace_enum", create_constraint=True
)


class Skill(Base, TimestampMixin):
    """Skills table — system and per-user skill manifests."""

    __tablename__ = "skills"
    __table_args__ = (
        UniqueConstraint(
            "namespace", "user_id", "name", name="uq_skills_namespace_user_name"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    namespace: Mapped[str] = mapped_column(skill_namespace_enum, nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    manifest: Mapped[dict] = mapped_column(JSONB, nullable=True)
