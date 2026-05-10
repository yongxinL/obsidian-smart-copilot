---
phase: 1a
slug: container-data-layer
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-08
---

# Phase 1a — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 1.x + testcontainers-python 4.x |
| **Config file** | `server/pyproject.toml` — Wave 0 installs |
| **Quick run command** | `cd server && ruff check app/ && pytest app/tests/ -x -q` |
| **Full suite command** | `cd server && ruff check app/ && pytest app/tests/ -v` |
| **Estimated runtime** | ~60 seconds (testcontainer boot ~20s + migration ~5s + tests) |

---

## Sampling Rate

- **After every task commit:** Run `cd server && ruff check app/ && pytest app/tests/ -x -q`
- **After every plan wave:** Run `cd server && ruff check app/ && pytest app/tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

> Wave alignment matches plan frontmatter: Plan 01 (wave 1), Plan 02 (wave 2), Plan 03 (wave 3), Plan 04 (wave 4 — Task 4 is human-verify checkpoint).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1a-01 | 01 | 1 | INFRA-04, INFRA-05 | — | N/A | unit (pnpm + version pin) | `pnpm install && pnpm ls && python3 --version \| grep 3.12 && node --version \| grep v20` | ❌ W0 | ⬜ pending |
| 1a-02 | 01 | 1 | INFRA-06 | — | N/A | unit | `cd server && ruff check app/` | ❌ W0 | ⬜ pending |
| 1a-03 | 01 | 1 | INFRA-06 | — | N/A | unit (pre-commit) | `cd server && pre-commit run --all-files` | ❌ W0 | ⬜ pending |
| 1a-04 | 02 | 2 | INFRA-07 | — | N/A | unit (import) | `cd server && python -c "from app.models import Base; print(len(Base.metadata.tables))"` | ❌ W0 | ⬜ pending |
| 1a-05 | 02 | 2 | INFRA-07 | T-1a-05 | encrypted_key column is BYTEA | unit (grep) | `grep -q LargeBinary server/app/models/provider_key.py` | ❌ W0 | ⬜ pending |
| 1a-06 | 02 | 2 | INFRA-07 | T-1a-07 | apscheduler_jobs excluded from metadata | unit (assertion) | `cd server && python -c "import app.models; assert 'apscheduler_jobs' not in app.models.Base.metadata.tables"` | ❌ W0 | ⬜ pending |
| 1a-07 | 03 | 3 | INFRA-07 | — | N/A | integration | `pytest app/tests/integration/test_boot.py::test_db_connection -x` | ❌ W0 | ⬜ pending |
| 1a-08 | 03 | 3 | INFRA-03 | — | N/A | integration | `pytest app/tests/integration/test_boot.py::test_pgvector_extension -x` | ❌ W0 | ⬜ pending |
| 1a-09 | 03 | 3 | TEST-01 | — | N/A | integration | `cd server && pytest app/tests/ -x` | ❌ W0 | ⬜ pending |
| 1a-10 | 04 | 4 | INFRA-02 | — | N/A | unit (grep) | `grep -c '^priority=' server/supervisord.conf \| grep -q '^5$' && grep -q 'app.mcp.server' server/supervisord.conf && grep -q 'app.scheduler.run' server/supervisord.conf && grep -q 'app.vault.watcher' server/supervisord.conf` | ❌ W0 | ⬜ pending |
| 1a-11 | 04 | 4 | INFRA-01 | T-1a-03 | postgres runs as user=postgres | unit (grep) | `grep -q '^user=postgres$' server/supervisord.conf && grep -q '^nodaemon=true' server/supervisord.conf` | ❌ W0 | ⬜ pending |
| 1a-12 | 04 | 4 | INFRA-08 | T-1a-13 | volumes declared in Dockerfile | unit (grep) | `grep -q '^VOLUME \["/data", "/vaults", "/config"\]' server/Dockerfile && grep -q '^FROM pgvector/pgvector:pg16' server/Dockerfile` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*W0 marker = file is created during phase execution as a Wave 0 artifact (see Wave 0 Requirements below) and does not yet exist at planning time.*

---

## Wave 0 Requirements

> Wave 0 = files that must exist before integration tests in later waves can run. They are created during phase execution (not pre-existing artifacts).

| Wave 0 File | Created By | Why It's Wave 0 |
|-------------|-----------|-----------------|
| `server/pyproject.toml` (with pytest-asyncio config: `asyncio_mode = auto`, `asyncio_default_fixture_loop_scope = "session"`) | Plan 01 | Test runner config required before any pytest invocation |
| `server/requirements-dev.txt` (`pytest>=9`, `pytest-asyncio>=1.0`, `testcontainers[postgres]>=4.0`) | Plan 01 | Test framework install |
| `server/.pre-commit-config.yaml` (ruff-check + ruff-format hooks) | Plan 01 | Pre-commit gate task 1a-03 |
| `server/app/tests/__init__.py` | Plan 03 | Test package marker |
| `server/app/tests/conftest.py` (session-scoped testcontainer, async engine, rollback-per-test fixture) | Plan 03 | Required by all integration tests in tasks 1a-07/08/09 |
| `server/app/tests/integration/__init__.py` | Plan 03 | Integration test package marker |
| `server/app/tests/integration/test_boot.py` (health check, pgvector extension, DB connection) | Plan 03 | Targets of tasks 1a-07/08/09 |

*Wave 0 completes during phase execution — `wave_0_complete: false` in frontmatter is the planning-time state. Will flip to `true` once Plans 01 + 03 finish (after which the Per-Task Verification Map's `❌ W0` markers also flip to ✅).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| supervisord all 5 programs RUNNING within 30s | INFRA-02 | Requires full Docker build + container boot; impractical in CI without Docker-in-Docker | `docker run --rm smart-copilot:latest sh -c "sleep 35 && supervisorctl status"` — verify all 5 show RUNNING (covered by Plan 04 Task 4 human checkpoint) |
| Alembic migrations run before uvicorn accepts connections | INFRA-01 | Startup ordering is supervisord priority-based; hard to assert programmatically without log parsing | Boot container, `docker logs <id>` — verify "Alembic upgrade complete" appears before "Application startup complete" (Plan 04 Task 4) |
| `/health` returns 200 after boot | INFRA-01 | Requires live container boot | `curl http://localhost:8000/health` after `docker run` — expect `{"status": "ok"}` (Plan 04 Task 4) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (verified after wave-mapping fix)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (every wave has automated verifies; Plan 04 Task 4 is the only manual-only task and is preceded by 3 automated tasks 1a-10/11/12)
- [x] Wave 0 covers all MISSING references (table above maps each Wave 0 file to its creator plan)
- [x] No watch-mode flags
- [x] Feedback latency < 90s (all `<automated>` blocks are static grep/file/import checks; live docker build/run is in plan `<action>` for executor + Plan 04 Task 4 human checkpoint)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending — wave 0 completes on execution
