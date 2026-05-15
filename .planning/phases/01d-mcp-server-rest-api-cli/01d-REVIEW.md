---
phase: 01d-mcp-server-rest-api-cli
reviewed: 2026-05-11T14:00:00Z
depth: standard
files_reviewed: 33
files_reviewed_list:
  - server/app/services/pages.py
  - server/app/services/capabilities.py
  - server/app/services/vault_resolver.py
  - server/app/notify/publisher.py
  - server/app/notify/listener.py
  - server/app/mcp/server.py
  - server/app/mcp/tools/brain.py
  - server/app/mcp/tools/capability.py
  - server/app/mcp/tools/__init__.py
  - server/app/mcp/tools/ingest.py
  - server/app/mcp/tools/jobs.py
  - server/app/mcp/tools/maintain.py
  - server/app/mcp/tools/skill.py
  - server/app/mcp/tools/entity.py
  - server/app/mcp/tools/enrich.py
  - server/app/mcp/tools/recipe.py
  - server/app/mcp/tools/graph.py
  - server/app/routes/pages.py
  - server/app/routes/search.py
  - server/app/routes/vault.py
  - server/app/routes/ws.py
  - server/app/main.py
  - server/app/cli/main.py
  - server/app/cli/page.py
  - server/app/cli/doctor.py
  - server/app/cli/mcp_serve.py
  - server/app/cli/stats.py
  - server/app/cli/check_resolvable.py
  - server/app/cli/reconcile.py
  - server/app/tests/integration/test_mcp_tools.py
  - server/app/tests/integration/test_rest_mcp_parity.py
  - server/app/tests/integration/test_phase_1d_acceptance.py
  - server/app/tests/integration/test_cli_page.py
  - server/app/tests/integration/test_cli_doctor.py
  - server/alembic/versions/0004_phase_1d_search_vector.py
findings:
  critical: 2
  warning: 9
  info: 5
  total: 16
status: issues_found
---

# Phase 01d: Code Review Report

**Reviewed:** 2026-05-11T14:00:00Z
**Depth:** standard
**Files Reviewed:** 33
**Status:** issues_found

## Summary

Phase 1d implements MCP server (stdio + HTTP transports), REST API parity, pg_notify pub/sub, and a CLI. The codebase is generally well-structured with clean separation between services, transports, and auth layers. However, two critical bugs were found: a reference to an undefined variable in `brain.stats` (NameError at runtime) and a silent WebSocketDisconnect swallow in the WS handler (loses disconnect signal). Several session management issues exist where async for loops return without commit or rollback, leaving connections dangling. A closure-capture bug in stub tools causes all stubs to report Phase 3 even when their `_AVAILABLE_IN_PHASE` differs. The content-hash deduplication check in `brain.update_compiled_truth` and `append_timeline` will silently no-op on identical content.

---

## Critical Issues

### CR-01: `vault_id` undefined in `brain.stats` — NameError at runtime

**File:** `server/app/mcp/tools/brain.py:582-590`
**Issue:** `vault_id` is assigned inside the `async for session in session_with_rls(ctx):` block but referenced in the return statement outside that block. The variable will not exist if `VaultNotFound` is raised, but even if no exception is raised, Python's block scoping means `vault_id` is unbound outside the loop. This is a guaranteed NameError on every call.

```python
async for session in session_with_rls(ctx):
    try:
        vault_id = await resolve_user_vault_id(session, ctx.user_id)
        stats = await vault_stats(session, ctx, vault_id=vault_id)
    except VaultNotFound as exc:
        return _err("not_found", str(exc))

return {
    "vault_id": str(vault_id),   # NameError — vault_id is not in scope here
    ...
}
```

**Fix:**
```python
async for session in session_with_rls(ctx):
    try:
        vault_id = await resolve_user_vault_id(session, ctx.user_id)
        stats = await vault_stats(session, ctx, vault_id=vault_id)
        return {
            "vault_id": str(vault_id),
            "page_count": stats.live_pages,
            ...
        }
    except VaultNotFound as exc:
        return _err("not_found", str(exc))

return _err("internal_error", "session loop exited without result")
```

---

### CR-02: WebSocketDisconnect swallowed — disconnect signal lost

**File:** `server/app/routes/ws.py:92-93`
**Issue:** `except WebSocketDisconnect: pass` silently discards the disconnect event. While the loop will naturally break on the next `queue.get()` if the socket is gone, this prevents any disconnect-specific cleanup, logging, or graceful shutdown logic from running. In particular, `ws.client_state` is never re-checked after a disconnect, so any events queued between the disconnect and the next `queue.get()` will be lost.

```python
except WebSocketDisconnect:
    pass  # silent — disconnect signal is lost
finally:
    if queue is not None and user_id is not None:
        ...
```

**Fix:**
```python
except WebSocketDisconnect:
    log.info("ws_client_disconnected", user_id=str(user_id))
```

---

## Warnings

### WR-01: Session leaks from early return without commit/rollback in multiple brain tools

**File:** `server/app/mcp/tools/brain.py` — lines 155-159, 214-217, 254-257
**Issue:** Three tools (`brain.get`, `brain.search`, `brain.list`) return inside the `async for` block without calling `await session.commit()` or `await session.rollback()`. This leaves the session's transaction open. SQLAlchemy's async session holds the connection until the context manager exits (end of `async with`), but within the loop, returning without a commit means the read transaction is left open and the session's internal state may be inconsistent. More critically, the `async for session in session_with_rls(ctx):` context manager does not auto-commit on exit — the caller must explicitly commit.

Additionally, `brain_get` (line 158) returns inside the `async for` block without committing. The difference with `brain_put` (which DOES commit at line 95) is that `brain_get` is read-only, so no mutation occurs, but the dangling transaction still consumes a connection pool slot until the context manager cleans up.

```python
async for session in session_with_rls(ctx):
    try:
        vault_id = await resolve_user_vault_id(session, ctx.user_id)
        page = await read_page(session, vault_id=vault_id, slug=slug)
        return { ... }   # returns here — session exits cleanly via context manager, but no commit
    except PageNotFound:
        return _err("not_found", f"Page {slug!r} not found")
    except VaultNotFound as exc:
        return _err("not_found", str(exc))

return _err("internal_error", "session loop exited without result")
```

**Fix:** For read-only tools, add `await session.commit()` before the return, or restructure to return outside the loop (matching the pattern used in `brain.stats`).

---

### WR-02: Missing `__future__` import in `capability.py` — `Any` type hint will fail

**File:** `server/app/mcp/tools/capability.py:16`
**Issue:** The `register` function uses `Any` type hint but `from typing import Any` is not present. In Python 3.10+, this raises a `NameError` at import time since `from __future__ import annotations` only defers annotation evaluation, not runtime name resolution. The file imports `Callable` correctly but omits `Any`.

```python
def register(mcp: Any, ctx_factory: Callable[..., OperationContext]) -> None:  # No `Any` imported
```

**Fix:**
```python
from __future__ import annotations

from collections.abc import Callable
from typing import Any  # add this import

from app.auth.context import OperationContext
from app.services.capabilities import get_capabilities
```

---

### WR-03: Stub tool closure-capture bug — all stubs return Phase 3

**File:** All stub files: `ingest.py`, `enrich.py`, `recipe.py`, `skill.py`, `jobs.py`, `maintain.py`, `entity.py`, `graph.py` — line ~48-49 each
**Issue:** The `register` function loops over `_TOOLS` and defines a nested function `_stub_tool` that captures `desc` (and `name`) by closure. Because the function is defined inside the loop without late binding, ALL registered stub tools end up using the LAST values of `desc` and `name` from the loop. This means every stub tool has the last tool's name and description. The `_AVAILABLE_IN_PHASE` is at module level so that's correct, but `name` is wrong (all tools get the last tool's name) and `desc` is wrong (all stubs show the last description). Only `code: "not_implemented"` and `available_in_phase` are correct.

```python
def register(mcp: Any, ctx_factory: Callable[..., OperationContext]) -> None:
    for name, desc in _TOOLS:
        @mcp.tool(name=name, description=desc)
        async def _stub_tool(**kwargs: Any) -> dict:
            return _stub()  # name and desc are from last iteration only
```

**Fix:**
```python
def register(mcp: Any, ctx_factory: Callable[..., OperationContext]) -> None:
    for name, desc in _TOOLS:
        @mcp.tool(name=name, description=desc)
        async def _stub_tool(n=name, d=desc, **_kwargs: Any) -> dict:  # bind defaults
            return {"error": {"code": "not_implemented", "message": f"tool available in Phase {_AVAILABLE_IN_PHASE}", "available_in_phase": _AVAILABLE_IN_PHASE}}
```

---

### WR-04: `update_compiled_truth` REST endpoint skips content-hash deduplication

**File:** `server/app/routes/pages.py:235-266`
**Issue:** `update_compiled_truth_endpoint` computes a `new_hash` via xxhash on the new truth + timeline but then passes `content_hash=new_hash` to `upsert_page`. However, the `write_page` service path (which goes through `parse_vault_file`) computes a different hash via `ParsedPage`. More critically, if the new compiled truth has the same hash as the existing page's hash (because only the `compiled_truth` field changed but the content is semantically identical to what was previously saved), the deduplication in `upsert_page` will silently return the existing page without any update. This means a user who deliberately updates their compiled truth will see no change and get `status: "ok"` with no indication that the write was a no-op.

```python
new_hash = xxhash.xxh64(new_content).hexdigest()
parsed = ParsedPage(
    ...
    content_hash=new_hash,
)
new_page = await upsert_page(..., parsed=parsed, ...)  # existing.content_hash may equal new_hash
await session.commit()
return {"slug": new_page.slug, ...}  # returns existing page if hash matched — silent no-op
```

**Fix:** Compare `new_hash` against `page.content_hash` before calling `upsert_page` and return an early response indicating no change if they match.

---

### WR-05: `revert_page` endpoint doesn't check history is non-empty before `history[0]`

**File:** `server/app/routes/pages.py:342-348`
**Issue:** After `revert_page` succeeds, the endpoint calls `get_page_history` and accesses `history[0].version` without checking `if not history`. If for some reason the page has no version history (shouldn't happen — VAULT-08 creates v1 on page creation), this will raise an `IndexError`.

```python
history = await get_page_history(session, ctx, page_id=page.id)
return {
    ...
    "new_version": history[0].version,  # IndexError if history is empty
}
```

**Fix:**
```python
history = await get_page_history(session, ctx, page_id=page.id)
return {
    "slug": page.slug,
    "page_id": str(page.id),
    "reverted_to": payload.target_version,
    "new_version": history[0].version if history else 1,
}
```

---

### WR-06: Inconsistent session commit discipline across brain tools

**File:** `server/app/mcp/tools/brain.py`
**Issue:** The five mutating tools have divergent commit patterns:
- `brain.put` (line 95): commits inside loop, then opens a SECOND session for history lookup
- `brain.delete` (line 284): commits inside loop — correct
- `brain.revert` (lines 415-417): commits inside loop, then opens a second session for history
- `brain.update_compiled_truth` (line 509): commits inside loop — correct
- `brain.append_timeline` (line 456): commits inside loop — correct

The two-session pattern in `brain.put` and `brain.revert` is intentional (primitive capture before session closes) but the inconsistency in error paths is subtle. Importantly, `brain.update_compiled_truth` does NOT call `session.commit()` before the early return paths at lines 510-513, which is fine since it's a write inside the loop that committed before the return.

**Fix:** Consolidate commit pattern — mutating tools should commit inside the loop before returning, matching `brain.delete`.

---

### WR-07: `brain.append_timeline` silently no-ops when content-hash deduplication triggers

**File:** `server/app/mcp/tools/brain.py:439-462`
**Issue:** `append_timeline` calls the service which calls `upsert_page`. If the timeline append produced content with the same hash as before (edge case: appending an empty or whitespace-only entry), `upsert_page` at line 176-177 will return the existing page without any timeline modification. The service returns this page, the tool does `await session.commit()` (on the unchanged session), and returns `{"slug": slug, "status": "appended"}` — a lie.

**Fix:** After the service call, compare `page.timeline` with what was expected, or add a pre-check in the service to reject empty/duplicate entries.

---

### WR-08: `brain.update_compiled_truth` uses `content_hash` from existing page, breaking deduplication

**File:** `server/app/mcp/tools/brain.py:494-515`
**Issue:** The `ParsedPage` is built with `content_hash=page.content_hash` (line 500 — the ORIGINAL hash). This means:
1. If the user updates compiled truth to the SAME content that was there before, `upsert_page` will see `existing.content_hash == parsed.content_hash` and return the existing page without any update.
2. The tool will report `status: "ok"` and return the existing page.

The REST endpoint at `routes/pages.py:249` correctly computes a new hash, but the MCP tool does not.

**Fix:** Compute the new content hash from the new compiled_truth:
```python
import xxhash
new_content = (compiled_truth + "\n---\n" + (page.timeline or "")).encode("utf-8")
new_hash = xxhash.xxh64(new_content).hexdigest()
parsed = ParsedPage(..., content_hash=new_hash, ...)
```

---

### WR-09: `brain.update_compiled_truth` reads `page.timeline` after session may be closed

**File:** `server/app/mcp/tools/brain.py:496-499`
**Issue:** `page.timeline` is accessed via ORM object (`page.timeline or ""`) inside the async for block, but the session is managed by `session_with_rls` context manager. The page object will be detached from the session when the context manager exits. However, the access happens inside the block so it is safe. This is a note for future警惕: the DetachedInstanceError mitigations documented in the file header are correctly applied in `brain.put` and `brain.revert` (where primitives are captured), but `brain.update_compiled_truth` directly passes ORM objects to `upsert_page`. Since `upsert_page` is called inside the same session block, this is fine — but it is inconsistent with the documented pattern.

**Fix:** Be consistent with the DetachedInstanceError mitigation pattern: capture `page.timeline` and `page.frontmatter` into local variables before the session closes.

---

## Info

### IN-01: `brain.backlinks` does not return error when vault not found

**File:** `server/app/mcp/tools/brain.py:526-561`
**Issue:** `brain.backlinks` catches `VaultNotFound` and returns `_err("not_found", str(exc))` but does not catch `PageNotFound`. If the page doesn't exist, the `async for` loop exits without a return and falls through to the final `return {"target_page_id": ..., "backlinks": [...]}` where `target_page_id_out` is `None` (never set) and `backlinks` references an undefined variable.

**Fix:** Add `except PageNotFound: return _err("not_found", ...)` alongside the existing `except VaultNotFound`.

---

### IN-02: `_find_slug_match` — SQL injection via `ILIKE` pattern not parameterized

**File:** `server/app/services/pages.py:122-123`
**Issue:** The `like_pattern` is constructed by f-string interpolation: `like_pattern = f"%/{search_target}"`. While `search_target` is derived from `target_text.lstrip("/").replace(" ", "-").lower()`, which normalizes the input, there is no explicit validation that it doesn't contain SQL wildcard characters (`%`, `_`). For example, a wikilink `[[notes/%]]` could produce a pattern `%/%` which is a valid SQL LIKE pattern that matches any slug containing a slash. This is low severity (only affects link resolution accuracy, not data corruption or unauthorized access) but worth noting.

**Fix:** Escape `%` and `_` in `search_target` before building the pattern:
```python
escaped = search_target.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
like_pattern = f"%/{escaped}"
```

---

### IN-03: `brain.get` — `page.updated_at` accessed on detached ORM object in return

**File:** `server/app/mcp/tools/brain.py:143-153`
**Issue:** The return dict is built inside the `async for` block, so the `page` ORM object is still attached when `page.updated_at.isoformat()` is called. This is safe but the file header documents the "capture primitives BEFORE session closes" pattern, and this tool doesn't follow it — it builds the full return dict inside the loop accessing ORM attributes directly. If the code is refactored to return outside the loop, this will break with a DetachedInstanceError.

**Fix:** Capture primitives before the return, even inside the loop, to follow the documented pattern consistently:
```python
page_id = page.id
slug = page.slug
title = page.frontmatter.get("title") if page.frontmatter else None
...
return {"page_id": str(page_id), "slug": slug, "title": title, ...}
```

---

### IN-04: `check_resolvable` CLI — hardcoded `DEFAULT_SKILLS_DIR` path

**File:** `server/app/cli/check_resolvable.py:12`
**Issue:** The default skills directory path `/vaults/shared/.skills` is hardcoded as a module-level constant. This path may not match the actual deployment path configured via environment variables or settings.

**Fix:** Read from `settings.skills_dir` or a `SMARTCOPILOT_SKILLS_DIR` environment variable instead of hardcoding.

---

### IN-05: `_handle_stats` — bare `except` clause

**File:** `server/app/cli/stats.py:43-58`
**Issue:** `_handle_stats` wraps the entire body in `async for session in session_with_rls(ctx):` but if `VaultNotFound` is raised, it prints and returns 2. However, if ANY other exception occurs, the function silently returns `None` (no explicit return at the end), which means the caller sees a `None` return that `asyncio.run` converts to exit code 0. Any unexpected error (e.g., DB connection failure, AttributeError) will be silently ignored.

**Fix:** Add an explicit error handler:
```python
try:
    vault_id = await resolve_user_vault_id(session, ctx.user_id)
except VaultNotFound as exc:
    print(f"error: {exc}", file=sys.stderr)
    return 2
stats = await vault_stats(session, ctx, vault_id=vault_id)
```

---

_Reviewed: 2026-05-11T14:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_