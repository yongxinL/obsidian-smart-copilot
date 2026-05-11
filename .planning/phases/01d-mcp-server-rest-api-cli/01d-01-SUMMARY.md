---
phase: 01d-mcp-server-rest-api-cli
plan: "01"
subsystem: api
tags: [postgres, fts, tsvector, websearch_to_tsquery, pgvector, diff, revert, version-history, health-check]

# Dependency graph
requires:
  - phase: 01c-vault-indexing
    provides: pages, page_versions tables; upsert_page with VAULT-08 versioning; RLS session context
provides:
  - pages.search_vector tsvector column with GIN index (Alembic 0004)
  - services/pages.py: 8 new helpers (search_pages_fts, list_pages, get_page_history, get_page_diff, revert_page, get_backlinks_for_page, vault_stats, vault_health)
  - services/capabilities.py: get_capabilities() single source of truth for REST-05 parity
affects: [01d-02-mcp-tools, 01d-03-rest-routes, 02a-llm-gateway, 02b-knowledge-graph]

# Tech tracking
tech-stack:
  added: [difflib (stdlib), AST (stdlib for fastapi import check)]
  patterns:
    - Transport-agnostic service layer (zero FastAPI imports in services/)
    - Dataclass frozen/slots pattern for domain return types
    - websearch_to_tsquery + plainto_tsquery fallback for FTS queries
    - Unified diff (difflib) for compiled_truth and timeline history

key-files:
  created:
    - server/alembic/versions/0004_phase_1d_search_vector.py
    - server/app/services/capabilities.py
    - server/app/tests/vault/test_pages_history.py
    - server/app/tests/vault/test_capabilities.py
  modified:
    - server/app/services/pages.py
    - server/app/tests/vault/test_pages_service.py
    - server/app/tests/vault/test_search_fts.py

key-decisions:
  - "Used difflib.unified_diff for version diffs instead of external diff library (stdlib)"
  - "watchdog_alive = None in Phase 1d; Plan 04 will wire pg_notify-based heartbeat"
  - "FTS fallback: COALESCE(NULLIF(websearch_to_tsquery, ''), plainto_tsquery)"
  - "AST-based fastapi import check in test instead of string search (avoids docstring false positives)"

patterns-established:
  - "Phase 1d helpers: ctx parameter accepted (no-op for ARG001) for future scope-based authorization"
  - "VaultHealth.watchdog_alive: None until Plan 04 (pg_notify integration)"
  - "All new service helpers use parameterized SQL (text(:bind)) — no SQL injection risk"

requirements-completed: [REST-05, REST-06]

# Metrics
duration: 35min
completed: 2026-05-11
---

# Phase 1d, Plan 01 Summary

**PostgreSQL FTS migration + 8 transport-agnostic service helpers for search, history, diff, revert, backlinks, stats, and health**

## Performance

- **Duration:** 35 min
- **Started:** 2026-05-11T10:05:00Z
- **Completed:** 2026-05-11T10:40:00Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- Alembic migration 0004 adds `pages.search_vector` (GENERATED ALWAYS AS tsvector) + GIN index `ix_pages_search_vector`
- Extended `services/pages.py` with 8 new helpers: search_pages_fts, list_pages, get_page_history, get_page_diff, revert_page, get_backlinks_for_page, vault_stats, vault_health
- Created `services/capabilities.py` as single source of truth for REST-05 capability payload
- All helpers transport-agnostic (zero FastAPI imports, verified via ruff F401 check)
- 27 integration tests pass across Phase 1d test files

## Task Commits

Each task was committed atomically:

1. **Task 1: Alembic migration 0004 + test_search_fts.py** - `5363f8e` (test)
2. **Task 2: Extend services/pages.py with helpers** - `39d85c5` (feat)
3. **Task 3: Create services/capabilities.py + tests** - `32796b5` (feat)

**Plan metadata:** `8137be5` (docs: phase 1d planning docs)

## Files Created/Modified

- `server/alembic/versions/0004_phase_1d_search_vector.py` - FTS tsvector column + GIN index migration
- `server/app/services/pages.py` - 8 new helpers (search_pages_fts, list_pages, get_page_history, get_page_diff, revert_page, get_backlinks_for_page, vault_stats, vault_health) + 6 frozen dataclasses
- `server/app/services/capabilities.py` - get_capabilities() for REST-05 / MCP tool parity
- `server/app/tests/vault/test_search_fts.py` - 5 integration tests for migration 0004
- `server/app/tests/vault/test_pages_service.py` - Extended with 4 new tests for list_pages, vault_stats, vault_health
- `server/app/tests/vault/test_pages_history.py` - 5 integration tests for history/diff/revert
- `server/app/tests/vault/test_capabilities.py` - 2 unit tests for get_capabilities()

## Decisions Made

- Used `difflib.unified_diff` for version diffs (stdlib, no extra dependency)
- `watchdog_alive` is `None` in Phase 1d; Plan 04 wires pg_notify heartbeat detection
- FTS fallback pattern: `COALESCE(NULLIF(websearch_to_tsquery('english', :q), ''::tsquery), plainto_tsquery('english', :q))`
- AST-based fastapi import check in test instead of string search (avoids docstring false positives)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- **Working tree reverted to HEAD** after commit 39d85c5 due to `git stash pop` during pre-commit troubleshooting. Resolved by `git checkout 39d85c5 -- server/app/services/pages.py` to restore the helpers before task 3 testing.
- **3 pre-existing test failures in test_shared_vault.py** (RLS isolation in shared vault read path). These failures existed before this plan at commit 5363f8e and are out of scope for 01d-01.

## Next Phase Readiness

- Plans 02 (MCP tools) and 03 (REST routes) can import from `services/pages.py` and `services/capabilities.py` immediately
- All 8 helper functions have concrete signatures matching the contract in 01d-01-PLAN.md
- Migration 0004 is reversible and applies cleanly against testcontainer PostgreSQL

---
*Phase: 01d-mcp-server-rest-api-cli*
*Completed: 2026-05-11*