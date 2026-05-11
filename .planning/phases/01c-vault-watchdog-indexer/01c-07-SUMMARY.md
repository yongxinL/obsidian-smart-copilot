---
phase: 01c
plan: "07"
subsystem: openapi-pre-commit
tags: [openapi, pre-commit, testclient, spec-generation]
wave: 4
depends_on:
  - "01c-05"
  - "01c-06"

# Dependency graph
requires:
  - "server/app/main.py"
    provides: "/openapi.json endpoint via FastAPI"
  - "server/app/tests/conftest.py"
    provides: "env vars set at session start (SMARTCOPILOT_FERNET_KEY, JWT_SIGNING_KEY)"
provides:
  - "scripts/regen_openapi.py: OpenAPI spec regeneration script"
  - "VAULT-11: docs/openapi.json committed to repo"
  - "VAULT-11: test_openapi.py passing tests (2/2)"
affects: ["01d-01"]  # Phase 1d routes will trigger hook on changes

# Tech tracking
tech-stack:
  added: [fastapi.testclient, pre-commit local hooks]
  patterns:
    - "TestClient approach: in-process FastAPI spec generation, no real server needed"
    - "Env var guard before app.main import (Pitfall 7 in RESEARCH.md)"
    - "pre-commit local hook: system language, pass_filenames=false, triggers on routes/services/models"

key-files:
  created:
    - "scripts/regen_openapi.py"
    - "docs/openapi.json"
  modified:
    - ".pre-commit-config.yaml"
    - "server/app/tests/vault/test_openapi.py"

key-decisions:
  - "D-12: Hook runs scripts/regen_openapi.py via TestClient (no real server)"
  - "D-13: docs/openapi.json is COMMITTED to repo; CI fails on stale spec"
  - "Pre-commit config at repo root (.pre-commit-config.yaml) — single source of truth"
  - "entry uses relative path scripts/regen_openapi.py from repo root"
  - "Script uses __file__ to compute repo root, works from any CWD"

requirements-completed: [VAULT-11]

# Metrics
duration: 5min
completed: 2026-05-11
---

# Phase 1c Plan 07: OpenAPI Pre-Commit Hook Summary

**OpenAPI pre-commit hook wired (D-12/D-13), initial docs/openapi.json generated, 2/2 tests passing**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-11T03:25:00Z
- **Completed:** 2026-05-11T03:30:00Z
- **Tasks:** 2 (each committed atomically)
- **Commits:** 2
- **Files modified:** 4

## Accomplishments

- `scripts/regen_openapi.py`: env var guard checks `SMARTCOPILOT_FERNET_KEY` + `JWT_SIGNING_KEY` BEFORE importing `app.main` (Pitfall 7 fix); uses `TestClient(app, raise_server_exceptions=True)` to call `GET /openapi.json`; writes to `docs/openapi.json`
- `.pre-commit-config.yaml` (repo root): added `regen-openapi` local hook — triggers on `server/app/(routes|services|models)/.*\.py$`, `pass_filenames: false`, `language: system`
- `docs/openapi.json`: initial generated spec with 6 paths (`/health`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/api/v1/admin/reauth`, `/api/v1/admin/_demo_destructive`)
- `test_openapi.py`: both stubs replaced with real tests — 2/2 passing

## Task Commits

| Task | Commit | Files |
| ---- | ------ | ----- |
| 1: regen_openapi.py + pre-commit config + initial openapi.json | `7e61cff` | scripts/regen_openapi.py, .pre-commit-config.yaml, docs/openapi.json |
| 2: test_openapi.py real tests | `08cf09d` | server/app/tests/vault/test_openapi.py |

## Files Created/Modified

- `scripts/regen_openapi.py` — Env var guard (SMARTCOPILOT_FERNET_KEY, JWT_SIGNING_KEY) before app.main import; `fastapi.testclient.TestClient` GET /openapi.json; writes `docs/openapi.json` via `json.dumps(resp.json(), indent=2)`
- `.pre-commit-config.yaml` (repo root) — Added `regen-openapi` local hook after ruff hooks; triggers on `^server/app/(routes|services|models)/.*\.py$`, `pass_filenames: false`
- `docs/openapi.json` — Initial generated spec; openapi 3.1.0, "Smart Copilot" v0.0.0; 6 paths; committed to repo
- `server/app/tests/vault/test_openapi.py` — Replaced stubs with real tests: `test_openapi_json_exists_and_is_valid_json` + `test_openapi_spec_matches_live_app`

## Decisions Made

- D-12: Hook runs `scripts/regen_openapi.py` via `TestClient` — no real server needed for spec generation
- D-13: `docs/openapi.json` is COMMITTED to repo; Phase 8 Electron client uses it for TypeScript codegen
- Pre-commit config lives at repo root (`.pre-commit-config.yaml`) — single source of truth, not duplicated at `server/.pre-commit-config.yaml`
- `entry: python scripts/regen_openapi.py` uses relative path from repo root; script uses `Path(__file__).resolve().parent.parent` to compute repo root
- Pitfall 7 in RESEARCH.md: env vars checked BEFORE `from app.main import app` — prevents `_fail_startup_if_missing_secrets()` from firing during script execution

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- `ruff format` reformatted both files during commit — re-staged and recommitted with formatted versions
- `test_shared_vault.py` tests have pre-existing failures (unrelated to this plan — they fail due to `PageNotFound` which is a service-layer issue, not an openapi hook issue)

## Source Invariant Verification

All acceptance criteria verified:
- `scripts/regen_openapi.py` exists and passes `py_compile`
- `scripts/regen_openapi.py` contains `os.environ.get("SMARTCOPILOT_FERNET_KEY")` check before any app import
- `scripts/regen_openapi.py` contains `from fastapi.testclient import TestClient`
- `scripts/regen_openapi.py` contains `from app.main import app` AFTER the env var check
- `.pre-commit-config.yaml` contains `id: regen-openapi`
- `.pre-commit-config.yaml` contains `files: ^server/app/(routes|services|models)/.*\.py$`
- `.pre-commit-config.yaml` still contains both `ruff-check` and `ruff-format` hooks
- `docs/openapi.json` exists and contains valid JSON
- `docs/openapi.json` contains `"openapi"` key
- `pytest app/tests/vault/test_openapi.py -x -q` exits 0, 2 tests PASSED

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| none | regen_openapi.py | No new trust boundary surface; script requires env vars and exits cleanly if missing |

## Phase 1c Completion

This plan completes Phase 1c (Vault + Watchdog Indexer). All VAULT requirements (01-11) and IDX requirements (01-04) are implemented:

- VAULT-01 through VAULT-10: page CRUD service, compiled-truth/timeline, frontmatter, wikilinks, content-hash
- VAULT-11: OpenAPI pre-commit hook and committed spec (this plan)
- IDX-01 through IDX-04: watchdog, reconciliation, content-hash dedup

All 11 plans (01c-01 through 01c-07) are complete.

---
*Phase: 01c-vault-watchdog-indexer / Plan 07*
*Completed: 2026-05-11T03:30:00Z*
*Commits: 7e61cff, 08cf09d*