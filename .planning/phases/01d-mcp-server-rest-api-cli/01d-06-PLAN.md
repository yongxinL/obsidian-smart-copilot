---
phase: 01d
plan: 06
type: execute
wave: 5
depends_on:
  - "01d-02"
  - "01d-03"
  - "01d-04"
  - "01d-05"
files_modified:
  - server/app/tests/integration/test_phase_1d_acceptance.py
  - .planning/phases/01d-mcp-rest-api-cli/01d-VALIDATION.md
autonomous: false
requirements:
  - TEST-03
  - TEST-04
  - MCP-08

must_haves:
  truths:
    - "End-to-end: create user → mint MCP token → spawn `smartcopilot mcp serve --stdio` with SMARTCOPILOT_MCP_TOKEN → drive JSON-RPC initialize → call brain.put → brain.get → brain.search → all succeed"
    - "Stdout is bytes-equal-to JSON-RPC framing across the entire session — no extra bytes (TEST-03 strict)"
    - "MCP token last_used_at advances across the session (MCP-08 — verified by SELECT after the run)"
    - "Phase 1c regression suite still passes (no service-layer regressions)"
    - "VALIDATION.md records each Phase 1d success criterion with the test that proves it"
  artifacts:
    - path: "server/app/tests/integration/test_phase_1d_acceptance.py"
      provides: "TEST-04 acceptance — end-to-end stdio flow + last_used_at verification"
      contains: "subprocess.Popen"
    - path: ".planning/phases/01d-mcp-rest-api-cli/01d-VALIDATION.md"
      provides: "Phase 1d validation matrix — every requirement → test mapping"
  key_links:
    - from: "server/app/tests/integration/test_phase_1d_acceptance.py"
      to: "server/app/cli/main.py"
      via: "Spawns `python -m app.cli.main mcp serve --stdio` as a subprocess"
      pattern: "smartcopilot|app.cli.main"
    - from: "server/app/tests/integration/test_phase_1d_acceptance.py"
      to: "server/app/services/mcp_tokens.py"
      via: "Calls create_mcp_token to mint a token; verifies last_used_at update"
      pattern: "create_mcp_token"
---

<objective>
Author the Phase 1d acceptance test and lock the validation matrix.

This plan stitches every previous plan into the headline TEST-04 flow:

1. Boot a real Postgres testcontainer.
2. Create a user (services/users.create_user).
3. Mint an MCP bearer token (services/mcp_tokens.create_mcp_token) — capture plaintext.
4. Spawn `python -m app.cli.main mcp serve --stdio` as a subprocess with `SMARTCOPILOT_MCP_TOKEN=<plaintext>` in env.
5. Speak the MCP JSON-RPC protocol over the subprocess's stdin/stdout: `initialize`, `tools/call brain.put`, `brain.get`, `brain.search`.
6. Assert each call returns the expected payload AND the cumulative stdout consists ONLY of valid JSON-RPC frames (TEST-03 strict).
7. After the subprocess exits, query the `mcp_tokens` table to confirm `last_used_at` advanced (MCP-08).
8. Populate `01d-VALIDATION.md` with the requirement → test mapping.

Purpose: Final gate before phase ships. After this plan, /gsd-verify-phase has a green VALIDATION.md to lift into the phase summary.

Output: 1 acceptance test file + 1 VALIDATION.md.
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
@.planning/phases/01d-mcp-rest-api-cli/01d-03-PLAN.md
@.planning/phases/01d-mcp-rest-api-cli/01d-04-PLAN.md
@.planning/phases/01d-mcp-rest-api-cli/01d-05-PLAN.md
@CLAUDE.md
@server/app/services/users.py
@server/app/services/mcp_tokens.py
@.planning/phases/01b-auth-security-primitives/01b-VALIDATION.md
@.planning/phases/01c-vault-watchdog-indexer/01c-VALIDATION.md

<interfaces>
<!-- MCP JSON-RPC framing (Streamable transport — but stdio uses ND-JSON over stdin/stdout
     in the Python SDK 1.25+, which exchanges {"jsonrpc": "2.0", ...} per line).
     Reference shape (subset; the SDK handles the rest): -->
```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"phase-1d-acceptance","version":"0.0.0"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"brain.put","arguments":{"slug":"acme","content":"title: Acme\\n---\\nFounded 2010"}}}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"brain.get","arguments":{"slug":"acme"}}}
{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"brain.search","arguments":{"query":"acme","limit":5}}}
```

<!-- Service entry points the test uses to seed user + token: -->
```python
# server/app/services/users.py:
async def create_user(session, ctx, *, username, password_plain, role="user", email=None) -> User: ...

# server/app/services/mcp_tokens.py:
async def create_mcp_token(session, ctx, *, name=None) -> tuple[str, McpToken]: ...
# Returns (plaintext_token, db_row); plaintext is shown ONCE — store it in the test.
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: TEST-04 Phase 1d acceptance — end-to-end stdio flow</name>
  <files>server/app/tests/integration/test_phase_1d_acceptance.py</files>
  <read_first>
    - server/app/services/users.py (create_user signature)
    - server/app/services/mcp_tokens.py (create_mcp_token returns plaintext)
    - server/app/cli/main.py (Plan 05 — `mcp serve --stdio` subcommand)
    - .planning/phases/01b-auth-security-primitives/01b-VALIDATION.md (style template for test layout)
    - .planning/phases/01c-vault-watchdog-indexer/01c-VALIDATION.md (style template for test layout)
  </read_first>
  <behavior>
    - Test seeds a user, mints a token, spawns the CLI subprocess, drives JSON-RPC handshake, asserts each tool call succeeds, asserts stdout-only-JSON-RPC, asserts last_used_at moved.
    - Test uses `subprocess.Popen` with `stdin=PIPE, stdout=PIPE, stderr=PIPE` and a tight timeout (e.g. 30s for the whole flow).
    - Each line written to stdin is one JSON-RPC frame followed by `\n`. Each line read from stdout is parsed as JSON; the test validates `jsonrpc=="2.0"` and matches `id` to the request.
    - After the test sends `brain.search` and reads its response, the test sends a `notifications/cancelled` or simply closes stdin to signal shutdown.
    - The accumulated stdout bytes are split on `\n` and EACH non-empty line MUST parse as a JSON object with `"jsonrpc": "2.0"` — no other bytes are tolerated (TEST-03 strict).
    - After subprocess exit (returncode 0 expected on graceful shutdown via stdin close, or accept SIGTERM equivalents), the test queries `mcp_tokens` via the test_engine to confirm `last_used_at` is set and recent (within the test window).
  </behavior>
  <action>
Create `server/app/tests/integration/test_phase_1d_acceptance.py`:

```python
"""Phase 1d acceptance test (TEST-04).

End-to-end: user → MCP token → Claude-Code-style stdio session → brain.put / get / search.
Also validates TEST-03 (stdio cleanliness) on the FULL session, not just the auth-failure path.
And MCP-08 (last_used_at advances).
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, AsyncSession

from app.auth.context import OperationContext, system_operation_context
from app.db_session import session_with_rls
from app.services.mcp_tokens import create_mcp_token
from app.services.users import create_user

SERVER_DIR = Path(__file__).resolve().parent.parent.parent.parent  # smart-copilot/server
ENV_FERNET = "T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU="
ENV_JWT = "test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa"


def _send(proc: subprocess.Popen, msg: dict) -> None:
    line = json.dumps(msg) + "\n"
    assert proc.stdin is not None
    proc.stdin.write(line.encode("utf-8"))
    proc.stdin.flush()


def _recv(proc: subprocess.Popen, timeout: float = 10.0) -> dict:
    deadline = time.monotonic() + timeout
    assert proc.stdout is not None
    while time.monotonic() < deadline:
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.05)
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            raise AssertionError(f"non-JSON byte on stdout: {line!r}")
    raise AssertionError("timed out waiting for response")


def _send_and_match(proc: subprocess.Popen, msg: dict) -> dict:
    _send(proc, msg)
    while True:
        resp = _recv(proc)
        # MCP servers may emit unsolicited notifications; skip those (no `id`).
        if resp.get("id") == msg["id"]:
            return resp


@pytest.mark.integration
async def test_phase_1d_acceptance_stdio_flow(
    test_engine: AsyncEngine, postgres_container,
) -> None:
    # ── 1. Seed user + MCP token ───────────────────────────────────────────────
    factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    username = f"acceptance-{uuid.uuid4().hex[:8]}"
    plaintext_token: str | None = None

    sys_ctx = system_operation_context(client_name="test", request_id="test-acceptance")
    async for session in session_with_rls(sys_ctx):
        user = await create_user(
            session, sys_ctx,
            username=username, password_plain="acceptance-password-12345",
            role="user", email=None,
        )
        await session.commit()

    user_ctx = OperationContext(
        user_id=user.id, role=user.role, transport="cli", remote=False,
        client_name="test", request_id="test-mint-token",
    )
    async for session in session_with_rls(user_ctx):
        plaintext_token, _row = await create_mcp_token(session, user_ctx, name="acceptance")
        await session.commit()

    # Seed a private vault for the user (Phase 1d MCP tools resolve vault from ctx.user_id).
    vault_id = uuid.uuid4()
    async with factory() as session:
        await session.execute(
            text(
                "INSERT INTO vaults (id, owner_user_id, kind, path, created_at, updated_at) "
                "VALUES (:id, :uid, 'private', :path, now(), now())"
            ),
            {"id": vault_id, "uid": user.id, "path": f"/vaults/private/{username}/"},
        )
        await session.commit()

    # ── 2. Spawn the CLI ───────────────────────────────────────────────────────
    sync_url = postgres_container.get_connection_url()
    raw_dsn = sync_url.replace("postgresql+psycopg2://", "postgresql://", 1)
    async_dsn = raw_dsn.replace("postgresql://", "postgresql+asyncpg://", 1)

    env = os.environ.copy()
    env["SMARTCOPILOT_FERNET_KEY"] = ENV_FERNET
    env["JWT_SIGNING_KEY"] = ENV_JWT
    env["SMARTCOPILOT_MCP_TOKEN"] = plaintext_token
    env["DATABASE_URL"] = async_dsn

    proc = subprocess.Popen(
        [sys.executable, "-m", "app.cli.main", "mcp", "serve", "--stdio"],
        cwd=str(SERVER_DIR),
        env=env,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        bufsize=0,
    )
    captured_stdout = bytearray()

    try:
        # ── 3. JSON-RPC handshake ────────────────────────────────────────────────
        init_resp = _send_and_match(proc, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "phase-1d-acceptance", "version": "0.0.0"},
            },
        })
        assert "result" in init_resp, init_resp

        # initialized notification (no id, no response):
        _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})

        # ── 4. brain.put ────────────────────────────────────────────────────────
        put_resp = _send_and_match(proc, {
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "brain.put", "arguments": {
                "slug": "acme", "content": "title: Acme\n---\nFounded 2010", "namespace": "private",
            }},
        })
        # The MCP SDK wraps the dict in {"content": [{"type":"text","text": "<json>"}]}.
        # We accept either: a raw `result` dict OR the SDK's wrapper.
        result = put_resp.get("result", {})
        body = _extract_tool_result(result)
        assert body.get("status") == "ok", body

        # ── 5. brain.get ────────────────────────────────────────────────────────
        get_resp = _send_and_match(proc, {
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "brain.get", "arguments": {"slug": "acme"}},
        })
        body = _extract_tool_result(get_resp.get("result", {}))
        assert body.get("slug") == "acme", body
        assert "Founded 2010" in (body.get("compiled_truth") or ""), body

        # ── 6. brain.search ─────────────────────────────────────────────────────
        srch_resp = _send_and_match(proc, {
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": "brain.search", "arguments": {"query": "acme", "limit": 5}},
        })
        body = _extract_tool_result(srch_resp.get("result", {}))
        assert body.get("search_type") == "fts_v1", body
        results = body.get("results") or []
        assert any(r.get("slug") == "acme" for r in results), body

        # ── 7. Shutdown ─────────────────────────────────────────────────────────
        proc.stdin.close()
        proc.wait(timeout=5)
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        # Drain any remaining stdout before the assertion below.
        if proc.stdout is not None:
            try:
                captured_stdout.extend(proc.stdout.read() or b"")
            except Exception:                                # noqa: BLE001
                pass

    # ── 8. TEST-03 strict: every non-empty stdout line is JSON-RPC ────────────────
    # Note: we already validated each line as we read it inside _recv. The assertion
    # below is a final sanity check on any tail bytes.
    tail = bytes(captured_stdout).strip()
    if tail:
        for line in tail.split(b"\n"):
            if not line.strip():
                continue
            obj = json.loads(line)
            assert obj.get("jsonrpc") == "2.0", f"non-JSON-RPC tail: {line!r}"

    # ── 9. MCP-08: last_used_at advanced ────────────────────────────────────────
    async with factory() as session:
        row = (await session.execute(
            text("SELECT last_used_at FROM mcp_tokens WHERE user_id = :uid"),
            {"uid": user.id},
        )).scalar_one_or_none()
    assert row is not None, "mcp_token row missing"
    assert datetime.now(UTC) - (row.replace(tzinfo=UTC) if row.tzinfo is None else row) < timedelta(minutes=2), \
        f"last_used_at not recent: {row}"


def _extract_tool_result(result: dict) -> dict:
    """MCP SDK 1.25+ wraps dict tool results as {"content":[{"type":"text","text":"<json>"}]}.

    Some return paths emit the raw dict in `result` directly. Handle both.
    """
    if not isinstance(result, dict):
        return {}
    content = result.get("content")
    if isinstance(content, list) and content and isinstance(content[0], dict):
        text_field = content[0].get("text")
        if isinstance(text_field, str):
            try:
                return json.loads(text_field)
            except json.JSONDecodeError:
                return {"raw": text_field}
    # Fallback: treat result itself as the payload.
    return result
```

Pre-flight: run `cd server && python -c "import mcp; print(mcp.__version__)"` to confirm the installed MCP SDK version is 1.25–1.x. If the SDK wraps tool results differently (e.g. SDK 1.26 ships native dict results), update `_extract_tool_result` accordingly. Run a single trial of the test against a live testcontainer; if it red-bars on the wrapper shape, adjust.
  </action>
  <verify>
    <automated>cd server && SMARTCOPILOT_FERNET_KEY=T8YTnEbNGq9aYUOA3LjL6PLghE15Vrn-uFO3chFiOEU= JWT_SIGNING_KEY=test-signing-key-min-32-bytes-aaaaaaaaaaaaaaaaaaaa pytest -x app/tests/integration/test_phase_1d_acceptance.py -v</automated>
  </verify>
  <acceptance_criteria>
    - File `server/app/tests/integration/test_phase_1d_acceptance.py` exists.
    - `grep -c "subprocess.Popen" server/app/tests/integration/test_phase_1d_acceptance.py` >= 1
    - `grep -c "brain.put\|brain.get\|brain.search" server/app/tests/integration/test_phase_1d_acceptance.py` >= 3 (one for each tool)
    - `grep -c "last_used_at" server/app/tests/integration/test_phase_1d_acceptance.py` >= 1 (MCP-08)
    - `grep -c "search_type.*fts_v1" server/app/tests/integration/test_phase_1d_acceptance.py` >= 1
    - The acceptance test passes.
    - Phase 1c regression: `cd server && pytest -x app/tests/vault/ -v` still green.
  </acceptance_criteria>
  <done>TEST-04 acceptance proves the entire Phase 1d slice end-to-end; MCP-08 last_used_at confirmed.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 2: Human verification — Claude Code stdio handshake on the host</name>
  <files>(none — operator-driven smoke test)</files>
  <what-built>
After Task 1 the automated acceptance test exercises the full MCP stdio flow inside testcontainers. Task 2 asks the operator to run the SAME flow against a real Claude Code (or any MCP client) connection. This catches edge cases the automated test cannot — terminal behavior, real MCP client framing quirks, log-routing surprises.
  </what-built>
  <how-to-verify>
1. Start the server in dev mode: `cd server && docker compose -f ../docker-compose.dev.yml up -d` (or the project's existing dev compose).
2. Mint a real MCP token: `smartcopilot user create --username alice --role user` (set SMARTCOPILOT_NEW_PASSWORD env first), then `smartcopilot mcp token create --user alice` — copy the plaintext.
3. Configure Claude Code with an MCP server entry pointing at: `command: smartcopilot, args: [mcp, serve, --stdio], env: {SMARTCOPILOT_MCP_TOKEN: "<paste>"}`.
4. Restart Claude Code. Confirm:
   - The smart-copilot MCP server shows as "connected" (green dot).
   - `brain.put`, `brain.get`, `brain.search` are visible in the tool palette.
5. Drive a brain.put → brain.get → brain.search round-trip from Claude Code.
6. Tail the server logs (`docker logs -f`); confirm the MCP HTTP process did NOT receive any stdio traffic (the stdio server runs out-of-container, on the host where Claude Code lives).
7. Reply with one of:
   - "approved" if all 6 steps pass.
   - "issue: <description>" if any step fails — describe what you observed.
  </how-to-verify>
  <action>Operator-driven verification (no executor automation). The executor must pause and await the operator response. Follow the steps in <how-to-verify> on the host machine; do NOT proceed past this task without an explicit "approved" or "issue: ..." reply.</action>
  <verify>Operator types "approved" → resume; operator types "issue: ..." → STOP execution, surface the issue back to /gsd-execute-phase, and create a follow-up plan via /gsd-plan-phase --gaps.</verify>
  <done>Operator has typed "approved" in response to <resume-signal>.</done>
  <resume-signal>Type "approved" or "issue: ..."</resume-signal>
</task>

<task type="auto">
  <name>Task 3: Populate VALIDATION.md — requirement → test mapping</name>
  <files>.planning/phases/01d-mcp-rest-api-cli/01d-VALIDATION.md</files>
  <read_first>
    - .planning/phases/01b-auth-security-primitives/01b-VALIDATION.md (style + structure to mirror)
    - .planning/phases/01c-vault-watchdog-indexer/01c-VALIDATION.md (style + structure to mirror)
    - .planning/ROADMAP.md (Phase 1d Success Criteria block — 5 items)
  </read_first>
  <behavior>
    - Document records every Phase 1d requirement (21 IDs) and links each to the test file/case proving it.
    - Each Phase 1d Success Criterion (the 5 items in ROADMAP.md) has a one-paragraph evidence section pointing to the test.
    - Mirrors the structure already used by `01b-VALIDATION.md` and `01c-VALIDATION.md`.
  </behavior>
  <action>
Create `.planning/phases/01d-mcp-rest-api-cli/01d-VALIDATION.md`. Mirror the structure of `01c-VALIDATION.md` exactly. Sections:

1. **Header** — phase, status, validated date.
2. **Requirement matrix** — table with columns: REQ-ID | Description | Test File | Test Case | Status. Cover all 21 IDs (MCP-01..08 = 8, REST-01..06 = 6, CLI-01..05 = 5, TEST-03 + TEST-04 = 2 → total 21).
3. **Phase 1d Success Criteria** — for each of the 5 ROADMAP success criteria, a paragraph naming the proving test and outcome.
4. **Outstanding gaps** — should be empty after Tasks 1–2 succeed; if anything was deferred (e.g., visual UAT findings), record under this header.

Reference test mappings (one row per requirement; IDs and test files are determinate from the Plan 01–06 artifacts):

| REQ | Test |
|-----|------|
| MCP-01 | test_mcp_stdout_clean.py + test_phase_1d_acceptance.py |
| MCP-02 | test_mcp_tools.py + manual --selftest in Plan 02 verify |
| MCP-03 | test_rest_mcp_parity.py |
| MCP-04 | test_mcp_tools.py — every tool builds OperationContext |
| MCP-05 | test_mcp_tools.py::test_remote_true_invalid_slug_rejected |
| MCP-06 | test_mcp_tools.py::test_total_tool_count_at_least_30 |
| MCP-07 | test_mcp_tools.py — Pydantic input validation tests |
| MCP-08 | test_phase_1d_acceptance.py last_used_at assertion |
| REST-01 | test_rest_mcp_parity.py |
| REST-02 | test_pages_routes.py — encrypted-key absence assertion |
| REST-03 | test_ws_index_events.py + test_ws_auth.py |
| REST-04 | test_pages_routes.py — error envelope assertions |
| REST-05 | test_vault_routes.py::test_capabilities_returns_phase_1d_payload |
| REST-06 | acceptance criteria grep gates in Plans 01/03 (no FastAPI in services/) |
| CLI-01 | test_cli_mcp_serve.py::test_smartcopilot_help_lists_all_subcommands |
| CLI-02 | test_cli_doctor.py::test_doctor_reports_all_d14_sections |
| CLI-03 | test_cli_check_resolvable.py::test_check_resolvable_passes_when_dir_missing |
| CLI-04 | test_pages_routes.py + test_search_route.py + test_vault_routes.py (REST-side parallel for Phase 1d slice) |
| CLI-05 | inherited from Phase 1b admin gates; no new destructive routes added in Phase 1d |
| TEST-03 | test_mcp_stdout_clean.py + test_phase_1d_acceptance.py (full session) |
| TEST-04 | test_phase_1d_acceptance.py |

Write the final VALIDATION.md verbatim using this exact table structure plus the 5 Success Criteria evidence paragraphs.
  </action>
  <verify>
    <automated>test -f .planning/phases/01d-mcp-rest-api-cli/01d-VALIDATION.md && grep -E "^\| (MCP|REST|CLI|TEST)" .planning/phases/01d-mcp-rest-api-cli/01d-VALIDATION.md | wc -l</automated>
  </verify>
  <acceptance_criteria>
    - File `.planning/phases/01d-mcp-rest-api-cli/01d-VALIDATION.md` exists.
    - `grep -E "^\| (MCP|REST|CLI|TEST)" .planning/phases/01d-mcp-rest-api-cli/01d-VALIDATION.md | wc -l` >= 21 (one row per requirement)
    - `grep -c "MCP-01" .planning/phases/01d-mcp-rest-api-cli/01d-VALIDATION.md` >= 1
    - `grep -c "TEST-04" .planning/phases/01d-mcp-rest-api-cli/01d-VALIDATION.md` >= 1
    - All 5 ROADMAP success criteria have an evidence paragraph (search for "Success Criterion 1" through "Success Criterion 5", or numbered list 1..5).
  </acceptance_criteria>
  <done>VALIDATION.md ready for /gsd-verify-phase to lift into the phase summary.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Test subprocess → MCP stdio | Acceptance test simulates an external MCP client; uses real plaintext token issued during the test |
| Real Claude Code (Task 2) → host stdio | Operator-driven; no automation can replace this final smoke |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-01d06-01 | Information Disclosure | acceptance test prints plaintext token in pytest output | mitigate | Test stores plaintext only in a local variable; never `print()`s it. Failure messages reference token presence, not value. |
| T-01d06-02 | Tampering | acceptance test left orphan rows in the test DB | accept | testcontainer is per-session; teardown wipes the DB. |
| T-01d06-03 | Repudiation | manual checkpoint (Task 2) lacks audit trail | accept | Operator records observed behaviour in the resume-signal message; the verifier captures it in the SUMMARY. Audit logging arrives in Phase 6 (OBS-03). |
| T-01d06-04 | DoS | acceptance test runtime > 60s | mitigate | Per-call timeouts (10s); whole-test timeout (30s). Test marked `@pytest.mark.integration` so it is skipped in fast-only CI runs. |
</threat_model>

<verification>
1. `cd server && pytest -x app/tests/integration/test_phase_1d_acceptance.py -v` — passes.
2. `cd server && pytest -x app/tests/vault/ -v` — Phase 1c regression green.
3. `.planning/phases/01d-mcp-rest-api-cli/01d-VALIDATION.md` populated with all 21 requirement rows + 5 success criteria evidence paragraphs.
4. Operator-confirmed Claude Code handshake (Task 2) returns "approved".
</verification>

<success_criteria>
- TEST-04 (Phase 1d acceptance test) passes against real PostgreSQL.
- TEST-03 stdout-cleanliness invariant holds across the entire stdio session, not just the auth-failure path.
- MCP-08 last_used_at advance verified.
- Manual Claude Code handshake confirmed by operator.
- VALIDATION.md authoritative for verifier consumption.
</success_criteria>

<output>
After completion, create `.planning/phases/01d-mcp-rest-api-cli/01d-06-SUMMARY.md` recording: acceptance-test outcome, operator's resume-signal verbatim, the VALIDATION.md row count, and any deviations.
</output>
