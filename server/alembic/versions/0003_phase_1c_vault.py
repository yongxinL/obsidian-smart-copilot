"""phase_1c_vault

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-08

Phase 1c adds:
  * pages.timeline TEXT (VAULT-04, D-01) — stores below-the-line append-only event log
  * pages.deleted_by UUID FK users.id NULLABLE (VAULT-08) — who triggered soft-delete
  * page_versions.timeline TEXT (VAULT-08) — snapshot the timeline alongside compiled_truth
  * Replace page_note_type_enum values: compiled_truth/timeline/mixed (wrong — body shape,
    not Zettelkasten lifecycle) with: fleeting/literature/permanent/archived_fleeting/skill/moc (D-04)
  * pages.note_type server_default changes from 'mixed' to 'fleeting' (D-04, Pitfall 4)
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Step 1: Add new columns to pages ──────────────────────────────────────
    op.add_column(
        "pages",
        sa.Column("timeline", sa.Text(), nullable=True, server_default=""),
    )
    op.add_column(
        "pages",
        sa.Column("deleted_by", sa.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_pages_deleted_by_users",
        "pages",
        "users",
        ["deleted_by"],
        ["id"],
        ondelete="SET NULL",
    )

    # ── Step 2: Add timeline column to page_versions ──────────────────────────
    op.add_column(
        "page_versions",
        sa.Column("timeline", sa.Text(), nullable=True, server_default=""),
    )

    # ── Step 3: Replace page_note_type_enum values ────────────────────────────
    # PostgreSQL cannot DROP VALUE from an existing ENUM (Pitfall 3 / RESEARCH.md).
    # Pattern: create new type → add new column with new type → drop old column →
    # rename new column → drop old type → rename new type.
    op.execute(
        "CREATE TYPE page_note_type_enum_new AS ENUM "
        "('fleeting', 'literature', 'permanent', 'archived_fleeting', 'skill', 'moc')"
    )
    op.execute(
        "ALTER TABLE pages ADD COLUMN note_type_new page_note_type_enum_new "
        "NOT NULL DEFAULT 'fleeting'::page_note_type_enum_new"
    )
    op.execute("ALTER TABLE pages DROP COLUMN note_type")
    op.execute("ALTER TABLE pages RENAME COLUMN note_type_new TO note_type")
    op.execute("DROP TYPE page_note_type_enum")
    op.execute("ALTER TYPE page_note_type_enum_new RENAME TO page_note_type_enum")


def downgrade() -> None:
    # ── Step 1: Swap out the current note_type column for the old enum values ───
    # PostgreSQL cannot DROP TYPE that a column uses. Strategy: add new temp column
    # with old type → migrate data → drop old column → rename temp column.
    # Then rename types: new type → placeholder → old name.
    op.execute(
        "CREATE TYPE page_note_type_enum_old AS ENUM "
        "('compiled_truth', 'timeline', 'mixed')"
    )
    op.execute(
        "ALTER TABLE pages ADD COLUMN note_type_old page_note_type_enum_old "
        "NOT NULL DEFAULT 'mixed'::page_note_type_enum_old"
    )
    op.execute(
        "UPDATE pages SET note_type_old = 'mixed'::page_note_type_enum_old "
        "WHERE note_type IS NULL OR note_type = ''::page_note_type_enum"
    )
    # Map new values to their closest old equivalents
    op.execute(
        "UPDATE pages SET note_type_old = 'mixed'::page_note_type_enum_old "
        "WHERE note_type IN ('fleeting', 'literature', 'permanent', "
        "'archived_fleeting', 'skill', 'moc')"
    )
    op.execute("ALTER TABLE pages DROP COLUMN note_type")
    op.execute("ALTER TABLE pages RENAME COLUMN note_type_old TO note_type")
    # Clean up types: new type still exists (renamed from _new), rename it away
    # so we can recreate with the old name
    op.execute("ALTER TYPE page_note_type_enum RENAME TO page_note_type_enum_recycled")
    op.execute("ALTER TYPE page_note_type_enum_old RENAME TO page_note_type_enum")
    op.execute("DROP TYPE page_note_type_enum_recycled")

    # ── Step 2: Drop columns added in upgrade ──────────────────────────────────
    op.drop_constraint("fk_pages_deleted_by_users", "pages", type_="foreignkey")
    op.drop_column("pages", "deleted_by")
    op.drop_column("pages", "timeline")
    op.drop_column("page_versions", "timeline")
