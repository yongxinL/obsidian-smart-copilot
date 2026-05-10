---
phase: 1b
plan: "02"
name: migration-and-models
wave: 1
depends_on: ["01"]
requirements: [AUTH-03, AUTH-06, AUTH-07, TEST-02]
files_modified:
  - server/app/models/login_attempt.py
  - server/app/models/__init__.py
  - server/app/models/session.py
  - alembic/versions/0002_phase_1b_auth.py
autonomous: true
must_haves:
  truths:
    - "alembic upgrade head succeeds against a fresh pgvector:pg16 testcontainer; alembic downgrade -1 followed by alembic upgrade head also succeeds (round-trip)"
    - "login_attempts table exists with (id, ip INET, username, attempted_at, user_agent, request_id) and a (ip, username, attempted_at DESC) index"
    - "sessions.admin_fresh_until column exists (TIMESTAMPTZ, nullable)"
    - "RLS POLICY exists for every table in 0001's RLS_TABLES list (22 tables) using NULLIF(current_setting('app.current_user_id', true), '')::uuid pattern"
    - "Every owner-RLS POLICY USING/WITH CHECK clause includes an explicit OR for the system user UUID '00000000-0000-0000-0000-000000000001' — auth-pipeline reads/writes (validate_refresh / validate_bearer / login session creation) succeed even before per-user GUC is set"
    - "login_attempts has NEITHER ENABLE ROW LEVEL SECURITY nor a POLICY (D-06 — system-internal table)"
    - "audit_log has NEITHER ENABLE ROW LEVEL SECURITY nor a POLICY (Phase 1a precedent — write-everywhere-readable-by-admin pattern)"
    - "A 'system' user exists in users table with username='system', role='admin', is_active=true; UUID is stable across restarts (deterministic UUID)"
    - "D-05: login_attempts table shape is (id, ip, username, attempted_at, user_agent NULL, request_id NULL); created in Alembic migration 0002_phase_1b_auth.py"
    - "D-11: sessions.admin_fresh_until is a TIMESTAMPTZ NULL column added in this 0002 migration; freshness lives in the DB (NOT in JWT) so it can be revoked before JWT expiry and survives logout"
  artifacts:
    - path: "alembic/versions/0002_phase_1b_auth.py"
      provides: "Single migration for login_attempts + sessions.admin_fresh_until + 22 RLS policies (with system-user bypass clause) + system user seed"
    - path: "server/app/models/login_attempt.py"
      provides: "LoginAttempt SQLAlchemy model"
    - path: "server/app/models/session.py"
      provides: "Existing Session model extended with admin_fresh_until column"
  key_links:
    - from: "alembic/versions/0002_phase_1b_auth.py"
      to: "alembic/versions/0001_initial_schema.py:RLS_TABLES (line 32-55)"
      via: "0002 reads the same 22 table names; one CREATE POLICY per table"
      pattern: "CREATE POLICY .* ON .* USING .*current_setting.*app.current_user_id"
    - from: "server/app/models/__init__.py"
      to: "server/app/models/login_attempt.py"
      via: "barrel import with # noqa: F401 (alphabetical position between link and llm_usage)"
      pattern: "login_attempt,  # noqa: F401"
threat_refs: [T-1b-03, T-1b-04]
---

<plan_objective>
Land the single Alembic migration `0002_phase_1b_auth.py` that adds the `login_attempts` table, the `sessions.admin_fresh_until` column, the 22 owner-only RLS policies (one per `RLS_TABLES` entry from 0001) — each with an explicit system-user bypass OR clause so the auth pipeline (validate_refresh, validate_bearer, login session creation) can read/write `sessions` and `mcp_tokens` before the per-user GUC has been set — and seeds the deterministic `system` user (`username='system'`, `role='admin'`). Add the corresponding `LoginAttempt` SQLAlchemy model and patch `models/session.py` for the new column. The migration is the foundation Plans 05/06/07 build on — every RLS test (TEST-02) requires the policies to exist, AND the auth-pipeline integration tests require the system-user bypass.
</plan_objective>

<threat_model>

## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| pooled DB connection ↔ per-user request | RLS policy fires on `current_setting('app.current_user_id', true)` — a tampered or unset GUC must fail closed (return zero rows), not return all rows |
| login_attempts INSERT path | System-internal writer; never exposed under user RLS (D-06). Brute-force protection only works if writes are not blocked by misconfigured policy |
| auth-pipeline read path (validate_refresh / validate_bearer) | Runs BEFORE the per-user GUC is set — it's HOW we discover who the user is. Owner-RLS policies on `sessions` and `mcp_tokens` MUST include a system-user bypass OR clause, otherwise refresh and bearer validation are permanently broken |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-1b-03 | I (Information Disclosure) | RLS POLICY blocks for 22 multi-tenant tables | mitigate | Every CREATE POLICY uses `NULLIF(current_setting('app.current_user_id', true), '')::uuid` for the per-user predicate, OR'd with an exact match against the system user UUID `'00000000-0000-0000-0000-000000000001'`. Graceful unset → NULL → predicate FALSE → fail closed (Landmine #8) for non-system contexts. The OR clause is what permits Plan 05's `validate_refresh` / `validate_bearer` and Plan 07's `routes/auth.py login` SELECT/INSERT path to succeed when running under `system_operation_context()` (see Plan 05 task 05-03 `session_with_rls(ctx)` helper). For tables whose owner column lives on a parent (e.g. `pages.vault_id → vaults.owner_user_id`), use EXISTS subquery. Verified by Plan 08's `test_cross_user_read_blocked`. |
| T-1b-04 | S (Spoofing — credential brute-force) | login_attempts table + index | mitigate | Index on `(ip, username, attempted_at DESC)` makes the sliding-window count query (Plan 06) sub-millisecond. Table is NOT in RLS_TABLES — Plan 06's writer path always succeeds even before per-user GUC is set. |

</threat_model>

<read_first_global>
- alembic/versions/0001_initial_schema.py (RLS_TABLES list at line 32-55; ENUM patterns; downgrade structure; full table inventory)
- server/app/models/audit_log.py (closest analog for LoginAttempt — append-only, system-writer, no RLS)
- server/app/models/session.py (current shape — admin_fresh_until column added INTO this class)
- server/app/models/__init__.py (alphabetical barrel — `login_attempt` slot between `link` and `llm_usage`)
- .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md decisions D-05, D-06, D-07, D-09, D-11
- .planning/phases/01b-auth-security-primitives/01b-RESEARCH.md §"Pattern 7" (RLS policy boilerplate, lines 552-571), §"Pattern 8" (login_attempts index, lines 661-663), §"Landmine #8" (graceful-unset), §"Landmine #10" (existing user_role_enum)
- .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md sections for `models/login_attempt.py`, `models/session.py (MODIFY)`, `alembic/versions/0002_phase_1b_auth.py`
</read_first_global>

<tasks>

<task type="auto">
  <id>02-01</id>
  <name>Task 1: LoginAttempt model + register in barrel</name>
  <read_first>
    - server/app/models/audit_log.py (analog: append-only, BigInteger PK, INET column, server_default="now()", no RLS)
    - server/app/models/__init__.py (current barrel — find alphabetical insert point between `link` and `llm_usage`)
    - server/app/models/base.py (Base + TimestampMixin shapes)
    - .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md "server/app/models/login_attempt.py (NEW model)" section
    - .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md D-05 (column shape) + D-06 (NO user RLS)
  </read_first>
  <action>
    Create `server/app/models/login_attempt.py` mirroring `audit_log.py` shape. NO `TimestampMixin` (single timestamp `attempted_at`, mirrors audit_log.created_at). NO FK to users (D-06 — username may not exist; system-internal writer):

    ```python
    """Login attempt domain model — REQ-402 / D-05.

    Table: login_attempts
    System-internal table for sliding-window login throttling. Per D-06, NOT under
    user RLS — written by the auth path regardless of who is authenticated.
    Per D-07, one file per domain.
    """
    from __future__ import annotations

    from sqlalchemy import BigInteger, DateTime, String, Text
    from sqlalchemy.dialects.postgresql import INET
    from sqlalchemy.orm import Mapped, mapped_column

    from app.models.base import Base


    class LoginAttempt(Base):
        """Append-only record of a failed login attempt (sliding-window rate limit)."""

        __tablename__ = "login_attempts"

        id: Mapped[int] = mapped_column(
            BigInteger, primary_key=True, autoincrement=True
        )
        # No FK — usernames may not match an existing user (D-06)
        username: Mapped[str] = mapped_column(String(64), nullable=False)
        ip: Mapped[object] = mapped_column(INET, nullable=False)
        attempted_at: Mapped[object] = mapped_column(
            DateTime(timezone=True), nullable=False, server_default="now()"
        )
        user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
        request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ```

    Edit `server/app/models/__init__.py`. In the alphabetical import block (currently between `link,  # noqa: F401` and `llm_usage,  # noqa: F401`), insert exactly:
    ```python
        login_attempt,  # noqa: F401
    ```
    Maintain the existing 4-space indentation and trailing comma. Do NOT modify the `__all__` line.
  </action>
  <acceptance_criteria>
    - `test -f server/app/models/login_attempt.py`
    - `grep -q '__tablename__ = "login_attempts"' server/app/models/login_attempt.py` returns 0
    - `grep -q "INET, nullable=False" server/app/models/login_attempt.py` returns 0
    - `grep -q "attempted_at: Mapped\[object\] = mapped_column" server/app/models/login_attempt.py` returns 0
    - `grep -v '^#' server/app/models/login_attempt.py | grep -q "ForeignKey" && exit 1; exit 0` (NO ForeignKey to users per D-06)
    - `grep -q "    login_attempt,  # noqa: F401" server/app/models/__init__.py` returns 0
    - Model registers cleanly: `cd server && python -c "from app.models import Base; assert 'login_attempts' in Base.metadata.tables; t = Base.metadata.tables['login_attempts']; cols = {c.name for c in t.columns}; assert cols == {'id','username','ip','attempted_at','user_agent','request_id'}, cols; print('ok')"` prints `ok`
    - `cd server && ruff check app/models/login_attempt.py app/models/__init__.py` exits 0
  </acceptance_criteria>
  <done>LoginAttempt model file exists, registers with Base.metadata, has the exact 6 columns, no FK, and the barrel import lands alphabetically.</done>
  <threat_ref>T-1b-04</threat_ref>
</task>

<task type="auto">
  <id>02-02</id>
  <name>Task 2: Add sessions.admin_fresh_until column to model</name>
  <read_first>
    - server/app/models/session.py (current shape — column added INTO this class)
    - .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md "server/app/models/session.py (MODIFY)" section
    - .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md D-11 (admin_fresh_until rationale — NOT in JWT)
  </read_first>
  <action>
    Edit `server/app/models/session.py`. Add ONE column inside the `Session` class, immediately after the existing `expires_at:` column declaration (preserve the `Mapped[object | None]` style used by `expires_at` — the file uses `object` not `datetime`):

    ```python
        admin_fresh_until: Mapped[object | None] = mapped_column(
            DateTime(timezone=True), nullable=True
        )
    ```

    Do NOT modify other columns. Do NOT add a relationship or index.
  </action>
  <acceptance_criteria>
    - `grep -q "admin_fresh_until: Mapped\[object | None\]" server/app/models/session.py` returns 0
    - `grep -q "admin_fresh_until.*DateTime(timezone=True), nullable=True" server/app/models/session.py` returns 0
    - Class still has only one definition: `grep -c "^class Session" server/app/models/session.py` returns `1`
    - Column registers in metadata: `cd server && python -c "from app.models import Base; t = Base.metadata.tables['sessions']; assert 'admin_fresh_until' in {c.name for c in t.columns}; print('ok')"` prints `ok`
    - `cd server && ruff check app/models/session.py` exits 0
  </acceptance_criteria>
  <done>Session model has the new nullable timestamp column matching the file's existing style.</done>
  <threat_ref>T-1b-03</threat_ref>
</task>

<task type="auto">
  <id>02-03</id>
  <name>Task 3: Alembic migration 0002 — login_attempts + admin_fresh_until + system seed</name>
  <read_first>
    - alembic/versions/0001_initial_schema.py header (lines 1-31), ENUM creation block (lines 65-90), audit_log table create (lines 226-244), index examples (lines 1027-1043), downgrade tail (lines 1057-1126)
    - server/app/tests/conftest.py (testcontainer + alembic upgrade head — verifies migration runs)
    - .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md "alembic/versions/0002_phase_1b_auth.py" section (full DDL templates)
    - .planning/phases/01b-auth-security-primitives/01b-RESEARCH.md §"Pattern 8" (index DDL line 660-663), §"Open Question 2" recommendation (system user seed)
    - .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md D-05, D-09, D-11
  </read_first>
  <action>
    Create `alembic/versions/0002_phase_1b_auth.py`. Header block (mirror 0001 lines 1-27):
    ```python
    """phase_1b_auth

    Revision ID: 0002
    Revises: 0001
    Create Date: 2026-05-08

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

    # Pairs of (table, owner_column) for tables whose owner column is local.
    # Tables whose owner column lives on a parent table use a separate block below.
    RLS_OWNER_LOCAL: list[tuple[str, str]] = [
        ("provider_keys", "user_id"),
        ("sessions", "user_id"),
        ("mcp_tokens", "user_id"),
        ("conversations", "user_id"),
        ("memories", "user_id"),
        ("projects", "user_id"),
        ("llm_usage", "user_id"),
        ("user_settings", "user_id"),
    ]
    ```

    `upgrade()` body sequence — DO NOT REORDER:

    1. **Create login_attempts** (mirror `audit_log` shape from 0001 lines 226-244):
       ```python
       op.create_table(
           "login_attempts",
           sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
           sa.Column("username", sa.String(64), nullable=False),
           sa.Column("ip", postgresql.INET(), nullable=False),
           sa.Column("attempted_at", sa.DateTime(timezone=True),
                     server_default="now()", nullable=False),
           sa.Column("user_agent", sa.Text(), nullable=True),
           sa.Column("request_id", sa.String(64), nullable=True),
           sa.PrimaryKeyConstraint("id"),
       )
       op.execute(
           "CREATE INDEX login_attempts_lookup_idx "
           "ON login_attempts (ip, username, attempted_at DESC)"
       )
       ```
       D-06 mandates NO `ENABLE ROW LEVEL SECURITY` for login_attempts. Do NOT add it.

    2. **Add sessions.admin_fresh_until**:
       ```python
       op.add_column(
           "sessions",
           sa.Column("admin_fresh_until", sa.DateTime(timezone=True), nullable=True),
       )
       ```

    3. **Create POLICY for each RLS_OWNER_LOCAL table** (Landmine #8 — graceful unset; system-user bypass OR clause for the auth pipeline):
       ```python
       for tbl, col in RLS_OWNER_LOCAL:
           op.execute(f"""
               CREATE POLICY {tbl}_owner ON {tbl}
                   USING (
                     {col} = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                     OR current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
                   )
                   WITH CHECK (
                     {col} = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                     OR current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
                   )
           """)
       ```
       The OR clause is LOAD-BEARING for `sessions` and `mcp_tokens`: Plan 05's `validate_refresh` / `validate_bearer` and Plan 07's `routes/auth.py login` open a session under `system_operation_context()` (which sets `app.current_user_id` to the system UUID) BEFORE the caller's identity is known. Without this OR, those reads return zero rows and refresh / bearer validation / login session creation are permanently broken.

    4. **Create POLICY for transitive-owner tables** — these own via a parent. Use EXISTS subqueries; the system bypass OR is added at the outer USING/WITH CHECK level:
       - `pages` owns via `vaults.owner_user_id` (vaults.id == pages.vault_id, vault is private):
         ```python
         op.execute(f"""
             CREATE POLICY pages_owner ON pages
                 USING (
                   current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
                   OR EXISTS (
                     SELECT 1 FROM vaults v
                     WHERE v.id = pages.vault_id
                       AND (v.kind = 'shared' OR v.owner_user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
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
         ```
       - `page_versions`, `chunks`, `links` (src side), `timeline_events`, `page_tags` — each owns via its FK to `pages`. Pattern (substitute `<tbl>` and the FK column; keep the system-bypass OR at the outer level):
         ```sql
         CREATE POLICY <tbl>_owner ON <tbl>
           USING (
             current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
             OR EXISTS (
               SELECT 1 FROM pages p JOIN vaults v ON v.id = p.vault_id
               WHERE p.id = <tbl>.<page_fk_col>
                 AND (v.kind = 'shared' OR v.owner_user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
             )
           )
           WITH CHECK (
             current_setting('app.current_user_id', true) = '{SYSTEM_USER_ID}'
             OR EXISTS (
               SELECT 1 FROM pages p JOIN vaults v ON v.id = p.vault_id
               WHERE p.id = <tbl>.<page_fk_col>
                 AND v.kind = 'private'
                 AND v.owner_user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
             )
           )
         ```
         **Inspect the actual FK column name in 0001 before emitting** — the planner's PATTERNS doc and 0001's table definitions are the source of truth. Check `page_versions.page_id`, `chunks.page_id`, `links.src_page_id`, `timeline_events.page_id`, `page_tags.page_id` (rename if 0001 uses different names).
       - `entities`, `tags` — these are global vocabulary tables. Owner column may not exist; check 0001. If they have a `user_id` column → add to RLS_OWNER_LOCAL list. If global / shared → leave them with `ENABLE+FORCE` from 0001 (which means no rows visible until a permissive policy is added) AND add a single permissive `<tbl>_read_all` policy: `USING (true)` — both `entities` and `tags` are reference data with no per-user privacy in v1. Document the choice with an inline `# v1: tags/entities are global reference data — permissive read policy.` comment.
       - `eval_candidates`, `messages`, `index_events`, `recipes`, `skills`, `dream_audit_log` — same FK-via-parent pattern with the system-bypass OR at the outer level. Inspect 0001 for the parent FK and adapt.

       **Required coverage:** every one of the 22 tables enumerated in 0001's `RLS_TABLES` list MUST receive at least one CREATE POLICY block (`<tbl>_owner`, `<tbl>_read_all`, or `<tbl>_system_bypass`). The acceptance criterion below loops over the full 22-table list programmatically — there is no hand-curated subset.

    5. **Seed system user** — single INSERT, idempotent (ON CONFLICT DO NOTHING):
       ```python
       op.execute(f"""
           INSERT INTO users (id, username, role, password_hash, is_active, created_at, updated_at)
           VALUES ('{SYSTEM_USER_ID}', 'system', 'admin',
                   '$argon2id$v=19$m=65536,t=3,p=1$disabled$disabled',
                   true, now(), now())
           ON CONFLICT (id) DO NOTHING
       """)
       ```
       The password hash is a syntactically-valid argon2id placeholder that no user can produce — system user MUST NOT be loginable through `/auth/login`. Plan 06's `services/users.create_user` and Plan 07's `/auth/login` route MUST refuse `username='system'` (acceptance verified in Plan 07).

    `downgrade()` body — reverse order:
    1. `op.execute(f"DELETE FROM users WHERE id = '{SYSTEM_USER_ID}'")`
    2. For every table in upgrade order, `op.execute(f"DROP POLICY IF EXISTS {tbl}_owner ON {tbl}")` (and `_read_all` for entities/tags).
    3. `op.drop_column("sessions", "admin_fresh_until")`
    4. `op.execute("DROP INDEX IF EXISTS login_attempts_lookup_idx")`
    5. `op.drop_table("login_attempts")`

    **Do NOT** redefine any ENUM type — Landmine #10 (`user_role_enum` from 0001 must not be CREATE TYPE'd again).

    **Do NOT** include `apscheduler_jobs` (CLAUDE.md anti-pattern; Phase 1a already excludes it from include_object filter).
  </action>
  <acceptance_criteria>
    - `test -f alembic/versions/0002_phase_1b_auth.py`
    - `grep -q 'revision: str = "0002"' alembic/versions/0002_phase_1b_auth.py` returns 0
    - `grep -q 'down_revision: str | None = "0001"' alembic/versions/0002_phase_1b_auth.py` returns 0
    - `grep -q '"login_attempts"' alembic/versions/0002_phase_1b_auth.py && grep -q 'op.create_table' alembic/versions/0002_phase_1b_auth.py` returns 0 (portable check; replaces non-portable `grep -Pzoq`)
    - `grep -q "login_attempts_lookup_idx" alembic/versions/0002_phase_1b_auth.py` returns 0
    - `grep -q "ENABLE ROW LEVEL SECURITY" alembic/versions/0002_phase_1b_auth.py && exit 1; exit 0` (RLS already enabled in 0001 — 0002 must not double-enable)
    - `grep -q "admin_fresh_until" alembic/versions/0002_phase_1b_auth.py` returns 0
    - **System-user bypass OR clause present** (BLOCKER #2 closure): `grep -q "00000000-0000-0000-0000-000000000001" alembic/versions/0002_phase_1b_auth.py && grep -qE "current_setting\\('app.current_user_id', true\\)\\s*=\\s*'00000000-0000-0000-0000-000000000001'" alembic/versions/0002_phase_1b_auth.py` returns 0
    - **All 22 RLS_TABLES tables receive at least one CREATE POLICY** (no hand-curated subset; programmatic loop covers every table from 0001's RLS_TABLES list including page_tags):
      ```bash
      for t in provider_keys sessions mcp_tokens pages page_versions chunks entities links timeline_events tags page_tags eval_candidates conversations messages memories projects llm_usage index_events user_settings recipes skills dream_audit_log; do
        grep -qE "CREATE POLICY \"?${t}(_owner|_read_all|_system_bypass)?\"? ON \"?${t}\"?" alembic/versions/0002_phase_1b_auth.py \
          || { echo "missing policy for $t"; exit 1; };
      done; echo all-policies-present
      ```
      exits 0 with `all-policies-present` printed.
    - System user seed present: `grep -q "INSERT INTO users" alembic/versions/0002_phase_1b_auth.py && grep -q "00000000-0000-0000-0000-000000000001" alembic/versions/0002_phase_1b_auth.py` returns 0
    - NO redefinition of existing ENUM types: `grep -q "CREATE TYPE user_role_enum" alembic/versions/0002_phase_1b_auth.py && exit 1; exit 0`
    - Migration runs against testcontainer: `cd server && pytest -x -q app/tests/integration/test_boot.py::test_all_tables_present` exits 0 (this re-runs alembic upgrade head; failure means migration broken)
    - Round-trip works: `cd server && pytest -x -q app/tests/integration/` exits 0 AND `cd server && ALEMBIC_DATABASE_URL=$(python -c "from app.settings import settings; print(settings.alembic_database_url)") alembic downgrade -1 && alembic upgrade head` succeeds (run only if local PG is up; otherwise rely on the testcontainer test).
    - Smoke check via testcontainer DB: after running tests, `psql` (or via `db_session.execute`) confirms `SELECT count(*) FROM pg_policies WHERE tablename IN ('provider_keys','sessions','mcp_tokens','pages')` returns >= 4. Verified by Plan 08 test.
    - `cd server && ruff check alembic/versions/0002_phase_1b_auth.py` exits 0 (file is in `extend-exclude` per pyproject.toml; ruff still passes — no error)
  </acceptance_criteria>
  <done>0002 migration applies cleanly to fresh testcontainer; existing 7 boot tests still pass; downgrade -1 + upgrade head completes without errors; system user is seeded; every RLS_TABLES entry has a CREATE POLICY (programmatic loop verifies); auth-pipeline reads under system context succeed via the OR-bypass clause.</done>
  <threat_ref>T-1b-03</threat_ref>
</task>

</tasks>

<verification>
  <command>cd server && ruff check app/ alembic/ && pytest -q app/tests/integration/</command>
  <expected>All 7 Phase 1a integration tests still green (alembic upgrade head succeeds — proves migration applies). 0002 migration introduces no test regressions.</expected>
</verification>

<must_haves>

## Truths
- `alembic upgrade head` runs cleanly against pgvector:pg16 (verified by every Phase 1a test that boots a testcontainer).
- Round-trip: `downgrade -1` then `upgrade head` succeeds without errors.
- Every multi-tenant table from 0001's RLS_TABLES has a CREATE POLICY block in 0002.
- Every owner-RLS POLICY's USING / WITH CHECK includes an explicit OR for the system user UUID — auth-pipeline reads (validate_refresh / validate_bearer / login session creation) succeed under system context.
- login_attempts and audit_log are NOT in RLS_TABLES — system writers always succeed.

## Artifacts
- `alembic/versions/0002_phase_1b_auth.py` — single migration covering all 1b schema changes.
- `server/app/models/login_attempt.py` — LoginAttempt model with 6 columns, no FK.
- `server/app/models/session.py` — extended with `admin_fresh_until: Mapped[object | None]`.

## Key Links
- 0002 ← 0001's RLS_TABLES list (22 entries; planner emits one CREATE POLICY per entry, with system-bypass OR clause at the outer level + EXISTS-subquery for transitive-owner tables).
- `models/__init__.py:login_attempt,  # noqa: F401` ← `models/login_attempt.py`.
- System user UUID `00000000-0000-0000-0000-000000000001` ← consumed by Plan 06 (services system context) and Plan 07 (APScheduler prune job).

</must_haves>

<output>
Append per-task rows to `.planning/phases/01b-auth-security-primitives/01B-VALIDATION.md` "Per-Task Verification Map".
Create `.planning/phases/01b-auth-security-primitives/01B-02-SUMMARY.md` documenting:
- Number of CREATE POLICY blocks emitted (= 22)
- System user UUID
- Tables that received transitive-owner EXISTS-subquery policies vs local-column policies
- Round-trip downgrade/upgrade verification
</output>
</output>
