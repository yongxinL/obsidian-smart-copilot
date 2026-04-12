# THREADWORK

Threadwork is an AI coding workflow tool that combines spec-driven project orchestration, hook-enforced quality gates, structured session handoffs, and token budget management into a single framework for Claude Code and Codex. It gives every AI session perfect context, every agent the right specs, and every developer a reliable way to hand off and resume work across sessions.

**Setup**: `npx threadwork-cc@latest && threadwork init`

---

## Behavioral Rules (Read Before Starting Any Work)

1. **If `.threadwork/state/checkpoint.json` exists and is not cleared** — read it first. Context was lost mid-session. Run `/tw:resume` to restore.
2. **Check token budget before starting any complex task** — run `/tw:budget` or `/tw:estimate <task>`. Budget warnings at 80% and 90% are mandatory stopping points.
3. **Never write framework files to the project root** — only `CLAUDE.md` / `AGENTS.md` belongs at root. All state goes in `.threadwork/`.
4. **Always commit atomically** — one task, one commit. Format: `T-N-M-K: <description>`.
5. **Quality gates are non-negotiable** — the Ralph Loop will re-invoke you if lint/typecheck/tests fail. Fix the actual error, do not suppress it.
6. **Specs override habits** — if a spec says "use jose for JWT", use jose. Not jsonwebtoken. Not a custom implementation.
7. **Run `/tw:done` at the end of every session** — this generates the handoff doc and resume prompt. Skipping it means losing session context.
8. **In Team mode, `BUDGET_LOW` is a hard stop** — if your worker budget drops below 10%, write a checkpoint and send `BUDGET_LOW` to the orchestrator immediately. Do not continue executing tasks.

---

## Slash Command Reference

| Command | Description | When to Use |
|---------|-------------|-------------|
| `/tw:new-project` | Init project — 7 clarifying questions → PROJECT.md + REQUIREMENTS.md + ROADMAP.md | Start of new project |
| `/tw:analyze-codebase` | Map brownfield codebase → detect framework, generate starter specs | Existing project |
| `/tw:discuss-phase <N>` | Capture library/pattern decisions before planning | Before plan-phase |
| `/tw:plan-phase <N>` | Generate XML plans with token estimates + phase budget preview | After discuss-phase |
| `/tw:execute-phase <N>` | Parallel wave execution with spec injection + Ralph Loop | After plan-phase |
| `/tw:execute-phase <N> --team` | Team-model parallel execution with bidirectional escalation | After plan-phase (multi-agent) |
| `/tw:execute-phase <N> --no-team` | Force legacy fire-and-forget execution | When budget is tight |
| `/tw:verify-phase <N>` | Goal-backward verification + token variance report | After execute-phase |
| `/tw:quick <desc>` | Fast task — shows estimate first, executes, commits | Small tasks |
| `/tw:parallel <desc>` | Isolated worktree execution → draft PR | Parallel features |
| `/tw:status` | Full dashboard — phase, task, budget, quality gate status | Anytime |
| `/tw:budget` | Token budget dashboard with last task variances | Anytime |
| `/tw:estimate <desc>` | Token estimate before committing to a task | Before big tasks |
| `/tw:tokens` | Full session token log | Anytime |
| `/tw:variance` | Phase token variance report with recommendations | After execute/verify |
| `/tw:done` | End session — generate 10-section handoff + resume prompt | End of session |
| `/tw:handoff` | Manage handoffs: list, show <N>, resume | Cross-session |
| `/tw:resume` | Load latest handoff and announce readiness | Session start |
| `/tw:recover` | Restore from checkpoint after crash | After crash |
| `/tw:tier` | View or set skill tier (beginner/advanced/ninja) | Anytime |
| `/tw:recall <query>` | Search journals, specs, handoffs, history | Context lookup |
| `/tw:specs` | Manage spec library — list, show, add, edit, review proposals | Anytime |
| `/tw:journal` | View/search session journals | Context lookup |
| `/tw:clear` | Close phase, increment phase counter, prepare for next | End of phase |
| `/tw:audit-milestone <N>` | Cross-phase milestone verification | End of milestone |

---

## Directory Structure

```
.threadwork/
├── state/
│   ├── project.json           ← Project metadata, current phase/milestone, skill tier, budget
│   ├── checkpoint.json        ← Recovery point (auto-written after each task)
│   ├── active-task.json       ← Currently executing task
│   ├── completed-tasks.json   ← Task completion log
│   ├── token-log.json         ← Token usage + variance data
│   ├── team-session.json      ← Active team coordination state (cleared after each wave)
│   ├── hook-log.json          ← Hook execution log + threshold events
│   ├── ralph-state.json       ← Quality gate retry state
│   ├── quality-config.json    ← Which gates are enabled/blocking
│   └── phases/
│       └── phase-N/
│           ├── CONTEXT.md     ← Phase discussion output
│           ├── deps.json      ← Plan dependency graph
│           ├── VERIFICATION.md ← Verification + variance report
│           ├── UAT.md         ← Manual test steps
│           └── plans/
│               └── PLAN-N-*.xml ← Executable task plans with token estimates
├── specs/
│   ├── index.md               ← Auto-rebuilt spec index
│   ├── frontend/              ← Frontend patterns (react, styling)
│   ├── backend/               ← Backend patterns (api, auth)
│   ├── testing/               ← Test standards
│   └── proposals/             ← AI-proposed spec updates (review with /tw:specs proposals)
└── workspace/
    ├── journals/              ← Session journals (YYYY-MM-DD-N.md)
    ├── handoffs/              ← 10-section session handoffs
    └── archive/               ← Journals/handoffs older than 30 days
```

---

## Hook System

Threadwork registers 4 hooks into `~/.claude/settings.json` (Claude Code) or `AGENTS.md` (Codex):

| Hook | Event | What It Does |
|------|-------|-------------|
| `session-start.js` | SessionStart | Injects project context, token budget, skill tier into every session |
| `pre-tool-use.js` | PreToolUse (Task + TeamCreate) | Injects relevant specs + tier instructions into every subagent prompt; injects budget + tier into TeamCreate calls |
| `post-tool-use.js` | PostToolUse | Tracks token usage, detects learning patterns, writes checkpoint |
| `subagent-stop.js` | SubagentStop | **Ralph Loop** — runs quality gates, blocks completion on failure |

Hooks never crash sessions (exit 0 on error). Hook log: `.threadwork/state/hook-log.json`.

---

## Skill Tier System

Set at `threadwork init`. Change anytime with `/tw:tier set <tier>`.

| Tier | What Changes |
|------|-------------|
| **beginner** | Step-by-step reasoning, inline code comments, quality gate error explanations, "you are here" orientation |
| **advanced** | Concise 1–2 sentence summaries, comments for non-obvious logic only, terse status updates *(default)* |
| **ninja** | Code only, no narration, raw error output, single emoji warnings |

The tier is injected into every subagent prompt by the pre-tool-use hook — it applies uniformly.

---

## Token Budget System

Configured at `threadwork init` (default: 800K = 80% of Sonnet's 1M context).

| Threshold | What Happens |
|-----------|-------------|
| **80% consumed** | `⚠️` warning injected into next prompt — "consider wrapping up after current task" |
| **90% consumed** | `🚨` critical warning — "run /tw:done NOW before context is lost" |
| **95% consumed** | Handoff auto-generated even without user command |

Check budget: `/tw:budget`. Estimate before starting: `/tw:estimate <task>`.

---

## Typical Workflow

```
threadwork init           # once per project
/tw:new-project           # define requirements, get ROADMAP.md
/tw:discuss-phase 1       # capture library/pattern decisions
/tw:plan-phase 1          # → XML plans with token estimates
/tw:execute-phase 1       # → parallel execution + Ralph Loop
/tw:verify-phase 1        # → requirements verification + variance report
/tw:done                  # → 10-section handoff + resume prompt
                          # (next session)
/tw:resume                # restore context instantly
/tw:clear                 # close phase 1, advance to phase 2
/tw:discuss-phase 2       # repeat
```
