---
phase: 02A
plan: 02
type: execute
wave: 2
depends_on: [02A-01]
files_modified:
  - server/app/llm/__init__.py
  - server/app/llm/tiers.py
  - server/app/llm/keys.py
  - server/app/llm/router.py
  - server/app/llm/usage.py
  - server/app/main.py
  - server/app/tests/llm/test_router.py
  - server/app/tests/llm/test_keys.py
  - server/app/tests/llm/test_usage_recorder.py
autonomous: true
requirements: [LLM-01, LLM-02, LLM-03, LLM-04, LLM-05]
tags: [rag, phase-2a, llm-router, litellm, cost-tracking, provider-keys]

must_haves:
  truths:
    - "from app.llm.router import llm_complete, embed_chunks succeeds; await llm_complete(session, ctx, prompt=..., tier='cheap') returns the completion text"
    - "Every successful llm_complete / embed_chunks call results in exactly one new row in llm_usage with user_id = ctx.user_id, provider, model, input_tokens, output_tokens, cost_usd populated"
    - "Per-user provider key (Fernet-decrypted) is used when present; otherwise the system-user shared key is used (PRD §24.2 resolution order)"
    - "When neither user nor system key exists, llm_complete raises MissingProviderKey(provider); no LiteLLM call is made and no llm_usage row is written"
    - "api_key value never appears in structlog output, llm_usage rows, or any exception message — only the 4-char hint may be logged"
    - "Tier name 'cheap' maps to settings.llm_tier_cheap; 'balanced' to settings.llm_tier_balanced; 'strong' to settings.llm_tier_strong; unknown tier raises LLMRouterError"
    - "DeepSeek (deepseek/deepseek-chat) and Ollama (ollama/llama3) tier values are accepted and routed without error (LLM-04)"
  artifacts:
    - path: "server/app/llm/__init__.py"
      provides: "Package init; re-exports llm_complete, embed_chunks, MissingProviderKey, LLMRouterError from router"
      contains: "llm_complete"
    - path: "server/app/llm/tiers.py"
      provides: "TIER_MODELS dict built from settings at module load; resolve_tier(name) returns model id; raises LLMRouterError on unknown"
      contains: "TIER_MODELS"
    - path: "server/app/llm/keys.py"
      provides: "resolve_api_key(session, ctx, *, provider) implementing PRD §24.2 order (per-user, system fallback, error)"
      contains: "resolve_api_key"
    - path: "server/app/llm/router.py"
      provides: "llm_complete() and embed_chunks() — sole allowed LiteLLM call sites in the codebase"
      contains: "from litellm import"
    - path: "server/app/llm/usage.py"
      provides: "UsageRecorder(CustomLogger) with async_log_success_event writing to llm_usage under system context"
      contains: "async_log_success_event"
    - path: "server/app/main.py"
      provides: "Lifespan registers litellm.callbacks = [UsageRecorder()] once at startup"
      contains: "UsageRecorder"
  key_links:
    - from: "server/app/main.py"
      to: "litellm.callbacks"
      via: "lifespan startup hook"
      pattern: "litellm.callbacks"
    - from: "server/app/llm/router.py"
      to: "app.llm.keys.resolve_api_key"
      via: "per-call api_key kwarg lookup"
      pattern: "resolve_api_key"
    - from: "server/app/llm/router.py"
      to: "app.llm.usage.UsageRecorder.async_log_success_event"
      via: "litellm metadata user_id, callback then INSERT INTO llm_usage"
      pattern: "metadata"
    - from: "server/app/llm/keys.py"
      to: "app.encryption.decrypt_provider_key"
      via: "Fernet decryption of per-user / system ProviderKey rows"
      pattern: "decrypt_provider_key"
---

<objective>
Build the single choke-point for all LLM and embedding I/O. app/llm/router.py is the only module in the codebase allowed to import litellm directly (TID251 ignores set in Plan 01); every other module must call llm_complete() or embed_chunks(). The router resolves the model from a tier name, fetches the user's encrypted provider key (system fallback), passes the decrypted key per-call (never via os.environ), and threads metadata={"user_id": ...} so the UsageRecorder callback can write llm_usage rows under a system RLS context.

Purpose: Close the entire LLM layer in one wave so subsequent plans (chunker/embedder in Plan 03, intent classifier expansion in Plan 04) consume a stable async API.

Output: app/llm/{router,tiers,keys,usage}.py, lifespan registration of the UsageRecorder, and real tests replacing the xfail stubs Plan 01 wrote for LLM-01..LLM-05.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-CONTEXT.md
@.planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-RESEARCH.md
@.planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-PATTERNS.md
@.planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-AI-SPEC.md
@.planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-01-SUMMARY.md

<interfaces>
<!-- Patterns and contracts the executor must reuse without re-discovering -->

From server/app/services/provider_keys.py:
- class MissingProviderKey(Exception): def __init__(self, provider: str) — reuse this exception class; do NOT duplicate
- async def get_for_user(session, *, user_id, provider) returns ProviderKey | None — existing helper Plan 02 wraps
- Resolution order (PRD §24.2 / AUTH-10): per-user row, system user row, then MissingProviderKey

From server/app/auth/context.py:
- OperationContext(user_id, role, transport, remote, client_name, request_id) — passed into router; do not modify
- SYSTEM_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
- system_operation_context(*, request_id, client_name) returns OperationContext — used by UsageRecorder to write llm_usage under system RLS

From server/app/encryption.py:
- decrypt_provider_key(ciphertext: bytes) returns str — already wired; use as-is
- Never log raw plaintext or the bytes ciphertext

From server/app/dependencies.py:
- async def session_with_rls(ctx) returns AsyncIterator[AsyncSession] — sets app.current_user_id, app.current_user_role, app.request_id GUCs, RESETs in finally; canonical non-FastAPI session

From server/app/models/llm_usage.py:
- class LLMUsage(Base) with columns: id BigInt PK, user_id UUID FK users.id, provider str(64), model str(128), input_tokens int, output_tokens int, cost_usd Numeric(12,6), conversation_id UUID nullable, created_at datetime. No request_id column.

From server/app/settings.py (Plan 01 additions):
- settings.llm_tier_cheap, settings.llm_tier_balanced, settings.llm_tier_strong — model id strings like "openai/gpt-4o-mini"

From litellm 1.83.14 (installed):
- from litellm import acompletion, aembedding, completion_cost — async APIs
- from litellm.integrations.custom_logger import CustomLogger — base class
- CustomLogger.async_log_success_event(self, kwargs, response_obj, start_time, end_time) — async variant required for SQLAlchemy I/O (Pitfall 1)
- response_obj.usage.prompt_tokens / response_obj.usage.completion_tokens available on completion responses; response_obj.usage.total_tokens on embedding responses
- metadata={"user_id": "..."} kwarg passes through to callback

From server/app/main.py (current lifespan):
- @asynccontextmanager async def lifespan(app) — calls configure_logging(), _fail_startup_if_missing_secrets(), starts IndexEventListener. Plan 02 inserts UsageRecorder registration after configure_logging and before yield.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Tier resolution and provider key resolution (llm/tiers.py, llm/keys.py)</name>
  <files>server/app/llm/__init__.py, server/app/llm/tiers.py, server/app/llm/keys.py, server/app/tests/llm/test_keys.py</files>
  <read_first>
    - server/app/services/provider_keys.py (resolution order pattern lines 114-133 per PATTERNS §llm/keys.py)
    - server/app/auth/context.py (SYSTEM_USER_ID + OperationContext)
    - server/app/encryption.py (decrypt_provider_key signature)
    - server/app/settings.py (post-Plan-01 llm_tier_* fields)
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-PATTERNS.md (sections llm/tiers.py and llm/keys.py)
    - server/app/tests/auth/test_provider_keys.py (test analog if present)
  </read_first>
  <behavior>
    - TIER_MODELS["cheap"] equals settings.llm_tier_cheap at import time
    - resolve_tier("balanced") equals settings.llm_tier_balanced; resolve_tier("unknown") raises LLMRouterError
    - resolve_api_key(session, ctx, provider="openai") returns the decrypted per-user key when ctx.user_id has a provider_keys row for "openai"
    - When ctx.user_id has no row but SYSTEM_USER_ID does, returns decrypted system key
    - When neither has a row, raises MissingProviderKey(provider="openai")
    - Decrypted plaintext is never returned in logs (verify by reviewing log.info/.error lines added)
  </behavior>
  <action>
    Create server/app/llm/__init__.py containing a single docstring; defer re-exports until router.py exists (Task 2).

    Create server/app/llm/tiers.py:
    - Use from __future__ import annotations
    - Import settings from app.settings
    - Define module-level TIER_MODELS dict mapping "cheap" to settings.llm_tier_cheap, "balanced" to settings.llm_tier_balanced, "strong" to settings.llm_tier_strong
    - Define class LLMRouterError(Exception): pass (router.py will re-export)
    - Define def resolve_tier(name: str) returns str; on missing tier raises LLMRouterError with message "unknown tier: {name!r}"

    Create server/app/llm/keys.py:
    - Use from __future__ import annotations; import AsyncSession, OperationContext, SYSTEM_USER_ID, decrypt_provider_key, MissingProviderKey from app.services.provider_keys, get_for_user from app.services.provider_keys
    - Define async def resolve_api_key(session: AsyncSession, ctx: OperationContext, *, provider: str) returns str. Body: call get_for_user(session, user_id=ctx.user_id, provider=provider); if not None, return decrypt_provider_key(row.encrypted_key). Else call get_for_user(session, user_id=SYSTEM_USER_ID, provider=provider); if not None, return decrypted system key. Else raise MissingProviderKey(provider).
    - Never log the decrypted return value; if you must log resolution decisions, log only provider and source ("user" or "system").

    Replace the Wave 0 stub at server/app/tests/llm/test_keys.py with real tests:
    - test_resolve_returns_user_key: seed a user; insert a ProviderKey row encrypted via encrypt_provider_key; call resolve_api_key and assert plaintext matches
    - test_resolve_falls_back_to_system_key: insert ProviderKey only for SYSTEM_USER_ID; assert plaintext matches
    - test_resolve_raises_when_missing: no rows; assert MissingProviderKey raised with .provider == "openai"
    Mark with pytestmark = [pytest.mark.llm, pytest.mark.integration] since testcontainers DB is required for the seed.
  </action>
  <verify>
    <automated>cd server && python -c "from app.llm.tiers import TIER_MODELS, resolve_tier, LLMRouterError; assert TIER_MODELS['cheap'] and resolve_tier('cheap') == TIER_MODELS['cheap']" && cd server && pytest app/tests/llm/test_keys.py -q -m "llm"</automated>
  </verify>
  <acceptance_criteria>
    - server/app/llm/__init__.py exists (may be empty or docstring-only)
    - server/app/llm/tiers.py source contains TIER_MODELS, resolve_tier, class LLMRouterError
    - server/app/llm/keys.py source contains async def resolve_api_key and references SYSTEM_USER_ID and decrypt_provider_key
    - server/app/llm/keys.py source does NOT contain a log call that includes plaintext (grep -E "log\.(info|debug|warning|error).*plaintext" returns empty)
    - cd server && pytest app/tests/llm/test_keys.py -q exits 0 with at least 3 passing tests
    - cd server && python -c "from app.llm.tiers import resolve_tier; resolve_tier('cheap')" exits 0
    - cd server && python -c "from app.llm.tiers import resolve_tier, LLMRouterError; resolve_tier('bogus')" exits non-zero with LLMRouterError
  </acceptance_criteria>
  <done>
    Tier dispatch and provider key resolution are pure, testable services. They satisfy LLM-02 (tiers) and LLM-05 (per-user, system fallback, error resolution). Router (Task 2) consumes them.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: LLM router and UsageRecorder callback (llm/router.py, llm/usage.py)</name>
  <files>server/app/llm/router.py, server/app/llm/usage.py, server/app/llm/__init__.py, server/app/main.py, server/app/tests/llm/test_router.py, server/app/tests/llm/test_usage_recorder.py</files>
  <read_first>
    - server/app/llm/tiers.py (Task 1 output: TIER_MODELS, resolve_tier, LLMRouterError)
    - server/app/llm/keys.py (Task 1 output: resolve_api_key)
    - server/app/services/provider_keys.py (MissingProviderKey to re-export)
    - server/app/auth/context.py (system_operation_context for callback)
    - server/app/dependencies.py (session_with_rls for callback DB writes)
    - server/app/models/llm_usage.py (LLMUsage columns)
    - server/app/main.py (current lifespan; identify insertion point right after configure_logging())
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-AI-SPEC.md §3 (callback pattern, per-call api_key)
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-RESEARCH.md §Pattern 1, §Pitfall 1, §Pitfall 2, §Pitfall 5
    - .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-PATTERNS.md §llm/router.py
  </read_first>
  <behavior>
    - llm_complete(session, ctx, prompt="hi", tier="cheap") calls litellm.acompletion with model=resolve_tier("cheap"), messages=[{"role":"user","content":"hi"}], api_key from resolve_api_key, metadata={"user_id": str(ctx.user_id)}, caching=True, ttl=3600 and returns response.choices[0].message.content
    - embed_chunks(texts, op_ctx=ctx, session=session) accepts list[str], calls litellm.aembedding(model="openai/text-embedding-3-small", input=texts, api_key=<decrypted>, metadata={"user_id": str(op_ctx.user_id)}) and returns list[list[float]] extracted from response.data
    - Router catches MissingProviderKey and re-raises; no llm_usage row is written
    - Router catches litellm.exceptions.AuthenticationError and surfaces it as LLMRouterError("auth") so callers can react without leaking the key
    - UsageRecorder.async_log_success_event (NOT sync log_success_event) inserts an llm_usage row using system_operation_context-backed session_with_rls; row contains user_id from kwargs metadata user_id, provider (first part of model id), model (full id), input_tokens and output_tokens from response_obj.usage.prompt_tokens/completion_tokens (fallback to total_tokens for embeddings), cost_usd from litellm.completion_cost(response_obj) cast to Decimal (default Decimal(0) on exception)
    - UsageRecorder strips api_key from any kwargs snapshot it logs (must not appear in stdout/stderr or DB)
  </behavior>
  <action>
    Create server/app/llm/router.py per PATTERNS §llm/router.py. Imports: from __future__ import annotations, from typing import Any, Literal, import litellm, from litellm import acompletion, aembedding, from litellm.exceptions import AuthenticationError, RateLimitError, from sqlalchemy.ext.asyncio import AsyncSession, from app.auth.context import OperationContext, from app.llm.keys import resolve_api_key, from app.llm.tiers import LLMRouterError, resolve_tier, from app.services.provider_keys import MissingProviderKey. Add import structlog; log = structlog.get_logger("smart_copilot.llm.router").

    Define async def llm_complete(session: AsyncSession, ctx: OperationContext, *, prompt: str, tier: Literal["cheap","balanced","strong"], response_format: dict | None = None) returns str. Body: model_id = resolve_tier(tier); provider = model_id.split("/", 1)[0]; api_key = await resolve_api_key(session, ctx, provider=provider). Build kwargs dict with model, messages=[{"role":"user","content":prompt}], api_key, metadata={"user_id": str(ctx.user_id)}, caching=True, ttl=3600; conditionally add response_format. Wrap response = await acompletion(**kwargs) in try/except AuthenticationError that raises LLMRouterError("auth") from None, and except RateLimitError that raises LLMRouterError("rate_limited") from None. Return response.choices[0].message.content.

    Define async def embed_chunks(texts: list[str], *, op_ctx: OperationContext, session: AsyncSession) returns list[list[float]]. Body: model_id = "openai/text-embedding-3-small"; provider = "openai"; api_key = await resolve_api_key(session, op_ctx, provider=provider). Call response = await aembedding(model=model_id, input=texts, api_key=api_key, metadata={"user_id": str(op_ctx.user_id)}). Return [item["embedding"] if isinstance(item, dict) else item.embedding for item in response.data]. Wrap in same auth/rate-limit handling.

    Re-export from server/app/llm/__init__.py: from app.llm.router import llm_complete, embed_chunks, LLMRouterError; from app.services.provider_keys import MissingProviderKey (re-export so callers can use from app.llm import MissingProviderKey).

    Create server/app/llm/usage.py:
    - Imports: from __future__ import annotations, import uuid, from decimal import Decimal, from typing import Any, import structlog, import litellm, from litellm.integrations.custom_logger import CustomLogger, from sqlalchemy import insert, from app.auth.context import system_operation_context, from app.dependencies import session_with_rls, from app.models.llm_usage import LLMUsage
    - log = structlog.get_logger("smart_copilot.llm.usage")
    - Define class UsageRecorder(CustomLogger) with async def async_log_success_event(self, kwargs: dict, response_obj: Any, start_time, end_time) returns None. Body: extract metadata = kwargs.get("metadata") or {}; user_id_str = metadata.get("user_id"); if missing or invalid UUID, log a single warning event with NO api_key and return. Extract model = kwargs.get("model") or ""; provider = model.split("/", 1)[0]. Token extraction: usage = getattr(response_obj, "usage", None); input_tokens = getattr(usage, "prompt_tokens", 0) or 0; output_tokens = getattr(usage, "completion_tokens", 0) or 0. If both 0 and usage has total_tokens, use total_tokens for input_tokens (embedding response). Cost: try cost = Decimal(str(litellm.completion_cost(completion_response=response_obj) or 0)) except Exception cost = Decimal(0). Write row: ctx = system_operation_context(request_id="usage_recorder", client_name="litellm_callback"); async for session in session_with_rls(ctx): await session.execute(insert(LLMUsage).values(user_id=uuid.UUID(user_id_str), provider=provider, model=model, input_tokens=input_tokens, output_tokens=output_tokens, cost_usd=cost)); await session.commit(). Wrap the entire body in try/except and log on failure (never raise — callback errors must not break the request).

    Register at startup: edit server/app/main.py lifespan async context manager. After configure_logging() and before _fail_startup_if_missing_secrets(), add import litellm; from app.llm.usage import UsageRecorder; litellm.callbacks = [UsageRecorder()]. Place the import block inside the lifespan function (lazy) to avoid affecting test collection.

    Replace Wave 0 stub server/app/tests/llm/test_router.py with real tests using unittest.mock.patch on app.llm.router.acompletion / app.llm.router.aembedding (so we never hit a real provider):
    - test_tier_resolution_cheap: mock acompletion to return canned response; assert model kwarg starts with settings.llm_tier_cheap split on "/"
    - test_provider_routing_deepseek: monkeypatch app.llm.tiers.TIER_MODELS["balanced"] = "deepseek/deepseek-chat"; assert mocked call uses deepseek provider — covers LLM-04
    - test_missing_provider_key_raises: no ProviderKey rows; assert MissingProviderKey raised and acompletion not called
    - test_per_call_api_key_passed: assert mocked call_kwargs api_key equals decrypted plaintext and os.environ.get("OPENAI_API_KEY") is unchanged after the call (covers Pitfall 2)
    - test_metadata_user_id_propagated: assert metadata["user_id"] == str(ctx.user_id) in call_kwargs

    Create server/app/tests/llm/test_usage_recorder.py:
    - test_async_log_success_event_writes_llm_usage_row: build a fake response_obj with usage.prompt_tokens=10, usage.completion_tokens=5, choices[0].message.content="x"; call await UsageRecorder().async_log_success_event(kwargs={"model":"openai/gpt-4o-mini","metadata":{"user_id": str(seed_user)}}, response_obj=fake_resp, start_time=0, end_time=0); assert one row in llm_usage with matching user_id, provider="openai", model="openai/gpt-4o-mini", input_tokens=10, output_tokens=5
    - test_callback_swallows_errors: pass kwargs={} (no metadata) and assert no exception escapes; no row written
    - test_callback_does_not_log_api_key: pass kwargs={"api_key": "sk-leaked", "model": "openai/gpt-4o-mini", "metadata": {"user_id": str(seed_user)}}; capture log output (caplog or capsys) and assert "sk-leaked" does not appear
  </action>
  <verify>
    <automated>cd server && pytest app/tests/llm/ -q -m "llm" 2>&1 | tail -20 && cd server && python -c "from app.llm import llm_complete, embed_chunks, LLMRouterError, MissingProviderKey; print('ok')" && cd server && python -c "from app.llm.usage import UsageRecorder; r = UsageRecorder(); assert hasattr(r, 'async_log_success_event')" && cd server && ruff check app/ --select TID 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - server/app/llm/router.py source contains from litellm import acompletion, aembedding and async def llm_complete(, async def embed_chunks(
    - server/app/llm/router.py never sets os.environ for any *_API_KEY (grep -E "os\.environ\[.*_API_KEY" returns empty)
    - server/app/llm/router.py passes api_key as a kwarg to acompletion and aembedding (grep -E "api_key\s*=\s*api_key" returns at least 2 matches)
    - server/app/llm/router.py passes metadata={"user_id"...} to acompletion and aembedding (grep -E "metadata=.*user_id" returns at least 2 matches)
    - server/app/llm/usage.py source contains class UsageRecorder(CustomLogger), async def async_log_success_event, system_operation_context, session_with_rls
    - server/app/llm/usage.py does NOT define log_success_event (sync variant) — grep -E "def log_success_event" returns empty (the sync variant would block the event loop per Pitfall 1)
    - server/app/main.py lifespan body contains UsageRecorder and litellm.callbacks
    - server/app/llm/__init__.py source contains from app.llm.router import llm_complete, embed_chunks, LLMRouterError and from app.services.provider_keys import MissingProviderKey
    - cd server && pytest app/tests/llm/ -q -m "llm" exits 0 with at least 9 passing tests (5 router + 3 keys + 3 usage_recorder, minimum)
    - cd server && ruff check app/ --select TID exits 0 (router/tiers/keys are per-file-ignored; no other module imports litellm)
    - grep -rE "^(import litellm|from litellm)" server/app/ --include="*.py" | grep -vE "/llm/(router|tiers|keys|usage)\.py:" | grep -v "/tests/" returns empty (only the four llm submodules and tests are allowed to mention litellm)
    - cd server && python -c "import litellm; from app.llm.usage import UsageRecorder; litellm.callbacks = [UsageRecorder()]; assert any(isinstance(cb, UsageRecorder) for cb in litellm.callbacks)" exits 0
  </acceptance_criteria>
  <done>
    LLM router is the sole LiteLLM entry point. UsageRecorder writes one llm_usage row per successful call under system RLS. Lifespan registers the callback at startup. All five LLM requirements (LLM-01 library mode, LLM-02 tier resolution, LLM-03 cost tracking, LLM-04 multi-provider routing, LLM-05 per-user + system key resolution) are satisfied with real tests in place of Plan 01 xfail stubs. Pitfall 1 (sync callback) and Pitfall 2 (global env var) are guarded by acceptance criteria greps.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Caller (route/service) -> llm/router.py | All LiteLLM kwargs flow through router; tier name and prompt are caller-controlled; api_key is router-resolved per call |
| Router -> LiteLLM HTTP egress | Decrypted provider API key crosses to OpenAI/Anthropic/DeepSeek; key must travel only via per-call api_key kwarg, never env var |
| LiteLLM callback -> llm_usage table | UsageRecorder writes under system RLS context (SYSTEM_USER_ID); kwargs metadata is the only attribution path |
| Provider key column (provider_keys.encrypted_key) -> router runtime memory | Decrypted plaintext lives only inside an in-flight router call frame; must not be logged, persisted, or stored in object attributes |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02A-02-01 | Information Disclosure | Per-user provider API keys | mitigate | Decrypted key passed only as per-call api_key kwarg; never assigned to os.environ; UsageRecorder strips api_key from any kwargs snapshot before logging; acceptance criterion greps for os.environ[*_API_KEY] write attempts and "sk-leaked" log output |
| T-02A-02-02 | Tampering | User attribution in llm_usage | mitigate | metadata["user_id"] threaded from OperationContext at call site; UsageRecorder rejects rows with missing/invalid UUID; system context (RLS bypass) used only for the callback INSERT, never for the LiteLLM call itself |
| T-02A-02-03 | Denial of Service | Event loop blocked by sync DB callback | mitigate | UsageRecorder implements async_log_success_event (NOT log_success_event); acceptance criterion grep enforces this. Try/except around the entire callback body so a DB failure never breaks the in-flight request |
| T-02A-02-04 | Elevation of Privilege | Cross-user key bleed via global env | mitigate | os.environ key writes forbidden (acceptance grep); per-call api_key kwarg ensures user-A request cannot accidentally use user-B's key on a shared process |
| T-02A-02-05 | Repudiation | LLM cost cannot be attributed to a user | mitigate | Every successful call writes one llm_usage row with user_id, provider, model, input_tokens, output_tokens, cost_usd; test_async_log_success_event_writes_llm_usage_row enforces |
| T-02A-02-SC | Tampering | npm/pip/cargo installs | mitigate | RESEARCH §Package Legitimacy Audit verified litellm and tiktoken on PyPI; both Approved; Plan 01 already pinned versions; no new installs in Plan 02 |
</threat_model>

<verification>
- Unit + integration tests for the llm/ package: cd server && pytest app/tests/llm/ -q -m "llm"
- Ruff TID lint: cd server && ruff check app/ --select TID exits 0 (per-file-ignores cover router/tiers/keys/usage)
- Direct litellm import grep: grep -rE "^(import litellm|from litellm)" server/app/ --include="*.py" | grep -vE "/llm/(router|tiers|keys|usage)\.py:" | grep -v "/tests/" returns empty
- Lifespan smoke test: cd server && python -c "from app.main import create_app; app = create_app(); print('app created')" exits 0
- Full suite still green: cd server && pytest app/tests/ -q
</verification>

<success_criteria>
1. from app.llm import llm_complete, embed_chunks, LLMRouterError, MissingProviderKey succeeds (LLM-01 library mode wired)
2. resolve_tier("cheap"/"balanced"/"strong") returns the configured model id; unknown tier raises LLMRouterError (LLM-02)
3. After llm_complete with metadata={"user_id": ctx.user_id} returns successfully, a new row exists in llm_usage with that user_id, provider, model, tokens, cost_usd (LLM-03)
4. Tier value "deepseek/deepseek-chat" routes via the same router without provider-specific branching (LLM-04)
5. With per-user ProviderKey row present, resolve_api_key returns user plaintext; absent, system plaintext; absent both, MissingProviderKey raised (LLM-05)
6. No module outside server/app/llm/ imports litellm (Ruff TID gate plus grep verification)
</success_criteria>

<output>
Create .planning/phases/02A-llm-gateway-hybrid-rag-pipeline/02A-02-SUMMARY.md when done.
</output>
