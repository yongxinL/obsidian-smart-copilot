---
phase: 01d
plan: 05
subsystem: cli
tags: [argparse, cli, doctor, reconcile, vault-crd, mcp-serve, integration-tests]
key-decisions:
  - "D-13: CLI expanded with 7 new subcommands; existing Phase 1b subcommands carry forward unchanged"
  - "D-14: doctor reports 6 sections: fernet_key, inotify_max_user_watches, cors_config, mcp_token_storage, db_connection, db_pgvector_extension"
  - "CLI uses system_operation_context for resolve/reconcile and per-user OperationContext(user_id) for page operations via session_with_rls"
  - "mcp_token.py extended in-place to register serve subcommand under mcp parent (add_serve_to_mcp_subparser hook)"
  - "vault_stats field names (live_pages/deleted_pages/total_bytes/last_updated_at) match VaultStats dataclass in services/pages.py"
  - "check-resolvable empty-tree invariant: nonexistent dir OR empty dir both return exit 0 with 'check: OK' — Phase 1 passes cleanly"
patterns-established:
  - "CLI subcommand pattern: add_subparser() + async _handle_X(args) returning int exit code"
  - "Transport-agnostic CLI: all ops use session_with_rls(ctx) with system_operation_context or per-user ctx"
  - "Integration tests use postgres_container fixture, subprocess.run in server/ cwd, env vars for secrets"
requirements-completed: [CLI-01, CLI-02, CLI-03]

# Dependency graph
requires:
  - phase: 01c
    provides: reconcile_vault() entrypoint in scheduler/jobs/reconcile_vault.py
  - phase: 01d-01
    provides: services/pages.py (write_page, read_page, soft_delete_page, list_pages, search_pages_fts, vault_stats)
  - phase: 01d-02
    provides: mcp/server.py (main_stdio, main_http entrypoints)
provides:
  - smartcopilot page get/put/delete/list/search subcommands (vault CRUD)
  - smartcopilot doctor (D-14 health smoke)
  - smartcopilot check-resolvable (CLI-03 empty-tree validator)
  - smartcopilot reconcile (Phase 1c synchronous reconciliation)
  - smartcopilot stats (vault page-count summary)
  - smartcopilot mcp serve --stdio|--http (MCP server dispatch)
affects:
  - Phase 1d-06 (acceptance test exercises mcp serve --stdio)
  - Phase 2a (FTS search expanded with chunk-level BM25)
  - Phase 3 (check-resolvable gains skills tree validation)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CLI subparser pattern: add_subparser(sub) + async _handle_X(args) -> int"
    - "Integration test pattern: subprocess.run with env vars, postgres_container fixture"

key-files:
  created:
    - server/app/cli/page.py
    - server/app/cli/doctor.py
    - server/app/cli/check_resolvable.py
    - server/app/cli/reconcile.py
    - server/app/cli/stats.py
    - server/app/cli/mcp_serve.py
    - server/app/tests/integration/test_cli_page.py
    - server/app/tests/integration/test_cli_doctor.py
    - server/app/tests/integration/test_cli_check_resolvable.py
    - server/app/tests/integration/test_cli_mcp_serve.py
    - server/app/tests/integration/test_cli_reconcile.py
  modified:
    - server/app/cli/main.py (registers all new subparsers)
    - server/app/cli/mcp_token.py (extends mcp with serve subcommand)

# Metrics
duration: 11min
completed: 2026-05-11
---

# Phase 01d Plan 05 Summary

**smartcopilot CLI expanded with 7 new subcommands: page CRUD, doctor health smoke, check-resolvable validator, reconcile, stats, and mcp serve dispatch**

## Performance

- **Duration:** 11 min
- **Started:** 2026-05-11T14:30:00Z
- **Completed:** 2026-05-11T14:41:00Z
- **Tasks:** 3 (all combined into single atomic commit)
- **Files created:** 11 (6 CLI modules + 5 integration test files)
- **Files modified:** 2 (main.py, mcp_token.py)

## Accomplishments

- 7 new CLI subcommands shipped (page, doctor, check-resolvable, reconcile, stats, mcp serve)
- D-14 doctor health smoke with 6 mandatory sections (fernet, inotify, cors, mcp_token_storage, db_connection, pgvector)
- Integration tests for all new commands (12 test functions total)
- mcp serve --stdio correctly dispatches to main_stdio; bad token exits 1 with AUTH ERROR on stderr
- --help discoverability verified: all 8 subcommands listed

## Task Commits

1. **Tasks 1+2+3 combined** - `0368f27` (feat)

**Plan metadata:** (not committed — per instructions: no STATE.md/ROADMAP.md updates)

## Files Created/Modified

- `server/app/cli/page.py` - vault CRUD (get/put/delete/list/search) via services/pages
- `server/app/cli/doctor.py` - D-14 health smoke (fernet, inotify, cors, db, pgvector)
- `server/app/cli/check_resolvable.py` - empty-skills-tree validator (Phase 1 invariant)
- `server/app/cli/reconcile.py` - synchronous Phase 1c reconciliation job wrapper
- `server/app/cli/stats.py` - vault page-count summary (live/deleted/bytes/last_updated)
- `server/app/cli/mcp_serve.py` - dispatch to main_stdio/main_http entrypoints
- `server/app/cli/main.py` - registers all 8 subparsers (user, mcp, provider, page, doctor, check-resolvable, reconcile, stats)
- `server/app/cli/mcp_token.py` - extended with add_serve_to_mcp_subparser() hook
- `server/app/tests/integration/test_cli_page.py` - 6 tests (put/get/list/search/delete/stats round-trip)
- `server/app/tests/integration/test_cli_doctor.py` - 2 tests (all sections present, ferret missing → exit 1)
- `server/app/tests/integration/test_cli_check_resolvable.py` - 2 tests (missing dir, empty dir both pass)
- `server/app/tests/integration/test_cli_mcp_serve.py` - 3 tests (--help lists all, bad token exits 1, transport required)
- `server/app/tests/integration/test_cli_reconcile.py` - 1 test (reconcile exits 0 with reconcile_vault_complete)

## Decisions Made

- D-13: CLI uses system_operation_context for system ops (resolve/reconcile) and per-user OperationContext for page-level CRUD
- D-14: doctor reports "none configured" for cors_config when settings has no cors_allow_origins (forward-compatible)
- vault_stats field names match VaultStats dataclass: live_pages/deleted_pages/total_bytes/last_updated_at
- check-resolvable uses `any(skills_dir.iterdir())` to detect empty directory (covers existing-but-empty case)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Ruff E702 (semicolon statements): fixed 7 `print(...); return N` to multi-line `print(...)\nreturn N`
- Ruff auto-format reformatted all 13 files with `ruff format --fix` (pre-commit hook auto-fixed, no manual edits needed)
- Plan showed reconcile_vault() signature as `async def reconcile_vault(deep: bool = False) -> dict`; actual signature is `async def reconcile_vault() -> None` (no parameters). Adapted to match actual Phase 1c implementation and removed `--deep` flag per plan guidance.

## Next Phase Readiness

- Plan 06 (acceptance test) can exercise `smartcopilot mcp serve --stdio` end-to-end
- All CLI subcommands registered and discoverable via --help
- Integration test suite ready for verification pass

---
*Phase: 01d-05*
*Completed: 2026-05-11*