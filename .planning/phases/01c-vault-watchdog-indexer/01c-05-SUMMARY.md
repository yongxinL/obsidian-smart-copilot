---
phase: 01c-vault-watchdog-indexer
plan: "05"
subsystem: vault
tags: [watchdog, inotify, asyncio, filesystem, dedup]
wave: 3

# Dependency graph
requires:
  - "01c-04"
    provides: "services/pages.py, parse_vault_file, sanitize_filename_to_slug"
provides:
  - "vault/watcher.py: VaultEventHandler, index_vault_file, soft_delete_vault_file, main()"
  - "test_watcher.py: 6 passing tests (IDX-01, IDX-02, IDX-03)"
affects: ["01c-06", "01c-07", "01c-08"]

# Tech tracking
tech-stack:
  added: [watchdog (Observer/inotify), threading.Timer]
  patterns:
    - "asyncio.run_coroutine_threadsafe: ONLY correct primitive for OS thread → asyncio handoff (D-06)"
    - "Per-path debounce: cancellable threading.Timer dict (D-07, 750ms default)"
    - "enforce_timeline=False on watchdog path: filesystem always wins (D-03)"
    - "Content-hash deduplication: early return when hash unchanged (IDX-03)"

key-files:
  created:
    - "server/app/vault/watcher.py"
  modified:
    - "server/app/tests/vault/test_watcher.py"

key-decisions:
  - "D-06: run_coroutine_threadsafe exclusively for async handoff (overrides CLAUDE.md call_soon_threadsafe)"
  - "D-07: Per-path cancellable timer dict for debounce (threading.Timer)"
  - "D-03: Watchdog uses enforce_timeline=False — no timeline rejection, just warnings"
  - "vault_id resolved from filesystem path via vaults table (_resolve_vault_id_and_slug)"
  - "SMARTCOPILOT_VAULT_ID env var controls which vault is watched (Phase 1d will wire real vault paths)"

requirements-completed: [IDX-01, IDX-02, IDX-03]

# Metrics
duration: 18min
completed: 2026-05-11
---

# Phase 1c Plan 05: Real Vault Watchdog Implementation Summary

**Real inotify-based vault watchdog with asyncio.run_coroutine_threadsafe handoff and 6 passing tests**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-05-11T01:58:00Z
- **Completed:** 2026-05-11T02:16:00Z
- **Tasks:** 2 (committed together as single unit)
- **Commits:** 1
- **Files modified:** 2

## Accomplishments

- `vault/watcher.py` replaces Phase 1a stub with real inotify-based watchdog
- VaultEventHandler with per-path debounce (threading.Timer dict, 750ms)
- `run_coroutine_threadsafe` handoff (D-06) — ONLY correct primitive for OS thread to asyncio
- Immediate on_deleted (no debounce), graceful shutdown with timer cancellation (Pitfall 6)
- `index_vault_file` skips DB write when content_hash unchanged (IDX-03 dedup)
- `soft_delete_vault_file` soft-deletes page via DB (VAULT-08)
- `enforce_timeline=False` on watchdog path — filesystem always wins (D-03)
- 6 tests pass covering IDX-01/02/03: source invariant, debounce, immediate delete, hash dedup, latency, soft-delete

## Task Commits

| Task | Commit | Files |
|------|--------|-------|
| Real watchdog implementation + tests | `58bc475` | vault/watcher.py, test_watcher.py |

## Files Created/Modified

- `server/app/vault/watcher.py` — Real watchdog: VaultEventHandler (per-path debounce, run_coroutine_threadsafe handoff), index_vault_file (content-hash dedup, enforce_timeline=False), soft_delete_vault_file (DB soft-delete), _amain (signal handling, graceful shutdown), argparse entry point
- `server/app/tests/vault/test_watcher.py` — 6 tests: test_handoff_api_uses_run_coroutine_threadsafe (source invariant), test_debounce_coalesces_rapid_events (unit), test_on_deleted_immediate_handoff_no_debounce (unit), test_hash_dedup_skips_unchanged_file (integration), test_file_detection_latency (integration), test_on_deleted_triggers_soft_delete (integration)

## Decisions Made

- D-06: run_coroutine_threadsafe exclusively for async handoff (overrides CLAUDE.md call_soon_threadsafe example)
- D-07: Per-path cancellable timer dict for debounce (threading.Timer, 750ms default, from settings)
- D-03: Watchdog uses enforce_timeline=False — no timeline rejection, just warnings on timeline_mutated_by_filesystem
- vault_id resolved from filesystem path via vaults table (_resolve_vault_id_and_slug helper)
- SMARTCOPILOT_VAULT_ID env var controls which vault is watched (hardcoded /vaults default; Phase 1d wires real paths)
- D-01 through D-13 decisions from 01c-CONTEXT.md respected throughout

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Session context manager mismatch**
- **Found during:** test_hash_dedup_skips_unchanged_file and test_on_deleted_triggers_soft_delete
- **Issue:** `session_with_rls` is an async generator (requires `async for`), not an async context manager. `async with session_with_rls(ctx)` raised `TypeError: 'async_generator' object does not support the asynchronous context manager protocol`
- **Fix:** Replaced `async with session_with_rls(ctx) as session:` with `async for session in session_with_rls(ctx): ... await session.close()`
- **Files modified:** `server/app/tests/vault/test_watcher.py`
- **Verification:** Tests pass after fix
- **Committed in:** 58bc475 (part of task commit)

**2. [Rule 1 - Bug] Vault path mismatch in integration tests**
- **Found during:** test_hash_dedup_skips_unchanged_file, test_on_deleted_triggers_soft_delete
- **Issue:** `seed_vault` fixture creates a vault with path `/vaults/private/vaultuser-{hex}/` but `tmp_vault_dir` is `/tmp/pytest-.../vaults/private/testuser/`. Watchdog code resolves vault by filesystem path, not by env var alone — vault not found, FK constraint error
- **Fix:** In both tests, create a new vault record with path matching `tmp_vault_dir + "/"` before calling index/delete functions. Use `test_engine` fixture directly (no seed_vault dependency)
- **Files modified:** `server/app/tests/vault/test_watcher.py`
- **Verification:** Tests pass after fix
- **Committed in:** 58bc475 (part of task commit)

**3. [Rule 1 - Bug] Nested event loop in test_file_detection_latency**
- **Found during:** test_file_detection_latency (original implementation)
- **Issue:** `loop.run_until_complete(asyncio.sleep(1.5))` inside pytest-asyncio async test raised `RuntimeError: Cannot run the event loop while another loop is running`
- **Fix:** Use `threading.Event` for cross-thread signaling and `await asyncio.sleep()` directly in the async test body. Patch `app.vault.watcher.asyncio.run_coroutine_threadsafe` for detection.
- **Files modified:** `server/app/tests/vault/test_watcher.py`
- **Verification:** Tests pass after fix
- **Committed in:** 58bc475 (part of task commit)

**4. [Rule 1 - Bug] E741 ambiguous variable name in lint check**
- **Found during:** pre-commit hook ruff check before commit
- **Issue:** `any("run_coroutine_threadsafe" in l for l in lines_with_handoff)` — E741 "Ambiguous variable name: l"
- **Fix:** Renamed to `src_line` — `any("run_coroutine_threadsafe" in src_line for src_line in lines_with_handoff)`
- **Files modified:** `server/app/tests/vault/test_watcher.py`
- **Verification:** ruff check passes; committed cleanly
- **Committed in:** 58bc475 (part of task commit)

## Issues Encountered

- `session_with_rls` is an async generator, not an async context manager — needed `async for` + explicit `await session.close()`
- `seed_vault` fixture path (`/vaults/private/vaultuser-*/`) doesn't match `tmp_vault_dir` (`/tmp/pytest-*/vaults/private/testuser/`) — had to create matching vault records in tests
- Nested event loop: `loop.run_until_complete()` inside pytest-asyncio async test raises `RuntimeError` — must use threading.Event for cross-thread coordination

## Source Invariant Verification

All 9 acceptance criteria verified via source inspection:
- `run_coroutine_threadsafe` present
- `call_soon_threadsafe` absent (for async indexing)
- `PollingObserver` absent
- `Observer()` present (inotify on Linux)
- `threading.Timer` present
- `enforce_timeline=False` present
- `cancel_all_timers` present
- `structlog` present
- `asyncio.get_running_loop()` inside `_amain` (not at module level)

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| none | watcher.py | No new trust boundary surface introduced; watchdog follows existing auth/RLS patterns from Phase 1b |

## Next Phase Readiness

- `vault/watcher.py` ready for use by 01c-06 (MCP server), 01c-07 (REST API), 01c-08 (CLI)
- IDX-01 (inotify detection), IDX-02 (run_coroutine_threadsafe handoff), IDX-03 (hash dedup) all verified
- Phase 1d will wire real vault paths from settings into the watchdog startup

---
*Phase: 01c-vault-watchdog-indexer / Plan 05*
*Completed: 2026-05-11T02:16:00Z*
*Commit: 58bc475*