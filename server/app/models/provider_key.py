"""Provider key model (REQ-303).

Per D-07, one file per domain.
encrypted_key MUST be LargeBinary (BYTEA) so Fernet ciphertext bytes
round-trip without text encoding ambiguity.
"""

from __future__ import annotations

import uuid  # noqa: F401 (used in Mapped[uuid.UUID] type hints)

from sqlalchemy import UUID, ForeignKey, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ProviderKey(Base, TimestampMixin):
    """Per-user encrypted API keys (Fernet-encrypted at rest)."""

    __tablename__ = "provider_keys"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_provider_keys_user_provider"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    encrypted_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    key_hint: Mapped[str] = mapped_column(String(32), nullable=False)
