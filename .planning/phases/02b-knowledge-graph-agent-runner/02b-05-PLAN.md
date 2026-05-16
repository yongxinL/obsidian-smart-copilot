---
phase: 02B
plan: 05
type: execute
wave: 3
depends_on: ["02B-04"]
files_modified:
  - server/app/agent/__init__.py
  - server/app/agent/models.py
  - server/app/agent/prompts.py
  - server/app/agent/react_loop.py
  - server/app/agent/tools/__init__.py
  - server/app/agent/tools/brain.py
  - server/app/agent/tools/graph.py
  - server/app/agent/tools/entity.py
  - server/app/agent/tools/jobs.py
  - server/app/observability/agent_spans.py
  - server/tests/fixtures/system_prompt.sha256
  - server/app/tests/agent/test_react_loop.py
  - server/app/tests/agent/test_tool_registry.py
autonomous: false
requirements: [AGENT-01, AGENT-02, AGENT-03]
tags: [phase-2b, wave-3, agent-runner, react-loop, litellm, tool-dispatch, phoenix]

must_haves:
  truths:
    - "run_react_loop() executes at most 10 iterations and returns AgentResponse with status max_iterations_reached when the limit is hit (D-05)"
    - "TOOL_REGISTRY has exactly 22 entries; TOOL_SPECS has exactly 22 OpenAI-format tool dicts (AGENT-03)"
    - "First tool invocation in tool_traces is always brain.search when the model issues any tool call (D-06 brain-first enforced via system prompt AND code-level external-tool gate)"
    - "Retryable LiteLLM exceptions (Timeout, ServiceUnavailableError, RateLimitError) cause exactly one retry; non-retryable (AuthenticationError, BadRequestError) abort immediately (D-07)"
    - "Non-critical tools (brain.graph.traverse, query.expand, entity.enrich) failing mid-loop produces status='success_with_warnings' with warnings populated; critical-tool failures abort with status='tool_error'"
    - "Empty brain.search + empty brain.graph.traverse returns AgentResponse(status='no_local_knowledge', answer=<canonical template>)"
    - "BRAIN_FIRST_SYSTEM_PROMPT SHA-256 matches the hash in server/tests/fixtures/system_prompt.sha256 (dimension 18 drift guard)"
    - "Phoenix spans agent.run, agent.iteration.{n}, tool.{name} are emitted under the SMARTCOPILOT_TRACING_ENABLED flag"
  artifacts:
    - path: "server/app/agent/react_loop.py"
      provides: "Bounded ReAct loop with D-05/D-06/D-07 semantics; ~200 LOC"
      min_lines: 150
    - path: "server/app/agent/models.py"
      provides: "AgentResponse + ToolTrace Pydantic models (locked from AI-SPEC §4b.1)"
      min_lines: 30
    - path: "server/app/agent/prompts.py"
      provides: "BRAIN_FIRST_SYSTEM_PROMPT immutable constant"
      contains: "BRAIN-FIRST DISCIPLINE"
    - path: "server/app/agent/tools/__init__.py"
      provides: "TOOL_REGISTRY (22 entries) + TOOL_SPECS (22 OpenAI tool dicts)"
      contains: "TOOL_REGISTRY"
    - path: "server/app/observability/agent_spans.py"
      provides: "agent_run_span, iteration_span, tool_span context managers with tracing-enabled guard"
      min_lines: 40
    - path: "server/tests/fixtures/system_prompt.sha256"
      provides: "Real SHA-256 digest of BRAIN_FIRST_SYSTEM_PROMPT (replaces placeholder zeros)"
  key_links:
    - from: "server/app/agent/react_loop.py"
      to: "server/app/agent/tools/__init__.py"
      via: "from app.agent.tools import TOOL_REGISTRY, TOOL_SPECS"
      pattern: "TOOL_REGISTRY"
    - from: "server/app/agent/react_loop.py"
      to: "litellm.acompletion"
      via: "from litellm import acompletion + exception classes"
      pattern: "acompletion"
    - from: "server/app/agent/tools/brain.py"
      to: "server/app/services/pages.py"
      via: "agent-internal tool wrappers call existing search/get/put services"
      pattern: "search_pages_fts|read_page|upsert_page"
---

<objective>
Build the agent core: a bounded ReAct loop (~200 LOC), the 22-tool registry, the brain-first system prompt, Pydantic response models, and Phoenix tracing context managers. This is the heart of Phase 2b — every Wave 4 entry point invokes `run_react_loop()` from here.

Purpose: AGENT-01 (22-tool ReAct loop), AGENT-02 (brain-first ordering), AGENT-03 (full 22-tool surface). The loop must enforce D-05 (max 10 iterations), D-06 (brain-first), D-07 (retryable/non-retryable error classification). The implementation is hand-rolled per the framework decision in AI-SPEC §2 (Pure Python ReAct over `litellm.acompletion()`).

Output: An importable `app.agent` package exporting `run_react_loop()`; a `TOOL_REGISTRY` with the 22 tool wrappers each calling existing services/* (or Phase 3 stubs); the SHA-256-locked BRAIN_FIRST_SYSTEM_PROMPT; and observability hooks under the `SMARTCOPILOT_TRACING_ENABLED` env flag.

This plan also contains the BLOCKING-HUMAN package legitimacy checkpoint for opentelemetry-sdk / opentelemetry-exporter-otlp / openinference-instrumentation-litellm / pyyaml. The pins were added in Plan 02B-01 but the install (when CI assembles the runtime environment) is gated here because Wave 3 is the first plan to actually `import` these packages.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/02B-knowledge-graph-agent-runner/02B-CONTEXT.md
@.planning/phases/02B-knowledge-graph-agent-runner/02B-RESEARCH.md
@.planning/phases/02B-knowledge-graph-agent-runner/02B-PATTERNS.md
@.planning/phases/02B-knowledge-graph-agent-runner/02B-AI-SPEC.md
@.planning/phases/02B-knowledge-graph-agent-runner/02B-04-SUMMARY.md
@server/app/mcp/tools/brain.py
@server/app/mcp/tools/graph.py
@server/app/mcp/tools/entity.py
@server/app/mcp/tools/jobs.py
@server/app/services/pages.py
@server/app/services/graph.py
@server/app/auth/context.py
@server/app/dependencies.py
@server/app/logging/redaction.py

<interfaces>
ReAct loop full implementation (AI-SPEC §3 lines 200-465) — locked code; the executor copies the structure verbatim.

22 PRD tools (CONTEXT.md + REQUIREMENTS.md MCP-06 + AI-SPEC §3 §4): brain.search, brain.query, brain.get, brain.put, brain.append_timeline, brain.update_compiled_truth, brain.list, brain.delete, brain.backlinks, brain.graph.traverse, brain.entity.lookup, brain.entity.enrich, brain.stats, brain.health, capability_discovery, ingest.idea (Phase-3 stub-acceptable in 2b), ingest.media (stub), ingest.meeting (stub), recipe.run (stub), skill.run (stub), jobs.submit, jobs.status.

The agent tool wrappers in `server/app/agent/tools/*.py` mirror the existing MCP tool registrations but call services/* directly (no MCP transport overhead). Each is a thin async function: validate args via Pydantic, call services/* via session_with_rls(ctx), return dict.

AgentResponse + ToolTrace Pydantic models (AI-SPEC §4b.1 lines 645-686): the schemas are LOCKED — no field renames or additions in Phase 2b. status Literal exactly: success / success_with_warnings / tool_error / max_iterations_reached / no_local_knowledge.

BRAIN_FIRST_SYSTEM_PROMPT (AI-SPEC §4b.3 lines 760-774): the prompt string is LOCKED. The exact text is the immutable contract. Hash is recorded in server/tests/fixtures/system_prompt.sha256 for drift detection.

LiteLLM exception classes (RESEARCH §Don't Hand-Roll lines 463-469):
- Retryable: Timeout, ServiceUnavailableError, RateLimitError
- Non-retryable: AuthenticationError, BadRequestError

Phoenix span helpers (AI-SPEC §5 lines 893-921 + PATTERNS.md §observability/agent_spans.py): three async context managers — agent_run_span(query, user_id, model), iteration_span(iteration), tool_span(tool_name, args). All three guarded by `SMARTCOPILOT_TRACING_ENABLED` env var; when false, the context manager is a no-op that yields None.

Non-critical tool set (D-07): frozenset({"brain.graph.traverse", "query.expand", "entity.enrich"}). All other tools are critical — failure aborts the loop.

Brain-first external-tool gate (D-06 enforcement at code level, on top of system-prompt enforcement): track whether `brain.search` has been called in this invocation. If the model attempts to call any tool outside the brain.* / graph.* / entity.lookup namespaces BEFORE brain.search has run, inject a synthetic observation `{"error": "brain_first_violation", "detail": "call brain.search before external tools"}` instead of dispatching. Increment a `agent_brain_first_violations_total` counter (declared but not necessarily wired to Prometheus in this plan).
</interfaces>
</context>

<tasks>

<task type="checkpoint:human-verify" gate="blocking-human">
  <name>Task 0: Package legitimacy verification (BLOCKING — assumed PyPI packages)</name>
  <what-built>Plan 02B-01 added these four PyPI pins to server/requirements.txt: opentelemetry-sdk>=1.41,<2 plus opentelemetry-exporter-otlp>=1.41,<2 plus openinference-instrumentation-litellm>=0.1.33 plus pyyaml>=6.0. They are tagged ASSUMED in RESEARCH Package Legitimacy Audit because slopcheck cannot evaluate PyPI. This task is the human verification gate required before any code in this plan imports them.</what-built>
  <action>Pause execution. Open each PyPI page listed in how-to-verify and visually confirm maintainer org, latest version, GitHub source link, and release cadence. Then run the pip install smoke command in an isolated venv. Block the plan from resuming until the human inspector types the approved signal.</action>
  <how-to-verify>
    1. Open https://pypi.org/project/opentelemetry-sdk/ in a browser. Confirm: maintainer is `open-telemetry` organisation; latest version >= 1.41; GitHub link points to `github.com/open-telemetry/opentelemetry-python`; release cadence is regular (>50 releases over multiple years).
    2. Open https://pypi.org/project/opentelemetry-exporter-otlp/. Confirm same org and active maintenance.
    3. Open https://pypi.org/project/openinference-instrumentation-litellm/. Confirm: maintainer Arize AI; GitHub link `github.com/Arize-ai/openinference`; version >= 0.1.33.
    4. Open https://pypi.org/project/pyyaml/. Confirm version >= 6.0 is available (standard library-grade package).
    5. Verify the four packages collectively install in a fresh venv without errors:
       `python3 -m venv /tmp/pip-test-2b && /tmp/pip-test-2b/bin/pip install opentelemetry-sdk opentelemetry-exporter-otlp openinference-instrumentation-litellm pyyaml`
    6. Confirm no security advisory listed against the installed versions (check https://pypi.org/security/ or the GitHub security advisories page for each repo).
  </how-to-verify>
  <resume-signal>Type `approved` to proceed with imports in Tasks 1–4. Type `revoke` or describe issues to halt the plan and trigger a re-research cycle.</resume-signal>
</task>

<task type="auto" tdd="true">
  <name>Task 1: Create app/agent package scaffold: models.py, prompts.py, agent_spans.py</name>
  <files>server/app/agent/__init__.py, server/app/agent/models.py, server/app/agent/prompts.py, server/app/observability/agent_spans.py, server/tests/fixtures/system_prompt.sha256</files>
  <read_first>
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-AI-SPEC.md (§4b.1 Pydantic models lines 645-686; §4b.3 BRAIN_FIRST_SYSTEM_PROMPT lines 760-774; §5 Phoenix span helpers lines 893-921)
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-PATTERNS.md (§agent/models.py + §agent/prompts.py + §observability/agent_spans.py)
    - server/app/logging/redaction.py (structlog processor analog for agent_spans.py context-manager idiom)
    - server/tests/fixtures/system_prompt.sha256 (placeholder from Plan 02B-02 — replace zeros with real SHA-256)
  </read_first>
  <behavior>
    - `AgentResponse(status="success", answer="ok", tool_traces=[], warnings=[])` validates without errors.
    - `AgentResponse(status="bogus")` raises Pydantic ValidationError (Literal constraint).
    - `BRAIN_FIRST_SYSTEM_PROMPT` is a `Final[str]` constant of at least 400 characters.
    - `sha256(BRAIN_FIRST_SYSTEM_PROMPT.encode())` hex digest equals the content of `server/tests/fixtures/system_prompt.sha256`.
    - `agent_run_span("hello", "user-id", "model")` yields a span (or None) when used as `async with`; when `SMARTCOPILOT_TRACING_ENABLED=false` it yields None without raising.
  </behavior>
  <action>
    Create `server/app/agent/__init__.py` — single-line marker `from app.agent.react_loop import run_react_loop  # noqa: F401` so callers can `from app.agent import run_react_loop`. (Plan 06 imports this.)

    Create `server/app/agent/models.py`:
      - `from __future__ import annotations`
      - Import `Any, Literal` from typing; `BaseModel, Field` from pydantic
      - Define `ToolTrace` and `AgentResponse` EXACTLY as in AI-SPEC §4b.1 lines 654-686 (locked schemas). status Literal values are exactly: success, success_with_warnings, tool_error, max_iterations_reached, no_local_knowledge.

    Create `server/app/agent/prompts.py`:
      - `from __future__ import annotations`
      - `from typing import Final`
      - Define `BRAIN_FIRST_SYSTEM_PROMPT: Final[str] = """..."""` containing EXACTLY the text from AI-SPEC §4b.3 lines 760-774 (verbatim — every paragraph including "BRAIN-FIRST DISCIPLINE (mandatory):" through "Include slug references like [page-slug] inline.").
      - At the end of the module, compute the hash and expose it:
        - import hashlib
        - `_SHA = hashlib.sha256(BRAIN_FIRST_SYSTEM_PROMPT.encode()).hexdigest()`
        - `def prompt_sha256() -> str: return _SHA`
      - Do NOT raise on mismatch at import time — assertion belongs in tests. The module just exposes the constant and the helper.

    Overwrite `server/tests/fixtures/system_prompt.sha256` with the actual SHA-256 hex digest of `BRAIN_FIRST_SYSTEM_PROMPT`. Generate it via:
      `python3 -c "import hashlib; from app.agent.prompts import BRAIN_FIRST_SYSTEM_PROMPT; print(hashlib.sha256(BRAIN_FIRST_SYSTEM_PROMPT.encode()).hexdigest())"`
    Write the result followed by a newline.

    Create `server/app/observability/agent_spans.py`:
      - `from __future__ import annotations`
      - Imports per PATTERNS.md §observability/agent_spans.py: `contextlib.asynccontextmanager`, `os`, `structlog`, `opentelemetry import trace`, `opentelemetry.sdk.trace import TracerProvider`, `opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter`
      - Helper `_tracing_enabled()` returns `os.getenv("SMARTCOPILOT_TRACING_ENABLED", "true").lower() in {"true", "1", "yes"}`
      - Three async context managers as defined in AI-SPEC §5 lines 893-921: `agent_run_span(query, user_id, model)`, `iteration_span(iteration)`, `tool_span(tool_name, args)`. Each guarded by `_tracing_enabled()` — when disabled, the function `yield None` and returns early (no span created).
      - Span attributes per AI-SPEC §7: agent.query (first 200 chars), agent.user_id, agent.model, agent.iteration, tool.name, tool.args_json (first 500 chars).
      - Do NOT call TracerProvider initialisation in this module; assume Phase 2a configured the global tracer provider. If not yet initialised, `trace.get_tracer(...)` returns a no-op tracer, which is the correct fallback.

    Add a small unit test (extend test_react_loop.py OR create test_prompt_drift.py — your choice; if extending, mark as `pytest.mark.agent, pytest.mark.unit`) that asserts:
      `hashlib.sha256(BRAIN_FIRST_SYSTEM_PROMPT.encode()).hexdigest() == open("server/tests/fixtures/system_prompt.sha256").read().strip()`. This is dimension 18 of the eval suite (prompt drift guard).
  </action>
  <verify>
    <automated>cd server &amp;&amp; python3 -c "import hashlib; from app.agent.prompts import BRAIN_FIRST_SYSTEM_PROMPT; from app.agent.models import AgentResponse, ToolTrace; r=AgentResponse(status='success', answer='ok'); print(hashlib.sha256(BRAIN_FIRST_SYSTEM_PROMPT.encode()).hexdigest() == open('tests/fixtures/system_prompt.sha256').read().strip())" | grep -q True</automated>
  </verify>
  <acceptance_criteria>
    - `grep -v '^#' server/app/agent/models.py | grep -c "class ToolTrace"` equals 1
    - `grep -v '^#' server/app/agent/models.py | grep -c "class AgentResponse"` equals 1
    - `grep -v '^#' server/app/agent/models.py | grep -c 'Literal\[' ` is at least 1
    - `grep -v '^#' server/app/agent/prompts.py | grep -c "BRAIN_FIRST_SYSTEM_PROMPT"` is at least 1
    - `grep -v '^#' server/app/agent/prompts.py | grep -c "BRAIN-FIRST DISCIPLINE"` is at least 1
    - `wc -c server/app/agent/prompts.py | awk '$1 > 800 {exit 0} {exit 1}'`
    - `grep -v '^#' server/app/observability/agent_spans.py | grep -c "agent_run_span\|iteration_span\|tool_span"` is at least 3
    - `grep -v '^#' server/app/observability/agent_spans.py | grep -c "SMARTCOPILOT_TRACING_ENABLED"` is at least 1
    - `cat server/tests/fixtures/system_prompt.sha256 | head -1 | grep -E "^[0-9a-f]{64}$"` matches AND is NOT all zeros
    - The sha256 hex digest in the fixture equals `python3 -c "import hashlib; from app.agent.prompts import BRAIN_FIRST_SYSTEM_PROMPT; print(hashlib.sha256(BRAIN_FIRST_SYSTEM_PROMPT.encode()).hexdigest())"` output
  </acceptance_criteria>
  <done>agent package scaffold + Pydantic models + system prompt + tracing helpers exist; fixture hash matches real prompt hash.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Build 22-tool registry and tool wrappers under server/app/agent/tools/</name>
  <files>server/app/agent/tools/__init__.py, server/app/agent/tools/brain.py, server/app/agent/tools/graph.py, server/app/agent/tools/entity.py, server/app/agent/tools/jobs.py, server/app/tests/agent/test_tool_registry.py</files>
  <read_first>
    - server/app/mcp/tools/brain.py (full file — mirror the 14 brain.* tool implementations as agent-internal wrappers)
    - server/app/mcp/tools/graph.py (real brain.graph.traverse from Plan 02B-04)
    - server/app/mcp/tools/entity.py (entity.* stubs — agent wrappers mirror these)
    - server/app/mcp/tools/jobs.py (jobs.* stubs — agent wrappers mirror but jobs.submit gets a partial implementation in Plan 02B-06)
    - server/app/services/pages.py (read_page, upsert_page, search_pages_fts, append_timeline, update_compiled_truth, soft_delete signatures)
    - server/app/services/graph.py (traverse_graph signature)
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-AI-SPEC.md (§3 Tool Use lines 547-577 — TOOL_SPECS and TOOL_REGISTRY shape)
    - server/app/tests/agent/test_tool_registry.py (2 skip stubs from Plan 02B-02 — unskip and implement)
  </read_first>
  <behavior>
    - test_tool_registry_has_22_tools: `len(TOOL_REGISTRY) == 22` AND `len(TOOL_SPECS) == 22`. The set of names in TOOL_SPECS matches the keys of TOOL_REGISTRY exactly.
    - test_tool_specs_match_registry: every tool spec dict has `type="function"`, contains a `function.name` matching a TOOL_REGISTRY key, has a non-empty `function.description`, has `function.parameters.type="object"` and a `properties` dict.
  </behavior>
  <action>
    Create `server/app/agent/tools/__init__.py`:
      - Imports from `app.agent.tools.brain`, `.graph`, `.entity`, `.jobs` — every wrapper function.
      - Defines `TOOL_REGISTRY: dict[str, Callable[..., Awaitable[dict]]]` mapping the 22 tool names to wrapper functions.
      - Defines `TOOL_SPECS: list[dict]` — 22 OpenAI-format tool definitions per AI-SPEC §3 lines 552-569. Each spec has `type: "function"` and `function: {name, description, parameters: {type, properties, required}}`.
      - Final assertion at module load: `assert len(TOOL_REGISTRY) == 22 and {s["function"]["name"] for s in TOOL_SPECS} == set(TOOL_REGISTRY.keys())` — module-level guard, raises ImportError if mismatched.

    The 22 tool names (per CONTEXT.md domain section + REQUIREMENTS.md MCP-06 + AI-SPEC §3):
      brain.search, brain.query, brain.get, brain.put, brain.append_timeline, brain.update_compiled_truth, brain.list, brain.delete, brain.backlinks, brain.graph.traverse, brain.entity.lookup, brain.entity.enrich, brain.stats, brain.health, capability_discovery, ingest.idea, ingest.media, ingest.meeting, recipe.run, skill.run, jobs.submit, jobs.status

    Confirm exactness by cross-checking `server/app/mcp/tools/__init__.py` — the agent surface MUST be a subset of (or equal to) the MCP-registered surface. If MCP exposes >22, document the omissions in the SUMMARY. If MCP exposes <22, the missing tools are still registered as agent wrappers that return `{"error": "not_implemented", "available_in_phase": "<phase>"}` (mirroring the Phase 1d `_AVAILABLE_IN_PHASE` stub pattern).

    Create the four tool-wrapper files:
      - `server/app/agent/tools/brain.py` — wraps all the brain.* tools. brain.query inside the agent is a no-op stub returning `{"error": "recursive_invocation"}` — the agent cannot invoke its own entry point. Each wrapper follows the pattern from PATTERNS.md §agent/tools/brain.py: define a Pydantic args model, async function `tool_name_tool(op_ctx: OperationContext, **kwargs) -> dict`, validate args, `async for session in session_with_rls(op_ctx):` open session, call service, return result dict. Return `_err("validation_error", ...)` on Pydantic ValidationError. `_err` helper local to the file mirroring brain.py lines 46-51.
      - `server/app/agent/tools/graph.py` — wraps brain.graph.traverse (uses traverse_graph from services/graph.py).
      - `server/app/agent/tools/entity.py` — wraps brain.entity.lookup, brain.entity.enrich (enrich path returns Phase-3 stub).
      - `server/app/agent/tools/jobs.py` — wraps jobs.submit, jobs.status. jobs.submit returns `{"error": "not_implemented", "available_in_phase": "2b-plan-06"}` for now; Plan 02B-06 wires the partial APScheduler path. jobs.status returns Phase-7 stub.
      - The ingest.* / recipe.run / skill.run wrappers all return Phase-3 stubs (registered in TOOL_REGISTRY so the agent can discover them but they cannot succeed in Phase 2b).

    Unskip the 2 tests in `test_tool_registry.py` and implement bodies per `<behavior>`.
  </action>
  <verify>
    <automated>cd server &amp;&amp; python3 -c "from app.agent.tools import TOOL_REGISTRY, TOOL_SPECS; assert len(TOOL_REGISTRY)==22, len(TOOL_REGISTRY); assert len(TOOL_SPECS)==22; assert set(s['function']['name'] for s in TOOL_SPECS) == set(TOOL_REGISTRY.keys()); print('OK')" &amp;&amp; pytest app/tests/agent/test_tool_registry.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `cd server && python3 -c "from app.agent.tools import TOOL_REGISTRY; print(len(TOOL_REGISTRY))"` outputs `22`
    - `cd server && python3 -c "from app.agent.tools import TOOL_SPECS; print(len(TOOL_SPECS))"` outputs `22`
    - `cd server && python3 -c "from app.agent.tools import TOOL_REGISTRY, TOOL_SPECS; print(set(TOOL_REGISTRY.keys()) == set(s['function']['name'] for s in TOOL_SPECS))"` outputs `True`
    - Every wrapper file contains `from __future__ import annotations` as line 1
    - `cd server && grep -l 'def _err' app/agent/tools/*.py | wc -l` is at least 1 (error helper present in at least one tool file)
    - `cd server && grep -l 'session_with_rls' app/agent/tools/*.py | wc -l` is at least 3 (brain, graph, entity wrappers all use RLS)
    - `cd server && pytest app/tests/agent/test_tool_registry.py -x -q` exits 0 with 2 PASSED
    - No `pytest.mark.skip` decorator remains in test_tool_registry.py
  </acceptance_criteria>
  <done>Exactly 22 tools registered with matching specs; all wrappers use session_with_rls + Pydantic arg validation; 2 registry tests pass.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Implement run_react_loop with D-05/D-06/D-07 semantics + brain-first code-level gate</name>
  <files>server/app/agent/react_loop.py, server/app/tests/agent/test_react_loop.py</files>
  <read_first>
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-AI-SPEC.md (§3 Entry Point Pattern lines 199-465 — full implementation; §4b.5 Cost and Latency Budget lines 814-820 — model defaults)
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-RESEARCH.md (Pattern 3 ReAct Loop lines 437-465; Common Pitfalls 1-5 lines 437-460)
    - server/app/agent/models.py (just-built AgentResponse, ToolTrace)
    - server/app/agent/prompts.py (BRAIN_FIRST_SYSTEM_PROMPT)
    - server/app/agent/tools/__init__.py (TOOL_REGISTRY, TOOL_SPECS)
    - server/app/observability/agent_spans.py (agent_run_span, iteration_span, tool_span)
    - server/app/tests/agent/test_react_loop.py (6 skip stubs — unskip and implement)
  </read_first>
  <behavior>
    - test_react_loop_max_iterations: mock litellm.acompletion to return a tool_call every iteration (model never finishes); after 10 iterations the loop returns AgentResponse(status="max_iterations_reached", tool_traces=<10 entries>). Counter starts at 1 and is incremented BEFORE the acompletion call (Pitfall 4).
    - test_react_loop_brain_first_first_tool_is_search: mock acompletion to issue tool calls; assert the FIRST entry of returned tool_traces has tool_name="brain.search". Additionally, mock the model to attempt entity.enrich first — the external-tool gate must inject a brain_first_violation observation instead of dispatching, and the next iteration must call brain.search.
    - test_react_loop_no_local_knowledge_returns_canonical: mock brain.search and brain.graph.traverse to return empty results; assert the loop returns AgentResponse(status="no_local_knowledge", answer matches the canonical "No local knowledge found for ..." template) after at most 4 iterations (D-06 safety net).
    - test_react_loop_non_retryable_aborts: mock litellm.acompletion to raise AuthenticationError; assert no retry occurred (only one call recorded), status="tool_error".
    - test_react_loop_retryable_retries_once: mock litellm.acompletion to raise Timeout on first call then succeed on second; assert exactly two calls recorded (Pitfall RESEARCH §Common Pitfalls — retryable retries exactly once).
    - test_react_loop_non_critical_tool_skip: mock brain.graph.traverse to fail with Timeout (twice — retry exhausted); brain.search succeeds with results; assert status="success_with_warnings" and warnings contains an entry mentioning "graph.traverse" and "transient".
  </behavior>
  <action>
    Create `server/app/agent/react_loop.py` implementing the FULL pattern from AI-SPEC §3 lines 199-465. Copy the structure verbatim — every line of the locked example is normative. Key invariants the executor MUST preserve:
      1. `iteration` is incremented BEFORE the acompletion call (top of while-body), NOT at the end (Pitfall RESEARCH §Common Pitfalls 4).
      2. ALWAYS use `acompletion()` (async), never `completion()` (sync) — Pitfall 5.
      3. Every `role: "tool"` observation message includes `tool_call_id` matching the assistant's `tool_calls[i].id` — Pitfall 1.
      4. Append the assistant message dict EXPLICITLY (do not pass raw ModelResponse) — Pitfall 2.
      5. `tool_choice="auto"` — never "required" (RESEARCH §Implementation Guidance lines 526-528).
      6. `temperature=0.0`, `max_tokens=2048`.
      7. JSON.loads(arguments) wrapped in try/except — Pitfall 3.

    Module-level constants:
      - `MAX_ITERATIONS = 10` (D-05).
      - `_RETRYABLE = (Timeout, ServiceUnavailableError, RateLimitError)` from `litellm.exceptions`.
      - `_NON_RETRYABLE = (AuthenticationError, BadRequestError)` from `litellm.exceptions`.
      - `_NON_CRITICAL_TOOLS = frozenset({"brain.graph.traverse", "query.expand", "entity.enrich"})`.
      - `_BRAIN_FIRST_NAMESPACES = ("brain.search", "brain.get", "brain.list", "brain.backlinks", "brain.graph.", "brain.entity.lookup")` — tools that may run BEFORE brain.search.
      - `_NO_LOCAL_KNOWLEDGE_TEMPLATE = 'No local knowledge found for "{query}". You can add relevant pages or ask to use external sources.'`.
      - `_NO_LOCAL_KNOWLEDGE_MAX_EMPTY_TURNS = 4` — D-06 safety net (force-terminate if both brain.search and brain.graph.traverse return empty 4 times running).

    Implement `async def run_react_loop(query: str, op_ctx: OperationContext, model: str = "anthropic/claude-sonnet-4-6", api_key: str | None = None) -> AgentResponse` per the locked AI-SPEC code. Wrap the entire body in `async with agent_run_span(query, str(op_ctx.user_id), model):`. Each iteration wrapped in `async with iteration_span(iteration):`.

    Implement `_dispatch_tool(tool_name, tool_args, op_ctx, traces, warnings, tc_id) -> dict | None` per AI-SPEC §3 lines 391-464 (locked). Two attempts max for retryable errors. Non-critical tools that fail (retryable exhausted OR non-retryable) → continue the loop with warnings populated; critical tools that fail → return None (signals caller to abort).

    Brain-first code-level gate (D-06): inside `_dispatch_tool`, before calling the tool function, check the brain-first state:
      - Maintain a `_brain_search_called` flag accessible across iterations (pass it through tool_traces inspection: `any(t.tool_name == "brain.search" for t in traces)`).
      - If `tool_name not in _BRAIN_FIRST_NAMESPACES` AND `not _brain_search_called`: synthesise observation `{"error": "brain_first_violation", "detail": "call brain.search before external tools"}`, append to traces with `skipped=True, skip_reason="brain_first_violation"`, return the synthetic observation. Do NOT call the tool.

    D-06 safety net: track count of consecutive iterations where both brain.search AND brain.graph.traverse were dispatched and returned empty/no-results observations. If count reaches `_NO_LOCAL_KNOWLEDGE_MAX_EMPTY_TURNS`, force-terminate the loop with AgentResponse(status="no_local_knowledge", answer=_NO_LOCAL_KNOWLEDGE_TEMPLATE.format(query=query)).

    Unskip all 6 tests in `test_react_loop.py` and implement per `<behavior>`. Use `unittest.mock.AsyncMock` or `monkeypatch` to mock `litellm.acompletion` and the tool registry callables. Construct OperationContext via the `_ctx_for` helper from PATTERNS.md §_ctx_for Test Helper.
  </action>
  <verify>
    <automated>cd server &amp;&amp; pytest app/tests/agent/test_react_loop.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -v '^#' server/app/agent/react_loop.py | grep -c "MAX_ITERATIONS = 10"` is at least 1
    - `grep -v '^#' server/app/agent/react_loop.py | grep -c "acompletion"` is at least 1
    - `grep -vE 'acompletion|async|description|^#' server/app/agent/react_loop.py | grep -c '\.completion('` equals 0 (no sync usage)
    - `grep -v '^#' server/app/agent/react_loop.py | grep -c "tool_call_id"` is at least 2
    - `grep -v '^#' server/app/agent/react_loop.py | grep -c 'tool_choice="auto"\|tool_choice=.auto.'` is at least 1 (never "required")
    - `grep -v '^#' server/app/agent/react_loop.py | grep -c "brain_first_violation"` is at least 1 (code-level gate present)
    - `grep -v '^#' server/app/agent/react_loop.py | grep -c "no_local_knowledge"` is at least 1
    - `grep -v '^#' server/app/agent/react_loop.py | grep -c "iteration += 1"` is at least 1 AND this line appears BEFORE `await acompletion` in the same while-body
    - `cd server && pytest app/tests/agent/test_react_loop.py -x -q` exits 0 with 6 PASSED
    - `cd server && pytest app/tests/agent/test_react_loop.py -k brain_first -x -q` exits 0 (brain-first dimension 4 verified)
    - `cd server && pytest app/tests/agent/test_react_loop.py -k max_iterations -x -q` exits 0 (D-05 verified)
    - `cd server && pytest app/tests/agent/test_react_loop.py -k retryable -x -q` exits 0 (D-07 verified)
    - No `pytest.mark.skip` decorator remains in test_react_loop.py
  </acceptance_criteria>
  <done>run_react_loop implemented with all D-05/D-06/D-07 semantics; brain-first code-level gate present; 6 react_loop tests pass.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| LLM provider (Anthropic/OpenAI) ↔ ReAct loop | Provider returns tool_calls + arguments; arguments are untrusted JSON; validated via Pydantic before dispatch |
| BRAIN_FIRST_SYSTEM_PROMPT ↔ runtime | Prompt is the system contract; drift compromises brain-first discipline |
| Assumed PyPI packages ↔ runtime imports | First import of opentelemetry-sdk, opentelemetry-exporter-otlp, openinference-instrumentation-litellm happens here |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02B-05-01 | Tampering (prompt drift) | BRAIN_FIRST_SYSTEM_PROMPT | mitigate | Constant is Final[str]; hash captured in server/tests/fixtures/system_prompt.sha256; eval dimension 18 in Plan 02B-07 will fail if hash changes without explicit bless |
| T-02B-05-02 | Elevation of Privilege (brain-first bypass) | ReAct loop external-tool gate | mitigate | Code-level gate in _dispatch_tool blocks external tools before brain.search; counter agent_brain_first_violations_total declared for monitoring (wired in Phase 6) |
| T-02B-05-03 | Tampering (malformed tool args) | _dispatch_tool | mitigate | Each tool wrapper validates kwargs via Pydantic before service call; ValidationError surfaces as structured observation, never crashes the loop |
| T-02B-05-04 | Denial of Service (runaway loop) | ReAct loop | mitigate | MAX_ITERATIONS=10 hard cap; D-06 safety net force-terminates after 4 consecutive empty turns; non-retryable errors abort immediately |
| T-02B-05-05 | Information Disclosure (provider key in trace) | acompletion api_key arg | mitigate | Inherit Phase 2a redaction.py scrubber; api_key never appears in trace observations, ToolTrace.args, or Phoenix span attributes |
| T-02B-05-SC | Tampering (supply chain) | opentelemetry-sdk, opentelemetry-exporter-otlp, openinference-instrumentation-litellm, pyyaml | mitigate | Blocking-human checkpoint Task 0 verifies each package on pypi.org before any import; not auto-approvable per planner_authority_limits |
</threat_model>

<verification>
- All 8 agent tests under server/app/tests/agent/ that this plan touches pass (2 registry + 6 react_loop)
- SHA-256 of BRAIN_FIRST_SYSTEM_PROMPT matches server/tests/fixtures/system_prompt.sha256 exactly
- TOOL_REGISTRY size is exactly 22 and matches TOOL_SPECS name set
- No sync `litellm.completion(` calls anywhere in agent/ directory (grep gate)
- agent/__init__.py exports `run_react_loop` for Plan 02B-06 to import
</verification>

<success_criteria>
- agent/ package complete: __init__.py + models.py + prompts.py + react_loop.py + tools/* (22 wrappers)
- observability/agent_spans.py provides Phoenix instrumentation under SMARTCOPILOT_TRACING_ENABLED flag
- All locked decisions D-05, D-06, D-07 enforced in code (max iter, brain-first ordering, error classification)
- Eval dimensions 4 (brain-first), 9 (iteration efficiency), 10 (retry semantics), 18 (prompt drift) testable
</success_criteria>

<output>
Create `.planning/phases/02B-knowledge-graph-agent-runner/02B-05-SUMMARY.md` when done. Record: SHA-256 of BRAIN_FIRST_SYSTEM_PROMPT, list of 22 tool names, list of Phase-3-stub tools (those returning not_implemented), count of LOC in react_loop.py, agent_brain_first_violations_total declaration location.
</output>
