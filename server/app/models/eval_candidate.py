"""Eval candidate model (REQ-316).

Per D-07, one file per domain.
"""

from __future__ import annotations

import uuid
from datetime import datetime  # noqa: F401

from sqlalchemy import UUID, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

eval_candidate_kind_enum = PG_ENUM(
    "golden",
    "regression",
    "manual",
    name="eval_candidates_kind_enum",
    create_constraint=True,
)


class EvalCandidate(Base):
    """Eval candidates table — golden/regression query benchmarks."""

    __tablename__ = "eval_candidates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(
        eval_candidate_kind_enum, nullable=False, server_default="golden"
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_slugs: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
