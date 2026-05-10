# Phase 1c: Vault + Watchdog Indexer - Research

**Researched:** 2026-05-08
**Domain:** Vault path management, page CRUD service, compiled-truth/timeline parsing, wikilink resolution, watchdog inotify, Alembic enum migration, OpenAPI pre-commit hook
**Confidence:** HIGH — all major findings verified against installed code and official docs

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Separator marker = standalone `---` on its own line, after frontmatter is stripped. (1) strip YAML frontmatter block first, (2) scan remaining body for first line exactly `---`, (3) content above = `compiled_truth`, content below = `timeline`, (4) at most one separator per page, (5) no separator → whole body = `compiled_truth`, `timeline` = empty string.
- **D-02:** Timeline append-only enforcement = **hard reject** via API (HTTP 422 / `validation_error`). Line-by-line diff; any edit/delete/reorder of existing timeline lines → reject.
- **D-03:** Filesystem edits bypass API enforcement; watchdog ingests disk change, updates DB, emits warning. Does NOT reject.
- **D-04:** `page_note_type_enum` migration fix — replace current wrong values (`compiled_truth`, `timeline`, `mixed`) with Zettelkasten lifecycle enum (`fleeting`, `literature`, `permanent`, `archived_fleeting`, `skill`, `moc`). Default for new pages = `fleeting`.
- **D-05:** `body_shape` is an in-memory Python enum/dataclass only — no DB column. Values: `compiled_truth_only`, `timeline_only`, `mixed`, `empty`.
- **D-06:** Canonical watchdog → asyncio handoff = `asyncio.run_coroutine_threadsafe(coro, loop)`. NOT `loop.call_soon_threadsafe`. OVERRIDES the CLAUDE.md example.
- **D-07:** Per-path debounce = cancellable timer dict, 750ms default. Add `vault_watch_debounce_ms: int = 750` to `settings.py` (env: `SMARTCOPILOT_VAULT_WATCH_DEBOUNCE_MS`). Cancel pending timer on new event for same path; schedule after debounce.
- **D-08:** IDX-04 reconciliation job every **5 minutes** via APScheduler. `coalesce=True, max_instances=1`. Lightweight: compare mtime + content_hash vs DB. Deep reconciliation reserved for startup/manual CLI.
- **D-09:** Phase 1c resolves wikilinks only — no writes to `links` table. Store result in `pages.frontmatter` JSONB under `_resolved_links` key.
- **D-10:** `_resolved_links` schema per wikilink: `{raw, target_text, resolved_slug, page_id, namespace, unresolved}`.
- **D-11:** Resolution algorithm: parse `[[...]]` → namespace routing (shared/ prefix or private-first) → shortest-unique-path match against `pages.slug` in DB → first alphabetically on tie → unresolved if no match; never reject on unresolved.
- **D-12/D-13:** OpenAPI pre-commit hook wired in Phase 1c. Uses `TestClient` (not real server). `docs/openapi.json` committed. CI fails on stale spec.

### Claude's Discretion

- `note_type` default for new pages: `fleeting`
- `body_shape` is in-memory only (no DB column)
- `watch_debounce_ms` default 750ms; configurable via env var
- Reconciliation job: `coalesce=True, max_instances=1`
- Wikilink parsing: simple regex `\[\[([^\]]+)\]\]`, no markdown-it plugin

### Deferred Ideas (OUT OF SCOPE)

- None — discussion stayed within phase scope

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VAULT-01 | Private vaults at `/vaults/private/{username}/`; shared at `/vaults/shared/`; symlink escape and `..` traversal rejected | Path safety section — `os.path.realpath` + prefix check pattern |
| VAULT-02 | Multi-tenancy enforced by PostgreSQL RLS with `app.current_user_id` session GUC | Already implemented in Phase 1b; page service reuses `session_with_rls` |
| VAULT-03 | Shared vault readable by all authenticated; write governed by `shared_vault_write` policy | Settings pattern documented; policy check in page service |
| VAULT-04 | Page CRUD with compiled-truth/timeline convention; horizontal-rule separator | D-01/D-02 parsing algorithm; timeline `Text` column needed in migration |
| VAULT-05 | Frontmatter parsed (YAML); page types recognized | `python-frontmatter` 1.1.0 installed; `page_type_enum` already in DB |
| VAULT-06 | Note types (Zettelkasten lifecycle): fleeting/literature/permanent/archived_fleeting/skill/moc | Migration 0003 replaces wrong enum values |
| VAULT-07 | Content-hash dedup (xxhash64 of raw file bytes); enrichment-hash trigger | `xxhash` 3.7.0 installed; `xxhash.xxh64(raw_bytes).hexdigest()` |
| VAULT-08 | Page versioning (`page_versions` table); soft delete with `deleted_at`, `deleted_by`, `delete_reason` | `page_versions` exists; `deleted_by` column MISSING from `pages` table — requires migration |
| VAULT-09 | Wikilink resolution: shortest-unique-path, alphabetically-first tie, cross-namespace | D-11 algorithm; DB query against `pages.slug` |
| VAULT-10 | Slug validation `^[a-z0-9][a-z0-9\-]{0,127}$` for `remote=true` callers; path confinement on all writes | Path guard function + regex compiled at import time |
| VAULT-11 | OpenAPI auto-generation; `docs/openapi.json` regenerated by pre-commit hook | D-12/D-13; `TestClient` approach; `.pre-commit-config.yaml` needs new hook |
| IDX-01 | Watchdog observer detects vault file changes (inotify on Linux) | `watchdog` 6.0.0 installed; `Observer()` (inotify) on Linux |
| IDX-02 | Watchdog as separate supervisord process; thread→asyncio handoff via `run_coroutine_threadsafe` | D-06 mandates `run_coroutine_threadsafe`; stub already at `vault/watcher.py` |
| IDX-03 | Change detection based on content_hash; re-parse and re-index only on change | xxhash64 compute → compare vs `pages.content_hash` in DB |
| IDX-04 | Reconciliation job corrects filesystem ↔ database drift | APScheduler 5-min interval job; `coalesce=True, max_instances=1` (D-08) |

</phase_requirements>

---

## Summary

Phase 1c builds the page CRUD service layer and filesystem watchdog on top of the Phase 1a/1b foundation. Three conceptual subsystems land together: (1) the vault parser (frontmatter, compiled-truth/timeline body, xxhash64 content-hash, wikilink resolution), (2) the page service (`services/pages.py`) with create/read/update/soft-delete/version/append-timeline, and (3) the watchdog indexer (`vault/watcher.py`) with inotify Observer, per-path debounce, and a 5-minute reconciliation APScheduler job.

All three domain-specific libraries needed for this phase are already installed in the project virtual environment: `watchdog` 6.0.0, `xxhash` 3.7.0, and `python-frontmatter` 1.1.0. The core Alembic infrastructure, test harness (testcontainers + pytest-asyncio), structlog redaction, `OperationContext`, `session_with_rls`, and APScheduler process are all operational from Phases 1a and 1b. Phase 1c extends rather than replaces any of these.

The most significant discovery is a schema gap: the `pages` table does NOT have a `timeline` column (compiled_truth stores above-the-line content; below-the-line has no column yet), and `deleted_by` (FK to users) is absent from both the model and the migration. The Alembic migration 0003 must add `pages.timeline TEXT`, `pages.deleted_by UUID FK users.id`, and replace `page_note_type_enum` values. The existing `page_versions` table also lacks a `timeline` column for snapshotting.

**Primary recommendation:** Structure Phase 1c as six waves: (0) migration + schema fixes, (1) vault parser module, (2) page service, (3) watchdog real implementation, (4) reconciliation job + settings extension, (5) OpenAPI pre-commit hook and acceptance test.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Vault path safety (symlink/traversal rejection) | API / Backend | — | Path confinement is a server-side security enforcement; never client-decided |
| Frontmatter parsing + body-shape detection | API / Backend | — | Parser runs server-side in the page service layer on every write/read |
| Compiled-truth/timeline enforcement | API / Backend | — | Business-rule enforcement belongs in the service layer, not transport or DB |
| Content-hash deduplication | API / Backend | Database / Storage | Hash computed in Python (xxhash64), compared against DB column |
| Page versioning (snapshot) | API / Backend | Database / Storage | Service triggers version insert; DB stores immutable snapshots |
| Wikilink resolution | API / Backend | Database / Storage | Deterministic DB query driven by service; results stored in JSONB |
| Watchdog inotify listener | OS / Process | API / Backend | Runs as a separate supervisord process; emits events to async service |
| Debounce + thread-asyncio handoff | OS / Process | API / Backend | run_coroutine_threadsafe bridges watchdog OS thread to asyncio event loop |
| Reconciliation job (filesystem ↔ DB drift) | API / Backend | Database / Storage | APScheduler 5-min job queries filesystem then DB, runs async service ops |
| OpenAPI spec generation | API / Backend | — | TestClient calls FastAPI in-process; hook runs at commit time |
| RLS data isolation | Database / Storage | API / Backend | Phase 1b RLS policies already active; page service reuses `session_with_rls` |

---

## Standard Stack

### Core (mandated by CLAUDE.md / already installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-frontmatter | 1.1.0 | YAML frontmatter parsing | Mandated in CLAUDE.md; handles `---` delimited frontmatter |
| xxhash | 3.7.0 | Content-hash (xxhash64) and enrichment-hash | Mandated; non-cryptographic, fastest Python hash for dedup |
| watchdog | 6.0.0 | Filesystem observation (inotify on Linux) | Mandated; inotify-native on Linux, polling fallback elsewhere |
| markdown-it-py | 4.0.0 | Markdown processing (NOT used for wikilink parsing per D-discretion) | Installed; wikilink uses simple regex per D-discretion |
| APScheduler | 3.11.2 | Reconciliation job scheduling | Mandated 3.x; 4.x is still alpha — existing scheduler process |
| asyncpg / SQLAlchemy 2.0 | as installed | DB session management | Existing pattern via `session_with_rls` |

**Version verification:** All versions confirmed via `pip3 show` against the active virtualenv. [VERIFIED: pip3 show output]

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| fastapi.testclient | (bundled with FastAPI) | OpenAPI pre-commit hook — calls `/openapi.json` in-process | VAULT-11 only; no real server needed |
| re (stdlib) | stdlib | Wikilink regex `\[\[([^\]]+)\]\]` | D-discretion: no markdown-it plugin for wikilinks |
| threading (stdlib) | stdlib | Timer-based per-path debounce dict in watchdog thread | D-07 cancellable timer pattern |
| pathlib (stdlib) | stdlib | Vault path construction and safety checks | Cross-platform path handling |
| os.path.realpath | stdlib | Symlink resolution for path confinement | VAULT-01 path guard |

**Installation for Phase 1c new dependencies:**
None required — all libraries already present. Phase 1c MUST add them to `requirements.txt` so they are declared:
```bash
# Add to server/requirements.txt:
watchdog>=4.0
xxhash>=3.0
python-frontmatter>=1.1
markdown-it-py>=3.0
```

---

## Architecture Patterns

### System Architecture Diagram

```
Filesystem (inotify)
        │  OS event (created/modified/deleted)
        ▼
[watchdog Observer thread]
  per-path debounce (750ms, cancellable timer dict)
        │  run_coroutine_threadsafe(index_page(path), loop)
        ▼
[asyncio event loop — watchdog process]
  index_page(path)
        │  read raw bytes → xxhash64 → compare content_hash
        │  if changed: parse (frontmatter + body_shape + wikilinks)
        ▼
[services/pages.py: upsert_page(ctx, parsed)]
        │  session_with_rls(system_ctx)
        │  INSERT/UPDATE pages + INSERT page_versions
        │  resolve wikilinks → update frontmatter._resolved_links
        │  INSERT index_events record
        ▼
[PostgreSQL]  pages / page_versions / index_events tables

─────────────────── 5-min interval ─────────────────────
[APScheduler reconciliation job — scheduler process]
  walk vault filesystem → compare mtime + hash vs DB
        │  diff: missing / stale / orphan
        ▼
[services/pages.py: upsert_page / soft_delete_page]
        │  session_with_rls(system_ctx)
        ▼
[PostgreSQL]

─────────────────── API write path ──────────────────────
[Phase 1d routes — NOT IN PHASE 1c]
  PUT /api/v1/pages/{slug}
        │  validate compiled-truth/timeline hard reject (D-02)
        │  validate slug (VAULT-10)
        │  path confinement (VAULT-01)
        ▼
[services/pages.py: write_page(ctx, slug, content)]
        │  parser → enforce timeline append-only diff
        │  xxhash64 dedup check
        │  session_with_rls(ctx)
        │  INSERT/UPDATE pages + INSERT page_versions
        │  write markdown file to vault filesystem path
        ▼
[PostgreSQL + Filesystem]
```

### Recommended Project Structure

```
server/app/
├── vault/
│   ├── __init__.py
│   ├── watcher.py          # Phase 1c: real watchdog impl (replaces stub)
│   ├── parser.py           # NEW: frontmatter + body_shape + wikilink regex
│   └── paths.py            # NEW: vault path safety (symlink/traversal guard)
├── services/
│   └── pages.py            # NEW: page CRUD service (transport-agnostic)
├── scheduler/
│   ├── run.py              # EXTEND: register reconciliation job
│   └── jobs/
│       ├── prune_login_attempts.py  # existing
│       └── reconcile_vault.py      # NEW: IDX-04 5-min reconciliation
├── models/
│   └── page.py             # EXTEND: add timeline + deleted_by; fix note_type enum
├── settings.py             # EXTEND: vault_watch_debounce_ms, shared_vault_write_policy
server/alembic/versions/
└── 0003_phase_1c_vault.py  # NEW: enum fix + timeline col + deleted_by col
docs/
└── openapi.json            # NEW: generated by pre-commit hook
server/.pre-commit-config.yaml  # EXTEND: add openapi-regen hook
scripts/
└── regen_openapi.py        # NEW: TestClient → /openapi.json → docs/openapi.json
```

### Pattern 1: Vault Path Safety (VAULT-01)

**What:** Ensure no symlink escape or `..` traversal can reach outside the vault root.
**When to use:** Every file write/read operation in the page service.

```python
# Source: Python stdlib os.path.realpath docs [CITED: docs.python.org/3/library/os.path.html]
import os
from pathlib import Path

def safe_vault_path(vault_root: str, slug: str) -> Path:
    """Resolve and confine a slug to vault_root. Raises PermissionError on escape."""
    # Slugs are filenames with .md extension; no directory separators allowed for private vault
    root = Path(os.path.realpath(vault_root))
    candidate = Path(os.path.realpath(root / f"{slug}.md"))
    try:
        candidate.relative_to(root)
    except ValueError:
        raise PermissionError(f"Path traversal attempt: {slug!r}")
    return candidate
```

**Key rule:** Always call `os.path.realpath` on BOTH root AND candidate before `relative_to`. `Path.is_relative_to()` does NOT follow symlinks — it is string-only.

### Pattern 2: Frontmatter + Body-Shape Parser (VAULT-04, VAULT-05, D-01, D-05)

**What:** Parse raw file bytes into structured fields. Returns: `frontmatter dict`, `compiled_truth str`, `timeline str`, `body_shape BodyShape`, `content_hash str`.
**When to use:** Every vault file read — on API write path, watchdog indexer, and reconciliation job.

```python
# Source: python-frontmatter docs [CITED: github.com/eyeseast/python-frontmatter]
# Source: D-01, D-05 from CONTEXT.md [CITED: .planning/phases/01c-vault-watchdog-indexer/01c-CONTEXT.md]
import xxhash
import frontmatter
from enum import Enum
from dataclasses import dataclass

class BodyShape(str, Enum):
    compiled_truth_only = "compiled_truth_only"
    timeline_only = "timeline_only"
    mixed = "mixed"
    empty = "empty"

@dataclass
class ParsedPage:
    frontmatter: dict
    compiled_truth: str
    timeline: str
    body_shape: BodyShape
    content_hash: str  # xxhash64 hexdigest of raw_bytes

def parse_vault_file(raw_bytes: bytes) -> ParsedPage:
    content_hash = xxhash.xxh64(raw_bytes).hexdigest()
    post = frontmatter.loads(raw_bytes.decode("utf-8", errors="replace"))
    fm: dict = dict(post.metadata)
    body: str = post.content  # content WITHOUT frontmatter block

    # D-01: scan body for first standalone `---` separator
    lines = body.split("\n")
    sep_idx = None
    for i, line in enumerate(lines):
        if line.strip() == "---":
            if sep_idx is not None:
                raise VaultParseError("Multiple compiled-truth/timeline separators found")
            sep_idx = i

    if sep_idx is None:
        compiled_truth = body
        timeline = ""
        if body.strip():
            body_shape = BodyShape.compiled_truth_only
        else:
            body_shape = BodyShape.empty
    else:
        compiled_truth = "\n".join(lines[:sep_idx]).rstrip()
        timeline = "\n".join(lines[sep_idx + 1:]).lstrip()
        if compiled_truth and timeline:
            body_shape = BodyShape.mixed
        elif timeline:
            body_shape = BodyShape.timeline_only
        else:
            body_shape = BodyShape.compiled_truth_only

    return ParsedPage(
        frontmatter=fm,
        compiled_truth=compiled_truth,
        timeline=timeline,
        body_shape=body_shape,
        content_hash=content_hash,
    )
```

### Pattern 3: Timeline Append-Only Diff (D-02)

**What:** Service-layer enforcement for API writes. Rejects if existing timeline is mutated.
**When to use:** `write_page()` API path only — NOT in watchdog path (D-03).

```python
# Source: D-02 from CONTEXT.md [CITED: .planning/phases/01c-vault-watchdog-indexer/01c-CONTEXT.md]
def _assert_timeline_append_only(existing_timeline: str, submitted_timeline: str) -> None:
    """Raise VaultTimelineError if any existing timeline line is edited, deleted, or reordered."""
    existing_lines = [l for l in existing_timeline.splitlines() if l.strip()]
    submitted_lines = [l for l in submitted_timeline.splitlines() if l.strip()]
    # Submitted must have all existing lines as a prefix (append-only)
    if submitted_lines[:len(existing_lines)] != existing_lines:
        raise VaultTimelineError(
            "Timeline is append-only; existing entries cannot be edited, deleted, or reordered."
        )
```

### Pattern 4: Watchdog Thread → Asyncio Handoff (D-06, IDX-01, IDX-02)

**What:** Safely submit async work from the watchdog OS thread to the asyncio event loop.
**When to use:** ALL async indexer work initiated from watchdog event handlers.

```python
# Source: Python asyncio docs [CITED: docs.python.org/3/library/asyncio-task.html#asyncio.run_coroutine_threadsafe]
# Source: D-06 from CONTEXT.md [CITED: .planning/phases/01c-vault-watchdog-indexer/01c-CONTEXT.md]
import asyncio
import threading
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

class VaultEventHandler(FileSystemEventHandler):
    def __init__(self, loop: asyncio.AbstractEventLoop, debounce_ms: int):
        self._loop = loop
        self._debounce_s = debounce_ms / 1000.0
        self._timers: dict[str, threading.Timer] = {}  # path → pending timer
        self._lock = threading.Lock()

    def _schedule_index(self, path: str) -> None:
        """Per-path debounce: cancel pending timer, schedule new one (D-07)."""
        with self._lock:
            if path in self._timers:
                self._timers[path].cancel()
            timer = threading.Timer(
                self._debounce_s,
                self._fire_index,
                args=(path,),
            )
            self._timers[path] = timer
            timer.start()

    def _fire_index(self, path: str) -> None:
        """Called by Timer thread after debounce — submit to asyncio loop (D-06)."""
        with self._lock:
            self._timers.pop(path, None)
        asyncio.run_coroutine_threadsafe(index_vault_file(path), self._loop)

    def on_modified(self, event):
        if not event.is_directory:
            self._schedule_index(event.src_path)

    def on_created(self, event):
        if not event.is_directory:
            self._schedule_index(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            asyncio.run_coroutine_threadsafe(
                soft_delete_vault_file(event.src_path), self._loop
            )
```

**Critical:** `Observer()` (not `PollingObserver()`) — inotify is more reliable on Linux. [VERIFIED: watchdog docs confirm inotify as default on Linux]

### Pattern 5: Alembic Enum Value Replacement (D-04)

**What:** PostgreSQL does not support DROP VALUE from an ENUM. The migration must use a multi-step approach to replace enum values.
**When to use:** Migration 0003 to replace `page_note_type_enum` values.

```python
# Source: PostgreSQL docs + Alembic patterns [CITED: alembic.sqlalchemy.org/en/latest/ops.html]
# [ASSUMED] — standard approach; verify exact SQL syntax in migration testing
def upgrade():
    # Step 1: Add new enum with correct values
    op.execute("CREATE TYPE page_note_type_enum_new AS ENUM "
               "('fleeting', 'literature', 'permanent', 'archived_fleeting', 'skill', 'moc')")
    # Step 2: Add new column, convert, swap, drop old
    op.execute("ALTER TABLE pages ADD COLUMN note_type_new page_note_type_enum_new "
               "NOT NULL DEFAULT 'fleeting'::page_note_type_enum_new")
    op.execute("ALTER TABLE pages DROP COLUMN note_type")
    op.execute("ALTER TABLE pages RENAME COLUMN note_type_new TO note_type")
    op.execute("DROP TYPE page_note_type_enum")
    op.execute("ALTER TYPE page_note_type_enum_new RENAME TO page_note_type_enum")
    # Update models/page.py ENUM definition to match
```

**Alternative approach (if no existing data):** Drop and recreate is simpler. Phase 1c is pre-production; there is no live data to migrate.

### Pattern 6: APScheduler Reconciliation Job (D-08, IDX-04)

**What:** 5-minute APScheduler job to correct filesystem ↔ database drift.
**When to use:** Always running in the `apscheduler` supervisord process.

```python
# Source: APScheduler 3.x docs [CITED: apscheduler.readthedocs.io/en/3.x/userguide.html]
# In scheduler/run.py (extend existing):
from app.scheduler.jobs.reconcile_vault import reconcile_vault

scheduler.add_job(
    reconcile_vault,
    "interval",
    minutes=5,
    id="reconcile_vault",
    replace_existing=True,
    coalesce=True,
    max_instances=1,
)
```

### Pattern 7: Wikilink Resolution (D-09, D-10, D-11, VAULT-09)

**What:** Parse `[[...]]` patterns, resolve to page slugs, store in `frontmatter._resolved_links` JSONB. No writes to `links` table.
**When to use:** On every page write (API or watchdog).

```python
# Source: D-09, D-10, D-11 from CONTEXT.md [CITED: .planning/phases/01c-vault-watchdog-indexer/01c-CONTEXT.md]
import re

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")

async def resolve_wikilinks(
    raw_content: str,
    user_vault_id: uuid.UUID,
    shared_vault_id: uuid.UUID,
    session: AsyncSession,
) -> list[dict]:
    resolved = []
    for match in WIKILINK_RE.finditer(raw_content):
        raw = match.group(0)
        inner = match.group(1)
        # Split display alias: [[Title|alias]] → target_text = "Title"
        target_text = inner.split("|")[0].strip()
        namespace = "shared" if target_text.startswith("shared/") else "private"
        search_text = target_text.removeprefix("shared/")
        # Query pages.slug in appropriate vault(s)
        # ... DB lookup for shortest-unique-path match ...
        resolved.append({
            "raw": raw,
            "target_text": target_text,
            "resolved_slug": slug_or_none,
            "page_id": str(page_id) if page_id else None,
            "namespace": namespace,
            "unresolved": page_id is None,
        })
    return resolved
```

### Pattern 8: OpenAPI Pre-Commit Hook (VAULT-11, D-12, D-13)

**What:** Script that imports FastAPI app, calls `GET /openapi.json` via `TestClient`, writes result to `docs/openapi.json`.
**When to use:** Pre-commit hook triggered on changes to `routes/`, `services/`, or Pydantic schema files.

```python
# scripts/regen_openapi.py
# Source: FastAPI docs + D-12 from CONTEXT.md [CITED: fastapi.tiangolo.com/tutorial/testing/]
import json
import sys
from pathlib import Path
from fastapi.testclient import TestClient
# Must set env vars before importing app.main
import os
os.environ.setdefault("SMARTCOPILOT_FERNET_KEY", os.environ["SMARTCOPILOT_FERNET_KEY"])
os.environ.setdefault("JWT_SIGNING_KEY", os.environ["JWT_SIGNING_KEY"])

from app.main import app

client = TestClient(app, raise_server_exceptions=True)
resp = client.get("/openapi.json")
if resp.status_code != 200:
    print(f"Failed to get /openapi.json: {resp.status_code}", file=sys.stderr)
    sys.exit(1)

out = Path(__file__).parent.parent / "docs" / "openapi.json"
out.write_text(json.dumps(resp.json(), indent=2))
print(f"Written: {out}")
```

Pre-commit hook entry:
```yaml
# In server/.pre-commit-config.yaml — add:
  - repo: local
    hooks:
      - id: regen-openapi
        name: Regenerate OpenAPI spec
        entry: python scripts/regen_openapi.py
        language: system
        types: [python]
        files: ^server/app/(routes|services|models)/.*\.py$
        pass_filenames: false
```

**Critical requirement for the hook:** `SMARTCOPILOT_FERNET_KEY` and `JWT_SIGNING_KEY` must be available in the developer's environment when running pre-commit. Add to `.env.example` guidance.

### Anti-Patterns to Avoid

- **`call_soon_threadsafe` for async indexing:** Only safe for lightweight sync callbacks. ALL async indexing work MUST use `run_coroutine_threadsafe`. (D-06)
- **`asyncio.run()` inside watchdog event handler:** Creates a new event loop in the wrong thread — causes `RuntimeError` or silent data races.
- **`await` inside watchdog event handler:** Watchdog runs in a dedicated OS thread, not the event loop — `await` will fail.
- **`SET LOCAL` for RLS GUC:** MUST use `SET app.current_user_id` (not `SET LOCAL`). Phase 1b established this pattern.
- **FastAPI types in `services/pages.py`:** Services take `OperationContext` and `AsyncSession`, never `Request`, `Response`, or `HTTPException`. CLAUDE.md constraint.
- **Polling observer on Linux:** Use `Observer()` (inotify). `PollingObserver()` is a fallback for non-Linux; using it on Linux wastes CPU.
- **Processing every raw filesystem event:** Without per-path debounce, rapid saves (auto-save editors) flood the indexer. Always debounce at 750ms minimum (D-07).
- **`Path.is_relative_to()` for path confinement:** String-only, does not resolve symlinks. MUST use `os.path.realpath` on both paths first (VAULT-01).
- **Writing to `links` table in Phase 1c:** The typed link extraction is Phase 2b. Phase 1c only populates `_resolved_links` in the `pages.frontmatter` JSONB.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML frontmatter parsing | Custom YAML scanner | `python-frontmatter` 1.1.0 | Handles edge cases: multi-line strings, nested YAML, encoding, `---` delimiter safety |
| Non-cryptographic content hashing | SHA-256 or md5 | `xxhash.xxh64(bytes).hexdigest()` | xxhash64 is 5-10x faster than MD5 on large files; CLAUDE.md mandates it |
| Filesystem watching (inotify) | `select` + `/proc` polling | `watchdog` 6.0.0 | Kernel-native inotify, retry/reconnect handling, cross-platform fallback built in |
| Debounce timer | `asyncio.sleep` loop | `threading.Timer` with cancel | `threading.Timer` is cancellable; asyncio sleep cannot be cancelled without Future wrappers |
| Thread → asyncio bridge | Custom queue + polling | `asyncio.run_coroutine_threadsafe` | Only correct primitive for submitting coroutines from non-asyncio threads (D-06) |
| YAML parsing (general) | `yaml.safe_load` + manual strip | `frontmatter.loads()` | frontmatter handles the `---` block extraction; avoids off-by-one bugs |

**Key insight:** The watchdog → asyncio handoff is deceptively complex. The only correct primitive for submitting coroutines from a non-asyncio thread to an existing running event loop is `asyncio.run_coroutine_threadsafe`. Any other approach (asyncio.run, loop.call_soon_threadsafe with async calls, concurrent.futures) will either fail immediately or produce subtle data races.

---

## Runtime State Inventory

> Phase 1c is NOT a rename/refactor/migration phase — it is a greenfield service layer. However, it DOES include an Alembic migration that modifies existing enum types and table columns. Runtime state relevant to migration 0003 is documented here.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `page_note_type_enum` in PostgreSQL with wrong values (`compiled_truth`, `timeline`, `mixed`); currently referenced by `pages.note_type` column | Alembic migration 0003: rename-and-recreate pattern (see Pattern 5) |
| Stored data | `pages.compiled_truth` column exists; `pages.timeline` column MISSING | Migration 0003: add `timeline TEXT NULLABLE` column to `pages` and `page_versions` |
| Stored data | `pages.deleted_by` column MISSING (VAULT-08 references it) | Migration 0003: add `deleted_by UUID FK users.id NULLABLE` to `pages` |
| Live service config | Watchdog `vault/watcher.py` is currently a stub process (RUNNING in supervisord) | No data migration; stub is replaced by real implementation; supervisord restarts it |
| OS-registered state | inotify limits: `max_user_watches=65536`, `max_user_instances=128` on this machine | No action for dev; production Docker may need `fs.inotify.max_user_watches` sysctl if vault is large |
| Secrets/env vars | `vault_watch_debounce_ms` is a new settings key — no existing data to migrate | Add to `settings.py` + `.env.example`; defaults to 750 |
| Build artifacts | None relevant to Phase 1c | — |

**Model vs migration gap (BLOCKING):** The `page.py` SQLAlchemy model does NOT define `timeline` or `deleted_by` columns. Both the model AND the migration must be updated together in migration 0003.

---

## Common Pitfalls

### Pitfall 1: Symlink Escape via `Path.is_relative_to()`
**What goes wrong:** Developer uses `candidate.is_relative_to(root)` without resolving symlinks first. A file at `vault_root/symlink` pointing to `../../../etc/passwd` passes the is_relative_to check because the check is string-only.
**Why it happens:** `pathlib.Path.is_relative_to()` is a string comparison — it does not follow symlinks.
**How to avoid:** ALWAYS call `os.path.realpath()` on both vault root AND candidate path before any comparison. Then use `relative_to()`.
**Warning signs:** Tests only test with non-symlink paths; VAULT-01 test must include a symlink fixture.

### Pitfall 2: `run_coroutine_threadsafe` Requires the Event Loop to Already Be Running
**What goes wrong:** Calling `asyncio.run_coroutine_threadsafe(coro, loop)` before the asyncio event loop is running raises `RuntimeError: no running event loop`.
**Why it happens:** The watchdog Observer starts its thread immediately; the asyncio event loop may not yet be running at that moment.
**How to avoid:** Start watchdog AFTER `asyncio.run()` or after the event loop is confirmed running. In the watcher process, store the loop reference from `asyncio.get_event_loop()` inside `asyncio.run()`, not at module import time.
**Warning signs:** Intermittent startup failures, particularly fast restarts.

### Pitfall 3: Alembic Enum Value Replacement — Cannot DROP VALUE
**What goes wrong:** Developer runs `ALTER TYPE page_note_type_enum DROP VALUE 'compiled_truth'` — this is not supported in PostgreSQL.
**Why it happens:** PostgreSQL enums are append-only for ADD; you cannot remove values without recreating.
**How to avoid:** Use the rename-and-recreate pattern (Pattern 5): create new type → add column with new type → drop old column → rename → drop old type.
**Warning signs:** Alembic migration fails with `ERROR: cannot drop enum value`.

### Pitfall 4: `page_note_type_enum` Server Default After Migration
**What goes wrong:** The `pages.note_type` column has `server_default='mixed'` (the old value). After replacing the enum, the server_default must be changed to `'fleeting'`.
**Why it happens:** Column default is stored separately from the type definition.
**How to avoid:** In the migration: `op.alter_column('pages', 'note_type', server_default='fleeting')` AFTER the type is swapped.
**Warning signs:** New rows get `note_type='mixed'` which no longer exists in the enum → insert errors.

### Pitfall 5: `pages.timeline` Column Missing from Model
**What goes wrong:** Writing the parser and service without updating `server/app/models/page.py` to include `timeline: Mapped[str | None]`. Alembic auto-generate will show the column but SQLAlchemy ORM won't map it.
**Why it happens:** Model and migration are maintained separately; easy to update one and forget the other.
**How to avoid:** Wave 0 must update BOTH `models/page.py` AND `models/page_version.py` AND `alembic/versions/0003_*.py` in the same atomic task.
**Warning signs:** `AttributeError: 'Page' object has no attribute 'timeline'` at runtime.

### Pitfall 6: Debounce Timer Not Cancelled on Process Shutdown
**What goes wrong:** Pending `threading.Timer` objects prevent clean process shutdown — they hold references and may fire after the asyncio loop is closed.
**Why it happens:** `threading.Timer` is a daemon-by-default OS thread; if the main watchdog process exits while a timer is pending, the timer fires into a closed event loop.
**How to avoid:** On SIGTERM/SIGINT in the watcher: (1) stop the Observer, (2) cancel all pending timers in the debounce dict, (3) then exit.
**Warning signs:** `RuntimeError: event loop is closed` in logs on clean shutdown.

### Pitfall 7: OpenAPI Script Needs Env Vars at Import Time
**What goes wrong:** `regen_openapi.py` imports `app.main` which triggers `_fail_startup_if_missing_secrets()` → container exits if `SMARTCOPILOT_FERNET_KEY` is not set in the pre-commit hook environment.
**Why it happens:** The startup guard runs at import time (in the lifespan factory), but `TestClient` does not call lifespan by default unless `with TestClient(app)` context manager is used.
**How to avoid:** Option 1 — use `with TestClient(app) as client:` which calls lifespan; ensure env vars are set. Option 2 — add a `no_startup_check` flag to the app factory for test/hook contexts. The simplest approach: the `regen_openapi.py` script requires `SMARTCOPILOT_FERNET_KEY` and `JWT_SIGNING_KEY` to be in the developer's environment (documented in `.env.example`).
**Warning signs:** Pre-commit hook fails with `FATAL: Fernet key not found`.

### Pitfall 8: Wikilink `_resolved_links` Key Overwritten by User Frontmatter
**What goes wrong:** User writes YAML frontmatter with a `_resolved_links` key — the service overwrites or is overwritten by it.
**Why it happens:** `_resolved_links` is a reserved system key in the JSONB column, but there is no enforcement at the model level.
**How to avoid:** In the page service parser: strip `_resolved_links` from the user-submitted frontmatter dict before persisting, then write the computed resolved links back in. Document `_resolved_links` as reserved in the API.
**Warning signs:** Stale or user-controlled wikilink resolution data.

### Pitfall 9: inotify Watch Limit Exhaustion
**What goes wrong:** `watchdog` raises `OSError: [Errno 28] No space left on device` (which is the inotify watch limit error, misleadingly named) when the vault grows large.
**Why it happens:** `max_user_watches` defaults to 65536 on this system. Each directory gets a watch; large vaults can exhaust this.
**How to avoid:** Document in `smartcopilot doctor` check (Phase 6). For Phase 1c, log a warning if watch count approaches limit. Production guidance: `echo fs.inotify.max_user_watches=524288 >> /etc/sysctl.conf`.
**Warning signs:** Watchdog silently stops reporting changes on new directories.

---

## Code Examples

### Frontmatter Round-Trip with python-frontmatter

```python
# Source: python-frontmatter README [CITED: github.com/eyeseast/python-frontmatter/blob/main/README.md]
import frontmatter

# Load: bytes or string both work
post = frontmatter.loads(raw_bytes.decode("utf-8"))
post.metadata  # dict of YAML frontmatter keys
post.content   # body WITHOUT frontmatter block (and without leading ---)

# Dump back to string (round-trip)
raw_out = frontmatter.dumps(post)
```

### xxhash64 Content Hash

```python
# Source: xxhash PyPI docs [CITED: pypi.org/project/xxhash/]
import xxhash

def content_hash(raw_bytes: bytes) -> str:
    """Returns 16-character hex string (64-bit)."""
    return xxhash.xxh64(raw_bytes).hexdigest()
```

### Session With RLS for Watchdog/Scheduler (reuse Phase 1b pattern)

```python
# Source: server/app/db_session.py [VERIFIED: codebase grep]
# Pattern established in Phase 1b — session_with_rls is the async generator
from app.auth.context import system_operation_context
from app.db_session import session_with_rls

async def index_vault_file(path: str) -> None:
    ctx = system_operation_context(request_id="watchdog", client_name="watcher")
    async for session in session_with_rls(ctx):
        # ... parse file, upsert pages, insert index_events ...
        await session.commit()
```

### page_note_type_enum Enum Fixture for Tests

```python
# Pattern for test fixture that doesn't break on enum rename
from enum import Enum

class NoteType(str, Enum):
    fleeting = "fleeting"
    literature = "literature"
    permanent = "permanent"
    archived_fleeting = "archived_fleeting"
    skill = "skill"
    moc = "moc"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `loop.call_soon_threadsafe` for async work | `asyncio.run_coroutine_threadsafe` for coroutines | Python 3.4.4+ | `call_soon_threadsafe` is for sync callbacks only; coroutines need `run_coroutine_threadsafe` |
| `watchdog` `PollingObserver` | `watchdog` `Observer` (inotify on Linux) | watchdog v0.x | inotify is kernel-native, much lower latency than polling |
| Alembic `ADD VALUE` to existing ENUM | Rename-and-recreate pattern | PostgreSQL limitation | `DROP VALUE` never supported; `ADD VALUE` only appends, cannot change existing |
| Frontmatter parsing with regex | `python-frontmatter` library | Pre-existing | Handles edge cases in YAML that naive regex misses |
| `typing.dataclass` for mutable ParsedPage | `dataclasses.dataclass` (mutable) or `attrs` | N/A | OperationContext is frozen (immutable); ParsedPage is mutable (accumulates fields) |

**Deprecated/outdated:**
- `page_note_type_enum` values (`compiled_truth`, `timeline`, `mixed`): Wrong semantic; these describe body shape, not Zettelkasten lifecycle. Replaced in migration 0003.
- `CLAUDE.md example code using `call_soon_threadsafe``: D-06 overrides this. The correct API for async coroutines from threads is `run_coroutine_threadsafe`.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | PostgreSQL rename-and-recreate enum pattern works cleanly with Alembic `op.execute` raw SQL | Architecture Patterns, Pattern 5 | Migration may require additional steps if there are enum dependencies (FK, constraints); test migration on throwaway DB first |
| A2 | `pages.deleted_by` column is required per VAULT-08 ("soft delete with `deleted_at`, `deleted_by`, `delete_reason`") | Runtime State Inventory | If `deleted_by` is optional for Phase 1c (i.e., added in Phase 1d when there's a user context), migration may not need it now |
| A3 | The `page_versions` table also needs a `timeline` column (to snapshot the timeline separately from compiled_truth) | Runtime State Inventory | If timeline is reconstructed on demand rather than snapshotted, no migration needed for page_versions — planner should decide |
| A4 | OpenAPI pre-commit hook requires `SMARTCOPILOT_FERNET_KEY` and `JWT_SIGNING_KEY` in developer environment | Architecture Patterns, Pattern 8 | If `create_app()` is refactored to defer startup guards to a later point, the hook might work without real secrets |
| A5 | `watchdog` 6.0.0 (installed) is backward-compatible with the `>=4.0` requirement in CLAUDE.md | Standard Stack | If watchdog 6.x has API breaking changes vs 4.x, code examples need updating. CLAUDE.md says `>=4.0` which is satisfied. |

---

## Open Questions

1. **Does `page_versions` need a `timeline` column?**
   - What we know: `page_versions` currently has `compiled_truth`, `frontmatter`, `content_hash`. The compiled-truth/timeline split is new in Phase 1c.
   - What's unclear: Whether version snapshots should store the full raw content (then derive timeline from it) OR store `compiled_truth` + `timeline` separately.
   - Recommendation: Add `timeline TEXT NULLABLE` to `page_versions` in migration 0003 for symmetry with `pages`. Avoids needing a separate parse step to reconstruct history.

2. **Is `deleted_by` required in Phase 1c or deferred to Phase 1d?**
   - What we know: VAULT-08 says "soft delete with `deleted_at`, `deleted_by`, `delete_reason`". The page service in 1c implements soft delete. But `deleted_by` requires a user_id — the watchdog's soft delete would use `system_user_id`.
   - What's unclear: Whether `deleted_by` is needed NOW vs when Phase 1d REST routes add user-initiated deletes.
   - Recommendation: Add the column in migration 0003 (nullable, FK users.id). Watchdog uses `SYSTEM_USER_ID`. Phase 1d service layer uses `ctx.user_id`. Deferring it causes a second migration.

3. **Slug validation for filesystem-originated pages (watchdog)?**
   - What we know: VAULT-10 says `^[a-z0-9][a-z0-9\-]{0,127}$` for `remote=true` callers. Watchdog is `remote=False` (system context).
   - What's unclear: What slug validation applies when the watchdog indexes a file whose name violates the slug pattern? Drop it? Log a warning? Use a sanitized slug?
   - Recommendation: Watchdog sanitizes the filename to derive a slug (lowercase, replace invalid chars with `-`, truncate to 128). Log a warning if sanitization was needed. Never reject watchdog-originated pages silently.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| watchdog | IDX-01, IDX-02 | ✓ | 6.0.0 | — |
| xxhash | VAULT-07, IDX-03 | ✓ | 3.7.0 | — |
| python-frontmatter | VAULT-05 | ✓ | 1.1.0 | — |
| markdown-it-py | VAULT-05 (parsing) | ✓ | 4.0.0 | — (not used for wikilinks per D-discretion) |
| APScheduler 3.x | IDX-04 | ✓ | 3.11.2 | — |
| inotify (Linux kernel) | IDX-01 | ✓ | kernel 6.8.0 | watchdog PollingObserver (slower) |
| PostgreSQL + pgvector | VAULT-02, all | ✓ | via Docker | — |
| pre-commit | VAULT-11 | ✓ | in dev deps | — |
| docs/openapi.json parent dir | VAULT-11 | ✓ | docs/ exists | — |

**Missing dependencies with no fallback:** None — all required dependencies are available.

**Declarations needed:** `watchdog>=4.0`, `xxhash>=3.0`, `python-frontmatter>=1.1`, `markdown-it-py>=3.0` must be added to `server/requirements.txt` (currently absent, though installed via the project package).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 1.x |
| Config file | `server/pyproject.toml` (`asyncio_mode = "auto"`, `asyncio_default_fixture_loop_scope = "session"`) |
| Quick run command | `cd server && pytest app/tests/vault/ -x -q` |
| Full suite command | `cd server && pytest -ra` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VAULT-01 | Symlink escape rejected; `..` traversal rejected; private vault path correct | unit | `pytest app/tests/vault/test_paths.py -x` | ❌ Wave 0 |
| VAULT-02 | RLS isolation: page written by user A invisible to user B | integration | `pytest app/tests/vault/test_rls_pages.py -x` | ❌ Wave 0 |
| VAULT-03 | Shared vault read by any user; write policy `admin_only` enforced | integration | `pytest app/tests/vault/test_shared_vault.py -x` | ❌ Wave 0 |
| VAULT-04 | compiled_truth/timeline split correct for various body shapes | unit | `pytest app/tests/vault/test_parser.py -x` | ❌ Wave 0 |
| VAULT-04 | Timeline append-only hard reject via service | unit | `pytest app/tests/vault/test_pages_service.py::test_timeline_append_only -x` | ❌ Wave 0 |
| VAULT-05 | Frontmatter parsed; page type recognized from frontmatter.type | unit | `pytest app/tests/vault/test_parser.py::test_frontmatter_page_types -x` | ❌ Wave 0 |
| VAULT-06 | New pages default to `fleeting`; enum values match Zettelkasten set | integration | `pytest app/tests/vault/test_pages_service.py::test_note_type_defaults -x` | ❌ Wave 0 |
| VAULT-07 | xxhash64 computed from raw bytes; re-index skipped when hash unchanged | unit | `pytest app/tests/vault/test_parser.py::test_content_hash_dedup -x` | ❌ Wave 0 |
| VAULT-08 | Page version snapshot on every update; soft delete sets deleted_at + deleted_by + delete_reason | integration | `pytest app/tests/vault/test_pages_service.py::test_versioning -x` | ❌ Wave 0 |
| VAULT-09 | Wikilink resolution: private/shared routing, shortest-unique-path, alphabetically-first tie, forward refs pass | integration | `pytest app/tests/vault/test_wikilinks.py -x` | ❌ Wave 0 |
| VAULT-10 | Slug validation regex; remote=True callers get 422 on invalid slug | unit | `pytest app/tests/vault/test_paths.py::test_slug_validation -x` | ❌ Wave 0 |
| VAULT-11 | `docs/openapi.json` generated and matches live spec | integration | `pytest app/tests/vault/test_openapi.py -x` | ❌ Wave 0 |
| IDX-01 | Watchdog detects modification within 1 second (tmpdir fixture) | integration | `pytest app/tests/vault/test_watcher.py::test_file_detection_latency -x` | ❌ Wave 0 |
| IDX-02 | Thread→asyncio handoff uses run_coroutine_threadsafe (not call_soon_threadsafe) | unit | `pytest app/tests/vault/test_watcher.py::test_handoff_api -x` | ❌ Wave 0 |
| IDX-03 | Re-index skipped when content_hash unchanged; triggered when changed | integration | `pytest app/tests/vault/test_watcher.py::test_hash_dedup -x` | ❌ Wave 0 |
| IDX-04 | Reconciliation job detects drift and corrects: missing page added, deleted file soft-deleted | integration | `pytest app/tests/vault/test_reconcile.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `cd server && pytest app/tests/vault/ -x -q --no-header`
- **Per wave merge:** `cd server && pytest -ra`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `app/tests/vault/__init__.py` — package init
- [ ] `app/tests/vault/test_paths.py` — VAULT-01, VAULT-10 path safety + slug validation
- [ ] `app/tests/vault/test_parser.py` — VAULT-04, VAULT-05, VAULT-07 frontmatter/body-shape/hash
- [ ] `app/tests/vault/test_pages_service.py` — VAULT-04, VAULT-06, VAULT-08 service-level tests
- [ ] `app/tests/vault/test_wikilinks.py` — VAULT-09 resolution algorithm
- [ ] `app/tests/vault/test_rls_pages.py` — VAULT-02 RLS isolation for pages
- [ ] `app/tests/vault/test_shared_vault.py` — VAULT-03 shared vault policy
- [ ] `app/tests/vault/test_watcher.py` — IDX-01, IDX-02, IDX-03 watchdog behavior
- [ ] `app/tests/vault/test_reconcile.py` — IDX-04 reconciliation job
- [ ] `app/tests/vault/test_openapi.py` — VAULT-11 spec freshness
- [ ] `app/tests/vault/conftest.py` — shared fixtures (tmp vault directory, system_ctx, test vault records)

*(No new framework install needed — pytest-asyncio + testcontainers already in requirements-dev.txt)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Phase 1b handled auth; page service consumes OperationContext only |
| V3 Session Management | No | Phase 1b |
| V4 Access Control | Yes | RLS via `session_with_rls`; per-user vault path confinement; shared vault write policy |
| V5 Input Validation | Yes | Slug regex validation (VAULT-10); frontmatter YAML sanitization; wikilink regex |
| V6 Cryptography | No | No crypto in Phase 1c; content hashing is non-cryptographic (xxhash) — not a security primitive |
| V7 Error Handling | Yes | VaultParseError, VaultTimelineError, PermissionError must NOT leak internal paths in error messages |
| V13 API | Yes | Path traversal prevention (VAULT-01); slug confinement for remote=true callers |

### Known Threat Patterns for Vault Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal (`../../../etc/passwd` in slug or wikilink) | Tampering/EoP | `os.path.realpath` + `relative_to` guard; NEVER join user input to path without realpath |
| Symlink escape (`vaults/private/alice/evil -> /etc`) | EoP | `os.path.realpath` resolves symlinks before path check |
| Malicious YAML frontmatter (YAML bombs, arbitrary tags) | DoS/Tampering | `python-frontmatter` uses PyYAML `safe_load` internally — no arbitrary object construction |
| Timeline mutation via direct filesystem edit | Tampering | D-03: watchdog detects and records as `index_event` with warning; API path enforces via D-02 |
| Cross-user vault access via wikilink resolution | Information Disclosure | Wikilink resolver must scope DB query to user's vault_id + shared vault only; never query other private vaults |
| `_resolved_links` injection via user frontmatter | Tampering | Service strips `_resolved_links` from user-submitted frontmatter before persisting (Pitfall 8) |
| inotify exhaustion (DoS via many files) | DoS | Log warning on watch limit approach; document `max_user_watches` sysctl guidance |

---

## Sources

### Primary (HIGH confidence)

- `server/app/models/page.py` — actual page model schema [VERIFIED: codebase read]
- `server/app/models/page_version.py` — page_versions schema [VERIFIED: codebase read]
- `server/alembic/versions/0001_initial_schema.py` — confirmed missing `timeline` + `deleted_by` columns in pages table [VERIFIED: codebase read]
- `server/app/db_session.py` — `session_with_rls` pattern for non-HTTP callers [VERIFIED: codebase read]
- `server/app/scheduler/run.py` — APScheduler AsyncIOScheduler initialization pattern [VERIFIED: codebase read]
- `server/app/scheduler/jobs/prune_login_attempts.py` — APScheduler job registration pattern to replicate [VERIFIED: codebase read]
- `server/app/auth/context.py` — OperationContext shape, system_operation_context() [VERIFIED: codebase read]
- `server/app/vault/watcher.py` — confirmed stub; real impl lands here [VERIFIED: codebase read]
- `server/.pre-commit-config.yaml` — Ruff hooks present; OpenAPI hook absent [VERIFIED: codebase read]
- `server/pyproject.toml` — pytest config (asyncio_mode=auto, session loop scope) [VERIFIED: codebase read]
- `server/requirements.txt` — phase 1c deps NOT listed (watchdog/xxhash/frontmatter absent) [VERIFIED: codebase read]
- `pip3 show watchdog xxhash python-frontmatter markdown-it-py apscheduler` — all installed [VERIFIED: shell]
- `/proc/sys/fs/inotify/max_user_watches = 65536` [VERIFIED: shell]
- `.planning/phases/01c-vault-watchdog-indexer/01c-CONTEXT.md` — all D-01 through D-13 decisions [VERIFIED: codebase read]
- `.planning/phases/01b-auth-security-primitives/01b-CONTEXT.md` — OperationContext shape, session_with_rls pattern [VERIFIED: codebase read]

### Secondary (MEDIUM confidence)

- Python asyncio docs — `run_coroutine_threadsafe` is the correct primitive for thread → coroutine submission [CITED: docs.python.org/3/library/asyncio-task.html#asyncio.run_coroutine_threadsafe]
- Python-frontmatter README — uses PyYAML `safe_load` internally (safe from YAML bombs) [CITED: github.com/eyeseast/python-frontmatter]
- watchdog docs — `Observer()` is inotify on Linux; `PollingObserver()` is the fallback [CITED: python-watchdog.readthedocs.io]
- PostgreSQL docs — `ALTER TYPE ... ADD VALUE` is append-only; DROP VALUE is unsupported [CITED: postgresql.org/docs/16/sql-altertype.html]
- FastAPI TestClient docs — in-process HTTP client for OpenAPI generation without a running server [CITED: fastapi.tiangolo.com/tutorial/testing/]

### Tertiary (LOW confidence)

- A1 (Alembic enum rename-and-recreate) — standard community pattern but not tested in this specific project yet; verify in migration test run.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified installed via pip3 show
- Architecture: HIGH — all patterns derived from locked decisions (D-01 through D-13) and verified codebase inspection
- Schema gaps (timeline, deleted_by): HIGH — confirmed by reading migration 0001 and page.py model directly
- Pitfalls: HIGH (path safety, enum migration) / MEDIUM (watchdog shutdown, OpenAPI hook env vars)
- Test map: MEDIUM — test file names and command patterns are proposed; exact test structure is planner's call

**Research date:** 2026-05-08
**Valid until:** 2026-06-08 (30 days; stable stack)
