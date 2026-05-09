# Smart Copilot

## What This Is

Smart Copilot is a self-hosted AI knowledge brain for small homelab teams (3–10 users) that combines a typed knowledge graph, hybrid RAG retrieval, an autonomous agent surface, and a skills-based workflow system over a plain-markdown vault. All functionality is exposed through a Model Context Protocol (MCP) server (stdio + Streamable HTTP) and a parallel REST + WebSocket API, with the Electron desktop client deferred to the final phase. The system runs as a single Docker container bundling Python 3.12/FastAPI and PostgreSQL 16 + pgvector under supervisord.

## Core Value

The agent can instantly query, write, and reason over the user's entire knowledge base — structured as a typed graph of people, companies, concepts, and ideas — through any MCP-capable client (Claude Code, Claude Desktop, Cursor, Hermes), with zero setup beyond `docker run`.

## Requirements

### Validated

- [ ] No phases validated yet (reset to Phase 1a on 2026-05-09)

### Active

- [ ] Single Docker container deployment with supervisord (PID 1), bundled PostgreSQL 16 + pgvector, FastAPI, APScheduler, and watchdog
- [ ] MCP server in both stdio and HTTP (Streamable HTTP, port 8787) modes from Phase 1
- [ ] REST + WebSocket API with 1:1 parity with MCP tool surface
- [ ] Multi-tenant page storage with PostgreSQL RLS per-user isolation
- [ ] Compiled-truth + timeline page convention (above-the-line rewritable, below-the-line append-only)
- [ ] Zero-LLM typed wikilink extraction on every page write
- [ ] Hybrid RAG pipeline: pgvector HNSW + BM25 tsvector + typed graph, fused via Reciprocal Rank Fusion
- [ ] 22-tool in-process agent surface with brain-first system prompt
- [ ] Skills system with RESOLVER.md dispatcher and system + per-user namespaces
- [ ] Default skill pack: idea-ingest, media-ingest, meeting-ingestion + 26 additional skills
- [ ] Tiered entity enrichment (T1/T2/T3) for people, companies, concepts
- [ ] Nightly Memory Dream consolidation cycle + continuous brain maintenance loop
- [ ] CLI admin tools (`smartcopilot` binary) and admin REST endpoints
- [ ] Fernet-encrypted API keys at rest, argon2-cffi password hashing
- [ ] Web search skill (DuckDuckGo + Jina + Wikipedia) with cross-vault reference detection
- [ ] Projects/workspaces (folder/tag-scoped contexts with optional system prompt)
- [ ] Vault intelligence endpoints (orphans, hubs, link suggestions, graph)
- [ ] Prometheus metrics, structured JSON logs, audit log query
- [ ] MCP server registry (admin-configurable external MCP servers)
- [ ] Durable-job parent-child DAGs with APScheduler + SQLAlchemyJobStore
- [ ] Automated backup + verified restore procedure
- [ ] Electron desktop client: chat-first UI, Tiptap split-pane editor, system tray + Quick Chat, Obsidian export

### Out of Scope

- LightRAG, GraphRAG, or any LLM-based link extractor — deterministic wikilink extraction only
- Redis, Celery, RabbitMQ, or any external broker — PostgreSQL does the heavy lifting
- LiteLLM as a separate proxy — imported as Python library only
- SQLite, DuckDB, PGLite as primary store
- Real-time multi-user collaborative editing
- Mobile clients
- VS Code companion extension
- Custom RBAC roles beyond `admin` and `user`
- Marketing copy, business model, pricing

## Context

- **Reference PRD:** `docs/product_requirements_document_v26.05.md` — complete, self-contained spec (v26.05.1 draft)
- **Build order:** Backend + MCP first (Phases 1–7), UI last (Phase 8) — deliberate inversion of typical order
- **Target environment:** Self-hosted homelab, 3–10 users, Docker on Linux
- **MCP-first principle:** All capabilities exposed via MCP from Phase 1; no UI dependency for any feature through Phase 7
- **Phase 1 acceptance test:** New user created via CLI → MCP token issued → Claude Code connects via stdio → `brain_put` / `brain_get` / `brain_search` succeed against seeded vault
- **Existing codebase:** None (greenfield); PRD is the authoritative spec

## Constraints

- **Tech stack:** Python 3.12 + FastAPI + PostgreSQL 16 + pgvector (no alternatives; mandated by PRD)
- **Monorepo:** pnpm workspaces; Python under `server/app/`; Electron client under `clients/desktop/`
- **LiteLLM:** Library import only — never proxied
- **Security:** Fernet-encrypted keys, argon2-cffi hashing, RLS via session GUC, trust boundary on `remote=true` callers
- **Embedding:** OpenAI `text-embedding-3-small` at 1536 dimensions for Phase 1 (later phases may migrate)
- **Services transport-agnostic:** MCP and REST both call the same `services/` layer; no FastAPI types in services
- **RLS discipline:** `SET app.current_user_id` (not `SET LOCAL`); always `RESET` in `finally:`

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| MCP-first (no UI for Phases 1–7) | External agent clients (Claude Code, Cursor, Hermes) are primary surface; Electron UI is Phase 8 only | — Pending |
| Single-container + supervisord | Simplifies homelab self-hosting; no orchestrator required | — Pending |
| PostgreSQL for everything (vector + BM25 + graph + jobs) | Eliminates Redis/Celery/graph-engine dependencies; single data store | — Pending |
| LiteLLM as library import | Avoids separate proxy deployment; 100+ providers in-process | — Pending |
| Zero-LLM auto-link extraction | Deterministic, fast, no API cost on every page write | — Pending |
| pnpm workspaces monorepo | Python backend + Electron client in one repo, unified tooling | — Pending |
| Compiled-truth + timeline page convention | Separates current understanding (rewritable) from event history (append-only) | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-09 — reset to Phase 1a (no phases validated)*
