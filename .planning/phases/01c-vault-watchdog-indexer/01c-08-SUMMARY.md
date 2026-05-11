---
phase: 01c-vault-watchdog-indexer
plan: "08"
subsystem: gap-closure
tags: [gap-closure, reconcile, requirements, doc-alignment]
wave: 1
depends_on:
  - "01c-07"
files_modified:
  - server/app/scheduler/jobs/reconcile_vault.py
  - server/requirements.txt
  - .planning/REQUIREMENTS.md
  - CLAUDE.md
autonomous: true
requirements:
  - IDX-02
  - IDX-04
gap_closure: true

# Dependency graph
requires:
  - "01c-06"
    provides: "reconcile_vault.py with session.commit outside loop"
  - "01c-07"
    provides: "Phase 1c implementation verification"
provides:
  - "CR-01 gap closed: per-vault commit inside loop"
  - "WR-06 gap closed: mcp and apscheduler declared"
  - "IDX-02 gap closed: docs aligned with D-06 decision"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-vault try/except with rollback on exception"
    - "Commit inside for-vault loop at indent 16 (for loop at indent 8)"

key-files:
  modified:
    - "server/app/scheduler/jobs/reconcile_vault.py"
    - "server/requirements.txt"
    - ".planning/REQUIREMENTS.md"
    - "CLAUDE.md"

key-decisions:
  - "CR-01 fix: session.commit moved from after-for-loop (indent 8) to inside for-vault block (indent 16)"
  - "D-06 alignment: CLAUDE.md now explicitly documents run_coroutine_threadsafe for watchdog async handoff"

patterns-established:
  - "Per-vault commit pattern: try/except around all per-vault work, rollback on exception, commit on success"

requirements-completed: [IDX-02, IDX-04]

# Metrics
duration: 2min
completed: 2026-05-11
---

# Phase 01c Plan 08: Gap Closure Summary

**All three Phase 01c verification gaps closed: CR-01 (per-vault commit), WR-06 (missing deps), IDX-02 (doc alignment)**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-05-11T03:33:43Z
- **Completed:** 2026-05-11T03:35:00Z
- **Tasks:** 3 (each committed atomically)
- **Commits:** 3
- **Files modified:** 4

## Accomplishments

- `reconcile_vault.py`: added `try/except` wrapper around all per-vault work; `await session.commit()` now fires at indent 16 (inside `for vault in vaults:` at indent 8); `await session.rollback()` on any vault-level exception
- `requirements.txt`: added `mcp>=1.25,<2` and `apscheduler>=3.10,<4` (both used in production but previously undeclared)
- `CLAUDE.md`: added Architecture Notes section documenting watchdog async handoff with `asyncio.run_coroutine_threadsafe(coro, loop)` as the correct primitive (D-06)
- `REQUIREMENTS.md` IDX-02 already correctly reads `asyncio.run_coroutine_threadsafe(coro, loop)` with `(D-06)` reference

## Task Commits

| Task | Commit | Files |
| ---- | ------ | ----- |
| 1: CR-01 fix: per-vault commit inside loop | `1de9ac7` | reconcile_vault.py |
| 2: WR-06 fix: add mcp and apscheduler | `6771dcb` | requirements.txt |
| 3: IDX-02 alignment: CLAUDE.md watchdog note | `75ac33c` | CLAUDE.md, REQUIREMENTS.md |

## Files Created/Modified

- `server/app/scheduler/jobs/reconcile_vault.py` — CR-01 fix: added try/except wrapper around per-vault work; `await session.commit()` at indent 16 (inside for loop at indent 8); `await session.rollback()` on vault-level exception; `log.error("reconcile_vault_failed", ...)` in outer except block
- `server/requirements.txt` — Added `mcp>=1.25,<2` and `apscheduler>=3.10,<4`; all 18 original lines preserved
- `.planning/REQUIREMENTS.md` — IDX-02 line 53 already reads `asyncio.run_coroutine_threadsafe(coro, loop)` with `(D-06)` reference; confirmed no change needed
- `CLAUDE.md` — Added Architecture Notes section with watchdog async handoff guidance; `asyncio.run_coroutine_threadsafe(coro, loop)` stated as correct primitive; `loop.call_soon_threadsafe()` explained as for synchronous callbacks only

## Decisions Made

- CR-01 fix: `await session.commit()` moved from after `for vault in vaults:` loop (indent 8) to inside the loop body (indent 16) with per-vault try/except wrapper — one failing vault no longer discards work for other vaults
- D-06 alignment: CLAUDE.md Architecture Notes section now explicitly documents the watchdog async handoff pattern; REQUIREMENTS.md IDX-02 already correct — no text change needed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] session.commit outside for-vault loop (CR-01)**
- **Found during:** Task 1 (initial file read)
- **Issue:** `await session.commit()` was at line 118, indent 8 (after the `for vault in vaults:` loop ends). Any unhandled exception during vault processing caused all committed work to be lost.
- **Fix:** Wrapped all per-vault work in `try/except`; moved `await session.commit()` inside the `for vault in vaults:` loop at indent 16; added `await session.rollback()` in except block
- **Files modified:** `server/app/scheduler/jobs/reconcile_vault.py`
- **Verification:** Commit at indent 16 (inside for loop at indent 8); rollback at indent 16; all three gaps verified programmatically
- **Committed in:** `1de9ac7`

**2. [Rule 3 - Blocking] CLAUDE.md watchdog section missing (D-06)**
- **Found during:** Task 3 (initial file read)
- **Issue:** CLAUDE.md is only 60 lines and contains no watchdog architecture note; D-06 decision not documented in CLAUDE.md
- **Fix:** Added new Architecture Notes section with watchdog async handoff guidance; explicit `asyncio.run_coroutine_threadsafe(coro, loop)` statement
- **Files modified:** `CLAUDE.md`
- **Verification:** `run_coroutine_threadsafe(coro, loop)` and `asyncio.run_coroutine_threadsafe` both now appear in CLAUDE.md
- **Committed in:** `75ac33c`

## Verification Results

```
GAP 1: commit inside loop
  FOR LOOP indent: 8, COMMIT indent: 16, ROLLBACK indent: 16
  PASS

GAP 2: requirements.txt
  mcp>=1.25,<2 present: PASS
  apscheduler>=3.10,<4 present: PASS
  All 18 original lines preserved: PASS

GAP 3: docs aligned with D-06
  REQUIREMENTS.md IDX-02 run_coroutine_threadsafe: PASS
  CLAUDE.md asyncio.run_coroutine_threadsafe: PASS
  call_soon_threadsafe() only absent from REQUIREMENTS.md: PASS
```

## Self-Check

| Check | Status |
|-------|--------|
| All 3 tasks executed | PASSED |
| All 3 tasks committed | PASSED (1de9ac7, 6771dcb, 75ac33c) |
| reconcile_vault.py commit inside for loop | PASSED |
| reconcile_vault.py has rollback | PASSED |
| requirements.txt has mcp and apscheduler | PASSED |
| CLAUDE.md has run_coroutine_threadsafe | PASSED |
| REQUIREMENTS.md IDX-02 correct | PASSED |

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| none | reconcile_vault.py | Per-vault rollback pattern is standard; no new trust boundary surface introduced |

## Phase 01c Completion

This plan completes Phase 01c (Vault + Watchdog Indexer). All gap-closure items resolved:

- CR-01 (BLOCKER): Per-vault commit inside loop with rollback — FIXED
- WR-06 (BLOCKER): mcp and apscheduler declared in requirements.txt — FIXED
- IDX-02 (WARNING): Docs aligned with D-06 decision — FIXED

All VAULT requirements (01-11) and IDX requirements (01-04) are implemented and verified.

---
*Phase: 01c-vault-watchdog-indexer / Plan 08*
*Completed: 2026-05-11T03:35:00Z*
*Commits: 1de9ac7, 6771dcb, 75ac33c*
