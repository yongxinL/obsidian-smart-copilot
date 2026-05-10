"""phase_1b_auth

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-10

Phase 1b adds:
  * login_attempts table (D-05) — system-internal, NO RLS
  * sessions.admin_fresh_until column (D-11)
  * 22 RLS POLICY blocks (one per RLS_TABLES entry from 0001) — owner-only
    with explicit system-user bypass OR clause (so auth-pipeline reads
    of sessions/mcp_tokens succeed before per-user GUC is set)
  * system user seed (deterministic UUID for APScheduler/Alembic contexts)
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# System user UUID — deterministic so every container boot resolves to the
# same row even if the seed is re-run. Used as OperationContext.user_id for
# APScheduler/Alembic contexts (see RESEARCH §Open Question 2 resolution).
SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# Local-owner tables: owner column is on the table itself (user_id)
# ---------------------------------------------------------------------------
RLS_OWNER_LOCAL: list[tuple[str, str]] = [
    ("provider_keys", "user_id"),
    ("sessions", "user_id"),
    ("mcp_tokens", "user_id"),
    ("eval_candidates", "user_id"),
    ("conversations", "user_id"),
    ("memories", "user_id"),
    ("projects", "user_id"),
    ("llm_usage", "user_id"),
    ("index_events", "user_id"),
    ("user_settings", "user_id"),
]


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # 1. Create login_attempts table (D-05 / D-06 — system-internal, NO RLS)
    # -----------------------------------------------------------------------
    op.create_table(
        "login_attempts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("ip", postgresql.INET(), nullable=False),
        sa.Column(
            "attempted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS login_attempts_lookup_idx "
        "ON login_attempts (ip, username, attempted_at DESC)"
    )

    # -----------------------------------------------------------------------
    # 2. Add sessions.admin_fresh_until column (D-11)
    # -----------------------------------------------------------------------
    op.add_column(
        "sessions",
        sa.Column("admin_fresh_until", sa.DateTime(timezone=True), nullable=True),
    )

    # -----------------------------------------------------------------------
    # 3. RLS POLICIES — local-owner tables
    #    Pattern: owner column = current_setting OR system-user bypass
    #    Expanded from loop (see RLS_OWNER_LOCAL) so verification greps find them.
    # -----------------------------------------------------------------------

    # provider_keys — user_id
    op.execute(f"""
        CREATE POLICY provider_keys_owner ON provider_keys
            USING (
                user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                OR current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
            )
            WITH CHECK (
                user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                OR current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
            )
    """)

    # sessions — user_id
    op.execute(f"""
        CREATE POLICY sessions_owner ON sessions
            USING (
                user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                OR current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
            )
            WITH CHECK (
                user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                OR current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
            )
    """)

    # mcp_tokens — user_id
    op.execute(f"""
        CREATE POLICY mcp_tokens_owner ON mcp_tokens
            USING (
                user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                OR current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
            )
            WITH CHECK (
                user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                OR current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
            )
    """)

    # eval_candidates — user_id
    op.execute(f"""
        CREATE POLICY eval_candidates_owner ON eval_candidates
            USING (
                user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                OR current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
            )
            WITH CHECK (
                user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                OR current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
            )
    """)

    # conversations — user_id
    op.execute(f"""
        CREATE POLICY conversations_owner ON conversations
            USING (
                user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                OR current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
            )
            WITH CHECK (
                user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                OR current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
            )
    """)

    # memories — user_id
    op.execute(f"""
        CREATE POLICY memories_owner ON memories
            USING (
                user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                OR current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
            )
            WITH CHECK (
                user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                OR current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
            )
    """)

    # projects — user_id
    op.execute(f"""
        CREATE POLICY projects_owner ON projects
            USING (
                user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                OR current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
            )
            WITH CHECK (
                user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                OR current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
            )
    """)

    # llm_usage — user_id
    op.execute(f"""
        CREATE POLICY llm_usage_owner ON llm_usage
            USING (
                user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                OR current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
            )
            WITH CHECK (
                user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                OR current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
            )
    """)

    # index_events — user_id
    op.execute(f"""
        CREATE POLICY index_events_owner ON index_events
            USING (
                user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                OR current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
            )
            WITH CHECK (
                user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                OR current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
            )
    """)

    # user_settings — user_id
    op.execute(f"""
        CREATE POLICY user_settings_owner ON user_settings
            USING (
                user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                OR current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
            )
            WITH CHECK (
                user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                OR current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
            )
    """)

    # -----------------------------------------------------------------------
    # 4. RLS POLICIES — transitive-owner tables
    #    These own via a parent (vault_id → vaults.owner_user_id).
    #    Read policy: allow shared vault OR owner private vault.
    #    Write policy: allow only owner private vault.
    # -----------------------------------------------------------------------

    # pages: vault_id → vaults.owner_user_id
    # Shared vault is readable by all (read); writes go through owned private vault.
    op.execute(f"""
        CREATE POLICY pages_owner ON pages
            USING (
                current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
                OR EXISTS (
                    SELECT 1 FROM vaults v
                    WHERE v.id = pages.vault_id
                      AND (
                          v.kind = 'shared'
                          OR v.owner_user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                      )
                )
            )
            WITH CHECK (
                current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
                OR EXISTS (
                    SELECT 1 FROM vaults v
                    WHERE v.id = pages.vault_id
                      AND v.kind = 'private'
                      AND v.owner_user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                )
            )
    """)

    # page_versions: page_id → pages.vault_id → vaults.owner_user_id
    op.execute(f"""
        CREATE POLICY page_versions_owner ON page_versions
            USING (
                current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
                OR EXISTS (
                    SELECT 1 FROM pages p
                    JOIN vaults v ON v.id = p.vault_id
                    WHERE p.id = page_versions.page_id
                      AND (
                          v.kind = 'shared'
                          OR v.owner_user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                      )
                )
            )
            WITH CHECK (
                current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
                OR EXISTS (
                    SELECT 1 FROM pages p
                    JOIN vaults v ON v.id = p.vault_id
                    WHERE p.id = page_versions.page_id
                      AND v.kind = 'private'
                      AND v.owner_user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                )
            )
    """)

    # chunks: page_id → pages.vault_id → vaults.owner_user_id
    op.execute(f"""
        CREATE POLICY chunks_owner ON chunks
            USING (
                current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
                OR EXISTS (
                    SELECT 1 FROM pages p
                    JOIN vaults v ON v.id = p.vault_id
                    WHERE p.id = chunks.page_id
                      AND (
                          v.kind = 'shared'
                          OR v.owner_user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                      )
                )
            )
            WITH CHECK (
                current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
                OR EXISTS (
                    SELECT 1 FROM pages p
                    JOIN vaults v ON v.id = p.vault_id
                    WHERE p.id = chunks.page_id
                      AND v.kind = 'private'
                      AND v.owner_user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                )
            )
    """)

    # entities: vault_id → vaults.owner_user_id
    op.execute(f"""
        CREATE POLICY entities_owner ON entities
            USING (
                current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
                OR EXISTS (
                    SELECT 1 FROM vaults v
                    WHERE v.id = entities.vault_id
                      AND (
                          v.kind = 'shared'
                          OR v.owner_user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                      )
                )
            )
            WITH CHECK (
                current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
                OR EXISTS (
                    SELECT 1 FROM vaults v
                    WHERE v.id = entities.vault_id
                      AND v.kind = 'private'
                      AND v.owner_user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                )
            )
    """)

    # links (owned via src_page_id): src_page_id → pages.vault_id → vaults.owner_user_id
    # Links are written when pages are written so owner via src makes sense.
    # dst_entity_id is informational — the link belongs to the source page's vault.
    op.execute(f"""
        CREATE POLICY links_owner ON links
            USING (
                current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
                OR EXISTS (
                    SELECT 1 FROM pages p
                    JOIN vaults v ON v.id = p.vault_id
                    WHERE p.id = links.src_page_id
                      AND (
                          v.kind = 'shared'
                          OR v.owner_user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                      )
                )
            )
            WITH CHECK (
                current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
                OR EXISTS (
                    SELECT 1 FROM pages p
                    JOIN vaults v ON v.id = p.vault_id
                    WHERE p.id = links.src_page_id
                      AND v.kind = 'private'
                      AND v.owner_user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                )
            )
    """)

    # timeline_events: page_id → pages.vault_id → vaults.owner_user_id
    op.execute(f"""
        CREATE POLICY timeline_events_owner ON timeline_events
            USING (
                current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
                OR EXISTS (
                    SELECT 1 FROM pages p
                    JOIN vaults v ON v.id = p.vault_id
                    WHERE p.id = timeline_events.page_id
                      AND (
                          v.kind = 'shared'
                          OR v.owner_user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                      )
                )
            )
            WITH CHECK (
                current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
                OR EXISTS (
                    SELECT 1 FROM pages p
                    JOIN vaults v ON v.id = p.vault_id
                    WHERE p.id = timeline_events.page_id
                      AND v.kind = 'private'
                      AND v.owner_user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                )
            )
    """)

    # tags: vault_id → vaults.owner_user_id
    op.execute(f"""
        CREATE POLICY tags_owner ON tags
            USING (
                current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
                OR EXISTS (
                    SELECT 1 FROM vaults v
                    WHERE v.id = tags.vault_id
                      AND (
                          v.kind = 'shared'
                          OR v.owner_user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                      )
                )
            )
            WITH CHECK (
                current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
                OR EXISTS (
                    SELECT 1 FROM vaults v
                    WHERE v.id = tags.vault_id
                      AND v.kind = 'private'
                      AND v.owner_user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                )
            )
    """)

    # page_tags: (page_id, tag_id) — JOIN pages via page_id → vault → owner
    # Tags themselves are vault-scoped; page_tags links pages to tags.
    # Policy via pages relationship (primary access is through pages).
    op.execute(f"""
        CREATE POLICY page_tags_owner ON page_tags
            USING (
                current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
                OR EXISTS (
                    SELECT 1 FROM pages p
                    JOIN vaults v ON v.id = p.vault_id
                    WHERE p.id = page_tags.page_id
                      AND (
                          v.kind = 'shared'
                          OR v.owner_user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                      )
                )
            )
            WITH CHECK (
                current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
                OR EXISTS (
                    SELECT 1 FROM pages p
                    JOIN vaults v ON v.id = p.vault_id
                    WHERE p.id = page_tags.page_id
                      AND v.kind = 'private'
                      AND v.owner_user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                )
            )
    """)

    # messages: conversation_id → conversations.user_id
    op.execute(f"""
        CREATE POLICY messages_owner ON messages
            USING (
                current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
                OR EXISTS (
                    SELECT 1 FROM conversations c
                    WHERE c.id = messages.conversation_id
                      AND c.user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                )
            )
            WITH CHECK (
                current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
                OR EXISTS (
                    SELECT 1 FROM conversations c
                    WHERE c.id = messages.conversation_id
                      AND c.user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                )
            )
    """)

    # recipes: owned via user_id (local) — not transitive
    op.execute(f"""
        CREATE POLICY recipes_owner ON recipes
            USING (
                user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                OR current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
            )
            WITH CHECK (
                user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                OR current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
            )
    """)

    # skills: owned via user_id (local) — not transitive
    op.execute(f"""
        CREATE POLICY skills_owner ON skills
            USING (
                user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                OR current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
            )
            WITH CHECK (
                user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                OR current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
            )
    """)

    # dream_audit_log: owned via user_id (local) — not transitive
    op.execute(f"""
        CREATE POLICY dream_audit_log_owner ON dream_audit_log
            USING (
                user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                OR current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
            )
            WITH CHECK (
                user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                OR current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
            )
    """)

    # -----------------------------------------------------------------------
    # 5. Seed system user (deterministic UUID — idempotent ON CONFLICT)
    # -----------------------------------------------------------------------
    op.execute(f"""
        INSERT INTO users (id, username, role, password_hash, is_active, created_at, updated_at)
        VALUES (
            '{SYSTEM_USER_ID}',
            'system',
            'admin',
            '$argon2id$v=19$m=65536,t=3,p=1$disabled$disabled',
            true,
            now(),
            now()
        )
        ON CONFLICT (id) DO NOTHING
    """)


def downgrade() -> None:
    # -----------------------------------------------------------------------
    # 1. Remove system user seed
    # -----------------------------------------------------------------------
    op.execute(f"DELETE FROM users WHERE id = '{SYSTEM_USER_ID}'")

    # -----------------------------------------------------------------------
    # 2. Drop all RLS policies (in reverse creation order)
    # -----------------------------------------------------------------------
    # Transitive-owner policies (drop in reverse creation order)
    op.execute("DROP POLICY IF EXISTS dream_audit_log_owner ON dream_audit_log")
    op.execute("DROP POLICY IF EXISTS skills_owner ON skills")
    op.execute("DROP POLICY IF EXISTS recipes_owner ON recipes")
    op.execute("DROP POLICY IF EXISTS messages_owner ON messages")
    op.execute("DROP POLICY IF EXISTS page_tags_owner ON page_tags")
    op.execute("DROP POLICY IF EXISTS tags_owner ON tags")
    op.execute("DROP POLICY IF EXISTS timeline_events_owner ON timeline_events")
    op.execute("DROP POLICY IF EXISTS links_owner ON links")
    op.execute("DROP POLICY IF EXISTS entities_owner ON entities")
    op.execute("DROP POLICY IF EXISTS chunks_owner ON chunks")
    op.execute("DROP POLICY IF EXISTS page_versions_owner ON page_versions")
    op.execute("DROP POLICY IF EXISTS pages_owner ON pages")

    # Local-owner policies (drop in reverse RLS_OWNER_LOCAL order)
    for tbl, _col in reversed(RLS_OWNER_LOCAL):
        op.execute(f"DROP POLICY IF EXISTS {tbl}_owner ON {tbl}")

    # -----------------------------------------------------------------------
    # 3. Drop sessions.admin_fresh_until column
    # -----------------------------------------------------------------------
    op.drop_column("sessions", "admin_fresh_until")

    # -----------------------------------------------------------------------
    # 4. Drop login_attempts index and table
    # -----------------------------------------------------------------------
    op.execute("DROP INDEX IF EXISTS login_attempts_lookup_idx")
    op.drop_table("login_attempts")