---
phase: 1c
slug: vault-watchdog-indexer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-08
---

# Phase 1c — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 1.x |
| **Config file** | `server/pyproject.toml` (`asyncio_mode = "auto"`, `asyncio_default_fixture_loop_scope = "session"`) |
| **Quick run command** | `cd server && pytest app/tests/vault/ -x -q` |
| **Full suite command** | `cd server && pytest -ra` |
| **Estimated runtime** | ~60–120 seconds (integration tests use testcontainers) |

---

## Sampling Rate

- **After every task commit:** Run `cd server && pytest app/tests/vault/ -x -q --no-header`
- **After every plan wave:** Run `cd server && pytest -ra`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1c-W0-01 | 01 | 0 | VAULT-01, VAULT-10 | T-path-traversal | Symlink escape + `..` traversal rejected | unit | `pytest app/tests/vault/test_paths.py -x` | ❌ W0 | ⬜ pending |
| 1c-W0-02 | 01 | 0 | VAULT-04, VAULT-05, VAULT-07 | — | Parser returns correct body_shape + content_hash | unit | `pytest app/tests/vault/test_parser.py -x` | ❌ W0 | ⬜ pending |
| 1c-W0-03 | 01 | 0 | VAULT-04, VAULT-06, VAULT-08 | — | Service: timeline append-only, versioning, soft-delete | integration | `pytest app/tests/vault/test_pages_service.py -x` | ❌ W0 | ⬜ pending |
| 1c-W0-04 | 01 | 0 | VAULT-09 | T-cross-user-wikilink | Wikilink resolver scopes to user vault | integration | `pytest app/tests/vault/test_wikilinks.py -x` | ❌ W0 | ⬜ pending |
| 1c-W0-05 | 01 | 0 | VAULT-02 | T-rls-isolation | RLS: user A pages invisible to user B | integration | `pytest app/tests/vault/test_rls_pages.py -x` | ❌ W0 | ⬜ pending |
| 1c-W0-06 | 01 | 0 | VAULT-03 | — | Shared vault read-all; admin_only write enforced | integration | `pytest app/tests/vault/test_shared_vault.py -x` | ❌ W0 | ⬜ pending |
| 1c-W0-07 | 01 | 0 | IDX-01, IDX-02, IDX-03 | — | Watchdog detects change ≤1s; run_coroutine_threadsafe; hash dedup | integration | `pytest app/tests/vault/test_watcher.py -x` | ❌ W0 | ⬜ pending |
| 1c-W0-08 | 01 | 0 | IDX-04 | — | Reconciliation: missing page added, deleted file soft-deleted | integration | `pytest app/tests/vault/test_reconcile.py -x` | ❌ W0 | ⬜ pending |
| 1c-W0-09 | 01 | 0 | VAULT-11 | — | docs/openapi.json generated and matches live spec | integration | `pytest app/tests/vault/test_openapi.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `app/tests/vault/__init__.py` — package init
- [ ] `app/tests/vault/conftest.py` — shared fixtures (tmp vault dir, system_ctx, test vault records)
- [ ] `app/tests/vault/test_paths.py` — VAULT-01, VAULT-10 path safety + slug validation (stubs)
- [ ] `app/tests/vault/test_parser.py` — VAULT-04, VAULT-05, VAULT-07 frontmatter/body-shape/hash (stubs)
- [ ] `app/tests/vault/test_pages_service.py` — VAULT-04, VAULT-06, VAULT-08 service stubs
- [ ] `app/tests/vault/test_wikilinks.py` — VAULT-09 resolution algorithm stubs
- [ ] `app/tests/vault/test_rls_pages.py` — VAULT-02 RLS isolation stubs
- [ ] `app/tests/vault/test_shared_vault.py` — VAULT-03 shared vault policy stubs
- [ ] `app/tests/vault/test_watcher.py` — IDX-01, IDX-02, IDX-03 watchdog behavior stubs
- [ ] `app/tests/vault/test_reconcile.py` — IDX-04 reconciliation job stubs
- [ ] `app/tests/vault/test_openapi.py` — VAULT-11 spec freshness stub

*Wave 0 stubs use `pytest.skip()` with NO fixture parameters (no testcontainers spin-up). Pattern established in Phase 1b.*

*(No new framework install needed — pytest-asyncio + testcontainers already in requirements-dev.txt)*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| inotify watch limit warning logged when approaching 65536 | IDX-01 | Requires mounting large vault dir with thousands of subdirs | Run `smartcopilot reconcile --deep` against a vault with 1000+ directories; confirm warning in logs |
| Pre-commit hook fails with helpful message when FERNET_KEY absent | VAULT-11 | Requires shell environment manipulation | Unset `SMARTCOPILOT_FERNET_KEY`, run `pre-commit run regen-openapi`; confirm non-zero exit with clear error |
| Supervisord restarts watchdog process cleanly on crash | IDX-02 | Requires process kill signal; hard to automate in CI | Send SIGKILL to watcher process; confirm supervisord restarts it within 5 seconds |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
