"""Job model (REQ-312).

Per D-07, one file per domain.
Note: apscheduler_jobs table is intentionally NOT a model — APScheduler manages it.
"""

from __future__ import annotations

import uuid
from datetime import datetime  # noqa: F401

from sqlalchemy import UUID, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

job_kind_enum = PG_ENUM(
    "index_page",
    "enrich_entity",
    "dream_consolidate",
    "embed_migration",
    "backup",
    "cleanup",
    name="jobs_kind_enum",
    create_constraint=True,
)

job_status_enum = PG_ENUM(
    "pending",
    "running",
    "success",
    "failed",
    "cancelled",
    name="jobs_status_enum",
    create_constraint=True,
)


class Job(Base, TimestampMixin):
    """Jobs table — durable parent-child DAG jobs via APScheduler."""

    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=True
    )
    kind: Mapped[str] = mapped_column(job_kind_enum, nullable=False)
    status: Mapped[str] = mapped_column(
        job_status_enum, nullable=False, server_default="pending"
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    idempotency_key: Mapped[str | None] = mapped_column(
        Text, unique=True, nullable=True
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
