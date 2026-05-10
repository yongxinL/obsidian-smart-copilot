---
phase: 01c
plan: 05
type: execute
wave: 3
depends_on:
  - "01c-04"
files_modified:
  - server/app/vault/watcher.py
  - server/app/tests/vault/test_watcher.py
autonomous: true
requirements:
  - IDX-01
  - IDX-02
  - IDX-03

must_haves:
  truths:
    - "VaultEventHandler uses asyncio.run_coroutine_threadsafe exclusively (not call_soon_threadsafe) for async indexing work"
    - "Per-path debounce using threading.Timer dict; rapid events for same path coalesced to single index call"
    - "on_deleted triggers soft_delete_vault_file (not index_vault_file)"
    - "Watchdog uses Observer() (inotify on Linux), not PollingObserver()"
    - "Graceful shutdown cancels all pending timers before stopping observer"
    - "index_vault_file skips DB write when content_hash unchanged (IDX-03)"
    - "test_watcher.py tests pass (not SKIP)"
  artifacts:
    - path: "server/app/vault/watcher.py"
      provides: "VaultEventHandler, index_vault_file, soft_delete_vault_file, main() entry point"
      contains: "run_coroutine_threadsafe"
    - path: "server/app/tests/vault/test_watcher.py"
      provides: "Integration tests for IDX-01, IDX-02, IDX-03"
  key_links:
    - from: "server/app/vault/watcher.py"
      to: "asyncio.run_coroutine_threadsafe"
      via: "D-06: only correct primitive for submitting coroutines from OS thread to asyncio loop"
      pattern: "run_coroutine_threadsafe"
    - from: "server/app/vault/watcher.py"
      to: "server/app/services/pages.py"
      via: "index_vault_file calls upsert_page with enforce_timeline=False (D-03 watchdog bypass)"
      pattern: "upsert_page"
    - from: "server/app/vault/watcher.py"
      to: "server/app/db_session.py:session_with_rls"
      via: "index_vault_file uses session_with_rls(system_ctx) — GUC discipline"
      pattern: "session_with_rls"
---

<objective>
Replace the Phase 1a watchdog stub with a real inotify-based watchdog implementation. The watchdog runs as a supervisord process, detects vault file changes via inotify, debounces per-path at 750ms, and submits async indexing work via `asyncio.run_coroutine_threadsafe`. Then replace the test_watcher.py stubs with real integration tests.

Purpose: IDX-01/02/03 mandate real filesystem watching. The watchdog is the second ingest path alongside the reconciler.

Output: `vault/watcher.py` real implementation and `test_watcher.py` with passing tests.
</objective>

<context>
@.planning/phases/01c-vault-watchdog-indexer/01c-CONTEXT.md
@.planning/phases/01c-vault-watchdog-indexer/01c-RESEARCH.md

<interfaces>
<!-- From server/app/scheduler/run.py — asyncio + signal + structlog entry point pattern -->
```python
async def _amain() -> int:
    configure_logging()
    log = structlog.get_logger("smart_copilot.scheduler")
    stop_event = asyncio.Event()
    def _stop(signum, _frame):
        stop_event.set()
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    await stop_event.wait()
    scheduler.shutdown(wait=False)
    return 0

def main() -> int:
    return asyncio.run(_amain())
```

<!-- D-06 handoff pattern (MUST use, NOT call_soon_threadsafe) -->
```python
import asyncio, threading
# In OS thread (watchdog event handler):
asyncio.run_coroutine_threadsafe(some_async_coro(arg), self._loop)
# NOT: self._loop.call_soon_threadsafe(lambda: asyncio.ensure_future(coro))
```

<!-- D-07 per-path debounce pattern -->
```python
class VaultEventHandler(FileSystemEventHandler):
    def __init__(self, loop, debounce_ms):
        self._loop = loop
        self._debounce_s = debounce_ms / 1000.0
        self._timers: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    def _schedule_index(self, path: str) -> None:
        with self._lock:
            if path in self._timers:
                self._timers[path].cancel()
            timer = threading.Timer(self._debounce_s, self._fire_index, args=(path,))
            self._timers[path] = timer
            timer.start()

    def _fire_index(self, path: str) -> None:
        with self._lock:
            self._timers.pop(path, None)
        asyncio.run_coroutine_threadsafe(index_vault_file(path), self._loop)
```

<!-- From server/app/db_session.py — session_with_rls pattern for watchdog -->
```python
from app.auth.context import system_operation_context
from app.db_session import session_with_rls

async def index_vault_file(path: str) -> None:
    ctx = system_operation_context(request_id="watchdog", client_name="watcher")
    async for session in session_with_rls(ctx):
        # ... parse file, upsert_page with enforce_timeline=False, commit ...
        await session.commit()
```

<!-- From server/app/services/pages.py (Plan 04 output) -->
```python
from app.services.pages import upsert_page, soft_delete_page, read_page, PageNotFound
from app.vault.parser import parse_vault_file
from app.vault.paths import sanitize_filename_to_slug
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Replace vault/watcher.py stub with real watchdog implementation</name>
  <read_first>
    - server/app/vault/watcher.py (current stub — understand what to replace; confirms it's a basic sleep loop)
    - server/app/scheduler/run.py (full file — asyncio + signal + structlog entry point pattern to copy exactly)
    - server/app/scheduler/jobs/prune_login_attempts.py (session_with_rls usage pattern in async function)
    - server/app/services/pages.py (upsert_page, soft_delete_page, read_page signatures — Plan 04 output)
    - server/app/vault/parser.py (parse_vault_file — Plan 03 output)
    - server/app/vault/paths.py (sanitize_filename_to_slug — Plan 03 output)
    - server/app/settings.py (vault_watch_debounce_ms field — Plan 01 output)
    - .planning/phases/01c-vault-watchdog-indexer/
    - .planning/phases/01c-vault-watchdog-indexer/01c-RESEARCH.md (Pattern 4: VaultEventHandler; Pitfall 2: loop must be running before run_coroutine_threadsafe; Pitfall 6: cancel timers on shutdown; Anti-pattern: PollingObserver)
    - .planning/phases/01c-vault-watchdog-indexer/01c-CONTEXT.md (D-06 run_coroutine_threadsafe; D-07 debounce 750ms; D-03 watchdog bypass; IDX-01: Observer not PollingObserver)
  </read_first>
  <files>server/app/vault/watcher.py</files>
  <behavior>
    - VaultEventHandler.on_modified and on_created: call _schedule_index(path), NOT _fire_index directly
    - VaultEventHandler.on_deleted: call run_coroutine_threadsafe(soft_delete_vault_file(path), loop) immediately (no debounce on delete)
    - _schedule_index: cancel any pending timer for same path, schedule new Timer for debounce_s seconds
    - _fire_index: pop path from timers dict, call run_coroutine_threadsafe(index_vault_file(path), loop)
    - index_vault_file(path): read file bytes, compute hash, compare with DB; if changed parse and upsert_page with enforce_timeline=False; insert IndexEvent
    - soft_delete_vault_file(path): derive slug from path, load page from DB, call soft_delete_page
    - Graceful shutdown (SIGTERM/SIGINT): set stop_event, cancel all pending timers in _timers dict, stop observer, join observer
    - main() uses asyncio.run(_amain()); loop reference obtained INSIDE _amain via asyncio.get_running_loop()
    - No PollingObserver — always watchdog.observers.Observer (inotify on Linux)
    - Structured logging with structlog (not stdlib logging)
  </behavior>
  <action>
**CRITICAL RULES (must be followed exactly, not approximated):**
- D-06: Use `asyncio.run_coroutine_threadsafe(coro, loop)` ONLY. Never `loop.call_soon_threadsafe` for async indexing. Never `asyncio.run()` inside event handlers (creates new loop in wrong thread).
- D-07: Per-path debounce dict with `threading.Timer`. Cancel pending timer on new event for same path.
- Pitfall 2: Obtain `loop = asyncio.get_running_loop()` INSIDE `async def _amain()`, then pass to `VaultEventHandler`. NEVER call `asyncio.get_event_loop()` at module import time.
- Pitfall 6: In the shutdown sequence (after `await stop_event.wait()`), cancel ALL timers in `handler._timers` before stopping the observer.
- IDX-01: `from watchdog.observers import Observer` (not `PollingObserver`).
- D-03: `index_vault_file` calls `upsert_page(session, ctx, ..., enforce_timeline=False)` — watchdog NEVER rejects timeline mutations.
- Structlog: replace the stdlib `logging` usage in the existing stub with `structlog` + `configure_logging()`.
- Log a structlog warning when timeline mutation is detected by watchdog (D-03): `log.warning("timeline_mutated_by_filesystem", slug=slug)`.

**Implement `server/app/vault/watcher.py`** following the RESEARCH.md Pattern 4 pattern. The file must:

1. Replace all stdlib `logging` with `structlog` and `configure_logging()` from `app.logging.redaction`
2. Define `VaultEventHandler(FileSystemEventHandler)` with:
   - `__init__(self, loop, debounce_ms, vault_root_path)` — store all three
   - `_schedule_index(path)` — per-path debounce
   - `_fire_index(path)` — submit to asyncio loop
   - `on_modified(event)`, `on_created(event)` — call `_schedule_index` if not directory
   - `on_deleted(event)` — call `run_coroutine_threadsafe(soft_delete_vault_file(...), loop)` immediately
3. Define `async def index_vault_file(path: str) -> None:` — read bytes, hash compare, parse, upsert
4. Define `async def soft_delete_vault_file(path: str) -> None:` — derive slug, load page, soft_delete
5. Define `async def _amain() -> int:` — configure_logging, get loop, build handler, build Observer, schedule handler on vault_root, start observer, signal handlers, await stop_event, shutdown cleanup
6. Define `def main() -> int:` — `return asyncio.run(_amain())`
7. Keep `if __name__ == "__main__": sys.exit(main())`

The vault root path is read from `settings.vault_watch_path` OR derived from the environment. Since this setting does not exist yet (it was not in Plan 01), use a hardcoded default of `/vaults` for now and log a startup banner showing the watched path. Phase 1d will wire the real vault path from settings.
  </action>
  <verify>
    <automated>cd /home/yongxin.Li/Documents/nexora/smart-copilot/server && python -c "
import py_compile; py_compile.compile('app/vault/watcher.py', doraise=True)
import ast, sys
tree = ast.parse(open('app/vault/watcher.py').read())
names = [n.id for n in ast.walk(tree) if isinstance(n, ast.Name)]
assert 'run_coroutine_threadsafe' in open('app/vault/watcher.py').read(), 'Missing run_coroutine_threadsafe'
assert 'call_soon_threadsafe' not in open('app/vault/watcher.py').read(), 'Forbidden: call_soon_threadsafe for async work'
print('watcher checks passed')
"</automated>
  </verify>
  <acceptance_criteria>
    - `server/app/vault/watcher.py` passes `py_compile` syntax check
    - File contains `run_coroutine_threadsafe` (D-06 mandatory handoff API)
    - File does NOT contain `call_soon_threadsafe` (D-06 override — forbidden for async indexing)
    - File does NOT contain `PollingObserver` (must use `Observer()` on Linux)
    - File does NOT contain `asyncio.run(` inside event handlers (Pitfall 2)
    - File contains `threading.Timer` (D-07 cancellable debounce)
    - File contains `enforce_timeline=False` in the index_vault_file upsert call (D-03)
    - File contains timer cancellation in shutdown sequence (Pitfall 6)
    - File contains `structlog.get_logger` (replaces stdlib logging)
    - File contains `asyncio.get_running_loop()` inside `_amain` (Pitfall 2 — not at module level)
  </acceptance_criteria>
  <done>vault/watcher.py real watchdog implementation: VaultEventHandler with per-path debounce, run_coroutine_threadsafe handoff, graceful shutdown, structlog logging</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Replace test_watcher.py stubs with real integration tests</name>
  <read_first>
    - server/app/tests/vault/test_watcher.py (current stubs to replace)
    - server/app/tests/vault/conftest.py (tmp_vault_dir fixture — provides temp directory)
    - server/app/vault/watcher.py (just implemented — VaultEventHandler API)
    - server/app/vault/parser.py (parse_vault_file — used to understand what index_vault_file does)
    - .planning/phases/01c-vault-watchdog-indexer/01c-RESEARCH.md (scheduler job test pattern for understanding async test structure)
    - .planning/phases/01c-vault-watchdog-indexer/01c-RESEARCH.md (IDX-01 latency requirement: detect within 1 second; Pitfall 2: loop must be running)
  </read_first>
  <files>server/app/tests/vault/test_watcher.py</files>
  <behavior>
    - test_file_detection_latency: write a file to tmp_vault_dir, start Observer briefly, confirm index_vault_file was called within 1 second (IDX-01)
    - test_handoff_api_uses_run_coroutine_threadsafe: verify VaultEventHandler uses asyncio.run_coroutine_threadsafe (not call_soon_threadsafe) — inspect source or use mock
    - test_hash_dedup_skips_unchanged_file: call index_vault_file twice with same bytes; verify DB write only happens once
    - test_debounce_coalesces_rapid_events: send 5 rapid events for same path within debounce window; confirm _fire_index called only once
    - test_on_deleted_triggers_soft_delete: write a file to DB, then call on_deleted; verify page.deleted_at is set
  </behavior>
  <action>
**Implementation notes for test_watcher.py:**

These tests bridge sync watchdog events and async operations. Use `asyncio` carefully:

**test_handoff_api_uses_run_coroutine_threadsafe:** This is a unit test (not integration). Read the source of `app/vault/watcher.py` and assert that `"run_coroutine_threadsafe"` appears in the source and `"call_soon_threadsafe"` does NOT appear as the handoff mechanism. This is a source-level guard (same pattern as `test_security_invariants.py` in Phase 1b):
```python
import inspect
from app.vault import watcher as watcher_module
source = inspect.getsource(watcher_module)
assert "run_coroutine_threadsafe" in source
assert "call_soon_threadsafe" not in source
```

**test_debounce_coalesces_rapid_events:** Unit test using mock. Create a `VaultEventHandler` with a very short debounce (10ms). Mock `_fire_index`. Call `_schedule_index(path)` 5 times rapidly. Use `time.sleep(0.1)` to let the timer fire. Assert `_fire_index` was called exactly once.

**test_hash_dedup_skips_unchanged_file:** Integration test. Write a vault file, call `index_vault_file(path)` directly (as a coroutine), assert page created. Call again with same file. Assert page_versions count is still 1 (no second version insert — hash unchanged).

**test_file_detection_latency:** Integration test. Write a file to `tmp_vault_dir`, create VaultEventHandler with `asyncio.get_running_loop()`, start an `Observer`, schedule handler for `tmp_vault_dir`. Wait up to 1.5 seconds. Assert `index_vault_file` was called (can mock it). Stop observer.

**test_on_deleted_triggers_soft_delete:** Integration test. Seed a page in DB, create a file for it, call `soft_delete_vault_file(path)` directly as a coroutine. Assert page.deleted_at is not None.

Mark integration tests with `pytest.mark.integration` and unit tests with `pytest.mark.unit`.
  </action>
  <verify>
    <automated>cd /home/yongxin.Li/Documents/nexora/smart-copilot/server && python -m pytest app/tests/vault/test_watcher.py -x -q --no-header 2>&1 | tail -8</automated>
  </verify>
  <acceptance_criteria>
    - `pytest app/tests/vault/test_watcher.py -x -q` exits 0 with all tests PASSED (no SKIP)
    - test_handoff_api_uses_run_coroutine_threadsafe is a source-level invariant check (no SKIP)
    - test_debounce_coalesces_rapid_events uses threading.Timer mock or real timer with short sleep
    - No `pytest.skip()` calls remain in the file
    - All 5 tests from the stub are implemented
  </acceptance_criteria>
  <done>test_watcher.py has 5 real passing tests covering IDX-01, IDX-02, IDX-03</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| OS filesystem → VaultEventHandler | inotify events from kernel; event.src_path is a filesystem path controlled by the OS |
| VaultEventHandler thread → asyncio loop | run_coroutine_threadsafe bridges the OS thread to the running event loop |
| index_vault_file → PostgreSQL | system_operation_context + session_with_rls; GUC set/reset discipline applies |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-01c05-01 | Tampering | Timeline mutations via filesystem | accept | D-03: watchdog processes the change and emits a warning; human filesystem access is trusted |
| T-01c05-02 | Denial of Service | inotify watch limit exhaustion | accept | Log warning when watching starts; Phase 6 doctor check; sysctl guidance documented in RESEARCH.md |
| T-01c05-03 | Denial of Service | Pending timer leak on crash | mitigate | Pitfall 6: cancel all timers in shutdown sequence (SIGTERM/SIGINT handler) |
| T-01c05-04 | Denial of Service | Rapid filesystem events flooding indexer | mitigate | Per-path debounce at 750ms (D-07); coalesces rapid saves from auto-save editors |
</threat_model>

<verification>
```bash
cd /home/yongxin.Li/Documents/nexora/smart-copilot/server

# Syntax and import check
python -c "from app.vault.watcher import VaultEventHandler, index_vault_file, soft_delete_vault_file, main; print('OK')"

# Source-level invariant checks
python -c "
import inspect
from app.vault import watcher as w
src = inspect.getsource(w)
assert 'run_coroutine_threadsafe' in src, 'Missing D-06 handoff'
assert 'call_soon_threadsafe' not in src, 'Forbidden call_soon_threadsafe found'
assert 'Observer()' in src or 'Observer(' in src, 'Missing inotify Observer'
assert 'PollingObserver' not in src, 'Forbidden PollingObserver'
print('All source invariants OK')
"

# Watcher tests
python -m pytest app/tests/vault/test_watcher.py -v --no-header
```
</verification>

<success_criteria>
- `vault/watcher.py` replaces stub with real VaultEventHandler using run_coroutine_threadsafe (D-06)
- Per-path debounce with threading.Timer and cancel (D-07)
- Observer() used (not PollingObserver) — inotify on Linux (IDX-01)
- Graceful shutdown cancels pending timers (Pitfall 6)
- `index_vault_file` calls upsert_page with enforce_timeline=False (D-03)
- `pytest app/tests/vault/test_watcher.py` exits 0, all tests PASSED
</success_criteria>

<output>
After completion, create `.planning/phases/01c-vault-watchdog-indexer/01c-05-SUMMARY.md`
</output>
