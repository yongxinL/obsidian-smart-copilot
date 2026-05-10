"""Golden eval models (REQ-372-374): suites, queries, runs.

Per D-07, golden_eval.py declares multiple closely-related tables in one file.
"""

from __future__ import annotations

import uuid
from datetime import datetime  # noqa: F401

from sqlalchemy import UUID, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

golden_suite_scope_enum = PG_ENUM(
    "system",
    "user",
    name="golden_query_suites_scope_enum",
    create_constraint=True,
)


class GoldenQuerySuite(Base, TimestampMixin):
    """Golden query suites table — benchmark groupings."""

    __tablename__ = "golden_query_suites"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scope: Mapped[str] = mapped_column(golden_suite_scope_enum, nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)


class GoldenQuery(Base, TimestampMixin):
    """Golden queries table — individual benchmark queries."""

    __tablename__ = "golden_queries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    suite_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("golden_query_suites.id", ondelete="CASCADE"),
        nullable=False,
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    expected_slugs: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )


class GoldenQueryRun(Base):
    """Golden query runs table — per-query evaluation metrics."""

    __tablename__ = "golden_query_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    query_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("golden_queries.id", ondelete="CASCADE"),
        nullable=False,
    )
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False)
    ran_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
