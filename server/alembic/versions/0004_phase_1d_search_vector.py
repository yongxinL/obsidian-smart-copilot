"""phase_1d_search_vector

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-11

Phase 1d adds:
  * pages.search_vector TSVECTOR GENERATED ALWAYS AS (...) STORED (D-03)
    Expression uses frontmatter->>'title' because Page has no bare title column.
  * GIN index on pages.search_vector for fast FTS queries (D-01)

D-01: websearch_to_tsquery FTS over compiled_truth + frontmatter title.
D-03: tsvector generated column — never null, updated by PostgreSQL automatically.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # GENERATED ALWAYS AS requires raw SQL — SQLAlchemy has no ORM abstraction
    # for generated columns. Using frontmatter->>'title' per verified Pattern Map:
    # Page model has no bare title column; title lives in frontmatter JSONB.
    op.execute(
        """
        ALTER TABLE pages
        ADD COLUMN search_vector tsvector
            GENERATED ALWAYS AS (
                to_tsvector(
                    'english',
                    coalesce(frontmatter->>'title', '') || ' ' ||
                    coalesce(compiled_truth, '')
                )
            ) STORED
        """
    )
    op.execute(
        "CREATE INDEX ix_pages_search_vector ON pages USING GIN (search_vector)"
    )


def downgrade() -> None:
    # Drop in reverse order: index first, then column
    op.execute("DROP INDEX IF EXISTS ix_pages_search_vector")
    op.execute("ALTER TABLE pages DROP COLUMN IF EXISTS search_vector")