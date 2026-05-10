# Phase 1c: Vault + Watchdog Indexer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-08
**Phase:** 1c-Vault + Watchdog Indexer
**Areas discussed:** Compiled-truth / timeline separator, Watchdog thread→asyncio handoff API, Wikilink extraction scope, OpenAPI hook placement

---

## Compiled-truth / Timeline Separator

### Question 1: Separator marker in markdown

| Option | Description | Selected |
|--------|-------------|----------|
| Plain `---` horizontal rule | Standard markdown HR; frontmatter end `---` is at position 2+ so mid-doc `---` unambiguous | ✓ |
| `<!-- timeline -->` comment | HTML comment — invisible in rendered markdown, survives copy-paste | |
| `## Timeline` heading | Visible in rendered page, readable but adds ATX heading to parse | |

**User's choice:** Plain `---` HR with explicit parser rules: strip frontmatter first → find first standalone `---` → above = compiled_truth, below = timeline → at most one separator → no separator = whole body is compiled_truth.

---

### Question 2: Append-only timeline enforcement strictness

| Option | Description | Selected |
|--------|-------------|----------|
| Hard reject (422 validation_error) | Diff existing vs. submitted timeline; reject if lines edited/deleted/reordered | ✓ |
| Soft warn | Allow write, emit structured log warning | |
| Advisory only | No enforcement, documented convention | |

**User's choice:** Hard reject for API/MCP writes. Preferred write path = `append_timeline` endpoint. Filesystem edits = "human wins" — reconciler ingests and emits maintenance warning without rejecting.

---

### Question 3: How `note_type` is derived

| Option | Description | Selected |
|--------|-------------|----------|
| You decide | Logical default: no separator = compiled_truth, separator + both sections = mixed, etc. | |
| Always `mixed` if separator present | Simpler — separator present = mixed, no separator = compiled_truth | |
| Specify a different rule | Custom logic | ✓ |

**User's choice (correction):** `pages.note_type` is the **Zettelkasten lifecycle kind**, NOT body structure. Existing `page_note_type_enum` values (`compiled_truth`, `timeline`, `mixed`) are WRONG. Phase 1c must migrate the enum to: `fleeting`, `literature`, `permanent`, `archived_fleeting`, `skill`, `moc`. Parser returns a separate in-memory `body_shape` field. Chunks use `chunk.kind`.

---

## Watchdog Thread→Asyncio Handoff API

### Question 1: Which API for handoff

| Option | Description | Selected |
|--------|-------------|----------|
| `asyncio.run_coroutine_threadsafe(coro, loop)` | Schedules coroutine directly; matches ROADMAP success criterion #4 | ✓ |
| `loop.call_soon_threadsafe(callback)` | Schedules sync callback per CLAUDE.md example; more boilerplate for coroutines | |
| Both, depending on use case | Use simpler one for signals, run_coroutine_threadsafe for real async work | |

**User's choice:** `run_coroutine_threadsafe` exclusively for async indexing work. `call_soon_threadsafe` only for lightweight sync callbacks. ROADMAP success criterion takes precedence over CLAUDE.md example. Update normative documentation to reflect this.

---

### Question 2: Debounce strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed 750ms (DEC-003) | Per CLAUDE.md DEC-003; not configurable | |
| Configurable (default 750ms) | `vault.watch_debounce_ms` in settings, env: `SMARTCOPILOT_VAULT_WATCH_DEBOUNCE_MS` | ✓ |
| No debounce | Process every event immediately | |

**User's choice:** Configurable per-path debounce, default 750ms. Per-path timer registry: cancel + reschedule on each event.

---

### Question 3: IDX-04 reconciliation cadence

| Option | Description | Selected |
|--------|-------------|----------|
| 5-minute APScheduler | Lightweight pass, quick exit when no drift | ✓ |
| Hourly APScheduler | Less aggressive, matches login-prune cadence | |
| On-demand CLI only | No background scheduling | |

**User's choice:** 5-minute lightweight pass + separate deep reconciliation path for startup and manual CLI.

---

## Wikilink Extraction Scope

### Question 1: What Phase 1c does with `[[Title]]` on page write

| Option | Description | Selected |
|--------|-------------|----------|
| Resolve only → `pages.frontmatter` JSONB `_resolved_links` | No writes to `links` table; Phase 2b does typed extraction | ✓ |
| Full extraction → `links` table | Parse + resolve + type + write to links table now | |
| Parse only, no resolution | Store raw extracted titles, no slug lookup | |

**User's choice:** Resolve only. Store in `pages.frontmatter._resolved_links` with schema: `{raw, target_text, resolved_slug, page_id, namespace, unresolved}`. `links` table is Phase 2b's job.

---

### Question 2: Ambiguous wikilink resolution

| Option | Description | Selected |
|--------|-------------|----------|
| Alphabetically-first slug wins; `unresolved=true` for no-match | Deterministic, non-blocking, forward references valid | ✓ |
| First-found (DB insertion order) | Non-deterministic on ties | |
| Reject write if any wikilink unresolved | No forward references allowed | |

**User's choice:** Deterministic 7-step algorithm: parse → namespace route (explicit shared / private-first-then-shared) → shortest-unique-path match → one match wins → tie = alphabetically-first → no match = unresolved=true. Never reject page write for unresolved wikilinks.

---

## OpenAPI Hook Placement

### Question 1: Where the hook lands

| Option | Description | Selected |
|--------|-------------|----------|
| Wire hook in Phase 1c against current routes | Infrastructure set up now; Phase 1d routes trigger auto-regen | ✓ |
| Defer entirely to Phase 1d | Criterion #5 acknowledged as misplaced | |
| Wire hook + add stub vault routes | Scope creep risk | |

**User's choice:** Wire hook in Phase 1c. Success criterion #5 satisfied by: FastAPI serves `/openapi.json`, script generates `docs/openapi.json`, pre-commit hook runs on route-file changes, CI fails on stale spec. Spec content at Phase 1c = current routes (health etc.); Phase 1d regen is automatic.

---

### Question 2: Commit `docs/openapi.json` to repo?

| Option | Description | Selected |
|--------|-------------|----------|
| Committed to repo (canonical interface contract) | Phase 8 Electron uses for openapi-typescript codegen | ✓ |
| Generated locally only, gitignored | Downstream tools fetch from running server | |
| Generated in CI only | Not local | |

**User's choice:** Committed to repo. Pre-commit hook regenerates and stages it. CI regenerates and fails if stale.

---

## Claude's Discretion

- `note_type` default for new pages = `fleeting` (unless frontmatter overrides)
- `body_shape` is in-memory enum only — not a DB column
- `watch_debounce_ms` default 750ms configurable via env var
- Reconciliation job: `coalesce=True, max_instances=1`
- Wikilink parser: simple regex `\[\[([^\]]+)\]\]`, no markdown-it plugin
- OpenAPI hook script: use `fastapi.testclient.TestClient` to avoid starting a real server

## Deferred Ideas

None — discussion stayed within phase scope.
