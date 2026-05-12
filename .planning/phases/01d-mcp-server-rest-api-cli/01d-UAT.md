---
status: complete
phase: 01d-mcp-server-rest-api-cli
source: 01d-01-SUMMARY.md, 01d-02-SUMMARY.md, 01d-03-SUMMARY.md, 01d-04-SUMMARY.md, 01d-05-SUMMARY.md, 01d-06-SUMMARY.md
started: 2026-05-11T19:30:00Z
updated: 2026-05-12T10:05:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running server/service. Clear ephemeral state. Start from scratch. Server boots without errors, migrations complete, and basic API call returns live data.
result: pass

### 2. MCP Stdio Transport — Bad Token
expected: Running `python -m app.mcp.server --stdio` with a bad/missing SMARTCOPILOT_MCP_TOKEN prints "AUTH ERROR" to stderr and exits with code 1.
result: pass

### 3. MCP HTTP Transport — Capabilities Endpoint
expected: GET /api/v1/capabilities returns HTTP 200 with JSON payload describing available capabilities. No auth required.
result: pass

### 4. CLI mcp serve --help
expected: `smartcopilot mcp serve --help` lists --stdio and --http transport flags with descriptions.
result: pass

### 5. CLI page put + get round-trip
expected: `smartcopilot page put <slug> --title "Test" --content "Hello"` creates a page. `smartcopilot page get <slug>` retrieves it with matching title and content.
result: blocked
blocked_by: server
reason: No user registration endpoint available; --user <id> required with auth token

### 6. CLI page list + search
expected: `smartcopilot page list` shows the created page in the list. `smartcopilot page search "Hello"` returns the page in results.
result: blocked
blocked_by: server
reason: No user registration endpoint available; --user <id> required with auth token

### 7. CLI doctor health check
expected: `smartcopilot doctor` runs without crashing and reports status for at least: fernet_key, db_connection, pgvector extension.
result: pass

### 8. CLI stats
expected: `smartcopilot stats` returns vault statistics (page count, bytes, last_updated_at) without error.
result: blocked
blocked_by: server
reason: No user registration endpoint available; --user <id> required with auth token

### 9. REST API — page CRUD round-trip
expected: POST /api/v1/pages creates a page. GET /api/v1/pages/{slug} retrieves it. DELETE /api/v1/pages/{slug} removes it (returns 204).
result: pass

### 10. REST API — Search endpoint
expected: POST /api/v1/search with {"query": "hello", "limit": 5} returns {"results": [...], "total": N, "query": "hello", "search_type": "fts_v1"}.
result: blocked
blocked_by: server
reason: Returns 401 Unauthorized — endpoint requires Bearer auth; no registration endpoint to obtain token

### 11. WebSocket — Auth Error Envelope
expected: Connecting to /api/v1/ws and sending a non-auth frame first returns {"type": "auth_error", "error": {"code": "unauthorized", ...}} before closing.
result: pass

### 12. Phase 1c Regression — write/read/delete page
expected: Writing a page via services layer, reading it back, and soft-deleting it completes without errors. Deleted page no longer appears in list.
result: skipped
reason: Requires integration test environment (testcontainer); not testable via manual CLI against running server without auth

## Summary

total: 12
passed: 7
issues: 0
blocked: 4
skipped: 1

## Gaps

[none yet]