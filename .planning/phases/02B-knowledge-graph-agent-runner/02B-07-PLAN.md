---
phase: 02B
plan: 07
type: execute
wave: 5
depends_on: ["02B-06"]
files_modified:
  - server/scripts/eval_agent.py
  - server/scripts/seed_golden_suite.py
  - server/app/tests/eval/test_golden_suite_seed.py
  - server/tests/fixtures/eval_baseline.json
  - .planning/phases/02B-knowledge-graph-agent-runner/02B-VALIDATION.md
autonomous: false
requirements: [AGENT-06, TEST-05]
tags: [phase-2b, wave-5, eval-runner, golden-queries, phase-3-gate]

must_haves:
  truths:
    - "scripts/eval_agent.py is invocable as `python server/scripts/eval_agent.py --fixture-vault ... --golden-queries ... --baseline ... --exit-on-critical-fail` (TEST-05)"
    - "Eval runner loads golden_queries.yaml, drives run_agent_query for each query, records metrics in golden_query_runs table"
    - "Computed metrics include: Precision@5, Recall@10, MRR, nDCG@10, p95 latency, mean cost_usd per invocation (per AI-SPEC §5 dimensions 5-8, 20, 21)"
    - "scripts/seed_golden_suite.py loads golden_queries.yaml into the golden_query_suites + golden_queries tables (AGENT-06)"
    - "Eval runner exits non-zero on any Critical dimension failure (vault-grounded recall, citation traceability, no_local_knowledge correctness, brain-first discipline, Precision@5 ≥ 0.7, MRR ≥ 0.6, retry semantics, MCP-REST parity, wikilink extraction precision)"
    - "First passing run blesses server/tests/fixtures/eval_baseline.json — subsequent runs regression-check against this baseline (>5% drop on High dimensions fails)"
    - "VALIDATION.md is updated with final status: all 14 verification rows show ✅ green; nyquist_compliant: true set in frontmatter"
  artifacts:
    - path: "server/scripts/eval_agent.py"
      provides: "Golden query eval runner; computes Precision@K, Recall@K, MRR, nDCG@K, latency, cost"
      min_lines: 200
    - path: "server/scripts/seed_golden_suite.py"
      provides: "One-shot script to load golden_queries.yaml into golden_query_suites + golden_queries tables"
      min_lines: 40
    - path: "server/tests/fixtures/eval_baseline.json"
      provides: "Blessed baseline metrics for regression comparison"
      contains: "Precision@5"
    - path: ".planning/phases/02B-knowledge-graph-agent-runner/02B-VALIDATION.md"
      provides: "Updated with green status for all 14 verification rows + nyquist_compliant: true frontmatter"
  key_links:
    - from: "server/scripts/eval_agent.py"
      to: "server/tests/fixtures/golden_queries.yaml"
      via: "yaml.safe_load + iterate"
      pattern: "golden_queries.yaml"
    - from: "server/scripts/eval_agent.py"
      to: "server/app/services/agent_service.py run_agent_query"
      via: "per-query agent invocation"
      pattern: "run_agent_query"
    - from: "server/scripts/seed_golden_suite.py"
      to: "golden_query_suites + golden_queries tables"
      via: "session_with_rls + bulk insert"
      pattern: "GoldenQuerySuite\\|GoldenQuery"
---

<objective>
Build the golden query eval runner and the DB seeding script that together turn the fixture corpus into the Phase 3 entry gate. The runner computes all 21 eval dimensions from AI-SPEC §5 against the fixture vault, exits non-zero on any Critical failure, and blesses the baseline metrics on the first passing run. The seeding script populates the golden_query_suites + golden_queries tables so the dataset is queryable via DB (AGENT-06).

This is the final plan of Phase 2b: after it lands, the Phase 3 entry gate is testable. The plan also includes a checkpoint:human-verify to confirm the gate actually passed (Precision@5 ≥ 0.7 AND MRR ≥ 0.6 — D-15) before declaring Phase 2b complete.

Purpose: TEST-05 (golden eval suite for retrieval regression), AGENT-06 (table seeding), the Phase 3 entry gate (D-15). Without this plan, Phase 3 has no quality bar to clear before its work begins.

Output: Two runnable Python scripts; a blessed baseline JSON; VALIDATION.md updated to nyquist_compliant=true; human-verified Phase 3 gate result captured in the SUMMARY.
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
@.planning/phases/02B-knowledge-graph-agent-runner/02B-VALIDATION.md
@.planning/phases/02B-knowledge-graph-agent-runner/02B-06-SUMMARY.md
@server/tests/fixtures/golden_queries.yaml
@server/tests/fixtures/sample_vault
@server/app/services/agent_service.py
@server/app/models/golden_eval.py
@server/app/scheduler/run.py
@server/scripts/regen_openapi.py

<interfaces>
Eval runner entry point (AI-SPEC §5 lines 924-933 + PATTERNS.md §scripts/eval_agent.py):
- CLI: `python scripts/eval_agent.py --fixture-vault <path> --golden-queries <path> --baseline <path> --report-out <path> [--bless] [--exit-on-critical-fail]`
- `--bless`: write current metrics as the new baseline (used on first passing main-branch run).
- `--exit-on-critical-fail`: exit 1 if any Critical dimension fails (default behaviour in CI).
- Async main pattern from server/app/scheduler/run.py lines 65-70 (asyncio.run wrapper).

Metric formulas (AI-SPEC §5 dimensions; pure Python, ~30 LOC per metric):
- Precision@K = |relevant ∩ retrieved_top_k| / K
- Recall@K = |relevant ∩ retrieved_top_k| / |relevant|
- MRR = mean(1/rank_of_expected_top_slug)
- nDCG@K = DCG/IDCG with binary relevance from expected_top_k_slugs (standard formula)
- p95 latency = numpy.percentile(latencies, 95) — or pure-Python sorted index calculation; no numpy required at this scale
- mean cost_usd per invocation = sum(llm_usage.cost_usd for conversation_id) / count(invocations) — but Phase 2b llm_usage may be 0 because Phase 2a wires usage tracking; reuse query at scripts/eval_agent.py against the llm_usage table if it exists

Critical dimensions (must pass — exit 1 on failure per AI-SPEC §5 CI/CD Integration lines 977-991):
- Vault-grounded recall (dim 1)
- Citation traceability (dim 2)
- no_local_knowledge correctness (dim 3)
- Brain-first discipline (dim 4)
- Precision@5 ≥ 0.70 (dim 5; D-15)
- MRR ≥ 0.60 (dim 6; D-15)
- Tool-error retry semantics (dim 10)
- Conversation persistence parity (dim 12)
- Wikilink extraction precision (dim 16)

High dimensions (regress > 5% vs baseline → fail):
- Recall@10 ≥ 0.80 (dim 7)
- nDCG@10 ≥ 0.65 (dim 8)
- Iteration efficiency (median ≤ 4, p95 ≤ 7) (dim 9)
- Non-critical tool skip behaviour (dim 11)
- Graph relationship accuracy (dim 13)
- Entity conflation guard (dim 14)
- Phoenix trace coverage (dim 19)

Medium dimensions (advisory, do not block):
- Stale-note awareness (dim 15)
- p95 latency < 8s (dim 20)
- Cost ceiling per query (dim 21)

Wikilink extraction snapshot test (dim 16, 17) — already covered by Plan 02B-03 expected_links.json snapshot test. The eval runner re-runs that snapshot comparison as part of its dimension-16 check.

LLM-judge for dim 1, 2, 14: per AI-SPEC §5 Labeling lines 1024 — use claude-sonnet-4-6 with a calibrated rubric. Calibration is "target Cohen's κ ≥ 0.7 before relying on the judge". For Phase 2b first run, the rubric prompt + judge invocation is implemented but the κ calibration is recorded as a Manual-Only Verification (not blocking the gate; flagged in VALIDATION.md).

Golden suite seed: insert one `GoldenQuerySuite(scope="system", user_id=None, name="phase-2b-hybrid-v1")` row, then bulk-insert 25 `GoldenQuery` rows from the YAML, mapping yaml fields → DB columns: query→query, tags→tags ARRAY, expected_top_slug→expected_top_slug, expected_status→expected_status, expected_tool_first→expected_tool_first, expected_edge_type→expected_edge_type, notes→notes, expected_top_k_slugs→expected_slugs (existing column). Idempotent: if suite name already exists, UPDATE+UPSERT children.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Build seed_golden_suite.py + unskip test_golden_suite_seed.py</name>
  <files>server/scripts/seed_golden_suite.py, server/app/tests/eval/test_golden_suite_seed.py</files>
  <read_first>
    - server/app/models/golden_eval.py (post-migration GoldenQuery columns from Plan 02B-01)
    - server/tests/fixtures/golden_queries.yaml (25 queries written in Plan 02B-02)
    - server/app/scheduler/run.py (asyncio.run entrypoint pattern lines 65-70)
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-PATTERNS.md (§scripts/eval_agent.py entrypoint pattern lines 698-723)
    - server/app/tests/eval/test_golden_suite_seed.py (2 skip stubs — implement)
  </read_first>
  <behavior>
    - test_golden_suite_loaded_from_yaml: running `python scripts/seed_golden_suite.py` against a clean test DB populates golden_query_suites with one row named "phase-2b-hybrid-v1" and golden_queries with exactly 25 rows. Re-running the script does not create duplicates (idempotent on suite name + query id).
    - test_golden_query_fields_match_yaml: every YAML query field present on the model maps to the correct DB column value; spot-check at least 3 fields per row (query, expected_top_slug, expected_status).
  </behavior>
  <action>
    Create `server/scripts/seed_golden_suite.py`:
      - `from __future__ import annotations`
      - Imports: argparse, asyncio, pathlib, yaml, structlog, AsyncSession, select, GoldenQuerySuite, GoldenQuery, session_with_rls or direct engine session (this is a script — it runs outside the FastAPI request context).
      - For session management: use `AsyncSessionLocal()` directly (not session_with_rls — scripts may run as system user). Or use `async with AsyncSessionLocal() as session: await session.execute(text("SET app.current_user_id = '00000000-0000-0000-0000-000000000000'"))` to satisfy RLS policies with the seeded system-user id (Phase 1b created a system user).
      - CLI args: `--yaml` (default: `server/tests/fixtures/golden_queries.yaml`), `--suite-name` (default: `phase-2b-hybrid-v1`), `--scope` (default: `system`).
      - Async main:
        1. Load YAML via `yaml.safe_load`.
        2. SELECT existing suite by name; if missing, INSERT.
        3. For each YAML query, UPSERT a GoldenQuery row (key: suite_id + query text — natural key). Fields: query, tags (array from yaml.tags), expected_slugs (from yaml.expected_top_k_slugs), expected_top_slug, expected_status, expected_tool_first, expected_edge_type (null if not present), notes.
        4. Commit.
        5. Log: "golden_suite_seeded", suite_name, query_count.
      - Returns exit code 0 on success.

    Unskip the 2 tests in `server/app/tests/eval/test_golden_suite_seed.py`. test_golden_suite_loaded_from_yaml runs the script (invoke `seed_main()` directly in the test rather than subprocess) and asserts row counts. test_golden_query_fields_match_yaml loads YAML and DB independently and compares row-by-row for 3 specific queries (q-001, q-007, q-013 — diverse: factual, empty-vault, graph).
  </action>
  <verify>
    <automated>cd server &amp;&amp; pytest app/tests/eval/test_golden_suite_seed.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -v '^#' server/scripts/seed_golden_suite.py | grep -c "yaml.safe_load"` is at least 1
    - `grep -v '^#' server/scripts/seed_golden_suite.py | grep -c "GoldenQuerySuite\|GoldenQuery"` is at least 2
    - `grep -v '^#' server/scripts/seed_golden_suite.py | grep -c "def main\|def _amain\|asyncio.run"` is at least 1
    - `cd server && pytest app/tests/eval/test_golden_suite_seed.py -x -q` exits 0 with 2 PASSED
    - Running the script twice in the test (idempotence check) does not change the row count
    - No `pytest.mark.skip` decorator remains in test_golden_suite_seed.py
  </acceptance_criteria>
  <done>seed_golden_suite.py populates the golden_query_suites + golden_queries tables idempotently; 2 eval tests pass.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Build scripts/eval_agent.py — the golden query eval runner</name>
  <files>server/scripts/eval_agent.py, server/tests/fixtures/eval_baseline.json</files>
  <read_first>
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-AI-SPEC.md (§5 Eval Tooling + Eval Runner lines 877-933; CI/CD Integration lines 965-991)
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-PATTERNS.md (§scripts/eval_agent.py lines 698-723)
    - server/app/services/agent_service.py (run_agent_query signature from Plan 02B-06)
    - server/tests/fixtures/golden_queries.yaml (25 queries — fields list, especially inject_failure for failure-injection probes)
    - server/tests/fixtures/sample_vault/ (16 fixture pages — indexed into test DB by the runner)
    - server/scripts/seed_golden_suite.py (just-created — call this once before iterating queries)
    - server/app/services/pages.py (upsert_page — used to write fixture pages into the test DB)
  </read_first>
  <action>
    Create `server/scripts/eval_agent.py` with the following structure:

    Header + imports (`from __future__ import annotations`):
      - asyncio, argparse, json, math, time, statistics, pathlib, hashlib, uuid
      - yaml, structlog
      - AsyncSessionLocal or session_with_rls; OperationContext; run_agent_query; upsert_page (to load fixtures); GoldenQueryRun model

    CLI args:
      - `--fixture-vault <path>` (required)
      - `--golden-queries <path>` (required)
      - `--baseline <path>` (required — path to eval_baseline.json)
      - `--report-out <path>` (default: stdout)
      - `--bless` (write current metrics as new baseline; exits 0 unconditionally — use only on intentional model/prompt changes)
      - `--exit-on-critical-fail` (default True; exits 1 if any Critical dimension fails)
      - `--llm-judge-enabled` (default False; when False, dimensions 1, 2, 14 are skipped — flagged as "advisory: judge disabled" in the report)

    Phases of the runner (`_amain`):
      1. Load fixture vault: read every .md under fixture-vault, parse via parse_vault_file, write via upsert_page into a CLEAN test DB (seed a single system user + vault first). The wikilink extractor + timeline event extractor (Plan 02B-03 hooks) run inline on each upsert → populates links + timeline_events tables.
      2. Seed golden suite: call the seed_golden_suite logic to populate golden_query_suites + golden_queries.
      3. Trigger the embedding pipeline: dispatch an APScheduler embed_worker job and wait for completion (depends on Phase 2a embedding pipeline; if Phase 2a is not yet executed at gate-run time, skip embedding and mark dimensions 5-8 as "unavailable: Phase 2a not executed").
      4. Iterate golden_queries.yaml: for each query, time the run, invoke `run_agent_query(op_ctx, vault_id, query.query, session_id=None)`, capture result + tool_traces, query llm_usage table for the conversation_id, record latency.
      5. Compute metrics for ALL 21 dimensions per AI-SPEC §5. Implementations:
         - Precision@K, Recall@K, MRR, nDCG@K: pure Python; standard formulas (~30 LOC). For each query, retrieved_top_k = list of slugs from the first brain.search observation's results, in order.
         - Vault-grounded recall (dim 1): if `--llm-judge-enabled`, prompt LiteLLM (claude-sonnet-4-6 via the Phase 2a router) with the rubric from AI-SPEC §5 dim 1 row and parse the verdict. Otherwise skip with status="advisory".
         - Citation traceability (dim 2): regex-extract `[slug]` tokens from result.answer; assert each is a member of the page set in tool_traces observations. Pure code, no judge.
         - no_local_knowledge correctness (dim 3): assert result.status == "no_local_knowledge" for queries flagged expected_status="no_local_knowledge" AND no external tool in traces (subset of {brain.search, brain.graph.traverse}).
         - Brain-first discipline (dim 4): tool_traces[0].tool_name == "brain.search" for every success-status query.
         - Iteration efficiency (dim 9): aggregate len(tool_traces) — record median and p95.
         - Tool-error retry semantics (dim 10): for inject_failure queries, mock the named tool to raise the requested exception (patch the tool wrapper temporarily; track retried flag in trace).
         - Non-critical tool skip behaviour (dim 11): similar to dim 10 but for non-critical tools — assert status=success_with_warnings.
         - MCP-REST parity (dim 12): for mcp-rest-parity tagged queries, issue same query via both transports and diff resulting rows.
         - Graph relationship accuracy (dim 13): for typed-edge queries, post-run: SELECT links rows for returned pages and assert link_type == expected_edge_type.
         - Wikilink extraction precision (dim 16): re-run the snapshot test from Plan 02B-03.
         - Wikilink idempotence (dim 17): re-run extractor on a sample page twice; diff row count.
         - Brain-first system prompt drift (dim 18): assert hash matches server/tests/fixtures/system_prompt.sha256 (Plan 02B-05 invariant).
         - Phoenix trace coverage (dim 19): if `SMARTCOPILOT_TRACING_ENABLED=true`, in-memory span collector via opentelemetry.sdk.trace.export.InMemorySpanExporter; assert the expected span tree shape per invocation.
         - p95 latency (dim 20), cost ceiling (dim 21): straightforward aggregation.
      6. Compare against baseline: load `--baseline` JSON; for each High dimension, compute delta. Flag any delta < -5%.
      7. Emit report:
         - Structured JSON to `--report-out` path (or stdout if path is "-")
         - Human-readable markdown summary to `<report-out>.md`
         - Top-level structure: `{run_id, git_sha, timestamp, summary: {pass_count, fail_count, regressed_count}, dimensions: {dim_1: {...}, ...}, queries: [{id, status, metrics, ...}]}`
      8. Exit code:
         - 0 if all Critical dimensions pass AND no High regression
         - 1 if any Critical dimension fails (with `--exit-on-critical-fail`)
         - 1 if any High dimension regressed > 5% vs baseline
         - 0 with `--bless` (skip comparison; just write baseline)

    Bless behaviour: when `--bless` is passed, write `--baseline` path with the current run's metrics. Include a `_blessed_at` ISO timestamp and `_git_sha` field at the top of the JSON.

    Create `server/tests/fixtures/eval_baseline.json` placeholder containing `{"_blessed_at": null, "_git_sha": null, "metrics": {}}` — an empty baseline. The first passing run with `--bless` populates this. Until then, the runner falls back to "no baseline available; absolute thresholds only".

    Sanity: the runner must NOT call external web APIs or any tool outside the brain.* / graph.* / entity.* namespaces during execution. The brain-first gate in Plan 05 enforces this at the agent layer.
  </action>
  <verify>
    <automated>python3 -c "import ast; ast.parse(open('server/scripts/eval_agent.py').read())" &amp;&amp; python3 server/scripts/eval_agent.py --help 2>&amp;1 | grep -q -E "fixture-vault|exit-on-critical-fail"</automated>
  </verify>
  <acceptance_criteria>
    - `python3 -c "import ast; ast.parse(open('server/scripts/eval_agent.py').read())"` exits 0 (file is valid Python)
    - `python3 server/scripts/eval_agent.py --help` prints help with `--fixture-vault`, `--golden-queries`, `--baseline`, `--exit-on-critical-fail`, `--bless` flags
    - `grep -v '^#' server/scripts/eval_agent.py | grep -c "def precision_at_k\|def precision_k\|Precision@"` is at least 1
    - `grep -v '^#' server/scripts/eval_agent.py | grep -c "def mrr\|reciprocal_rank"` is at least 1
    - `grep -v '^#' server/scripts/eval_agent.py | grep -c "def ndcg\|def n_dcg"` is at least 1
    - `grep -v '^#' server/scripts/eval_agent.py | grep -c "run_agent_query"` is at least 1
    - `grep -v '^#' server/scripts/eval_agent.py | grep -c "yaml.safe_load"` is at least 1
    - `grep -v '^#' server/scripts/eval_agent.py | grep -c "expected_status\|expected_top_slug"` is at least 2
    - `grep -v '^#' server/scripts/eval_agent.py | grep -c "exit_on_critical_fail\|exit-on-critical-fail"` is at least 1
    - `python3 -c "import json; b=json.load(open('server/tests/fixtures/eval_baseline.json')); print('metrics' in b)"` outputs True
    - `wc -l server/scripts/eval_agent.py | awk '$1 >= 200 {exit 0} {exit 1}'`
  </acceptance_criteria>
  <done>eval_agent.py is a runnable script with the documented CLI; metric implementations grep-confirmed; baseline placeholder JSON exists.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: Phase 3 entry gate verification (D-15)</name>
  <what-built>
    The eval runner (Task 2) is now operational. Running it end-to-end against the fixture vault produces the Phase 3 entry gate report. The gate criteria from D-15: Precision@5 ≥ 0.70 AND MRR ≥ 0.60 AND every Critical dimension PASS (vault-grounded recall, citation traceability, no_local_knowledge correctness, brain-first discipline, retry semantics, MCP-REST parity, wikilink precision, prompt drift hash). Plan 02B-06 SUMMARY confirmed the 14 agent tests pass; Plans 02B-03 + 02B-04 confirmed the 12 graph tests pass. This checkpoint runs the eval suite as a human-supervised gate before declaring Phase 2b complete.
  </what-built>
  <action>Pause execution. Drop and recreate the test DB, then run the full eval suite end-to-end against the fixture vault using the documented CLI. Inspect the markdown summary and confirm every Critical dimension is PASS and the D-15 thresholds are met. If green, bless the baseline and commit it. If any Critical dimension fails, halt and route to gap-closure.</action>
  <how-to-verify>
    1. Ensure the test database is clean (drop + alembic upgrade head). The fixture vault must NOT be present in any other vault.
    2. Run the full eval:
       `cd server && python scripts/eval_agent.py --fixture-vault tests/fixtures/sample_vault/ --golden-queries tests/fixtures/golden_queries.yaml --baseline tests/fixtures/eval_baseline.json --report-out /tmp/agent_eval_$(git rev-parse --short HEAD).json --exit-on-critical-fail`
    3. Inspect the printed markdown summary. Confirm:
       - All 9 Critical dimensions show PASS
       - Precision@5 mean ≥ 0.70 (D-15)
       - MRR mean ≥ 0.60 (D-15)
       - Recall@10 mean ≥ 0.80
       - nDCG@10 mean ≥ 0.65
       - p50 iteration count ≤ 4; p95 ≤ 7
       - p95 latency < 8s (advisory — may exceed in dev environment)
       - Mean cost per query < $0.05 (advisory — depends on Phase 2a model routing)
    4. If all Critical dimensions PASS, bless the baseline:
       `python scripts/eval_agent.py --fixture-vault ... --golden-queries ... --baseline tests/fixtures/eval_baseline.json --bless`
    5. Commit the updated eval_baseline.json to the repo.
    6. If any Critical dimension FAILS, the gate is RED — type `revoke` and report which dimensions failed. The orchestrator will route to gap-closure planning.
  </how-to-verify>
  <resume-signal>Type `approved` if Precision@5 ≥ 0.70 AND MRR ≥ 0.60 AND every Critical dimension PASS — Phase 2b is complete and Phase 3 may begin. Type `revoke` with the list of failing dimensions to trigger gap closure.</resume-signal>
</task>

<task type="auto" tdd="false">
  <name>Task 4: Update VALIDATION.md to nyquist_compliant=true + record gate result</name>
  <files>.planning/phases/02B-knowledge-graph-agent-runner/02B-VALIDATION.md</files>
  <read_first>
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-VALIDATION.md (current state — all 14 task rows ⬜ pending)
    - .planning/phases/02B-knowledge-graph-agent-runner/02B-06-SUMMARY.md (Plan 06 status)
    - the eval report from Task 3 (path passed in by the human checkpoint)
  </read_first>
  <action>
    Modify `.planning/phases/02B-knowledge-graph-agent-runner/02B-VALIDATION.md`:
      - Set frontmatter `nyquist_compliant: true` and `wave_0_complete: true`.
      - Update every row's Status column from `⬜ pending` to `✅ green` provided the relevant pytest commands exit 0 (verify each by running the command in the Automated Command column; record per-row in the Task 3 SUMMARY).
      - If any row would be ❌ red because its automated command fails, leave it red and DO NOT set nyquist_compliant=true — instead flag the gap and return to the orchestrator for gap-closure planning (this case is handled by checkpoint Task 3 `revoke` path).
      - Update the Validation Sign-Off section: tick every checkbox if the eval gate (Task 3) passed.
      - In the Manual-Only Verifications table, record the human-verified result of Task 3 (Phoenix trace inspection if SMARTCOPILOT_TRACING_ENABLED was set; mcp_mode=disable behaviour confirmed if exercised).
      - Append a final dated entry under the Validation Sign-Off heading: `**Phase 2b gate: PASSED on YYYY-MM-DD** — Precision@5=X.XX, MRR=Y.YY, all Critical dimensions green.` (or `FAILED` with the failing dimensions listed if Task 3 returned revoke).
  </action>
  <verify>
    <automated>grep -q "nyquist_compliant: true" .planning/phases/02B-knowledge-graph-agent-runner/02B-VALIDATION.md &amp;&amp; ! grep -q "⬜ pending" .planning/phases/02B-knowledge-graph-agent-runner/02B-VALIDATION.md</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "nyquist_compliant: true" .planning/phases/02B-knowledge-graph-agent-runner/02B-VALIDATION.md` is at least 1
    - `grep -c "wave_0_complete: true" .planning/phases/02B-knowledge-graph-agent-runner/02B-VALIDATION.md` is at least 1
    - `grep -c "⬜ pending" .planning/phases/02B-knowledge-graph-agent-runner/02B-VALIDATION.md` equals 0 (every row updated)
    - `grep -c "✅ green" .planning/phases/02B-knowledge-graph-agent-runner/02B-VALIDATION.md` is at least 14 (one per task row)
    - `grep -c "Phase 2b gate" .planning/phases/02B-knowledge-graph-agent-runner/02B-VALIDATION.md` is at least 1
  </acceptance_criteria>
  <done>VALIDATION.md reflects the gate result; nyquist_compliant=true if and only if the eval gate passed.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| eval_agent.py ↔ production DB | Eval runner must use TEST DB ONLY; refuses to run if DATABASE_URL points at production |
| LLM judge ↔ eval scoring | When --llm-judge-enabled, judge can fabricate verdicts; rubric prompt + κ calibration mitigate |
| eval_baseline.json ↔ regression gate | Baseline file is the source of truth for regression checks; tampering relaxes the gate |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02B-07-01 | Tampering (production DB write) | eval_agent.py | mitigate | Refuse to run if DATABASE_URL env var does not contain "test" substring; eval runner only operates on the dedicated test database; documented in script docstring |
| T-02B-07-02 | Repudiation (eval result fabrication) | eval_agent.py report | mitigate | report includes git_sha + timestamp + run_id (UUID); baseline file records _blessed_at + _git_sha; CI ensures the bless commit is reviewable |
| T-02B-07-03 | Tampering (LLM judge prompt injection) | dim 1, 2, 14 judge | accept | Phase 2b first run runs without judge enabled (--llm-judge-enabled=False default); dims 1, 2, 14 flagged as "advisory: judge disabled". Phase 3 calibrates κ before enabling |
| T-02B-07-04 | Information Disclosure (vault content in eval logs) | eval_agent.py logs | mitigate | structlog redaction processor (Phase 2a) scrubs any provider api_key from log output; vault content itself is non-sensitive test fixture data |
| T-02B-07-05 | Denial of Service (runaway eval) | eval_agent.py | mitigate | Each query has a 60s timeout; total run capped at 25 queries × 60s = 25min worst case; CI step has its own timeout enforcement |
</threat_model>

<verification>
- `cd server && pytest app/tests/eval/ -x -q` passes (2 golden suite seed tests)
- `python3 scripts/eval_agent.py --help` returns help text
- Full eval gate run (Task 3 human checkpoint) records the PASS/FAIL result in VALIDATION.md
- `eval_baseline.json` exists (empty placeholder before gate, blessed after gate passes)
</verification>

<success_criteria>
- seed_golden_suite.py + eval_agent.py operational
- Eval baseline placeholder exists; blessed after successful first run
- VALIDATION.md reflects nyquist_compliant=true if and only if eval gate passes
- Phase 2b is complete after this plan AND the Phase 3 entry gate is verified as green (or routed to gap-closure if red)
</success_criteria>

<output>
Create `.planning/phases/02B-knowledge-graph-agent-runner/02B-07-SUMMARY.md` when done. Record: count of golden queries seeded into DB, eval runner LOC, baseline blessing timestamp + git_sha, per-dimension PASS/FAIL summary from Task 3, any Manual-Only Verifications that remain pending.

Final Phase 2b deliverable: this SUMMARY is the artifact the orchestrator reads to confirm Phase 2b is complete and Phase 3 may begin.
</output>
