---
phase: 01c
reviewed: 2026-05-11T00:00:00Z
depth: standard
files_reviewed: 25
files_reviewed_list:
  - server/alembic/versions/0003_phase_1c_vault.py
  - server/app/models/page.py
  - server/app/models/page_version.py
  - server/app/settings.py
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
  - server/app/vault/parser.py
  - server/app/vault/paths.py
  - server/app/vault/__init__.py
  - server/app/services/pages.py
  - server/app/vault/watcher.py
  - server/app/scheduler/jobs/reconcile_vault.py
  - server/app/scheduler/run.py
  - scripts/regen_openapi.py
  - docs/openapi.json
findings:
  critical: 2
  warning: 4
  info: 4
  total: 10
status: issues_found
---

# Phase 01c: Code Review Report

**Reviewed:** 2026-05-11
**Depth:** standard
**Files Reviewed:** 25
**Status:** issues_found

## Summary

The Phase 1c vault and watchdog indexer implementation is generally well-structured. The compiled-truth/timeline convention, wikilink resolution, path confinement, and RLS enforcement are all correctly implemented. However, two critical bugs were found in the reconciliation job that can cause data inconsistency: a transaction boundary error allowing partial commits, and a race condition where a file deleted between scan and read crashes the reconciler loop. Four warnings and four info-level findings complete the report.

---

## Critical Issues

### CR-01: Per-vault `session.commit()` is outside the try block in `reconcile_vault`

**File:** `server/app/scheduler/jobs/reconcile_vault.py:125`
**Issue:** `await session.commit()` sits outside the inner try-except block but inside the vault loop. When an exception is raised during processing of vault N (e.g., a malformed file), the except block rolls back and the loop `continue`s to vault N+1 — but the `commit()` from vault N-1 has already executed, and the `commit()` for the failed vault N is still reached (not skipped by the except). The result is that a subsequent exception inside the same vault's processing after the first exception is caught, rolled back, but then `commit()` is still called on the now-rolled-back session.

More critically: if `session.commit()` itself raises (e.g., a database connection loss mid-commit), it is not inside the try block and will propagate uncaught, aborting the entire loop. All remaining vaults in the iteration will not be reconciled.

```python
for vault in vaults:
    try:
        # ... ops for vault ...
        await session.commit()  # <-- NOT inside try
    except Exception as exc:
        await session.rollback()  # catches only ops, not the commit itself
```

**Fix:** Move `await session.commit()` inside the try block, so that a database error on commit also triggers rollback and logs the failure before continuing to the next vault:

```python
for vault in vaults:
    try:
        # ... ops for vault ...
        await session.commit()
    except Exception as exc:
        log.error("reconcile_vault_commit_failed", vault_id=str(vault.id), error=str(exc))
        await session.rollback()
```

---

### CR-02: File read race condition — deleted file crashes reconciler loop mid-iteration

**File:** `server/app/scheduler/jobs/reconcile_vault.py:86-103`
**Issue:** The reconciler builds a `disk_slugs` dict by reading file bytes in a first loop (line 58-72), then accesses those same files in a second loop (line 86-103). Between the two loops, a file could be deleted. The `try/except OSError` at lines 59-62 only catches errors in the first loop, not the second. An `OSError` from `md_path.read_bytes()` at line 91 will propagate uncaught through `reconcile_vault`, aborting the entire reconciliation run and leaving remaining vaults and remaining slugs unprocessed.

The watchdog correctly guards against this with `if not file_path.exists(): return` (watcher.py:49-50). The reconciler does not.

**Fix:** Add the same guard inside the second loop:

```python
for slug, (disk_hash, md_path) in disk_slugs.items():
    db_hash, _ = db_slugs.get(slug, (None, None))
    if db_hash == disk_hash:
        continue
    if not md_path.exists():  # guard: file deleted between scan and read
        continue
    try:
        raw = md_path.read_bytes()
        # ...
```

---

## Warnings

### WR-01: `write_page` resolves wikilinks using `user_vault_id` for both namespaces

**File:** `server/app/services/pages.py:265-268`
**Issue:** `write_page` calls `resolve_and_store_wikilinks(session, page, raw_text, user_vault_id=vault_id, shared_vault_id=shared_vault_id)`. When `namespace == "shared"`, `_find_slug_match` searches the `shared_vault_id` (correct). However, `vault_id` is passed as `user_vault_id` regardless of which vault the page lives in. If a page in the shared vault (`kind == "shared"`) has a private-namespace wikilink, the resolution falls back to `user_vault_id` which is also the shared vault — not the caller's private vault. This is ambiguous behavior: the caller's private vault ID is unknown in `write_page`.

The `shared_vault_id` parameter could be the same as `vault_id` when called for a shared vault page, causing private-namespace links to incorrectly resolve within the shared vault instead of the caller's private vault.

**Fix:** Clarify the calling convention: callers of `write_page` must pass `user_vault_id` (their own private vault) and `shared_vault_id` (the shared vault UUID) separately, not reusing `vault_id` for both. Document this in the docstring.

---

### WR-02: `append_timeline` uses unreliable `_body_shape` fallback from user frontmatter

**File:** `server/app/services/pages.py:343`
**Issue:** `body_shape=page.frontmatter.get("_body_shape", "compiled_truth_only")` reads a key from the stored `page.frontmatter` JSONB. This value is never explicitly set by the service — it only exists if it was somehow written to the frontmatter JSONB by prior parsing. The fallback `"compiled_truth_only"` is likely wrong for pages with a non-empty `page.timeline`. This value is not actually used (since `enforce_timeline=False`), but it means the `ParsedPage` object is constructed with an incorrect field.

**Fix:** Derive body shape from the actual page data:

```python
body_shape = (
    "mixed"
    if (page.compiled_truth and page.timeline)
    else ("timeline_only" if page.timeline else "compiled_truth_only")
)
```

---

### WR-03: `soft_delete_vault_file` silently no-ops when vault ID is not set

**File:** `server/app/vault/watcher.py:108-111`
**Issue:** If `SMARTCOPILOT_VAULT_ID` is absent from the environment, the function logs a warning and returns without taking any action. In particular, if a file is deleted but its page still exists in the database, the watchdog silently fails to clean it up. The test covers this path with a `monkeypatch.setenv` call, which masks the production behavior.

**Fix:** Raise or propagate the error instead of silently returning:

```python
vault_id_str = os.environ.get("SMARTCOPILOT_VAULT_ID", "")
if not vault_id_str:
    raise ValueError("SMARTCOPILOT_VAULT_ID environment variable is not set")
```

---

### WR-04: OpenAPI spec test only validates path keys and title — schema drift goes undetected

**File:** `server/app/tests/vault/test_openapi.py:37-61`
**Issue:** `test_openapi_spec_matches_live_app` compares only `set(live_spec["paths"].keys())` and `info.title`. If a parameter type changes, a response schema is modified, or a required field is added/removed, the test still passes. The `scripts/regen_openapi.py` script does regenerate the full spec correctly, but the regression test does not verify it caught drift.

**Fix:** Either expand the comparison to include the full spec JSON (e.g., `json.dumps(live_spec, sort_keys=True) == json.dumps(committed_spec, sort_keys=True)`) or use `TestClient.validate_response()` to validate the spec structure against OpenAPI 3.1 requirements.

---

## Info

### IN-01: Dead `from sqlalchemy import select` import in `watcher.py`

**File:** `server/app/vault/watcher.py:62`
**Issue:** `from sqlalchemy import select` is imported inside the `index_vault_file` function (line 62) and `soft_delete_vault_file` (line 114), but `select` is not actually used in either function — the query uses `Page` model directly with `where(...)` which is ORM-style. This is dead import code.

**Fix:** Remove the local `from sqlalchemy import select` import from both functions.

---

### IN-02: `IndexEvent.user_id` is nullable but set to system user on watchdog/scheduler paths

**File:** `server/app/services/pages.py:183-189`
**Issue:** In `upsert_page`, when called from the watchdog/scheduler with `system_operation_context`, the `IndexEvent.user_id` is set to `SYSTEM_USER_ID` (`00000000-0000-0000-0000-000000000001`). This is technically correct (system operations are tracked), but the `user_id` column on `index_events` is nullable by design (`ForeignKey("users.id", ondelete="CASCADE")` with `nullable=True`). A comment documenting this design intent would help future maintainers.

**Fix:** Add a comment above the `IndexEvent` instantiation: `# user_id=SYSTEM_USER_ID: watchdog/scheduler actions are attributed to the system user.`

---

### IN-03: `system_ctx` fixture in `conftest.py` is session-scoped loop fixture used as function-scoped

**File:** `server/app/tests/vault/conftest.py:137-142`
**Issue:** The `system_ctx` fixture is a plain `@pytest.fixture` (function-scoped) but uses `system_operation_context` (which is a pure function with no state). More importantly, there are no tests that actually use `system_ctx` — all watchdog/scheduler tests call `system_operation_context` directly. The fixture is defined but unused.

**Fix:** Either remove the fixture if unused, or mark it `@pytest.fixture(scope="function")` for clarity (it already is function-scoped by default).

---

### IN-04: Migration downgrade has an inconsistent enum mapping for note_type values

**File:** `server/alembic/versions/0003_phase_1c_vault.py:86-94`
**Issue:** The downgrade maps all six new note_type values (`fleeting`, `literature`, `permanent`, `archived_fleeting`, `skill`, `moc`) to the same old value `'mixed'`. This means a database with `note_type = 'literature'` will downgrade to `'mixed'`, losing the semantic distinction. This is noted as a known limitation in the docstring ("closest old equivalents"), but it means `note_type` data is lossy in the downgrade direction.

**Fix:** No action required if lossy downgrade is acceptable. Add a comment in the downgrade function documenting the data loss: `# Note: note_type downgrade is lossy — all new values map to 'mixed'.`

---

_Reviewed: 2026-05-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_