"""Domain models package.

Aggregate imports are added once all model modules exist (Task 4).
Importing this package MUST cause every domain table to be registered
with Base.metadata so that Alembic autogenerate sees the complete schema.
"""

from app.models.base import Base, TimestampMixin

__all__ = ["Base", "TimestampMixin"]
