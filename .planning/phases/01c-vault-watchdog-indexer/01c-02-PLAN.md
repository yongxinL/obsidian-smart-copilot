---
phase: 01c
plan: 02
type: execute
wave: 0
depends_on: []
files_modified:
  - server/app/tests/vault/__init__.py
  - server/app/tests/vault/conftest.py
  - server/app/tests/vault/test_paths.py
  - server/app/tests/vault/test_parser.py
  - server/app/tests/vault/test_pages_service.py
  - server/app/tests/vault/test_wikilinks.py
  - server/app/tests/vault/test_rls_pages.py
  - server/app/tests/vault/test_shared_vault.py
  - server/app/tests/vault/test_watcher.py
  - server/app/tests/vault/test_reconcile.py
  - server/app/tests/vault/test_openapi.py
autonomous: true
requirements:
  - VAULT-01
  - VAULT-02
  - VAULT-03
  - VAULT-04
  - VAULT-05
  - VAULT-06
  - VAULT-07
  - VAULT-08
  - VAULT-09
  - VAULT-10
  - VAULT-11
  - IDX-01
  - IDX-02
  - IDX-03
  - IDX-04

must_haves:
  truths:
    - "pytest can collect the vault test package without errors"
    - "All 9 test files exist in server/app/tests/vault/"
    - "All stub tests SKIP (not FAIL) when run against a real DB"
    - "conftest.py defines tmp_vault_dir, seed_vault, seed_page, system_ctx fixtures"
  artifacts:
    - path: "server/app/tests/vault/__init__.py"
      provides: "Package init for vault test directory"
    - path: "server/app/tests/vault/conftest.py"
      provides: "Shared fixtures: tmp_vault_dir, seed_vault, seed_page, system_ctx, _patch_session_factory"
      contains: "tmp_vault_dir"
    - path: "server/app/tests/vault/test_paths.py"
      provides: "VAULT-01, VAULT-10 test stubs"
      contains: "pytest.skip"
    - path: "server/app/tests/vault/test_watcher.py"
      provides: "IDX-01, IDX-02, IDX-03 test stubs"
      contains: "pytest.skip"
  key_links:
    - from: "server/app/tests/vault/conftest.py"
      to: "server/app/tests/conftest.py"
      via: "Inherits test_engine and postgres_container fixtures from parent conftest"
      pattern: "test_engine"
    - from: "server/app/tests/vault/conftest.py"
      to: "server/app/tests/auth/conftest.py"
      via: "_patch_session_factory pattern copied from auth conftest"
      pattern: "_patch_session_factory"
---

<objective>
Create the Wave 0 test scaffold for Phase 1c. This plan creates all 11 vault test files (1 conftest + 10 test files) as SKIP stubs. The stub pattern ensures tests are collected by pytest without importing implementation modules that do not yet exist, and without spinning up testcontainers (fast collection).

Purpose: Every subsequent plan can immediately run `pytest app/tests/vault/ -x -q` against its new files and see SKIP (not ERROR). Stubs define the test API surface that later plans flesh out.

Output: `server/app/tests/vault/` package with conftest.py and 10 stub test files.
</objective>

<context>
@.planning/phases/01c-vault-watchdog-indexer/01c-CONTEXT.md
@.planning/phases/01c-vault-watchdog-indexer/01c-RESEARCH.md
@.planning/phases/01c-vault-watchdog-indexer/01c-VALIDATION.md

<interfaces>
<!-- From server/app/tests/auth/conftest.py — the pattern this plan replicates -->
```python
# _patch_session_factory: session-scoped, autouse=True — redirects async_session_factory to test engine
@pytest_asyncio.fixture(scope="session", autouse=True, loop_scope="session")
async def _patch_session_factory(test_engine: AsyncEngine) -> AsyncIterator[None]:
    import app.dependencies as deps
    test_factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    original = deps.async_session_factory
    deps.async_session_factory = test_factory
    yield
    deps.async_session_factory = original
```

<!-- From server/app/tests/conftest.py — parent fixtures available to vault tests -->
```python
# Available fixtures (session-scoped, inherited automatically):
# postgres_container -> PostgresContainer
# test_engine -> AsyncEngine (with Alembic migrations run)
# db_session -> AsyncSession
```

<!-- From Phase 1b test stubs — the skip pattern (NO fixture params, just pytest.skip) -->
```python
# Pattern: stubs use pytest.skip() with NO fixture parameters
# This ensures they SKIP without spinning testcontainers
def test_something():
    pytest.skip("stub — implemented in Wave N")
```

<!-- From server/app/tests/auth/conftest.py — seed_user pattern -->
```python
async def _seed_user(engine, *, username, role, password_hash="$argon2id$...") -> uuid.UUID:
    uid = uuid.uuid4()
    async with factory() as session:
        await session.execute(text("INSERT INTO users ..."), {...})
        await session.commit()
    return uid
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Create vault test package init and conftest.py</name>
  <read_first>
    - server/app/tests/auth/conftest.py (full file — _patch_session_factory, seed_user patterns to replicate exactly)
    - server/app/tests/conftest.py (full file — understand inherited fixtures: test_engine, postgres_container)
    - server/app/tests/auth/__init__.py (1 line — package init pattern)
    - .planning/phases/01c-vault-watchdog-indexer/01c-VALIDATION.md (Wave 0 requirements list and test stubs pattern)
  </read_first>
  <files>server/app/tests/vault/__init__.py, server/app/tests/vault/conftest.py</files>
  <action>
**1. Create `server/app/tests/vault/__init__.py`:**

Match the pattern from `server/app/tests/auth/__init__.py` — single line:
```python
"""Vault + Watchdog Indexer test package — Phase 1c."""
```

**2. Create `server/app/tests/vault/conftest.py`:**

```python
"""Function-scoped vault fixtures consuming session-scope test_engine.

Reuses postgres_container, test_engine from server/app/tests/conftest.py.
Adds: tmp_vault_dir, seed_vault, seed_page, system_ctx.
Also adds: _patch_session_factory (session-scoped, autouse) — redirects
app.dependencies.async_session_factory to the testcontainer engine so that
session_with_rls() in vault service tests targets the test DB.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


@pytest_asyncio.fixture(scope="session", autouse=True, loop_scope="session")
async def _patch_session_factory(test_engine: AsyncEngine) -> AsyncIterator[None]:
    """Redirect session_with_rls to use the test engine pool (not prod DB).

    Mirrors server/app/tests/auth/conftest.py _patch_session_factory exactly.
    Also registers the production PoolEvents.reset listener on test_engine.
    """
    import app.dependencies as deps

    @event.listens_for(test_engine.sync_engine, "reset")
    def _on_pool_reset(dbapi_conn, connection_record, reset_state):  # noqa: ARG001
        async def _scrub(conn):
            await conn.execute("RESET app.current_user_id")
            await conn.execute("RESET app.current_user_role")
            await conn.execute("RESET app.request_id")

        try:
            dbapi_conn.run_async(_scrub)
        except Exception:  # noqa: BLE001
            pass

    test_factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    original = deps.async_session_factory
    deps.async_session_factory = test_factory
    yield
    deps.async_session_factory = original


@pytest.fixture
def tmp_vault_dir(tmp_path: Path) -> Path:
    """Return a temporary directory simulating a private vault root."""
    vault_root = tmp_path / "vaults" / "private" / "testuser"
    vault_root.mkdir(parents=True)
    return vault_root


@pytest_asyncio.fixture(loop_scope="session")
async def seed_user_for_vault(test_engine: AsyncEngine) -> AsyncIterator[uuid.UUID]:
    """Seed a user for vault tests. Returns the user UUID."""
    uid = uuid.uuid4()
    factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        await session.execute(
            text(
                "INSERT INTO users (id, username, role, password_hash, is_active, created_at, updated_at) "
                "VALUES (:id, :u, 'user', '$argon2id$v=19$m=65536,t=3,p=1$placeholder', true, now(), now())"
            ),
            {"id": uid, "u": f"vaultuser-{uid.hex[:8]}"},
        )
        await session.commit()
    yield uid
    async with factory() as session:
        await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": uid})
        await session.commit()


@pytest_asyncio.fixture(loop_scope="session")
async def seed_vault(test_engine: AsyncEngine, seed_user_for_vault: uuid.UUID) -> AsyncIterator[uuid.UUID]:
    """Seed a private vault row for the vault test user. Returns vault UUID."""
    vid = uuid.uuid4()
    factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        await session.execute(
            text(
                "INSERT INTO vaults (id, owner_user_id, kind, path, created_at, updated_at) "
                "VALUES (:id, :uid, 'private', :path, now(), now())"
            ),
            {"id": vid, "uid": seed_user_for_vault, "path": f"/vaults/private/vaultuser-{seed_user_for_vault.hex[:8]}/"},
        )
        await session.commit()
    yield vid
    async with factory() as session:
        await session.execute(text("DELETE FROM vaults WHERE id = :id"), {"id": vid})
        await session.commit()


@pytest_asyncio.fixture(loop_scope="session")
async def seed_page(test_engine: AsyncEngine, seed_vault: uuid.UUID) -> AsyncIterator[uuid.UUID]:
    """Seed a minimal page row for upsert/soft-delete tests. Returns page UUID."""
    pid = uuid.uuid4()
    factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        await session.execute(
            text(
                "INSERT INTO pages (id, vault_id, slug, type, note_type, frontmatter, compiled_truth, content_hash, created_at, updated_at) "
                "VALUES (:id, :vid, 'seed-page', 'note', 'fleeting', '{}', 'Seed content', 'abc123def456789a', now(), now())"
            ),
            {"id": pid, "vid": seed_vault},
        )
        await session.commit()
    yield pid
    async with factory() as session:
        await session.execute(text("DELETE FROM pages WHERE id = :id"), {"id": pid})
        await session.commit()


@pytest.fixture
def system_ctx():
    """Return a system OperationContext for watchdog/scheduler use."""
    from app.auth.context import system_operation_context
    return system_operation_context(request_id="test", client_name="test-vault")
```
  </action>
  <verify>
    <automated>cd /home/yongxin.Li/Documents/nexora/smart-copilot/server && python -c "import py_compile; py_compile.compile('app/tests/vault/conftest.py', doraise=True); print('conftest syntax OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `server/app/tests/vault/__init__.py` exists
    - `server/app/tests/vault/conftest.py` exists
    - conftest.py contains `_patch_session_factory` fixture with `autouse=True`
    - conftest.py contains `tmp_vault_dir` fixture
    - conftest.py contains `seed_vault` fixture
    - conftest.py contains `seed_page` fixture
    - conftest.py contains `system_ctx` fixture returning `system_operation_context(...)`
    - conftest.py passes `py_compile` syntax check
    - `from __future__ import annotations` is the first non-comment line
  </acceptance_criteria>
  <done>vault/ test package created with conftest.py defining all five fixtures (_patch_session_factory, tmp_vault_dir, seed_vault, seed_page, system_ctx)</done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Create all 10 Wave 0 test stubs (pytest.skip, no fixture params)</name>
  <read_first>
    - server/app/tests/vault/conftest.py (just created — understand available fixtures)
    - .planning/phases/01c-vault-watchdog-indexer/01c-VALIDATION.md (Per-Task Verification Map — exact test names and requirements coverage)
    - .planning/phases/01c-vault-watchdog-indexer/01c-RESEARCH.md (Validation Architecture section — test file list and requirement mapping)
  </read_first>
  <files>
    server/app/tests/vault/test_paths.py,
    server/app/tests/vault/test_parser.py,
    server/app/tests/vault/test_pages_service.py,
    server/app/tests/vault/test_wikilinks.py,
    server/app/tests/vault/test_rls_pages.py,
    server/app/tests/vault/test_shared_vault.py,
    server/app/tests/vault/test_watcher.py,
    server/app/tests/vault/test_reconcile.py,
    server/app/tests/vault/test_openapi.py
  </files>
  <action>
Create all 10 stub test files. CRITICAL RULE: stubs use `pytest.skip()` with NO fixture parameters. Each stub function calls `pytest.skip("stub — implemented in Wave N")` immediately, no fixture args, no imports of implementation modules that do not yet exist.

**`server/app/tests/vault/test_paths.py`** (VAULT-01, VAULT-10):
```python
"""Vault path safety tests — VAULT-01, VAULT-10.

Stubs: implemented when vault/paths.py lands in Wave 1.
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.vault, pytest.mark.unit]


def test_safe_vault_path_resolves_within_root():
    pytest.skip("stub — implemented in Wave 1 (vault/paths.py)")


def test_safe_vault_path_rejects_dotdot_traversal():
    pytest.skip("stub — implemented in Wave 1 (vault/paths.py)")


def test_safe_vault_path_rejects_symlink_escape():
    pytest.skip("stub — implemented in Wave 1 (vault/paths.py)")


def test_slug_validation_accepts_valid():
    pytest.skip("stub — implemented in Wave 1 (vault/paths.py)")


def test_slug_validation_rejects_uppercase():
    pytest.skip("stub — implemented in Wave 1 (vault/paths.py)")


def test_slug_validation_rejects_leading_hyphen():
    pytest.skip("stub — implemented in Wave 1 (vault/paths.py)")


def test_slug_sanitizer_converts_watchdog_filename():
    pytest.skip("stub — implemented in Wave 1 (vault/paths.py)")
```

**`server/app/tests/vault/test_parser.py`** (VAULT-04, VAULT-05, VAULT-07):
```python
"""Vault file parser tests — VAULT-04, VAULT-05, VAULT-07.

Stubs: implemented when vault/parser.py lands in Wave 1.
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.vault, pytest.mark.unit]


def test_parse_compiled_truth_only():
    pytest.skip("stub — implemented in Wave 1 (vault/parser.py)")


def test_parse_timeline_only():
    pytest.skip("stub — implemented in Wave 1 (vault/parser.py)")


def test_parse_mixed_body():
    pytest.skip("stub — implemented in Wave 1 (vault/parser.py)")


def test_parse_empty_body():
    pytest.skip("stub — implemented in Wave 1 (vault/parser.py)")


def test_multiple_separators_raises():
    pytest.skip("stub — implemented in Wave 1 (vault/parser.py)")


def test_frontmatter_page_types():
    pytest.skip("stub — implemented in Wave 1 (vault/parser.py)")


def test_content_hash_dedup():
    pytest.skip("stub — implemented in Wave 1 (vault/parser.py)")


def test_resolved_links_stripped_from_user_frontmatter():
    pytest.skip("stub — implemented in Wave 1 (vault/parser.py)")


def test_wikilink_extraction():
    pytest.skip("stub — implemented in Wave 1 (vault/parser.py)")


def test_timeline_append_only_accepts_extension():
    pytest.skip("stub — implemented in Wave 1 (vault/parser.py)")


def test_timeline_append_only_rejects_edit():
    pytest.skip("stub — implemented in Wave 1 (vault/parser.py)")
```

**`server/app/tests/vault/test_pages_service.py`** (VAULT-04, VAULT-06, VAULT-08):
```python
"""Page service integration tests — VAULT-04, VAULT-06, VAULT-08.

Stubs: implemented when services/pages.py lands in Wave 2.
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.vault, pytest.mark.integration]


def test_timeline_append_only():
    pytest.skip("stub — implemented in Wave 2 (services/pages.py)")


def test_note_type_defaults_to_fleeting():
    pytest.skip("stub — implemented in Wave 2 (services/pages.py)")


def test_versioning_inserts_page_version_on_update():
    pytest.skip("stub — implemented in Wave 2 (services/pages.py)")


def test_soft_delete_sets_deleted_at_and_deleted_by():
    pytest.skip("stub — implemented in Wave 2 (services/pages.py)")


def test_dedup_skips_reindex_when_hash_unchanged():
    pytest.skip("stub — implemented in Wave 2 (services/pages.py)")


def test_write_page_creates_index_event():
    pytest.skip("stub — implemented in Wave 2 (services/pages.py)")
```

**`server/app/tests/vault/test_wikilinks.py`** (VAULT-09):
```python
"""Wikilink resolution tests — VAULT-09.

Stubs: implemented when services/pages.py wikilink resolver lands in Wave 2.
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.vault, pytest.mark.integration]


def test_private_namespace_routing():
    pytest.skip("stub — implemented in Wave 2 (services/pages.py resolve_wikilinks)")


def test_shared_namespace_routing():
    pytest.skip("stub — implemented in Wave 2 (services/pages.py resolve_wikilinks)")


def test_shortest_unique_path_alphabetical_tie():
    pytest.skip("stub — implemented in Wave 2 (services/pages.py resolve_wikilinks)")


def test_unresolved_forward_reference_allowed():
    pytest.skip("stub — implemented in Wave 2 (services/pages.py resolve_wikilinks)")


def test_resolved_links_stored_in_frontmatter_jsonb():
    pytest.skip("stub — implemented in Wave 2 (services/pages.py resolve_wikilinks)")


def test_display_alias_parsed():
    pytest.skip("stub — implemented in Wave 2 (services/pages.py resolve_wikilinks)")
```

**`server/app/tests/vault/test_rls_pages.py`** (VAULT-02):
```python
"""RLS isolation tests for pages — VAULT-02.

Stubs: implemented in Wave 2 alongside services/pages.py.
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.vault, pytest.mark.integration]


def test_user_a_cannot_read_user_b_pages():
    pytest.skip("stub — implemented in Wave 2 (VAULT-02 RLS isolation)")


def test_guc_not_leaked_after_page_request():
    pytest.skip("stub — implemented in Wave 2 (VAULT-02 RLS isolation)")
```

**`server/app/tests/vault/test_shared_vault.py`** (VAULT-03):
```python
"""Shared vault policy tests — VAULT-03.

Stubs: implemented in Wave 2 alongside services/pages.py.
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.vault, pytest.mark.integration]


def test_any_user_can_read_shared_vault():
    pytest.skip("stub — implemented in Wave 2 (VAULT-03 shared vault)")


def test_admin_only_write_policy_blocks_non_admin():
    pytest.skip("stub — implemented in Wave 2 (VAULT-03 shared vault)")
```

**`server/app/tests/vault/test_watcher.py`** (IDX-01, IDX-02, IDX-03):
```python
"""Watchdog tests — IDX-01, IDX-02, IDX-03.

Stubs: implemented when vault/watcher.py real impl lands in Wave 3.
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.vault, pytest.mark.integration]


def test_file_detection_latency():
    pytest.skip("stub — implemented in Wave 3 (vault/watcher.py)")


def test_handoff_api_uses_run_coroutine_threadsafe():
    pytest.skip("stub — implemented in Wave 3 (vault/watcher.py)")


def test_hash_dedup_skips_unchanged_file():
    pytest.skip("stub — implemented in Wave 3 (vault/watcher.py)")


def test_debounce_coalesces_rapid_events():
    pytest.skip("stub — implemented in Wave 3 (vault/watcher.py)")


def test_on_deleted_triggers_soft_delete():
    pytest.skip("stub — implemented in Wave 3 (vault/watcher.py)")
```

**`server/app/tests/vault/test_reconcile.py`** (IDX-04):
```python
"""Reconciliation job tests — IDX-04.

Stubs: implemented when scheduler/jobs/reconcile_vault.py lands in Wave 3.
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.vault, pytest.mark.integration]


def test_reconcile_picks_up_new_file():
    pytest.skip("stub — implemented in Wave 3 (scheduler/jobs/reconcile_vault.py)")


def test_reconcile_soft_deletes_missing_file():
    pytest.skip("stub — implemented in Wave 3 (scheduler/jobs/reconcile_vault.py)")


def test_reconcile_skips_unchanged_hash():
    pytest.skip("stub — implemented in Wave 3 (scheduler/jobs/reconcile_vault.py)")
```

**`server/app/tests/vault/test_openapi.py`** (VAULT-11):
```python
"""OpenAPI spec freshness tests — VAULT-11.

Stubs: implemented when scripts/regen_openapi.py and pre-commit hook land in Wave 4.
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.vault, pytest.mark.integration]


def test_openapi_json_exists_and_is_valid_json():
    pytest.skip("stub — implemented in Wave 4 (scripts/regen_openapi.py)")


def test_openapi_spec_matches_live_app():
    pytest.skip("stub — implemented in Wave 4 (scripts/regen_openapi.py)")
```
  </action>
  <verify>
    <automated>cd /home/yongxin.Li/Documents/nexora/smart-copilot/server && python -m pytest app/tests/vault/ --collect-only -q 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - All 9 test files exist in `server/app/tests/vault/`
    - `pytest app/tests/vault/ --collect-only -q` exits 0 (no collection errors)
    - `pytest app/tests/vault/ -x -q` exits 0 with all tests SKIPPED (no failures, no errors)
    - No test stub function has fixture parameters in its signature
    - Every stub calls `pytest.skip(...)` as the first statement
    - `pytestmark` is set in every test file
    - `from __future__ import annotations` is present in every file
  </acceptance_criteria>
  <done>All 10 stub test files created, pytest collects them without errors, all stubs SKIP cleanly</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Test fixtures → test DB | _patch_session_factory redirects session_with_rls to testcontainer; no prod DB access |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-01c02-01 | Information Disclosure | conftest seed fixtures | accept | Test-only seeds use placeholder password hashes; no real credentials |
</threat_model>

<verification>
```bash
cd /home/yongxin.Li/Documents/nexora/smart-copilot/server

# Collection check — must exit 0 with no errors
python -m pytest app/tests/vault/ --collect-only -q 2>&1

# Run stubs — all must SKIP, none FAIL
python -m pytest app/tests/vault/ -x -q --no-header 2>&1 | tail -10
```

Expected output: all tests show `s` (skipped), exit 0.
</verification>

<success_criteria>
- `server/app/tests/vault/` package created with `__init__.py` and `conftest.py`
- `conftest.py` has `_patch_session_factory` (autouse, session-scoped), `tmp_vault_dir`, `seed_vault`, `seed_page`, `system_ctx` fixtures
- All 10 test stub files created covering VAULT-01 through VAULT-11 and IDX-01 through IDX-04
- `pytest app/tests/vault/ --collect-only` exits 0
- `pytest app/tests/vault/ -x -q` exits 0, all tests SKIPPED
</success_criteria>

<output>
After completion, create `.planning/phases/01c-vault-watchdog-indexer/01c-02-SUMMARY.md`
</output>
