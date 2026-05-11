---
phase: 01d
plan: 02
type: execute
wave: 2
depends_on:
  - "01d-01"
files_modified:
  - server/app/services/vault_resolver.py
  - server/app/mcp/server.py
  - server/app/mcp/tools/__init__.py
  - server/app/mcp/tools/brain.py
  - server/app/mcp/tools/capability.py
  - server/app/mcp/tools/ingest.py
  - server/app/mcp/tools/enrich.py
  - server/app/mcp/tools/recipe.py
  - server/app/mcp/tools/skill.py
  - server/app/mcp/tools/jobs.py
  - server/app/mcp/tools/maintain.py
  - server/app/mcp/tools/entity.py
  - server/app/mcp/tools/graph.py
  - server/app/tests/integration/test_mcp_tools.py
  - server/app/tests/integration/test_mcp_stdout_clean.py
autonomous: true
requirements:
  - MCP-01
  - MCP-02
  - MCP-03
  - MCP-04
  - MCP-05
  - MCP-06
  - MCP-07
  - MCP-08

must_haves:
  truths:
    - "Real MCP tools call services/pages.py via session_with_rls(ctx) — never raw async_session_factory"
    - "All 14 real tools (brain.put, brain.get, brain.search, brain.list, brain.delete, brain.history, brain.diff, brain.revert, brain.append_timeline, brain.update_compiled_truth, brain.backlinks, brain.stats, brain.health, capability_discovery) are registered and discoverable"
    - "All ≥16 stub tools (ingest.*, enrich.*, recipe.*, skill.*, jobs.*, maintain.*, brain.entity.*, brain.graph.*) return D-05 not_implemented payload"
    - "stdio mode reads SMARTCOPILOT_MCP_TOKEN env var, validates via auth.core.validate_bearer, exits non-zero on auth failure"
    - "stdio mode writes ZERO bytes to stdout outside JSON-RPC framing — all logs go to stderr"
    - "HTTP mode uses stateless_http=True and json_response=True; per-request Authorization: Bearer header validated"
    - "OperationContext.transport is mcp_stdio (remote=False) for stdio, mcp_http (remote=True) for HTTP"
    - "remote=True callers blocked from cross-user vault reads (read_page/list_pages restricted to ctx.user_id's vault) and slug must pass validate_slug"
    - "Each MCP tool has a Pydantic input model and a documented output dict shape"
    - "smartcopilot mcp serve --http exits cleanly on SIGTERM (no hung process)"
    - "vault_resolver lives under app.services (transport-agnostic) — REST routes (Plan 03) and CLI (Plan 05) import the same helper without crossing the MCP boundary"
  artifacts:
    - path: "server/app/services/vault_resolver.py"
      provides: "Transport-agnostic vault resolution helper: VaultNotFound + resolve_user_vault_id; consumed by MCP tools, REST routes, and CLI alike"
      contains: "async def resolve_user_vault_id"
    - path: "server/app/mcp/server.py"
      provides: "MCP server entry points: main_stdio() and main_http(); both build OperationContext, register tools, run the SDK"
      contains: "stateless_http=True"
    - path: "server/app/mcp/tools/__init__.py"
      provides: "register_all_tools(mcp_server, ctx_factory) — single function called from server.py to wire every tool"
    - path: "server/app/mcp/tools/brain.py"
      provides: "14 real Phase 1d brain tools (D-04)"
      contains: "async def brain_put"
    - path: "server/app/mcp/tools/capability.py"
      provides: "capability_discovery — calls services/capabilities.get_capabilities (REST-05 parity seam)"
    - path: "server/app/mcp/tools/ingest.py"
      provides: "Stubbed ingest.idea, ingest.media, ingest.meeting (D-04, D-05)"
    - path: "server/app/mcp/tools/enrich.py"
      provides: "Stubbed enrich.entity (D-05)"
    - path: "server/app/mcp/tools/recipe.py"
      provides: "Stubbed recipe.run (D-05)"
    - path: "server/app/mcp/tools/skill.py"
      provides: "Stubbed skill.list, skill.get, skill.run (D-05)"
    - path: "server/app/mcp/tools/jobs.py"
      provides: "Stubbed jobs.submit, jobs.status, jobs.cancel (D-05)"
    - path: "server/app/mcp/tools/maintain.py"
      provides: "Stubbed maintain.run, maintain.report (D-05)"
    - path: "server/app/mcp/tools/entity.py"
      provides: "Stubbed brain.entity.* (D-05)"
    - path: "server/app/mcp/tools/graph.py"
      provides: "Stubbed brain.graph.traverse (D-05)"
    - path: "server/app/tests/integration/test_mcp_tools.py"
      provides: "Tool tests with constructed OperationContext (MCP-07)"
    - path: "server/app/tests/integration/test_mcp_stdout_clean.py"
      provides: "TEST-03 stdio cleanliness test"
  key_links:
    - from: "server/app/mcp/tools/brain.py"
      to: "server/app/services/pages.py"
      via: "Every brain.* tool calls a service function inside session_with_rls(ctx)"
      pattern: "from app.services.pages import"
    - from: "server/app/mcp/tools/brain.py"
      to: "server/app/services/vault_resolver.py"
      via: "Vault-id resolution lives in services/, not mcp/tools/_vault.py — preserves the transport-agnostic boundary required by REST-06"
      pattern: "from app.services.vault_resolver import"
    - from: "server/app/mcp/tools/capability.py"
      to: "server/app/services/capabilities.py"
      via: "capability_discovery delegates to get_capabilities() — REST-05 parity"
      pattern: "from app.services.capabilities import get_capabilities"
    - from: "server/app/mcp/server.py"
      to: "server/app/auth/core.py"
      via: "validate_bearer on stdio bootstrap and per-request HTTP token verification"
      pattern: "from app.auth.core import validate_bearer"
---

<objective>
Replace the Phase 1b MCP stub with the real Model Context Protocol server in two transports (stdio + Streamable HTTP) plus the per-domain tools package. After this plan, Claude Code (or any MCP client) can connect to the running server and execute the 14 Phase 1d real tools; all ≥16 stub tools register cleanly and return the D-05 not_implemented payload.

Purpose: This is the headline deliverable for MCP-01..MCP-08. Plan 03 (REST) and Plan 04 (WS) parallel-implement the same service surface; Plan 05 (CLI) adds `smartcopilot mcp serve` to launch this server; Plan 06 acceptance test uses the stdio entrypoint to drive `brain_put / brain_get / brain_search` end-to-end.

Architectural note (revision): the vault-resolution helper lives at `server/app/services/vault_resolver.py` (NOT `server/app/mcp/tools/_vault.py`). REST routes (Plan 03) and the CLI (Plan 05) import the same helper directly without crossing into the MCP layer — this preserves the transport-agnostic services boundary required by REST-06 and CLAUDE.md.

Output: New `server/app/services/vault_resolver.py`, replaced `server/app/mcp/server.py`, new `server/app/mcp/tools/` package (10 modules), 2 new test files.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/01d-mcp-rest-api-cli/01d-CONTEXT.md
@.planning/phases/01d-mcp-rest-api-cli/01d-PATTERNS.md
@.planning/phases/01d-mcp-rest-api-cli/01d-01-PLAN.md
@CLAUDE.md
@server/app/mcp/server.py
@server/app/auth/core.py
@server/app/auth/context.py
@server/app/services/pages.py
@server/app/services/capabilities.py
@server/app/vault/paths.py

<interfaces>
<!-- Service surface available after Plan 01 ships. Tools call these directly: -->
```python
# server/app/services/pages.py — Phase 1c + Phase 1d Plan 01:
from app.services.pages import (
    PageNotFound, TimelineViolation, SharedVaultWriteDenied,
    SearchHit, PageVersionSummary, PageDiff, BacklinkHit, VaultStats, VaultHealth,
    upsert_page, write_page, read_page, soft_delete_page, append_timeline,
    search_pages_fts, list_pages, get_page_history, get_page_diff,
    revert_page, get_backlinks_for_page, vault_stats, vault_health,
)
from app.services.capabilities import get_capabilities

# server/app/auth/core.py:
async def validate_bearer(token: str | None) -> AuthResult: ...   # returns user_id, role, mcp_token_id, error

# server/app/auth/context.py:
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

# server/app/db_session.py:
async def session_with_rls(ctx: OperationContext) -> AsyncIterator[AsyncSession]: ...

# server/app/vault/paths.py:
def validate_slug(slug: str) -> None: ...   # raises ValueError on bad slug
```

<!-- MCP SDK 1.25+ tool registration shape (CLAUDE.md notes + library docs): -->
```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("smart-copilot")

@mcp.tool()
async def brain_put(slug: str, content: str, namespace: str = "private") -> dict:
    """Write a page to the vault."""
    ...

# Stdio entrypoint:
mcp.run(transport="stdio")     # blocks; reads/writes JSON-RPC over stdin/stdout

# Streamable HTTP entrypoint:
mcp_http = FastMCP("smart-copilot", stateless_http=True, json_response=True)
# mounts as ASGI sub-app on the FastAPI app OR runs standalone via uvicorn
```

<!-- D-05 stub payload — registered tool returns this; NOT a protocol-level error: -->
```python
{
    "error": {
        "code": "not_implemented",
        "message": "tool available in Phase Xa",
        "available_in_phase": "<phase>",
    }
}
```

<!-- Vault resolution for ALL transports — Phase 1d uses the user's private vault by default.
     Centralised in server/app/services/vault_resolver.py (transport-agnostic per REST-06).
     MCP tools, REST routes, and CLI all import from app.services.vault_resolver. -->
```python
# Resolve the vault_id for ctx.user_id by querying vaults WHERE owner_user_id = ctx.user_id AND kind='private'.
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: MCP server entrypoints (stdio + HTTP) — server/app/mcp/server.py</name>
  <files>server/app/mcp/server.py, server/app/tests/integration/test_mcp_stdout_clean.py</files>
  <read_first>
    - server/app/mcp/server.py (current Phase 1b stub — replace, don't append)
    - server/app/auth/core.py (validate_bearer signature + AuthResult)
    - server/app/auth/context.py (OperationContext dataclass + transport literal)
    - server/app/vault/watcher.py lines 263–315 (async main + SIGTERM template — see 01d-PATTERNS.md)
    - server/app/logging/redaction.py (configure_logging — must call before any structlog.get_logger)
    - CLAUDE.md (MCP Stack section — `>= 1.25, < 2`, stateless_http=True, json_response=True, NEVER write to stdout in stdio mode)
  </read_first>
  <behavior>
    - main_stdio(): reads `SMARTCOPILOT_MCP_TOKEN` env var; calls `validate_bearer(token)`; on error, prints `f"AUTH ERROR: {result.error}"` to stderr and returns exit code 1; never writes to stdout.
    - main_stdio(): on success, builds `OperationContext(transport="mcp_stdio", remote=False, ...)` and registers tools; calls `mcp.run(transport="stdio")` which blocks.
    - main_http(): starts a FastMCP server with `stateless_http=True, json_response=True`; binds Authorization: Bearer to per-request OperationContext via the SDK's auth hook; SIGTERM exits cleanly.
    - Both modes call `configure_logging()` before any logger creation; redaction processor is active.
    - Stdout cleanliness test: spawn `python -m app.mcp.server --http --port 0 --selftest` (or equivalent) — capture stdout. Stdout MUST be empty bytes. All log output is on stderr.
  </behavior>
  <action>
REPLACE the contents of `server/app/mcp/server.py`. The new file MUST contain:

1. Module docstring naming D-05/D-06 contract and stating "NEVER write to stdout in stdio mode".
2. Imports — only stdlib + `mcp` SDK + app modules. No `print()` calls anywhere in stdio code paths.
3. Argument parser supporting `--stdio | --http`, `--port` (default 8787 from `settings.mcp_http_port` if added; otherwise hardcode 8787), and `--selftest` (HTTP mode only — exits 0 immediately after binding).
4. `main_stdio() -> int`:
   - Calls `configure_logging()`.
   - `token = os.environ.get("SMARTCOPILOT_MCP_TOKEN")`
   - `result = asyncio.run(validate_bearer(token))`
   - If `result.error` is not None: write to stderr `print(f"AUTH ERROR: {result.error}", file=sys.stderr)` and `return 1`.
   - Else build `ctx = OperationContext(user_id=result.user_id, role=result.role or "user", transport="mcp_stdio", remote=False, client_name="mcp_stdio", request_id="mcp-stdio", mcp_token_id=result.mcp_token_id)`.
   - Import `mcp.server.fastmcp.FastMCP`, instantiate, call `register_all_tools(mcp, lambda req=None: ctx)` from `app.mcp.tools` (Task 2).
   - Call `mcp.run(transport="stdio")`. Return 0 on graceful exit.
5. `main_http() -> int`:
   - Calls `configure_logging()`.
   - Builds a `ctx_factory(request)` closure that:
     - Extracts `Authorization: Bearer <token>` from the request headers.
     - Calls `await validate_bearer(token)`.
     - Raises a 401 / closes the request on failure (use the SDK's auth hook; do NOT throw FastAPI exceptions — this entrypoint is not the FastAPI app).
     - On success, returns `OperationContext(transport="mcp_http", remote=True, client_name=request.client.host, request_id=request.headers.get("x-request-id") or "mcp-http", user_id=result.user_id, role=result.role or "user", mcp_token_id=result.mcp_token_id)`.
   - Instantiate `FastMCP("smart-copilot", stateless_http=True, json_response=True)`.
   - Register all tools.
   - If `--selftest` flag is set: print "ok" to stderr and `return 0` immediately.
   - Else run uvicorn binding 0.0.0.0:<port> with SIGTERM handler that triggers shutdown.
6. `main()` dispatches argparse → `main_stdio` or `main_http`.
7. `if __name__ == "__main__": sys.exit(main())`.

CREATE `server/app/tests/integration/test_mcp_stdout_clean.py` (TEST-03):

```python
"""TEST-03: MCP stdio cleanliness — no unexpected bytes on stdout after init.

Spawns the stdio entry point as a subprocess, sends a JSON-RPC `initialize`
frame, captures stdout up to the response, then asserts no extraneous bytes
were emitted before/after JSON-RPC framing.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest


@pytest.mark.integration
def test_mcp_stdio_writes_only_jsonrpc_framing_to_stdout() -> None:
    # Use a known-bad token so the process exits 1 on stderr — but BEFORE exiting,
    # the auth check must not have written anything to stdout.
    env = os.environ.copy()
    env["SMARTCOPILOT_MCP_TOKEN"] = "definitely-not-a-real-token-xxx"
    env.setdefault("SMARTCOPILOT_FERNET_KEY", "T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU=")
    env.setdefault("JWT_SIGNING_KEY", "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa")

    proc = subprocess.run(
        [sys.executable, "-m", "app.mcp.server", "--stdio"],
        env=env, capture_output=True, timeout=10, cwd="server",
    )
    assert proc.returncode == 1, f"stderr={proc.stderr.decode()!r}"
    # CRITICAL — stdout must be EMPTY when stdio mode fails auth before tool loop.
    assert proc.stdout == b"", f"stdio mode wrote {len(proc.stdout)} bytes to stdout: {proc.stdout!r}"
    assert b"AUTH ERROR" in proc.stderr
```

A second test (after a real MCP token is seeded) drives a full initialize / list_tools handshake — defer to Plan 06 acceptance, since seeding requires DB. The above test alone proves the no-stdout-leak invariant.
  </action>
  <verify>
    <automated>cd server && SMARTCOPILOT_FERNET_KEY=T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU= JWT_SIGNING_KEY=test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa pytest -x app/tests/integration/test_mcp_stdout_clean.py -v</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "stateless_http=True" server/app/mcp/server.py` >= 1
    - `grep -c "json_response=True" server/app/mcp/server.py` >= 1
    - `grep -c "transport=\"mcp_stdio\"" server/app/mcp/server.py` >= 1
    - `grep -c "transport=\"mcp_http\"" server/app/mcp/server.py` >= 1
    - `grep -c "validate_bearer" server/app/mcp/server.py` >= 2 (stdio + http paths)
    - `grep -E "^\s*print\(" server/app/mcp/server.py | grep -v "file=sys.stderr" | wc -l` returns 0 (no print to stdout)
    - `grep -c "raise NotImplementedError" server/app/mcp/server.py` returns 0 (Phase 1b stub gone)
    - The stdout-clean test passes.
    - `cd server && python -m app.mcp.server --http --port 0 --selftest` exits 0 with stdout empty.
  </acceptance_criteria>
  <done>MCP server.py replaces the Phase 1b stub; both transports build correct OperationContext; stdio writes nothing to stdout before tool loop entry.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: tools/ package — 14 real brain.* tools + capability_discovery (+ services/vault_resolver.py)</name>
  <files>server/app/services/vault_resolver.py, server/app/mcp/tools/__init__.py, server/app/mcp/tools/brain.py, server/app/mcp/tools/capability.py, server/app/tests/integration/test_mcp_tools.py</files>
  <read_first>
    - server/app/mcp/tools/__init__.py (Phase 1b — empty; replace)
    - server/app/services/pages.py (signatures the tools wrap — added in Plan 01)
    - server/app/services/capabilities.py (added in Plan 01)
    - server/app/auth/context.py (OperationContext fields)
    - server/app/vault/paths.py (validate_slug for remote=True calls — MCP-05)
    - server/app/models/vault.py (Vault model — owner_user_id + kind columns)
    - .planning/phases/01d-mcp-rest-api-cli/01d-PATTERNS.md (lines 110-176 — MCP tool → service call pattern)
  </read_first>
  <behavior>
    - resolve_user_vault_id(session, user_id) lives in `server/app/services/vault_resolver.py`; raises VaultNotFound if no private vault exists. Module imports nothing from FastAPI or app.mcp.* (transport-agnostic per REST-06).
    - brain_put: validates slug (validate_slug) when ctx.remote, resolves user's private vault_id, calls write_page in session_with_rls, captures slug + page_id locally before the session-with-rls block exits, returns `{"slug": str, "page_id": str, "version": int, "status": "ok"}`.
    - brain_get: read_page, returns `{slug, page_id, title, note_type, frontmatter, compiled_truth, timeline, content_hash, updated_at}`.
    - brain_search: search_pages_fts, returns the D-02 envelope `{results: [...], total: int, query: str, search_type: "fts_v1"}` — each result has the D-02 shape.
    - brain_list: list_pages → `{pages: [...], total: int}`.
    - brain_delete: soft_delete_page → `{slug, page_id, status: "deleted"}`. Service writes index_event row (already done in Phase 1c).
    - brain_history: get_page_history → `{page_id, slug, versions: [{version, content_hash, created_at}]}`.
    - brain_diff: get_page_diff → `{page_id, slug, from_version, to_version, compiled_truth_diff, timeline_diff}`. Returns `{"error": {"code": "not_found", ...}}` if either version is missing.
    - brain_revert: revert_page → `{slug, page_id, reverted_to: int, new_version: int}`.
    - brain_append_timeline: append_timeline → `{slug, page_id, status: "appended"}`.
    - brain_update_compiled_truth: writes the new compiled_truth via upsert_page (timeline preserved). Returns `{slug, page_id, status: "ok"}`.
    - brain_backlinks: get_backlinks_for_page → `{target_page_id, backlinks: [{page_id, slug, title}]}`.
    - brain_stats: vault_stats → `{vault_id, page_count, deleted_page_count, total_compiled_truth_bytes, last_indexed_at}`.
    - brain_health: vault_health → `{db_ok, fernet_ok, watchdog_alive}`.
    - capability_discovery: returns `get_capabilities()` (already a dict).
    - Every tool catches PageNotFound, TimelineViolation, SharedVaultWriteDenied, ValueError (slug invalid) and returns the structured `{"error": {"code": "...", "message": "..."}}` shape — never raises.
    - MCP-05 enforcement: when `ctx.remote=True` and the requested slug points to another user's vault, the tool returns `{"error": {"code": "forbidden", ...}}`. (vault_id is resolved from ctx.user_id; cross-vault reads are impossible by construction in Phase 1d.)
  </behavior>
  <action>
First create `server/app/services/vault_resolver.py` (transport-agnostic helper — REST-06 invariant):

```python
"""Vault resolution helper — transport-agnostic per REST-06.

Phase 1d: each user has exactly one private vault; resolve_user_vault_id returns it.
Imported by:
  - server/app/mcp/tools/brain.py    (Plan 02)
  - server/app/routes/pages.py        (Plan 03)
  - server/app/routes/search.py       (Plan 03)
  - server/app/routes/vault.py        (Plan 03)
  - server/app/cli/page.py            (Plan 05)
  - server/app/cli/stats.py           (Plan 05)

NO FastAPI imports. NO MCP imports. Lives in services/ so callers from any
transport can compose with it without crossing layer boundaries.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vault import Vault


class VaultNotFound(Exception):
    """Raised when a user has no private vault yet."""


async def resolve_user_vault_id(session: AsyncSession, user_id: uuid.UUID) -> uuid.UUID:
    row = (await session.execute(
        select(Vault.id).where(Vault.owner_user_id == user_id, Vault.kind == "private").limit(1)
    )).scalar_one_or_none()
    if row is None:
        raise VaultNotFound(f"no private vault for user {user_id}")
    return row
```

Then create the tools package starting with `server/app/mcp/tools/__init__.py`:

```python
"""MCP tools package — D-06 per-domain organisation.

Phase 1d ships REAL implementations for brain.* and capability_discovery.
All other tool modules contain STRUCTURED STUBS returning the D-05 payload.
Both transports (stdio + HTTP) call register_all_tools(mcp, ctx_factory)
to wire the same Pydantic-typed surface.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.auth.context import OperationContext


def register_all_tools(
    mcp: Any,
    ctx_factory: Callable[..., OperationContext],
) -> None:
    """Register every Phase 1d tool on the FastMCP server.

    ctx_factory is invoked per-tool-call: it returns the OperationContext for
    the current caller. For stdio it returns the same module-level ctx; for
    HTTP it builds a per-request ctx from Authorization headers.
    """
    from app.mcp.tools import (
        brain, capability, ingest, enrich, recipe, skill, jobs,
        maintain, entity, graph,
    )
    brain.register(mcp, ctx_factory)
    capability.register(mcp, ctx_factory)
    ingest.register(mcp, ctx_factory)
    enrich.register(mcp, ctx_factory)
    recipe.register(mcp, ctx_factory)
    skill.register(mcp, ctx_factory)
    jobs.register(mcp, ctx_factory)
    maintain.register(mcp, ctx_factory)
    entity.register(mcp, ctx_factory)
    graph.register(mcp, ctx_factory)
```

Create `server/app/mcp/tools/brain.py` — register all 13 brain.* tools. Each tool is `async def`, takes Pydantic-typed kwargs (see `<behavior>` above for shapes), calls a service helper inside `async for session in session_with_rls(ctx):`, catches domain exceptions, returns the documented dict shape.

**DetachedInstanceError mitigation (revision):** SQLAlchemy ORM objects fetched inside `async for session in session_with_rls(ctx):` may be expired/detached after the block exits because the session terminates and `expire_on_commit` is the default. ALWAYS capture primitive attributes (slug, page_id, version, etc.) into local variables BEFORE the `async for` block exits. Never reference `page.slug` or `page.id` in a return statement that runs after the session closes.

Skeleton for one tool (replicate this exact pattern for the rest — note the local-variable capture before block exit):

```python
"""Real Phase 1d MCP brain.* tool implementations (D-04)."""
from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any, Literal

import structlog
from pydantic import BaseModel, Field

from app.auth.context import OperationContext
from app.db_session import session_with_rls
from app.services.pages import (
    PageNotFound, SharedVaultWriteDenied, TimelineViolation,
    append_timeline, get_backlinks_for_page, get_page_diff,
    get_page_history, list_pages, read_page, revert_page,
    search_pages_fts, soft_delete_page, upsert_page, vault_health,
    vault_stats, write_page,
)
from app.services.vault_resolver import VaultNotFound, resolve_user_vault_id
from app.vault.paths import validate_slug

log = structlog.get_logger("smart_copilot.mcp.brain")


def _err(code: str, message: str, **details: Any) -> dict:
    payload = {"error": {"code": code, "message": message}}
    if details:
        payload["error"]["details"] = details
    return payload


class _PutIn(BaseModel):
    slug: str = Field(..., min_length=1, max_length=128)
    content: str = Field(..., min_length=0, max_length=10_000_000)
    namespace: Literal["private"] = "private"        # Phase 1d: private only


def register(mcp: Any, ctx_factory: Callable[..., OperationContext]) -> None:

    @mcp.tool(name="brain.put", description="Write a page to the user's private vault.")
    async def brain_put(slug: str, content: str, namespace: Literal["private"] = "private") -> dict:
        ctx = ctx_factory()
        try:
            payload = _PutIn(slug=slug, content=content, namespace=namespace)
        except Exception as exc:                       # noqa: BLE001
            return _err("validation_error", str(exc))
        if ctx.remote:
            try:
                validate_slug(payload.slug)
            except ValueError as exc:
                return _err("validation_error", str(exc))
        # First session: write the page. Capture primitives locally BEFORE the
        # block exits — page.slug/page.id are unsafe to read after the session
        # closes (DetachedInstanceError risk on expired ORM attributes).
        slug_out: str | None = None
        page_id_out: uuid.UUID | None = None
        async for session in session_with_rls(ctx):
            try:
                vault_id = await resolve_user_vault_id(session, ctx.user_id)
                page = await write_page(
                    session, ctx,
                    slug=payload.slug,
                    raw_content=payload.content.encode("utf-8"),
                    vault_id=vault_id,
                )
                # CAPTURE primitives BEFORE session.commit() / block exit:
                slug_out = page.slug
                page_id_out = page.id
                await session.commit()
            except VaultNotFound as exc:
                return _err("not_found", str(exc))
            except TimelineViolation as exc:
                return _err("timeline_violation", str(exc))
            except SharedVaultWriteDenied as exc:
                return _err("forbidden", str(exc))
        if slug_out is None or page_id_out is None:
            return _err("internal_error", "page write produced no result")
        # Second session: look up version count using the captured page_id.
        async for session in session_with_rls(ctx):
            history = await get_page_history(session, ctx, page_id=page_id_out)
        return {
            "slug": slug_out,
            "page_id": str(page_id_out),
            "version": history[0].version if history else 1,
            "status": "ok",
        }

    # ... brain_get, brain_search, brain_list, brain_delete, brain_history, brain_diff,
    # ... brain_revert, brain_append_timeline, brain_update_compiled_truth, brain_backlinks,
    # ... brain_stats, brain_health
    # All follow the exact same shape: validate input → session_with_rls → call service →
    # CAPTURE primitives into local variables → commit → exit block → return dict;
    # catch domain exceptions and return structured _err().
```

Implement ALL 13 brain.* tools in `brain.py` following the skeleton. Apply the same local-variable capture rule to every tool that returns ORM-derived primitives (slug, id, version, etc.) after the session block exits. The full tool list with their input schemas and return shapes is enumerated in the `<behavior>` block above and in 01d-CONTEXT.md D-04.

Create `server/app/mcp/tools/capability.py`:

```python
"""capability_discovery MCP tool — REST-05 parity (D-15)."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.auth.context import OperationContext
from app.services.capabilities import get_capabilities


def register(mcp: Any, ctx_factory: Callable[..., OperationContext]) -> None:

    @mcp.tool(
        name="capability_discovery",
        description="Return server capabilities (transports, ingestion limits, clipboard availability, phase).",
    )
    async def capability_discovery() -> dict:
        _ = ctx_factory()                              # noqa: F841 — auth still required; ignored
        return get_capabilities()
```

Create `server/app/tests/integration/test_mcp_tools.py` with at least these tests (constructed `OperationContext`, no MCP SDK):

1. `test_brain_put_creates_page`: Construct ctx for seeded user, call `brain_put` directly (extracting the registered function from a stub mcp), assert page exists in DB.
2. `test_brain_get_returns_page_dict`: write a page, then call brain_get; assert returned shape matches the contract.
3. `test_brain_search_returns_fts_envelope`: write 3 pages, call brain_search with a query that matches one, assert envelope shape.
4. `test_brain_search_invalid_query_returns_validation_error`: empty string → `{"error": {"code": "validation_error"}}`.
5. `test_brain_history_diff_revert_round_trip`: put v1 → put v2 → history shows 2 versions → diff returns unified diff text → revert to v1 → page now matches v1.
6. `test_capability_discovery_matches_get_capabilities`: returned dict equals `services.capabilities.get_capabilities()`.
7. `test_remote_true_invalid_slug_rejected`: ctx with `remote=True`, slug `"BAD SLUG"`, brain_put returns `validation_error`.
8. `test_brain_health_returns_status`: brain_health returns dict with db_ok/fernet_ok/watchdog_alive keys.

Tests use a tiny `_FakeMcp` class that captures registered tools so they can be called directly without spawning the full SDK runtime:

```python
class _FakeMcp:
    def __init__(self) -> None:
        self.tools: dict[str, Any] = {}

    def tool(self, *, name: str, description: str = "") -> Any:    # noqa: ARG002
        def deco(fn: Any) -> Any:
            self.tools[name] = fn
            return fn
        return deco
```
  </action>
  <verify>
    <automated>cd server && SMARTCOPILOT_FERNET_KEY=T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU= JWT_SIGNING_KEY=test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa pytest -x app/tests/integration/test_mcp_tools.py -v</automated>
  </verify>
  <acceptance_criteria>
    - File `server/app/services/vault_resolver.py` exists; `grep -c "async def resolve_user_vault_id" server/app/services/vault_resolver.py` == 1; `grep -c "class VaultNotFound" server/app/services/vault_resolver.py` == 1.
    - `grep -E "from fastapi|import fastapi|from app.mcp" server/app/services/vault_resolver.py | wc -l` returns 0 (transport-agnostic invariant).
    - File `server/app/mcp/tools/brain.py` exists with `grep -E '@mcp\.tool\(name="brain\.(put|get|search|list|delete|history|diff|revert|append_timeline|update_compiled_truth|backlinks|stats|health)"' server/app/mcp/tools/brain.py | wc -l` >= 13
    - `grep -E '@mcp\.tool\(name="capability_discovery"' server/app/mcp/tools/capability.py | wc -l` == 1
    - `grep -c "session_with_rls" server/app/mcp/tools/brain.py` >= 13 (one per tool)
    - `grep -c "from app.services.vault_resolver import" server/app/mcp/tools/brain.py` >= 1
    - `grep -E "from fastapi|HTTPException" server/app/mcp/tools/ -r | wc -l` returns 0 (transport boundary preserved)
    - `grep -c "register_all_tools" server/app/mcp/tools/__init__.py` == 1
    - All 8 tests in `test_mcp_tools.py` pass.
    - `cd server && ruff check app/mcp/tools/ app/services/vault_resolver.py` exits 0.
  </acceptance_criteria>
  <done>14 real Phase 1d MCP tools registered, all calling `services/` via `session_with_rls`; vault_resolver lives in services/ (transport-agnostic); all backed by integration tests.</done>
</task>

<task type="auto">
  <name>Task 3: 8 stub tool modules — ingest/enrich/recipe/skill/jobs/maintain/entity/graph</name>
  <files>server/app/mcp/tools/ingest.py, server/app/mcp/tools/enrich.py, server/app/mcp/tools/recipe.py, server/app/mcp/tools/skill.py, server/app/mcp/tools/jobs.py, server/app/mcp/tools/maintain.py, server/app/mcp/tools/entity.py, server/app/mcp/tools/graph.py</files>
  <read_first>
    - server/app/mcp/tools/__init__.py (register signature contract — must match)
    - .planning/phases/01d-mcp-rest-api-cli/01d-CONTEXT.md (D-05 stub payload exact shape)
    - .planning/phases/01d-mcp-rest-api-cli/01d-PATTERNS.md lines 154-164 (stub_tool template)
  </read_first>
  <behavior>
    - Each module exposes `def register(mcp, ctx_factory)` that calls `@mcp.tool(name=..., description=...)` for each MCP-06 stub tool the module owns.
    - Each stub tool is async and returns `{"error": {"code": "not_implemented", "message": "tool available in Phase X", "available_in_phase": "X"}}`.
    - Tools are discoverable: a `list_tools` enumeration over the registered `_FakeMcp.tools` shows every name.
    - `available_in_phase` mapping (per ROADMAP.md):
        - ingest.* → "3"
        - enrich.* → "3"
        - recipe.* → "3"
        - skill.* → "3"
        - jobs.* → "7"
        - maintain.* → "4"
        - brain.entity.* → "3"
        - brain.graph.* → "2b"
  </behavior>
  <action>
For EACH of the 8 modules, create the file with this exact template (substitute names/phase per the mapping above):

```python
"""<module> stubs — D-05 not_implemented payload, registered + discoverable.

Phase 1d does NOT implement these tools; they ship as stubs so MCP clients can
discover the full surface and surface a useful error rather than NOT_FOUND.
NOT_FOUND is reserved for unregistered tools (D-05).
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.auth.context import OperationContext

_AVAILABLE_IN_PHASE = "<phase>"      # e.g. "3" for ingest, "7" for jobs

_TOOLS: tuple[tuple[str, str], ...] = (
    ("<tool.name>", "<short description>"),
    # ...
)


def _stub() -> dict:
    return {
        "error": {
            "code": "not_implemented",
            "message": f"tool available in Phase {_AVAILABLE_IN_PHASE}",
            "available_in_phase": _AVAILABLE_IN_PHASE,
        }
    }


def register(mcp: Any, ctx_factory: Callable[..., OperationContext]) -> None:    # noqa: ARG001
    for name, desc in _TOOLS:
        @mcp.tool(name=name, description=desc)
        async def _stub_tool(**kwargs: Any) -> dict:                              # noqa: ARG001
            return _stub()
```

Tool catalogues (MCP-06 list scoped to Phase 1d stubs):

- `ingest.py` — `("ingest.idea", "..."), ("ingest.media", "..."), ("ingest.meeting", "...")`
- `enrich.py` — `("enrich.entity", "...")`
- `recipe.py` — `("recipe.run", "...")`
- `skill.py` — `("skill.list", "..."), ("skill.get", "..."), ("skill.run", "...")`
- `jobs.py` — `("jobs.submit", "..."), ("jobs.status", "..."), ("jobs.cancel", "...")`
- `maintain.py` — `("maintain.run", "..."), ("maintain.report", "...")`
- `entity.py` — `("brain.entity.get", "..."), ("brain.entity.merge", "..."), ("brain.entity.list", "...")`
- `graph.py` — `("brain.graph.traverse", "...")`

(That's 17 stubs — total tool surface 14 real + 17 stubs = 31, satisfying MCP-06 ≥30.)

EXTEND `server/app/tests/integration/test_mcp_tools.py` (created in Task 2) with:

```python
def test_all_stub_tools_return_not_implemented_payload(_fake_mcp_with_all_tools_registered) -> None:
    fake = _fake_mcp_with_all_tools_registered                # fixture from Task 2
    stub_names = [
        "ingest.idea", "ingest.media", "ingest.meeting",
        "enrich.entity", "recipe.run",
        "skill.list", "skill.get", "skill.run",
        "jobs.submit", "jobs.status", "jobs.cancel",
        "maintain.run", "maintain.report",
        "brain.entity.get", "brain.entity.merge", "brain.entity.list",
        "brain.graph.traverse",
    ]
    for name in stub_names:
        result = await fake.tools[name]()
        assert result["error"]["code"] == "not_implemented"
        assert "available_in_phase" in result["error"]


def test_total_tool_count_at_least_30() -> None:
    # MCP-06 acceptance: ≥30 tools registered.
    fake = _fake_mcp_with_all_tools_registered
    assert len(fake.tools) >= 30
```
  </action>
  <verify>
    <automated>cd server && SMARTCOPILOT_FERNET_KEY=T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU= JWT_SIGNING_KEY=test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa pytest -x app/tests/integration/test_mcp_tools.py::test_all_stub_tools_return_not_implemented_payload app/tests/integration/test_mcp_tools.py::test_total_tool_count_at_least_30 -v</automated>
  </verify>
  <acceptance_criteria>
    - All 8 stub modules exist under `server/app/mcp/tools/`.
    - `grep -l "not_implemented" server/app/mcp/tools/*.py | wc -l` >= 8
    - `grep -h "@mcp.tool" server/app/mcp/tools/*.py | wc -l` >= 31 (14 real + 17 stubs)
    - The two new tests pass.
    - `cd server && ruff check app/mcp/tools/` exits 0.
  </acceptance_criteria>
  <done>Stub coverage complete; total registered tool count ≥30; every stub returns the D-05 payload.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| MCP client → MCP server (stdio) | Untrusted bytes on stdin; SMARTCOPILOT_MCP_TOKEN env var is the only auth |
| MCP client → MCP server (HTTP) | Untrusted Authorization header per request |
| Tool function → service layer | OperationContext is the only handoff; FastAPI types forbidden |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-01d02-01 | Spoofing | MCP stdio token | mitigate | `validate_bearer` on bootstrap; missing/invalid token → exit 1, no tool surface exposed. |
| T-01d02-02 | Spoofing | MCP HTTP token | mitigate | Per-request `validate_bearer` on Authorization header; failure returns 401 via SDK auth hook. |
| T-01d02-03 | Information Disclosure | stdio mode log leaks via stdout | mitigate | configure_logging routes structlog to stderr; explicit grep gate `grep -E "^\s*print\(" ... | grep -v file=sys.stderr` returns 0 in CI. TEST-03 stdout-clean test enforced. |
| T-01d02-04 | Information Disclosure | cross-vault read via brain_get | mitigate | `resolve_user_vault_id(ctx.user_id)` always resolves to the caller's own vault; cross-user reads are impossible by construction in Phase 1d. RLS via `session_with_rls` is the second layer. |
| T-01d02-05 | Tampering | brain_put with crafted slug | mitigate | `validate_slug(slug)` for `ctx.remote=True`; rejects `..`, slashes, control chars. Service layer also validates. |
| T-01d02-06 | Elevation of Privilege | brain_revert called by remote=true non-admin | accept (Phase 1d) → mitigate (Phase 6) | brain_revert is service-controlled; revert_page enforces no timeline mutation by the caller (the historic version is preserved). Audit logging (OBS-03) deferred to Phase 6. |
| T-01d02-07 | Repudiation | tool calls not auditable | accept | Audit log integration is Phase 6 (OBS-03). index_events table already records page mutations from the service layer. |
| T-01d02-08 | DoS | brain_put with 10MB content | mitigate | `_PutIn.content` has `max_length=10_000_000`; FastMCP applies its own request size limit. |
| T-01d02-09 | Spoofing | unregistered tool invocation | accept | MCP protocol returns NOT_FOUND for unregistered names; D-05 reserves NOT_FOUND for this case (vs. registered stubs returning not_implemented). |
| T-01d02-10 | Tampering | OperationContext forgery in HTTP path | mitigate | ctx is built fresh per-request from a validated token inside a closure; tools can never receive a synthesised ctx because ctx_factory is the only path. |
</threat_model>

<verification>
After all 3 tasks:
1. `cd server && pytest -x app/tests/integration/test_mcp_tools.py app/tests/integration/test_mcp_stdout_clean.py -v` — all pass.
2. `cd server && pytest -x app/tests/vault/ -v` — Phase 1c regressions all green.
3. `cd server && ruff check app/mcp/ app/services/vault_resolver.py` exits 0.
4. `grep -rE "from fastapi|HTTPException" server/app/mcp/ | wc -l` returns 0 (MCP layer never imports FastAPI types — REST-06 invariant preserved).
5. `grep -rE "from fastapi|from app.mcp" server/app/services/vault_resolver.py | wc -l` returns 0 (services layer is transport-agnostic).
6. `cd server && python -m app.mcp.server --http --port 0 --selftest` exits 0 with empty stdout.
</verification>

<success_criteria>
- 14 real Phase 1d brain.* tools + capability_discovery registered and tested against PostgreSQL.
- 17 stub tools registered, every one returning the D-05 payload.
- `services/vault_resolver.py` ships as transport-agnostic; consumed by MCP, REST, and CLI without crossing layer boundaries.
- Stdio entry point reads SMARTCOPILOT_MCP_TOKEN, validates via auth.core, never writes to stdout before tool loop.
- HTTP entry point uses stateless_http=True + json_response=True, builds per-request OperationContext from Authorization header.
- TEST-03 stdout-clean integration test passes.
- MCP-01..MCP-08 satisfied.
</success_criteria>

<output>
After completion, create `.planning/phases/01d-mcp-rest-api-cli/01d-02-SUMMARY.md` listing: tool count by module, test results, any deviations from action.
</output>
