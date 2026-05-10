"""Dream audit log model (REQ-363).

Per D-07, one file per domain.
"""

from __future__ import annotations

import uuid  # noqa: F401
from datetime import datetime

from sqlalchemy import UUID, BigInteger, DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

dream_audit_log_kind_enum = PG_ENUM(
    "consolidate",
    "audit",
    "extract",
    "backup",
    name="dream_audit_log_kind_enum",
    create_constraint=True,
)

dream_audit_log_status_enum = PG_ENUM(
    "success",
    "partial",
    "failed",
    name="dream_audit_log_status_enum",
    create_constraint=True,
)


class DreamAuditLog(Base):
    """Dream audit log table — nightly consolidation run records."""

    __tablename__ = "dream_audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    kind: Mapped[str] = mapped_column(dream_audit_log_kind_enum, nullable=False)
    status: Mapped[str] = mapped_column(dream_audit_log_status_enum, nullable=False)
    pages_processed: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
