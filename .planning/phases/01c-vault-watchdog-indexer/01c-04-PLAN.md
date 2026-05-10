---
phase: 01c
plan: 04
type: execute
wave: 2
depends_on:
  - "01c-03"
files_modified:
  - server/app/services/pages.py
  - server/app/tests/vault/test_pages_service.py
  - server/app/tests/vault/test_wikilinks.py
  - server/app/tests/vault/test_rls_pages.py
  - server/app/tests/vault/test_shared_vault.py
autonomous: true
requirements:
  - VAULT-02
  - VAULT-03
  - VAULT-04
  - VAULT-06
  - VAULT-07
  - VAULT-08
  - VAULT-09

must_haves:
  truths:
    - "upsert_page creates a new page with note_type=fleeting by default"
    - "upsert_page skips re-index when content_hash is unchanged (IDX-03)"
    - "upsert_page inserts a page_versions snapshot on every update"
    - "write_page rejects timeline mutations with VaultTimelineError (D-02)"
    - "write_page accepts timeline append (D-02)"
    - "watchdog path (enforce_timeline=False) does NOT reject timeline mutations (D-03)"
    - "soft_delete_page sets deleted_at, deleted_by, delete_reason"
    - "resolve_and_store_wikilinks stores _resolved_links in page.frontmatter JSONB (not links table)"
    - "page service has zero FastAPI imports"
    - "RLS: user A cannot read user B pages via session_with_rls"
    - "shared vault write blocked for non-admin when policy=admin_only"
  artifacts:
    - path: "server/app/services/pages.py"
      provides: "upsert_page, write_page, read_page, soft_delete_page, append_timeline, resolve_and_store_wikilinks; PageNotFound, TimelineViolation, SharedVaultWriteDenied"
      contains: "class TimelineViolation"
    - path: "server/app/tests/vault/test_pages_service.py"
      provides: "Integration tests for VAULT-04, VAULT-06, VAULT-07, VAULT-08"
    - path: "server/app/tests/vault/test_wikilinks.py"
      provides: "Integration tests for VAULT-09 wikilink resolution"
    - path: "server/app/tests/vault/test_rls_pages.py"
      provides: "Integration tests for VAULT-02 RLS isolation"
    - path: "server/app/tests/vault/test_shared_vault.py"
      provides: "Integration tests for VAULT-03 shared vault policy"
  key_links:
    - from: "server/app/services/pages.py"
      to: "server/app/vault/parser.py"
      via: "parse_vault_file, assert_timeline_append_only, extract_wikilinks imported and called on write path"
      pattern: "from app.vault.parser import"
    - from: "server/app/services/pages.py"
      to: "server/app/db_session.py:session_with_rls"
      via: "session_with_rls(ctx) used for all DB writes — per D-20 RLS discipline"
      pattern: "session_with_rls"
    - from: "server/app/services/pages.py"
      to: "server/app/models/page.py"
      via: "Page model upsert — timeline, deleted_by columns added in Plan 01"
      pattern: "from app.models.page import Page"
---

<objective>
Implement the page CRUD service (`services/pages.py`) — the core transport-agnostic layer that writes/reads pages, enforces the compiled-truth/timeline convention, snapshots versions, soft-deletes, and resolves wikilinks. Then replace the four Wave 0 stubs (test_pages_service, test_wikilinks, test_rls_pages, test_shared_vault) with real integration tests.

Purpose: This is the main business-logic hub for Phase 1c. The watchdog (Plan 05) and reconciler (Plan 06) both call functions from this module.

Output: `services/pages.py` and four test files with passing integration tests.
</objective>

<context>
@.planning/phases/01c-vault-watchdog-indexer/01c-CONTEXT.md
@.planning/phases/01c-vault-watchdog-indexer/01c-RESEARCH.md

<interfaces>
<!-- From server/app/services/provider_keys.py — the exact CRUD service pattern to replicate -->
```python
"""...(transport-agnostic)...
CLAUDE.md: no FastAPI imports; services take OperationContext + AsyncSession.
"""
from __future__ import annotations
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.context import OperationContext, SYSTEM_USER_ID

class DomainError(Exception): ...   # one-liner error classes

async def upsert_thing(session: AsyncSession, ctx: OperationContext, *, ...) -> Thing:
    existing = (await session.execute(select(Thing).where(...))).scalar_one_or_none()
    if existing is None:
        thing = Thing(id=uuid.uuid4(), ...)
        session.add(thing)
        await session.flush()
        return thing
    else:
        existing.field = new_value
        await session.flush()
        return existing
```

<!-- From server/app/db_session.py — session_with_rls pattern for non-HTTP callers -->
```python
from app.db_session import session_with_rls
ctx = system_operation_context(request_id="...", client_name="...")
async for session in session_with_rls(ctx):
    # GUCs set automatically; RESET in finally: guaranteed
    await session.execute(...)
    await session.commit()
```

<!-- From server/app/auth/context.py — OperationContext fields -->
```python
@dataclass(frozen=True, slots=True)
class OperationContext:
    user_id: uuid.UUID
    role: Literal["admin", "user"]
    transport: Literal["rest", "mcp_http", "mcp_stdio", "cli", "system"]
    remote: bool
    client_name: str
    request_id: str
    session_id: uuid.UUID | None = None
    mcp_token_id: uuid.UUID | None = None
SYSTEM_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
```

<!-- From server/app/models/page.py (after Plan 01 update) -->
```python
class Page(TimestampMixin, Base):
    __tablename__ = "pages"
    id: Mapped[uuid.UUID]
    vault_id: Mapped[uuid.UUID]           # FK vaults.id CASCADE
    slug: Mapped[str]                     # String(256), unique per vault
    type: Mapped[str]                     # page_type_enum: person/company/concept/...
    note_type: Mapped[str]                # page_note_type_enum: fleeting/literature/...
    frontmatter: Mapped[dict]             # JSONB (includes _resolved_links system key)
    compiled_truth: Mapped[str | None]    # Text (above-the-line)
    timeline: Mapped[str | None]          # Text (below-the-line) — added in Plan 01
    content_hash: Mapped[str]             # String(32) — xxhash64 hexdigest
    enrichment_hash: Mapped[str | None]   # String(32)
    deleted_at: Mapped[object | None]     # DateTime(timezone=True)
    delete_reason: Mapped[str | None]     # Text
    deleted_by: Mapped[uuid.UUID | None]  # UUID FK users.id — added in Plan 01
```

<!-- From server/app/models/page_version.py (after Plan 01 update) -->
```python
class PageVersion(Base):
    __tablename__ = "page_versions"
    id: Mapped[uuid.UUID]
    page_id: Mapped[uuid.UUID]   # FK pages.id CASCADE
    version: Mapped[int]
    frontmatter: Mapped[dict]
    compiled_truth: Mapped[str | None]
    timeline: Mapped[str | None]  # added in Plan 01
    content_hash: Mapped[str]
    created_at: Mapped[object]
```

<!-- From server/app/models/index_event.py -->
```python
class IndexEvent(Base):
    __tablename__ = "index_events"
    id: Mapped[int]          # BigInteger autoincrement
    user_id: Mapped[object | None]   # UUID FK users.id
    event_type: Mapped[str | None]   # index_event_type_enum: created/updated/deleted/re_indexed/error
    page_slug: Mapped[str | None]    # String(256)
    details: Mapped[dict]            # JSONB
    created_at: Mapped[object]       # DateTime
```

<!-- From server/app/vault/parser.py (Plan 03 output) -->
```python
from app.vault.parser import (
    ParsedPage, VaultTimelineError, assert_timeline_append_only, extract_wikilinks,
    parse_vault_file,
)
```

<!-- From server/app/models/vault.py -->
```python
class Vault(TimestampMixin, Base):
    __tablename__ = "vaults"
    id: Mapped[uuid.UUID]
    owner_user_id: Mapped[uuid.UUID | None]  # NULL = system shared vault
    kind: Mapped[str]     # vault_kind_enum: "private" | "shared"
    path: Mapped[str]     # Text, unique
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement services/pages.py</name>
  <read_first>
    - server/app/services/provider_keys.py (full file — exact CRUD service pattern: imports, error classes, upsert pattern, flush discipline)
    - server/app/services/users.py (lines 1-25 — error class style, service function signatures)
    - server/app/models/page.py (full file — column names and types for the upsert)
    - server/app/models/page_version.py (full file — PageVersion constructor fields)
    - server/app/models/index_event.py (full file — IndexEvent fields)
    - server/app/vault/parser.py (full file — ParsedPage fields, VaultTimelineError, assert_timeline_append_only, extract_wikilinks)
    - server/app/settings.py (shared_vault_write_policy field added in Plan 01)
    - .planning/phases/01c-vault-watchdog-indexer/01c-RESEARCH.md (Pattern 7: wikilink resolution DB query; Anti-patterns: no FastAPI imports)
    - .planning/phases/01c-vault-watchdog-indexer/01c-CONTEXT.md (D-02 timeline enforcement, D-03 watchdog bypass, D-04 note_type default, D-09/10/11 wikilink resolution, VAULT-03 shared vault policy)
  </read_first>
  <files>server/app/services/pages.py</files>
  <behavior>
    - upsert_page(session, ctx, vault_id=V, slug="my-note", parsed=P, enforce_timeline=True): new page created with note_type from frontmatter or "fleeting" default (D-04)
    - upsert_page with same content_hash as existing: returns existing page without flush (IDX-03 hash dedup)
    - upsert_page on update: inserts a PageVersion snapshot with page_id, version=N+1, frontmatter, compiled_truth, timeline, content_hash
    - upsert_page with enforce_timeline=True and mutated timeline: raises VaultTimelineError (D-02)
    - upsert_page with enforce_timeline=False (watchdog path): processes timeline mutation without error (D-03)
    - soft_delete_page(session, ctx, page_id=P, reason="file_deleted"): sets deleted_at=now(), deleted_by=ctx.user_id, delete_reason="file_deleted"
    - resolve_and_store_wikilinks(session, page, raw_content): stores _resolved_links list in page.frontmatter JSONB; does NOT write to links table
    - write_page(session, ctx, slug, raw_content, vault_id): calls parse_vault_file + upsert_page + resolve_and_store_wikilinks + IndexEvent insert
    - SharedVaultWriteDenied raised when non-admin tries to write to shared vault with policy=admin_only (VAULT-03)
  </behavior>
  <action>
**CRITICAL IMPLEMENTATION RULES:**
- ZERO FastAPI imports. ZERO starlette imports. Services take `OperationContext` and `AsyncSession`, never a `Request`.
- `_resolved_links` is a RESERVED system key in `pages.frontmatter` JSONB. Never expose it in ParsedPage frontmatter (already stripped by parser). Write computed result back after upsert.
- `enforce_timeline=True` is the API path (D-02). `enforce_timeline=False` is the watchdog path (D-03).
- `note_type` default is `"fleeting"` (D-04). Use `parsed.frontmatter.get("note_type", "fleeting")` on create.
- Content-hash dedup (IDX-03): if `existing.content_hash == parsed.content_hash`, return existing without flush or version insert.
- `_next_version` helper: `SELECT MAX(version) FROM page_versions WHERE page_id = :id` → return 1 if None, else N+1.
- IndexEvent insert on every upsert: event_type="created" or "updated", user_id=ctx.user_id, page_slug=slug.
- Wikilink resolution (D-11): for each extracted wikilink, query `pages.slug` for shortest-unique-path match within user's vault_id (for private) or shared vault_id (for shared namespace). Multiple matches → alphabetically first. No match → unresolved=True, page_id=None. Never reject write for unresolved.
- Shared vault write policy (VAULT-03): if vault.kind=="shared" and settings.shared_vault_write_policy=="admin_only" and ctx.role!="admin" → raise SharedVaultWriteDenied.

Create `server/app/services/pages.py` with the following public API:

```python
"""Page CRUD service (transport-agnostic).

CLAUDE.md: no FastAPI imports; services take OperationContext + AsyncSession.
D-02: timeline append-only enforcement on API writes (enforce_timeline=True).
D-03: watchdog path bypasses enforcement (enforce_timeline=False).
D-04: note_type defaults to 'fleeting' for new pages.
D-09: wikilink resolution stored in frontmatter._resolved_links; no writes to links table.
VAULT-03: shared vault write policy enforced per settings.shared_vault_write_policy.
"""
```

Implement these functions (provider_keys.py analog):

1. `class PageNotFound(Exception): ...`
2. `class TimelineViolation(Exception): ...`
3. `class SharedVaultWriteDenied(PermissionError): ...`

4. `async def _next_version(session: AsyncSession, page_id: uuid.UUID) -> int:`
   - Query `MAX(page_versions.version)` where `page_id = page_id`
   - Return `1` if no versions, else `max_version + 1`

5. `async def _find_slug_match(session: AsyncSession, target_text: str, namespace: str, user_vault_id: uuid.UUID, shared_vault_id: uuid.UUID | None) -> Page | None:`
   - Namespace routing per D-11: if namespace=="shared", query shared vault only; else query user private vault first, then shared if no match
   - Shortest-unique-path: query pages where slug ends with the target text (or is exactly the target text after removing folder prefix)
   - Alphabetically first on tie: `ORDER BY slug ASC LIMIT 1`
   - Returns Page or None

6. `async def upsert_page(session: AsyncSession, ctx: OperationContext, *, vault_id: uuid.UUID, slug: str, parsed: ParsedPage, enforce_timeline: bool = True) -> Page:`
   - Content-hash dedup: early return if hash unchanged
   - Version insert on every update (not on create? or also on create to establish v1 — planner's call: insert v1 on create too for complete history)
   - Insert IndexEvent with event_type="created" or "updated"

7. `async def write_page(session: AsyncSession, ctx: OperationContext, *, slug: str, raw_content: bytes, vault_id: uuid.UUID, shared_vault_id: uuid.UUID | None = None) -> Page:`
   - Parse: `parsed = parse_vault_file(raw_content)`
   - Check shared vault write policy (load vault.kind from DB if needed)
   - Validate slug (call validate_slug from vault.paths)
   - Upsert with enforce_timeline=True
   - After upsert: call resolve_and_store_wikilinks
   - Return the Page

8. `async def read_page(session: AsyncSession, *, vault_id: uuid.UUID, slug: str) -> Page:`
   - `SELECT ... WHERE vault_id=vault_id AND slug=slug AND deleted_at IS NULL`
   - Raises PageNotFound if not found

9. `async def soft_delete_page(session: AsyncSession, ctx: OperationContext, *, page_id: uuid.UUID, reason: str = "file_deleted") -> None:`
   - `UPDATE pages SET deleted_at=now(), deleted_by=ctx.user_id, delete_reason=reason WHERE id=page_id`
   - Insert IndexEvent with event_type="deleted"

10. `async def append_timeline(session: AsyncSession, ctx: OperationContext, *, vault_id: uuid.UUID, slug: str, entry: str) -> Page:`
    - Load page, get current timeline, append entry (with newline separator), call upsert_page with enforce_timeline=False (it's a service-controlled append, not raw user content)

11. `async def resolve_and_store_wikilinks(session: AsyncSession, page: Page, raw_content: str, *, user_vault_id: uuid.UUID, shared_vault_id: uuid.UUID | None = None) -> None:`
    - Call `extract_wikilinks(raw_content)` to get parsed wikilinks
    - For each: call `_find_slug_match` to resolve
    - Build list of dicts per D-10 schema: `{raw, target_text, resolved_slug, page_id, namespace, unresolved}`
    - Write `page.frontmatter["_resolved_links"] = resolved_list` and `await session.flush()`
  </action>
  <verify>
    <automated>cd /home/yongxin.Li/Documents/nexora/smart-copilot/server && python -c "from app.services.pages import upsert_page, write_page, read_page, soft_delete_page, append_timeline, resolve_and_store_wikilinks, PageNotFound, TimelineViolation, SharedVaultWriteDenied; print('all imports OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `server/app/services/pages.py` exists
    - `from app.services.pages import upsert_page, write_page, read_page, soft_delete_page, append_timeline, resolve_and_store_wikilinks, PageNotFound, TimelineViolation, SharedVaultWriteDenied` succeeds
    - File does NOT contain `from fastapi` or `from starlette` (grep must return empty)
    - File contains `enforce_timeline: bool = True` in upsert_page signature
    - File contains `parsed.content_hash == ` hash dedup check
    - File contains `PageVersion(` constructor call (version snapshot insert)
    - File contains `IndexEvent(` constructor call (indexing event)
    - File contains `_resolved_links` string (wikilink storage)
    - File contains `SharedVaultWriteDenied` class and raise site
    - File contains `from app.vault.parser import` (parser imports)
  </acceptance_criteria>
  <done>services/pages.py created as fully transport-agnostic service with all 10 public functions and domain exceptions</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Replace four test stubs with real integration tests</name>
  <read_first>
    - server/app/tests/vault/test_pages_service.py (current stubs to replace)
    - server/app/tests/vault/test_wikilinks.py (current stubs to replace)
    - server/app/tests/vault/test_rls_pages.py (current stubs to replace)
    - server/app/tests/vault/test_shared_vault.py (current stubs to replace)
    - server/app/tests/vault/conftest.py (available fixtures: test_engine, seed_vault, seed_page, seed_user_for_vault, system_ctx, _patch_session_factory)
    - server/app/tests/auth/test_rls_isolation.py (lines 32-37: _ctx_for helper, lines 76-97: GUC leak test pattern)
    - server/app/tests/auth/test_scheduler_prune.py (full file — count helper + seed + test pattern for scheduler job)
    - server/app/services/pages.py (just created — read to understand function signatures)
    - .planning/phases/01c-vault-watchdog-indexer/01c-RESEARCH.md (RLS isolation test pattern section, scheduler job test pattern)
  </read_first>
  <files>
    server/app/tests/vault/test_pages_service.py,
    server/app/tests/vault/test_wikilinks.py,
    server/app/tests/vault/test_rls_pages.py,
    server/app/tests/vault/test_shared_vault.py
  </files>
  <behavior>
    - test_note_type_defaults_to_fleeting: upsert_page with no note_type in frontmatter -> page.note_type == "fleeting"
    - test_versioning_inserts_page_version_on_update: update existing page -> count of page_versions for that page increases by 1
    - test_dedup_skips_reindex_when_hash_unchanged: upsert twice with same content -> page_versions count unchanged on second call
    - test_timeline_append_only: upsert_page with enforce_timeline=True and mutated timeline -> raises VaultTimelineError
    - test_soft_delete_sets_fields: soft_delete_page -> page.deleted_at is not None, page.deleted_by == ctx.user_id, page.delete_reason == "file_deleted"
    - test_user_a_cannot_read_user_b_pages: write page as user_a -> read as user_b with user_b's session_with_rls -> PageNotFound (RLS blocks)
    - test_guc_not_leaked: after request as user_a, same DB connection as user_b sees no app.current_user_id GUC set
    - test_wikilink_stored_in_frontmatter: write page with [[Target]] -> page.frontmatter["_resolved_links"] is a list
    - test_unresolved_forward_ref_allowed: [[NonExistent]] -> write succeeds, unresolved=True in _resolved_links
    - test_admin_only_write_policy: non-admin writing to shared vault with policy=admin_only -> SharedVaultWriteDenied
  </behavior>
  <action>
**CRITICAL: These are integration tests that use the testcontainer DB. They must use `test_engine` fixture, not call `session_with_rls` with prod DB. The `_patch_session_factory` in conftest.py handles this redirect automatically.**

**Context pattern from auth tests:** Use `OperationContext` directly for test user contexts. Create `_ctx_for(user_id, role="user")` helper returning `OperationContext(user_id=user_id, role=role, transport="rest", remote=True, client_name="test", request_id="test")`.

**For RLS tests (test_rls_pages.py):** Follow `server/app/tests/auth/test_rls_isolation.py` pattern:
- Create two users with `_seed_user` pattern
- Write a page as user A via `session_with_rls(ctx_a)`
- Attempt to read as user B via `session_with_rls(ctx_b)` — expect PageNotFound
- GUC leak test: after user A's session exits `finally:`, query `current_setting('app.current_user_id', true)` on a fresh connection — expect empty string

**For shared vault tests (test_shared_vault.py):** 
- Need a shared vault row in DB (kind='shared', owner_user_id=None)
- Test `write_page` to shared vault as non-admin with `settings.shared_vault_write_policy='admin_only'` → SharedVaultWriteDenied
- Test that admin can write to shared vault

**Session management in tests:** Use `async_sessionmaker(test_engine, ...)` to get a direct session (not session_with_rls) for seeding data. For testing services that use `session_with_rls`, call the service functions with a direct session obtained from the test factory (the _patch_session_factory redirect means session_with_rls already uses the test engine).

**Replace all four test files** removing all `pytest.skip()` calls and replacing with real test implementations that use the fixtures from conftest.py. Use `pytestmark = [pytest.mark.vault, pytest.mark.integration]` in each file.

For `test_pages_service.py`: import and call `upsert_page`, `soft_delete_page`, `read_page` directly with `async for session in session_with_rls(ctx):` pattern.

For `test_wikilinks.py`: write pages containing `[[...]]` wikilinks and assert `page.frontmatter["_resolved_links"]` structure.

For `test_rls_pages.py`: create two vault users, write page as user_a, confirm user_b cannot read it.

For `test_shared_vault.py`: seed a shared vault, test write policy enforcement.
  </action>
  <verify>
    <automated>cd /home/yongxin.Li/Documents/nexora/smart-copilot/server && python -m pytest app/tests/vault/test_pages_service.py app/tests/vault/test_rls_pages.py app/tests/vault/test_wikilinks.py app/tests/vault/test_shared_vault.py -x -q --no-header 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - `pytest app/tests/vault/test_pages_service.py -x -q` exits 0, all tests PASSED (no SKIP)
    - `pytest app/tests/vault/test_rls_pages.py -x -q` exits 0, all tests PASSED
    - `pytest app/tests/vault/test_wikilinks.py -x -q` exits 0, all tests PASSED
    - `pytest app/tests/vault/test_shared_vault.py -x -q` exits 0, all tests PASSED
    - No `pytest.skip()` calls remain in any of the four files
    - test_rls_pages.py contains at least one test that verifies cross-user read returns no data (VAULT-02)
    - test_shared_vault.py contains a test verifying SharedVaultWriteDenied for non-admin (VAULT-03)
    - test_pages_service.py covers note_type default, versioning, hash dedup, soft-delete, timeline enforcement
  </acceptance_criteria>
  <done>Four integration test files replaced with real tests; all pass against testcontainer DB; VAULT-02, VAULT-03, VAULT-04, VAULT-06, VAULT-07, VAULT-08, VAULT-09 covered</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| API caller → write_page | Untrusted raw_content bytes; parsed by vault parser before DB write |
| write_page → shared vault | Shared vault write policy checks ctx.role before allowing write |
| session_with_rls → PostgreSQL | RLS GUC (app.current_user_id) scopes all reads to the authenticated user |
| wikilink resolver → pages table | Query scoped to user_vault_id + shared_vault_id; never queries other private vaults |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-01c04-01 | Information Disclosure | Cross-user page reads | mitigate | RLS via session_with_rls(ctx) — SET app.current_user_id enforces per-user visibility |
| T-01c04-02 | Tampering | Timeline mutation via API | mitigate | assert_timeline_append_only called in upsert_page when enforce_timeline=True (D-02) |
| T-01c04-03 | Tampering | _resolved_links user injection | mitigate | Parser strips key (Plan 03); service writes system-computed value after upsert |
| T-01c04-04 | Information Disclosure | Wikilink cross-vault reads | mitigate | _find_slug_match queries only user_vault_id + shared_vault_id; never queries other private vaults |
| T-01c04-05 | EoP | Shared vault write by non-admin | mitigate | SharedVaultWriteDenied raised when vault.kind=="shared" and ctx.role!="admin" with admin_only policy |
</threat_model>

<verification>
```bash
cd /home/yongxin.Li/Documents/nexora/smart-copilot/server

# Import check — must have zero FastAPI imports
python -c "from app.services.pages import upsert_page, write_page, read_page, soft_delete_page, append_timeline, resolve_and_store_wikilinks, PageNotFound, TimelineViolation, SharedVaultWriteDenied; print('OK')"

# Grep gate — no FastAPI in service
grep -v '^#' app/services/pages.py | grep -c 'from fastapi\|import fastapi'
# Expected: 0

# Integration tests
python -m pytest app/tests/vault/test_pages_service.py app/tests/vault/test_rls_pages.py app/tests/vault/test_wikilinks.py app/tests/vault/test_shared_vault.py -v --no-header
```
</verification>

<success_criteria>
- `services/pages.py` created as transport-agnostic CRUD service with all 10 functions and 3 exception classes
- Zero FastAPI/starlette imports in pages.py
- Content-hash dedup, page version snapshot, IndexEvent insert all implemented
- Timeline enforcement (D-02) and bypass (D-03) both implemented via enforce_timeline parameter
- Wikilink resolution stores _resolved_links in JSONB, does NOT write to links table (D-09)
- All four integration test files pass with real tests (no SKIP)
- VAULT-02 RLS isolation test verifies cross-user reads are blocked
- VAULT-03 test verifies admin_only policy enforced
</success_criteria>

<output>
After completion, create `.planning/phases/01c-vault-watchdog-indexer/01c-04-SUMMARY.md`
</output>
