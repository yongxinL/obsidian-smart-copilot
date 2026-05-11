---
phase: 01c-vault-watchdog-indexer
plan: "06"
subsystem: scheduler-reconciler
tags: [apscheduler, reconciliation, xxhash, content-hash, drift-correction]
dependency-graph:
  requires:
    - phase: "01c-04"
      provides: "services/pages.py, upsert_page, soft_delete_page, parse_vault_file, sanitize_filename_to_slug"
  provides:
    - "scheduler/jobs/reconcile_vault.py: reconcile_vault() async function"
    - "APScheduler 5-minute drift-correction job (IDX-04)"
  affects: ["01c-07", "01c-08"]

tech-stack:
  added: [xxhash, apscheduler]
  patterns:
    - "system_operation_context + session_with_rls async generator pattern (identical to prune_login_attempts)"
    - "Lightweight reconciliation: xxhash64 comparison, enforce_timeline=False"
    - "D-08: coalesce=True, max_instances=1"

key-files:
  created:
    - "server/app/scheduler/jobs/reconcile_vault.py"
  modified:
    - "server/app/scheduler/run.py"
    - "server/app/tests/vault/test_reconcile.py"

key-decisions:
  - "D-08: coalesce=True and max_instances=1 prevent pile-up and parallel execution"
  - "D-03: reconcile_vault uses enforce_timeline=False — human filesystem edits are trusted (same as watchdog)"
  - "VAULT_ROOT defaults to /vaults but each vault.path is stored in DB — reconciler walks per-vault paths"
  - "Module-level function only (no closures) — APScheduler 3.x SQLAlchemyJobStore compatibility"

requirements-completed: [IDX-04]

metrics:
  duration: 20min
  completed: 2026-05-11
---

# Phase 1c Plan 06: Vault Reconciliation Job Summary

**5-minute APScheduler drift-correction job and 3 passing integration tests**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-05-11T01:15:00Z
- **Completed:** 2026-05-11T01:35:00Z
- **Tasks:** 2 (each committed atomically)
- **Commits:** 2
- **Files modified:** 3

## Accomplishments
- `reconcile_vault()` async function walks all vault paths from DB, computes xxhash64 for each .md file, compares against DB content_hash
- Files on disk not in DB OR hash changed → upsert_page(enforce_timeline=False)
- DB pages with no corresponding disk file → soft_delete_page(reason="reconciler_file_missing")
- Registered in scheduler/run.py: 5-min interval, coalesce=True, max_instances=1 (D-08)
- 3 integration tests: new file creates DB page, missing file soft-deletes DB page, unchanged hash skips page_versions growth

## Task Commits

| Task | Commit | Files |
| ---- | ------ | ----- |
| 1: reconcile_vault.py + scheduler extension | `5b97bae` | reconcile_vault.py, run.py |
| 2: test_reconcile.py real tests | `e8f1b8a` | test_reconcile.py |

## Files Created/Modified

- `server/app/scheduler/jobs/reconcile_vault.py` — reconcile_vault() walks all vaults from DB, builds disk_slugs dict via vault_path.rglob("*.md"), compares xxhash64 vs DB content_hash, calls upsert_page/soft_delete_page; uses system_operation_context + session_with_rls; D-08: coalesce, max_instances=1
- `server/app/scheduler/run.py` — extended with reconcile_vault import and add_job registration (5-min interval, id="reconcile_vault", coalesce=True, max_instances=1); log.info lists both jobs
- `server/app/tests/vault/test_reconcile.py` — 3 integration tests: _seed_vault_and_user() helper creates user+vault in same transaction via patched session_with_rls

## Decisions Made

- D-08: coalesce=True and max_instances=1 prevent pile-up and parallel execution after scheduler outage
- D-03: reconcile_vault uses enforce_timeline=False — human filesystem edits are trusted (same as watchdog)
- VAULT_ROOT defaults to /vaults but each vault.path is stored in DB — reconciler walks per-vault paths from the vaults table
- Module-level function only (no closures) — APScheduler 3.x SQLAlchemyJobStore compatibility (CLAUDE.md constraint)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] ModuleNotFoundError for app.db_session**
- **Found during:** Task 1 (reconcile_vault.py implementation)
- **Issue:** reconcile_vault.py imported `from app.db_session import session_with_rls` but the module is named `app.dependencies`
- **Fix:** Changed import to `from app.dependencies import session_with_rls` (matching prune_login_attempts.py pattern)
- **Files modified:** `server/app/scheduler/jobs/reconcile_vault.py`
- **Verification:** Import check passes
- **Committed in:** 5b97bae (part of task commit)

**2. [Rule 3 - Blocking] session_with_rls async generator vs async context manager**
- **Found during:** Task 2 (test_reconcile.py implementation)
- **Issue:** Tests used `async with session_with_rls(ctx) as session:` — raises TypeError because session_with_rls is an async generator (uses yield), not an async context manager
- **Fix:** Changed all usages to `async for session in session_with_rls(ctx):` (the canonical non-FastAPI session pattern)
- **Files modified:** `server/app/tests/vault/test_reconcile.py`
- **Verification:** Tests pass after fix
- **Committed in:** e8f1b8a (part of task commit)

**3. [Rule 1 - Bug] Foreign key constraint violation in test setup**
- **Found during:** Task 2 (test_reconcile.py implementation)
- **Issue:** _seed_vault_with_path inserted vault with owner_user_id but didn't create the user in the test DB (test factory session vs patched session_with_rls)
- **Fix:** Created _seed_vault_and_user() helper that creates both user AND vault in the same transaction via patched session_with_rls; uses uuid.uuid4() to avoid session-scoped fixture conflicts
- **Files modified:** `server/app/tests/vault/test_reconcile.py`
- **Verification:** All 3 tests pass
- **Committed in:** e8f1b8a (part of task commit)

**4. [Rule 3 - Blocking] SQLAlchemyProgrammingError: column "private" does not exist**
- **Found during:** Task 2 (test_reconcile.py implementation)
- **Issue:** Raw SQL INSERT used double-quotes `"private"` instead of single-quotes `'private'` for the kind column
- **Fix:** Changed all raw SQL INSERT statements to use single-quotes for PostgreSQL string literals
- **Files modified:** `server/app/tests/vault/test_reconcile.py`
- **Verification:** All 3 tests pass
- **Committed in:** e8f1b8a (part of task commit)

## Issues Encountered

- `session_with_rls` is an async generator (uses `yield`), not an async context manager — needed `async for` pattern throughout
- Test DB sessions (test factory) vs patched session_with_rls — created _seed_vault_and_user() to use the patched factory consistently
- Double-quotes in raw SQL for string literals — PostgreSQL requires single-quotes

## Source Invariant Verification

All acceptance criteria verified:
- `reconcile_vault.py` exists and passes py_compile
- `from app.scheduler.jobs.reconcile_vault import reconcile_vault` succeeds
- `reconcile_vault.py` contains `system_operation_context(request_id="reconcile_vault"`
- `reconcile_vault.py` contains `enforce_timeline=False` in upsert_page call
- `reconcile_vault.py` contains `reason="reconciler_file_missing"` in soft_delete_page call
- `reconcile_vault.py` does NOT contain any FastAPI imports
- `scheduler/run.py` contains `from app.scheduler.jobs.reconcile_vault import reconcile_vault`
- `scheduler/run.py` contains `id="reconcile_vault"` and `coalesce=True` and `max_instances=1`
- `scheduler/run.py` log.info lists both jobs

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| none | reconcile_vault.py | No new trust boundary surface; reconciler follows existing session_with_rls pattern from Phase 1b |

## Self-Check

- reconcile_vault.py: FOUND
- scheduler/run.py: FOUND
- test_reconcile.py: FOUND
- Commit 5b97bae: FOUND in git log
- Commit e8f1b8a: FOUND in git log
- All 3 tests pass: PASSED

## Next Phase Readiness
- reconcile_vault() ready for 01c-07 (MCP server can query vault state) and 01c-08 (CLI can trigger manual reconciliation)
- D-08 constraints (coalesce, max_instances) prevent runaway scheduler in production
- Content-hash dedup via IDX-03 ensures minimal DB writes during reconciliation

---
*Phase: 01c-vault-watchdog-indexer / Plan 06*
*Completed: 2026-05-11T01:35:00Z*
*Commits: 5b97bae, e8f1b8a*
