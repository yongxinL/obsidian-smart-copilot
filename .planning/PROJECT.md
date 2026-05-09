# Smart Copilot

## What This Is

Smart Copilot is a self-hosted AI knowledge brain for small homelab teams (3–10 users) that combines a typed knowledge graph, hybrid RAG retrieval, an autonomous agent, and a skills-based workflow system over a plain-markdown vault. MCP-first: all functionality exposed via MCP server (stdio + HTTP) and REST + WebSocket API, with Electron desktop client deferred to Phase 8.

## Core Value

Users can query their personal knowledge vault through AI agents (Claude Desktop, Claude Code, Hermes) with hybrid retrieval (vector + BM25 + typed graph) and get grounded, cite-backed responses — without relying on external services.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Multi-tenant knowledge brain with PostgreSQL RLS
- [ ] MCP server (stdio + HTTP) from day one
- [ ] REST + WebSocket API from day one
- [ ] CLI admin tools + admin REST endpoints
- [ ] Hybrid RAG with RRF fusion
- [ ] Zero-LLM auto-link extraction
- [ ] Memory Dream + brain maintenance
- [ ] Skills system with RESOLVER.md dispatcher
- [ ] Single Docker container + supervisord
- [ ] Fernet-encrypted API keys

### Out of Scope

- LightRAG / GraphRAG / LLM-based link extraction — zero-LLM approach only
- Redis/Celery/RabbitMQ or external brokers — PostgreSQL does everything
- LiteLLM as separate proxy — in-process library only
- SQLite/DuckDB/PGLite as primary store — PostgreSQL only
- Real-time multi-user collaborative editing
- Mobile clients
- VS Code companion extension
- Custom RBAC beyond admin/user

## Context

**Product:** Smart Copilot v26.05.1 PRD exists with detailed specifications covering 8 phases, ~50+ REQ blocks, architecture diagrams, file structure, and AI agent implementation guidance.

**Tech Stack:**
- Single Docker container (supervisord, nodaemon=true)
- Python 3.12 + FastAPI + asyncpg
- PostgreSQL 16 + pgvector
- LiteLLM as library (not proxy)
- Argon2-cffi for password hashing
- Fernet for API key encryption
- APScheduler with SQLAlchemyJobStore
- pnpm workspaces monorepo
- Electron desktop client (Phase 8)

**Source of Truth:** `.planning/product_requirements_v26.05.md` — comprehensive 270KB PRD covering all phases, REQs, architecture, data models, API contracts, and AI agent guidance.

## Constraints

- **Runtime**: Single Docker container with supervisord PID 1
- **Database**: PostgreSQL 16 + pgvector only; no Redis/Celery/external broker
- **MCP**: First-class from Phase 1; no UI dependency for any feature
- **LLM**: LiteLLM as in-process library only
- **Link Extraction**: Zero-LLM, deterministic, on every page write
- **Trust Boundary**: `remote=true` callers blocked from dangerous ops
- **Electron UI**: Deferred to Phase 8; CLI/MCP/REST available from Phase 1

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| MCP-first architecture | Agents (Claude Code/Desktop) are primary clients | — Pending |
| PostgreSQL-only stack | Simplicity, RLS, pgvector, no Redis/Celery | — Pending |
| Zero-LLM link extraction | Deterministic, no cost, no latency | — Pending |
| Single Docker container | Easy deployment, homelab-friendly | — Pending |
| Plain markdown vault | User-owned, portable, no lock-in | — Pending |

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
*Last updated: 2026-05-09 after initialization*