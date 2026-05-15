# Deferred Items — Phase 01d

## Out-of-Scope Discoveries

### test_shared_vault.py — 3 pre-existing test failures

**Found during:** Full vault test run (all tests pass except these)
**Affected tests:**
- `test_admin_only_write_policy_blocks_non_admin`
- `test_admin_can_write_to_shared_vault`
- `test_any_user_can_read_shared_vault`

**Symptom:** `PageNotFound` raised when reading pages inserted via raw SQL into the shared vault, even with admin credentials. The `read_page()` service correctly filters by `vault_id`, but the pages inserted directly via test factory may be invisible to RLS-filtered reads.

**Root cause:** Not investigated — these tests failed at commit `5363f8e` (before any changes to services/pages.py in this plan). Likely an RLS configuration or test fixture issue in the shared vault setup, not a code bug in the Phase 1d service helpers.

**Files affected:** `server/app/tests/vault/test_shared_vault.py`
**Status:** Out of scope for 01d-01. Requires investigation by Phase 1b or 1c owner.
**Discovery commit:** `28f0244` (SUMMARY.md commit)