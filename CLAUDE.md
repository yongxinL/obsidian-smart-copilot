# Smart Copilot — Project Guide

## Core Value

Users can query their personal knowledge vault through AI agents (Claude Desktop, Claude Code, Hermes) with hybrid retrieval and get grounded, cite-backed responses.

## Quick Reference

| Artifact | Location |
|----------|----------|
| PROJECT.md | `.planning/PROJECT.md` |
| Requirements | `.planning/REQUIREMENTS.md` |
| Roadmap | `.planning/ROADMAP.md` |
| PRD | `.planning/product_requirements_v26.05.md` |
| State | `.planning/STATE.md` |

## Phases

1. **Foundation** — Docker, auth, schema, file watcher, MCP, REST+WS
2. **RAG + Agent** — Hybrid retrieval, auto-links, 22-tool agent
3. **Skills + Ingestion** — Skills runtime, default ingest skills, enrichment
4. **Memory Dream** — Nightly consolidation, brain maintenance
5. **Web + Workspaces** — Web search, projects, vault intelligence
6. **Admin + Observability** — Admin REST, Prometheus, audit
7. **Platform** — MCP registry, DAG jobs, backups
8. **Electron Client** — Desktop UI (deferred)

## Workflow

- **Mode:** interactive (confirm at each step)
- **Granularity:** standard
- **Parallelization:** enabled

## Commands

| Command | Purpose |
|---------|---------|
| `/gsd-plan-phase 1` | Plan Phase 1 (Foundation) |
| `/gsd-discuss-phase 1` | Discuss Phase 1 approach |
| `/gsd-progress` | Check current progress |
| `/gsd-stats` | Display project statistics |

## Key Decisions

- **MCP-first:** Agents are primary clients, no UI dependency for any feature
- **PostgreSQL-only:** No Redis/Celery/external broker
- **Zero-LLM links:** Deterministic auto-link extraction, no cost
- **Single Docker:** Easy deployment, homelab-friendly

## Notes

- PRD v26.05.1 is comprehensive (270KB) — use it as primary reference
- All requirements mapped to phases (68 total, 0 unmapped)
- Phase 8 (Electron UI) deferred; CLI/MCP/REST available from Phase 1

---
*Last updated: 2026-05-09 after initialization*