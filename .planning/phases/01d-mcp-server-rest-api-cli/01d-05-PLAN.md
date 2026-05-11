---
phase: 01d
plan: 05
type: execute
wave: 3
depends_on:
  - "01d-01"
  - "01d-02"
files_modified:
  - server/app/cli/main.py
  - server/app/cli/mcp_token.py
  - server/app/cli/page.py
  - server/app/cli/doctor.py
  - server/app/cli/check_resolvable.py
  - server/app/cli/mcp_serve.py
  - server/app/cli/reconcile.py
  - server/app/cli/stats.py
  - server/app/tests/integration/test_cli_page.py
  - server/app/tests/integration/test_cli_doctor.py
  - server/app/tests/integration/test_cli_check_resolvable.py
  - server/app/tests/integration/test_cli_mcp_serve.py
  - server/app/tests/integration/test_cli_reconcile.py
autonomous: true
requirements:
  - CLI-01
  - CLI-02
  - CLI-03

must_haves:
  truths:
    - "smartcopilot mcp serve --stdio invokes app.mcp.server.main_stdio (no NotImplementedError)"
    - "smartcopilot mcp serve --http invokes app.mcp.server.main_http with --port flag wired"
    - "smartcopilot doctor reports Fernet key status, inotify watch limit, CORS config status, MCP token storage mode (D-14)"
    - "smartcopilot check-resolvable returns exit 0 with 'no skills directory' message when empty (Phase 1 invariant)"
    - "smartcopilot page get/put/delete/list/search call services/pages.py via session_with_rls"
    - "smartcopilot reconcile invokes the Phase 1c reconciliation job entry point"
    - "smartcopilot stats returns vault page count + deleted count + bytes (calls services/pages.vault_stats)"
    - "All new subcommands use system_operation_context or per-user OperationContext (transport='cli', remote=False) — never raw async_session_factory"
    - "cli/main.py registers all new subparsers; calling smartcopilot --help lists every command"
  artifacts:
    - path: "server/app/cli/main.py"
      provides: "Updated argparse entry point registering 7 new subparsers"
      contains: "page_cmd.add_subparser"
    - path: "server/app/cli/mcp_token.py"
      provides: "Extended `mcp` parser to register `serve` subcommand alongside existing `token` (Phase 1d edit only)"
    - path: "server/app/cli/page.py"
      provides: "smartcopilot page get/put/delete/list/search subcommands"
    - path: "server/app/cli/doctor.py"
      provides: "smartcopilot doctor — D-14 health smoke (CLI-02)"
    - path: "server/app/cli/check_resolvable.py"
      provides: "smartcopilot check-resolvable — empty skills tree passes (CLI-03)"
    - path: "server/app/cli/mcp_serve.py"
      provides: "smartcopilot mcp serve --stdio|--http --port — dispatches to mcp.server entrypoints"
    - path: "server/app/cli/reconcile.py"
      provides: "smartcopilot reconcile [--deep] — runs the Phase 1c reconciliation job synchronously"
    - path: "server/app/cli/stats.py"
      provides: "smartcopilot stats — vault page-count summary"
  key_links:
    - from: "server/app/cli/page.py"
      to: "server/app/services/pages.py"
      via: "Each subcommand calls a service helper inside session_with_rls(ctx)"
      pattern: "from app.services.pages import"
    - from: "server/app/cli/mcp_serve.py"
      to: "server/app/mcp/server.py"
      via: "Dispatches to main_stdio / main_http"
      pattern: "from app.mcp import server as mcp_server"
    - from: "server/app/cli/reconcile.py"
      to: "server/app/scheduler/jobs/reconcile_vault.py"
      via: "Imports the reconcile entry function (Phase 1c)"
      pattern: "from app.scheduler.jobs.reconcile_vault import"
---

<objective>
Expand the `smartcopilot` CLI binary with all subcommands listed in D-13:

- `smartcopilot mcp serve [--stdio|--http] [--port N]` — launch the MCP server
- `smartcopilot doctor` — D-14 health smoke (CLI-02)
- `smartcopilot check-resolvable` — skills-tree validator; empty tree passes cleanly (CLI-03)
- `smartcopilot reconcile [--deep]` — run vault reconciliation synchronously
- `smartcopilot page get/put/delete/list/search` — vault CRUD over the service layer
- `smartcopilot stats` — vault summary

Existing Phase 1b subcommands (`user create`, `mcp token create/list/revoke`, `provider_key set`) carry forward unchanged.

Purpose: CLI-01..CLI-03 deliverable. Plan 06 acceptance test exercises `smartcopilot mcp serve --stdio` for the headline TEST-04 flow. Plan 05 depends on Plans 01 and 02 (services/pages.py + mcp/server entrypoints); it cannot run in Wave 2 alongside Plan 02 because cli/mcp_serve.py imports from app.mcp.server. Plan 05 runs in Wave 3 in parallel with Plan 03 (no files_modified overlap).

Output: 6 new CLI modules + extended cli/main.py + mcp_token.py edited + 4 new integration test files.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/01d-mcp-rest-api-cli/01d-CONTEXT.md
@.planning/phases/01d-mcp-rest-api-cli/01d-PATTERNS.md
@.planning/phases/01d-mcp-rest-api-cli/01d-01-PLAN.md
@.planning/phases/01d-mcp-rest-api-cli/01d-02-PLAN.md
@CLAUDE.md
@server/app/cli/main.py
@server/app/cli/mcp_token.py
@server/app/cli/user.py
@server/app/encryption.py
@server/app/services/pages.py

<interfaces>
<!-- Existing CLI subparser pattern (server/app/cli/mcp_token.py — replicate exactly): -->
```python
def add_subparser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("<name>", help="<help>")
    p.add_argument(...)
    p.set_defaults(func=_handle_<verb>)

async def _handle_<verb>(args: argparse.Namespace) -> int:
    ctx = system_operation_context(client_name="cli", request_id="cli-<name>-<verb>")
    # OR per-user ctx for ops that need user_id resolution
    async for session in session_with_rls(ctx):
        ...
        await session.commit()
    print(...)
    return 0
```

<!-- MCP server entrypoints from Plan 02: -->
```python
# server/app/mcp/server.py:
def main_stdio() -> int: ...
def main_http() -> int: ...    # honours --port via argparse in mcp.server itself
```

<!-- Phase 1c reconciliation job entry: -->
```python
# server/app/scheduler/jobs/reconcile_vault.py — Phase 1c provides this:
async def reconcile_vault(deep: bool = False) -> dict: ...
# Returns a summary dict {pages_created, pages_updated, pages_soft_deleted, errors: []}.
# (If the function is named differently in Phase 1c, grep server/app/scheduler/jobs/ for
#  the actual entry point and adapt the import.)
```

<!-- Encryption module (used by doctor): -->
```python
# server/app/encryption.py:
class FernetKeyMissing(Exception): ...
def fernet() -> MultiFernet: ...     # raises FernetKeyMissing if env var unset
```

<!-- D-14 doctor report sections: -->
```text
fernet_key:               OK | MISSING — set SMARTCOPILOT_FERNET_KEY
inotify_max_user_watches: <integer> | (unreadable — not Linux?)
cors_config:              <list of allowed origins> | none configured
mcp_token_storage:        sha256-hashed (Phase 1b: hash-only; plaintext shown once at creation)
db_connection:            OK | <error string>
db_pgvector_extension:    OK | not loaded
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: page CRUD CLI + reconcile + stats subcommands</name>
  <files>server/app/cli/page.py, server/app/cli/reconcile.py, server/app/cli/stats.py, server/app/tests/integration/test_cli_page.py</files>
  <read_first>
    - server/app/cli/mcp_token.py (exact subparser pattern to mirror)
    - server/app/services/pages.py (signatures after Plan 01)
    - server/app/services/users.py (get_user_by_username helper)
    - server/app/scheduler/jobs/reconcile_vault.py (entry function name + signature — Phase 1c)
  </read_first>
  <behavior>
    - `smartcopilot page get --user <username> --slug <slug>`: prints `slug=...\ntitle=...\nnote_type=...\nupdated_at=...\ncompiled_truth:\n<text>\ntimeline:\n<text>`. Returns 0 on success, 2 if user/page not found.
    - `smartcopilot page put --user <username> --slug <slug> --file <path>`: reads bytes from file, calls write_page, prints `slug=... page_id=... version=...`.
    - `smartcopilot page delete --user <username> --slug <slug>`: calls soft_delete_page, prints `deleted slug=...`.
    - `smartcopilot page list --user <username> [--limit 50]`: prints one line per page `<slug>\t<note_type>\t<updated_at>`.
    - `smartcopilot page search --user <username> --query "<text>" [--limit 20]`: prints one line per hit `<score>\t<slug>\t<snippet>`.
    - `smartcopilot reconcile [--deep]`: runs `await reconcile_vault(deep=args.deep)`; prints summary dict as `key=value` lines; returns 0.
    - `smartcopilot stats --user <username>`: prints `page_count=N\ndeleted_page_count=N\ntotal_compiled_truth_bytes=N\nlast_indexed_at=<iso8601>`.
  </behavior>
  <action>
Create `server/app/cli/page.py`:

```python
"""smartcopilot page — vault CRUD subcommands (D-13)."""
from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

from app.auth.context import OperationContext, system_operation_context
from app.dependencies import session_with_rls
from app.services.vault_resolver import VaultNotFound, resolve_user_vault_id
from app.services.pages import (
    PageNotFound, SharedVaultWriteDenied, TimelineViolation,
    get_page_history, list_pages, read_page, search_pages_fts,
    soft_delete_page, write_page,
)
from app.services.users import get_user_by_username, normalize_username


def add_subparser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("page", help="vault page CRUD")
    psub = p.add_subparsers(dest="page_command", required=True)

    g = psub.add_parser("get", help="get a page by slug")
    g.add_argument("--user", required=True)
    g.add_argument("--slug", required=True)
    g.set_defaults(func=_handle_get)

    pp = psub.add_parser("put", help="write a page from a file")
    pp.add_argument("--user", required=True)
    pp.add_argument("--slug", required=True)
    pp.add_argument("--file", required=True, help="path to a markdown file")
    pp.set_defaults(func=_handle_put)

    rm = psub.add_parser("delete", help="soft-delete a page")
    rm.add_argument("--user", required=True)
    rm.add_argument("--slug", required=True)
    rm.set_defaults(func=_handle_delete)

    ls = psub.add_parser("list", help="list pages")
    ls.add_argument("--user", required=True)
    ls.add_argument("--limit", type=int, default=50)
    ls.set_defaults(func=_handle_list)

    sr = psub.add_parser("search", help="full-text search pages")
    sr.add_argument("--user", required=True)
    sr.add_argument("--query", required=True)
    sr.add_argument("--limit", type=int, default=20)
    sr.set_defaults(func=_handle_search)


async def _resolve_user_ctx(username: str, request_id: str) -> tuple[OperationContext, uuid.UUID]:
    norm = normalize_username(username)
    sys_ctx = system_operation_context(client_name="cli", request_id=f"cli-{request_id}-resolve")
    async for session in session_with_rls(sys_ctx):
        user = await get_user_by_username(session, norm)
        if user is None:
            print(f"error: user not found: {username}", file=sys.stderr)
            raise SystemExit(2)
        return OperationContext(
            user_id=user.id, role=user.role, transport="cli", remote=False,
            client_name="cli", request_id=f"cli-{request_id}",
        ), user.id
    raise SystemExit(2)                                    # pragma: no cover


async def _handle_get(args: argparse.Namespace) -> int:
    ctx, _ = await _resolve_user_ctx(args.user, "page-get")
    async for session in session_with_rls(ctx):
        try:
            vault_id = await resolve_user_vault_id(session, ctx.user_id)
            page = await read_page(session, vault_id=vault_id, slug=args.slug)
        except (VaultNotFound, PageNotFound) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    print(f"slug={page.slug}")
    print(f"title={(page.frontmatter or {}).get('title')}")
    print(f"note_type={page.note_type}")
    print(f"updated_at={page.updated_at.isoformat()}")
    print("compiled_truth:")
    print(page.compiled_truth or "")
    print("timeline:")
    print(page.timeline or "")
    return 0


async def _handle_put(args: argparse.Namespace) -> int:
    ctx, _ = await _resolve_user_ctx(args.user, "page-put")
    raw = Path(args.file).read_bytes()
    async for session in session_with_rls(ctx):
        try:
            vault_id = await resolve_user_vault_id(session, ctx.user_id)
            page = await write_page(session, ctx, slug=args.slug, raw_content=raw, vault_id=vault_id)
            await session.commit()
        except VaultNotFound as exc:
            print(f"error: {exc}", file=sys.stderr); return 2
        except TimelineViolation as exc:
            print(f"error: timeline_violation: {exc}", file=sys.stderr); return 2
        except SharedVaultWriteDenied as exc:
            print(f"error: forbidden: {exc}", file=sys.stderr); return 2
        history = await get_page_history(session, ctx, page_id=page.id)
    version = history[0].version if history else 1
    print(f"slug={page.slug} page_id={page.id} version={version}")
    return 0


async def _handle_delete(args: argparse.Namespace) -> int:
    ctx, _ = await _resolve_user_ctx(args.user, "page-delete")
    async for session in session_with_rls(ctx):
        try:
            vault_id = await resolve_user_vault_id(session, ctx.user_id)
            page = await read_page(session, vault_id=vault_id, slug=args.slug)
            await soft_delete_page(session, ctx, page_id=page.id, reason="cli_delete")
            await session.commit()
        except (VaultNotFound, PageNotFound) as exc:
            print(f"error: {exc}", file=sys.stderr); return 2
    print(f"deleted slug={args.slug}")
    return 0


async def _handle_list(args: argparse.Namespace) -> int:
    ctx, _ = await _resolve_user_ctx(args.user, "page-list")
    async for session in session_with_rls(ctx):
        try:
            vault_id = await resolve_user_vault_id(session, ctx.user_id)
        except VaultNotFound as exc:
            print(f"error: {exc}", file=sys.stderr); return 2
        pages = await list_pages(session, ctx, vault_id=vault_id, limit=args.limit)
    for p in pages:
        print(f"{p.slug}\t{p.note_type}\t{p.updated_at.isoformat()}")
    return 0


async def _handle_search(args: argparse.Namespace) -> int:
    ctx, _ = await _resolve_user_ctx(args.user, "page-search")
    async for session in session_with_rls(ctx):
        try:
            vault_id = await resolve_user_vault_id(session, ctx.user_id)
        except VaultNotFound as exc:
            print(f"error: {exc}", file=sys.stderr); return 2
        try:
            hits = await search_pages_fts(
                session, ctx, vault_id=vault_id,
                query=args.query, limit=args.limit,
            )
        except ValueError as exc:
            print(f"error: validation: {exc}", file=sys.stderr); return 2
    for h in hits:
        snippet = (h.snippet or "").replace("\n", " ")
        print(f"{h.score:.4f}\t{h.slug}\t{snippet}")
    return 0
```

Create `server/app/cli/reconcile.py`:

```python
"""smartcopilot reconcile — synchronous vault reconciliation (D-13).

Phase 1c reconcile_vault() has no parameters and returns None (logs internally).
No --deep flag exists in Phase 1c. Future phases may add a deep mode."""
from __future__ import annotations

import argparse
import sys

from app.scheduler.jobs.reconcile_vault import reconcile_vault


def add_subparser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("reconcile", help="reconcile filesystem ↔ database (Phase 1c)")
    p.set_defaults(func=_handle_reconcile)


async def _handle_reconcile(args: argparse.Namespace) -> int:  # noqa: ARG001
    try:
        summary = await reconcile_vault()
    except Exception as exc:                                # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"reconcile_vault_complete: True")
    return 0
```

Pre-flight: run `grep -E "^(async )?def reconcile_vault" server/app/scheduler/jobs/reconcile_vault.py`. If the function name differs (e.g., `run_reconciliation`), adapt the import accordingly. The Phase 1c summary file `01c-06-SUMMARY.md` documents the actual entry point — read it if grep is ambiguous.

Create `server/app/cli/stats.py`:

```python
"""smartcopilot stats — vault summary (D-13)."""
from __future__ import annotations

import argparse
import sys
import uuid

from app.auth.context import OperationContext, system_operation_context
from app.db_session import session_with_rls
from app.services.vault_resolver import VaultNotFound, resolve_user_vault_id
from app.services.pages import vault_stats
from app.services.users import get_user_by_username, normalize_username


def add_subparser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("stats", help="vault page-count summary")
    p.add_argument("--user", required=True)
    p.set_defaults(func=_handle_stats)


async def _resolve_stats_user(username: str) -> tuple[OperationContext, uuid.UUID]:
    norm = normalize_username(username)
    sys_ctx = system_operation_context(client_name="cli", request_id="cli-stats-resolve")
    async for session in session_with_rls(sys_ctx):
        user = await get_user_by_username(session, norm)
        if user is None:
            print(f"error: user not found: {username}", file=sys.stderr)
            raise SystemExit(2)
        return OperationContext(
            user_id=user.id, role=user.role, transport="cli", remote=False,
            client_name="cli", request_id="cli-stats",
        ), user.id
    raise SystemExit(2)                                    # pragma: no cover


async def _handle_stats(args: argparse.Namespace) -> int:
    ctx, _ = await _resolve_stats_user(args.user)
    async for session in session_with_rls(ctx):
        try:
            vault_id = await resolve_user_vault_id(session, ctx.user_id)
        except VaultNotFound as exc:
            print(f"error: {exc}", file=sys.stderr); return 2
        stats = await vault_stats(session, ctx, vault_id=vault_id)
    print(f"page_count={stats.page_count}")
    print(f"deleted_page_count={stats.deleted_page_count}")
    print(f"total_compiled_truth_bytes={stats.total_compiled_truth_bytes}")
    print(f"last_indexed_at={stats.last_indexed_at.isoformat() if stats.last_indexed_at else 'never'}")
    return 0
```

Create `server/app/tests/integration/test_cli_page.py` — tests use `subprocess.run([sys.executable, "-m", "app.cli.main", "page", "put", "--user", ..., "--slug", ..., "--file", ...])`. Seed the user/vault first via fixtures. Assert returncode and parsed stdout.

At minimum:

1. `test_cli_page_put_then_get` — round-trip through CLI.
2. `test_cli_page_put_unknown_user_returns_2` — exit code 2, stderr contains `user not found`.
3. `test_cli_page_list_returns_seeded_pages` — list reflects what was put.
4. `test_cli_page_search_returns_match` — search query finds the page.
5. `test_cli_page_delete_then_get_returns_2` — delete then get → exit 2.
6. `test_cli_stats_returns_count` — stats matches list count.
  </action>
  <verify>
    <automated>cd server && SMARTCOPILOT_FERNET_KEY=T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU= JWT_SIGNING_KEY=test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa pytest -x app/tests/integration/test_cli_page.py -v</automated>
  </verify>
  <acceptance_criteria>
    - File `server/app/cli/page.py` exists with `grep -c "def _handle_" server/app/cli/page.py` >= 5
    - File `server/app/cli/reconcile.py` exists; `grep -c "reconcile_vault" server/app/cli/reconcile.py` >= 1
    - File `server/app/cli/stats.py` exists; `grep -c "vault_stats" server/app/cli/stats.py` >= 1
    - All 6 tests in `test_cli_page.py` pass.
    - `cd server && ruff check app/cli/page.py app/cli/reconcile.py app/cli/stats.py` exits 0.
  </acceptance_criteria>
  <done>page/reconcile/stats CLI subcommands ship and pass round-trip tests.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: doctor + check-resolvable subcommands</name>
  <files>server/app/cli/doctor.py, server/app/cli/check_resolvable.py, server/app/tests/integration/test_cli_doctor.py, server/app/tests/integration/test_cli_check_resolvable.py</files>
  <read_first>
    - server/app/encryption.py (FernetKeyMissing + fernet() signatures)
    - server/app/cli/user.py (CLI subcommand without DB writes — doctor will add DB ping)
    - .planning/phases/01d-mcp-rest-api-cli/01d-CONTEXT.md (D-14 — exact doctor report sections)
  </read_first>
  <behavior>
    - `smartcopilot doctor` prints (one line per check) — exact tokens enforced by acceptance criteria:
      - `fernet_key: OK` or `fernet_key: MISSING — set SMARTCOPILOT_FERNET_KEY` (returncode != 0 if missing)
      - `inotify_max_user_watches: <int>` or `inotify_max_user_watches: (unreadable — not Linux?)`
      - `cors_config: <comma-separated origins>` or `cors_config: none configured`
      - `mcp_token_storage: sha256-hashed`
      - `db_connection: OK` or `db_connection: ERROR — <message>`
      - `db_pgvector_extension: OK` or `db_pgvector_extension: not loaded`
      - Returns 0 if all OK; 1 if Fernet missing; 1 if db_connection fails.
    - `smartcopilot check-resolvable [--skills-dir <path>]` (default `/vaults/shared/.skills/`):
      - If directory doesn't exist OR is empty: prints `no skills directory at <path>` AND `check: OK` AND returns 0 (Phase 1 invariant).
      - Phase 3 plug-in point: when SKILLS arrive in Phase 3, this command will validate the tree. For Phase 1d, the empty case is the only required pass.
  </behavior>
  <action>
Create `server/app/cli/doctor.py`:

```python
"""smartcopilot doctor — D-14 system health smoke (CLI-02)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import text

from app.auth.context import system_operation_context
from app.dependencies import session_with_rls
from app.encryption import FernetKeyMissing, fernet
from app.settings import settings


def add_subparser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("doctor", help="report system health (D-14)")
    p.set_defaults(func=_handle_doctor)


async def _handle_doctor(args: argparse.Namespace) -> int:    # noqa: ARG001
    overall_ok = True

    # 1. Fernet key
    try:
        fernet()
        print("fernet_key: OK")
    except FernetKeyMissing:
        print("fernet_key: MISSING — set SMARTCOPILOT_FERNET_KEY", file=sys.stderr)
        overall_ok = False
    except ValueError as exc:
        print(f"fernet_key: INVALID — {exc}", file=sys.stderr)
        overall_ok = False

    # 2. inotify limit
    try:
        watches = int(Path("/proc/sys/fs/inotify/max_user_watches").read_text().strip())
        print(f"inotify_max_user_watches: {watches}")
    except OSError:
        print("inotify_max_user_watches: (unreadable — not Linux?)")

    # 3. CORS config — Phase 1d settings has no cors origins yet (added in Phase 6).
    #    Surface "none configured" so doctor is forward-compatible.
    cors_origins = getattr(settings, "cors_allow_origins", None)
    if cors_origins:
        print(f"cors_config: {','.join(cors_origins)}")
    else:
        print("cors_config: none configured")

    # 4. MCP token storage mode (D-14)
    print("mcp_token_storage: sha256-hashed")

    # 5. DB connection + pgvector extension
    try:
        ctx = system_operation_context(client_name="cli", request_id="cli-doctor")
        async for session in session_with_rls(ctx):
            await session.execute(text("SELECT 1"))
            print("db_connection: OK")
            row = (await session.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            )).scalar_one_or_none()
            if row:
                print("db_pgvector_extension: OK")
            else:
                print("db_pgvector_extension: not loaded")
    except Exception as exc:                                  # noqa: BLE001
        print(f"db_connection: ERROR — {exc}", file=sys.stderr)
        overall_ok = False

    return 0 if overall_ok else 1
```

Create `server/app/cli/check_resolvable.py`:

```python
"""smartcopilot check-resolvable — skills-tree validator (CLI-03).

Phase 1d: empty tree passes cleanly. Phase 3 will populate this with the real
RESOLVER.md MECE/DRY/orphan checks; Phase 1d only enforces the empty-pass invariant.
"""
from __future__ import annotations

import argparse
from pathlib import Path

DEFAULT_SKILLS_DIR = "/vaults/shared/.skills"


def add_subparser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("check-resolvable", help="validate skills tree reachability (CLI-03)")
    p.add_argument("--skills-dir", default=DEFAULT_SKILLS_DIR)
    p.set_defaults(func=_handle_check_resolvable)


async def _handle_check_resolvable(args: argparse.Namespace) -> int:
    skills_dir = Path(args.skills_dir)
    if not skills_dir.exists() or not skills_dir.is_dir():
        print(f"no skills directory at {skills_dir}")
        print("check: OK")
        return 0
    # Phase 1d: an existing-but-empty directory also passes.
    if not any(skills_dir.iterdir()):
        print(f"empty skills directory at {skills_dir}")
        print("check: OK")
        return 0
    # Phase 3 will replace this branch with real validation. For Phase 1d, surface a TODO.
    print(f"skills directory at {skills_dir} — full validation arrives in Phase 3")
    print("check: OK")
    return 0
```

Create `server/app/tests/integration/test_cli_doctor.py`:

```python
"""smartcopilot doctor tests (CLI-02 / D-14)."""
from __future__ import annotations

import os
import subprocess
import sys

import pytest


@pytest.mark.integration
def test_doctor_reports_all_d14_sections(postgres_container) -> None:
    env = os.environ.copy()
    env["SMARTCOPILOT_FERNET_KEY"] = "T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU="
    env["JWT_SIGNING_KEY"] = "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa"
    sync_url = postgres_container.get_connection_url()
    raw_dsn = sync_url.replace("postgresql+psycopg2://", "postgresql://", 1)
    env["DATABASE_URL"] = raw_dsn.replace("postgresql://", "postgresql+asyncpg://", 1)

    proc = subprocess.run(
        [sys.executable, "-m", "app.cli.main", "doctor"],
        env=env, capture_output=True, timeout=30, cwd="server",
    )
    out = proc.stdout.decode()
    # D-14 mandatory sections:
    assert "fernet_key:" in out
    assert "inotify_max_user_watches:" in out
    assert "cors_config:" in out
    assert "mcp_token_storage: sha256-hashed" in out
    assert "db_connection:" in out
    assert "db_pgvector_extension:" in out
    assert proc.returncode == 0


@pytest.mark.integration
def test_doctor_returns_1_when_fernet_missing(postgres_container) -> None:
    env = os.environ.copy()
    env.pop("SMARTCOPILOT_FERNET_KEY", None)
    env["SMARTCOPILOT_FERNET_KEY"] = ""                       # explicit empty
    env["JWT_SIGNING_KEY"] = "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa"
    sync_url = postgres_container.get_connection_url()
    env["DATABASE_URL"] = sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    proc = subprocess.run(
        [sys.executable, "-m", "app.cli.main", "doctor"],
        env=env, capture_output=True, timeout=30, cwd="server",
    )
    # Exit non-zero AND stderr names the env var.
    assert proc.returncode != 0
    assert b"SMARTCOPILOT_FERNET_KEY" in proc.stderr
```

Create `server/app/tests/integration/test_cli_check_resolvable.py`:

```python
"""smartcopilot check-resolvable tests (CLI-03)."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

import pytest


@pytest.mark.integration
def test_check_resolvable_passes_when_dir_missing() -> None:
    env = os.environ.copy()
    env["SMARTCOPILOT_FERNET_KEY"] = "T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU="
    env["JWT_SIGNING_KEY"] = "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa"
    proc = subprocess.run(
        [sys.executable, "-m", "app.cli.main", "check-resolvable",
         "--skills-dir", "/nonexistent/path/zzz"],
        env=env, capture_output=True, timeout=10, cwd="server",
    )
    assert proc.returncode == 0
    assert b"no skills directory" in proc.stdout
    assert b"check: OK" in proc.stdout


@pytest.mark.integration
def test_check_resolvable_passes_when_dir_empty() -> None:
    env = os.environ.copy()
    env["SMARTCOPILOT_FERNET_KEY"] = "T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU="
    env["JWT_SIGNING_KEY"] = "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa"
    with tempfile.TemporaryDirectory() as tmp:
        proc = subprocess.run(
            [sys.executable, "-m", "app.cli.main", "check-resolvable",
             "--skills-dir", tmp],
            env=env, capture_output=True, timeout=10, cwd="server",
        )
        assert proc.returncode == 0
        assert b"check: OK" in proc.stdout
```
  </action>
  <verify>
    <automated>cd server && SMARTCOPILOT_FERNET_KEY=T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU= JWT_SIGNING_KEY=test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa pytest -x app/tests/integration/test_cli_doctor.py app/tests/integration/test_cli_check_resolvable.py -v</automated>
  </verify>
  <acceptance_criteria>
    - File `server/app/cli/doctor.py` exists; `grep -c '"fernet_key: OK"' server/app/cli/doctor.py` >= 1; `grep -c '"mcp_token_storage: sha256-hashed"' server/app/cli/doctor.py` >= 1.
    - File `server/app/cli/check_resolvable.py` exists; `grep -c "no skills directory" server/app/cli/check_resolvable.py` >= 1; `grep -c "check: OK" server/app/cli/check_resolvable.py` >= 1.
    - All 4 tests pass.
    - `cd server && ruff check app/cli/doctor.py app/cli/check_resolvable.py` exits 0.
  </acceptance_criteria>
  <done>doctor + check-resolvable ship; D-14 sections all present; CLI-02/CLI-03 satisfied for Phase 1d.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: mcp serve + register all subparsers in cli/main.py</name>
  <files>server/app/cli/mcp_serve.py, server/app/cli/main.py, server/app/cli/mcp_token.py, server/app/tests/integration/test_cli_mcp_serve.py</files>
  <read_first>
    - server/app/cli/main.py (current entry point — extend with new subparsers)
    - server/app/cli/mcp_token.py (existing `mcp` subparser owner — Edit to add a `serve` sibling)
    - server/app/mcp/server.py (Plan 02 — main_stdio + main_http entrypoints + argparse for --port + --selftest)
  </read_first>
  <behavior>
    - `smartcopilot mcp serve --stdio`: dispatches to `main_stdio()`. Auth failure exits 1 (mirrors mcp.server's own behaviour).
    - `smartcopilot mcp serve --http --port 8888`: dispatches to `main_http(port=8888)`.
    - `smartcopilot mcp serve` without `--stdio` or `--http` exits 2 with usage error.
    - `smartcopilot --help` lists every Phase 1d subcommand: user, mcp, provider_key, page, doctor, check-resolvable, reconcile, stats.
  </behavior>
  <action>
Create `server/app/cli/mcp_serve.py`:

```python
"""smartcopilot mcp serve — wrapper that dispatches to app.mcp.server (D-13).

Note: this conflicts with the existing `mcp` subparser owned by mcp_token.py.
Phase 1b registered `mcp token ...`; Phase 1d adds `mcp serve ...` to the
SAME `mcp` parent. We integrate by having mcp_token.py keep ownership of the
`mcp` subparser and exposing an `extend_subparser` hook here.
"""
from __future__ import annotations

import argparse
import sys

from app.mcp import server as mcp_server


def add_serve_to_mcp_subparser(mcp_subsubparsers: argparse._SubParsersAction) -> None:
    """Register `serve` under the existing `mcp` subparser owned by mcp_token.py."""
    sv = mcp_subsubparsers.add_parser("serve", help="run the MCP server (stdio or HTTP)")
    grp = sv.add_mutually_exclusive_group(required=True)
    grp.add_argument("--stdio", action="store_true", help="stdio transport (Claude Code, etc.)")
    grp.add_argument("--http", action="store_true", help="Streamable HTTP transport")
    sv.add_argument("--port", type=int, default=8787, help="HTTP port (default 8787)")
    sv.set_defaults(func=_handle_mcp_serve)


async def _handle_mcp_serve(args: argparse.Namespace) -> int:
    if args.stdio:
        return mcp_server.main_stdio()
    if args.http:
        # Replace sys.argv so the embedded argparse in mcp.server picks up --port.
        sys.argv = ["app.mcp.server", "--http", "--port", str(args.port)]
        return mcp_server.main_http()
    print("error: must specify --stdio or --http", file=sys.stderr)
    return 2
```

Edit `server/app/cli/mcp_token.py` (use Edit tool) — extend the existing `mcp` subparser to also register the `serve` subcommand. After the existing `tsub = token.add_subparsers(...)` block, add:

```python
    # Phase 1d: extend `mcp` parent with `serve` subcommand.
    from app.cli.mcp_serve import add_serve_to_mcp_subparser
    add_serve_to_mcp_subparser(msub)
```

(`msub` is the `mcp` subparser's `add_subparsers(...)` action — identifier is already in scope inside `add_subparser`.)

Edit `server/app/cli/main.py` to register the new top-level subcommands. The new file should look like (preserving Phase 1b imports and existing pattern):

```python
"""smartcopilot CLI entrypoint (Phase 1d expansion of D-13)."""
from __future__ import annotations

import argparse
import asyncio
import sys

from app.cli import (
    check_resolvable as check_resolvable_cmd,
    doctor as doctor_cmd,
    mcp_token as mcp_token_cmd,
    page as page_cmd,
    provider_key as provider_key_cmd,
    reconcile as reconcile_cmd,
    stats as stats_cmd,
    user as user_cmd,
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="smartcopilot")
    sub = p.add_subparsers(dest="command", required=True)

    user_cmd.add_subparser(sub)
    mcp_token_cmd.add_subparser(sub)        # registers `mcp token` AND (Phase 1d) `mcp serve`
    provider_key_cmd.add_subparser(sub)
    page_cmd.add_subparser(sub)             # NEW Phase 1d
    doctor_cmd.add_subparser(sub)           # NEW Phase 1d
    check_resolvable_cmd.add_subparser(sub) # NEW Phase 1d
    reconcile_cmd.add_subparser(sub)        # NEW Phase 1d
    stats_cmd.add_subparser(sub)            # NEW Phase 1d

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return asyncio.run(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
```

Create `server/app/tests/integration/test_cli_mcp_serve.py`:

```python
"""Test smartcopilot mcp serve dispatch."""
from __future__ import annotations

import os
import subprocess
import sys

import pytest


@pytest.mark.integration
def test_smartcopilot_help_lists_all_subcommands() -> None:
    env = os.environ.copy()
    env.setdefault("SMARTCOPILOT_FERNET_KEY", "T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU=")
    env.setdefault("JWT_SIGNING_KEY", "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa")
    proc = subprocess.run(
        [sys.executable, "-m", "app.cli.main", "--help"],
        env=env, capture_output=True, timeout=10, cwd="server",
    )
    out = proc.stdout.decode()
    for token in ("user", "mcp", "provider_key", "page", "doctor", "check-resolvable", "reconcile", "stats"):
        assert token in out, f"missing subcommand in --help: {token}"
    assert proc.returncode == 0


@pytest.mark.integration
def test_mcp_serve_stdio_with_bad_token_exits_1() -> None:
    env = os.environ.copy()
    env["SMARTCOPILOT_FERNET_KEY"] = "T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU="
    env["JWT_SIGNING_KEY"] = "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa"
    env["SMARTCOPILOT_MCP_TOKEN"] = "definitely-not-a-real-token-zzz"
    proc = subprocess.run(
        [sys.executable, "-m", "app.cli.main", "mcp", "serve", "--stdio"],
        env=env, capture_output=True, timeout=10, cwd="server",
    )
    assert proc.returncode == 1
    assert b"AUTH ERROR" in proc.stderr
    # And, per TEST-03, stdout must be empty.
    assert proc.stdout == b""


@pytest.mark.integration
def test_mcp_serve_requires_transport_flag() -> None:
    env = os.environ.copy()
    env["SMARTCOPILOT_FERNET_KEY"] = "T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU="
    env["JWT_SIGNING_KEY"] = "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa"
    proc = subprocess.run(
        [sys.executable, "-m", "app.cli.main", "mcp", "serve"],
        env=env, capture_output=True, timeout=10, cwd="server",
    )
    # argparse mutually_exclusive_group(required=True) → exit code 2.
    assert proc.returncode == 2


Create `server/app/tests/integration/test_cli_reconcile.py`:

```python
"""smartcopilot reconcile tests (CLI-01)."""
from __future__ import annotations

import os
import subprocess
import sys

import pytest


@pytest.mark.integration
def test_reconcile_runs_and_exits_0(postgres_container) -> None:
    env = os.environ.copy()
    env["SMARTCOPILOT_FERNET_KEY"] = "T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU="
    env["JWT_SIGNING_KEY"] = "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa"
    sync_url = postgres_container.get_connection_url()
    raw_dsn = sync_url.replace("postgresql+psycopg2://", "postgresql://", 1)
    env["DATABASE_URL"] = raw_dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
    proc = subprocess.run(
        [sys.executable, "-m", "app.cli.main", "reconcile"],
        env=env, capture_output=True, timeout=30, cwd="server",
    )
    assert proc.returncode == 0, f"stderr={proc.stderr.decode()!r}"
    assert b"reconcile_vault_complete" in proc.stdout
```
  </action>
  <verify>
    <automated>cd server && SMARTCOPILOT_FERNET_KEY=T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU= JWT_SIGNING_KEY=test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa pytest -x app/tests/integration/test_cli_mcp_serve.py app/tests/integration/test_cli_reconcile.py -v</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "from app.cli import" server/app/cli/main.py` >= 1
    - `grep -E "page_cmd|doctor_cmd|check_resolvable_cmd|reconcile_cmd|stats_cmd" server/app/cli/main.py | wc -l` >= 5
    - `grep -c "add_serve_to_mcp_subparser" server/app/cli/mcp_token.py` >= 1
    - `grep -c "main_stdio\|main_http" server/app/cli/mcp_serve.py` >= 2
    - All 4 tests pass (3 from mcp_serve + 1 from reconcile).
    - `cd server && ruff check app/cli/` exits 0.
    - `cd server && python -m app.cli.main --help` exits 0 and stdout contains every subcommand name.
  </acceptance_criteria>
  <done>CLI registry complete; mcp serve dispatches to MCP server entrypoints; --help discoverability verified.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Operator shell → CLI | The CLI runs as the container's local user; treat all flag values as trusted (operator authored them) |
| CLI → service layer | OperationContext built from `username` lookup; transport="cli", remote=False — broader privileges than remote callers per MCP-05 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-01d05-01 | Tampering | `--file` argument reads attacker-controlled path | accept | CLI is operator-only; running smartcopilot at all implies host trust. write_page applies parser + slug validation. |
| T-01d05-02 | Information Disclosure | `page get` prints compiled_truth to stdout | accept | Operator already has filesystem access to `/vaults/`; printing same content adds no exposure. |
| T-01d05-03 | Information Disclosure | `doctor` leaks DB DSN in error string | mitigate | Generic SQLAlchemy errors are stringified; we DO NOT print the DSN — only `db_connection: ERROR — <message>` from the exception. Verified by inspecting `_handle_doctor` exception path. |
| T-01d05-04 | Spoofing | `--user` argument doesn't authenticate | accept | CLI runs locally; operator privileges are the auth boundary. Audit logging arrives in Phase 6 (OBS-03). |
| T-01d05-05 | Information Disclosure | mcp serve --stdio writes to stdout | mitigate | Plan 02 already enforces no-stdout-before-tool-loop; the CLI wrapper changes nothing — TEST-03 in test_cli_mcp_serve.py also asserts the empty-stdout invariant. |
| T-01d05-06 | DoS | `page list --limit 999999` | mitigate | Service `list_pages` clamps to 1..200 server-side. |
| T-01d05-07 | Tampering | `reconcile` runs unbounded | accept | Phase 1c reconcile_vault() iterates all vaults; operator-triggered. |
</threat_model>

<verification>
After all 3 tasks:
1. `cd server && pytest -x app/tests/integration/test_cli_page.py app/tests/integration/test_cli_doctor.py app/tests/integration/test_cli_check_resolvable.py app/tests/integration/test_cli_mcp_serve.py -v` — all pass.
2. `cd server && ruff check app/cli/` exits 0.
3. `cd server && python -m app.cli.main --help` exits 0; stdout lists every subcommand.
4. `cd server && python -m app.cli.main mcp serve --stdio` with no SMARTCOPILOT_MCP_TOKEN env var: exit 1, stdout empty, stderr contains AUTH ERROR.
</verification>

<success_criteria>
- 6 new CLI modules ship; cli/main.py registers all subparsers; --help discoverability proven by integration test.
- D-14 doctor sections all emitted with the exact tokens.
- check-resolvable empty-tree invariant (Phase 1) holds.
- mcp serve dispatches correctly to stdio / HTTP entrypoints.
- CLI-01..CLI-03 satisfied.
</success_criteria>

<output>
After completion, create `.planning/phases/01d-mcp-rest-api-cli/01d-05-SUMMARY.md` listing subcommand inventory, test counts, any deviations.
</output>
