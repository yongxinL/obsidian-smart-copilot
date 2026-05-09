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

1. **Phase 1a: Container + Data Layer** — Docker/supervisord, PostgreSQL 16 + pgvector, monorepo scaffold
2. **Phase 1b: Auth + Security Primitives** — Argon2 password hashing, JWT sessions, MCP bearer tokens, RLS enforcement
3. **Phase 1c: Vault + Watchdog Indexer** — Page CRUD, compiled-truth/timeline convention, filesystem watchdog
4. **Phase 1d: MCP Server + REST API + CLI** — Stdio and HTTP MCP transports, smartcopilot CLI
5. **Phase 2a: LLM Gateway + Hybrid RAG** — LiteLLM router, pgvector HNSW, BM25, RRF fusion
6. **Phase 2b: Knowledge Graph + Agent Runner** — Zero-LLM wikilink extraction, 22-tool ReAct agent
7. **Phase 3: Skills + Ingestion + Enrichment** — Skills runtime, default ingest skills, tiered enrichment
8. **Phase 4: Memory Dream** — Nightly consolidation, orphan/dead-link audit
9. **Phase 5: Web + Workspaces + Intel** — Web search, projects, vault intelligence
10. **Phase 6: Admin + Observability** — Prometheus, audit logs, admin REST
11. **Phase 7: Platform** — MCP registry, DAG jobs, backups
12. **Phase 8: Electron Client** — Desktop UI (deferred)

## Workflow

- **Mode:** interactive (confirm at each step)
- **Granularity:** standard
- **Parallelization:** enabled

## Commands

| Command | Purpose |
|---------|---------|
| `/gsd-discuss-phase 1a` | Discuss Phase 1a approach |
| `/gsd-plan-phase 1a` | Plan Phase 1a |
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
*Last updated: 2026-05-09 — reset to Phase 1a (Foundation)*