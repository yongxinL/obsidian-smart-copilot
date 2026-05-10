---
phase: 01c
plan: 08
type: execute
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

must_haves:
  truths:
    - "reconcile_vault.py commits per-vault inside the for-vault loop with try/except wrapping"
    - "server/requirements.txt declares mcp>=1.25,<2 and apscheduler>=3.10,<4"
    - "REQUIREMENTS.md IDX-02 text says run_coroutine_threadsafe, not call_soon_threadsafe"
    - "CLAUDE.md watchdog note says run_coroutine_threadsafe for async coroutine handoff"
  artifacts:
    - path: "server/app/scheduler/jobs/reconcile_vault.py"
      provides: "Per-vault commit inside for-vault loop — CR-01 data-loss bug fixed"
      contains: "await session.commit()"
    - path: "server/requirements.txt"
      provides: "Declared mcp and apscheduler dependencies"
      contains: "mcp>=1.25,<2"
    - path: ".planning/REQUIREMENTS.md"
      provides: "IDX-02 text aligned with D-06 decision"
      contains: "run_coroutine_threadsafe"
    - path: "CLAUDE.md"
      provides: "Watchdog note aligned with D-06 decision"
      contains: "run_coroutine_threadsafe"
  key_links:
    - from: "server/app/scheduler/jobs/reconcile_vault.py"
      to: "session_with_rls commit"
      via: "await session.commit() INSIDE for vault in vaults loop"
      pattern: "session\\.commit"
    - from: "server/requirements.txt"
      to: "mcp, apscheduler packages"
      via: "pip install -r requirements.txt"
      pattern: "mcp>=1\\.25"
---

<objective>
Fix three gaps found by the Phase 01c verifier:

1. **CR-01 (BLOCKER):** `reconcile_vault.py` — move `await session.commit()` inside the `for vault in vaults:` loop with per-vault try/except. Current placement at line 112 (outside the loop) causes all committed work for all vaults to be lost on any unhandled exception.
2. **WR-06 (BLOCKER):** `server/requirements.txt` — add `mcp>=1.25,<2` and `apscheduler>=3.10,<4`. Both packages are used in production code but are undeclared; fresh pip installs fail.
3. **IDX-02 (WARNING):** `REQUIREMENTS.md` and `CLAUDE.md` both say `loop.call_soon_threadsafe()` as the mandatory handoff primitive. D-06 (CONTEXT.md) and the implementation correctly use `asyncio.run_coroutine_threadsafe()`. Update the written documents to match the decision and the implementation.

Purpose: Close all three verification gaps so Phase 01c scores 16/16 must-haves.
Output: Updated reconcile_vault.py (commit placement fix), updated requirements.txt (two new entries), updated REQUIREMENTS.md IDX-02 line, updated CLAUDE.md watchdog note.
</objective>

<context>
@.planning/phases/01c-vault-watchdog-indexer/01c-CONTEXT.md
@.planning/phases/01c-vault-watchdog-indexer/01c-VERIFICATION-DRAFT.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix reconcile_vault.py commit placement (CR-01)</name>
  <read_first>
    - server/app/scheduler/jobs/reconcile_vault.py (FULL FILE — must read current state before editing; the bug is at line 112)
  </read_first>
  <files>server/app/scheduler/jobs/reconcile_vault.py</files>
  <action>
The current file has `await session.commit()` at line 112, OUTSIDE the `for vault in vaults:` loop (which runs lines 41–110). This means any unhandled exception during DB queries (e.g., the `select(Page...)` at lines 66–73) causes a rollback that discards ALL work for ALL vaults processed in that run.

**Correct structure:** move the commit INSIDE the loop, at the end of each vault's processing block, and wrap the entire per-vault block in try/except so one failing vault doesn't skip commits for others.

**Exact change:** The `for vault in vaults:` block currently contains sections 2–5 and the `await session.commit()` is after the loop ends. Restructure so:

```python
        for vault in vaults:
            try:
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
                        log.warning(
                            "slug_sanitized",
                            original=md_file.name,
                            slug=slug,
                            vault_id=str(vault.id),
                        )
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
                            session,
                            ctx,
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
                                session,
                                ctx,
                                page_id=page_id,
                                reason="reconciler_file_missing",
                            )
                            log.info("page_soft_deleted", slug=slug, vault_id=str(vault.id))
                        except Exception as exc:  # noqa: BLE001
                            log.error(
                                "reconcile_soft_delete_failed", slug=slug, error=str(exc)
                            )

                await session.commit()  # per-vault commit INSIDE loop
            except Exception as exc:  # noqa: BLE001
                log.error("reconcile_vault_failed", vault_id=str(vault.id), error=str(exc))
                await session.rollback()
```

The final `log.info("reconcile_vault_complete")` stays after the `async for session` block (outside it, below).

**Write the complete updated file** with this structure. Do not leave any `await session.commit()` outside the `for vault in vaults:` loop.
  </action>
  <verify>
    <automated>cd /home/yongxin.Li/Documents/nexora/smart-copilot/server && python -c "
import ast, sys
src = open('app/scheduler/jobs/reconcile_vault.py').read()
tree = ast.parse(src)
# Verify syntax
print('syntax OK')
# Check that session.commit appears at least once
assert 'session.commit' in src, 'session.commit missing'
# Check that session.rollback appears (per-vault error handling)
assert 'session.rollback' in src, 'session.rollback missing — per-vault error handler not present'
print('commit and rollback both present')
# Import check
sys.path.insert(0, '.')
# Just do a compile check
compile(src, 'reconcile_vault.py', 'exec')
print('compile OK')
"
</automated>
  </verify>
  <acceptance_criteria>
    - `server/app/scheduler/jobs/reconcile_vault.py` passes `python -c "compile(open(...).read(), '', 'exec')"`
    - File contains `await session.commit()` (present)
    - File contains `await session.rollback()` (per-vault exception handler)
    - File contains `log.error("reconcile_vault_failed"` (the outer except log call)
    - grep confirms `session.commit` appears inside the `for vault in vaults:` indentation block — verify by checking that `session.rollback` also exists (it only exists if the try/except wraps the per-vault block, and commit is inside the try)
    - File does NOT have `await session.commit()` as the last statement before `log.info("reconcile_vault_complete")` (i.e., the commit is no longer at the outermost level after the for loop)
  </acceptance_criteria>
  <done>reconcile_vault.py restructured so session.commit() fires per-vault inside the loop; session.rollback() on per-vault exception; CR-01 data-loss bug eliminated</done>
</task>

<task type="auto">
  <name>Task 2: Add mcp and apscheduler to requirements.txt (WR-06)</name>
  <read_first>
    - server/requirements.txt (FULL FILE — must read current state; currently 18 lines, missing mcp and apscheduler)
  </read_first>
  <files>server/requirements.txt</files>
  <action>
Current `server/requirements.txt` is missing two packages used in production:
- `mcp` — imported by `server/app/mcp/server.py`; CLAUDE.md mandates `mcp>=1.25,<2`
- `apscheduler` — imported by `server/app/scheduler/run.py`; CLAUDE.md mandates APScheduler 3.x stable

Add both lines to the file. Place them in a logical grouping. The file currently ends with `markdown-it-py>=3.0`. Append after `markdown-it-py>=3.0`:

```
mcp>=1.25,<2
apscheduler>=3.10,<4
```

**Exact version constraints (non-negotiable — from CLAUDE.md):**
- `mcp>=1.25,<2` — per CLAUDE.md: "mcp | >= 1.25, < 2 | ... CVE-2025-66416 fixed in >= 1.23"
- `apscheduler>=3.10,<4` — per CLAUDE.md: "APScheduler | 3.x (3.11.2) | ... 4.x is still alpha"

Write the complete updated requirements.txt preserving all existing lines exactly (including the comment on line 12 about python-jose CVE).
  </action>
  <verify>
    <automated>cd /home/yongxin.Li/Documents/nexora/smart-copilot/server && python -c "
content = open('requirements.txt').read()
assert 'mcp>=1.25,<2' in content, 'mcp line missing'
assert 'apscheduler>=3.10,<4' in content, 'apscheduler line missing'
# Verify existing lines still present
assert 'fastapi>=0.111' in content
assert 'watchdog>=4.0' in content
assert 'markdown-it-py>=3.0' in content
print('requirements.txt OK — mcp and apscheduler present, existing lines preserved')
"
</automated>
  </verify>
  <acceptance_criteria>
    - `server/requirements.txt` contains exactly `mcp>=1.25,<2` (not `mcp` alone, not `mcp>=1.25`)
    - `server/requirements.txt` contains exactly `apscheduler>=3.10,<4`
    - All 18 original lines remain unchanged (fastapi, uvicorn, pydantic, etc.)
    - The python-jose comment line is preserved verbatim
    - `grep -c 'mcp>=1.25,<2' server/requirements.txt` outputs `1`
    - `grep -c 'apscheduler>=3.10,<4' server/requirements.txt` outputs `1`
  </acceptance_criteria>
  <done>server/requirements.txt declares mcp>=1.25,<2 and apscheduler>=3.10,<4; fresh pip install -r requirements.txt will succeed for MCP and APScheduler processes</done>
</task>

<task type="auto">
  <name>Task 3: Align IDX-02 text in REQUIREMENTS.md and CLAUDE.md with D-06 decision</name>
  <read_first>
    - .planning/REQUIREMENTS.md (lines 50–56 — IDX-02 entry at line 53; read the section to confirm exact current text)
    - CLAUDE.md (lines 145–155 — watchdog section; line 150 contains the stale call_soon_threadsafe note)
    - .planning/phases/01c-vault-watchdog-indexer/01c-CONTEXT.md (D-06 entry — confirms run_coroutine_threadsafe is the locked decision)
  </read_first>
  <files>.planning/REQUIREMENTS.md, CLAUDE.md</files>
  <action>
**Context:** D-06 in CONTEXT.md locked `asyncio.run_coroutine_threadsafe(coro, loop)` as the canonical watchdog→asyncio handoff. The implementation uses it. But two written documents still say `loop.call_soon_threadsafe()`, creating a false conflict. Fix the written documents.

**Change 1 — `.planning/REQUIREMENTS.md` line 53:**

Current text:
```
- [ ] **IDX-02**: Watchdog runs as a separate supervisord process; thread→asyncio handoff via `loop.call_soon_threadsafe()` only
```

Replace with:
```
- [ ] **IDX-02**: Watchdog runs as a separate supervisord process; thread→asyncio handoff via `asyncio.run_coroutine_threadsafe(coro, loop)` for async coroutine dispatch (D-06)
```

**Change 2 — `CLAUDE.md` line 150:**

Current text (in the `## File Watching: watchdog` section):
```
- `loop.call_soon_threadsafe()` is the ONLY safe bridge from the watchdog thread to asyncio
```

Replace with:
```
- `asyncio.run_coroutine_threadsafe(coro, loop)` is the correct primitive for dispatching async coroutines from the watchdog thread to the asyncio event loop (D-06); `loop.call_soon_threadsafe()` is for synchronous callbacks only
```

**Do not change any other lines** in either file. Make surgical edits only. The CLAUDE.md file is large (300+ lines); use Edit to change only line 150.

**Verify test is still correct:** `server/app/tests/vault/test_watcher.py` has a test named `test_handoff_api_uses_run_coroutine_threadsafe` that validates the D-06 decision. This test is CORRECT and must NOT be changed — it already validates the right behavior.
  </action>
  <verify>
    <automated>cd /home/yongxin.Li/Documents/nexora/smart-copilot && python -c "
req = open('.planning/REQUIREMENTS.md').read()
assert 'run_coroutine_threadsafe' in req, 'REQUIREMENTS.md IDX-02 not updated'
assert 'call_soon_threadsafe() only' not in req, 'Old IDX-02 text still present'
print('REQUIREMENTS.md IDX-02 updated OK')

claude = open('CLAUDE.md').read()
assert 'run_coroutine_threadsafe(coro, loop)' in claude, 'CLAUDE.md watchdog note not updated'
print('CLAUDE.md watchdog note updated OK')
"
</automated>
  </verify>
  <acceptance_criteria>
    - `.planning/REQUIREMENTS.md` IDX-02 line contains `run_coroutine_threadsafe` (not `call_soon_threadsafe() only`)
    - `.planning/REQUIREMENTS.md` IDX-02 line contains `(D-06)` reference
    - `CLAUDE.md` watchdog section line contains `run_coroutine_threadsafe(coro, loop)`
    - `CLAUDE.md` watchdog section line explains that `call_soon_threadsafe` is for synchronous callbacks only
    - No other lines in either file are changed (all surrounding text identical to before)
    - `grep -c 'call_soon_threadsafe() only' .planning/REQUIREMENTS.md` outputs `0`
    - `grep -c 'run_coroutine_threadsafe' .planning/REQUIREMENTS.md` outputs at least `1`
    - `grep -c 'run_coroutine_threadsafe' CLAUDE.md` outputs at least `1`
  </acceptance_criteria>
  <done>REQUIREMENTS.md IDX-02 and CLAUDE.md watchdog note both say run_coroutine_threadsafe; no conflict between written spec and D-06 decision; test_watcher.py unchanged and still validates correct behavior</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Filesystem → reconcile_vault loop | Unchanged — reconciler reads .md files from vault paths registered in DB |
| requirements.txt → pip install | Trusted — adds missing declared deps; no new attack surface |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-01c08-01 | Tampering | reconcile_vault per-vault rollback | accept | Per-vault rollback on exception prevents partial state; normal behavior, not a threat |
| T-01c08-02 | Denial of Service | mcp/apscheduler added to requirements | accept | Adding declared deps to requirements.txt has no security impact; packages were already imported |
</threat_model>

<verification>
```bash
cd /home/yongxin.Li/Documents/nexora/smart-copilot

# GAP 1: commit inside loop
python -c "
src = open('server/app/scheduler/jobs/reconcile_vault.py').read()
assert 'session.rollback' in src, 'FAIL: session.rollback missing'
assert 'session.commit' in src, 'FAIL: session.commit missing'
print('GAP 1 OK: commit + rollback present')
"

# GAP 2: requirements.txt
python -c "
r = open('server/requirements.txt').read()
assert 'mcp>=1.25,<2' in r, 'FAIL: mcp missing'
assert 'apscheduler>=3.10,<4' in r, 'FAIL: apscheduler missing'
print('GAP 2 OK: mcp and apscheduler declared')
"

# GAP 3: written docs updated
python -c "
req = open('.planning/REQUIREMENTS.md').read()
assert 'run_coroutine_threadsafe' in req and 'call_soon_threadsafe() only' not in req
claude = open('CLAUDE.md').read()
assert 'run_coroutine_threadsafe(coro, loop)' in claude
print('GAP 3 OK: IDX-02 text and CLAUDE.md note updated')
"
```
</verification>

<success_criteria>
- `reconcile_vault.py` has `await session.commit()` inside the `for vault in vaults:` loop (CR-01 fixed)
- `reconcile_vault.py` has `await session.rollback()` in the per-vault except block
- `server/requirements.txt` contains `mcp>=1.25,<2` and `apscheduler>=3.10,<4` (WR-06 fixed)
- `REQUIREMENTS.md` IDX-02 says `run_coroutine_threadsafe` with `(D-06)` reference (IDX-02 conflict resolved)
- `CLAUDE.md` watchdog note says `run_coroutine_threadsafe(coro, loop)` for async coroutine dispatch
- Phase 01c verifier re-run scores 16/16 must-haves
</success_criteria>

<output>
After completion, create `.planning/phases/01c-vault-watchdog-indexer/01c-08-SUMMARY.md`
</output>
