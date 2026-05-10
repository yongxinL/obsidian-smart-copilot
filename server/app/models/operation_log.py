"""Operation log model (REQ-365).

Per D-07, one file per domain.
"""

from __future__ import annotations

import uuid
from datetime import datetime  # noqa: F401

from sqlalchemy import UUID, BigInteger, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class OperationLog(Base):
    """Operation log table — low-level mutation tracking."""

    __tablename__ = "operation_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    operation: Mapped[str] = mapped_column(String(128), nullable=False)
    target_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
