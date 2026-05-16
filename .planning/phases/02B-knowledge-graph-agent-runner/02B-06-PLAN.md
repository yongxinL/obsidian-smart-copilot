---
phase: 02B
plan: 06
type: execute
wave: 4
depends_on: ["02B-05"]
files_modified:
  - server/app/services/agent_service.py
  - server/app/routes/query.py
  - server/app/mcp/tools/brain.py
  - server/app/mcp/tools/jobs.py
  - server/app/agent/tools/jobs.py
  - server/app/main.py
  - server/app/tests/agent/test_conversation_persistence.py
  - server/app/tests/agent/test_jobs_tool.py
autonomous: true
requirements: [AGENT-04, AGENT-05]
tags: [phase-2b, wave-4, agent-entry-points, conversation-persistence, brain-query, jobs-submit]

must_haves:
  truths:
    - "POST /api/v1/query (REST) invokes run_react_loop and returns AgentResponse-shaped JSON including message_id and conversation_id (AGENT-05)"
    - "MCP tool brain.query is registered with the same semantics as the REST route and calls the same agent_service.run_agent_query (D-08 parity)"
    - "Every brain.query invocation creates or appends to a conversation row; messages table records user + final assistant message only (D-11)"
    - "Tool traces are stored as JSONB on messages.tool_calls (D-12)"
    - "When session_id is provided, the new message is appended to the existing conversation; when omitted, a new single-turn conversation UUID is generated (D-09)"
    - "MCP and REST transports for the same query under the same user_id produce structurally identical conversations + messages rows (dimension 12)"
    - "jobs.submit MCP tool writes a Job row with status='pending' and calls APScheduler add_job(...) for the requested kind (AGENT-04 partial path)"
  artifacts:
    - path: "server/app/services/agent_service.py"
      provides: "run_agent_query, persist_agent_invocation, get_or_create_conversation; the agent's only service entry point"
      min_lines: 80
    - path: "server/app/routes/query.py"
      provides: "POST /api/v1/query route with QueryIn/QueryResponse Pydantic models"
      contains: "POST"
    - path: "server/app/mcp/tools/brain.py"
      provides: "Modified to register brain.query MCP tool calling run_agent_query"
      contains: "brain.query"
    - path: "server/app/mcp/tools/jobs.py"
      provides: "jobs.submit replaced with partial APScheduler implementation"
      contains: "add_job"
  key_links:
    - from: "server/app/routes/query.py"
      to: "server/app/services/agent_service.py"
      via: "POST /api/v1/query handler awaits run_agent_query and persist_agent_invocation"
      pattern: "run_agent_query"
    - from: "server/app/mcp/tools/brain.py brain.query"
      to: "server/app/services/agent_service.py"
      via: "MCP tool calls run_agent_query — same service function as REST"
      pattern: "run_agent_query"
    - from: "server/app/services/agent_service.py persist_agent_invocation"
      to: "conversations + messages tables"
      via: "INSERT user message + INSERT assistant message inside same RLS-scoped session"
      pattern: "session.add\\(.*Message\\)"
---

<objective>
Wire the two agent entry points (MCP `brain.query` and REST `POST /api/v1/query`) so both invoke `run_react_loop` from Plan 05 and persist the conversation. Provide the minimal `jobs.submit` path for AGENT-04 (Job row write + APScheduler enqueue — full DAG orchestration remains Phase 7). Verify MCP/REST parity via the dimension-12 integration test.

Purpose: AGENT-04 (`jobs.submit` + `skill_run` stub already present) and AGENT-05 (conversations table populated, every invocation recorded with citations + token usage + model tracking). D-08 (no parity gap between transports) + D-09 (session handling) + D-11 (only user + final assistant) + D-12 (tool traces in JSONB) are the locked decisions enforced here.

Output: Agent entry points (one service, two transports), conversation persistence following D-09/D-11/D-12, and a working `jobs.submit` that survives in the existing APScheduler supervisord process (no new infrastructure).
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
@.planning/phases/02B-knowledge-graph-agent-runner/02B-05-SUMMARY.md
@server/app/agent/__init__.py
@server/app/agent/react_loop.py
@server/app/agent/models.py
@server/app/routes/search.py
@server/app/routes/pages.py
@server/app/mcp/tools/brain.py
@server/app/mcp/tools/jobs.py
@server/app/services/pages.py
@server/app/scheduler/run.py
@server/app/models/conversation.py
@server/app/models/job.py
@server/app/auth/deps.py
@server/app/dependencies.py
@server/app/main.py

<interfaces>
agent_service patterns (RESEARCH §Code Examples lines 663-695 + PATTERNS.md §services/agent_service.py):
- `run_agent_query(op_ctx, vault_id, query, session_id=None) -> AgentResponse` — wrapper around `run_react_loop` that also handles persistence.
- `persist_agent_invocation(op_ctx, session_id, user_query, result, model) -> uuid.UUID` — writes user message + assistant message inside `async for session in session_with_rls(op_ctx):`. Returns the assistant message_id.
- `get_or_create_conversation(session, ctx, session_id) -> Conversation` — D-09 session handling.

QueryIn / QueryResponse Pydantic models (PATTERNS.md §routes/query.py lines 538-549):
- QueryIn: query (1-4096 chars), session_id (UUID optional)
- QueryResponse: status, answer, tool_traces, warnings, message_id, conversation_id

POST /api/v1/query route handler (PATTERNS.md §routes/query.py lines 552-569):
- Depends on require_user + get_db_session
- Resolves vault_id, calls run_agent_query, returns QueryResponse

MCP brain.query registration: append to existing `server/app/mcp/tools/brain.py` `register()` function. Tool name "brain.query", description matches PRD §17.

jobs.submit minimal APScheduler path (RESEARCH §Open Question 4 — minimal implementation):
- Pydantic args: kind (string — name of a known job function), args (dict), idempotency_key (optional)
- Behaviour: insert Job row with status="pending"; call `scheduler.add_job(_job_dispatcher, args=[job_id, kind, args], id=str(job_id))` against the existing AsyncIOScheduler from server/app/scheduler/run.py
- Returns {"job_id": str, "status": "pending"}
- The actual job executor `_job_dispatcher(job_id, kind, args)` is a small stub that updates the job row status; full implementation is Phase 7

Citation extraction helper (AI-SPEC §4 implementation lines 587-619): from a list of ToolTrace, walk tool_traces[*].observation looking for retrieval results, extract page_slug+chunk_id pairs into a list of `{slug, chunk_id}` dicts for the messages.citations JSONB column. The brain.search observation shape from Plan 05 includes `results: [{page_slug, chunk_id, content, ...}]` — citation extraction reads these.

token_usage extraction: sum response.usage.total_input_tokens and total_output_tokens from each LiteLLM acompletion call recorded in tool_traces. Sum into a single `{input_tokens, output_tokens, total_tokens}` dict stored on the assistant message row.

Existing main.py app construction: read for the router-registration pattern (search/pages/vault routes are added via `app.include_router(...)`). Plan 06 adds `app.include_router(query.router)`.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement agent_service with run_agent_query, persist_agent_invocation, get_or_create_conversation</name>
  <files>server/app/services/agent_service.py, server/app/tests/agent/test_conversation_persistence.py</files>
  <read_first>
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-PATTERNS.md (§services/agent_service.py lines 240-294)
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-AI-SPEC.md (§4 State Management lines 583-619 — persist_agent_invocation example)
    - server/app/agent/__init__.py + server/app/agent/react_loop.py (run_react_loop signature)
    - server/app/models/conversation.py (post-migration Message has token_usage + model columns)
    - server/app/dependencies.py (session_with_rls iterator)
    - server/app/services/vault_resolver.py (resolve_user_vault_id signature)
    - server/app/tests/agent/test_conversation_persistence.py (4 skip stubs — implement)
  </read_first>
  <behavior>
    - test_brain_query_creates_conversation_new_session: calling run_agent_query without session_id creates a new Conversation row with mcp_mode="disable", web_search_enabled=False; messages table has exactly 2 rows for that conversation_id (one role=user, one role=assistant); returned message_id matches the assistant row.
    - test_brain_query_appends_to_existing_session: calling run_agent_query a second time WITH the conversation_id from the first call adds 2 more messages to the SAME conversation_id (total 4 rows).
    - test_message_token_usage_persisted: the assistant message row has non-null token_usage JSONB containing input_tokens/output_tokens keys and non-null model TEXT column.
    - test_brain_query_mcp_rest_parity (cross-test — also exercised in Task 3): two structurally identical invocations under the same user_id produce diff-equal conversation + messages rows (excluding timestamps and UUIDs).
  </behavior>
  <action>
    Create `server/app/services/agent_service.py`:
      - `from __future__ import annotations`
      - Imports: uuid, structlog, AsyncSession, select, Conversation, Message, session_with_rls, OperationContext, run_react_loop, AgentResponse, ToolTrace, resolve_user_vault_id
      - `log = structlog.get_logger("smart_copilot.services.agent_service")`

    Function `async def get_or_create_conversation(session, ctx, session_id) -> Conversation`:
      - If session_id provided: SELECT * FROM conversations WHERE id = :session_id AND user_id = :user_id. If found → return. If not found → raise ValueError (don't silently create — caller passed an explicit but bogus id).
      - If session_id is None: create `Conversation(user_id=ctx.user_id, mcp_mode="disable", web_search_enabled=False, title=None)`. session.add + session.flush. Return.

    Function `async def persist_agent_invocation(op_ctx, session_id, user_query, result: AgentResponse, model: str) -> tuple[uuid.UUID, uuid.UUID]` (returns (conversation_id, message_id)):
      - `async for session in session_with_rls(op_ctx):`
      - `conv = await get_or_create_conversation(session, op_ctx, session_id)`
      - Build `user_msg = Message(conversation_id=conv.id, role="user", content=user_query, citations=[], tool_calls=[])`
      - session.add(user_msg) + flush
      - Extract citations via helper `_extract_citations(result.tool_traces)` (list of {slug, chunk_id, score} drawn from brain.search observations)
      - Extract token_usage via helper `_sum_token_usage(result.tool_traces)` (sum input + output across acompletion-recorded entries; or compute from LiteLLM usage attached to the tool_traces — see AI-SPEC §4 State Management)
      - Build assistant message: `Message(conversation_id=conv.id, role="assistant", content=result.answer or "", citations=_extract_citations(...), tool_calls=[t.model_dump() for t in result.tool_traces], token_usage=_sum_token_usage(...), model=model)`
      - session.add(assistant_msg) + commit. Return (conv.id, assistant_msg.id).

    Function `async def run_agent_query(op_ctx: OperationContext, vault_id: uuid.UUID, query: str, session_id: uuid.UUID | None = None, model: str = "anthropic/claude-sonnet-4-6") -> dict`:
      - Calls `result = await run_react_loop(query, op_ctx, model=model)`.
      - Calls `(conv_id, msg_id) = await persist_agent_invocation(op_ctx, session_id, query, result, model=model)`.
      - Returns dict shaped like AgentResponse plus conversation_id + message_id: `{**result.model_dump(), "conversation_id": str(conv_id), "message_id": str(msg_id)}`.

    Helper `_extract_citations(traces: list[ToolTrace]) -> list[dict]`:
      - Walk every trace, look for tool_name in {"brain.search", "brain.get", "brain.graph.traverse"}, parse observation for `results` list with `page_slug` / `chunk_id` keys. Return deduplicated list of `{slug, chunk_id, score}` (score optional).

    Helper `_sum_token_usage(traces: list[ToolTrace]) -> dict`:
      - For each trace observation that contains `usage` key (LiteLLM observation shape), sum input/output/total. If no usage data found, return `{"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}`.

    Unskip 4 tests in test_conversation_persistence.py; mock run_react_loop to return a fixed AgentResponse with one ToolTrace whose observation has a `usage` dict and a `results` list with one slug. Implement the assertions per `<behavior>`. The mcp_rest_parity test will be filled in Task 3 once the MCP brain.query tool is registered.
  </action>
  <verify>
    <automated>cd server &amp;&amp; pytest app/tests/agent/test_conversation_persistence.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -v '^#' server/app/services/agent_service.py | grep -c "async def run_agent_query"` equals 1
    - `grep -v '^#' server/app/services/agent_service.py | grep -c "async def persist_agent_invocation"` equals 1
    - `grep -v '^#' server/app/services/agent_service.py | grep -c "async def get_or_create_conversation"` equals 1
    - `grep -v '^#' server/app/services/agent_service.py | grep -c "session_with_rls"` is at least 1
    - `grep -v '^#' server/app/services/agent_service.py | grep -c "mcp_mode=\"disable\"\|mcp_mode='disable'"` is at least 1
    - `grep -v '^#' server/app/services/agent_service.py | grep -cE "from fastapi|from starlette"` equals 0 (transport-agnostic — no FastAPI imports in services/)
    - `cd server && pytest app/tests/agent/test_conversation_persistence.py -k 'creates_conversation or appends_to_existing or token_usage' -x -q` exits 0 with 3 PASSED
  </acceptance_criteria>
  <done>agent_service.py implements run_agent_query / persist_agent_invocation / get_or_create_conversation; 3 of 4 conversation tests pass; transport-agnostic (no FastAPI imports).</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add jobs.submit partial implementation + agent tool wrapper</name>
  <files>server/app/mcp/tools/jobs.py, server/app/agent/tools/jobs.py, server/app/tests/agent/test_jobs_tool.py</files>
  <read_first>
    - server/app/mcp/tools/jobs.py (current stub with _AVAILABLE_IN_PHASE="7" — change to partial for jobs.submit only)
    - server/app/scheduler/run.py (existing AsyncIOScheduler instance + add_job pattern from Phase 1c)
    - server/app/models/job.py (Job model — id, kind, args JSONB, status enum, idempotency_key, created_at)
    - server/app/dependencies.py (session_with_rls)
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-RESEARCH.md (Open Question 4 lines 743-747 — minimal jobs.submit)
    - server/app/tests/agent/test_jobs_tool.py (2 skip stubs — implement)
  </read_first>
  <behavior>
    - test_jobs_submit_writes_job_row: calling the jobs.submit MCP tool with `kind="reconcile_vault", args={}` creates a Job row with kind="reconcile_vault", status="pending", and the returned job_id matches the new row's id.
    - test_jobs_submit_enqueues_apscheduler: after the call, `scheduler.get_job(str(job_id))` returns a Job (verify the APScheduler instance was called with add_job(id=str(job_id), ...)) — use monkeypatch on scheduler.add_job to record the call.
  </behavior>
  <action>
    Modify `server/app/mcp/tools/jobs.py`:
      - Remove the `_AVAILABLE_IN_PHASE = "7"` constant for the jobs.submit tool (keep it for jobs.status / jobs.cancel — those remain Phase 7 stubs).
      - Replace the jobs.submit tool body with a real implementation:
        - Pydantic args: `class JobsSubmitArgs(BaseModel): kind: str; args: dict = Field(default_factory=dict); idempotency_key: str | None = None`
        - Real handler:
          1. Validate args.
          2. `async for session in session_with_rls(ctx):` — open session.
          3. Idempotency check: if idempotency_key provided AND a Job row exists with this idempotency_key for this user, return that job_id without inserting.
          4. Insert Job row: `Job(user_id=ctx.user_id, kind=args.kind, args=args.args, status="pending", idempotency_key=args.idempotency_key)`. flush + commit.
          5. Call `from app.scheduler.run import scheduler; scheduler.add_job(func=_job_dispatcher, args=[str(job.id), args.kind, args.args], id=str(job.id), replace_existing=False)` — the APScheduler instance already runs as a separate supervisord process and persists via SQLAlchemyJobStore (Phase 1c).
          6. Return `{"job_id": str(job.id), "status": "pending"}`.
        - `_job_dispatcher(job_id_str, kind, args)` — small module-level async function that updates the Job row status to "running" then dispatches to a kind→handler dispatch table. For Phase 2b the only supported kind is `reconcile_vault` which calls the existing Phase 1c handler. Any other kind sets status="failed" with detail="kind not handled in Phase 2b". Full DAG support is Phase 7.

    Create `server/app/agent/tools/jobs.py` (or extend if exists from Plan 02B-05):
      - The agent-tool wrapper for jobs.submit calls the same Pydantic-validated handler logic (refactor: extract the handler body from mcp/tools/jobs.py into a shared service function `server/app/services/jobs.py::submit_job` if the duplication is noticeable; otherwise inline-call via the MCP-tool-registration's inner function reference).
      - Replace the agent-tool jobs.submit stub (`{"error": "not_implemented", "available_in_phase": "2b-plan-06"}`) with a real call.
      - jobs.status and jobs.cancel agent wrappers remain Phase 7 stubs.

    Unskip the 2 jobs tool tests; implement bodies. Use monkeypatch to replace `scheduler.add_job` with an AsyncMock that records the call. Use db_session fixture to verify Job row creation.
  </action>
  <verify>
    <automated>cd server &amp;&amp; pytest app/tests/agent/test_jobs_tool.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -v '^#' server/app/mcp/tools/jobs.py | grep -c "scheduler.add_job\|scheduler\\.add_job"` is at least 1
    - `grep -v '^#' server/app/mcp/tools/jobs.py | grep -c "_AVAILABLE_IN_PHASE.*2b-plan-06\|not_implemented.*2b-plan-06"` equals 0 (stub removed for jobs.submit)
    - `grep -v '^#' server/app/agent/tools/jobs.py | grep -c "not_implemented.*2b-plan-06"` equals 0
    - `grep -v '^#' server/app/mcp/tools/jobs.py | grep -c "idempotency_key"` is at least 1 (idempotency check present)
    - `cd server && pytest app/tests/agent/test_jobs_tool.py -x -q` exits 0 with 2 PASSED
    - No `pytest.mark.skip` decorator remains in test_jobs_tool.py for the 2 jobs.submit tests (the jobs.status / jobs.cancel tests if any remain skip-pending Phase 7)
  </acceptance_criteria>
  <done>jobs.submit MCP + agent tool wrappers fully wired to APScheduler; 2 jobs tests pass; idempotency key enforced.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Wire brain.query MCP tool + POST /api/v1/query route + verify MCP-REST parity</name>
  <files>server/app/mcp/tools/brain.py, server/app/routes/query.py, server/app/main.py, server/app/tests/agent/test_conversation_persistence.py</files>
  <read_first>
    - server/app/mcp/tools/brain.py (existing tool registration pattern — Phase 1d real implementations of brain.search, brain.get, brain.put; lines 62-216)
    - server/app/routes/search.py (route handler analog with QueryIn/QueryResponse patterns)
    - server/app/services/agent_service.py (just-created run_agent_query)
    - server/app/main.py (existing include_router calls; capability_discovery endpoint registration if relevant)
    - server/app/services/vault_resolver.py (resolve_user_vault_id + VaultNotFound exception)
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-PATTERNS.md (§routes/query.py lines 516-569)
    - server/app/tests/agent/test_conversation_persistence.py (test_brain_query_mcp_rest_parity stub — implement)
  </read_first>
  <behavior>
    - test_brain_query_mcp_rest_parity: issue the same query under the same user_id via the MCP brain.query tool AND via POST /api/v1/query. Compare the resulting conversation + messages rows. Excluding id, conversation_id, message_id, created_at, the structural shape (role sequence, content text, citations JSON shape, tool_calls JSON shape, model string, token_usage shape) must be identical. Difference in any other field fails the test.
  </behavior>
  <action>
    Modify `server/app/mcp/tools/brain.py` to register a new MCP tool brain.query:
      - Inside the existing `register(mcp, ctx_factory)` function, add another `@mcp.tool(name="brain.query", description="Invoke the 22-tool ReAct agent over the user's vault. Returns final assistant answer with citations.")` decorator on an async function:
        ```
        async def brain_query(query: str, session_id: str | None = None) -> dict:
            ctx = ctx_factory()
            async for session in session_with_rls(ctx):
                try:
                    vault_id = await resolve_user_vault_id(session, ctx.user_id)
                    sid = uuid.UUID(session_id) if session_id else None
                    result = await run_agent_query(ctx, vault_id, query, session_id=sid)
                    return result
                except VaultNotFound as exc:
                    return _err("not_found", str(exc))
                except ValueError as exc:
                    return _err("validation_error", str(exc))
                except Exception as exc:
                    log.exception("brain_query_failed", query=query[:80])
                    return _err("internal_error", "agent invocation failed")
            return _err("internal_error", "session loop exited without result")
        ```
      - Import `run_agent_query` from `app.services.agent_service` at the top.

    Create `server/app/routes/query.py` per PATTERNS.md §routes/query.py:
      - `from __future__ import annotations`
      - imports: uuid, FastAPI APIRouter + Depends + HTTPException, Pydantic BaseModel + Field, AsyncSession, OperationContext, require_user, get_db_session, run_agent_query, VaultNotFound, resolve_user_vault_id
      - `router = APIRouter(prefix="/api/v1", tags=["query"])`
      - `class QueryIn(BaseModel): query: str = Field(..., min_length=1, max_length=4096); session_id: uuid.UUID | None = None`
      - `class QueryResponse(BaseModel): status: str; answer: str | None; tool_traces: list; warnings: list[str]; message_id: uuid.UUID; conversation_id: uuid.UUID`
      - Route handler:
        ```
        @router.post("/query", response_model=QueryResponse)
        async def query_endpoint(payload: QueryIn, ctx: OperationContext = Depends(require_user), session: AsyncSession = Depends(get_db_session)) -> QueryResponse:
            try:
                vault_id = await resolve_user_vault_id(session, ctx.user_id)
            except VaultNotFound as exc:
                raise HTTPException(status_code=404, detail={"error": {"code": "not_found", "message": str(exc)}}) from None
            result = await run_agent_query(ctx, vault_id, payload.query, session_id=payload.session_id)
            return QueryResponse(**result)
        ```
      - On unexpected exception, raise HTTPException 500 with `{"error": {"code": "internal_error", "message": "agent invocation failed"}}`.

    Modify `server/app/main.py` to include the new router:
      - Add `from app.routes import query` to the imports.
      - Add `app.include_router(query.router)` near the existing router registrations (search.router, pages.router, etc.).

    Regenerate `docs/openapi.json` if the pre-commit hook regen script (Phase 1c) does not auto-run.

    Unskip the remaining `test_brain_query_mcp_rest_parity` test in test_conversation_persistence.py. Implementation uses both transports (FastAPI TestClient for REST; direct MCP tool function invocation for stdio path; constructed OperationContexts must match on user_id, transport=mcp vs rest, remote=False, client_name="test"). After both invocations, query conversations + messages rows for that user and assert the structural diff is empty (excluding id, conversation_id, message_id, created_at columns).
  </action>
  <verify>
    <automated>cd server &amp;&amp; pytest app/tests/agent/test_conversation_persistence.py -x -q &amp;&amp; pytest app/tests/agent/ -x -q &amp;&amp; grep -q "brain.query" server/app/mcp/tools/brain.py &amp;&amp; grep -q '"/query"' server/app/routes/query.py</automated>
  </verify>
  <acceptance_criteria>
    - `grep -v '^#' server/app/mcp/tools/brain.py | grep -c 'name="brain.query"\|name=.brain.query.'` is at least 1
    - `grep -v '^#' server/app/mcp/tools/brain.py | grep -c "run_agent_query"` is at least 1
    - `grep -v '^#' server/app/routes/query.py | grep -c "@router.post"` is at least 1
    - `grep -v '^#' server/app/routes/query.py | grep -c "/query"` is at least 1
    - `grep -v '^#' server/app/routes/query.py | grep -c "QueryIn\|QueryResponse"` is at least 2
    - `grep -v '^#' server/app/main.py | grep -c "query.router\|include_router(query"` is at least 1
    - `grep -v '^#' server/app/services/agent_service.py | grep -cE "from fastapi|from starlette"` equals 0 (services remain transport-agnostic)
    - `cd server && pytest app/tests/agent/ -x -q` exits 0 with 14+ PASSED (6 react_loop + 2 tool_registry + 2 jobs + 4 conversation = 14)
    - `cd server && pytest app/tests/agent/test_conversation_persistence.py -k parity -x -q` exits 0 (dimension 12 verified)
    - `curl http://localhost:8000/openapi.json | jq '.paths."/api/v1/query"'` returns a non-null object when the app is running (optional manual spot-check — not part of automated verify)
  </acceptance_criteria>
  <done>brain.query MCP tool and POST /api/v1/query route both wired to run_agent_query; MCP-REST parity test passes; entire app/tests/agent/ suite green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| HTTP request body ↔ POST /api/v1/query | Untrusted query text + optional session_id from client; Pydantic-validated |
| MCP tool input ↔ brain.query | Untrusted query + session_id from MCP client (Claude Desktop, agent); same validation as REST |
| session_id ↔ conversations table | Must belong to the calling user (RLS) — verify on lookup |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02B-06-01 | Tampering (session hijack) | get_or_create_conversation | mitigate | session_id lookup includes WHERE user_id = ctx.user_id; missing or wrong-user session_id raises ValueError; RLS policy on conversations table provides DB-layer defence-in-depth |
| T-02B-06-02 | Information Disclosure (tool_traces leaking secrets) | persist_agent_invocation | mitigate | tool_traces are stored verbatim from the agent loop; Phase 2a redaction.py scrubber already strips provider api_keys from acompletion logs; trace observations are sanitised before insertion into messages.tool_calls JSONB |
| T-02B-06-03 | Repudiation (missing conversation row) | run_agent_query | mitigate | persist_agent_invocation called UNCONDITIONALLY at the end of run_agent_query (in the success and failure paths); test_brain_query_mcp_rest_parity asserts row creation on both transports under identical inputs |
| T-02B-06-04 | Denial of Service (oversized query) | QueryIn / brain.query args | mitigate | Pydantic max_length=4096 on query field; MCP tool wrapper also clamps before passing to run_react_loop (defence in depth) |
| T-02B-06-05 | Elevation of Privilege (job submission as another user) | jobs.submit | mitigate | Job row insert sets user_id = ctx.user_id from OperationContext; RLS on jobs table (migration 0001) enforces per-user isolation |
| T-02B-06-06 | Tampering (duplicate job submission) | jobs.submit | mitigate | idempotency_key column checked before insert; existing row returned without re-enqueue if key matches |
</threat_model>

<verification>
- `cd server && pytest app/tests/agent/ -x -q` passes all 14+ tests
- `grep -v '^#' server/app/services/agent_service.py | grep -cE "from fastapi|from starlette"` equals 0 (services transport-agnostic)
- POST /api/v1/query appears in OpenAPI spec at /openapi.json
- MCP brain.query tool callable from Claude Code (manual smoke verify in SUMMARY only)
</verification>

<success_criteria>
- agent_service.py orchestrates run_react_loop + persistence
- POST /api/v1/query REST route registered and wired
- brain.query MCP tool registered and wired
- D-08 MCP-REST parity verified by integration test
- jobs.submit partial path operational (Job row + APScheduler enqueue + idempotency)
- All 14 agent tests pass
</success_criteria>

<output>
Create `.planning/phases/02B-knowledge-graph-agent-runner/02B-06-SUMMARY.md` when done. Record: location of agent_service helpers, run_agent_query signature, list of supported job kinds in _job_dispatcher (Phase 2b: reconcile_vault only), MCP-REST parity dimensions verified, count of passing agent tests.
</output>
