---
phase: 01c
plan: 06
type: execute
wave: 3
depends_on:
  - "01c-04"
files_modified:
  - server/app/scheduler/jobs/reconcile_vault.py
  - server/app/scheduler/run.py
  - server/app/tests/vault/test_reconcile.py
autonomous: true
requirements:
  - IDX-04

must_haves:
  truths:
    - "reconcile_vault APScheduler job registered with id='reconcile_vault', interval=5 minutes, coalesce=True, max_instances=1"
    - "reconcile_vault scans vault filesystem and compares content_hash vs DB pages"
    - "reconcile_vault calls upsert_page for changed/missing pages (enforce_timeline=False)"
    - "reconcile_vault calls soft_delete_page for DB pages with no corresponding filesystem file"
    - "reconcile_vault uses system_operation_context and session_with_rls"
    - "scheduler/run.py logs both jobs at startup"
    - "test_reconcile.py tests pass (not SKIP)"
  artifacts:
    - path: "server/app/scheduler/jobs/reconcile_vault.py"
      provides: "reconcile_vault() async function for IDX-04 drift correction"
      contains: "async def reconcile_vault"
    - path: "server/app/scheduler/run.py"
      provides: "APScheduler startup with both prune_login_attempts and reconcile_vault jobs"
      contains: "reconcile_vault"
    - path: "server/app/tests/vault/test_reconcile.py"
      provides: "Integration tests for IDX-04"
  key_links:
    - from: "server/app/scheduler/jobs/reconcile_vault.py"
      to: "server/app/scheduler/jobs/prune_login_attempts.py"
      via: "Exact same module structure: system_operation_context + session_with_rls + await session.commit()"
      pattern: "system_operation_context"
    - from: "server/app/scheduler/run.py"
      to: "server/app/scheduler/jobs/reconcile_vault.py"
      via: "scheduler.add_job(reconcile_vault, 'interval', minutes=5, id='reconcile_vault', replace_existing=True, coalesce=True, max_instances=1)"
      pattern: "reconcile_vault"
---

<objective>
Implement the IDX-04 reconciliation APScheduler job and wire it into `scheduler/run.py`. Then replace the test_reconcile.py stubs with real integration tests.

This plan runs in parallel with Plan 05 (watcher.py) — no file overlap. Both depend on Plan 04 (pages service) but are otherwise independent.

Purpose: The reconciler ensures filesystem ↔ database drift is corrected even if the watchdog misses events (process restart, Docker restart, manual vault edits when watchdog was not running).

Output: `scheduler/jobs/reconcile_vault.py`, updated `scheduler/run.py`, and `test_reconcile.py` with passing tests.
</objective>

<context>
@.planning/phases/01c-vault-watchdog-indexer/01c-CONTEXT.md
@.planning/phases/01c-vault-watchdog-indexer/01c-RESEARCH.md

<interfaces>
<!-- From server/app/scheduler/jobs/prune_login_attempts.py — exact analog to replicate -->
```python
"""...(module docstring)..."""
from __future__ import annotations
from sqlalchemy import text
from app.auth.context import system_operation_context
from app.dependencies import session_with_rls
from app.settings import settings

async def prune_login_attempts() -> int:
    ctx = system_operation_context(request_id="prune_login_attempts", client_name="scheduler")
    deleted = 0
    async for session in session_with_rls(ctx):
        result = await session.execute(text("DELETE FROM login_attempts WHERE ..."), {...})
        deleted = result.rowcount or 0
        await session.commit()
    return deleted
```

<!-- From server/app/scheduler/run.py — the extension pattern -->
```python
# Add import alongside existing:
from app.scheduler.jobs.reconcile_vault import reconcile_vault

# Add alongside existing add_job call:
scheduler.add_job(
    reconcile_vault,
    "interval",
    minutes=5,
    id="reconcile_vault",
    replace_existing=True,
    coalesce=True,        # D-08
    max_instances=1,      # D-08
)

# Update log.info:
log.info("scheduler started", jobs=["prune_login_attempts (hourly)", "reconcile_vault (5-min)"])
```

<!-- From server/app/services/pages.py (Plan 04 output) — called by reconcile_vault -->
```python
from app.services.pages import upsert_page, soft_delete_page, read_page, PageNotFound, write_page
from app.vault.parser import parse_vault_file
from app.vault.paths import sanitize_filename_to_slug
```

<!-- D-08: reconciliation job constraints -->
# - Interval: 5 minutes
# - id: "reconcile_vault"
# - replace_existing=True (idempotent on scheduler restart)
# - coalesce=True (D-08: prevent pile-up after outage)
# - max_instances=1 (D-08: one run at a time)
# - Uses system_operation_context (remote=False, role="admin")
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement reconcile_vault.py and extend scheduler/run.py</name>
  <read_first>
    - server/app/scheduler/jobs/prune_login_attempts.py (full file — exact module structure to replicate)
    - server/app/scheduler/run.py (full file — extension points: import, add_job, log.info)
    - server/app/services/pages.py (upsert_page, soft_delete_page signatures — Plan 04 output)
    - server/app/vault/parser.py (parse_vault_file — Plan 03 output)
    - server/app/vault/paths.py (sanitize_filename_to_slug — Plan 03 output)
    - server/app/models/page.py (Page.slug, Page.content_hash, Page.deleted_at fields)
    - server/app/models/vault.py (Vault.path field — needed to enumerate vault filesystem)
    - .planning/phases/01c-vault-watchdog-indexer/
    - .planning/phases/01c-vault-watchdog-indexer/01c-CONTEXT.md (D-08: 5-min interval, coalesce, max_instances; lightweight pass only)
  </read_first>
  <files>server/app/scheduler/jobs/reconcile_vault.py, server/app/scheduler/run.py</files>
  <behavior>
    - reconcile_vault(): walks vault filesystem at VAULT_ROOT (default /vaults or from settings), compares slug→content_hash vs DB pages
    - Files on disk with no DB page → call upsert_page with enforce_timeline=False
    - Files on disk with changed content_hash vs DB → call upsert_page with enforce_timeline=False
    - DB pages (not soft-deleted) with no corresponding file on disk → call soft_delete_page with reason="reconciler_file_missing"
    - Files on disk whose name produces an invalid slug → sanitize via sanitize_filename_to_slug, log warning
    - reconcile_vault registered with id="reconcile_vault", minutes=5, replace_existing=True, coalesce=True, max_instances=1
    - scheduler/run.py logs both jobs at startup
  </behavior>
  <action>
**CRITICAL RULES:**
- Module-level function ONLY (no closures, no lambdas) — APScheduler 3.x SQLAlchemyJobStore pickles job args.
- `system_operation_context(request_id="reconcile_vault", client_name="scheduler")` — names match job ID.
- `async for session in session_with_rls(ctx):` — canonical non-FastAPI session pattern.
- `await session.commit()` at the end (not flush).
- D-08: `coalesce=True, max_instances=1` — prevent pile-up and parallel execution.
- Lightweight reconciliation: walk filesystem, compute xxhash64, compare to DB. Deep reconciliation reserved for Phase 1d CLI.
- VAULT_ROOT: use a hardcoded default of `/vaults` or read from `os.environ.get("SMARTCOPILOT_VAULT_ROOT", "/vaults")` — avoid adding a new settings field now.

**1. Create `server/app/scheduler/jobs/reconcile_vault.py`:**

```python
"""IDX-04: Lightweight vault reconciliation job (D-08).

Runs every 5 minutes via APScheduler. Detects filesystem ↔ DB drift:
  - Files on disk with no DB page → upsert
  - Files on disk with changed content_hash → re-index
  - DB pages (active) with no corresponding file → soft-delete

CLAUDE.md: module-level function, no closures — APScheduler pickles job args.
D-08: coalesce=True, max_instances=1 — one run at a time.
"""
from __future__ import annotations

import os
from pathlib import Path

import structlog
import xxhash
from sqlalchemy import select

from app.auth.context import system_operation_context
from app.db_session import session_with_rls
from app.models.page import Page
from app.models.vault import Vault
from app.services.pages import soft_delete_page, upsert_page
from app.vault.parser import parse_vault_file
from app.vault.paths import sanitize_filename_to_slug

log = structlog.get_logger("smart_copilot.reconciler")

_VAULT_ROOT = Path(os.environ.get("SMARTCOPILOT_VAULT_ROOT", "/vaults"))


async def reconcile_vault() -> None:
    """Lightweight reconciliation: compare mtime + content_hash vs DB pages."""
    ctx = system_operation_context(request_id="reconcile_vault", client_name="scheduler")
    async for session in session_with_rls(ctx):
        # 1. Load all active vaults from DB
        vaults_result = await session.execute(select(Vault))
        vaults = vaults_result.scalars().all()

        for vault in vaults:
            vault_path = Path(vault.path)
            if not vault_path.exists():
                log.warning("vault_path_missing", vault_id=str(vault.id), path=str(vault_path))
                continue

            # 2. Build disk inventory: slug -> (content_hash, full_path)
            disk_slugs: dict[str, tuple[str, Path]] = {}
            for md_file in vault_path.rglob("*.md"):
                try:
                    raw = md_file.read_bytes()
                except OSError:
                    continue
                slug = sanitize_filename_to_slug(md_file.name)
                if slug != md_file.stem:
                    log.warning("slug_sanitized", original=md_file.name, slug=slug, vault_id=str(vault.id))
                content_hash = xxhash.xxh64(raw).hexdigest()
                disk_slugs[slug] = (content_hash, md_file)

            # 3. Load DB inventory for this vault: slug -> (content_hash, page_id)
            pages_result = await session.execute(
                select(Page.id, Page.slug, Page.content_hash).where(
                    Page.vault_id == vault.id,
                    Page.deleted_at.is_(None),
                )
            )
            db_slugs: dict[str, tuple[str, object]] = {
                row.slug: (row.content_hash, row.id) for row in pages_result
            }

            # 4. Reconcile: files on disk not in DB OR hash changed
            for slug, (disk_hash, md_path) in disk_slugs.items():
                db_hash, _ = db_slugs.get(slug, (None, None))
                if db_hash == disk_hash:
                    continue  # IDX-03: skip unchanged
                try:
                    raw = md_path.read_bytes()
                    parsed = parse_vault_file(raw)
                    await upsert_page(
                        session, ctx,
                        vault_id=vault.id,
                        slug=slug,
                        parsed=parsed,
                        enforce_timeline=False,  # D-03: reconciler is like watchdog
                    )
                    log.info("page_reconciled", slug=slug, vault_id=str(vault.id))
                except Exception as exc:  # noqa: BLE001
                    log.error("reconcile_upsert_failed", slug=slug, error=str(exc))

            # 5. Reconcile: DB pages with no corresponding disk file
            for slug, (_, page_id) in db_slugs.items():
                if slug not in disk_slugs:
                    try:
                        await soft_delete_page(
                            session, ctx,
                            page_id=page_id,
                            reason="reconciler_file_missing",
                        )
                        log.info("page_soft_deleted", slug=slug, vault_id=str(vault.id))
                    except Exception as exc:  # noqa: BLE001
                        log.error("reconcile_soft_delete_failed", slug=slug, error=str(exc))

        await session.commit()
    log.info("reconcile_vault_complete")
```

**2. Extend `server/app/scheduler/run.py`:**

Add the reconcile_vault import alongside the existing prune_login_attempts import:
```python
from app.scheduler.jobs.reconcile_vault import reconcile_vault
```

Add the reconcile_vault job registration after the existing prune_login_attempts job:
```python
scheduler.add_job(
    reconcile_vault,
    "interval",
    minutes=5,
    id="reconcile_vault",
    replace_existing=True,
    coalesce=True,     # D-08: prevent pile-up after outage
    max_instances=1,   # D-08: only one reconciliation at a time
)
```

Update the log.info line to include both jobs:
```python
log.info("scheduler started", jobs=["prune_login_attempts (hourly)", "reconcile_vault (5-min)"])
```
  </action>
  <verify>
    <automated>cd /home/yongxin.Li/Documents/nexora/smart-copilot/server && python -c "
import py_compile
py_compile.compile('app/scheduler/jobs/reconcile_vault.py', doraise=True)
py_compile.compile('app/scheduler/run.py', doraise=True)
print('syntax OK')
# Import check
from app.scheduler.jobs.reconcile_vault import reconcile_vault
print('import OK')
# Verify run.py has both jobs
src = open('app/scheduler/run.py').read()
assert 'reconcile_vault' in src
assert 'coalesce=True' in src
print('scheduler/run.py has reconcile_vault job registered')
"</automated>
  </verify>
  <acceptance_criteria>
    - `server/app/scheduler/jobs/reconcile_vault.py` exists and passes py_compile
    - `from app.scheduler.jobs.reconcile_vault import reconcile_vault` succeeds
    - `reconcile_vault.py` contains `system_operation_context(request_id="reconcile_vault"`
    - `reconcile_vault.py` contains `enforce_timeline=False` in upsert_page call
    - `reconcile_vault.py` contains `reason="reconciler_file_missing"` in soft_delete_page call
    - `reconcile_vault.py` does NOT contain any FastAPI imports
    - `scheduler/run.py` contains `from app.scheduler.jobs.reconcile_vault import reconcile_vault`
    - `scheduler/run.py` contains `id="reconcile_vault"` in add_job call
    - `scheduler/run.py` contains `coalesce=True` and `max_instances=1` in the reconcile_vault add_job call
    - `scheduler/run.py` log.info lists both jobs
  </acceptance_criteria>
  <done>reconcile_vault.py implemented; scheduler/run.py extended with 5-min reconciliation job; both pass syntax checks</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Replace test_reconcile.py stubs with real integration tests</name>
  <read_first>
    - server/app/tests/vault/test_reconcile.py (current stubs to replace)
    - server/app/tests/vault/conftest.py (tmp_vault_dir, seed_vault, seed_page fixtures)
    - server/app/scheduler/jobs/reconcile_vault.py (just created — reconcile_vault signature and behavior)
    - server/app/tests/auth/test_scheduler_prune.py (full file — seed helper + count helper + async test pattern for scheduler jobs)
    - .planning/phases/01c-vault-watchdog-indexer/01c-RESEARCH.md (Scheduler job test pattern section)
  </read_first>
  <files>server/app/tests/vault/test_reconcile.py</files>
  <behavior>
    - test_reconcile_picks_up_new_file: write .md file to tmp vault dir (seed_vault path), call reconcile_vault(), assert page row created in DB with correct slug and content_hash
    - test_reconcile_soft_deletes_missing_file: seed a page in DB (seed_page), do NOT write corresponding file to disk, call reconcile_vault(), assert page.deleted_at is not None
    - test_reconcile_skips_unchanged_hash: write file, reconcile (creates page), reconcile again (same file), assert page_versions count is still 1 (no second upsert when hash unchanged)
  </behavior>
  <action>
**Implementation notes:**

These are integration tests that call `reconcile_vault()` directly (not via APScheduler scheduler). `reconcile_vault()` is an `async def`, so tests must be `async def test_*()`.

The `_VAULT_ROOT` in reconcile_vault.py is hardcoded to `/vaults`. For tests, we need the reconciler to watch `tmp_vault_dir`. Options:
1. Monkeypatch `app.scheduler.jobs.reconcile_vault._VAULT_ROOT` to `tmp_vault_dir`
2. OR: seed the vault DB row with `path = str(tmp_vault_dir)` and rely on the vault DB walk

**Use option 2**: seed the vault row with `path = str(tmp_vault_dir)` in conftest. The `seed_vault` fixture already inserts a vault row with a path. Use `monkeypatch` to set the vault path, or better: create a fresh test vault row whose `path` is `tmp_vault_dir`.

**Test structure** (copy from `test_scheduler_prune.py` pattern):

```python
from __future__ import annotations
import uuid
import pytest
import pytest_asyncio
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.scheduler.jobs.reconcile_vault import reconcile_vault

pytestmark = [pytest.mark.vault, pytest.mark.integration]

async def _seed_vault_with_path(engine: AsyncEngine, user_id: uuid.UUID, path: str) -> uuid.UUID:
    """Seed a vault row with a specific filesystem path for testing."""
    vid = uuid.uuid4()
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        await session.execute(
            text("INSERT INTO vaults (id, owner_user_id, kind, path, created_at, updated_at) VALUES (:id, :uid, 'private', :path, now(), now())"),
            {"id": vid, "uid": user_id, "path": path},
        )
        await session.commit()
    return vid

async def _count_page_versions(engine: AsyncEngine, page_id: uuid.UUID) -> int:
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        result = await session.execute(
            text("SELECT COUNT(*) FROM page_versions WHERE page_id = :id"), {"id": page_id}
        )
        return result.scalar_one()
```

Write all three tests. For `test_reconcile_picks_up_new_file`:
1. Seed user and vault with path=str(tmp_vault_dir)
2. Write `tmp_vault_dir / "my-note.md"` with content `b"---\ntype: note\n---\nContent\n"`
3. Call `await reconcile_vault()`
4. Query DB: `SELECT id FROM pages WHERE slug = 'my-note' AND vault_id = :vid` — assert row exists

For `test_reconcile_soft_deletes_missing_file`:
1. Seed user and vault with path=str(tmp_vault_dir)
2. Insert a page row in DB for that vault (slug="orphan-page"), but do NOT write the file to disk
3. Call `await reconcile_vault()`
4. Query DB: `SELECT deleted_at FROM pages WHERE slug = 'orphan-page'` — assert deleted_at is not None

For `test_reconcile_skips_unchanged_hash`:
1. Seed user and vault, write a file, call reconcile_vault() (creates page, inserts version 1)
2. Call reconcile_vault() again without changing the file
3. Assert page_versions count is still 1
  </action>
  <verify>
    <automated>cd /home/yongxin.Li/Documents/nexora/smart-copilot/server && python -m pytest app/tests/vault/test_reconcile.py -x -q --no-header 2>&1 | tail -8</automated>
  </verify>
  <acceptance_criteria>
    - `pytest app/tests/vault/test_reconcile.py -x -q` exits 0, all 3 tests PASSED (no SKIP)
    - test_reconcile_picks_up_new_file verifies page created in DB
    - test_reconcile_soft_deletes_missing_file verifies deleted_at is set on DB page with no corresponding file
    - test_reconcile_skips_unchanged_hash verifies no second version insert when hash unchanged
    - No `pytest.skip()` calls remain
  </acceptance_criteria>
  <done>test_reconcile.py has 3 real passing integration tests covering IDX-04</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Filesystem walk → reconcile_vault | Reads .md files from vault root; no user input; OS-level trust |
| reconcile_vault → PostgreSQL | session_with_rls(system_ctx) with GUC discipline |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-01c06-01 | Denial of Service | Reconciler running in parallel | mitigate | max_instances=1, coalesce=True (D-08) — APScheduler prevents concurrent execution |
| T-01c06-02 | Tampering | Timeline mutations via reconciler | accept | D-03: reconciler uses enforce_timeline=False — human filesystem edits are trusted |
| T-01c06-03 | Denial of Service | Large vault with many files | accept | Lightweight reconciliation: only hash comparison; deep reconciliation reserved for CLI |
</threat_model>

<verification>
```bash
cd /home/yongxin.Li/Documents/nexora/smart-copilot/server

# Import + syntax
python -c "from app.scheduler.jobs.reconcile_vault import reconcile_vault; print('OK')"

# Verify scheduler has both jobs
python -c "
src = open('app/scheduler/run.py').read()
assert 'reconcile_vault' in src
assert 'coalesce=True' in src  
assert 'max_instances=1' in src
print('scheduler/run.py checks passed')
"

# Integration tests
python -m pytest app/tests/vault/test_reconcile.py -v --no-header
```
</verification>

<success_criteria>
- `scheduler/jobs/reconcile_vault.py` implements 5-minute drift-correction job (IDX-04)
- Job registered with coalesce=True, max_instances=1, id="reconcile_vault" (D-08)
- `scheduler/run.py` logs both jobs on startup
- `pytest app/tests/vault/test_reconcile.py` exits 0, all tests PASSED
- No FastAPI imports in reconcile_vault.py
</success_criteria>

<output>
After completion, create `.planning/phases/01c-vault-watchdog-indexer/01c-06-SUMMARY.md`
</output>
