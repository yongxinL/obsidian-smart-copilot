---
phase: 01c-vault-watchdog-indexer
plan: "01"
subsystem: database
tags: [alembic, postgresql, pydantic, schema]

# Dependency graph
requires:
  - phase: 01b-auth-security-primitives
    provides: Users table FK, sessions table, system user seed
provides:
  - Phase 1c schema foundation: migration 0003, updated Page/PageVersion models, vault watchdog settings
affects:
  - Phase 1c subsequent plans (01c-02 through 01c-08)
  - Page service layer
  - Watchdog indexer
  - Vault filesystem parser

# Tech tracking
tech-stack:
  added: [watchdog>=4.0, xxhash>=3.0, python-frontmatter>=1.1, markdown-it-py>=3.0]
  patterns: [Alembic enum rename-and-recreate pattern, SQLAlchemy mapped_column with UUID FK]

key-files:
  created:
    - server/alembic/versions/0003_phase_1c_vault.py
  modified:
    - server/app/models/page.py
    - server/app/models/page_version.py
    - server/app/settings.py
    - server/requirements.txt

key-decisions:
  - "D-04: page_note_type_enum replaced with Zettelkasten lifecycle values (fleeting/literature/permanent/archived_fleeting/skill/moc)"
  - "D-07: vault_watch_debounce_ms uses validation_alias='VAULT_WATCH_DEBOUNCE_MS' to match documented env var without adding env_prefix"
  - "Alembic enum rename-and-recreate: create new type, add column, drop old column, rename new column, drop old type, rename new type"

patterns-established:
  - "Pattern: Alembic op.execute for multi-step DDL (enum replacement, FK constraint creation)"
  - "Pattern: SQLAlchemy mapped_column with UUID(as_uuid=True) + ForeignKey for nullable user refs"
  - "Pattern: pydantic Field with validation_alias for env var mapping without env_prefix"

requirements-completed: [VAULT-04, VAULT-06, VAULT-07, VAULT-08]

# Metrics
duration: ~5min
completed: 2026-05-10
---

# Phase 01c Plan 01: Vault Schema Foundation Summary

**Alembic migration 0003 adds pages.timeline/deleted_by columns, page_versions.timeline, and replaces page_note_type_enum with Zettelkasten lifecycle values; Page/PageVersion models and settings updated accordingly**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-10T23:43:31Z
- **Completed:** 2026-05-10T23:48:46Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Alembic migration 0003 (0002→0003) with pages.timeline TEXT, pages.deleted_by UUID FK users.id, page_versions.timeline TEXT
- Enum rename-and-recreate pattern replaces page_note_type_enum: compiled_truth/timeline/mixed → fleeting/literature/permanent/archived_fleeting/skill/moc
- SQLAlchemy Page model: timeline + deleted_by mapped columns, enum values + server_default updated
- SQLAlchemy PageVersion model: timeline mapped column added
- settings.py: vault_watch_debounce_ms (int, 750ms, env: VAULT_WATCH_DEBOUNCE_MS) + shared_vault_write_policy (str, admin_only)
- requirements.txt: watchdog, xxhash, python-frontmatter, markdown-it-py declared

## Task Commits

Each task was committed atomically:

1. **Task 1: Alembic migration 0003** - `c5670ae` (feat)
2. **Task 2: Page/PageVersion models + Settings + requirements** - `88f5f9b` (feat)

## Files Created/Modified
- `server/alembic/versions/0003_phase_1c_vault.py` - Alembic migration 0003: timeline/deleted_by columns + enum fix
- `server/app/models/page.py` - SQLAlchemy Page model: timeline + deleted_by columns, fixed note_type enum
- `server/app/models/page_version.py` - SQLAlchemy PageVersion model: timeline column added
- `server/app/settings.py` - Settings: vault_watch_debounce_ms + shared_vault_write_policy fields
- `server/requirements.txt` - Phase 1c dependencies declared

## Decisions Made
- Used validation_alias="VAULT_WATCH_DEBOUNCE_MS" on vault_watch_debounce_ms to match D-07 env var without adding env_prefix (which would break all existing Phase 1b env vars)
- Migration downgrade reverses in opposite order: constraint drop first, then enum reversal, then column drops

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

```
alembic history:
  0002 -> 0003 (head), phase_1c_vault
  0001 -> 0002, phase_1b_auth
  <base> -> 0001, initial_schema

py_compile checks: all 4 files OK

Model imports:
  Page import OK — Enum values: ['fleeting', 'literature', 'permanent', 'archived_fleeting', 'skill', 'moc']
  PageVersion import OK

Settings:
  vault_watch_debounce_ms: 750
  shared_vault_write_policy: admin_only
```

## Next Phase Readiness
- Migration 0003 is the blocking prerequisite for all subsequent Phase 1c plans
- Page/PageVersion models ready for page service layer (01c-03+)
- Settings vault fields ready for watchdog configuration
- Phase 1c-02 (test fixtures) already committed on this branch

---
*Phase: 01c-vault-watchdog-indexer*
*Completed: 2026-05-10*
