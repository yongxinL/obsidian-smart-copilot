---
phase: 01c
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - server/alembic/versions/0003_phase_1c_vault.py
  - server/app/models/page.py
  - server/app/models/page_version.py
  - server/app/settings.py
  - server/requirements.txt
autonomous: true
requirements:
  - VAULT-04
  - VAULT-06
  - VAULT-07
  - VAULT-08

must_haves:
  truths:
    - "Alembic migration 0003 runs to completion against the testcontainer DB"
    - "pages.timeline TEXT column exists in the DB after migration"
    - "pages.deleted_by UUID FK users.id exists in the DB after migration"
    - "page_versions.timeline TEXT column exists after migration"
    - "page_note_type_enum has values fleeting/literature/permanent/archived_fleeting/skill/moc after migration"
    - "pages.note_type column server_default is 'fleeting' after migration"
    - "SQLAlchemy Page model has timeline and deleted_by mapped columns"
    - "SQLAlchemy PageVersion model has timeline mapped column"
    - "settings.py has vault_watch_debounce_ms and shared_vault_write_policy fields"
    - "requirements.txt declares watchdog>=4.0, xxhash>=3.0, python-frontmatter>=1.1, markdown-it-py>=3.0"
  artifacts:
    - path: "server/alembic/versions/0003_phase_1c_vault.py"
      provides: "Alembic migration adding timeline/deleted_by columns and replacing page_note_type_enum"
      contains: "revision = \"0003\""
    - path: "server/app/models/page.py"
      provides: "SQLAlchemy Page model with timeline + deleted_by columns and fixed enum"
      contains: "timeline"
    - path: "server/app/models/page_version.py"
      provides: "SQLAlchemy PageVersion model with timeline column"
      contains: "timeline"
    - path: "server/app/settings.py"
      provides: "Settings with vault watchdog config"
      contains: "vault_watch_debounce_ms"
    - path: "server/requirements.txt"
      provides: "Declared dependencies for Phase 1c libraries"
      contains: "watchdog>=4.0"
  key_links:
    - from: "server/alembic/versions/0003_phase_1c_vault.py"
      to: "server/app/models/page.py"
      via: "Both must agree on column names: timeline, deleted_by, note_type enum values"
      pattern: "timeline"
    - from: "server/app/models/page.py"
      to: "page_note_type_enum"
      via: "ENUM definition must match the DB type created by migration 0003"
      pattern: "fleeting.*literature.*permanent"
---

<objective>
This plan lays the schema foundation for Phase 1c. It writes the Alembic migration 0003, fixes the SQLAlchemy models to match the new schema, extends settings with vault watchdog config, and declares Phase 1c library dependencies in requirements.txt.

Purpose: Every subsequent Phase 1c plan depends on the correct schema being in place. Migration 0003 is the single most BLOCKING item in this phase — the page service, watchdog, and reconciler all require `pages.timeline`, `pages.deleted_by`, and the correct `page_note_type_enum` values.

Output: Migration file, updated Page/PageVersion models, updated settings, updated requirements.
</objective>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/01c-vault-watchdog-indexer/01c-CONTEXT.md
@.planning/phases/01c-vault-watchdog-indexer/01c-RESEARCH.md

<interfaces>
<!-- From server/app/models/page.py (current state — BEFORE this plan modifies it) -->
```python
page_note_type_enum = ENUM(
    "compiled_truth", "timeline", "mixed",
    name="page_note_type_enum", create_type=False,
)

class Page(TimestampMixin, Base):
    __tablename__ = "pages"
    id: Mapped[uuid.UUID]
    vault_id: Mapped[uuid.UUID]  # FK vaults.id CASCADE
    slug: Mapped[str]            # String(256)
    type: Mapped[str]            # page_type_enum
    note_type: Mapped[str]       # page_note_type_enum, server_default="mixed"
    frontmatter: Mapped[dict]    # JSONB
    compiled_truth: Mapped[str | None]  # Text
    content_hash: Mapped[str]    # String(32)
    enrichment_hash: Mapped[str | None]  # String(32)
    deleted_at: Mapped[object | None]   # DateTime(timezone=True)
    delete_reason: Mapped[str | None]   # Text
    # MISSING: timeline, deleted_by
```

<!-- From server/app/models/page_version.py (current state) -->
```python
class PageVersion(Base):
    __tablename__ = "page_versions"
    id: Mapped[uuid.UUID]
    page_id: Mapped[uuid.UUID]   # FK pages.id CASCADE
    version: Mapped[int]
    frontmatter: Mapped[dict]    # JSONB
    compiled_truth: Mapped[str | None]  # Text
    content_hash: Mapped[str]    # String(32)
    created_at: Mapped[object]
    # MISSING: timeline
```

<!-- From server/app/settings.py (current state) -->
```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False)
    database_url: str
    alembic_database_url: str
    test_database_url: str
    smartcopilot_fernet_key: str
    jwt_signing_key: str
    # ... (Phase 1b fields)
    # MISSING: vault_watch_debounce_ms, shared_vault_write_policy
```

<!-- From server/alembic/versions/0002_phase_1b_auth.py (header pattern to replicate) -->
```python
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Alembic migration 0003 — schema additions and enum replacement</name>
  <read_first>
    - server/alembic/versions/0002_phase_1b_auth.py (header format, upgrade/downgrade structure, op.add_column, op.execute patterns — read lines 1-35 for header, 36-200 for upgrade body style)
    - server/alembic/versions/0001_initial_schema.py (read lines 1-50 for context on existing tables, confirm pages/page_versions table structure matches expectations)
    - server/app/models/page.py (current state — confirms missing timeline + deleted_by + wrong enum values)
    - server/app/models/page_version.py (current state — confirms missing timeline column)
    - .planning/phases/01c-vault-watchdog-indexer/01c-RESEARCH.md (Pattern 5: Alembic enum rename-and-recreate; Pitfall 3: cannot DROP VALUE; Pitfall 4: server_default must change; Pitfall 5: both model AND migration)
  </read_first>
  <files>server/alembic/versions/0003_phase_1c_vault.py</files>
  <action>
Create `server/alembic/versions/0003_phase_1c_vault.py` with the following exact content:

```python
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
    # ── Step 1: Reverse enum replacement ──────────────────────────────────────
    op.execute(
        "CREATE TYPE page_note_type_enum_old AS ENUM "
        "('compiled_truth', 'timeline', 'mixed')"
    )
    op.execute(
        "ALTER TABLE pages ADD COLUMN note_type_old page_note_type_enum_old "
        "NOT NULL DEFAULT 'mixed'::page_note_type_enum_old"
    )
    op.execute("ALTER TABLE pages DROP COLUMN note_type")
    op.execute("ALTER TABLE pages RENAME COLUMN note_type_old TO note_type")
    op.execute("DROP TYPE page_note_type_enum")
    op.execute("ALTER TYPE page_note_type_enum_old RENAME TO page_note_type_enum")

    # ── Step 2: Drop columns added in upgrade ──────────────────────────────────
    op.drop_constraint("fk_pages_deleted_by_users", "pages", type_="foreignkey")
    op.drop_column("pages", "deleted_by")
    op.drop_column("pages", "timeline")
    op.drop_column("page_versions", "timeline")
```

Key correctness checks:
- `down_revision = "0002"` (chains from the Phase 1b migration)
- Timeline added BEFORE enum replacement (simpler dependency order)
- `fk_pages_deleted_by_users` constraint name is used in both upgrade and downgrade
- Downgrade reverses steps in opposite order (constraint drop first, then enum reverse, then column drops)
- The `server_default=""` on timeline columns matches the compiled_truth pattern in the existing model
  </action>
  <verify>
    <automated>cd /home/yongxin.Li/Documents/nexora/smart-copilot/server && python -c "import py_compile; py_compile.compile('alembic/versions/0003_phase_1c_vault.py', doraise=True); print('syntax OK')"</automated>
  </verify>
  <acceptance_criteria>
    - File `server/alembic/versions/0003_phase_1c_vault.py` exists
    - Contains `revision: str = "0003"`
    - Contains `down_revision: str | None = "0002"`
    - Contains `pages.timeline` column addition: grep for `"timeline"` in upgrade function
    - Contains `pages.deleted_by` column addition: grep for `"deleted_by"` in upgrade function
    - Contains `fk_pages_deleted_by_users` FK constraint
    - Contains `page_versions` timeline column addition
    - Contains `page_note_type_enum_new` enum creation with `fleeting`
    - Contains `'archived_fleeting'` in the new enum definition
    - downgrade function exists and reverses the upgrade steps
    - `python -c "import py_compile; py_compile.compile('alembic/versions/0003_phase_1c_vault.py', doraise=True)"` exits 0
  </acceptance_criteria>
  <done>Migration file created with correct chain (0002→0003), adds timeline+deleted_by to pages, timeline to page_versions, replaces page_note_type_enum with Zettelkasten values, has working downgrade</done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Update Page/PageVersion models + Settings extension + requirements.txt</name>
  <read_first>
    - server/app/models/page.py (full file — need to understand ALL existing imports/columns before modifying)
    - server/app/models/page_version.py (full file — add timeline column)
    - server/app/settings.py (full file — extend with Phase 1c fields)
    - server/requirements.txt (full file — add 4 new deps)
    - .planning/phases/01c-vault-watchdog-indexer/01c-RESEARCH.md (sections: models/page.py and settings.py patterns; D-04, D-07 for field names)
  </read_first>
  <files>server/app/models/page.py, server/app/models/page_version.py, server/app/settings.py, server/requirements.txt</files>
  <action>
**1. Update `server/app/models/page.py`:**

Change the `page_note_type_enum` definition (around line 38-44) from old wrong values to new Zettelkasten values:
```python
page_note_type_enum = ENUM(
    "fleeting",
    "literature",
    "permanent",
    "archived_fleeting",
    "skill",
    "moc",
    name="page_note_type_enum",
    create_type=False,
)
```

Change `note_type` column `server_default` from `"mixed"` to `"fleeting"` (Pitfall 4 in RESEARCH.md — column default is stored separately from type; must be updated to match new enum):
```python
note_type: Mapped[str] = mapped_column(
    page_note_type_enum, nullable=False, server_default="fleeting"
)
```

Add `timeline` column after `compiled_truth` (mirrors the Text/nullable/server_default pattern):
```python
timeline: Mapped[str | None] = mapped_column(
    Text, nullable=True, server_default=""
)
```

Add `deleted_by` column after `delete_reason` (UUID FK to users.id, nullable, ondelete SET NULL). Add `ForeignKey` to the existing imports if not already present (it is already imported). The column:
```python
deleted_by: Mapped[uuid.UUID | None] = mapped_column(
    UUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
)
```

Update the module docstring to reference Phase 1c: add `VAULT-04 (timeline), VAULT-06 (note_type lifecycle enum), VAULT-08 (deleted_by)` to the docstring comment.

**2. Update `server/app/models/page_version.py`:**

Add `timeline` column after `compiled_truth`, using the same pattern:
```python
timeline: Mapped[str | None] = mapped_column(
    Text, nullable=True, server_default=""
)
```

Update the module docstring to note Phase 1c addition.

**3. Update `server/app/settings.py`:**

Add a Phase 1c section after the existing Phase 1b fields (before the closing `settings = Settings()` line):
```python
    # --- Phase 1c: Vault + Watchdog Indexer ---
    # Per-path debounce for filesystem watchdog (D-07, DEC-003 from CLAUDE.md)
    # Env var: VAULT_WATCH_DEBOUNCE_MS (pydantic-settings maps snake_case to env without prefix)
    # D-07 specifies SMARTCOPILOT_VAULT_WATCH_DEBOUNCE_MS — use validation_alias to match:
    vault_watch_debounce_ms: int = Field(
        default=750,
        validation_alias="VAULT_WATCH_DEBOUNCE_MS",
    )
    # Shared vault write policy (VAULT-03) — "admin_only" | "all_users"
    shared_vault_write_policy: str = Field(default="admin_only")
```

NOTE on env var naming: The settings.py has no `env_prefix` in `model_config`, so pydantic-settings maps `vault_watch_debounce_ms` → env var `VAULT_WATCH_DEBOUNCE_MS`. D-07 mentions `SMARTCOPILOT_VAULT_WATCH_DEBOUNCE_MS` but adding an `env_prefix` would break all existing env vars (Phase 1b already ships without prefix). Use `validation_alias="VAULT_WATCH_DEBOUNCE_MS"` to keep the field name readable while accepting the env var. Document this discrepancy in a comment.

**4. Update `server/requirements.txt`:**

Append the four Phase 1c library declarations after the existing lines:
```
watchdog>=4.0
xxhash>=3.0
python-frontmatter>=1.1
markdown-it-py>=3.0
```

These libraries are already installed in the virtualenv (confirmed via RESEARCH.md Environment Availability section); this makes the dependency explicit in the manifest.
  </action>
  <verify>
    <automated>cd /home/yongxin.Li/Documents/nexora/smart-copilot/server && python -c "
import py_compile
for f in ['app/models/page.py','app/models/page_version.py','app/settings.py']:
    py_compile.compile(f, doraise=True)
    print(f'{f}: OK')
"</automated>
  </verify>
  <acceptance_criteria>
    - `server/app/models/page.py` contains `"fleeting"` in `page_note_type_enum` ENUM definition
    - `server/app/models/page.py` contains `"archived_fleeting"` in `page_note_type_enum` ENUM definition
    - `server/app/models/page.py` does NOT contain `"compiled_truth"` in `page_note_type_enum` ENUM definition (the wrong value is gone)
    - `server/app/models/page.py` contains `server_default="fleeting"` on the `note_type` column
    - `server/app/models/page.py` contains `timeline: Mapped[str | None]` mapped column
    - `server/app/models/page.py` contains `deleted_by: Mapped[uuid.UUID | None]` mapped column with FK to users.id
    - `server/app/models/page_version.py` contains `timeline: Mapped[str | None]` mapped column
    - `server/app/settings.py` contains `vault_watch_debounce_ms: int`
    - `server/app/settings.py` contains `shared_vault_write_policy: str`
    - `server/requirements.txt` contains `watchdog>=4.0`
    - `server/requirements.txt` contains `xxhash>=3.0`
    - `server/requirements.txt` contains `python-frontmatter>=1.1`
    - `server/requirements.txt` contains `markdown-it-py>=3.0`
    - All three Python files compile without syntax errors
  </acceptance_criteria>
  <done>Page model has timeline+deleted_by+fixed enum, PageVersion has timeline, settings has vault_watch_debounce_ms+shared_vault_write_policy, requirements.txt has all four Phase 1c deps declared</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Migration runtime → PostgreSQL | Raw SQL executed via op.execute; enum rename-and-recreate is pure DDL with no user input |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-01c01-01 | Tampering | Migration 0003 downgrade | accept | Downgrade is an admin operation; pre-production phase, no live data to corrupt |
| T-01c01-02 | Denial of Service | inotify limit (max_user_watches) | accept | Configuration/settings declared; actual guard is Phase 6 doctor check |
</threat_model>

<verification>
After both tasks complete, run Alembic migration against the test DB to confirm 0003 applies cleanly:

```bash
cd /home/yongxin.Li/Documents/nexora/smart-copilot/server
# Verify migration chain is correct (dry run)
alembic history | grep -E "0002|0003"

# Verify Python syntax on all modified files
python -c "
import py_compile
for f in [
    'alembic/versions/0003_phase_1c_vault.py',
    'app/models/page.py',
    'app/models/page_version.py',
    'app/settings.py',
]:
    py_compile.compile(f, doraise=True)
    print(f'{f}: OK')
"

# Verify model imports (no import errors)
python -c "from app.models.page import Page, page_note_type_enum; print('Page import OK'); print(page_note_type_enum.enums)"
python -c "from app.models.page_version import PageVersion; print('PageVersion import OK')"
python -c "from app.settings import settings; print('vault_watch_debounce_ms:', settings.vault_watch_debounce_ms)"
```
</verification>

<success_criteria>
- `alembic/versions/0003_phase_1c_vault.py` exists with correct revision chain (0002→0003)
- Migration adds `pages.timeline`, `pages.deleted_by` (FK users.id), `page_versions.timeline`
- Migration replaces `page_note_type_enum` with Zettelkasten lifecycle values (fleeting/literature/permanent/archived_fleeting/skill/moc)
- `models/page.py` ENUM definition matches migration and uses server_default="fleeting"
- `models/page.py` has both `timeline` and `deleted_by` mapped columns
- `models/page_version.py` has `timeline` mapped column
- `settings.py` exposes `vault_watch_debounce_ms` (int, default 750) and `shared_vault_write_policy` (str, default "admin_only")
- `requirements.txt` declares all four Phase 1c libraries with `>=` version floors
- All modified Python files pass `py_compile` syntax check
</success_criteria>

<output>
After completion, create `.planning/phases/01c-vault-watchdog-indexer/01c-01-SUMMARY.md`
</output>
