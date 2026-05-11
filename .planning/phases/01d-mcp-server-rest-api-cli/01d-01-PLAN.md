---
phase: 01d
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - server/alembic/versions/0004_phase_1d_search_vector.py
  - server/app/services/pages.py
  - server/app/services/capabilities.py
  - server/app/tests/vault/test_pages_service.py
  - server/app/tests/vault/test_search_fts.py
  - server/app/tests/vault/test_pages_history.py
  - server/app/tests/vault/test_capabilities.py
autonomous: true
requirements:
  - REST-05
  - REST-06

must_haves:
  truths:
    - "Alembic 0004 adds pages.search_vector tsvector GENERATED ALWAYS using frontmatter->>'title' || compiled_truth"
    - "GIN index ix_pages_search_vector exists on pages.search_vector"
    - "search_pages_fts returns ranked SearchHit list with snippet, score, matched_fields"
    - "search_pages_fts uses websearch_to_tsquery with plainto_tsquery fallback"
    - "list_pages, get_page_history, get_page_diff, revert_page, get_backlinks_for_page, vault_stats helpers exist in services/pages.py"
    - "vault_health exists in services/pages.py (db_ok, fernet_ok, watchdog_alive=None)"
    - "services/capabilities.py exposes get_capabilities() returning the Phase 1d capability dict"
    - "All new service helpers are transport-agnostic (no FastAPI imports)"
  artifacts:
    - path: "server/alembic/versions/0004_phase_1d_search_vector.py"
      provides: "Migration 0004 — tsvector column + GIN index"
      contains: "search_vector tsvector"
    - path: "server/app/services/pages.py"
      provides: "Phase 1d service helpers: search_pages_fts, list_pages, get_page_history, get_page_diff, revert_page, get_backlinks_for_page, vault_stats, vault_health"
      contains: "async def search_pages_fts"
    - path: "server/app/services/capabilities.py"
      provides: "get_capabilities() — single source of truth for capability_discovery + GET /api/v1/capabilities (REST-05)"
      contains: "def get_capabilities"
    - path: "server/app/tests/vault/test_search_fts.py"
      provides: "Integration tests proving FTS ranks compiled_truth vs frontmatter title hits, applies vault_id RLS"
    - path: "server/app/tests/vault/test_pages_history.py"
      provides: "Integration tests for get_page_history, get_page_diff, revert_page using page_versions snapshots"
  key_links:
    - from: "server/app/services/pages.py"
      to: "server/alembic/versions/0004_phase_1d_search_vector.py"
      via: "search_pages_fts SELECT references the new search_vector column added by 0004"
      pattern: "search_vector @@ websearch_to_tsquery"
    - from: "server/app/services/pages.py"
      to: "server/app/models/page_version.py"
      via: "history/diff/revert query the page_versions table populated by upsert_page in Phase 1c"
      pattern: "from app.models.page_version import PageVersion"
---

<objective>
Build the Phase 1d service-layer foundation that every later plan depends on:

1. Alembic migration **0004** adding `pages.search_vector` (tsvector, GENERATED ALWAYS) + GIN index, per D-03 — the column expression uses `frontmatter->>'title'` because the Page model has NO bare `title` column (verified in Pattern Map / `server/app/models/page.py`).
2. Extend `server/app/services/pages.py` with the transport-agnostic helpers consumed by both MCP tools (Plan 02) and REST routes (Plan 03): `search_pages_fts`, `list_pages`, `get_page_history`, `get_page_diff`, `revert_page`, `get_backlinks_for_page`, `vault_stats`, `vault_health`.
3. Create `server/app/services/capabilities.py` exposing the single `get_capabilities()` function used by both the `capability_discovery` MCP tool and `GET /api/v1/capabilities` REST endpoint (REST-05 parity).
4. Real integration tests against PostgreSQL (testcontainers) covering the new helpers — no service stubs, no DB mocks.

Purpose: Plans 02–05 cannot start without these helpers — they are the shared kernel. Doing them first eliminates the "scavenger hunt" anti-pattern; downstream plans receive concrete signatures via the must_haves contract.

Output: Migration 0004 + extended `services/pages.py` + new `services/capabilities.py` + 2 new test files.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/01d-mcp-rest-api-cli/01d-CONTEXT.md
@.planning/phases/01d-mcp-rest-api-cli/01d-PATTERNS.md
@CLAUDE.md
@server/app/services/pages.py
@server/app/models/page.py
@server/app/models/page_version.py
@server/alembic/versions/0003_phase_1c_vault.py

<interfaces>
<!-- Existing service signatures the new helpers must compose with. -->
<!-- From server/app/services/pages.py (Phase 1c — DO NOT change these): -->
```python
class PageNotFound(Exception): ...
class TimelineViolation(Exception): ...
class SharedVaultWriteDenied(PermissionError): ...

async def upsert_page(session, ctx, *, vault_id, slug, parsed, enforce_timeline=True) -> Page: ...
async def write_page(session, ctx, *, slug, raw_content, vault_id, shared_vault_id=None) -> Page: ...
async def read_page(session, *, vault_id, slug) -> Page: ...
async def soft_delete_page(session, ctx, *, page_id, reason="file_deleted") -> None: ...
async def append_timeline(session, ctx, *, vault_id, slug, entry) -> Page: ...
```

<!-- From server/app/auth/context.py — context type used in every service signature: -->
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
```

<!-- From server/app/models/page.py — there is NO `title` column. Title lives in frontmatter JSONB: -->
```python
class Page(TimestampMixin, Base):
    __tablename__ = "pages"
    id: Mapped[uuid.UUID]
    vault_id: Mapped[uuid.UUID]
    slug: Mapped[str]                  # 256 chars
    type: Mapped[str]                  # page_type_enum
    note_type: Mapped[str]             # page_note_type_enum (default 'fleeting')
    frontmatter: Mapped[dict]          # JSONB — title comes from frontmatter['title']
    compiled_truth: Mapped[str | None]
    timeline: Mapped[str | None]
    content_hash: Mapped[str]
    enrichment_hash: Mapped[str | None]
    deleted_at: Mapped[datetime | None]
    delete_reason: Mapped[str | None]
    deleted_by: Mapped[uuid.UUID | None]
    # NO title column. NO updated_at as Mapped — comes from TimestampMixin.
```

<!-- From server/app/models/page_version.py — populated by Phase 1c upsert_page. -->
```python
class PageVersion(Base):
    __tablename__ = "page_versions"
    id: Mapped[uuid.UUID]
    page_id: Mapped[uuid.UUID]         # FK pages.id ON DELETE CASCADE
    version: Mapped[int]               # monotonically increasing
    frontmatter: Mapped[dict]          # JSONB
    compiled_truth: Mapped[str | None]
    timeline: Mapped[str | None]
    content_hash: Mapped[str]
    created_at: Mapped[datetime]       # server_default now()
```

<!-- Service-layer return-type contract (consumed verbatim by Plans 02 + 03): -->
```python
# server/app/services/pages.py — NEW dataclasses. ALSO: zero FastAPI imports.
from dataclasses import dataclass, field

@dataclass(frozen=True, slots=True)
class SearchHit:
    page_id: uuid.UUID
    slug: str
    title: str | None
    note_type: str
    score: float
    snippet: str
    matched_fields: list[str]          # subset of {"title", "compiled_truth", "timeline"}
    updated_at: datetime
    chunk_hits: list = field(default_factory=list)   # always [] in Phase 1d (D-02)

@dataclass(frozen=True, slots=True)
class PageVersionSummary:
    version: int
    content_hash: str
    created_at: datetime

@dataclass(frozen=True, slots=True)
class PageDiff:
    from_version: int
    to_version: int
    compiled_truth_diff: str           # unified diff
    timeline_diff: str                 # unified diff

@dataclass(frozen=True, slots=True)
class BacklinkHit:
    page_id: uuid.UUID
    slug: str
    title: str | None

@dataclass(frozen=True, slots=True)
class VaultStats:
    page_count: int
    deleted_page_count: int
    total_compiled_truth_bytes: int
    last_indexed_at: datetime | None

@dataclass(frozen=True, slots=True)
class VaultHealth:
    db_ok: bool
    fernet_ok: bool
    watchdog_alive: bool | None        # None = unknown (pg_notify recency check, see Plan 04)
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Alembic migration 0004 — pages.search_vector + GIN index</name>
  <files>server/alembic/versions/0004_phase_1d_search_vector.py, server/app/tests/vault/test_search_fts.py</files>
  <read_first>
    - server/alembic/versions/0003_phase_1c_vault.py (exact migration header + raw `op.execute()` style)
    - server/app/models/page.py (confirm: NO `title` column — title lives in frontmatter JSONB)
    - server/app/tests/conftest.py (testcontainer + Alembic-against-test-DB pattern)
    - server/app/tests/vault/conftest.py (seed_vault, seed_user_for_vault fixtures)
  </read_first>
  <behavior>
    - Test 1: After running Alembic upgrade to head, `pages.search_vector` column exists with type `tsvector` and GIN index `ix_pages_search_vector` is present.
    - Test 2: Inserting a page with frontmatter `{"title": "Acme Corporation"}` and compiled_truth `"founded 2010"` makes `search_vector @@ websearch_to_tsquery('english', 'acme')` return TRUE.
    - Test 3: Inserting a page with empty frontmatter (`'{}'::jsonb`) and `compiled_truth = ''` produces a non-NULL search_vector (GENERATED ALWAYS — never NULL).
    - Test 4: A page in vault A is invisible to a `search_vector @@ websearch_to_tsquery(...)` query that filters `WHERE vault_id = <vault B>` (RLS column filter still applies).
    - Test 5: Migration downgrade drops both the index and the column cleanly.
  </behavior>
  <action>
Create `server/alembic/versions/0004_phase_1d_search_vector.py` matching the EXACT structure of `0003_phase_1c_vault.py` (header docstring, `revision: str = "0004"`, `down_revision: str | None = "0003"`, `branch_labels`, `depends_on`).

`upgrade()` MUST execute these two `op.execute()` calls (raw SQL — SQLAlchemy has no ORM abstraction for `GENERATED ALWAYS AS ... STORED`):

```python
op.execute(
    """
    ALTER TABLE pages
    ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (
            to_tsvector(
                'english',
                coalesce(frontmatter->>'title', '') || ' ' ||
                coalesce(compiled_truth, '')
            )
        ) STORED
    """
)
op.execute("CREATE INDEX ix_pages_search_vector ON pages USING GIN (search_vector)")
```

The column expression MUST use `frontmatter->>'title'` (NOT a bare `title` column). This is the corrected expression flagged in `01d-PATTERNS.md` line 641 — the Pattern Map verified that `Page` has no `title` column.

`downgrade()` MUST drop in reverse order:
```python
op.execute("DROP INDEX IF EXISTS ix_pages_search_vector")
op.execute("ALTER TABLE pages DROP COLUMN IF EXISTS search_vector")
```

Then create `server/app/tests/vault/test_search_fts.py` with the 5 behavior tests above. Use the existing `seed_vault` and `seed_user_for_vault` fixtures from `server/app/tests/vault/conftest.py`. Tests use raw SQL (`text()`) — service-layer search helper is added in Task 2.

Pre-flight check before writing migration: run `grep -n 'title' server/app/models/page.py` — if grep returns lines containing `Mapped[str] = mapped_column(... title ...)`, STOP and ask for clarification (the model would have a bare title column, contradicting the Pattern Map). Expected: zero matches for a `title` Mapped column; only frontmatter dict references.
  </action>
  <verify>
    <automated>cd server && SMARTCOPILOT_FERNET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())") JWT_SIGNING_KEY=test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa pytest -x app/tests/vault/test_search_fts.py -v</automated>
  </verify>
  <acceptance_criteria>
    - `grep -E "search_vector tsvector" server/alembic/versions/0004_phase_1d_search_vector.py | wc -l` returns >= 1
    - `grep -E "frontmatter->>'title'" server/alembic/versions/0004_phase_1d_search_vector.py | wc -l` returns >= 1
    - `grep -E "ix_pages_search_vector" server/alembic/versions/0004_phase_1d_search_vector.py | wc -l` returns >= 2 (CREATE + DROP)
    - `grep -c "revision: str = \"0004\"" server/alembic/versions/0004_phase_1d_search_vector.py` returns 1
    - `grep -c "down_revision: str | None = \"0003\"" server/alembic/versions/0004_phase_1d_search_vector.py` returns 1
    - All 5 tests in `server/app/tests/vault/test_search_fts.py` pass against the testcontainer-managed PostgreSQL with Alembic upgrade to head succeeding.
    - `grep -v '^#' server/app/models/page.py | grep -c 'title.*mapped_column'` returns 0 (proves no bare title column added).
  </acceptance_criteria>
  <done>Migration 0004 ships and applies cleanly; FTS column queryable with `websearch_to_tsquery`; new tests pass.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Extend services/pages.py with FTS + history + diff + revert + backlinks + stats + health</name>
  <files>server/app/services/pages.py, server/app/tests/vault/test_pages_service.py, server/app/tests/vault/test_pages_history.py</files>
  <read_first>
    - server/app/services/pages.py (full file — append, do not rewrite)
    - server/app/models/page.py + page_version.py (column types, constraints)
    - server/app/auth/context.py (OperationContext shape)
    - server/app/tests/vault/test_pages_service.py (existing test conventions)
    - server/app/db_session.py (session_with_rls discipline — services NEVER call this; callers do)
  </read_first>
  <behavior>
    - search_pages_fts: query "acme" returns hits ranked by `ts_rank(search_vector, websearch_to_tsquery('english', :q))` desc; deleted pages excluded; matched_fields populated correctly when title-only hit vs compiled_truth-only hit.
    - search_pages_fts: empty query string (`""`) raises `ValueError`; limit clamped to <=100 server-side.
    - search_pages_fts: when `websearch_to_tsquery` returns empty parse, falls back to `plainto_tsquery` (assert by passing `"&&&"` which `websearch_to_tsquery` parses as empty in PG).
    - list_pages: returns Page list filtered by vault_id, deleted_at IS NULL, ordered by `updated_at` desc, paginated by `limit/offset`.
    - get_page_history: returns `list[PageVersionSummary]` ordered by `version` DESC for a given page_id.
    - get_page_diff: takes (page_id, from_version, to_version) → returns `PageDiff` with unified diffs of compiled_truth and timeline.
    - get_page_diff: raises `PageNotFound` when either version row is missing.
    - revert_page: copies a target `page_versions` row into a new upsert (calls upsert_page with enforce_timeline=False) — page now reflects historic content + a new max version snapshot.
    - get_backlinks_for_page: scans `frontmatter->'_resolved_links'` JSONB array for entries whose `page_id` matches the target page; returns `list[BacklinkHit]` (empty list is valid).
    - vault_stats: returns counts of live/deleted pages, sum of compiled_truth byte length, and max(updated_at).
    - vault_health: returns `db_ok=True` after a successful `SELECT 1`; `fernet_ok` calls `app.encryption.fernet()` and returns False if FernetKeyMissing; `watchdog_alive=None` (Plan 04 will compute by querying recent index_events / pg_notify).
  </behavior>
  <action>
APPEND (do not rewrite) the following to `server/app/services/pages.py`:

1. Imports at the top of the file (merge with existing — DO NOT duplicate):
```python
import difflib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from app.encryption import FernetKeyMissing, fernet
```

2. Frozen dataclasses (verbatim from the `<interfaces>` block above): `SearchHit`, `PageVersionSummary`, `PageDiff`, `BacklinkHit`, `VaultStats`, `VaultHealth`.

3. New service helpers — every signature matches `(session: AsyncSession, ctx: OperationContext, *, ...)` and returns a domain object. ZERO FastAPI imports. ZERO HTTPException. Raise existing domain exceptions only (`PageNotFound`).

```python
async def search_pages_fts(
    session: AsyncSession,
    ctx: OperationContext,                  # noqa: ARG001 — accepted for future scoping; vault_id passed explicitly
    *,
    vault_id: uuid.UUID,
    query: str,
    limit: int = 20,
    namespace: Literal["private", "shared", "all"] = "private",   # noqa: ARG001 — Phase 1d uses vault_id directly
) -> list[SearchHit]:
    if not query or not query.strip():
        raise ValueError("query must be non-empty")
    limit = max(1, min(int(limit), 100))

    # D-01: try websearch_to_tsquery; fall back to plainto_tsquery if it parses to empty.
    sql = """
        WITH q AS (
            SELECT
                COALESCE(NULLIF(websearch_to_tsquery('english', :q), ''::tsquery),
                         plainto_tsquery('english', :q)) AS tsq
        )
        SELECT
            p.id, p.slug, p.frontmatter->>'title' AS title, p.note_type, p.updated_at,
            ts_rank(p.search_vector, q.tsq) AS score,
            ts_headline(
                'english',
                COALESCE(p.compiled_truth, ''),
                q.tsq,
                'MaxFragments=1,MaxWords=20'
            ) AS snippet,
            (to_tsvector('english', COALESCE(p.frontmatter->>'title', '')) @@ q.tsq) AS title_match,
            (to_tsvector('english', COALESCE(p.compiled_truth, '')) @@ q.tsq) AS truth_match
        FROM pages p, q
        WHERE p.vault_id = :vid
          AND p.deleted_at IS NULL
          AND p.search_vector @@ q.tsq
        ORDER BY score DESC, p.updated_at DESC
        LIMIT :lim
    """
    rows = (await session.execute(text(sql), {"q": query, "vid": str(vault_id), "lim": limit})).mappings().all()
    hits: list[SearchHit] = []
    for r in rows:
        matched: list[str] = []
        if r["title_match"]:
            matched.append("title")
        if r["truth_match"]:
            matched.append("compiled_truth")
        hits.append(SearchHit(
            page_id=r["id"], slug=r["slug"], title=r["title"], note_type=r["note_type"],
            score=float(r["score"]), snippet=r["snippet"] or "",
            matched_fields=matched, updated_at=r["updated_at"],
        ))
    return hits


async def list_pages(
    session: AsyncSession, ctx: OperationContext,                  # noqa: ARG001
    *, vault_id: uuid.UUID, limit: int = 50, offset: int = 0,
) -> list[Page]:
    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))
    rows = await session.execute(
        select(Page)
        .where(Page.vault_id == vault_id, Page.deleted_at.is_(None))
        .order_by(Page.updated_at.desc())
        .limit(limit).offset(offset)
    )
    return list(rows.scalars().all())


async def get_page_history(
    session: AsyncSession, ctx: OperationContext,                  # noqa: ARG001
    *, page_id: uuid.UUID,
) -> list[PageVersionSummary]:
    rows = await session.execute(
        select(PageVersion.version, PageVersion.content_hash, PageVersion.created_at)
        .where(PageVersion.page_id == page_id)
        .order_by(PageVersion.version.desc())
    )
    return [PageVersionSummary(version=v, content_hash=h, created_at=ts) for v, h, ts in rows.all()]


async def get_page_diff(
    session: AsyncSession, ctx: OperationContext,                  # noqa: ARG001
    *, page_id: uuid.UUID, from_version: int, to_version: int,
) -> PageDiff:
    rows = (await session.execute(
        select(PageVersion).where(
            PageVersion.page_id == page_id,
            PageVersion.version.in_([from_version, to_version]),
        )
    )).scalars().all()
    if len(rows) != 2:
        raise PageNotFound(f"missing one of versions {from_version}, {to_version} for page {page_id}")
    by_v = {r.version: r for r in rows}
    a, b = by_v[from_version], by_v[to_version]
    truth_diff = "\n".join(difflib.unified_diff(
        (a.compiled_truth or "").splitlines(), (b.compiled_truth or "").splitlines(),
        fromfile=f"v{from_version}", tofile=f"v{to_version}", lineterm="",
    ))
    tl_diff = "\n".join(difflib.unified_diff(
        (a.timeline or "").splitlines(), (b.timeline or "").splitlines(),
        fromfile=f"v{from_version}", tofile=f"v{to_version}", lineterm="",
    ))
    return PageDiff(from_version=from_version, to_version=to_version,
                    compiled_truth_diff=truth_diff, timeline_diff=tl_diff)


async def revert_page(
    session: AsyncSession, ctx: OperationContext,
    *, vault_id: uuid.UUID, slug: str, target_version: int,
) -> Page:
    page = await read_page(session, vault_id=vault_id, slug=slug)
    target = (await session.execute(
        select(PageVersion).where(
            PageVersion.page_id == page.id, PageVersion.version == target_version
        )
    )).scalar_one_or_none()
    if target is None:
        raise PageNotFound(f"version {target_version} not found for page {slug}")
    from app.vault.parser import ParsedPage
    parsed = ParsedPage(
        frontmatter=dict(target.frontmatter),
        compiled_truth=target.compiled_truth or "",
        timeline=target.timeline or "",
        body_shape=None,                   # type: ignore[arg-type]  # not needed for upsert
        content_hash=target.content_hash,
    )
    return await upsert_page(
        session, ctx, vault_id=vault_id, slug=slug, parsed=parsed,
        enforce_timeline=False,            # revert is service-controlled; bypass D-02
    )


async def get_backlinks_for_page(
    session: AsyncSession, ctx: OperationContext,                  # noqa: ARG001
    *, vault_id: uuid.UUID, target_page_id: uuid.UUID,
) -> list[BacklinkHit]:
    # _resolved_links is a JSONB array of dicts containing {"page_id": "<uuid>"} when resolved.
    # Query: find all live pages in the same vault whose frontmatter._resolved_links contains a
    # match with page_id == target_page_id.
    sql = """
        SELECT p.id, p.slug, p.frontmatter->>'title' AS title
        FROM pages p
        WHERE p.vault_id = :vid
          AND p.deleted_at IS NULL
          AND EXISTS (
              SELECT 1
              FROM jsonb_array_elements(
                       COALESCE(p.frontmatter->'_resolved_links', '[]'::jsonb)
                   ) AS link
              WHERE link->>'page_id' = :tpid
          )
        ORDER BY p.slug ASC
    """
    rows = (await session.execute(text(sql), {"vid": str(vault_id), "tpid": str(target_page_id)})).mappings().all()
    return [BacklinkHit(page_id=r["id"], slug=r["slug"], title=r["title"]) for r in rows]


async def vault_stats(
    session: AsyncSession, ctx: OperationContext,                  # noqa: ARG001
    *, vault_id: uuid.UUID,
) -> VaultStats:
    sql = """
        SELECT
            COUNT(*) FILTER (WHERE deleted_at IS NULL) AS live,
            COUNT(*) FILTER (WHERE deleted_at IS NOT NULL) AS deleted,
            COALESCE(SUM(LENGTH(COALESCE(compiled_truth, ''))) FILTER (WHERE deleted_at IS NULL), 0) AS bytes,
            MAX(updated_at) FILTER (WHERE deleted_at IS NULL) AS last_indexed
        FROM pages
        WHERE vault_id = :vid
    """
    row = (await session.execute(text(sql), {"vid": str(vault_id)})).mappings().one()
    return VaultStats(
        page_count=int(row["live"]), deleted_page_count=int(row["deleted"]),
        total_compiled_truth_bytes=int(row["bytes"]),
        last_indexed_at=row["last_indexed"],
    )


async def vault_health(
    session: AsyncSession, ctx: OperationContext,                  # noqa: ARG001
) -> VaultHealth:
    db_ok = False
    try:
        await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:                       # noqa: BLE001 — degraded health, not a crash
        db_ok = False
    fernet_ok = True
    try:
        fernet()
    except FernetKeyMissing:
        fernet_ok = False
    return VaultHealth(db_ok=db_ok, fernet_ok=fernet_ok, watchdog_alive=None)
```

EXTEND the existing `server/app/tests/vault/test_pages_service.py` with new tests that exercise list_pages, get_page_history, get_page_diff, get_backlinks_for_page, vault_stats, vault_health.

CREATE `server/app/tests/vault/test_pages_history.py` with focused tests for `revert_page` (write v1 → write v2 → revert to v1 → assert content matches v1 and a v3 row was created).

ALL tests use the existing `seed_vault` / `seed_user_for_vault` fixtures from `server/app/tests/vault/conftest.py` and run `session_with_rls(ctx)` (NEVER raw `async_session_factory()`).
  </action>
  <verify>
    <automated>cd server && SMARTCOPILOT_FERNET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())") JWT_SIGNING_KEY=test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa pytest -x app/tests/vault/test_pages_service.py app/tests/vault/test_pages_history.py app/tests/vault/test_search_fts.py -v</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "^async def search_pages_fts" server/app/services/pages.py` == 1
    - `grep -c "^async def list_pages" server/app/services/pages.py` == 1
    - `grep -c "^async def get_page_history" server/app/services/pages.py` == 1
    - `grep -c "^async def get_page_diff" server/app/services/pages.py` == 1
    - `grep -c "^async def revert_page" server/app/services/pages.py` == 1
    - `grep -c "^async def get_backlinks_for_page" server/app/services/pages.py` == 1
    - `grep -c "^async def vault_stats" server/app/services/pages.py` == 1
    - `grep -c "^async def vault_health" server/app/services/pages.py` == 1
    - `grep -c "websearch_to_tsquery" server/app/services/pages.py` >= 1
    - `grep -c "plainto_tsquery" server/app/services/pages.py` >= 1
    - `grep -E "from fastapi|import fastapi|HTTPException|APIRouter" server/app/services/pages.py | wc -l` returns 0 (transport-agnostic invariant per REST-06)
    - All tests in `test_search_fts.py`, `test_pages_history.py`, and the extended `test_pages_service.py` pass
    - `cd server && ruff check app/services/pages.py` exits 0
  </acceptance_criteria>
  <done>Eight new service helpers ship in `services/pages.py`, all transport-agnostic, all backed by passing integration tests against PostgreSQL.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: services/capabilities.py — single source of truth for REST-05 parity</name>
  <files>server/app/services/capabilities.py, server/app/tests/vault/test_capabilities.py</files>
  <read_first>
    - server/app/routes/health.py (template for trivial transport-agnostic helper)
    - .planning/phases/01d-mcp-rest-api-cli/01d-CONTEXT.md (D-15 capabilities payload — search "Claude's Discretion")
  </read_first>
  <behavior>
    - get_capabilities() returns the exact dict: `{"transports": ["stdio", "http"], "ingestion_limits": {}, "clipboard_available": False, "phase": "1d"}`
    - Function is synchronous (no I/O, no DB) and importable without FastAPI being installed.
    - Module imports nothing from fastapi/starlette.
  </behavior>
  <action>
Create `server/app/services/capabilities.py` with:

```python
"""Capability discovery — REST-05 / D-15 parity.

Single source of truth for the capability payload. Imported by:
  - server/app/mcp/tools/capability.py (capability_discovery MCP tool — Plan 02)
  - server/app/routes/vault.py     (GET /api/v1/capabilities — Plan 03)

NO FastAPI imports — this module is transport-agnostic per REST-06.
"""
from __future__ import annotations


def get_capabilities() -> dict:
    """Phase 1d capability payload (REST-05).

    transports         — Phase 1d wires both MCP transports.
    ingestion_limits   — empty in Phase 1d (ingest tools are stubs; D-04, D-05).
    clipboard_available — False; client-side feature, deferred to Phase 8.
    phase               — coarse phase identifier consumed by clients for
                          feature gating during the 1.x rollout.
    """
    return {
        "transports": ["stdio", "http"],
        "ingestion_limits": {},
        "clipboard_available": False,
        "phase": "1d",
    }
```

Create `server/app/tests/vault/test_capabilities.py`:

```python
"""Unit tests for services/capabilities.py — REST-05 parity (Plan 01)."""
from __future__ import annotations

import pytest

from app.services.capabilities import get_capabilities


@pytest.mark.unit
def test_get_capabilities_returns_phase_1d_payload() -> None:
    payload = get_capabilities()
    assert payload == {
        "transports": ["stdio", "http"],
        "ingestion_limits": {},
        "clipboard_available": False,
        "phase": "1d",
    }


@pytest.mark.unit
def test_get_capabilities_does_not_import_fastapi() -> None:
    import app.services.capabilities as cap_module

    src = open(cap_module.__file__).read()
    assert "fastapi" not in src.lower()
    assert "starlette" not in src.lower()
```
  </action>
  <verify>
    <automated>cd server && pytest -x app/tests/vault/test_capabilities.py -v</automated>
  </verify>
  <acceptance_criteria>
    - File `server/app/services/capabilities.py` exists.
    - `grep -c "def get_capabilities" server/app/services/capabilities.py` == 1
    - `grep -E "fastapi|starlette" server/app/services/capabilities.py | wc -l` returns 0
    - Both tests pass.
  </acceptance_criteria>
  <done>get_capabilities() ships in services layer, importable by both MCP tools (Plan 02) and REST routes (Plan 03).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Alembic migration → live DB | Schema-changing DDL must be safe to roll back |
| FTS query input (`:q`) → tsquery parser | Plan 03/02 will pass user-supplied query strings — Task 2 already uses parameterised SQL bindings, never string concatenation |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-01d01-01 | Tampering | Migration 0004 | mitigate | Use parameterised `op.execute()` raw SQL; no env interpolation. Migration is data-preserving (column add only); no UPDATE/DELETE on existing rows. |
| T-01d01-02 | Information Disclosure | search_pages_fts | mitigate | Caller passes explicit `vault_id`; SQL filters `WHERE vault_id = :vid AND deleted_at IS NULL`. RLS enforced upstream by `session_with_rls`. Tests in test_search_fts.py prove cross-vault leak does not occur. |
| T-01d01-03 | Injection | search_pages_fts query parameter | mitigate | All bind parameters use SQLAlchemy `text(:bind)` placeholders. The `websearch_to_tsquery` PG function is itself injection-safe. No `f"..."` SQL construction anywhere in the new code. Verified by `grep -E 'f"SELECT|f"WHERE|f"INSERT' server/app/services/pages.py` returning 0. |
| T-01d01-04 | DoS | revert_page on enormous version | accept | revert_page calls upsert_page which already enforces normal size limits. No new DoS surface. |
| T-01d01-05 | Information Disclosure | get_backlinks_for_page leaking cross-vault refs | mitigate | SQL is `WHERE p.vault_id = :vid` — backlink scan never crosses vault boundaries. |
| T-01d01-06 | Repudiation | revert_page bypasses timeline enforcement | accept | revert_page is service-controlled (never called from `remote=True` callers in Phase 1d — Plan 02/03 will gate via `ctx.role == 'admin'` for the brain.revert tool). Audit logging deferred to Phase 6 (OBS-03). |
</threat_model>

<verification>
After all tasks complete:
1. `cd server && pytest -x app/tests/vault/ -v` — all vault tests pass (existing + new).
2. `cd server && ruff check app/services/pages.py app/services/capabilities.py app/tests/vault/test_search_fts.py app/tests/vault/test_pages_history.py app/tests/vault/test_capabilities.py` exits 0.
3. `grep -E "from fastapi|import fastapi" server/app/services/` returns 0 results across the services package.
4. `cd server && alembic upgrade head` succeeds against a fresh DB; `cd server && alembic downgrade -1` followed by `alembic upgrade head` also succeeds (migration is reversible).
</verification>

<success_criteria>
- Migration 0004 ships and is reversible.
- `services/pages.py` exposes 8 new transport-agnostic helpers backed by tests.
- `services/capabilities.py` exposes `get_capabilities()`.
- All Phase 1c tests still pass — no regressions to existing service signatures.
- Plan 02 (MCP tools) and Plan 03 (REST routes) can import these helpers and start work in parallel.
</success_criteria>

<output>
After completion, create `.planning/phases/01d-mcp-rest-api-cli/01d-01-SUMMARY.md` with: artifacts, key signatures added, test-pass count, any deviations from the action.
</output>
