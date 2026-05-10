# Phase 1c: Vault + Watchdog Indexer - Context

**Gathered:** 2026-05-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the page CRUD service layer on top of the Phase 1a/1b foundation:

- Vault path management (`/vaults/private/{username}/`, `/vaults/shared/`) with symlink-escape and `..`-traversal rejection
- Frontmatter parser (YAML), body-shape detector (compiled_truth_only / timeline_only / mixed / empty), content-hash computation (xxhash64)
- Compiled-truth / timeline convention enforcement: separator = standalone `---` after frontmatter; above-the-line = rewritable `compiled_truth`; below-the-line = append-only event log
- Wikilink resolution (Obsidian shortest-unique-path → resolved_links in `pages.frontmatter` JSONB; no writes to `links` table — that is Phase 2b)
- Page CRUD service (`services/pages.py`): create, read, update, soft-delete, version snapshot, compiled-truth/timeline hard enforcement
- Content-hash deduplication (xxhash64); re-index only on hash change
- `page_note_type_enum` migration fix: replace current wrong values with Zettelkasten lifecycle enum (fleeting / literature / permanent / archived_fleeting / skill / moc)
- Real watchdog implementation in `vault/watcher.py`: inotify Observer, per-path 750ms debounce, `asyncio.run_coroutine_threadsafe` handoff
- IDX-04 reconciliation job (5-minute APScheduler interval, lightweight)
- OpenAPI pre-commit hook wiring (`docs/openapi.json` committed to repo, CI fails on stale spec)

**Not in this phase:** REST/MCP routes (Phase 1d), typed link extraction to `links` table (Phase 2b), embedding/chunking (Phase 2a).

</domain>

<decisions>
## Implementation Decisions

### Compiled-Truth / Timeline Separator

- **D-01:** Separator marker = standalone `---` horizontal rule on its own line, after frontmatter is removed. Parser rule: (1) strip YAML frontmatter block first, (2) scan remaining body for the first line that is exactly `---`, (3) content above = `compiled_truth`, content below = `timeline`, (4) at most one separator per page, (5) no separator → whole body = `compiled_truth`, `timeline` = empty string.
- **D-02:** Timeline append-only enforcement — **hard reject** for API/MCP writes. The service layer diffs existing timeline content against the submitted timeline. If any existing timeline line is edited, deleted, or reordered, the write is rejected with HTTP 422 / `validation_error`. Only new timeline entries appended at the end are allowed. The preferred write path for timeline updates is a dedicated `append_timeline` operation, not a full-page PUT.
- **D-03:** Filesystem edits bypass API enforcement ("human always wins"). When the watchdog ingests a disk change that contains timeline mutations, it processes the file and emits an `index_event` + maintenance warning — it does NOT reject the write. The page DB state is updated to match disk.
- **D-04:** `pages.note_type` is the **Zettelkasten lifecycle kind**, NOT the body structure. The existing `page_note_type_enum` has wrong values (`compiled_truth`, `timeline`, `mixed`) — Phase 1c MUST add an Alembic migration to replace them with: `fleeting`, `literature`, `permanent`, `archived_fleeting`, `skill`, `moc`. New pages default to `fleeting` unless frontmatter specifies otherwise.
- **D-05:** Parser returns a separate `body_shape` field (Python enum/dataclass, not a DB column): `compiled_truth_only`, `timeline_only`, `mixed`, `empty`. Used internally by the indexer and chunker. Chunks use `chunk.kind` (`compiled_truth`, `timeline`, `frontmatter`) to type their content.

### Watchdog Thread→Asyncio Handoff

- **D-06:** Canonical handoff API = `asyncio.run_coroutine_threadsafe(coro, loop)`. The watchdog Observer runs in a dedicated OS thread; ALL async indexer/reconciliation work is submitted via `run_coroutine_threadsafe`. `loop.call_soon_threadsafe` is reserved for truly synchronous lightweight callbacks only (not the indexing path). The ROADMAP success criterion #4 takes precedence over the CLAUDE.md example code.
- **D-07:** Per-path debounce implemented as a cancellable timer dictionary. Add `vault.watch_debounce_ms: int = 750` to `settings.py` (pydantic-settings, env: `SMARTCOPILOT_VAULT_WATCH_DEBOUNCE_MS`). On each filesystem event for a path: cancel any pending timer for that path, schedule `run_coroutine_threadsafe(index_page(path), loop)` after the debounce interval. Do NOT process every raw filesystem event.
- **D-08:** IDX-04 reconciliation job runs every **5 minutes** via APScheduler (same `apscheduler` supervisord process as the Phase 1b login-prune job). Lightweight pass: scan vault directory tree, compare file paths + mtimes + content_hash against DB, enqueue only changed / missing / deleted pages. Separate "deep reconciliation" path reserved for container startup and manual CLI invocation (`smartcopilot reconcile --deep`).

### Wikilink Resolution

- **D-09:** Phase 1c does **resolve only** — no writes to the `links` table. On page write: parse all wikilink patterns (`[[Title]]`, `[[folder/Title]]`, `[[shared/Title]]`, `[[Title|display]]`), resolve each to a target page using the VAULT-09 algorithm, store result in `pages.frontmatter` JSONB under reserved system key `_resolved_links`. Do NOT write to the typed `links` table — that is Phase 2b's zero-LLM extraction job.
- **D-10:** `_resolved_links` schema per wikilink: `{raw: str, target_text: str, resolved_slug: str | null, page_id: UUID | null, namespace: "private" | "shared", unresolved: bool}`.
- **D-11:** Resolution algorithm (VAULT-09, deterministic, non-blocking):
  1. Parse raw wikilink text (strip `[[`, `]]`, split on `|` for display alias)
  2. Namespace routing: explicit `[[shared/...]]` → shared vault; otherwise search user's private vault first, then shared
  3. Shortest-unique-path match against `pages.slug` in DB
  4. Exactly one match → resolve to that `page_id` / `resolved_slug`
  5. Multiple equal matches → alphabetically-first slug wins
  6. No match → `unresolved=true`, preserve raw target text, `page_id=null`
  7. **Never reject** the page write for unresolved wikilinks — forward references are valid

### OpenAPI Pre-Commit Hook

- **D-12:** Wire the `docs/openapi.json` pre-commit hook in Phase 1c. Hook runs a script that starts the FastAPI app in test mode, calls `GET /openapi.json`, and writes `docs/openapi.json`. Triggers on changes to any `routes/`, `services/`, or Pydantic schema file.
- **D-13:** `docs/openapi.json` is **committed to the repo**. CI step regenerates it and fails if `git diff` detects a stale spec. Phase 8 Electron client uses the checked-in spec for `openapi-typescript` codegen. At Phase 1c, the spec contains only currently-implemented routes (e.g., `/health`); Phase 1d vault routes will trigger automatic regeneration.

### Claude's Discretion

- `note_type` default for new pages: `fleeting` (unless frontmatter contains `note_type: <other value>`)
- `body_shape` is an in-memory enum only — not a DB column
- `watch_debounce_ms` default 750ms matches DEC-003 from CLAUDE.md; configurable via env var
- Reconciliation job: `coalesce=True, max_instances=1` (consistent with APScheduler discipline from Phase 1b D-09)
- Wikilink parsing: use a simple regex (`\[\[([^\]]+)\]\]`) rather than a markdown-it plugin — keeps parser deterministic and dependency-free for this feature

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product Requirements
- `docs/product_requirements_document_v26.05.md` — authoritative PRD (v26.05.1). Phase 1c directly implements: §VAULT sections (vault path management, compiled-truth/timeline convention, wikilink resolution, content-hash, page versioning, soft delete), §IDX sections (watchdog, reconciliation), §VAULT-01–11, §IDX-01–04.

### Planning Artifacts
- `.planning/REQUIREMENTS.md` — structured requirements VAULT-01 through VAULT-11, IDX-01 through IDX-04 scoped to Phase 1c
- `.planning/ROADMAP.md` — phase boundary, 5 success criteria for Phase 1c, and dependency on Phase 1b
- `.planning/PROJECT.md` — out-of-scope list (no Redis, no LightRAG, no LLM-based link extractor)
- `.planning/phases/01b-auth-security-primitives/01b-CONTEXT.md` — Phase 1b decisions: D-17–22 (OperationContext shape), D-20 (RLS GUC discipline, get_db_session, session_with_rls), D-27 (structlog field redaction keys)
- `.planning/phases/01a-container-data-layer/01a-CONTEXT.md` — Phase 1a decisions: D-09 (module ownership), D-13 (pydantic-settings pattern)

### Architecture Constraints (CLAUDE.md)
- Services MUST be transport-agnostic: no FastAPI types in `services/`; services take `OperationContext`
- RLS discipline: `SET app.current_user_id` (not `SET LOCAL`); always `RESET` in `finally:`
- Watchdog → asyncio handoff: `asyncio.run_coroutine_threadsafe(coro, loop)` exclusively for async indexing work (D-06 overrides CLAUDE.md call_soon_threadsafe example)
- Debounce at 750ms (DEC-003): coalesce rapid-fire events; D-07 makes this configurable via settings

### Existing Code (already shipped)
- `server/app/models/page.py` — `pages` table: `compiled_truth` (Text), `content_hash` (String(32)), `enrichment_hash`, `frontmatter` (JSONB), `note_type` (ENUM — needs migration fix), soft-delete columns
- `server/app/models/page_version.py` — `page_versions` table: `page_id`, `version`, `frontmatter`, `compiled_truth`, `content_hash`
- `server/app/models/vault.py` — `vaults` table: `kind` (private/shared), `path`, `owner_user_id`
- `server/app/models/link.py` — `links` table: `src_page_id`, `dst_entity_id`, `link_type`, `source_kind` (wikilink/enrichment/inferred) — Phase 1c does NOT write here
- `server/app/models/index_event.py` — `index_events` table: for recording watchdog/reconciler activity
- `server/app/vault/watcher.py` — STUB process (Phase 1a); real implementation lands in Phase 1c
- `server/app/dependencies.py:get_db_session` — already has RESET in finally; extend with SET for page service
- `server/app/settings.py` — pydantic-settings base; add `vault_watch_debounce_ms: int = 750` and `shared_vault_write_policy: str = "admin_only"`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server/app/dependencies.py:get_db_session` — reuse directly; it already owns the RLS GUC SET/RESET pattern; page service depends on it via `session_with_rls(ctx)` helper established in Phase 1b
- `server/app/auth/core.py:AuthResult` + `OperationContext` (Phase 1b) — page service accepts `OperationContext`, never a FastAPI `Request`
- `server/app/scheduler/` — APScheduler process already running; add the 5-minute reconciliation job alongside the Phase 1b login-prune job
- `server/app/models/index_event.py` — already modeled; use for recording watchdog/reconciler events

### Established Patterns
- One file per domain in `server/app/models/` (D-07 from Phase 1a) — page service lives in `server/app/services/pages.py`
- Transport-agnostic services: `services/` never imports FastAPI; takes `OperationContext` and `AsyncSession`
- APScheduler job registration: `add_job(..., replace_existing=True, coalesce=True, max_instances=1)` — consistent with Phase 1b D-09
- structlog field redaction already active (Phase 1b); no `content_hash`, `encrypted_key`, or wikilink target values should appear at ERROR level

### Integration Points
- `server/app/vault/watcher.py` — stub becomes the real watchdog process; shares the `app` package and imports `services/pages.py`
- `server/app/models/__init__.py` — no new model files expected; migration adds/fixes the `page_note_type_enum` values
- `alembic/` — new migration `0003_fix_page_note_type_enum.py` to replace enum values with Zettelkasten lifecycle kinds
- Phase 1d will add routes that call the page service built in Phase 1c; no route code in Phase 1c

</code_context>

<specifics>
## Specific Ideas

- **Separator invariant:** "at most one compiled-truth/timeline separator per page" is enforced by the parser — raise `VaultParseError` if a second standalone `---` appears below the first
- **Timeline diff for enforcement:** line-by-line text comparison between `current_timeline` and `submitted_timeline`; reject if any prefix of existing lines differs
- **Wikilink regex:** `\[\[([^\]]+)\]\]` — simple, no markdown-it plugin dependency
- **pre-commit hook script:** likely a small Python script that imports the FastAPI app, uses `fastapi.testclient.TestClient` to hit `/openapi.json`, and writes the result to `docs/openapi.json`; avoids starting a real server
- **`_resolved_links` is a reserved system key** in `pages.frontmatter` JSONB — callers must not overwrite it in their frontmatter submissions

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 1c-Vault + Watchdog Indexer*
*Context gathered: 2026-05-08*
