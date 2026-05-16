---
phase: 02B
slug: knowledge-graph-agent-runner
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-16
---

# Phase 02B — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest` + `pytest-asyncio` (already established) |
| **Config file** | `server/pyproject.toml` (existing) |
| **Quick run command** | `pytest server/app/tests/agent/ server/app/tests/graph/ -x -q` |
| **Full suite command** | `pytest server/ -x -q` |
| **Eval runner** | `python server/scripts/eval_agent.py --fixture-vault server/tests/fixtures/sample_vault/ --golden-queries server/tests/fixtures/golden_queries.yaml --baseline server/tests/fixtures/eval_baseline.json` |
| **Estimated runtime** | ~90 seconds (unit + integration); ~5 min (eval runner) |

---

## Sampling Rate

- **After every task commit:** Run `pytest server/app/tests/agent/ server/app/tests/graph/ -x -q`
- **After every plan wave:** Run `pytest server/ -x -q`
- **Before `/gsd:verify-work`:** Full eval suite must be green (`python server/scripts/eval_agent.py --exit-on-critical-fail`)
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02B-migration-01 | migration | 0 | GRAPH-01,GRAPH-02,AGENT-05 | — | N/A | integration | `alembic upgrade head && alembic check` | ❌ W0 | ⬜ pending |
| 02B-graph-01 | wikilink | 1 | GRAPH-01 | T-wikilink-01 | target_text stored as TEXT, never interpolated as SQL | unit | `pytest server/app/tests/graph/test_wikilink_extractor.py -x` | ❌ W0 | ⬜ pending |
| 02B-graph-02 | wikilink | 1 | GRAPH-02 | T-wikilink-01 | typed edge categories never executed as code | unit | `pytest server/app/tests/graph/test_wikilink_extractor.py -x -k types` | ❌ W0 | ⬜ pending |
| 02B-graph-03 | traversal | 1 | GRAPH-03 | T-rls-01 | session_with_rls() enforced on every CTE; vault_id param bound | integration | `pytest server/app/tests/graph/test_graph_traversal.py -x` | ❌ W0 | ⬜ pending |
| 02B-graph-04 | entity | 1 | GRAPH-04 | — | N/A | integration | `pytest server/app/tests/graph/test_entity_merge.py -x` | ❌ W0 | ⬜ pending |
| 02B-graph-05 | timeline | 1 | GRAPH-05 | — | N/A | integration | `pytest server/app/tests/graph/test_timeline_events.py -x` | ❌ W0 | ⬜ pending |
| 02B-graph-06 | mcp-tools | 2 | GRAPH-06 | T-rls-01 | session_with_rls() on brain.graph.traverse; vault_id checked | integration | `pytest server/app/tests/graph/test_brain_graph_traverse.py -x` | ❌ W0 | ⬜ pending |
| 02B-agent-01 | react-loop | 2 | AGENT-01 | T-loop-01 | max_iterations=10 hard cap enforced before external calls | unit | `pytest server/app/tests/agent/test_react_loop.py -x -k max_iterations` | ❌ W0 | ⬜ pending |
| 02B-agent-02 | react-loop | 2 | AGENT-02 | T-brain-first-01 | brain.search always first; external tools blocked before brain call | unit | `pytest server/app/tests/agent/test_react_loop.py -x -k brain_first` | ❌ W0 | ⬜ pending |
| 02B-agent-03 | tools | 2 | AGENT-03 | — | N/A | unit | `pytest server/app/tests/agent/test_tool_registry.py -x` | ❌ W0 | ⬜ pending |
| 02B-agent-04 | jobs | 2 | AGENT-04 | — | N/A | integration | `pytest server/app/tests/agent/test_jobs_tool.py -x` | ❌ W0 | ⬜ pending |
| 02B-agent-05 | conversation | 3 | AGENT-05 | T-rls-01 | conversations table RLS; session_id UUID from caller only | integration | `pytest server/app/tests/agent/test_conversation_persistence.py -x` | ❌ W0 | ⬜ pending |
| 02B-agent-06 | eval-seed | 3 | AGENT-06 | — | N/A | integration | `pytest server/app/tests/eval/test_golden_suite_seed.py -x` | ❌ W0 | ⬜ pending |
| 02B-test-05 | eval-run | 4 | TEST-05 | — | N/A | e2e eval | `python server/scripts/eval_agent.py --exit-on-critical-fail` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `server/app/tests/graph/` directory + `__init__.py`
- [ ] `server/app/tests/graph/test_wikilink_extractor.py` — stubs for GRAPH-01, GRAPH-02
- [ ] `server/app/tests/graph/test_graph_traversal.py` — stubs for GRAPH-03, GRAPH-06
- [ ] `server/app/tests/graph/test_entity_merge.py` — stubs for GRAPH-04
- [ ] `server/app/tests/graph/test_timeline_events.py` — stubs for GRAPH-05
- [ ] `server/app/tests/graph/test_brain_graph_traverse.py` — stubs for GRAPH-06 MCP tool
- [ ] `server/app/tests/agent/` directory + `__init__.py`
- [ ] `server/app/tests/agent/test_react_loop.py` — stubs for AGENT-01, AGENT-02
- [ ] `server/app/tests/agent/test_tool_registry.py` — stubs for AGENT-03
- [ ] `server/app/tests/agent/test_jobs_tool.py` — stubs for AGENT-04
- [ ] `server/app/tests/agent/test_conversation_persistence.py` — stubs for AGENT-05
- [ ] `server/app/tests/eval/` directory + `__init__.py`
- [ ] `server/app/tests/eval/test_golden_suite_seed.py` — stubs for AGENT-06 DB seeding
- [ ] `server/tests/fixtures/sample_vault/` — 16 markdown fixture pages
- [ ] `server/tests/fixtures/golden_queries.yaml` — 25 golden queries (TEST-05)
- [ ] `server/tests/fixtures/expected_links.json` — expected links snapshot for idempotence test
- [ ] `server/tests/fixtures/system_prompt.sha256` — SHA-256 of BRAIN_FIRST_SYSTEM_PROMPT
- [ ] `server/scripts/eval_agent.py` — eval runner (TEST-05)
- [ ] Alembic migration 0006 — links schema + mcp_mode enum + messages token/model + GoldenQuery fields

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Phoenix tracing captures ReAct spans in Arize UI | AGENT-01 | Requires live Phoenix sidecar + browser | Start app, run agent query, open localhost:6006, confirm spans appear |
| `mcp_mode=disable` blocks all external tool calls | AGENT-01 | Integration with live MCP server required | Set mcp_mode=disable via API, run agent, confirm zero external tool calls in trace |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
