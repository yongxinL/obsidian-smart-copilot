# Smart Copilot — Product Requirements Document

**Version:** v26.05
**Status:** DRAFT (v26.05.1)
**Document type:** Authoritative product specification
**Audience:** Implementing AI coding agent (no other reference materials required)

---
**AI Agent Annotations:**
- Requirement type tags: `[IMPL]` = generate code, `[CFG]` = configuration, `[TEST]` = write test, `[DOC]` = document only
- File mappings: See Section 30J.1 / 30J.2 for authoritative file paths per module
- Decision log: See Appendix D
- Test skeleton: See Appendix E
- Common pitfalls: See Section 30P

---

## Table of Contents

1. [Document Metadata](#1-document-metadata)
1A. [Executive Summary & Product Vision](#1a-executive-summary--product-vision)
2. [Product Overview](#2-product-overview)
3. [Goals and Non-Goals](#3-goals-and-non-goals)
4. [User Personas and Use Cases](#4-user-personas-and-use-cases)
5. [System Architecture (stated as requirements)](#5-system-architecture-stated-as-requirements)
5A. [Architecture & System Design](#5a-architecture--system-design)
6. [Phase Plan](#6-phase-plan)
6A. [Epics, Features & Prioritisation](#6a-epics-features--prioritisation)
7. [Data Model](#7-data-model)
8. [Authentication and Authorization](#8-authentication-and-authorization)
9. [MCP Server (first-class)](#9-mcp-server-first-class)
10. [REST API + WebSocket](#10-rest-api--websocket)
11. [CLI Admin Tools (gbrain-style)](#11-cli-admin-tools-gbrain-style)
12. [Admin REST Endpoints (parallel to CLI)](#12-admin-rest-endpoints-parallel-to-cli)
13. [Vault Management](#13-vault-management)
14. [Page Schema and Conventions](#14-page-schema-and-conventions)
15. [Auto-Link Extraction and Typed Knowledge Graph](#15-auto-link-extraction-and-typed-knowledge-graph)
16. [Hybrid RAG Pipeline](#16-hybrid-rag-pipeline)
17. [Agent Surface (22 tools)](#17-agent-surface-22-tools)
18. [Skills System](#18-skills-system)
18A. [Client Integration Kit (Claude Desktop, Hermes Agent, Generic MCP)](#18a-client-integration-kit-claude-desktop-hermes-agent-generic-mcp)
19. [Ingestion Skills](#19-ingestion-skills)
20. [Entity Enrichment](#20-entity-enrichment)
21. [Data-Research Recipes](#21-data-research-recipes)
22. [Memory Dream and Brain Maintenance](#22-memory-dream-and-brain-maintenance)
23. [Durable Job System](#23-durable-job-system)
24. [LLM Provider Integration](#24-llm-provider-integration)
25. [Embedding System](#25-embedding-system)
26. [Health Checks and Observability](#26-health-checks-and-observability)
27. [Security and Trust Boundary](#27-security-and-trust-boundary)
28. [Testing Requirements](#28-testing-requirements)
29. [Deployment](#29-deployment)
30. [UI — Phase 8 (Electron Desktop Client)](#30-ui--phase-8-electron-desktop-client)
30A. [API Contract Reference](#30a-api-contract-reference)
30B. [Streaming Protocol (WebSocket primary; SSE for chat completions)](#30b-streaming-protocol-websocket-primary-sse-for-chat-completions)
30C. [Agent System — 22 Tools (detailed)](#30c-agent-system--22-tools-detailed)
30D. [Memory Dream Consolidation System](#30d-memory-dream-consolidation-system)
30E. [Zettelkasten Workflows](#30e-zettelkasten-workflows)
30F. [HTML Sanitisation Strategy](#30f-html-sanitisation-strategy)
30G. [Indexing Strategy](#30g-indexing-strategy)
30H. [Server Configuration Reference](#30h-server-configuration-reference)
30I. [Docker Deployment](#30i-docker-deployment)
30J. [File Structure Reference](#30j-file-structure-reference)
30K. [Non-Functional Requirements & Success Metrics](#30k-non-functional-requirements--success-metrics)
30L. [Quality Gates by Phase](#30l-quality-gates-by-phase)
30M. [Assumptions, Constraints & Dependencies](#30m-assumptions-constraints--dependencies)
30N. [Risks & Mitigations](#30n-risks--mitigations)
30O. [Reference Codebases & Resources](#30o-reference-codebases--resources)
[30P. AI Agent Implementation Guidance](#30p-ai-agent-implementation-guidance)
31. [Glossary](#31-glossary)
- [Appendix A — Default Skill List](#appendix-a--default-skill-list-one-line-definitions)
- [Appendix B — Default Tool Surface](#appendix-b--default-tool-surface-22-agent-tools--30-mcp-tools)
- [Appendix C — Default RLS Policies](#appendix-c--default-rls-policies-pseudocode)
- [Appendix D — Decision Log](#appendix-d--decision-log)
- [Appendix E — Test Skeleton](#appendix-e--test-skeleton)
- [Appendix F — Common Pitfalls](#appendix-f--common-pitfalls)
- [Appendix G — Backup & Restore Runbook (Operational)](#appendix-g--backup--restore-runbook-operational)

---

## 1. Document Metadata

### 1.1 Identity
- **Product name:** Smart Copilot
- **Document version:** v26.05.1 (draft 0.5.1)
- **Status:** DRAFT — implementation specification
- **Scope:** Complete, self-contained product requirements for the Smart Copilot system. This document is the spec; no external references, blueprints, or decision logs are required to implement it.

### 1.2 Conventions
- **REQ-XXX** identifies a numbered, testable requirement.
- **MUST / MUST NOT / SHOULD / MAY** follow RFC 2119 semantics.
- "Phase 1" refers to the first delivery phase per Section 6.
- All file paths use POSIX form. All times are UTC unless otherwise noted.
- Stored timestamps are UTC; scheduled jobs execute using the container timezone, which MUST be explicitly configured by the operator.

### 1.3 Out of scope for this document
- Marketing copy, business model, pricing.
- Hardware procurement.
- Final visual design of the Electron UI (the UI is deferred to Phase 8 — see Section 30 and Section 6.6).

---

## 1A. Executive Summary & Product Vision

Smart Copilot is a **self-hosted AI knowledge brain** for small homelab teams (3–10 users) that combines a typed knowledge graph, hybrid RAG retrieval, an autonomous agent, and a skills-based workflow system over a plain-markdown vault. The system is **MCP-first**: all functionality is exposed through a Model Context Protocol server (stdio + HTTP) and a parallel REST + WebSocket API, with the Electron desktop client deferred to the final phase.

The backend runs as a single Docker container managed by `supervisord` (nodaemon=true), bundling Python 3.12 / FastAPI and PostgreSQL 16 + pgvector. It watches markdown vault directories, parses pages on the **compiled-truth + timeline** convention (a horizontal-rule separator splits each page into an above-the-line rewritable summary and a below-the-line append-only event log), extracts typed wikilinks deterministically with zero LLM calls, and indexes content into pgvector HNSW + tsvector BM25 + a typed-link graph.

A 22-tool agent surface plus a 30+ tool MCP surface drive read/write operations, ingestion, enrichment, and maintenance. A nightly **Memory Dream** consolidation cycle and a continuous brain-maintenance loop keep citations fixed, dead links audited, orphans surfaced, and stale pages flagged. A **skills system** (RESOLVER.md dispatcher, system + per-user namespaces) encodes workflows as fat markdown files the agent reads and executes.

Three external agent clients are formally supported from day one: Claude Desktop, Hermes Agent, and any generic MCP-compliant agent. The Electron desktop client (Phase 8) consumes the same documented REST + WebSocket API and provides a chat-first UI with a split-pane Tiptap editor, system tray Quick Chat, and a global hotkey.

### 1A.1 Core principles (non-negotiable)

| ID  | Principle                             | Implication                                                                             |
| --- | ------------------------------------- | --------------------------------------------------------------------------------------- |
| P1  | **MCP-first**                         | All capabilities exposed via MCP from Phase 1; no UI dependency for any feature         |
| P2  | **Single-container deploy**           | One Docker container, supervisord, bundled Postgres + pgvector                          |
| P3  | **PostgreSQL does the heavy lifting** | Vector + BM25 + recursive-CTE graph in one database; no Redis/Celery/external broker    |
| P4  | **LiteLLM as library**                | In-process Python import; never deployed as a separate proxy                            |
| P5  | **Zero-LLM auto-link extraction**     | Typed wikilinks extracted deterministically on every page write                         |
| P6  | **Brain-first**                       | The agent MUST query the local brain (`search`/`get_page`) before any external API call |
| P7  | **Hybrid namespace from day one**     | Per-user private vaults + shared vault; never retrofit sharing later                    |
| P8  | **Trust boundary**                    | `remote=true` callers blocked from dangerous ops; admin operations always local         |
| P9  | **Memory hygiene via Dream cycles**   | Long-term memory is consolidated nightly, not left to rot                               |
| P10 | **Spec-first, agent-second**          | This PRD is fully self-contained; agents do not need to read blueprints or design docs  |

### 1A.2 Explicit out-of-scope for v1.0

- LightRAG, GraphRAG batch extraction, or any LLM-based link extractor.
- Redis, Celery, RabbitMQ, or any external broker.
- LiteLLM as a separate proxy service (it is imported as a library only).
- SQLite, DuckDB, PGLite, or other embedded stores as the primary store.
- Real-time multi-user collaborative editing.
- Mobile clients.
- VS Code companion extension.
- Custom RBAC roles beyond `admin` and `user`.

---

## 2. Product Overview

Smart Copilot is a self-hosted, multi-user (3–10 user homelab) AI knowledge brain. It ingests user content (markdown vaults, meeting transcripts, articles, links, media, voice notes), maintains a typed knowledge graph of people, companies, concepts and ideas, and exposes its capabilities through two transport-agnostic surfaces: an MCP (Model Context Protocol) server for agent clients (Claude Code, Cursor, Claude Desktop, Hermes, Cowork) and a REST + WebSocket API for the eventual Electron desktop client.

Smart Copilot stores knowledge as plain markdown files using the **compiled-truth + timeline** convention: a horizontal-rule separator splits each page into an above-the-line "current understanding" (rewritable) and a below-the-line "append-only timeline" (event log). Indexing layers — pgvector HNSW, BM25 tsvector, and a typed wikilink graph — feed a hybrid RAG pipeline using Reciprocal Rank Fusion. A nightly Memory Dream cycle plus continuous brain maintenance keeps citations fixed, dead links audited, orphans surfaced, and stale pages flagged. A skills system (RESOLVER.md dispatcher, system + user namespaces) encodes workflows as fat markdown files that the agent reads and executes.

---

## 3. Goals and Non-Goals

### 3.1 Goals
- **REQ-001** [IMPL] Provide a multi-tenant knowledge brain with strict per-user isolation enforced by PostgreSQL Row-Level Security.
- **REQ-002** [IMPL] Expose all functionality through two coexisting transports from day one: MCP (stdio + HTTP) and REST/WebSocket.
- **REQ-003** [IMPL] Allow administrators to operate the system fully without a UI, via both CLI commands inside the container and curl-able admin REST endpoints.
- **REQ-004** [IMPL] Deliver hybrid retrieval (vector + BM25 + typed graph) with Reciprocal Rank Fusion, multi-query expansion, and intent classification.
- **REQ-005** [IMPL] Auto-extract typed links on every page write with zero LLM calls, populating a typed knowledge graph (people, companies, concepts).
- **REQ-006** [IMPL] Run a nightly Memory Dream consolidation and a continuous brain-maintenance cycle (stale pages, orphans, dead links, citations, back-links, tag consistency).
- **REQ-007** [IMPL] Support skills as the first-class workflow primitive with a RESOLVER.md dispatcher, system namespace, and per-user user namespace.
- **REQ-008** [IMPL] Run as a single Docker container managed by `supervisord` (nodaemon=true), bundling Python 3.12 FastAPI and PostgreSQL 16 with pgvector.
- **REQ-009** [IMPL] Encrypt all third-party API keys at rest using Fernet.
- **REQ-010** [TEST] Deliver `pytest + pytest-asyncio` test suite executing against a real PostgreSQL test database, including RLS isolation tests.

### 3.2 Non-Goals
- **REQ-011** [DOC] Smart Copilot MUST NOT depend on Redis, Celery, RabbitMQ, or any external broker.
- **REQ-012** [DOC] Smart Copilot MUST NOT include LightRAG, GraphRAG batch extraction, or any LLM-based link extractor.
- **REQ-013** [DOC] LiteLLM MUST be imported as a Python library and MUST NOT be deployed as a separate proxy service.
- **REQ-014** [DOC] SQLite, DuckDB, PGLite, and other embedded stores MUST NOT be used as the primary store.
- **REQ-015** [DOC] The Electron desktop client is explicitly deferred to the final phase; no UI work is required to declare Phases 1–7 complete.

---

## 4. User Personas and Use Cases

### 4.1 Operational personas (internal trust model)
- **P1 — Owner/Admin (George):** lead architect, full root inside the container, configures vaults, users, providers, and skills.
- **P2 — Homelab User:** member of the household or trusted group; has a private vault, MCP tokens, and access to the shared vault.
- **P3 — Agent Client:** any MCP-capable agent (Claude Code, Cursor, Hermes, Cowork) acting on behalf of a user via a per-user MCP bearer token.
- **P4 — Background Job:** durable APScheduler job (cron, ingestion, maintenance) operating with a system-level OperationContext.

### 4.2 Product personas (target end-users)

#### 4.2.1 Primary — Knowledge Worker (Alice)
- **Role:** Zettelkasten practitioner, researcher, writer.
- **Vault scale:** 500–5,000 notes.
- **Workflow:** reads papers → ingests as literature notes → splits into atomic Zettel → asks questions across vault → writes grounded in retrieved knowledge.
- **Technical comfort:** Obsidian user, basic CLI, not a developer.
- **Primary surface:** Phase 1–7: MCP via Claude Desktop / Hermes. Phase 8: Electron desktop client.

#### 4.2.2 Secondary — Homelab Admin (Bob)
- **Role:** Technical lead of a small team or family.
- **Responsibilities:** Deploy, manage encryption keys, configure providers, monitor cost.
- **Workflow:** `docker run` → configure API keys → create users → monitor admin endpoints / dashboard.
- **Technical comfort:** Docker, Linux, self-hosting.
- **Primary surface:** CLI inside the container + admin REST endpoints. UI optional.

#### 4.2.3 Tertiary — Team Member (Carol)
- **Role:** Non-admin user on a shared instance.
- **Vault scale:** 100–1,000 notes.
- **Workflow:** Open client (MCP-compatible agent or, post-Phase 8, the Electron app) → log in → chat with vault → save insights.
- **Technical comfort:** Desktop app user, not technical.

### 4.3 Representative use cases
- **U1** Admin creates a user, generates an MCP bearer token, points Claude Code at the stdio MCP server, and immediately queries the brain.
- **U2** Agent ingests a meeting transcript via the `meeting-ingestion` skill; people and companies referenced are auto-enriched; typed links are extracted on write; the page becomes searchable within the next index tick.
- **U3** User edits a markdown file directly in their vault on disk; the watchdog detects the change, the indexer re-chunks/re-embeds, and the next query reflects the edit.
- **U4** Nightly Memory Dream runs: stale pages flagged, dead wikilinks audited, citations re-checked, orphans listed in a maintenance report.
- **U5** Admin curls `POST /admin/users` to create a new user from a script with no UI present.
- **U6** Remote agent (Claude Desktop) connects to MCP HTTP mode over an authenticated bearer token and operates under `remote=true` trust boundary, blocking dangerous operations.
- **U7** (Phase 8) Carol opens the Electron client, browses her vault sidebar, chats with the brain, accepts a `put_page` confirmation modal, and watches the Tiptap editor open the new note.

---

## 5. System Architecture (stated as requirements)

### 5.1 Runtime
- **REQ-100** The system MUST run as a single Docker container.
- **REQ-101** The container MUST use `supervisord` with `nodaemon=true` as PID 1 to manage at minimum: `postgres`, `fastapi` (uvicorn), `mcp-http`, `apscheduler`, `watchdog`.
- **REQ-102** The backend MUST be Python 3.12, FastAPI, async-first, using `asyncpg` for runtime and `psycopg2` for Alembic migrations only.
- **REQ-103** PostgreSQL 16 with the `pgvector` extension MUST be the sole primary datastore.
- **REQ-104** Embeddings MUST be stored in `pgvector` HNSW indexes at 1536 dimensions for Phase 1 (`openai/text-embedding-3-small`). Phase 1 default is 1536; later phases MAY change dimensions via embedding migration (REQ-2105).
- **REQ-105** BM25 keyword search MUST be implemented with PostgreSQL `tsvector` + `websearch_to_tsquery`.
- **REQ-106** The wikilink graph MUST be queried via recursive CTEs (no external graph engine).
- **REQ-107** Hybrid retrieval MUST combine vector + BM25 + graph results using Reciprocal Rank Fusion (RRF) with `score = sum(1/(60 + rank))`.
- **REQ-108** LiteLLM MUST be used as an in-process Python library import.
- **REQ-109** Password hashing MUST use `argon2-cffi`.
- **REQ-110** API keys for third-party providers MUST be Fernet-encrypted in PostgreSQL; the encrypted column MUST NEVER appear in any Pydantic response schema.
- **REQ-111** Multi-tenancy MUST be enforced by PostgreSQL Row-Level Security policies driven by a session GUC set per request.
- **REQ-112** Durable jobs MUST use APScheduler with `SQLAlchemyJobStore` persisting to the same PostgreSQL instance.

### 5.2 Repository layout
- **REQ-120** The repo MUST be a `pnpm` workspaces monorepo.
- **REQ-121** Python packages MUST be located under `server/app/` using src-style layout with plain domain-named files (e.g., `server/app/services/page_service.py`, `server/app/routes/pages.py`, `server/app/mcp/server.py`).
- **REQ-122** Node 20 LTS and Python 3.12 MUST be pinned via `.nvmrc` and `pyproject.toml`/`.python-version`.
- **REQ-123** Ruff MUST be the sole Python linter/formatter.
- **REQ-124** The Electron client (Phase 8) MUST live under `clients/desktop/` and MUST NOT import any Python.

### 5.3 Service layer
- **REQ-130** Routes MUST be thin: validate input, call a service, return a response model.
- **REQ-131** Services MUST be transport-agnostic and MUST NOT import FastAPI types.
- **REQ-132** Both the MCP server and the REST/WebSocket API MUST call the same service layer.
- **REQ-133** Dependency injection MUST use FastAPI `Depends()`; no third-party DI container is permitted.

---

## 5A. Architecture & System Design

> Companion to Section 5. Section 5 defines the runtime as a set of requirements; this section provides the architecture diagram, technology stack inventory, OpenAPI sync convention, and cross-cutting design notes.

### 5A.1 System architecture diagram

```
┌──────────────────────────────────────────────────────────────────┐
│  External MCP-capable agents (always supported, Phase 1+)        │
│  Claude Code · Claude Desktop · Cursor · Hermes · Cowork         │
│  Generic MCP clients · Custom agents                             │
└──────────────────────────────────┬───────────────────────────────┘
                                   │ MCP (stdio + Streamable HTTP)
                                   │ + REST + WebSocket
                                   │
┌──────────────────────────────────▼───────────────────────────────┐
│  Electron Desktop Client (Phase 8 — DEFERRED)                    │
│  React + Tiptap + Radix UI + Lexical · Tray + Quick Chat         │
│  DOMPurify (clipboard) · Generated TS client from OpenAPI         │
└──────────────────────────────────┬───────────────────────────────┘
                                   │ REST + WebSocket
                                   │
┌──────────────────────────────────▼───────────────────────────────┐
│  Single Docker Container — supervisord (nodaemon=true)           │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Process: fastapi (uvicorn)                                │  │
│  │   ├── REST API (~103 endpoints, OpenAPI generated)        │  │
│  │   ├── WebSocket gateway (real-time updates)               │  │
│  │   └── SSE stream (chat completions only)                  │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │  Process: mcp-http (Streamable HTTP transport, port 8787) │  │
│  │  Process: mcp-stdio (per-invocation, on-demand)           │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │  Process: apscheduler (durable jobs, SQLAlchemyJobStore)  │  │
│  │   ├── Memory Dream (nightly)                              │  │
│  │   ├── Brain maintenance (stale, orphans, links, citations)│  │
│  │   ├── Reconciliation (filesystem ↔ DB drift)              │  │
│  │   └── User-scheduled tasks                                │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │  Process: watchdog (file-system observer)                 │  │
│  │   └── thread → asyncio handoff via call_soon_threadsafe() │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │  In-process subsystems (shared service layer):            │  │
│  │   ├── Hybrid RAG engine (RRF + multi-query expansion)     │  │
│  │   ├── Auto-link extractor (zero-LLM, deterministic)       │  │
│  │   ├── Skills runtime (RESOLVER.md dispatcher)             │  │
│  │   ├── Agent runner (22 built-in tools + 30+ MCP tools)    │  │
│  │   ├── LiteLLM router (cheap/balanced/strong tiers)        │  │
│  │   ├── Embedder (batched, version-tracked)                 │  │
│  │   ├── nh3 HTML sanitizer · Web search (DDG/Jina/Wiki)     │  │
│  │   └── Fernet encryption · argon2-cffi password hashing    │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │  Process: postgres (16 + pgvector)                        │  │
│  │   ├── HNSW vector index · GIN tsvector · recursive CTEs   │  │
│  │   ├── Row-Level Security (per-user GUC)                   │  │
│  │   ├── APScheduler job store · audit log · llm_usage       │  │
│  │   └── Encrypted provider keys                             │  │
│  └────────────────────────────────────────────────────────────┘  │
│  Volumes: /data (Postgres) · /vaults (markdown) · /config        │
└──────────────────────────────────────────────────────────────────┘
External providers: OpenAI · Anthropic · Gemini · DeepSeek
                    OpenRouter · Ollama (local) · custom endpoints
```

### 5A.2 Technology stack — backend

| Layer                  | Technology                          | Notes                                             |
| ---------------------- | ----------------------------------- | ------------------------------------------------- |
| Language               | Python 3.12                         | pinned via `.python-version` and `pyproject.toml` |
| API                    | FastAPI                             | async, native SSE, OpenAPI generation             |
| Database               | PostgreSQL 16 + pgvector            | bundled inside the container under supervisord    |
| DB driver (runtime)    | asyncpg                             | async only                                        |
| DB driver (migrations) | psycopg2                            | sync; Alembic `env.py` only                       |
| ORM                    | SQLAlchemy 2.0 + Alembic            | async ORM + sync migrations                       |
| LLM                    | LiteLLM (library import)            | 100+ providers in-process; never proxied          |
| Background jobs        | APScheduler + SQLAlchemyJobStore    | persistent across restarts; PostgreSQL-backed     |
| File watching          | watchdog                            | inotify (Linux); falls back to polling            |
| Markdown               | markdown-it-py + python-frontmatter |                                                   |
| HTML sanitisation      | nh3                                 | Rust-based defense-in-depth                       |
| PDF extraction         | PyMuPDF (fitz)                      | lazy-loaded on demand                             |
| DOCX extraction        | python-docx                         |                                                   |
| HTML cleanup           | readability-lxml                    | downstream of nh3                                 |
| HTTP client            | httpx                               | async                                             |
| MCP SDK                | `mcp >= 1.25, < 2`                  | stdio + Streamable HTTP transports                |
| Auth                   | python-jose (JWT) + argon2-cffi     | sessions and password hashing                     |
| Encryption             | cryptography (Fernet)               | API keys at rest                                  |
| Hashing                | xxhash                              | non-cryptographic content/enrichment hashes       |
| Validation             | Pydantic v2                         | request/response models                           |
| Process manager        | supervisord                         | nodaemon=true; PID 1                              |
| Codegen                | openapi-typescript                  | TS client from OpenAPI spec                       |

### 5A.3 Technology stack — frontend (Phase 8)

| Layer           | Technology                         | Notes                                                                                                                                                                              |
| --------------- | ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Platform        | Electron (latest stable)           | macOS + Windows; Linux dev only                                                                                                                                                    |
| Language        | TypeScript 5.x                     |                                                                                                                                                                                    |
| Build           | Vite (renderer) + esbuild (main)   | Electron Forge                                                                                                                                                                     |
| Package manager | pnpm                               | workspaces monorepo                                                                                                                                                                |
| UI framework    | React 18                           |                                                                                                                                                                                    |
| Chat input      | Lexical                            | @mentions support                                                                                                                                                                  |
| Editor          | Tiptap v2 + @tiptap/markdown       | split-pane WYSIWYG markdown                                                                                                                                                        |
| Panels          | react-resizable-panels             |                                                                                                                                                                                    |
| File tree       | react-complex-tree                 | accessible, virtualised                                                                                                                                                            |
| Components      | Radix UI                           | 15 primitives                                                                                                                                                                      |
| Styling         | CSS modules                        | `.sc-` prefix                                                                                                                                                                      |
| Icons           | Lucide React                       | primary (~1,500 icons, covers 99% of use cases)                                                                                                                                    |
| Icons           | Material Symbols Outlined          | supplementary (~3,000 additional glyphs for niche needs like Dream-cycle phase indicators, calendar recurrences, and domain-specific status icons; loaded as Google variable font) |
| Command         | cmdk                               | command palette                                                                                                                                                                    |
| Diff            | diff + react-diff-viewer-continued |                                                                                                                                                                                    |
| Graph           | Cytoscape.js (lazy-loaded)         | wikilink graph                                                                                                                                                                     |
| Sanitisation    | DOMPurify                          | clipboard input only                                                                                                                                                               |
| Auto-update     | electron-updater                   | GitHub Releases                                                                                                                                                                    |
| Local storage   | electron-store                     | client-only settings (vault path, theme, layout)                                                                                                                                   |
| API client      | generated from OpenAPI             | auto-synced                                                                                                                                                                        |
| Animation       | motion/react (Framer Motion v11)   | panel transitions, modals                                                                                                                                                          |

### 5A.4 OpenAPI sync convention

- **REQ-2700** The backend MUST auto-generate `openapi.json` from FastAPI route definitions.
- **REQ-2701** The Phase 8 client MUST consume `docs/openapi.json` via `openapi-typescript` to generate its TypeScript client.
- **REQ-2702** A pre-commit hook MUST regenerate `docs/openapi.json` whenever any route module changes.
- **REQ-2703** CI MUST fail if generated client types do not match the committed `docs/openapi.json`.
- **REQ-2704** `docs/openapi.json` is the canonical interface contract — all external integrations (Phase 8 client, generic MCP clients consuming the REST surface) MUST validate against it.

### 5A.5 Multi-tenancy & namespace model

- **REQ-2705** Every page MUST belong to exactly one namespace: `private` (per-user) or `shared` (visible to all users).
- **REQ-2706** Filesystem layout: `/vaults/private/{username}/` for private vaults, `/vaults/shared/` for the shared vault. (See Section 7.5.)
- **REQ-2707** Publishing a private page to shared MUST be an intentional, audited file move.
- **REQ-2707A** Shared vault rows MUST be readable by all authenticated users.
- **REQ-2707B** Shared vault write access MUST be governed by a single global policy: `shared_vault_write = admin_only | all_users`. Default is `all_users`.
- **REQ-2707C** When `shared_vault_write=admin_only`, only users with role=`admin` MAY write to the shared vault.
- **REQ-2707D** When `shared_vault_write=all_users`, any authenticated user MAY write to the shared vault.
- **REQ-2707E** Publishing private → shared MUST occur via an intentional, audited move operation (REQ-2707) and MUST enforce the shared vault write policy.
- **REQ-2708** Cross-namespace wikilinks use explicit prefix `[[shared/Topic]]`.
- **REQ-2709** Conversations, memories, usage records, and provider keys are ALWAYS private — they MUST NOT have a shared namespace variant.

### 5A.6 Wikilink resolution

- **REQ-2710** Within a namespace, unqualified wikilinks (`[[Topic]]`) MUST resolve via shortest-unique-path matching (Obsidian-compatible).
- **REQ-2711** When ambiguous after path matching, the alphabetically-first path MUST win (deterministic, debuggable behaviour).
- **REQ-2712** Cross-namespace resolution order: user's current namespace → shared namespace.
- **REQ-2713** The explicit prefix `[[shared/Topic]]` MUST bypass resolution order and target the shared namespace directly.

### 5A.7 Trust boundary

- **REQ-2714** Every service entry point MUST construct an `OperationContext` (see Section 9.3) carrying `user_id`, `transport`, `remote` flag, and `request_id`, and pass it to the service layer.
- **REQ-2715** `remote=true` callers MUST NOT execute arbitrary shell, write outside their own private vault, read other users' private vaults, install or modify system skills, rotate keys, create users, or modify RLS-bypassing rows.
- **REQ-2716** Slug and filename validation MUST apply to all `remote=true` write paths.
- **REQ-2717** All admin REST endpoints MUST enforce `role='admin'` AND a fresh authentication factor (password or admin-scoped MCP token presented within the last 60 minutes) for destructive operations.

---

## 6. Phase Plan

The build order is reversed from typical: backend + MCP first, UI last. v26.05.1 splits the original "Phase 5 — UI" into a fully-specified **Phase 8 — Electron Desktop Client** and renames intermediate phases.

### 6.1 Phase 1 — Backend foundation + MCP first
- **REQ-200** [IMPL] Provision the single Docker image, supervisord, PostgreSQL 16 + pgvector, FastAPI skeleton.
- **REQ-201** [IMPL] Implement users, sessions, MCP tokens, encrypted provider keys, RLS, vault layout.
- **REQ-202** [IMPL] Implement page CRUD (create/read/update/delete) with frontmatter parsing, compiled-truth/timeline split, content-hash dedup.
- **REQ-203** [IMPL] Implement watchdog file indexer with thread→asyncio handoff via `loop.call_soon_threadsafe()`.
- **REQ-204** [IMPL] Stand up MCP server in BOTH stdio and HTTP modes with per-user bearer auth, exposing the full tool surface (Section 9). **Note:** The in-product agent runner (ReAct loop, Section 17) is not a Phase 1 deliverable — Phase 1 ships the MCP tool surface and REST/WebSocket endpoints for external agents and the future Phase 2 agent runner.
- **REQ-205** [IMPL] Stand up REST + WebSocket API with the parallel surface.
- **REQ-206** [IMPL] Stand up CLI admin tools and admin REST endpoints (Sections 11 and 12).
- **REQ-207** [TEST] Phase 1 acceptance: a new user is created via CLI, an MCP token is issued, Claude Code connects via stdio and successfully `brain_put` / `brain_get` / `brain_search` against the seeded vault.

### 6.2 Phase 2 — Hybrid RAG + auto-link extraction + agent
- **REQ-210** [IMPL] Implement chunking, embedding via LiteLLM, HNSW index population.
- **REQ-211** [IMPL] Implement BM25 tsvector index and triggers.
- **REQ-212** [IMPL] Implement zero-LLM auto-link extraction on every page write (Section 15).
- **REQ-213** [IMPL] Implement intent classifier, multi-query expansion, RRF fusion, compiled-truth boost, 4-layer dedup.
- **REQ-214** [IMPL] Implement the 22-tool agent surface (Section 17) and brain-first system prompt.
- **REQ-215** [TEST] Phase 2 acceptance: graph queries (`who works at X`, `what did Y invest in`) return correct typed-link traversals; hybrid search beats vector-only on a fixture corpus.

### 6.3 Phase 3 — Skills + ingestion + entity enrichment + data-research
- **REQ-220** [IMPL] Implement the skills system, RESOLVER.md dispatcher, system + user namespaces (Section 18).
- **REQ-221** [IMPL] Ship default ingestion skills: `idea-ingest`, `media-ingest`, `meeting-ingestion`.
- **REQ-222** [IMPL] Implement tiered entity enrichment (Section 20).
- **REQ-223** [IMPL] Implement data-research recipes (Section 21).
- **REQ-224** [TEST] Phase 3 acceptance: a pasted meeting transcript triggers `meeting-ingestion`, creates/updates person and company pages with compiled-truth + timeline, and emits typed links.

### 6.4 Phase 4 — Memory Dream + brain maintenance
- **REQ-230** [IMPL] Implement nightly Memory Dream with the gbrain `maintain` pattern: stale-page detection, orphan detection, dead-link audit, citation audit, back-link enforcement, tag consistency.
- **REQ-231** [IMPL] Emit a maintenance report consumable via MCP and REST.
- **REQ-232** [TEST] Phase 4 acceptance: scheduled job runs, repairable defects auto-fixed, unrepairable ones surfaced in the report.

### 6.5 Phase 5 — Web search, projects/workspaces, intelligence dashboards (server-side)
- **REQ-2720** [IMPL] Implement web-search skill (DuckDuckGo + Jina Reader + Wikipedia, with cross-vault reference detection per Section 30H).
- **REQ-2721** [IMPL] Implement projects/workspaces (folder/tag-scoped contexts) with `include_folders`, `exclude_folders`, `tags`, optional system prompt and default model.
- **REQ-2722** [IMPL] Implement vault intelligence endpoints (orphans, hubs, link suggestions, vault graph) — server-side only; rendering deferred to Phase 8. The `/vault/organize{,/apply,/undo}` endpoints are also Phase 5 but are workflow tools (not strictly "intelligence") — they can be exercised via CLI/MCP before Phase 8 UI is available.
- **REQ-2723** [TEST] Phase 5 acceptance: `@web` queries return ranked results; project-scoped queries restrict RAG to the project; orphan/hub endpoints return correct counts on a fixture vault.

### 6.6 Phase 6 — Admin surfaces + observability
- **REQ-2730** [IMPL] Implement full admin REST + CLI surfaces: user CRUD, shared API keys, embedding migration, dream status/triggers, MCP server registration.
- **REQ-2731** [IMPL] Implement Prometheus `/metrics`, structured JSON logs, audit log query endpoint.
- **REQ-2732** [TEST] Phase 6 acceptance: admin can register a new user, swap embedding models with progress tracking, view real per-user usage and cost via REST, and observe metrics in Prometheus format.

### 6.7 Phase 7 — Platform polish + MCP server registry
- **REQ-2740** [IMPL] Implement MCP server registry (admin-configurable external MCP servers added to the agent's tool surface; Section 17 + Admin endpoints).
- **REQ-2741** [IMPL] Implement durable-job parent-child DAGs (`minion-orchestrator` skill); job cancellation; rate limits.
- **REQ-2742** [IMPL] Implement a deterministic backup automation script and verified restore procedure, as specified in Section 24A (Backup and Restore).
- **REQ-2743** [TEST] Phase 7 acceptance: admin adds a new MCP server, agent discovers and uses its tools with confirmation gates; a scheduled DAG of dependent jobs runs to completion across a container restart.

### 6.8 Phase 8 — Electron desktop client
- **REQ-2750** [IMPL] Build the Electron/TypeScript/React desktop client (`clients/desktop/`) consuming only the documented REST + WebSocket API.
- **REQ-2751** [IMPL] Implement the chat-first UI, split-pane Tiptap editor, vault sidebar, system tray + Quick Chat with global hotkey.
- **REQ-2752** [IMPL] Implement DOMPurify clipboard sanitisation, electron-store local settings, electron-updater auto-update via GitHub Releases.
- **REQ-2753** [IMPL] Implement the SSE streaming chat UX (citations, tool_start/tool_result, tool_confirm modals, client_request handling).
- **REQ-2754** [IMPL] Implement Obsidian export feature (folder dialog → batch write of conversations and notes with frontmatter and wikilinks).
- **REQ-2755** [TEST] Phase 8 acceptance: end-to-end walkthrough — new user logs in via the Electron client, chats with the brain, accepts a `put_page` confirmation, opens the resulting note in the Tiptap editor, exports a conversation to a configured Obsidian vault path.
- **REQ-2756** [DOC] Detailed visual and interaction specs for Phase 8 are tracked separately in `ui-spec.md`; until Phase 8 begins, all user-facing operations MUST be available via CLI, MCP, or admin REST.

### 6.9 Phase Dependency Map

> **FOR AI AGENTS:** These are the critical intra-phase and cross-phase ordering constraints. Skipping ahead causes integration failures.

| Dependency                              | From      | To        | Why                                                                       |
| --------------------------------------- | --------- | --------- | ------------------------------------------------------------------------- |
| `models/` exists before `services/`     | Any phase | Any phase | Service layer calls ORM models                                            |
| `dependencies.py` before all routes     | Phase 1   | Phase 1   | `get_current_user`, `require_admin`, `get_db_session` are used everywhere |
| `mcp/server.py` calls `services/`       | Phase 1   | Phase 1   | MCP and REST share the same service layer (REQ-132, REQ-606)              |
| `vault/` before `rag/`                  | Phase 1   | Phase 2   | RAG indexes vault content; vault watcher must exist first                 |
| `rag/queries.py` before `rag/engine.py` | Phase 2   | Phase 2   | `HybridRAGEngine` calls SQL in `queries.py`                               |
| `skills/` before `agent/`               | Phase 3   | Phase 2   | Agent's `skill_run` tool calls the skills runtime                         |
| `llm/gateway.py` before everything else | Phase 1   | Phase 2+  | Embedding and LLM calls depend on the router                              |
| `auth/middleware.py` before `services/` | Phase 1   | Phase 1   | `OperationContext` is constructed by middleware                           |

### 6.10 Phase-Intrinsic Anti-Patterns

> **FOR AI AGENTS:** These patterns look correct but violate phase ordering or architectural constraints.

| Anti-Pattern                                          | Why Wrong                                                | Correct Approach                                                           |
| ----------------------------------------------------- | -------------------------------------------------------- | -------------------------------------------------------------------------- |
| Importing FastAPI types in `services/`                | Makes services non-transport-agnostic (violates REQ-131) | Use Pydantic models only; no `Request`, `Response`, `HTTPException`        |
| Calling LLM in vault watcher thread                   | Blocking call in sync thread; causes deadlock            | Queue work to asyncio via `call_soon_threadsafe()`, handle in main thread  |
| MCP tool implementation that bypasses service layer   | Duplicates logic; drift between transports               | All tools call `services/*.py` functions                                   |
| Using `SET LOCAL` for RLS GUC                         | GUC only lasts transaction scope                         | Use `SET` for session scope; `RESET` in `finally:` block                   |
| Calling `LiteLLM` directly in routes                  | No cost tracking, no key injection                       | Go through `llm/router.py` which handles both                              |
| Skipping `enrichment_hash` on page write              | Stale embeddings; re-index storm on model change         | Always compute `enrichment_hash` on write; compare to decide re-enrichment |
| Storing HTML in `pages.compiled_truth`                | XSS vector; violates REQ-2802                            | Always convert HTML → markdown before storage                              |
| `mcp_servers` table modified without admin role check | Trust boundary violation                                 | Admin-only RLS; verify `ctx.role == 'admin'` before any mutation           |

---

## 6A. Epics, Features & Prioritisation

### 6A.1 Epic map

| Epic                      | Description                                                                                      | Phases |
| ------------------------- | ------------------------------------------------------------------------------------------------ | ------ |
| E1: Foundation            | Docker, auth, schema, file watcher, vault layout, MCP stdio + HTTP, REST + WebSocket             | 1      |
| E2: RAG & Agent           | Chunking, embedding, hybrid retrieval, auto-link extraction, 22-tool agent, brain-first prompt   | 2      |
| E3: Skills & Ingestion    | Skills runtime, RESOLVER.md dispatcher, idea/media/meeting ingestion, tiered enrichment, recipes | 3      |
| E4: Memory & Maintenance  | Memory Dream nightly cycle, brain maintenance loop, maintenance report                           | 4      |
| E5: Web & Workspaces      | Web search, project/workspace scoping, vault intelligence endpoints                              | 5      |
| E6: Admin & Observability | Admin REST + CLI, embedding migration, Prometheus metrics, audit log query                       | 6      |
| E7: Platform              | MCP server registry, minion-orchestrator (DAG), backups, rate limits                             | 7      |
| E8: Electron Client       | Desktop UI, tray + Quick Chat, Obsidian export, auto-update                                      | 8      |

### 6A.2 MoSCoW prioritisation

**Must Have** — v1.0 blocker:
- All Phase 1 REQs (REQ-200–207)
- All Phase 2 REQs (REQ-210–215)
- All Phase 3 REQs (REQ-220–224)
- All Phase 4 REQs (REQ-230–232)
- Auth, RLS, encrypted keys (REQ-001–010, REQ-100–112)
- Single-container deploy + supervisord (REQ-100–103)

**Should Have** — significant value, target v1.0:
- Web search + workspaces (REQ-2720–2723)
- Admin surfaces + Prometheus (REQ-2730–2732)
- MCP server registry (REQ-2740)
- Backup automation (REQ-2742)

**Could Have** — nice for v1.0:
- Durable-job DAGs (REQ-2741)
- Full Electron client (REQ-2750–2756)
- Obsidian export (REQ-2754)

**Won't Have** (v1.0):
- LightRAG / GraphRAG / LLM-based link extraction (REQ-012)
- Mobile clients
- Real-time collaborative editing
- Custom RBAC roles beyond `admin` and `user`
- VS Code companion extension

### 6A.3 Feature inventory (cross-reference to REQ blocks)

| Feature ID   | Definition                                                            | Phase | Primary REQs               |
| ------------ | --------------------------------------------------------------------- | ----- | -------------------------- |
| F-AUTH-01    | User registration, login, password hashing (argon2-cffi)              | 1     | REQ-400–402                |
| F-AUTH-02    | MCP bearer tokens (per-user, named, revocable)                        | 1     | REQ-410–414                |
| F-AUTH-03    | Admin role + audited admin operations                                 | 1     | REQ-420–421                |
| F-SCHEMA-01  | Full database schema + RLS policies + GUC discipline                  | 1     | REQ-300–352, REQ-2705–2709 |
| F-DOCKER-01  | Single Docker image + supervisord + bootstrap                         | 1     | REQ-100–103, REQ-2500–2531 |
| F-MCP-01     | MCP stdio mode                                                        | 1     | REQ-500                    |
| F-MCP-02     | MCP HTTP (Streamable HTTP) mode                                       | 1     | REQ-501+                   |
| F-IDX-01     | Watchdog file indexer with thread→asyncio handoff                     | 1     | REQ-203                    |
| F-IDX-02     | Auto-link extraction on every page write                              | 2     | REQ-212, Section 15        |
| F-RAG-01     | Hybrid retrieval (vector + BM25 + graph + RRF)                        | 2     | REQ-1200–1209, REQ-104–107 |
| F-RAG-02     | Multi-query expansion + intent classifier + dedup                     | 2     | REQ-1200–1207              |
| F-AGENT-01   | 22-tool agent surface                                                 | 2     | Section 17, REQ-1300–1302  |
| F-AGENT-02   | Brain-first system prompt + refusal-on-insufficient-evidence          | 2     | REQ-1300–1302              |
| F-SKILLS-01  | Skills runtime + RESOLVER.md dispatcher                               | 3     | REQ-1400–1441              |
| F-SKILLS-02  | Default skill pack (29 skills)                                        | 3     | REQ-1440 + Appendix A      |
| F-INGEST-01  | idea-ingest, media-ingest, meeting-ingestion                          | 3     | REQ-1500–1543              |
| F-ENRICH-01  | Tiered (T1/T2/T3) entity enrichment                                   | 3     | REQ-1600–1622              |
| F-RECIPE-01  | Data-research recipes                                                 | 3     | Section 21                 |
| F-MEM-01     | Memory Dream nightly consolidation                                    | 4     | Section 30D                |
| F-MEM-02     | Brain maintenance (stale, orphans, links, citations, backlinks, tags) | 4     | REQ-230–232                |
| F-WEB-01     | Web search with cross-vault reference detection                       | 5     | REQ-2720                   |
| F-WORK-01    | Projects / workspaces (folder/tag scoping + system prompt)            | 5     | REQ-2721                   |
| F-VAULT-01   | Vault intelligence endpoints (orphans, hubs, suggestions, graph)      | 5     | REQ-2722                   |
| F-ADMIN-01   | Admin user CRUD + shared keys                                         | 6     | REQ-2730                   |
| F-ADMIN-02   | Embedding migration (estimate, start, status, cancel)                 | 6     | REQ-2730                   |
| F-ADMIN-03   | Dream status / trigger by user                                        | 6     | REQ-2730                   |
| F-OBS-01     | Prometheus `/metrics` + structured logs                               | 6     | REQ-2220–2222, REQ-2731    |
| F-MCP-REG-01 | Admin-managed MCP server registry                                     | 7     | REQ-2740                   |
| F-JOBS-01    | Durable-job parent-child DAGs                                         | 7     | REQ-2741                   |
| F-BACKUP-01  | Backup automation script + restore                                    | 7     | REQ-2742 + Section 24      |
| F-CLIENT-01  | Electron desktop client                                               | 8     | REQ-2750–2756              |
| F-CLIENT-02  | System tray + Quick Chat + global hotkey                              | 8     | REQ-2751                   |
| F-CLIENT-03  | Obsidian export                                                       | 8     | REQ-2754                   |

---

## 7. Data Model

### 7.1 Tables (PostgreSQL 16, all with `created_at`, `updated_at` `TIMESTAMPTZ`)
- **REQ-300** `users(id UUID PK, username TEXT UNIQUE, email TEXT, password_hash TEXT, role TEXT CHECK in ('admin','user'), is_active BOOL, ...)`.
- **REQ-301** `sessions(id UUID PK, user_id UUID FK, token_hash TEXT, expires_at TIMESTAMPTZ, ...)`.
- **REQ-302** `mcp_tokens(id UUID PK, user_id UUID FK, name TEXT, token_hash TEXT, last_used_at TIMESTAMPTZ, revoked_at TIMESTAMPTZ, ...)`.
- **REQ-303** `provider_keys(id UUID PK, user_id UUID FK, provider TEXT, encrypted_key BYTEA, key_hint TEXT, ...)` — `encrypted_key` MUST NEVER be returned by any API. Shared (admin-provided) provider keys MAY exist in system configuration; per-request resolution order is defined in Section 24.2.
- **REQ-304** `vaults( id UUID PK, owner_user_id UUID NULL, kind TEXT CHECK in ('private','shared'), path TEXT, ...)`.
- **REQ-305**  `pages( id UUID PK, vault_id UUID FK, slug TEXT, title TEXT, type TEXT CHECK in ( 'person','company','concept','idea','project', 'note', 'meeting','article','media','personal' ), note_type TEXT CHECK in ('fleeting','literature','permanent', 'archived_fleeting','skill','moc' ) NULL, frontmatter JSONB, compiled_truth TEXT, compiled_truth_updated_at TIMESTAMPTZ, content_hash TEXT, enrichment_hash TEXT, version INT, ...)`. UNIQUE on (vault_id, slug). Two separate type systems apply: - `type` is the **dossier kind** (what kind of entity or object the page describes). - `note_type` is the **Zettelkasten lifecycle kind** (what role the page plays in the knowledge cycle; see §30E). `type` represents the semantic dossier kind of the page and MUST remain limited to the values defined in the enum above. Capture‑specific distinctions (e.g., tweet, voice note, original capture) MUST NOT introduce new `type` values and are represented via folder conventions and optional frontmatter fields (e.g., `subtype`). `compiled_truth_updated_at` is updated on every successful `update_compiled_truth` call and is used for stale detection. `enrichment_hash` is the xxhash64 (XXH64) of concatenated enrichment inputs and is compared on write to decide whether re‑enrichment and re‑embedding are required. `content_hash` is the xxhash64 (XXH64) of the raw page file bytes as stored on disk, including YAML frontmatter and body, with no normalization (exact byte comparison; line endings preserved). It is used solely as a low‑level change detector for: - filesystem reconciliation (watchdog vs database), - API/MCP write idempotency, - deciding whether a page requires re‑parse and re‑index. `content_hash` MUST NOT be used for semantic comparison, enrichment logic, search freshness, or staleness checks. **Semantic hashing (reserved, non‑v1):**  A future revision MAY introduce an optional `semantic_hash` representing a hash of a normalized parsed representation of the page (e.g., sorted frontmatter keys, normalized whitespace, parsed markdown body) to distinguish semantic stability from byte‑level changes. `semantic_hash` is not implemented in v1, does not exist as a column, and MUST NOT affect indexing or enrichment behavior unless explicitly introduced by a future migration. 
- **REQ-306** `page_versions(id UUID PK, page_id UUID FK, version INT, frontmatter JSONB, compiled_truth TEXT, timeline TEXT, content_hash TEXT, created_at TIMESTAMPTZ)`.
- **REQ-307** `chunks(id UUID PK, page_id UUID FK, chunk_index INT, kind TEXT CHECK in ('compiled_truth','timeline','frontmatter'), text TEXT, enriched_content TEXT, tsv tsvector GENERATED, embedding vector(<rag.embedding_dimensions>), ...)`. `text` is raw content; `enriched_content` includes enrichment prefix (e.g. "Entity: John Doe | Role: CEO") used for embedding; `tsv` is computed from `text`; `embedding` is computed from `enriched_content`. `embedding` dimensions MUST equal the active configured embedder dimensions; migrations MUST handle dimension changes by rebuilding the column type and vector indexes (REQ-2105).
- **REQ-308** `entities(id UUID PK, vault_id UUID FK, kind TEXT CHECK in ('person','company','concept','idea'), canonical_slug TEXT, aliases TEXT[], ...)`.
- **REQ-309** `links(id UUID PK, src_page_id UUID FK, dst_entity_id UUID FK, link_type TEXT, confidence REAL, source_kind TEXT CHECK in ('wikilink','bare_slug','inferred'), context_excerpt TEXT, ...)`. INDEX on `(dst_entity_id, link_type)`.
- **REQ-310** `timeline_events(id UUID PK, page_id UUID FK, event_date DATE, source TEXT, detail TEXT, raw_ref TEXT, ...)`.
- **REQ-311** `tags(id UUID PK, vault_id UUID FK, name TEXT)`, `page_tags(page_id, tag_id)` join.
- **REQ-312** `jobs(id UUID PK, parent_id UUID NULL, kind TEXT, status TEXT, payload JSONB, result JSONB, run_at TIMESTAMPTZ, attempts INT, idempotency_key TEXT UNIQUE NULL, ...)`.
- **REQ-313** `audit_log(id UUID PK, user_id UUID NULL, action TEXT, target_kind TEXT, target_id UUID NULL, request_id UUID NULL, payload JSONB, created_at TIMESTAMPTZ)`. `request_id` enables correlation with `OperationContext.request_id` (REQ-520).
- **REQ-314** `skills(id UUID PK, namespace TEXT CHECK in ('system','user'), user_id UUID NULL, name TEXT, version TEXT, frontmatter JSONB, body TEXT, ...)`. UNIQUE `(namespace, COALESCE(user_id, '00000000-...'), name)`.
- **REQ-315** `recipes(id UUID PK, namespace TEXT, user_id UUID NULL, name TEXT, version TEXT, yaml TEXT, ...)`.
- **REQ-316** `eval_candidates(id UUID PK, user_id UUID FK, kind TEXT, query TEXT, retrieved_slugs TEXT[], ...)` — opt-in capture.
- **REQ-360** `conversations(id UUID PK, user_id UUID FK, title TEXT, mcp_mode TEXT CHECK in ('disable','auto','manual') DEFAULT 'auto', web_search_enabled BOOL DEFAULT false, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)`.
- **REQ-361** `messages(id UUID PK, conversation_id UUID FK, role TEXT CHECK in ('user','assistant','system'), content TEXT, citations JSONB, tokens_used INT, model TEXT, created_at TIMESTAMPTZ)`.
- **REQ-362** `memories(id UUID PK, user_id UUID FK, content TEXT, source_conversation_id UUID FK, extracted_at TIMESTAMPTZ, archived BOOL DEFAULT false)`.
- **REQ-363** `dream_audit_log(id UUID PK, user_id UUID FK, run_at TIMESTAMPTZ, kind TEXT, status TEXT, pages_processed INT, memories_created INT, errors JSONB)`.
- **REQ-364** `projects(id UUID PK, user_id UUID FK, name TEXT, folder_patterns TEXT[], tag_includes TEXT[], tag_excludes TEXT[], system_prompt TEXT, default_model TEXT, created_at TIMESTAMPTZ)`.
- **REQ-365** `operation_log(id UUID PK, user_id UUID FK, operation TEXT, target_kind TEXT, target_id UUID, payload JSONB, created_at TIMESTAMPTZ)`.
- **REQ-366** `llm_usage(id UUID PK, user_id UUID FK, provider TEXT, model TEXT, input_tokens INT, output_tokens INT, cost_usd REAL, conversation_id UUID FK, created_at TIMESTAMPTZ)`.
- **REQ-367** `index_events(id UUID PK, user_id UUID FK, event_type TEXT, page_slug TEXT, details JSONB, created_at TIMESTAMPTZ)`.
- **REQ-368** `user_settings(id UUID PK, user_id UUID FK, settings JSONB, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)`.
- **REQ-369** `system_config(id UUID PK, key TEXT UNIQUE, value JSONB, updated_at TIMESTAMPTZ)`.
- **REQ-370** `mcp_servers(id UUID PK, name TEXT UNIQUE, type TEXT CHECK in ('stdio','streamable_http'), command TEXT, args TEXT[], env JSONB, url TEXT, auth_key_provider TEXT, always_allow TEXT[], enabled BOOL DEFAULT true, last_connected_at TIMESTAMPTZ, last_error TEXT)`. Admin-only RLS.

### 7.2 Indexes
- **REQ-320** HNSW index on `chunks.embedding` with `vector_cosine_ops`.
- **REQ-321** GIN index on `chunks.tsv`.
- **REQ-322** B-tree on `pages.slug`, `links.src_page_id`, `links.dst_entity_id`.
- **REQ-323** GIN index on `pages.frontmatter`.

### 7.3 RLS policies (pseudocode in Appendix C)
- **REQ-330** Every multi-tenant table MUST have RLS enabled.
- **REQ-331** A session GUC `app.current_user_id` MUST drive policies.
- **REQ-332** Shared-vault rows MUST be readable by all authenticated users; writable per the vault's ACL.
- **REQ-333** System/maintenance jobs MUST set `app.current_user_id` to a designated system UUID and use a policy carve-out.

### 7.4 RLS session context discipline
- **REQ-340** `get_db_session` MUST issue `SET app.current_user_id = ...` (not `SET LOCAL`) and MUST `RESET app.current_user_id` in a `finally:` block.
- **REQ-341** A unit test MUST assert that exiting a request scope leaves no session GUC leaked across pooled connections.

### 7.5 Vault layout on disk
- **REQ-350** Private vaults MUST live at `/vaults/private/{username}/`.
- **REQ-351** The shared vault MUST live at `/vaults/shared/`.
- **REQ-352** Vault paths MUST be confined; symlink escape, `..` traversal, and absolute paths outside the vault root MUST be rejected.

---

## 8. Authentication and Authorization

### 8.1 Users and sessions
- **REQ-400** Passwords MUST be hashed with argon2-cffi (memory ≥ 64 MiB, iterations ≥ 3, parallelism ≥ 1).
- **REQ-401** Sessions are represented by refresh tokens stored as SHA‑256 hashes in sessions. /auth/login returns {access_jwt, refresh_token}; access JWT is short-lived and not stored server-side; refresh token is stored hashed and revocable.
- **REQ-402** Login MUST rate-limit at 10 failures / 15 minutes / IP+username pair.

### 8.2 MCP bearer tokens
- **REQ-410** Each user MAY have multiple named MCP bearer tokens (e.g., "claude-code-laptop", "cursor-desktop").
- **REQ-411** Tokens MUST be 256-bit random, presented to the user once on creation, and stored as SHA-256 hashes.
- **REQ-412** MCP requests authenticated by an MCP token MUST run under that user's RLS context.
- **REQ-413** Tokens MUST be revocable individually; revocation MUST take effect within 5 seconds.
- **REQ-414** Tokens MUST record `last_used_at` on every successful auth.

### 8.3 RBAC
- **REQ-420** Two roles only: `admin` and `user`. Admin grants access to admin REST endpoints and CLI tools.
- **REQ-421** All admin operations MUST be auditable in `audit_log`.

### 8.4 Trusted Proxy Headers (Rate Limiting)
- **REQ-422** Client IP for rate limiting MUST use the direct socket peer IP by default.
- **REQ-423** `X-Forwarded-For` (or equivalent) MUST be honored only when `SMARTCOPILOT_TRUST_PROXY=true`.
- **REQ-424** When `SMARTCOPILOT_TRUST_PROXY=true`, forwarded headers MUST be accepted only from allowlisted proxy IP ranges.
- **REQ-425** If multiple IPs exist in `X-Forwarded-For`, the left-most IP MUST be treated as the client IP.

### 8.5 Step-Up (Fresh) Authentication for Admin Operations
- **REQ-430** Destructive or security-sensitive admin operations MUST require a "fresh authentication" factor verified within the last 60 minutes.
- **REQ-431** The system MUST provide a step-up authentication mechanism (e.g., `POST /api/v1/admin/reauth`) that re-validates the admin’s credentials and records a freshness marker.
- **REQ-432** Freshness MUST be represented as a time-bound value (e.g., `admin_fresh_until`) attached to the admin session or token.
- **REQ-433** Authorization middleware MUST enforce admin freshness for all routes marked as destructive and reject requests when freshness has expired. 
- **REQ-434** When fresh authentication is required but missing or expired, the system MUST return a structured `admin_reauth_required` error.

---

## 9. MCP Server (first-class)

### 9.1 Modes
- **REQ-500** The MCP server MUST support **stdio mode**, launchable via `smartcopilot mcp serve --stdio`. STDIO mode MUST never write to stdout except for JSON-RPC framing; logs MUST go to stderr.
- **REQ-501** The MCP server MUST support **HTTP mode** (Streamable HTTP transport) on a configurable port (default 8787), launched by supervisord under the name `mcp-http`.
- **REQ-502** Both modes MUST use the same tool implementations from the service layer.

### 9.2 Authentication
- **REQ-510** STDIO mode MUST authenticate via the `SMARTCOPILOT_MCP_TOKEN` environment variable.
- **REQ-511** HTTP mode MUST authenticate via `Authorization: Bearer <token>` and MUST return `missing_auth` / `invalid_token` / `service_unavailable` per gbrain conventions.
- **REQ-512** Per-token usage metrics MUST be recorded.

### 9.3 Trust boundary (OperationContext)
- **REQ-520** Every MCP request MUST be wrapped in an `OperationContext` with fields: `user_id`, `transport` ∈ {`stdio`,`http`}, `remote` ∈ {`true`,`false`}, `client_name`, `request_id`.
- **REQ-521** STDIO requests from a process whose CWD is inside `/vaults/` MUST be marked `remote=false`; HTTP requests MUST be marked `remote=true`. STDIO transport is always treated as a local-trust execution context; security relies on token scoping and the trust boundary, not on working-directory heuristics alone.
- **REQ-522** `remote=true` callers MUST be confined to vault-relative paths; symlinks, `..`, and absolute paths outside the vault MUST be rejected.
- **REQ-523** Slugs and filenames from `remote=true` callers MUST match `^[a-z0-9][a-z0-9\-]{0,127}$` (allowlist; no control chars, no RTL overrides, no backslashes).
- **REQ-524** A documented set of "protected" tools (e.g., `jobs.submit_shell`, `vault.delete`, `system.exec`) MUST be blocked for `remote=true` and only permitted for CLI/operator callers.

### 9.4 Tool surface (≥ 30 MCP tools, mirroring the REST API)
The MCP tool surface MUST include at minimum: `brain.search`, `brain.query`, `brain.get`, `brain.put`, `brain.append_timeline`, `brain.update_compiled_truth`, `brain.list`, `brain.delete`, `brain.history`, `brain.diff`, `brain.revert`, `brain.tags.list`, `brain.tags.add`, `brain.tags.remove`, `brain.backlinks`, `brain.graph.traverse`, `brain.entity.get`, `brain.entity.merge`, `brain.entity.alias.add`, `brain.stats`, `brain.health`, `apability_discovery`, `ingest.idea`, `ingest.media`, `ingest.meeting`, `enrich.entity`, `recipe.run`, `skill.list`, `skill.get`, `skill.run`, `jobs.submit`, `jobs.status`, `jobs.cancel`, `maintain.run`, `maintain.report`. Each MUST be defined per Section 10's service contract.

- **REQ-530** Each tool MUST have a JSON schema for inputs and outputs.
- **REQ-531** Each tool MUST be testable via an integration test that calls the underlying service directly with a constructed `OperationContext`.

---

## 10. REST API + WebSocket

### 10.1 Service layer parity
- **REQ-600** Every MCP tool MUST have a 1:1 REST endpoint backed by the same service function.
- **REQ-603A** "Special interactions" implemented via SSE/WebSocket events (e.g., `client_request: read_clipboard`, `client_request: open_editor`) are NOT MCP tools and are explicitly excluded from the MCP↔REST 1:1 parity requirement.
- **REQ-601** REST endpoints MUST be prefixed `/api/v1/`.
- **REQ-602** All REST responses MUST be Pydantic models. `encrypted_key` MUST NOT appear in any response schema.

### 10.2 WebSocket
- **REQ-610** A `/ws` endpoint MUST stream: indexing progress, job status updates, ingestion progress, maintenance reports, query streaming tokens.
- **REQ-611** WebSocket auth MUST use the same session or MCP-token model.

### 10.3 Errors
- **REQ-620** Errors MUST follow `{error: {code, message, details?}}` with stable codes: `unauthorized`, `forbidden`, `not_found`, `validation_error`, `conflict`, `rate_limited`, `service_unavailable`, `internal_error`.

### 10.4 Capability Discovery
- **REQ-630** The system MUST expose a capability discovery interface that allows clients to determine supported features and limits at runtime.
- **REQ-631** Capability discovery MUST be available via:
  - REST: `GET /api/v1/capabilities`
  - MCP tool: `capability_discovery`
- **REQ-632** The capability response MUST include at minimum:
  - supported transports (`stdio`, `http`)
  - clipboard capture availability
  - enabled ingestion capabilities (ocr, transcription, repo_ingest)
  - operational limits (max_upload_bytes, max_tool_payload_bytes)
- **REQ-633** Capability discovery MUST be read-only and MUST NOT require elevated permissions.

---

## 11. CLI Admin Tools (gbrain-style)

A `smartcopilot` binary MUST be available inside the container.

- **REQ-700** `smartcopilot user create --username <u> --email <e> [--admin]` — creates a user, prints generated password once.
- **REQ-701** `smartcopilot user list [--json]`.
- **REQ-702** `smartcopilot user delete --username <u>`.
- **REQ-703** `smartcopilot user passwd --username <u>` — interactive prompt.
- **REQ-704** `smartcopilot mcp token create --user <u> --name <n>` — prints token once.
- **REQ-705** `smartcopilot mcp token list --user <u>`.
- **REQ-706** `smartcopilot mcp token revoke --id <id>`.
- **REQ-707** `smartcopilot provider key set --user <u> --provider <p>` — reads key from stdin, encrypts.
- **REQ-708** `smartcopilot provider key list --user <u>` — never prints the key.
- **REQ-709** `smartcopilot vault create --kind {private|shared} [--user <u>]`.
- **REQ-710** `smartcopilot vault reindex [--vault <id>]`.
- **REQ-711** `smartcopilot mcp serve --stdio` and `smartcopilot mcp serve --http --port 8787`.
- **REQ-712** `smartcopilot doctor` — runs the smoke tests of Section 26.
- **REQ-713** `smartcopilot maintain run [--dry-run]` — runs a Memory Dream cycle on demand.
- **REQ-714** `smartcopilot ingest <file-or-url>` — routes to the proper ingestion skill.
- **REQ-715** `smartcopilot search <query>` and `smartcopilot query <question>`.
- **REQ-716** `smartcopilot get <slug>` and `smartcopilot put <slug>` (latter reads markdown from stdin).
- **REQ-717** `smartcopilot extract links --vault <id>` — backfill graph.
- **REQ-718** `smartcopilot extract timeline --vault <id>` — backfill timeline events.
- **REQ-719** `smartcopilot jobs list|status|cancel`.
- **REQ-720** `smartcopilot skill list|get|create|run`.
- **REQ-721** `smartcopilot skillify check <path>` and `smartcopilot skillify scaffold <name>`.
- **REQ-722** `smartcopilot check-resolvable` — validates skills tree for reachability, MECE, DRY, gap detection, orphans.
- **REQ-723** `smartcopilot smoke-test` — drop-in user tests at `/etc/smartcopilot/smoke-tests.d/*.sh`.
- **REQ-724** All CLI commands MUST support `--json` output for agent consumption and MUST exit non-zero on failure.

---

## 12. Admin REST Endpoints (parallel to CLI)

Every CLI admin command MUST have a corresponding admin REST endpoint, all under `/api/v1/admin/` and gated by the `admin` role:

- **REQ-800** `POST /api/v1/admin/users` (create), `GET /api/v1/admin/users`, `DELETE /api/v1/admin/users/{id}`.
- **REQ-801** `POST /api/v1/admin/users/{id}/password`.
- **REQ-802** `POST /api/v1/admin/users/{id}/mcp-tokens`, `GET …`, `DELETE …/{token_id}`.
- **REQ-803** `POST /api/v1/admin/users/{id}/provider-keys`, `GET …` (never returns the key), `DELETE …/{key_id}`.
- **REQ-804** `POST /api/v1/admin/vaults`, `GET …`, `POST …/{id}/reindex`.
- **REQ-805** `POST /api/v1/admin/maintain/run`.
- **REQ-806** `GET /api/v1/admin/health`, `GET /api/v1/admin/doctor`.
- **REQ-807** `POST /api/v1/admin/jobs/{id}/cancel`, `GET /api/v1/admin/jobs`.
- **REQ-808** `POST /api/v1/admin/skills`, `GET …`, `PUT …/{id}`, `DELETE …/{id}`.
- **REQ-809** Admin endpoints MUST log every mutation to `audit_log`.
- **REQ-810** Admin endpoints MUST be curl-able with a session cookie or an admin-scoped MCP token.

---

## 13. Vault Management

### 13.1 Layout and scope
- **REQ-900** Each user MUST have exactly one private vault at `/vaults/private/{username}/` and MAY access the shared vault at `/vaults/shared/`.
- **REQ-901** Vaults MUST be a directory tree of markdown files (`.md`) with optional binary attachments under `.attachments/`.
- **REQ-902** A vault MUST contain a `RESOLVER.md` at its root for that vault's user-namespace skills.

#### 13.1.1 Shared Vault Write Rules
- **REQ-903** Shared vault write access MUST follow the global policy `shared_vault_write` as defined in Section 5A.5.
- **REQ-904** All API/MCP paths that write to `/vaults/shared/` MUST enforce this policy before any filesystem mutation.
- **REQ-905** All writes to the shared vault (create/update/delete/move) MUST be recorded in `operation_log` and `audit_log` with user_id, action, target path/slug, and request_id correlation.

### 13.2 File watching and indexing
- **REQ-910** A `watchdog` Observer MUST monitor each vault.
- **REQ-911** Filesystem events MUST be handed to the asyncio loop via `loop.call_soon_threadsafe(...)`; no blocking call MUST occur inside the watchdog thread.
- **REQ-912** A debounced indexer MUST coalesce rapid edits (default 750 ms) and re-chunk + re-embed only changed pages, identified by content hash. The indexer’s "changed page" detection MUST compare pages.content_hash (XXH64 raw bytes) against the newly computed value from disk; if equal, the page MUST be skipped.
- **REQ-913** The indexer MUST update tsvector and HNSW indexes idempotently.
- **REQ-914** On startup, a full reconciliation pass MUST detect added, removed, and modified files vs the database and reconcile.

### 13.3 Conflict handling
- **REQ-920** "Human always wins": if a file on disk differs from the database, the on-disk content is authoritative; the database is updated to match. "Differs" means the computed XXH64 raw-bytes content_hash for disk content does not match the database pages.content_hash.
- **REQ-921** API/MCP writes MUST be crash-safe and follow this sequence:
  1) Write to a temporary file in the same directory.
  2) fsync the temp file.
  3) Atomic rename to the target path.
  4) Read back the on-disk bytes and compute `content_hash`.
  5) Update the database in a single DB transaction using the computed `content_hash`.
  If step (4) or (5) fails, the write MUST be treated as failed and logged.
- **REQ-921A** Conflict detection MUST compare on-disk `content_hash` with `pages.content_hash`. If the file changed between steps (1) and (3), the API write MUST abort with `conflict`.
- **REQ-921B** If a user modifies a file on disk while an agent-initiated write is in progress, the on-disk content is authoritative ("human always wins"); the agent write MUST abort, be logged, and be retriable after reconciliation.
- **REQ-930** Pages MAY support optimistic concurrency control using a `version` field.
- **REQ-931** Clients MAY supply `expected_version` with write requests. If the stored version does not match, the server MUST reject the request with HTTP 409 Conflict.
- **REQ-932** Conflict responses MUST include:
  - current page version
  - content_hash
  - pointers to diff or reconciliation guidance
- **REQ-933** After a conflict, filesystem watchers MUST reconcile disk and DB content according to the "human always wins" rule.

---

## 14. Page Schema and Conventions

### 14.1 Frontmatter
- **REQ-1000** Every page MUST have YAML frontmatter delimited by `---` lines.
- **REQ-1001** Required fields: `type` (one of `person|company|concept|idea|project|note|meeting|article|media|personal`), `title`. Optional structured fields include: `subtype`, `tags`, `aliases`, `slug`, `created`, `updated`, `score`, and type-specific fields (e.g., role, company, stage).
- **REQ-1002** Optional structured fields: `tags`, `aliases`, `slug`, `created`, `updated`, `score`, plus type-specific fields (`role`, `company`, `stage`, etc.).

### 14.2 Compiled truth + timeline split
- **REQ-1010** A page body MUST contain at most one horizontal-rule separator (`\n---\n`) below the closing frontmatter, separating the compiled truth (above) from the timeline (below).
- **REQ-1011** Compiled truth MUST be the current synthesized state and MAY be rewritten freely by agents.
- **REQ-1012** The timeline MUST be append-only, reverse-chronological, with each entry of the form `- YYYY-MM-DD: <source>: <detail>`.
- **REQ-1013** Timeline edits to existing entries MUST be rejected by the API/MCP put paths; they MUST instead append a new dated entry.
- **REQ-1014** Compiled-truth chunks MUST receive a configurable boost (default +0.15 to RRF score) in search ranking.

### 14.3 Slugs and wikilinks
- **REQ-1020** Slugs MUST be lowercase kebab-case; wikilinks MUST use `[[type/slug]]` or `[[type/slug|display]]`.
- **REQ-1021** Bare slug references (e.g., `people/jane-doe`) in body text MUST be auto-detected as link candidates.
- **REQ-1022** Code fences MUST be stripped before link extraction to avoid false positives.

### 14.4 Citations

> **Three citation formats coexist in this system:**
> - `[^srcN]` — in-page footnotes in the compiled-truth section (REQ-1030)
> - `[slug]` — agent-synthesized answer citations resolved to retrieved page hits (REQ-1221)
> - `[N]` (numeric) — chat-message-scoped streaming citations in SSE `tool_result` / `citations` events (Section 30B.4)

- **REQ-1030** Claims in compiled truth SHOULD carry a citation footnote `[^src1]` resolving to a `[^src1]: <ref>` line at end of compiled-truth section.
- **REQ-1031** The citation auditor (Section 22) MUST flag dangling and orphaned citations.

### 14.6 Attachment Policy
- **REQ-1040** Attachments MUST be stored under `.attachments/` and referenced from markdown pages via relative links.
- **REQ-1041** The system MUST enforce a maximum attachment size (configurable; default 50 MB).
- **REQ-1042** Only allowlisted MIME types MAY be attached. Disallowed types MUST be rejected early.
- **REQ-1043** Text-bearing attachments (PDF, image via OCR) MAY have extracted text indexed, but extracted text MUST NOT be embedded into the page markdown unless explicitly requested.
- **REQ-1044** Attachments MUST be content-hashed; duplicate attachments MAY be deduplicated internally but MUST preserve logical references.

---

## 15. Auto-Link Extraction and Typed Knowledge Graph

### 15.1 Zero-LLM extraction pipeline (runs on every page write)
- **REQ-1100** Strip code fences and inline code spans.
- **REQ-1101** Detect entity references via:
  1. Markdown links and wikilinks.
  2. Bare slugs of the form `type/slug` matching the slug allowlist.
  3. Display-name fuzzy match against `entities.aliases` (pg_trgm threshold ≥ 0.85).
- **REQ-1102** Within-page dedup: collapse same target to a single link.
- **REQ-1103** Stale-link reconciliation: links no longer present in the new body MUST be deleted.
- **REQ-1104** A page MAY emit multiple link types to the same target (e.g., `works_at` and `advises`).

### 15.2 Typed inference cascade
- **REQ-1110** Link type MUST be inferred deterministically by, in order, the following signals:
  1. Explicit annotation in markdown: `[[people/jane|jane]]{rel=invested_in}`.
  2. Section header on source page (e.g., `## Investments`, `## Founded`, `## Advisor To`, `## Attended`).
  3. Source page `type` priors (e.g., a `person` page in a partner-bio template defaults investments to `invested_in`).
  4. Sentence-level regex cues (`founded`, `co-founded`, `invested in`, `attended`, `works at`, `advises`).
  5. Fallback: `mentions`.
- **REQ-1111** Default supported link types: `attended`, `works_at`, `founded`, `co_founded`, `invested_in`, `advises`, `mentions`, `references`, `related_to`, `parent_of`, `child_of`, `replaces`, `replaced_by`.
- **REQ-1112** Each link MUST carry `confidence ∈ [0,1]` from a deterministic table indexed by (signal, page-role).

### 15.3 Graph queries
- **REQ-1120** Graph traversal MUST use a recursive CTE with a configurable max depth (default 3, hard cap 8).
- **REQ-1121** A backlink-boost MUST be applied to search ranking proportional to in-degree of the target entity (capped to avoid runaway).
- **REQ-1122** `brain.graph.traverse(start, link_types?, depth?, direction?)` MUST return nodes + edges as JSON.

### 15.4 Backfill
- **REQ-1130** `smartcopilot extract links --vault` MUST backfill the link table for existing pages.
- **REQ-1131** `smartcopilot extract timeline --vault` MUST backfill `timeline_events` from the timeline section of existing pages.

---

## 16. Hybrid RAG Pipeline

### 16.1 Pipeline stages
- **REQ-1200** Query → intent classifier (`entity` | `temporal` | `event` | `general`) using a deterministic classifier first, LLM fallback only if ambiguous.
- **REQ-1201** Multi-query expansion: rephrase the user query into 3 paraphrases via a cheap LLM (Phase 1 default: `claude-haiku` or `gpt-4o-mini` per provider availability).
- **REQ-1202** For each query, run vector search (HNSW cosine top-K=50) and BM25 search (`websearch_to_tsquery`, top-K=50) in parallel.
- **REQ-1203** Run a graph query when the intent is `entity` or `temporal`, fetching pages within depth 2 of detected entities.
- **REQ-1204** Fuse results using RRF: `score(d) = Σ_i 1 / (60 + rank_i(d))` across all retrievers.
- **REQ-1204A** Hybrid fusion uses Reciprocal Rank Fusion (RRF) without per-retriever weighting; `rag.hybrid_weights` is not used in v1.
- **REQ-1205** Apply compiled-truth boost (+0.15) to chunks with `kind='compiled_truth'`.
- **REQ-1206** Apply backlink boost: `score(d) += min(0.10, in_degree(target_entity)/100)`.
- **REQ-1207** 4-layer dedup, in order: by source page, by cosine > 0.85, type cap (no single `type` exceeds 60%), per-page max chunks (default 3).
- **REQ-1208** Stale alert annotation: if the page's compiled-truth `updated` is older than the latest timeline entry, mark the result `stale=true`.
- **REQ-1209** Final result MUST include for each hit: `slug`, `title`, `kind`, `excerpt`, `score`, `signals` (which retrievers contributed), `stale`.

### 16.2 Synthesis
- **REQ-1220** The agent's `query` tool MUST synthesize an answer ONLY from retrieved chunks. If retrieved evidence is insufficient, it MUST respond with `"the brain doesn't have info on X"` and not hallucinate.
- **REQ-1221** Every synthesized answer MUST include citations as `[slug]` references resolvable to retrieved hits.

### 16.3 Chunking
- **REQ-1230** Chunking MUST use a 5-level delimiter hierarchy: paragraphs > lines > sentences > clauses > whitespace. Default chunk size 800 tokens, overlap 100.
- **REQ-1231** Chunks MUST be tagged by `kind` (`compiled_truth`, `timeline`, `frontmatter`).
- **REQ-1232** Chunking MUST be idempotent (same input → same chunks → same content hashes).

---

## 17. Agent Surface (22 tools)

The system prompt + tool surface for the in-product agent MUST expose exactly these 22 tools:

1. `search` — hybrid retrieval with synthesis off.
2. `query` — hybrid retrieval with synthesis on, citations required.
3. `get_page` — fetch by slug.
4. `put_page` — create/update with full body.
5. `update_compiled_truth` — atomic rewrite of above-the-line.
6. `append_timeline` — append a dated entry.
7. `list_pages` — by type/tag/recency filters.
8. `delete_page` — soft delete (versioned).
9. `history` — list versions for a slug.
10. `diff` — diff between two versions.
11. `revert` — revert to an earlier version (re-chunks/re-embeds).
12. `tags` — list/add/remove tags.
13. `backlinks` — pages linking to a slug.
14. `graph_traverse` — typed graph walk.
15. `entity_get` — typed entity dossier.
16. `entity_merge` — merge two entities (admin / owner only).
17. `enrich_entity` — call tiered enrichment skill.
18. `ingest` — auto-route to ingestion skill by content type.
19. `recipe_run` — run a data-research recipe.
20. `skill_run` — execute a named skill.
21. `jobs_submit` — submit a durable job.
22. `maintain_run` — run brain maintenance on demand.

- **REQ-1300** The system prompt MUST include the **brain-first convention**: before any external API/LLM call to answer a factual question, the agent MUST `search` or `get_page` first.
- **REQ-1301** The system prompt MUST instruct the agent to read `RESOLVER.md` before creating any new page or running any new workflow.
- **REQ-1302** The agent MUST refuse to answer factual questions when retrieval returns insufficient evidence.

---

## 18. Skills System

### 18.1 Namespaces
- **REQ-1400** A **system** namespace MUST live at `/etc/smartcopilot/skills/` and ship with the default skill pack.
- **REQ-1401** A **user** namespace MUST live at `/vaults/private/{username}/skills/` and override system skills by name.
- **REQ-1402** A user-level RESOLVER.md MUST live at the vault root and chain to the system RESOLVER.md.

### 18.2 RESOLVER.md dispatcher
- **REQ-1410** Each RESOLVER.md MUST list `Trigger → Skill` mappings.
- **REQ-1411** When two skills match, the more specific MUST win (e.g., `meeting-ingestion` over `ingest`).
- **REQ-1412** URL content-type routing: link → `idea-ingest`, video/audio → `media-ingest`, PDF → `media-ingest`, calendar/transcript → `meeting-ingestion`.

### 18.3 Skill schema
- **REQ-1420** A skill is a directory `<name>/` containing:
  - `SKILL.md` with YAML frontmatter (`name`, `version`, `triggers`, `writes_pages`, `writes_to`, `chains`, `quality`).
  - Optional `code/` for deterministic helpers.
  - `tests/` with unit, integration, and resolver-trigger tests.
  - `evals/` with rubric-graded LLM cases (when applicable).
- **REQ-1421** A skill MUST have at least one resolver entry, one unit test, and one integration test before being considered "complete".

### 18.4 Conventions
- **REQ-1430** `conventions/quality.md` MUST define: minimum citation coverage, anti-hallucination rules, anti-paraphrase rules for verbatim sources.
- **REQ-1431** `conventions/brain-first.md` MUST mandate `search`/`get_page` before any external API call.
- **REQ-1432** `conventions/model-routing.md` MUST list cheap/balanced/strong tiers and which tasks default to which.
- **REQ-1433** `conventions/test-before-bulk.md` MUST require fixture-driven validation before running any operation that mutates ≥ 50 pages.
- **REQ-1434** `conventions/cross-modal.yaml` MUST list the cross-modal review checks invoked by `cross-modal-review`.

### 18.5 Default skill pack (29)
The default system skills MUST include: `signal-detector`, `brain-ops`, `ingest`, `idea-ingest`, `media-ingest`, `meeting-ingestion`, `enrich`, `query`, `maintain`, `citation-fixer`, `repo-architecture`, `publish`, `data-research`, `daily-task-manager`, `daily-task-prep`, `cron-scheduler`, `reports`, `cross-modal-review`, `webhook-transforms`, `testing`, `skill-creator`, `skillify`, `skillpack-check`, `smoke-test`, `minion-orchestrator`, `soul-audit`, `setup`, `migrate`, `briefing`. (See Appendix A for one-line definitions.)

### 18.6 Validation
- **REQ-1440** `smartcopilot check-resolvable` MUST validate reachability, MECE, DRY, gap detection, orphans across both namespaces and exit non-zero on failure.
- **REQ-1441** `smartcopilot skillify check <path>` MUST produce a 10-item scorecard (SKILL.md present, frontmatter valid, manifest entry, resolver entry, unit tests, integration tests, evals, brain filing, e2e smoke, resolver-trigger eval).

---

## 18A. Client Integration Kit (Claude Desktop, Hermes Agent, Generic MCP)

This section specifies the configuration artifacts Smart Copilot MUST ship so external MCP clients can connect to a deployed instance. Three clients are formally supported in v26.05.1: **Claude Desktop**, **Hermes Agent**, and a **Generic MCP** transport-neutral specification for any other compliant client.

### 18A.0 Skill system layering (normative)

Smart Copilot's skill system (Section 18) and the Hermes Agent skill system are two distinct layers that operate on opposite sides of the MCP boundary. Both MAY be active simultaneously and MUST NOT overlap in responsibility.

- **REQ-1499A** **Smart Copilot skills (server-side)** — markdown workflows in `/etc/smartcopilot/skills/` (system) or `/vaults/private/{username}/skills/` (user) — MUST be the ONLY layer permitted to: read or write the database, read or write vault files, invoke the embedder, invoke the LLM router for synthesis, run graph queries, perform auto-link extraction, dispatch durable jobs, or perform any operation requiring RLS or transactions.
- **REQ-1499B** **Hermes skills (client-side)** — markdown files in `~/.hermes/skills/smart-copilot/` shipped as part of Smart Copilot's Hermes skill pack — MUST be limited to: instructing the Hermes LLM when to call which `mcp_smart_copilot_*` tool, how to format responses, how to phrase citations, and how to suggest follow-up actions. Hermes skills MUST NOT attempt to replicate server-side logic.
- **REQ-1499C** A Hermes skill MUST NOT pre-process content before dispatching to a server-side ingestion tool. For example, a Hermes ingestion routing skill MUST NOT summarize a transcript and then call `brain_put_page`; it MUST call `mcp_smart_copilot_ingest` with the raw content and let the server-side `meeting-ingestion` skill handle dispatch and enrichment.
- **REQ-1499D** A Smart Copilot server-side skill MUST NOT attempt to drive client-side conversational behavior. Server-side skills return structured data; presentation is the responsibility of the client agent's own skills.
- **REQ-1499E** Hermes skill files MUST declare a compatibility footer with the minimum Smart Copilot version they require AND the list of MCP tool names they invoke. Drift MUST be detectable by `smartcopilot client validate hermes`.
- **REQ-1499F** When the Smart Copilot MCP tool surface changes (tool added, renamed, removed, or schema-changed), a corresponding Hermes skill pack release MUST be cut.
- **REQ-1499G** Users MAY edit or replace the shipped Hermes skill files; Smart Copilot MUST NOT enforce conformance, only detect breakage.
- **REQ-1499H** A documented end-to-end trace MUST exist (in `docs/clients/hermes/skill-flow.md`) showing how a user request flows through (1) Hermes-side skill firing, (2) MCP tool dispatch, (3) server-side skill resolution via `RESOLVER.md`, (4) server-side execution and chaining, (5) result return, (6) Hermes-side response-formatting skill firing.

### 18A.1 General requirements
- **REQ-1500A** Smart Copilot MUST ship a "Client Integration Kit" under `/etc/smartcopilot/clients/` and `docs/clients/` with one subdirectory per supported client: `claude-desktop/`, `hermes/`, and `generic-mcp/`.
- **REQ-1500B** A CLI command `smartcopilot client config <client>` MUST print a ready-to-paste configuration snippet, populated with the user's selected MCP token and the deployment's host URL.
- **REQ-1500C** A CLI command `smartcopilot client config <client> --token-name <n> [--user <u>] [--copy]` MUST issue a fresh MCP token (or reuse an existing one by name), embed it into the snippet, and optionally copy the result to the system clipboard.
- **REQ-1500D** Each client subdirectory MUST contain at minimum: `README.md` (install steps), `config.example.json` or `config.example.yaml` (template), and `troubleshooting.md`.
- **REQ-1500E** All examples MUST use a documented placeholder syntax (`{{HOST_URL}}`, `{{MCP_TOKEN}}`, `{{USERNAME}}`) that the CLI substitutes at print time.
- **REQ-1500F** Where a client supports stdio only, the kit MUST document the `mcp-remote` stdio→HTTP shim and provide a working example.

### 18A.2 Claude Desktop integration
- **REQ-1501A** The Claude Desktop config artifact MUST target `claude_desktop_config.json` at the platform-specific path (macOS: `~/Library/Application Support/Claude/`, Windows: `%APPDATA%\Claude\`, Linux: `~/.config/Claude/`).
- **REQ-1501B** The artifact MUST provide TWO connection profiles:
  1. **Stdio direct** — used when Claude Desktop is on the same host as the container, invoking `smartcopilot mcp serve --stdio` with `SMARTCOPILOT_MCP_TOKEN` in `env`.
  2. **HTTP via mcp-remote shim** — used when Claude Desktop is on a different host, invoking `npx -y mcp-remote https://{{HOST_URL}}/mcp --header "Authorization: Bearer {{MCP_TOKEN}}"` until Claude Desktop ships native Streamable HTTP transport.
- **REQ-1501C** The README MUST instruct the user to fully quit and relaunch Claude Desktop after editing the config (changes are not picked up by `Cmd+R`).
- **REQ-1501D** The README MUST include a verification step: ask Claude "list your tools" and confirm at least the `brain_search`, `brain_query`, and `brain_get_page` tools appear under the `smart-copilot` server.
- **REQ-1501E** The example HTTP-via-shim JSON MUST follow this exact shape:

  ```json
  {
    "mcpServers": {
      "smart-copilot": {
        "command": "npx",
        "args": ["-y", "mcp-remote", "https://{{HOST_URL}}/mcp",
                 "--header", "Authorization: Bearer {{MCP_TOKEN}}"]
      }
    }
  }
  ```
- **REQ-1501F** The CLI snippet generator MUST also emit a stdio-direct variant for local-host installs.

### 18A.3 Hermes Agent integration

Hermes is itself an agent, not a thin MCP client. Integration has TWO parts: connecting the MCP server, and shipping a Hermes-side skill pack that teaches the Hermes agent when to call Smart Copilot tools. See Section 18A.0 for the layering principle.

#### 18A.3.1 MCP server connection
- **REQ-1502A** The Hermes artifact MUST target `~/.hermes/config.yaml` under the `mcp_servers:` key.
- **REQ-1502B** The example MUST include both transports:

  Stdio:
  ```yaml
  mcp_servers:
    smart-copilot:
      command: "smartcopilot"
      args: ["mcp", "serve", "--stdio"]
      env:
        SMARTCOPILOT_MCP_TOKEN: "{{MCP_TOKEN}}"
  ```

  HTTP:
  ```yaml
  mcp_servers:
    smart-copilot:
      url: "https://{{HOST_URL}}/mcp"
      headers:
        Authorization: "Bearer {{MCP_TOKEN}}"
      timeout: 60
      connect_timeout: 10
  ```
- **REQ-1502C** A recommended-default `tools.include` allowlist MUST be provided that exposes the read-and-write brain surface but excludes admin operations (`maintain.run`, `entity.merge`, `jobs.submit_shell`).
- **REQ-1502D** The artifact MUST document `/reload-mcp` for Hermes to re-read the config without restart.
- **REQ-1502E** The artifact MUST document the tool-naming convention: Hermes registers Smart Copilot tools under `mcp_smart_copilot_<tool_name>` (e.g., `mcp_smart_copilot_brain_search`).
- **REQ-1502F** The artifact MUST recommend disabling MCP sampling for Smart Copilot (`sampling.enabled: false`) unless the operator explicitly wants Hermes to provide LLM inference back to Smart Copilot.

#### 18A.3.2 Hermes skill pack

Hermes' skills are markdown procedural-memory files (compatible with the `agentskills.io` standard). Smart Copilot MUST ship a complementary Hermes-side skill pack that gets installed into Hermes' skill directory. These skills are CLIENT-SIDE; they do not execute server logic and they do not duplicate server-side skill behavior — see REQ-1499A through REQ-1499D.

- **REQ-1502G** A Hermes skill pack MUST be packaged at `/etc/smartcopilot/clients/hermes/skills/` and MUST be installable into a Hermes instance via `smartcopilot client install-skills hermes --target ~/.hermes/skills/smart-copilot/`.
- **REQ-1502H** The skill pack MUST contain at minimum the following Hermes-side skills, each as a single markdown file conforming to Hermes' skill schema (`name`, `triggers`, `description`, `body`, optional `examples`):
  1. **`brain-first.skill.md`** — instructs the Hermes agent: before answering any factual question about people, companies, projects, or events, first call `mcp_smart_copilot_brain_search` or `mcp_smart_copilot_brain_query`. If insufficient evidence is returned, do not hallucinate; report "the brain doesn't have info on X" and offer to ingest a source.
  2. **`brain-write-conventions.skill.md`** — instructs Hermes how to write back to the brain: use `mcp_smart_copilot_brain_put_page` for new pages, `update_compiled_truth` for above-the-line edits, and `append_timeline` for dated events; never edit the timeline section by overwriting; respect the compiled-truth + timeline `---` separator.
  3. **`ingestion-routing.skill.md`** — when the user pastes a URL, transcript, file path, or asks "ingest this": route via `mcp_smart_copilot_ingest` which auto-dispatches to `idea-ingest`, `media-ingest`, or `meeting-ingestion` server-side. Do not attempt to summarize-then-ingest; let the server-side ingestion skill chain into enrichment automatically.
  4. **`entity-enrichment-trigger.skill.md`** — when the user references a person or company by name 3+ times in a conversation that the brain has only Tier-1 stub data for, suggest calling `mcp_smart_copilot_enrich_entity` with the slug.
  5. **`citation-fidelity.skill.md`** — when asked to summarize or quote, return citations as `[slug]` references resolvable by `mcp_smart_copilot_brain_get_page`. Never fabricate slugs.
  6. **`session-recap.skill.md`** — at the end of a long session, offer to write a session summary as a brain page via `mcp_smart_copilot_brain_put_page` so future Hermes sessions have continuity.
- **REQ-1502I** Each Hermes skill MUST include a `triggers` block listing 3–5 trigger phrases or patterns Hermes uses to fire the skill (e.g., for `brain-first`: "what do we know about", "tell me about", "have we discussed", "any context on").
- **REQ-1502J** The skill pack MUST include a top-level `MANIFEST.md` listing every skill, its trigger summary, the Smart Copilot tools it depends on, and minimum Smart Copilot version; failure of any required tool MUST be detectable via `smartcopilot client validate hermes`.
- **REQ-1502K** Each skill file MUST include a "compatibility" footer indicating the minimum Smart Copilot version it requires and the list of MCP tools it invokes.
- **REQ-1502L** When Smart Copilot ships a new MCP tool, an updated Hermes skill pack MUST be released; the version MUST be discoverable by Hermes' `/reload-skills` flow.
- **REQ-1502M** The shipped skill files MUST be plainly editable by users; Smart Copilot MUST NOT lock or sign them. The validate command (REQ-1502N) detects breakage but does not enforce conformance.

#### 18A.3.3 Hermes-side validation
- **REQ-1502N** `smartcopilot client validate hermes --config ~/.hermes/config.yaml` MUST: parse the Hermes config, verify the `smart-copilot` MCP server entry exists, attempt a connection with the embedded token, list the discovered tools, and assert the recommended set is present.
- **REQ-1502O** A health command `smartcopilot client doctor hermes` MUST run all of: token validity, HTTP/stdio reachability, tool list parity, skill pack installed, skill pack version current, manifest tools all present in the live MCP registry.

### 18A.4 Generic MCP client integration
- **REQ-1503A** A `generic-mcp/` directory MUST contain a transport-neutral specification: HTTP endpoint, transport (Streamable HTTP), authentication header format, full tool list, JSON Schemas for inputs/outputs, error-code reference, and rate limits.
- **REQ-1503B** A `tools.openapi.json` MUST be auto-generated from the MCP tool registry on every release.
- **REQ-1503C** The README MUST include a curl-based verification example demonstrating a successful tool list request and a sample tool invocation.

### 18A.5 OAuth 2.1 roadmap (forward compatibility)
- **REQ-1504A** Smart Copilot MUST architecturally accommodate OAuth 2.1 dynamic client registration so future MCP clients requiring OAuth can be onboarded without breaking changes; bearer-token auth remains primary in v26.05.1.
- **REQ-1504B** A documented stub `POST /mcp/oauth/register` SHOULD be present and return a 501 with a stable error code until OAuth is implemented.

### 18A.6 Documentation generation
- **REQ-1505A** The build pipeline MUST regenerate `docs/clients/<client>/README.md` and `docs/clients/<client>/config.example.*` on every PR that changes the MCP tool surface.
- **REQ-1505B** A CI check MUST fail the build if any client artifact references a tool that no longer exists in the MCP registry.
- **REQ-1505C** Each client README MUST include: a 30-second quickstart, a screenshot or text transcript verifying the connection, and a troubleshooting table mapping symptoms to root causes.

### 18.7 Skill and Recipe Schema Compatibility
- **REQ-1450** The server MUST define a supported compatibility range for skill and recipe schema versions.
- **REQ-1451** Skill and recipe frontmatter MUST declare a schema version.
- **REQ-1452** The system MUST validate schema version compatibility at load time and MUST reject incompatible skills or recipes.
- **REQ-1453** Incompatible definitions MUST be rejected with a structured `schema_incompatible` error.

---

## 19. Ingestion Skills

### 19.0 URL Fetch Security Policy
- **REQ-1531** The URL Fetch Security Policy applies to idea-ingest and to `/api/v1/web-search/fetch` (Jina Reader pipeline).
- **REQ-1532** Only `http` and `https` URL schemes are permitted for any server-side fetch.
- **REQ-1533** Requests to loopback, link-local, or private CIDR ranges MUST be rejected (SSRF protection).
- **REQ-1534** DNS MUST be resolved per request and every redirect target MUST be revalidated against SSRF rules.
- **REQ-1535** Maximum redirects MUST be 2.
- **REQ-1536** Maximum response size MUST be 10 MB.
- **REQ-1537** Connection timeout MUST be 10s and read timeout MUST be 10s unless otherwise specified.
- **REQ-1538** Violations MUST return a structured `fetch_blocked` error.
- **REQ-1539** Fetch requests MUST use a fixed User-Agent: `SmartCopilotBot/1.0`.
- **REQ-1540** If robots.txt disallows the requested URL for this User-Agent, the fetch MUST be rejected with `fetch_disallowed`.
- **REQ-1541** robots.txt results MUST be cached for 24 hours per host.
- **REQ-1542** robots.txt fetch timeout MUST be 5 seconds. When third-party readers such as Jina Reader are used, robots.txt enforcement MAY be delegated to the reader; in such cases the reader is considered responsible for compliance.

### 19.1 idea-ingest (links / articles / tweets)
- **REQ-1500** Inputs: a URL or pasted article text; an optional note.
- **REQ-1501** Behavior: fetch the URL (respect robots.txt, timeout 10s), extract main content via readability, classify the source as long-form article or short-form post (e.g. tweet), and create or update a page:
  - under `articles/<slug>/` for long-form content
  - under `articles/tweets/<slug>/` for tweets or short-form posts
All pages created by idea-ingest MUST use `type: article`. When the source is a tweet or short-form post, the page MUST include `subtype: tweet` in frontmatter. The page includes an executive summary, verbatim quotes (preserved exactly), key insights, and a "why it matters" section, and MUST create or update an author person page. The skill MUST chain into `enrich` for each detected person or company.
- **REQ-1502** Errors: `fetch_failed`, `unreadable_content`, `unsupported_url` MUST be returned as structured errors.
> Note: `tweet` is represented as `type: article` with `subtype: tweet` (not as a first-class `type` value).


### 19.2 media-ingest (video / audio / PDF / screenshots / repos)
- **REQ-1510** Inputs: a file path inside the vault `.attachments/` directory or a URL.
- **REQ-1511** Behavior:
  - Audio/video: transcribe via configured provider, store transcript verbatim, generate summary.
  - PDF: extract text (and OCR as fallback), preserve page numbers in citations.
  - Screenshots: OCR; store the image in `.attachments/`.
  - Repos: clone shallow, summarize README + structure.
- **REQ-1512** Voice notes MUST be captured verbatim (exact phrasing preserved, never paraphrased). Pages created from voice notes MUST use: 
  - `type: personal`
  - `subtype: voice_note`
Voice-note pages are stored under `media/voice-notes/<slug>/`. Other media outputs follow these rules:
  - Original source captures → `type: media`, `subtype: original`, stored under `media/originals/<slug>/`
  - Classified concept captures → `type: concept`
  - Classified people or company captures → `type: person` / `company`
  - Idea captures → `type: idea`
No media-ingest flow may introduce new `type` enum values.

### 19.3 meeting-ingestion (transcripts)
- **REQ-1520** Inputs: a meeting transcript (Circleback-style or generic).
- **REQ-1521** Behavior: identify all attendees, create/update person and company pages, create a `meetings/YYYY-MM-DD-<slug>` page with attendees, summary, action items, decisions, and verbatim quotes for material claims. MUST chain into `enrich` for each attendee. MUST emit `attended` typed links.
- **REQ-1522** Re-ingestion of the same transcript (same content hash) MUST be idempotent.

### 19.4 Wiring rule
- **REQ-1543** Every ingestion skill MUST call enrich for each detected person and company. Implementations missing this call MUST be rejected by check-resolvable.

---

## 20. Entity Enrichment

### 20.1 Tiered approach
- **REQ-1600** **Tier 1** (1–2 mentions): create stub page with name, aliases, and source citations only.
- **REQ-1601** **Tier 2** (3–9 mentions): augment with publicly-known basics gathered via configured providers (e.g., LinkedIn-style role, company); compiled truth ≤ 200 words.
- **REQ-1602** **Tier 3** (≥ 10 mentions or starred): full dossier with role history, related entities, key quotes, recent timeline events.
- **REQ-1603** Enrichment MUST be idempotent: re-running on a Tier-3 entity produces no diff unless new evidence has arrived.

### 20.2 Alias handling
- **REQ-1610** Aliases include misspellings, maiden names, nicknames, email addresses, social handles, phonetic variants.
- **REQ-1611** When enrichment encounters a new variant for a known entity, it MUST add the variant to `entities.aliases` and MUST NOT create a new page.

### 20.3 Filing rules
- **REQ-1620** Concept vs. Idea: teachable framework → `concept`; buildable thing → `idea`.
- **REQ-1621** Concept vs. Personal: shareable in a professional talk → `concept`; private reflection → `personal`.
- **REQ-1622** Idea vs. Project: someone is working on it → `project`; otherwise `idea`.

---

## 21. Data-Research Recipes

### 21.1 Schema
- **REQ-1700** A recipe is a YAML file with frontmatter fields `id`, `name`, `version`, `description`, `inputs`, `outputs`, `steps`, `health_check`.
- **REQ-1701** `inputs` declares typed parameters; `steps` declares an ordered list of operations (`fetch`, `extract`, `transform`, `write_page`, `append_timeline`, `enrich`).
- **REQ-1702** Trusted recipes MUST be those bundled in `/etc/smartcopilot/recipes/`. Recipes loaded from a vault directory or `SMARTCOPILOT_RECIPES_DIR` MUST be marked **untrusted** and MUST NOT be permitted to run `command` health checks or live HTTP health checks.

### 21.2 Execution
- **REQ-1710** `recipe.run <id> --param k=v` MUST execute deterministically; structured extraction MUST happen in code where possible, LLMs reserved for judgment-bound steps.
- **REQ-1711** Every recipe execution MUST be recorded in `audit_log` with provenance.

### 21.3 Default recipes (Phase 3)
- **REQ-1720** Ship at minimum: `email-thread-extract`, `linkedin-style-bio-extract`, `funding-round-extract`, `meeting-summary-extract`.

---

## 22. Memory Dream and Brain Maintenance

### 22.1 Schedule
- **REQ-1800** Memory Dream MUST run nightly at a configurable time (default 03:30 local container time) as a durable APScheduler job.
- **REQ-1801** A subset (`citation-fixer`, `dead-link-audit`) MAY run hourly.

### 22.2 Maintenance phases
- **REQ-1810** **Stale-page detection:** flag pages where compiled-truth `updated` is older than the latest timeline entry by ≥ 30 days; emit a maintenance task.
- **REQ-1811** **Orphan detection:** identify pages not linked from any other page and not tagged `index`; surface in report.
- **REQ-1812** **Dead-link audit:** identify wikilinks with no resolvable target page; create a stub or list as broken depending on policy.
- **REQ-1813** **Citation audit:** verify each `[^srcN]` has a definition; verify external citation URLs return 2xx within 10 s; flag failures.
- **REQ-1814** **Back-link enforcement:** ensure every typed link in `links` table has a corresponding mention on the source page; reconcile drift.
- **REQ-1815** **Tag consistency:** detect near-duplicate tags via pg_trgm; propose merges; auto-merge only with admin approval.
- **REQ-1816** **Graph population:** re-run `extract links` and `extract timeline` for any pages whose content hash changed since last run.
- **REQ-1817** **Embedding backfill:** re-embed any chunks whose embedder version differs from the current configured embedder.

### 22.3 Reporting
- **REQ-1820** A maintenance run MUST emit a report page at `system/maintenance/YYYY-MM-DD.md` with counts, fixed items, and unresolved items.
- **REQ-1821** The report MUST be retrievable via `maintain.report` (MCP) and `GET /api/v1/admin/maintain/report`.

---

## 23. Durable Job System

### 23.1 Engine
- **REQ-1900** APScheduler with `SQLAlchemyJobStore` against the same PostgreSQL instance MUST be the sole scheduler/queue.
- **REQ-1901** Jobs MUST persist across container restarts.

### 23.2 Job model
- **REQ-1910** Jobs MUST support parent-child DAGs via `parent_id`; child completion MUST be deliverable to a `child_done` inbox the parent can poll.
- **REQ-1911** Every job MUST be idempotent: an `idempotency_key` (UNIQUE) MUST suppress duplicate submissions.
- **REQ-1912** Failed jobs MUST retry with exponential backoff (default base 30 s, factor 2, cap 1 h, max 8 attempts).
- **REQ-1913** A jobs supervisor MUST keep the worker alive across crashes; supervisord restart policy is the outermost guard.

### 23.3 Job kinds
- **REQ-1920** Built-in kinds: `index_page`, `embed_chunks`, `extract_links`, `extract_timeline`, `enrich_entity`, `recipe_run`, `ingest_*`, `maintain`, `cron_<name>`, `subagent_run`.
- **REQ-1921** `jobs.submit_shell` (arbitrary shell) MUST be CLI/operator only; MCP `remote=true` callers MUST be blocked from this kind.

### 23.4 Recovery
- **REQ-1930** On boot, the worker MUST scan for `running` jobs orphaned by a crash, mark them `recovered`, and re-enqueue them.

### 23.5 Indexing Throttling and Backpressure
- **REQ-1940** The system MUST enforce limits on concurrent indexing and embedding jobs.
- **REQ-1941** Backpressure thresholds MAY be configured to limit queue depth and per-user indexing load.
- **REQ-1942** When throttling limits are exceeded, new indexing requests MUST fail fast with a structured error and retry guidance.
- **REQ-1943** Throttling limits and queue pressure MUST be observable via metrics and capability discovery.

---

## 24. LLM Provider Integration

### 24.1 LiteLLM as a library

- **REQ-2000** LiteLLM MUST be imported as a Python library; no proxy process is permitted.
- **REQ-2001** A central `llm_router` service MUST resolve `model` strings to provider+model and inject the user's encrypted-then-decrypted API key per request.
- **REQ-2002** Decrypted keys MUST be held only in process memory for the duration of the request.

### 24.2 Provider key management

- **REQ-2010** Keys MUST be Fernet-encrypted with a master key from `SMARTCOPILOT_FERNET_KEY` (mandatory env var; container refuses to start if absent).
- **REQ-2011** Master key rotation MUST be supported via `smartcopilot admin rotate-fernet --new-key <…>`.
- **REQ-2012** Provider key resolution MUST follow this precedence order for every LLM/embedding request:
  1) user-scoped provider key (`provider_keys.user_id = ctx.user_id`)
  2) shared/admin-provided key (system-configured shared key store)
  3) return a structured `missing_provider_key` error if neither exists.
- **REQ-2013** The key source used for each request MUST be recorded for auditing and cost attribution as `key_type ∈ {user, shared}` in `llm_usage`.

### 24.3 Routing tiers

- **REQ-2020** The router MUST expose tiers `cheap`, `balanced`, `strong` and a default mapping per provider; skills declare which tier they want, not a specific model.
- **REQ-2021** Per-user provider preferences MUST override the default tier mapping.

### 24.4 Cost and rate limits

- **REQ-2030** Token usage and cost MUST be recorded per request with user attribution.
- **REQ-2031** Per-user daily budgets MAY be configured; exceeding the budget MUST return `rate_limited`.

## 24A. Backup and Restore

Smart Copilot MUST provide a deterministic, operator‑controlled backup and restore mechanism suitable for single‑container and homelab deployments, without relying on external services.

### 24A.1 Backup Scope

- **REQ-2050** A full system backup MUST include:
  - All PostgreSQL application data, including pgvector indexes and job metadata.
  - All vault filesystem content under `/vaults/` (private and shared).
  - All non‑secret server configuration files under `/config/`.
- **REQ-2051** A backup MUST explicitly exclude:
  - Decrypted third‑party provider API keys.
  - The Fernet master key (`SMARTCOPILOT_FERNET_KEY`).
  - Transient runtime state (logs, caches, temporary files, sockets).
- **REQ-2052** Provider keys MUST remain encrypted in the backup exactly as stored in the database.
- **REQ-2053** The operator is responsible for preserving the Fernet key separately; loss of the Fernet key makes encrypted provider keys unrecoverable after restore.

### 24A.2 Backup Format

- **REQ-2060** Backups MUST be produced as a single compressed archive  (e.g., `.tar.zst` or `.tar.gz`).
- **REQ-2061** The backup archive MUST contain the following top‑level layout:
  - `db/` — logical PostgreSQL dump (pg_dump, plain or custom format).
  - `vaults/` — exact copy of the vault directory tree.
  - `config/` — server configuration files (non‑secret only).
  - `manifest.json` — backup metadata.
- **REQ-2062** `manifest.json` MUST include at minimum:
  - Backup timestamp (UTC).
  - Smart Copilot version.
  - Database schema migration head.
  - List of included components (db, vaults, config).
  - Backup tool version.

### 24A.3 Backup Execution

- **REQ-2070** A backup MUST be executable via a CLI command (`smartcopilot backup create`).
- **REQ-2071** A backup MUST also be executable as a durable job (`jobs.submit` with `kind=backup`).
- **REQ-2072** Backup execution MUST be safe to run while the system is online and MUST NOT require service shutdown.
- **REQ-2073** Backup execution MUST NOT modify vault files or database contents.
- **REQ-2074** Every successful or failed backup attempt MUST be recorded in `audit_log`.

### 24A.4 Restore Procedure

- **REQ-2080** Restore MUST be performed into a fresh or empty Smart Copilot instance.
- **REQ-2081** Restore MUST:
  - Load the database dump.
  - Restore vault files exactly as backed up.
  - Restore configuration files.
  - Run all pending database migrations automatically on first boot.
- **REQ-2082** Restore MUST fail fast if:
  - The database schema version is incompatible.
  - Vault paths are not writable.
  - The required Fernet key is not supplied at restore time.
- **REQ-2083** Restore MUST NOT silently skip failed components; partial restores MUST be rejected.

### 24A.5 Restore Verification

- **REQ-2090** A restore verification command MUST exist  
  (`smartcopilot backup verify`) that validates:
  - Database connectivity and schema health.
  - Presence of expected tables and indexes.
  - Vault readability and basic integrity.
  - Consistency with `manifest.json`.
- **REQ-2091** Restore verification failures MUST return structured errors suitable for CLI and automated workflows.

### 24A.6 Non‑Goals (Informative)

The backup and restore system does **not** include:
- Fernet key generation, escrow, or recovery.
- Off‑site storage or synchronization.
- Backup scheduling policies beyond invoking a durable job.
- Multi‑instance or multi‑region backup coordination.

### 24A.7 User Data Export (Non-admin)

- **REQ-2092** The system MUST provide a user-scoped data export mechanism that allows exporting all data owned by a specific user.
- **REQ-2093** User data export MUST be invocable via CLI and API, e.g.: `smartcopilot export user --username <user> --output <path>`.
- **REQ-2094** A user export MUST include:
  - All vault pages owned by the user.
  - User-specific database rows (memories, preferences, usage records).
  - User-owned project definitions and skill overrides.
- **REQ-2095** Encrypted provider keys MAY be included but MUST remain encrypted and MUST NOT be decrypted during export.
- **REQ-2096** User export archives MUST NOT include data belonging to other users or shared-vault content unless explicitly owned by the exporting user.

---

## 25. Embedding System

- **REQ-2100** Phase 1 default embedder MUST be `openai/text-embedding-3-small` at 1536 dimensions.
- **REQ-2101** The `chunks.embedding` column MUST use pgvector and MUST match the active embedding model’s configured dimensions. Dimension changes MUST be performed via the embedding migration flow (REQ-2105).
- **REQ-2102** An embedder version field MUST be stored on each chunk; a backfill job MUST re-embed any chunks whose version differs from the current default.
- **REQ-2103** Embedding requests MUST be batched (default batch size 64) with retry on transient errors.
- **REQ-2104** A local fallback embedder MAY be configured for offline operation.
- **REQ-2105** Embedding migration MUST support dimension changes (1536↔3072↔768) without data loss; migration MUST rebuild HNSW indexes and track progress.

---

## 26. Health Checks and Observability

### 26.1 Smoke tests (post-restart)
- **REQ-2200** `smartcopilot doctor` MUST run at minimum these checks: Python runtime, CLI binary present, Postgres reachable + migrations current, pgvector + tsvector available, APScheduler worker alive, watchdog observers alive, MCP stdio entrypoint loads, MCP HTTP endpoint reachable, Fernet key present and valid, at least one provider key present.
- **REQ-2201** Drop-in user smoke tests MUST be discovered at `/etc/smartcopilot/smoke-tests.d/*.sh` and executed in lexical order.

### 26.2 Health endpoints
- **REQ-2210** `GET /healthz` MUST return 200 if the API process is up.
- **REQ-2211** `GET /readyz` MUST return 200 only if Postgres, pgvector, scheduler, watchdog, and MCP HTTP are all healthy.
- **REQ-2212** `GET /api/v1/admin/health` MUST return a structured JSON breakdown.

### 26.3 Metrics and logs
- **REQ-2220** Structured JSON logs MUST be emitted to stdout for `fastapi`, `mcp-http`, `apscheduler`; STDIO MCP MUST log to stderr only.
- **REQ-2221** Prometheus-format metrics MUST be exposed at `/metrics`, including request counts, latencies, embedding counts, job successes/failures, MCP calls per tool.
- **REQ-2222** `audit_log` MUST be queryable via admin REST.

### 26.4 Data Retention Policies
- **REQ-2640** The system MUST define default retention periods for operational data.
- **REQ-2641** Default retention values:
  - `llm_usage`: 180 days
  - `audit_log`: 365 days
  - `operation_log`: 30 days
- **REQ-2642** Retention values MUST be admin-configurable.
- **REQ-2643** Expired records MUST be deleted or irreversibly anonymized.
- **REQ-2644** User-initiated deletion of derived data MUST NOT violate audit-log integrity requirements.

### 26.5 Degraded and Read-Only Modes

- **REQ-2660** The system MUST detect degraded operating conditions, including database unavailability, read-only filesystem, or embedding provider failure.
- **REQ-2661** When operating in degraded or read-only mode, the system MUST:
  - allow read-only retrieval from existing indexes
  - disable page writes, ingestion, and background jobs
  - continue serving health and capability discovery endpoints
- **REQ-2662** The current operating mode (`normal | degraded | read_only`) MUST be exposed via health endpoints.
- **REQ-2663** Attempts to perform disabled operations MUST return a clear, structured error indicating the current mode.

---

## 27. Security and Trust Boundary

- **REQ-2300** Every service entry point MUST construct an `OperationContext` (Section 9.3) and pass it down to services; services MUST refuse to run without one.
- **REQ-2301** `remote=true` callers MUST NOT be able to: execute arbitrary shell, write outside the user's vault, read other users' vaults, install or modify system skills, rotate keys, create users, or modify RLS-bypassing rows.
- **REQ-2302** Slug and filename validation MUST apply to all `remote=true` write paths.
- **REQ-2303** All admin endpoints MUST enforce `role='admin'` AND a fresh authentication factor (password or admin-scoped MCP token) within the last 60 minutes for destructive operations. The step-up (fresh authentication) mechanism used to satisfy this requirement is defined in Section 8.5.
- **REQ-2304** Fernet key, MCP token hashes, and password hashes MUST never be logged.
- **REQ-2305** CORS MUST be deny-by-default; the Electron client (Phase 8) origin will be allowlisted at that time.
- **REQ-2306** TLS termination is out of scope for the container; deployments MUST front the container with a reverse proxy for HTTP MCP and admin endpoints.

---

## 28. Testing Requirements

- **REQ-2400** Tests MUST run against a real PostgreSQL test database (no mocking of the DB layer); a `pytest` fixture MUST create an ephemeral schema per test session.
- **REQ-2401** Test runner MUST be `pytest` with `pytest-asyncio` in `auto` mode.
- **REQ-2402** RLS isolation tests MUST assert: user A cannot read user B's pages via any service path; admin endpoints with the wrong role return 403; switching session GUC mid-request is reflected in subsequent queries.
- **REQ-2403** Auto-link extraction MUST have unit tests for: code-fence stripping, within-page dedup, stale-link reconciliation, multi-type links, each typed-inference signal.
- **REQ-2404** Hybrid retrieval MUST have a fixture corpus + benchmark harness reporting Precision@5, Recall@5, top-1 stability, latency.
- **REQ-2405** MCP tools MUST have integration tests that drive both stdio and HTTP transports through the real MCP SDK.
- **REQ-2406** Drift tests MUST assert that every MCP tool has a corresponding REST endpoint and vice versa, and that their service-layer call signatures match.
- **REQ-2407** Skill validation tests MUST assert that `check-resolvable` passes on every PR.
- **REQ-2408** Phase acceptance criteria from Section 6 MUST each have at least one e2e test.

---

## 29. Deployment

### 29.1 Container
- **REQ-2500** A single Docker image MUST be the deliverable; image build MUST be reproducible via `docker build .` from the repo root.
- **REQ-2501** `supervisord` MUST run as PID 1 with `nodaemon=true` and supervise: `postgres`, `fastapi`, `mcp-http`, `apscheduler`, `watchdog`.
- **REQ-2502** A `/data` volume MUST hold the Postgres data directory; a `/vaults` volume MUST hold user vaults.

### 29.2 Environment variables
- **REQ-2510** Required: `SMARTCOPILOT_FERNET_KEY`, `POSTGRES_PASSWORD`, `SMARTCOPILOT_HOST_URL`.
- **REQ-2511** Optional: `SMARTCOPILOT_MCP_HTTP_PORT` (default 8787), `SMARTCOPILOT_API_PORT` (default 8000), `SMARTCOPILOT_LOG_LEVEL`, `SMARTCOPILOT_DEFAULT_EMBEDDER`, `SMARTCOPILOT_DEFAULT_TIER`.

### 29.3 First-boot setup
- **REQ-2520** On first boot, if no admin user exists, the container MUST print to stderr a one-time bootstrap token; the operator uses `smartcopilot bootstrap --token <…>` to create the first admin user.
- **REQ-2521** Alembic migrations MUST run automatically on boot using synchronous psycopg2 in `env.py`; the runtime MUST then connect via asyncpg.
- **REQ-2522** The default vault layout MUST be created (`/vaults/private/`, `/vaults/shared/`).
- **REQ-2523** The default skill pack and default recipes MUST be installed into the system namespace on first boot.

### 29.4 Upgrades
- **REQ-2530** Upgrades MUST run all pending migrations on container start; failed migrations MUST abort the boot.
- **REQ-2531** A migration MUST be provided to backfill `enrichment_hash` and backfill `compiled_truth_updated_at` on existing pages on first deploy. Existing `links` rows (with their typed-link columns) require no backfill migration.

---
## 30. UI — Phase 8 (Electron Desktop Client)

> **Phase 8 status:** This section captures the requirements that define the Phase 8 Electron desktop client. It supersedes the prior "UI (Deferred)" framing — Phase 8 is now a fully-specified delivery phase, not an open-ended deferral. Visual and interaction details are tracked in `ui-spec.md`; this section defines the contract between the client and the Smart Copilot REST + WebSocket + SSE surface.

- **REQ-2600** The Electron/TypeScript/React desktop client MUST live under `clients/desktop/` (see Section 5.2 / REQ-124) and MUST NOT be a precondition for declaring Phases 1–7 complete.
- **REQ-2601** The Phase 8 client MUST consume only the documented REST + WebSocket + SSE surface (Sections 30A and 30B); it MUST NOT bypass the service layer.
- **REQ-2602** All user-facing operations MUST remain available via CLI, MCP, or admin REST throughout Phases 1–7; the client MUST NOT hide functionality unique to itself.
- **REQ-2603** The client MUST authenticate with a session token obtained from `POST /api/v1/auth/login` and MUST maintain a WebSocket connection for real-time updates (see Section 30B).
- **REQ-2604** The client MUST consume the SSE stream from `POST /api/v1/chat/completions` for streaming chat responses (see Section 30B.2).
- **REQ-2605** The client MUST NOT store provider API keys; keys live in the database, encrypted via Fernet (REQ-110, REQ-009). The client UI manages keys exclusively through admin REST endpoints.
- **REQ-2606** The client MUST sanitise all clipboard HTML content with DOMPurify before posting to the server (see Section 30C).
- **REQ-2607** The client MUST persist client-only state (theme, layout, last-used vault path, last-active workspace) in `electron-store`; it MUST NOT persist user content or credentials in `electron-store`.
- **REQ-2608** Provider API tokens stored on the client side (e.g., MCP token cache) MUST use `safeStorage` (OS keychain) and MUST NOT be written to plain JSON.
- **REQ-2609** The client MUST emit thumbprint requests (e.g., user thumbs-up/down on citations) to the server for KPI tracking (see Section 30D).
- **REQ-2610** Detailed visual, layout, and interaction specs are tracked in `ui-spec.md`; where this PRD and `ui-spec.md` conflict, the PRD wins for data contracts and API bindings, and `ui-spec.md` wins for visual and interaction decisions.

---

## 30A. API Contract Reference

> **FOR AI AGENTS:** Implement these endpoints exactly as specified. The OpenAPI spec auto-generated from FastAPI is the runtime source of truth (see REQ-2700–2704), but these definitions are the design spec. Total: ~103 endpoints across 14 route groups. The MCP tool surface (Section 9.4) MUST mirror these endpoints; drift tests (REQ-2406) enforce parity.

### 30A.1 Auth (9 endpoints — Phase 1)

| Method | Path                           | Auth | Notes                                                                                                                                              |
| ------ | ------------------------------ | ---- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| POST   | `/api/v1/auth/register`        | None | First user → admin. Returns 403 when registration disabled and users exist                                                                         |
| POST   | `/api/v1/auth/login`           | None | Returns access + refresh tokens                                                                                                                    |
| POST   | `/api/v1/auth/refresh`         | None | Refresh token → new pair                                                                                                                           |
| POST   | `/api/v1/auth/change-password` | JWT  | Requires current password                                                                                                                          |
| GET    | `/api/v1/auth/me`              | JWT  | Returns current user profile (id, username, email, role, display_name, title, created_at)                                                          |
| PATCH  | `/api/v1/auth/me`              | JWT  | Update mutable user fields (`email`, `display_name`, `title`). Username immutable (used in vault paths).                                           |
| PATCH  | `/api/v1/auth/me/avatar`       | JWT  | Upload/replace avatar. Multipart `avatar` file, max 2 MB, server-resized to 128×128, stored at `/vaults/private/{username}/.avatar.png`. Phase 8+. |
| GET    | `/api/v1/auth/sessions`        | JWT  | List active sessions for current user                                                                                                              |
| DELETE | `/api/v1/auth/sessions/{id}`   | JWT  | Revoke a session by ID. Cannot revoke the request's own session (returns 400)                                                                      |

### 30A.2 MCP tokens (4 endpoints — Phase 1)

| Method | Path                             | Auth | Notes                                                                                 |
| ------ | -------------------------------- | ---- | ------------------------------------------------------------------------------------- |
| GET    | `/api/v1/mcp/tokens`             | JWT  | List user's MCP tokens (name, last_used_at, revoked_at; never the token itself)       |
| POST   | `/api/v1/mcp/tokens`             | JWT  | Issue a new named MCP token; returns the token plaintext exactly once                 |
| DELETE | `/api/v1/mcp/tokens/{id}`        | JWT  | Revoke an MCP token (effective within 5 seconds — REQ-413)                            |
| POST   | `/api/v1/mcp/tokens/{id}/rotate` | JWT  | Rotate by issuing a new token under the same name and revoking the old one atomically |

### 30A.3 Chat (8 endpoints — Phase 2; export endpoint Phase 8)

| Method | Path                                    | Auth | Notes                                                                                                                          |
| ------ | --------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------ |
| POST   | `/api/v1/chat/completions`              | JWT  | SSE streaming with RAG + citations (Section 30B.2)                                                                             |
| GET    | `/api/v1/conversations`                 | JWT  | Paginated. Query: `search`, `date_from`, `date_to`, `project_id` (UUID; pass `none` for unassigned)                            |
| GET    | `/api/v1/conversations/{id}`            | JWT  | With messages                                                                                                                  |
| POST   | `/api/v1/conversations`                 | JWT  | Create. Optional `project_id`                                                                                                  |
| PATCH  | `/api/v1/conversations/{id}`            | JWT  | Update `title`, `model_id`, `mode_id`, `project_id` (null to clear), `web_search_enabled`, `relevant_note_enabled`, `mcp_mode` |
| DELETE | `/api/v1/conversations/{id}`            | JWT  | Delete                                                                                                                         |
| POST   | `/api/v1/conversations/{id}/regenerate` | JWT  | Delete last assistant message, re-run                                                                                          |
| POST   | `/api/v1/conversations/{id}/export`     | JWT  | Export to vault as markdown. Phase 8 (Phase 2 endpoint stub may return 501).                                                   |

### 30A.4 Search (3 endpoints — Phase 2)

| Method | Path                      | Auth | Notes                                            |
| ------ | ------------------------- | ---- | ------------------------------------------------ |
| POST   | `/api/v1/search`          | JWT  | Hybrid: vector + BM25 + typed graph (Section 16) |
| POST   | `/api/v1/search/semantic` | JWT  | Vector-only                                      |
| POST   | `/api/v1/search/keyword`  | JWT  | BM25-only                                        |

### 30A.5 Pages / Documents (5 endpoints — Phases 1–3)

| Method | Path                                    | Auth | Phase | Notes                                                                                                                        |
| ------ | --------------------------------------- | ---- | ----- | ---------------------------------------------------------------------------------------------------------------------------- |
| GET    | `/api/v1/pages`                         | JWT  | 1     | Paginated. Query: `type`, `folder`, `tag`, `project_id` (applies workspace include/exclude/tags). Response includes `total`. |
| GET    | `/api/v1/pages/{slug}`                  | JWT  | 1     | Frontmatter + compiled_truth + timeline; includes back-links and outgoing typed links                                        |
| PUT    | `/api/v1/pages/{slug}`                  | JWT  | 1     | Create or update page. Triggers auto-link extraction (Section 15) and re-index (Section 30E).                                |
| POST   | `/api/v1/pages/upload`                  | JWT  | 3     | Import PDF, DOCX, HTML — dispatches to `media-ingest` skill                                                                  |
| GET    | `/api/v1/pages/upload/{task_id}/status` | JWT  | 3     | Poll import progress                                                                                                         |

### 30A.6 Vault (14 endpoints — Phases 1, 2, 3, 4, 5, 7)

| Method | Path                                     | Auth | Phase | Notes                                                                                      |
| ------ | ---------------------------------------- | ---- | ----- | ------------------------------------------------------------------------------------------ |
| POST   | `/api/v1/vault/write`                    | JWT  | 1     | Create/update file (raw passthrough to page write)                                         |
| POST   | `/api/v1/vault/move`                     | JWT  | 3     | Move + update wikilinks                                                                    |
| POST   | `/api/v1/vault/split`                    | JWT  | 3     | Split into atomic Zettel (Section 30G)                                                     |
| GET    | `/api/v1/vault/orphans`                  | JWT  | 5     | Orphan pages                                                                               |
| GET    | `/api/v1/vault/hubs`                     | JWT  | 5     | Most-connected pages                                                                       |
| GET    | `/api/v1/vault/health`                   | JWT  | 5     | Composite health score (orphan/density/type-coverage/freshness — Section 30D)              |
| GET    | `/api/v1/vault/graph`                    | JWT  | 5     | Wikilink graph in Cytoscape.js native format (Section 30A.6.1)                             |
| GET    | `/api/v1/vault/index/events`             | JWT  | 5     | User's recent index events                                                                 |
| GET    | `/api/v1/vault/links/suggestions/{slug}` | JWT  | 5     | Link suggestions for a specific page (slug required)                                       |
| GET    | `/api/v1/vault/links/suggestions`        | JWT  | 5     | Vault-wide top link suggestions (no slug)                                                  |
| GET    | `/api/v1/vault/index/progress`           | JWT  | 1     | `{active, current, total, eta_seconds}`. Used for status bars and welcome subtitles.       |
| POST   | `/api/v1/vault/organize`                 | JWT  | 5     | Dry-run reorganisation suggestions                                                         |
| POST   | `/api/v1/vault/organize/apply`           | JWT  | 5     | Apply organisation plan                                                                    |
| POST   | `/api/v1/vault/organize/undo`            | JWT  | 5     | Undo last organisation (uses OperationLog)                                                 |
| POST   | `/api/v1/vault/reindex`                  | JWT  | 2     | Trigger full reindex of current user's namespace. 202 Accepted. Rate-limited: 1/hour/user. |

#### 30A.6.1 `GET /api/v1/vault/graph` response schema

Query params: `namespace` (`private`|`shared`|`all`, default `all`), `note_type` (filter, comma-separated), `seed_page_id` (UUID; ego-graph mode), `max_hops` (default 3, only with seed), `max_nodes` (default 500), `min_links` (default 0, hides isolates).

Response body (Cytoscape.js native — passed directly to `cy.add()` without transformation):

```json
{
  "nodes": [
    {
      "data": {
        "id": "page-uuid-1",
        "label": "Backpropagation basics",
        "note_type": "permanent",
        "namespace": "private",
        "is_orphan": false,
        "incoming_count": 5,
        "outgoing_count": 3,
        "word_count": 247,
        "folder": "/concepts/ml/",
        "updated_at": "2026-02-14T09:30:00Z"
      }
    }
  ],
  "edges": [
    { "data": { "id": "link-uuid-1", "source": "page-uuid-1", "target": "page-uuid-2" } }
  ],
  "meta": {
    "total_nodes": 3847,
    "total_edges": 12503,
    "returned_nodes": 500,
    "returned_edges": 1823,
    "truncated": true
  }
}
```

`max_nodes: 500` default keeps Cytoscape.js Canvas renderer responsive (< 1,000 elements). Larger neighbourhoods use `seed_page_id` for focused exploration.

### 30A.7 Memories (6 endpoints — Phase 4)

| Method | Path                            | Auth | Notes                                                                     |
| ------ | ------------------------------- | ---- | ------------------------------------------------------------------------- |
| GET    | `/api/v1/memories`              | JWT  | Paginated; filter by `is_archived`                                        |
| POST   | `/api/v1/memories`              | JWT  | Create memory directly (manual capture)                                   |
| DELETE | `/api/v1/memories/{id}`         | JWT  | Soft-archive                                                              |
| POST   | `/api/v1/memories/search`       | JWT  | Vector search over memories                                               |
| GET    | `/api/v1/memories/dream/status` | JWT  | Last run, next eligible run, audit summary                                |
| POST   | `/api/v1/memories/dream/run`    | JWT  | Trigger Dream now (rate-limited; rejects if a run is already in progress) |

### 30A.8 Workspaces / Projects (5 endpoints — Phase 5)

| Method | Path                    | Auth | Notes                                                                                                                           |
| ------ | ----------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------- |
| GET    | `/api/v1/projects`      | JWT  | List user's projects                                                                                                            |
| POST   | `/api/v1/projects`      | JWT  | Create. Body: `name`, `description?`, `include_folders[]`, `exclude_folders[]`, `tags[]`, `system_prompt?`, `default_model_id?` |
| GET    | `/api/v1/projects/{id}` | JWT  | With page count + active conversation count                                                                                     |
| PATCH  | `/api/v1/projects/{id}` | JWT  | Update any field                                                                                                                |
| DELETE | `/api/v1/projects/{id}` | JWT  | Delete; conversations with this project_id have project_id set to NULL                                                          |

### 30A.9 Web search (2 endpoints — Phase 5)

| Method | Path                       | Auth | Notes                                                    |
| ------ | -------------------------- | ---- | -------------------------------------------------------- |
| POST   | `/api/v1/web-search`       | JWT  | DuckDuckGo + Wikipedia + cross-vault reference detection |
| POST   | `/api/v1/web-search/fetch` | JWT  | Jina Reader → nh3 → readability-lxml → markdown          |

### 30A.10 Models (2 endpoints — Phases 1–6)

| Method | Path                       | Auth | Notes                                                     |
| ------ | -------------------------- | ---- | --------------------------------------------------------- |
| GET    | `/api/v1/models`           | JWT  | List configured chat + embedding models with capabilities |
| GET    | `/api/v1/models/embedding` | JWT  | Embedding-only subset (used by admin migration UI)        |

### 30A.11 Settings (3 endpoints — Phases 1–6)

| Method | Path                     | Auth | Notes                                                                                     |
| ------ | ------------------------ | ---- | ----------------------------------------------------------------------------------------- |
| GET    | `/api/v1/settings`       | JWT  | Returns user's `user_settings.settings` JSONB plus effective server defaults              |
| PUT    | `/api/v1/settings`       | JWT  | Replace user settings JSONB. Validates against the documented key schema (Section 30H.2). |
| GET    | `/api/v1/settings/modes` | JWT  | List available chat modes (Ask/Write/Research/Focus + custom)                             |

### 30A.12 Usage (2 endpoints — Phase 6)

| Method | Path                       | Auth | Notes                                                        |
| ------ | -------------------------- | ---- | ------------------------------------------------------------ |
| GET    | `/api/v1/usage`            | JWT  | Current user's token usage + cost over time, grouped by day  |
| GET    | `/api/v1/usage/by-purpose` | JWT  | Breakdown by `purpose` (chat, dream, embedding, agent, etc.) |

### 30A.13 Admin (24 endpoints — Phase 6, MCP registry Phase 7)

| Method | Path                                         | Auth  | Notes                                                           |
| ------ | -------------------------------------------- | ----- | --------------------------------------------------------------- |
| GET    | `/api/v1/admin/usage/total`                  | Admin | All-user usage aggregate                                        |
| GET    | `/api/v1/admin/usage/history`                | Admin | Usage time series                                               |
| GET    | `/api/v1/admin/health`                       | Admin | System health; reads backup-status.json                         |
| GET    | `/api/v1/admin/users`                        | Admin | List with stats                                                 |
| POST   | `/api/v1/admin/users`                        | Admin | Create user                                                     |
| DELETE | `/api/v1/admin/users/{id}`                   | Admin | Delete user + DB data                                           |
| POST   | `/api/v1/admin/users/{id}/reset-password`    | Admin | Returns temp password                                           |
| PATCH  | `/api/v1/admin/users/{id}`                   | Admin | Update `role`, `email`. Cannot demote self. Username immutable. |
| POST   | `/api/v1/admin/reindex`                      | Admin | Force full reindex                                              |
| GET    | `/api/v1/admin/index/status`                 | Admin | Index queue status                                              |
| GET    | `/api/v1/admin/api-keys`                     | Admin | Shared keys (hints only, never the key)                         |
| POST   | `/api/v1/admin/api-keys`                     | Admin | Add/update shared key                                           |
| DELETE | `/api/v1/admin/api-keys/{id}`                | Admin | Delete shared key                                               |
| POST   | `/api/v1/admin/api-keys/{id}/test`           | Admin | Verify key against the provider                                 |
| GET    | `/api/v1/admin/embeddings/estimate`          | Admin | Migration cost/time estimate                                    |
| POST   | `/api/v1/admin/embeddings/migrate`           | Admin | Start migration                                                 |
| GET    | `/api/v1/admin/embeddings/status`            | Admin | Migration progress                                              |
| POST   | `/api/v1/admin/embeddings/cancel`            | Admin | Cancel migration                                                |
| GET    | `/api/v1/admin/dream/status`                 | Admin | Dream status all users                                          |
| POST   | `/api/v1/admin/dream/trigger/{user_id}`      | Admin | Trigger Dream for a specific user                               |
| GET    | `/api/v1/admin/mcp/servers`                  | Admin | List configured MCP servers + discovered tools (Phase 7)        |
| POST   | `/api/v1/admin/mcp/servers`                  | Admin | Add or update MCP server config                                 |
| DELETE | `/api/v1/admin/mcp/servers/{name}`           | Admin | Remove an MCP server                                            |
| POST   | `/api/v1/admin/mcp/servers/{name}/toggle`    | Admin | Enable/disable without removing config                          |
| POST   | `/api/v1/admin/mcp/servers/{name}/reconnect` | Admin | Force reconnect                                                 |
| POST   | `/api/v1/admin/maintain/run`                 | Admin | Run brain maintenance on demand                                 |
| GET    | `/api/v1/admin/maintain/report`              | Admin | Fetch latest maintenance report                                 |
| GET    | `/api/v1/admin/doctor`                       | Admin | System smoke test                                               |

> **Note:** MCP OAuth (`POST /mcp/oauth/register`, Phase 7 stub) is documented in REQ-1504B. MCP tool registry endpoints are listed under Admin above (Phase 7).

### 30A.14 Health + Metrics (4 endpoints — Phase 1)

| Method | Path       | Auth  | Notes                                                                                                                |
| ------ | ---------- | ----- | -------------------------------------------------------------------------------------------------------------------- |
| GET    | `/health`  | None  | Lightweight; alias for `/healthz`. Returns `setup_required` flag when no users exist.                                |
| GET    | `/healthz` | None  | API process up                                                                                                       |
| GET    | `/readyz`  | None  | All subsystems healthy (Postgres, pgvector, scheduler, watchdog, MCP HTTP). Used by load balancers.                  |
| GET    | `/metrics` | Admin | Prometheus-format metrics (request counts, latencies, embedding counts, job successes/failures, MCP calls per tool). |

`/health` response body:

```json
{
  "status": "ok | degraded | error",
  "setup_required": true,
  "version": "1.0.0",
  "database": "connected | error",
  "indexing": { "active": false, "current": null, "total": null }
}
```
When `setup_required: true`, the Phase 8 client renders the "Create Admin Account" form variant on the login page; otherwise the standard login form.

### 30A.15 Agent (2 endpoints — Phase 2)

| Method | Path                            | Auth | Notes                                                                          |
| ------ | ------------------------------- | ---- | ------------------------------------------------------------------------------ |
| POST   | `/api/v1/agent/approve`         | JWT  | Respond to a pending `tool_confirm` (approve/reject).                          |
| POST   | `/api/v1/agent/client-response` | JWT  | Client supplies data requested by a `client_request` (e.g. clipboard content). |

### 30A.16 Error response schema (all endpoints)

```json
{ "detail": "Human-readable error message", "code": "MACHINE_READABLE_CODE" }
```

| HTTP | Code               | Usage                                                     |
| ---- | ------------------ | --------------------------------------------------------- |
| 400  | `VALIDATION_ERROR` | Request body validation failed                            |
| 401  | `UNAUTHORIZED`     | Missing or invalid JWT/MCP token                          |
| 403  | `FORBIDDEN`        | Insufficient role                                         |
| 404  | `NOT_FOUND`        | Resource missing or hidden by RLS                         |
| 409  | `CONFLICT`         | Duplicate (e.g., username)                                |
| 429  | `RATE_LIMITED`     | Per-user rate limit. Body includes `retry_after_seconds`. |
| 500  | `INTERNAL_ERROR`   | Unexpected server error                                   |

### 30A.17 Capabilities (1 endpoint — Phase 1)

- `GET /api/v1/capabilities` — Returns server capability discovery payload (see Section 10.4).

---

## 30B. Streaming Protocol (WebSocket primary; SSE for chat completions)

> **Transport rule:** Real-time updates flow over a single per-user WebSocket. Streaming chat completions (token-by-token assistant output) flow over SSE on the dedicated `POST /api/v1/chat/completions` endpoint. The MCP HTTP transport is independent of both.

### 30B.1 WebSocket gateway

- **REQ-2760** A single per-user WebSocket MUST be established at `wss://{host}/api/v1/ws` after login.
- **REQ-2761** Authentication MUST occur via the access token sent as the first frame (`{"type":"auth","data":{"token":"..."}}`); the server MUST close the connection on invalid token.
- **REQ-2762** The WebSocket MUST carry: indexing progress events, vault health alerts, Dream status changes, scheduled job completions, MCP server state changes, system notifications, admin broadcasts.
- **REQ-2763** Frame envelope: `{"type":"<event_type>","data":{...}}`. Same shape as SSE events for symmetry.
- **REQ-2764** The server MUST send heartbeat pings every 30 seconds; clients MUST close and reconnect after 90 seconds with no traffic.
- **REQ-2765** Reconnection MUST use exponential backoff (initial 1s, cap 30s); on reconnect the client MUST re-fetch any state it cached.

### 30B.2 SSE on `POST /api/v1/chat/completions`

**Authentication:** The POST request body MAY include `access_token` as a fallback when header injection on streaming requests is inconvenient. The backend validates the token from either the `Authorization: Bearer` header or the body field before opening the stream.

**Token naming:** `access_jwt` and `access_token` refer to the same JWT access token. For SSE requests, the token MAY be supplied via `Authorization: Bearer <access_jwt>` header or as `access_token` in the request body.

```
data: {"type":"status","data":{"description":"Searching knowledge base...","done":false}}

data: {"type":"citations","data":{"sources":[{"page_id":"...","slug":"...","title":"...","score":0.92,"excerpt":"..."}]}}

data: {"type":"token","data":{"content":"Based on"}}
data: {"type":"token","data":{"content":" your notes"}}

data: {"type":"tool_start","data":{"tool":"ragSearch","input":{"query":"neural networks"}}}
data: {"type":"tool_result","data":{"tool":"ragSearch","elapsed_ms":340,"result_count":5}}

data: {"type":"tool_confirm","data":{"tool":"put_page","input":{"path":"/notes/new.md","content":"..."},"description":"Create new note: new.md","call_id":"uuid"}}

data: {"type":"client_request","data":{"request_id":"uuid","action":"read_clipboard","max_payload_bytes":5242880}}

data: {"type":"client_request","data":{"request_id":"uuid","action":"open_editor","path":"/notes/example.md"}}

data: {"type":"notification","data":{"title":"3 orphan notes detected","body":"Run maintain_run(kind=cleanup_orphans) to review.","severity":"info"}}

data: {"type":"done","data":{"usage":{"prompt_tokens":1200,"completion_tokens":450,"cost_usd":0.0034},"title":"Auto-generated title","suggested_tasks":[{"title":"Run orphan cleanup","action":"maintain_run","kind":"cleanup_orphans"}]}}
```

### 30B.3 Event types

`status`, `citations`, `token`, `tool_start`, `tool_result`, `tool_confirm`, `client_request`, `notification`, `done`, `error`.

- **`tool_confirm`** — emitted when the agent requests a write operation requiring approval. The client shows a confirmation modal. User response sent to `POST /api/v1/agent/approve` with `call_id` and `approved: true|false`.
- **`client_request`** — emitted when the agent needs data or action from the client. `action` field semantics:
  - `read_clipboard` — client reads system clipboard, normalises, and responds via `POST /api/v1/agent/client-response` within 10 seconds. See captureFromClipboard protocol in Section 30C.2.
  - `open_editor` — client opens the specified `path` in the Tiptap editor (or focuses if already open). **Fire-and-forget** — no response expected; client ignores `request_id`. If file missing, client shows toast "File not found: {path}".
- **`notification`** — emitted by the proactive background agent for vault health alerts, maintenance results, and indexing completion. Severities: `info`, `warning`, `action_required`. Phase 8 client renders as system notifications when window unfocused, toasts when focused.
- **`done`** — `title` field is set when the conversation title was auto-generated on first message (null otherwise).

### 30B.4 Citation marker scoping

Citation markers (`[1]`, `[2]`) are scoped per-message. Each assistant response cites only the RAG sources retrieved for that specific user message. Previous messages' citations are not re-referenced.

### 30B.5 Error handling

- SSE `error` event: `{"type":"error","data":{"code":"PROVIDER_ERROR","message":"OpenAI returned 429: rate limited","retryable":true}}`
  - `retryable: true` → client shows error with "Retry" button.
  - `retryable: false` → client shows error and closes stream.
- If the SSE connection drops (network, proxy timeout): the client MUST NOT auto-reconnect. The partial response is displayed with an inline "(Connection lost — response may be incomplete)" indicator and a "Retry" button that re-sends the last user message.
- The stream is not resumable — each `POST /api/v1/chat/completions` is self-contained.
- **Reverse-proxy configuration note:** Caddy/Nginx MUST disable response buffering for `/api/v1/chat/completions`. Caddy: `flush_interval -1`. Nginx: `proxy_buffering off`.

---

## 30C. Agent System — 22 Tools (detailed)

> **Companion to Section 17.** Section 17 enumerates the 22 tools and the brain-first prompt. This section adds: auto-approve vs confirmation classification, the clipboard-ingest cooperative protocol, per-mode tool availability, and proactive-mode behaviour.

### 30C.1 Tool classification

#### 30C.1.1 Auto-approve (read-only — no confirmation)

| #   | Tool             | Description                                 |
| --- | ---------------- | ------------------------------------------- |
| 1   | `search`         | Hybrid retrieval, synthesis off             |
| 2   | `query`          | Hybrid retrieval with synthesis + citations |
| 3   | `get_page`       | Read page by slug                           |
| 4   | `list_pages`     | List by type/tag/recency                    |
| 5   | `history`        | Page version list                           |
| 6   | `diff`           | Diff between two versions                   |
| 7   | `tags`           | Read or list tags                           |
| 8   | `backlinks`      | Pages linking to a slug                     |
| 9   | `graph_traverse` | Typed graph walk (read-only)                |
| 10  | `entity_get`     | Typed entity dossier                        |

#### 30C.1.2 Require user confirmation (write or external operations)

| #   | Tool                    | Description                                        |
| --- | ----------------------- | -------------------------------------------------- |
| 11  | `put_page`              | Create/update full page body                       |
| 12  | `update_compiled_truth` | Atomic rewrite of above-the-line content           |
| 13  | `append_timeline`       | Append a dated entry                               |
| 14  | `delete_page`           | Soft-delete (versioned)                            |
| 15  | `revert`                | Revert to an earlier version (re-chunks/re-embeds) |
| 16  | `entity_merge`          | Merge two entities (admin / owner only)            |
| 17  | `enrich_entity`         | Run tiered enrichment skill                        |
| 18  | `ingest`                | Auto-route to ingestion skill                      |
| 19  | `recipe_run`            | Run a data-research recipe                         |
| 20  | `skill_run`             | Execute a named skill                              |
| 21  | `jobs_submit`           | Submit a durable job                               |
| 22  | `maintain_run`          | Run brain maintenance on demand                    |

**Why some apparently-read-only operations require confirmation:** `enrich_entity` and `recipe_run` consume paid LLM credits and may make external network requests. `skill_run` and `jobs_submit` are general-purpose; they may invoke any combination of read and write operations. `maintain_run` audits and may auto-fix repairable defects.

### 30C.2 Clipboard-ingest cooperative protocol

**Note:** `captureFromClipboard` is **not** a standalone MCP tool — it is an SSE-mediated subroutine invoked by the `ingest` tool. The client cooperation described here applies when ingest detects clipboard content and needs the Phase 8 client to read and sanitise it before the agent confirms the write.

A read tool (technically auto-approve, but requires client cooperation):

```
1. Agent calls ingest() with clipboard content or image reference
2. Backend emits SSE: {"type":"client_request","data":{"request_id":"uuid","action":"read_clipboard"}}
3. Client (Phase 8) reads clipboard, normalises:
   - Plain text: trim, normalise line endings, truncate 500 KB
   - HTML:       DOMPurify sanitise, truncate 1 MB
   - URL:        validate HTTP(S), strip tracking params
   - Image:      resize if > 4096 px, compress ≤ 5 MB PNG, base64, strip EXIF
   - File path:  text only — client does NOT read file contents
4. Client POSTs to /api/v1/agent/client-response with the request_id
5. Server re-sanitises via nh3 (defence in depth — Section 30F), processes by type
6. Agent requests confirmation (tool_confirm) before creating any page
7. Timeout: 10 seconds → error + "Try pasting into chat instead"
```

Pre-Phase-8, the `ingest` tool returns `{ "error": "no_client_capability" }` when clipboard capture is needed and no Phase 8 client is connected.
- **REQ-2803A** When a client capability required by `client_request` is unavailable (no Phase 8 client connected), the server MUST return `capability_missing` and the agent/client MUST fall back to requesting the data directly from the user (e.g., "paste the content here").

### 30C.3 Per-mode tool availability (hardcoded v1.0)

| Mode         | Available tools                                                                   | Tool numbers  |
| ------------ | --------------------------------------------------------------------------------- | ------------- |
| **Ask**      | search, query, get_page, list_pages, backlinks, entity_get                        | #1–4, #8, #10 |
| **Write**    | search, query, get_page (RAG scoped to current page)                              | #1–3          |
| **Research** | All 22 built-in tools + all configured MCP tools                                  | #1–22 + MCP   |
| **Focus**    | Read-only query tools + entity_get + graph_traverse (RAG scoped to project)       | #1–4, #8–10   |
| **Custom**   | `agent_tools: true` → all 22 + MCP; `agent_tools: false` → read-only only (#1–10) | Configurable  |

Tool lists are hardcoded per mode in v1.0. Custom per-mode tool selection is deferred.

MCP tools (Phase 7) are added to all modes where `agent_tools: true`. MCP tool calls follow the same confirmation gate as built-in write tools, unless the admin has added a tool to the server's `always_allow` list. Modes with `agent_tools: false` (Ask, Write, Focus) never see MCP tools.

### 30C.4 Tool invocation: pipeline vs agent loop

Tools are invoked in two distinct ways:

1. **Pipeline invocation (always active):** The chat completion pipeline calls `search` and (Phase 4+) memory recall internally to build RAG context for every message, regardless of mode or `agent_enabled` flag. This is not visible as a tool call to the user — it is part of how the system builds context. This is why all modes benefit from hybrid search even when `agent_tools: false`.
2. **Agent loop invocation (Research mode and custom modes with `agent_tools: true`):** The LLM explicitly calls tools via the ReAct loop (Thought → Action → Observation). Tool calls are visible in the chat as `tool_start` / `tool_result` SSE events. Only modes with `agent_tools: true` AND `agent_enabled: true` activate the loop.

### 30C.5 Background agent (proactive mode, opt-in)

Runs via APScheduler:
1. Vault health check → notify if below threshold.
2. Orphan count exceeds threshold → suggest cleanup.
3. New pages without typed links → suggest connections.
4. Scheduled maintenance tasks (reconcile, etc.).
5. Memory Dream consolidation (nightly).
6. System health snapshot every 15 minutes → metrics endpoint.

---

## 30D. Memory Dream Consolidation System

> **Companion to Section 22.** Section 22 enumerates the brain maintenance loop; this section specifies the 4-phase nightly Memory Dream cycle that operates on the user's `memories` table.

### 30D.1 Problem statement

After 10–15 sessions, accumulated memories become noise: relative dates are meaningless out of context, contradictions co-exist, references to deleted pages persist. Memory Dream is the consolidation layer that prevents this rot.

### 30D.2 4-phase nightly cycle

**Phase 1 — Orientation:** Count active memories, age distribution, flag relative time references, detect broken page references.

**Phase 2 — Gather Signal:** LLM-targeted search for corrections, key decisions, recurring patterns, contradicted facts. Recorded with `purpose: 'dream'` in `llm_usage`.

**Phase 3 — Consolidation** (each action logged to `dream_audit_log`):
- Relative → absolute timestamps.
- Contradiction deletion (keep newer, archive older).
- Stale pruning (deleted page refs, 90+ days with zero recalls).
- Duplicate merge.
- Preference resolution (last explicit statement wins).

**Phase 4 — Prune & Index:** Archive excess over 200 active. Re-embed modified memories. Generate consolidation summary.

### 30D.3 Trigger conditions
- **Automatic:** 24+ hours AND 5+ sessions since last cycle.
- **Manual:** admin endpoint (`POST /api/v1/admin/dream/trigger/{user_id}`), or user's `POST /api/v1/memories/dream/run`.
- **Checked every hour** by APScheduler.
- **One user at a time** (advisory lock).
- Uses **cheapest model tier** (e.g., `gpt-4o-mini`, `claude-haiku-4-5`).
- **Skips users with fewer than 20 memories.**

### 30D.4 Concurrency guard

```python
# PostgreSQL advisory lock prevents overlapping runs across all workers
pg_try_advisory_lock(hashtext('dream'))
```

The advisory-lock approach extends to all scheduled tasks (reconciliation, system health snapshots, proactive agent checks, fleeting-note expiry) when running with multiple uvicorn workers. See Section 29.

### 30D.5 Audit, restore, and observability

- **REQ-2780** Every consolidation action MUST write a row to `dream_audit_log` (user_id, dream_run_at, phase, action, memory_id, old_content, new_content, reason).
- **REQ-2781** Archived memories MUST remain restorable for 90 days; users MUST be able to restore via the user-facing memory tab.
- **REQ-2782** Dream status (last run, next eligible run, last consolidation summary) MUST be exposed via `GET /api/v1/memories/dream/status` and the WebSocket gateway.

---

## 30E. Zettelkasten Workflows

The Zettelkasten model in Smart Copilot rests on three page types — fleeting, literature, permanent — plus map-of-content (MOC) pages. The compiled-truth + timeline page schema (Section 14) is orthogonal to these types; both literature and permanent pages use the schema.

### 30E.1 Workflow A — Import external document

1. User uploads via chat or `POST /api/v1/pages/upload`.
2. `media-ingest` skill extracts text (HTML: nh3 → readability-lxml; PDF: PyMuPDF; DOCX: python-docx).
3. Saved as a literature page with full source citation.
4. Server offers: "This page is {N} words — split into atomic Zettel?"
5. If accepted → `splitter` skill runs (H1 > H2 > H3 hierarchy; atomic permanents with source backlinks).
6. Literature page is updated with links to its children.
7. (Phase 8) client opens the literature page in the Tiptap editor.

### 30E.2 Workflow B — Chat to Zettel

1. User chats normally.
2. User says "@zettel save this".
3. Agent distils to atomic format.
4. `tool_confirm` modal appears with the proposed Zettel preview.
5. Accept → `put_page` writes + indexes immediately + extracts typed links.

### 30E.3 Workflow C — Convert existing long page

1. Command palette / explicit ask: "Split this page" — or auto-offered when `single_chunk_threshold` is exceeded.
2. Same splitter flow as Workflow A step 5.
3. Original becomes literature page (default), is archived, or is deleted (confirmation required).

### 30E.4 Fleeting page expiry

- **REQ-2790** Fleeting pages whose `created_at` is older than `fleeting_expiry_days` (default 30) MUST be moved to the archive folder by the reconciler during its periodic run.
- **REQ-2791** The page's `note_type` frontmatter MUST be updated to `archived_fleeting`; the database `pages.note_type` column MUST be updated accordingly.
- **REQ-2792** `archived_fleeting` pages MUST be removed from all RAG indexes (no chunks, no embeddings) but MUST remain on disk in the archive folder.
- **REQ-2793** The file move MUST be recorded in the operation log for undo support.
- **REQ-2794** The reconciler MUST process expiry once per `vault.reconciliation_interval_hours` (default 6 hours).
- **REQ-2795** Files MUST NEVER be auto-deleted — only explicit user action or the `maintain_run(kind=cleanup_orphans)` tool removes files permanently.

---

## 30F. HTML Sanitisation Strategy

Defence-in-depth: all untrusted HTML is sanitised on both the client (when present) and on the server. The server-side pass is the security guarantee — clients are not trusted.

### 30F.1 Client-side: DOMPurify (Phase 8 Electron renderer)

```typescript
import DOMPurify from 'dompurify';

const SANITIZE_CONFIG: DOMPurify.Config = {
  ALLOWED_TAGS: ['h1','h2','h3','h4','h5','h6','p','blockquote','pre',
    'ul','ol','li','a','em','strong','code','table','thead','tbody','tr','th','td','img','br'],
  ALLOWED_ATTR: ['href','src','alt','title','colspan','rowspan'],
  ALLOW_DATA_ATTR: false, ALLOW_ARIA_ATTR: false, ALLOW_UNKNOWN_PROTOCOLS: false,
};

DOMPurify.addHook('afterSanitizeAttributes', (node: Element) => {
  if (node.tagName === 'A') {
    node.setAttribute('rel', 'noopener noreferrer');
    const href = node.getAttribute('href');
    if (href && !/^(https?:|mailto:|#)/i.test(href)) node.removeAttribute('href');
  }
  if (node.tagName === 'IMG') {
    const src = node.getAttribute('src');
    if (src && !/^https?:/i.test(src)) node.removeAttribute('src');
  }
});
```

### 30F.2 Server-side: nh3 (Python, defence-in-depth — required for all flows)

```python
import nh3

html_cleaner = nh3.Cleaner(
    tags={"h1","h2","h3","h4","h5","h6","p","blockquote","pre",
          "ul","ol","li","a","em","strong","code","table","thead","tbody","tr","td","th","img"},
    attributes={"a": {"href","title"}, "img": {"src","alt","title","width","height"},
                "td": {"colspan","rowspan"}, "th": {"colspan","rowspan","scope"}},
    clean_content_tags={"script","style","iframe","object","embed","noscript"},
    url_schemes={"http","https","mailto"},
    link_rel="noopener noreferrer",
    strip_comments=True,
)
```

### 30F.3 Flow by source

```
Clipboard paste (Phase 8) → DOMPurify (client) → API → nh3 (server) → readability-lxml → markdown
URL capture               →                     → API → nh3 (server) → readability-lxml → markdown
HTML upload               →                     → API → nh3 (server) → readability-lxml → markdown
MCP-supplied content      →                     → MCP → nh3 (server) → markdown (no readability pass)
```

- **REQ-2800** All HTML content from any external source (clipboard via client, URL fetch, file upload, MCP tool result) MUST pass through nh3 server-side before being persisted, embedded, or returned to the LLM.
- **REQ-2801** nh3 sanitisation MUST run with the configuration in REQ-2802 (above) and MUST NOT be bypassed even when the source is a "trusted" MCP server.
- **REQ-2802** Sanitised HTML MUST then be converted to markdown for storage; HTML MUST NOT be stored verbatim in the `pages.compiled_truth` or `pages.timeline` columns.

---

## 30G. Indexing Strategy

> **Companion to Sections 7 (Data Model) and 16 (Hybrid RAG).** Section 16 specifies the retrieval pipeline; this section specifies how content gets into the indexes — chunking, contextual enrichment, content/enrichment hashes, and the cascading re-enrichment rule.

### 30G.1 Note-type gating

The indexer checks `pages.note_type` before chunking. Note types `archived_fleeting` and `skill` skip the enrich → chunk → embed pipeline entirely — the pages row is created/updated (with frontmatter, path, content_hash) but no chunks rows are produced. All other note types proceed through the full pipeline.

### 30G.2 Chunking

- **Atomic notes** (≤ `single_chunk_threshold` tokens, default 600): embedded as a single chunk. No splitting. The enrichment prefix is prepended; the entire page is embedded as one unit. This covers ~90% of permanent Zettelkasten notes.
- **Long notes** (> `single_chunk_threshold` tokens): recursive character splitting with markdown-aware separators.

**Separator hierarchy:** `\n## ` → `\n### ` → `\n\n` → `\n- ` → `\n` → `. ` → ` `

| Param                  | Default            | Configurable via                      |
| ---------------------- | ------------------ | ------------------------------------- |
| Chunk size             | 512 tokens         | `rag.chunking.chunk_size_tokens`      |
| Overlap                | 64 tokens (~12.5%) | `rag.chunking.chunk_overlap_tokens`   |
| Minimum chunk          | 50 tokens          | `rag.chunking.min_chunk_tokens`       |
| Boundary respect       | paragraph          | `rag.chunking.respect_boundaries`     |
| Frontmatter            | strip              | `rag.chunking.frontmatter_handling`   |
| Single-chunk threshold | 600 tokens         | `rag.chunking.single_chunk_threshold` |

Code blocks and blockquotes MUST NEVER be split mid-block.

Each chunk receives the same contextual enrichment prefix. For long notes, chunks also receive a section header trail (e.g., `Section: Chapter 3 > Key Findings`) when headers are present.

**Frontmatter handling:** YAML frontmatter is stripped before chunking. Frontmatter fields are used only for contextual enrichment (prepended separately) and metadata columns (for filtering). `[[Wikilinks]]` in the body are resolved to plain-text titles before embedding — the bracket syntax adds no semantic value.

### 30G.3 Cascading re-enrichment

`pages.content_hash` is xxhash (XXH64) of the raw file bytes (full file including frontmatter YAML), stored as 16-character hex. `pages.enrichment_hash` is xxhash (XXH64) of the concatenated enrichment inputs (`title + folder + tags + sorted(backlink_titles) + sorted(outlink_titles)`), stored as 16-character hex. This definition is normative for pages.content_hash throughout the system.

**Flow on file change:**
1. Compute `content_hash`.
2. Both unchanged → skip.
3. `content_hash` changed → full re-process (parse, enrich, chunk, embed).
4. `content_hash` same, `enrichment_hash` changed → re-enrich + re-embed existing chunks (no chunk replacement).

**Cascade:** After indexing any page, check whether its outgoing wikilinks changed. If yes, mark linked pages for `enrichment_hash` recalculation. **Depth limited to 1 hop** to bound the cascade.

### 30G.4 Chunk replacement (atomic)

Replacement is done as DELETE-then-INSERT inside a SAVEPOINT. If embedding fails midway, the SAVEPOINT rolls back and the previous chunks remain. The page is never unsearchable mid-update.

For enrichment-only updates: `UPDATE` existing rows' `enriched_content` and `embedding` in place — no DELETE.

### 30G.5 Hybrid RAG query reference

The complete hybrid search query, fusing vector + BM25 + typed-graph reachability via Reciprocal Rank Fusion (k = 60), lives in `server/app/rag/queries.py`. RLS automatically scopes results to the current user's `private` + `shared` rows. Parameters:

| Param | Meaning                | Default                   |
| ----- | ---------------------- | ------------------------- |
| `$1`  | Query embedding vector | from embedder             |
| `$2`  | Candidate pool size    | 50                        |
| `$3`  | Allowed page types     | per intent                |
| `$4`  | Raw query text (BM25)  | input                     |
| `$5`  | Seed page UUID (graph) | NULL when no context page |
| `$6`  | Max graph hops         | 3 (cap 8)                 |
| `$7`  | Final top_k            | 10                        |

When `$5` is NULL, the graph CTE returns zero rows and only vector + BM25 contribute. This happens when no page is open in the editor, the user is in a new conversation with no context, or the mode does not provide a seed.

**RRF k = 60:** standard from Cormack et al. 2009. Higher k reduces the impact of rank-position differences; lower k amplifies them. 60 is the documented safe default. *(See DEC-001 in Appendix D for rationale and testing implications.)*

---

## 30H. Server Configuration Reference

File: `/config/settings.yaml` — only non-secret config. API keys live in the `provider_keys` table (Section 7), not in this file or environment variables.

```yaml
server:
  host: 0.0.0.0
  port: 8000
  log_level: info
  cors_origins: ["http://localhost:*", "app://."]
  rate_limit:
    max_requests_per_minute: 30
    max_agent_tool_calls_per_minute: 60

vault:
  base_path: /vaults
  watch_debounce_ms: 300
  reconciliation_interval_hours: 6
  health_weights:
    orphan: 0.4
    density: 0.3
    type_coverage: 0.2
    freshness: 0.1
  health_thresholds:
    green: 0.8
    yellow: 0.5

rag:
  context_enrichment: true
  top_k: 10
  graph_max_hops: 3
  embedding_model: openai/text-embedding-3-small
  embedding_dimensions: 1536
  chunking:
    chunk_size_tokens: 512
    chunk_overlap_tokens: 64
    min_chunk_tokens: 50
    respect_boundaries: paragraph
    frontmatter_handling: strip
    single_chunk_threshold: 600

llm:
  default_chat_tier: balanced
  default_temperature: 0.7
  default_max_tokens: 4096
  dream_tier: cheap
  tiers:
    cheap:
      - openai/gpt-4o-mini
      - anthropic/claude-haiku-4-5-20251001
    balanced:
      - openai/gpt-4o
      - anthropic/claude-sonnet-4-20250514
      - gemini/gemini-2.5-pro
    strong:
      - anthropic/claude-opus-4-7
      - openai/gpt-4o
  embedding_models:
    - { id: openai/text-embedding-3-small, display_name: OpenAI Embedding Small, dimensions: 1536 }
    - { id: openai/text-embedding-3-large, display_name: OpenAI Embedding Large, dimensions: 3072 }
    - { id: ollama/nomic-embed-text, display_name: Nomic Embed (local), dimensions: 768 }
  local_endpoints: []  # Ollama or OpenAI-compatible servers; { name, base_url, model_prefix }

zettelkasten:
  note_types:
    infer_from_folder: true
    fleeting_folders: ["/inbox/", "/fleeting/"]
    project_folders: ["/projects/", "/journal/"]
    fleeting_tags: ["#fleeting", "#inbox"]
    project_tags: ["#project", "#journal"]
    fleeting_expiry_days: 30
  splitter:
    auto_offer_split: true
    min_word_count: 1000
    original_note_handling: keep    # keep | archive | delete
    archive_folder: /archive/
  link_suggestions: { min_confidence: 0.7, max_suggestions: 10 }
  id_format: { use_timestamp: true, separator: "" }

agent:
  max_tool_calls_per_turn: 10
  confirm_before_write: true
  confirm_before_split: true
  confirm_before_organize: true
  confirm_before_web_search: true
  proactive_mode: false
  maintenance_schedule: weekly
  max_skill_tokens: 2000
  skill_cache_ttl_seconds: 300

memory:
  auto_extract: true  # When true, on every /conversations PATCH (user sends a message) the server auto-extracts factual claims, preferences, and decisions into the memories table via the memory/extractor.py module. Gated by the user's memory.auto_extract config.
  max_memories_per_user: 500
  max_active_memories: 200
  dream:
    enabled: true
    min_hours_between_runs: 24
    min_sessions_between_runs: 5
    check_interval_minutes: 60
    stale_threshold_days: 90
    min_memories_to_run: 20

web_search:
  free_provider: duckduckgo
  page_reader: jina
  max_results: 5
  cross_reference_vault: true
  wikipedia_lookup: true

chat_history:
  vault_export_folder: "Smart Copilot"
  filename_format: "YYYY-MM-DD HH-mm {id}"
  include_timestamps: false
  project_subfolder: true
  max_conversations_per_user: 0   # 0 = unlimited

auth:
  allow_registration: false
  first_user_is_admin: true
  jwt_expiry_minutes: 1440
  jwt_refresh_expiry_days: 30

mcp:
  enabled: true
  http_port: 8787
  stdio_enabled: true
  connection_timeout_seconds: 10
  tool_call_timeout_seconds: 60
  health_check_interval_seconds: 60
  max_retries: 5
  servers: {}    # External MCP server registry — typically managed via admin REST, not YAML
```

### 30H.1 Configuration scopes

- **Server-only (not user-overridable):** `server.*`, `vault.*`, `rag.embedding_model`, `rag.embedding_dimensions`, `rag.chunking.*`, `llm.local_endpoints`, `llm.dream_tier`, `auth.*`, `memory.dream.*`, `chat_history.max_conversations_per_user`, `mcp.*`.
- **Admin-configurable via admin REST (not just YAML):** `rag.chunking.*` (changes trigger a confirmed full reindex), `vault.health_weights` and `vault.health_thresholds`, `server.rate_limit.*`.
- **User-overridable via `user_settings.settings` JSONB:** everything else (RAG weights, top_k, temperature, zettelkasten preferences, agent confirmation toggles, mode definitions, etc.).

### 30H.2 `user_settings.settings` JSONB — key reference

The following keys are stored in the `user_settings.settings` JSONB column. All are optional; if absent, the server default from `settings.yaml` applies.

| Key                                | Type    | Default           | Notes                                                                          |
| ---------------------------------- | ------- | ----------------- | ------------------------------------------------------------------------------ |
| `quick_phrases`                    | array   | `[]`              | Array of `{id, title, text}`. Max 20.                                          |
| `mcp_default_mode`                 | string  | `"auto"`          | `'disable'` \| `'auto'` \| `'manual'`. Default MCP mode for new conversations. |
| `profile_bio`                      | string  | `""`              | Max 500 chars.                                                                 |
| `notification_sounds`              | boolean | `true`            |                                                                                |
| `show_indexing_progress`           | boolean | `true`            | Footer status bar visibility.                                                  |
| `date_format`                      | string  | `"YYYY-MM-DD"`    | `'YYYY-MM-DD'` \| `'DD/MM/YYYY'` \| `'MM/DD/YYYY'`.                            |
| `language`                         | string  | `"en"`            | UI language. v1.0: `'en'` only.                                                |
| `chat_history.include_timestamps`  | boolean | `false`           | Per-message timestamps in vault exports.                                       |
| `chat_history.project_subfolder`   | boolean | `true`            | Organise exports into workspace subfolders.                                    |
| `chat_history.vault_export_folder` | string  | `"Smart Copilot"` | Folder name within vault for exported conversations.                           |
| `ai_persona_name`                  | string  | `"Smart Copilot"` | Agent name shown in UI.                                                        |
| `default_chat_mode`                | string  | `"ask"`           |                                                                                |
| `default_chat_model`               | string  | (server default)  |                                                                                |
| `vision_model`                     | string  | `null`            |                                                                                |
| `llm.temperature`                  | float   | `0.7`             |                                                                                |
| `llm.max_tokens`                   | int     | `4096`            |                                                                                |
| `llm.reasoning_effort`             | string  | `null`            | Provider-specific.                                                             |

---

## 30I. Docker Deployment

> **Companion to Section 29 (Deployment).** Section 29 enumerates the deployment requirements; this section provides the canonical Dockerfile, supervisord.conf, and run commands.

### 30I.1 Dockerfile

```dockerfile
FROM pgvector/pgvector:pg16 AS base

RUN apt-get update && apt-get install -y \
    python3.12 python3.12-venv python3-pip supervisor curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY server/ /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/ /app/scripts/
RUN chmod +x /app/scripts/wait-for-pg.sh

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

VOLUME ["/var/lib/postgresql/data", "/vaults", "/config"]
EXPOSE 8000 8787

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
```

**MCP stdio servers (Phase 7, optional):** If the admin configures external MCP servers that use npm/npx (e.g., `npx @modelcontextprotocol/server-filesystem`), the Docker image must include Node.js. Two approaches:
1. **Include by default:** Add `apt-get install -y nodejs npm` to the Dockerfile. Adds ~80 MB to image size.
2. **Document as optional:** Keep the base image lean. Document that admins extend the image: `FROM smart-copilot:latest` → `RUN apt-get install -y nodejs npm`.

Recommended: **Option 2.** Most MCP servers can also be installed globally and referenced by absolute path, avoiding `npx`. Python-based MCP servers work without Node.js.

### 30I.2 supervisord.conf

```ini
[supervisord]
nodaemon=true
user=root

[program:postgresql]
command=/usr/lib/postgresql/16/bin/postgres -D /var/lib/postgresql/data -c config_file=/etc/postgresql/postgresql.conf
user=postgres
autostart=true
autorestart=true
priority=10

[program:fastapi]
command=/app/scripts/wait-for-pg.sh
directory=/app
autostart=true
autorestart=true
priority=20

[program:mcp-http]
command=python3 -m smartcopilot.mcp.serve --http --port 8787
directory=/app
autostart=true
autorestart=true
priority=30

[program:apscheduler]
command=python3 -m smartcopilot.scheduler.run
directory=/app
autostart=true
autorestart=true
priority=40

[program:watchdog]
command=python3 -m smartcopilot.vault.watcher
directory=/app
autostart=true
autorestart=true
priority=50
```

### 30I.3 wait-for-pg.sh

```bash
#!/bin/bash
set -e
echo "Waiting for PostgreSQL..."
until pg_isready -h localhost -p 5432 -U postgres -q; do sleep 1; done
echo "Running migrations..."
python3 -m alembic upgrade head
echo "Starting FastAPI..."
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

**Worker configuration note:** `--workers 2` is safe because each uvicorn worker runs an independent asyncpg connection pool. The RLS `SET / RESET app.current_user_id` operates per-connection within each worker's pool — no cross-worker leakage. Any in-memory caches (e.g., a vault path → user/namespace map) are rebuilt independently per worker.

**APScheduler and multi-worker:** APScheduler MUST be initialised in only ONE worker process to prevent duplicate job execution. Two approaches:
1. **Preferred:** Run APScheduler in a dedicated supervisord program (as shown in `supervisord.conf` above), separate from uvicorn workers.
2. **Alternative:** Use `pg_try_advisory_lock` at the start of every scheduled job. The first worker to acquire the lock runs the job; the others skip.

The advisory-lock approach is already used for Memory Dream (Section 30D) and SHOULD be extended to all scheduled tasks: reconciliation, system health snapshots, proactive agent checks, fleeting-page expiry.

### 30I.4 Run commands

```bash
# Generate Fernet key (store this in a password manager — losing it makes encrypted keys unrecoverable)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Standard deployment (bundled Postgres)
docker run -d --name smart-copilot \
  -p 8000:8000 -p 8787:8787 \
  -v smart-copilot-data:/var/lib/postgresql/data \
  -v /path/to/vaults:/vaults \
  -e SMARTCOPILOT_FERNET_KEY=your-key \
  -e POSTGRES_PASSWORD=$(openssl rand -base64 32) \
  -e SMARTCOPILOT_HOST_URL=https://copilot.example.com \
  smart-copilot:latest

# External PostgreSQL
docker run -d --name smart-copilot \
  -p 8000:8000 -p 8787:8787 \
  -v /path/to/vaults:/vaults \
  -e EXTERNAL_DB=true \
  -e DATABASE_URL=postgresql+asyncpg://copilot:pass@pg-host:5432/copilot \
  -e SMARTCOPILOT_FERNET_KEY=your-key \
  -e SMARTCOPILOT_HOST_URL=https://copilot.example.com \
  smart-copilot:latest
```

---

## 30J. File Structure Reference

> Authoritative layout for the monorepo. Aligns with REQ-120 (pnpm workspaces), REQ-121 (`server/app/` src-style with plain domain-named files), REQ-124 (`clients/desktop/`).

### 30J.1 Backend (`server/`)

```
server/
├── Dockerfile
├── supervisord.conf
├── requirements.txt
├── pyproject.toml
├── alembic.ini
├── alembic/versions/
├── scripts/wait-for-pg.sh
├── static/                          # built web client bundle (output of pnpm build:web)
└── app/                              # src-style layout, plain domain-named files (REQ-121)
    ├── main.py                       # FastAPI app, startup validation
    ├── config.py                     # Pydantic settings from YAML + env
    ├── dependencies.py               # get_db_session (RLS-aware), get_current_user, require_admin
    ├── encryption.py                 # Fernet encrypt/decrypt
    ├── routes/                       # thin routes, transport-specific
    │   ├── auth.py
    │   ├── chat.py                   # SSE streaming
    │   ├── conversations.py
    │   ├── search.py
    │   ├── pages.py
    │   ├── vault.py
    │   ├── agent.py                  # client-response endpoint
    │   ├── web_search.py
    │   ├── memories.py
    │   ├── projects.py
    │   ├── models.py
    │   ├── usage.py
    │   ├── settings.py
    │   ├── admin.py
    │   ├── mcp_admin.py              # MCP server registry CRUD
    │   ├── ws.py                     # WebSocket gateway
    │   └── health.py
    ├── services/                     # transport-agnostic; called by routes AND mcp/server.py
    │   ├── page_service.py
    │   ├── chat_service.py
    │   ├── search_service.py
    │   ├── vault_service.py
    │   ├── memory_service.py
    │   ├── enrichment_service.py
    │   └── admin_service.py
    ├── models/                       # SQLAlchemy models (PascalCase classes per saved convention)
    │   ├── user.py
    │   ├── session.py
    │   ├── mcp_token.py
    │   ├── provider_key.py
    │   ├── vault.py
    │   ├── page.py
    │   ├── page_version.py
    │   ├── chunk.py
    │   ├── entity.py
    │   ├── link.py
    │   ├── timeline_event.py
    │   ├── tag.py
    │   ├── job.py
    │   ├── audit_log.py
    │   ├── skill.py
    │   ├── recipe.py
    │   ├── eval_candidate.py
    │   ├── memory.py
    │   ├── dream_audit_log.py
    │   ├── project.py
    │   ├── operation_log.py
    │   ├── llm_usage.py
    │   ├── index_event.py
    │   └── system_config.py
    ├── schemas/                      # Pydantic v2 — Request / Response / Create / Update suffixes
    │   ├── auth.py
    │   ├── chat.py
    │   ├── search.py
    │   ├── page.py
    │   ├── conversation.py
    │   ├── vault.py
    │   ├── memory.py
    │   ├── project.py
    │   ├── usage.py
    │   ├── health.py
    │   ├── admin.py
    │   ├── settings.py
    │   ├── mcp.py
    │   └── common.py
    ├── rag/
    │   ├── engine.py                 # HybridRAGEngine
    │   ├── context_enricher.py
    │   ├── intent_classifier.py
    │   ├── embedder.py               # LiteLLM aembedding wrapper + batching
    │   ├── chunker.py
    │   └── queries.py                # SQL: hybrid search + RRF
    ├── vault/
    │   ├── registry.py               # VaultRegistry: in-memory path → (user_id, namespace)
    │   ├── watcher.py                # watchdog → loop.call_soon_threadsafe()
    │   ├── parser.py                 # markdown + frontmatter + compiled-truth/timeline split
    │   ├── indexer.py                # IndexQueue: enrich → embed → upsert
    │   ├── link_extractor.py         # zero-LLM auto-link extraction (Section 15)
    │   ├── link_graph.py             # recursive CTE traversal, orphan/hub scoring
    │   ├── link_refactorer.py        # rename / move with link rewrite
    │   ├── operation_log.py          # multi-step undo
    │   └── reconciler.py             # 6-hourly drift fix; fleeting expiry
    ├── agent/
    │   ├── runner.py                 # ReAct loop: Thought → Action → Observation
    │   ├── tools.py                  # 22 built-in tool implementations
    │   ├── prompts.py                # brain-first system prompt + per-mode bundles
    │   └── scheduler.py              # APScheduler integration
    ├── skills/
    │   ├── runtime.py                # SKILL.md loader, trigger matching, caching
    │   ├── resolver.py               # RESOLVER.md dispatcher (system + user namespace)
    │   ├── conventions.py            # quality.md, brain-first.md, etc.
    │   └── registry.py               # default-skill-pack install
    ├── mcp/
    │   ├── server.py                 # MCP server (stdio + Streamable HTTP)
    │   ├── tools.py                  # tool exposure: brain.* / enrich.* / recipe.* / skill.* / jobs.* / maintain.*
    │   ├── client.py                 # MCP CLIENT for external server registry (Phase 7)
    │   ├── client_registry.py        # ToolRegistry: merges built-in + external MCP tools
    │   └── health.py                 # health-check loop, reconnection backoff
    ├── llm/
    │   ├── gateway.py                # LiteLLM wrapper
    │   ├── router.py                 # cheap/balanced/strong tier routing
    │   ├── key_resolver.py           # user → shared → error + key_type tracking
    │   └── callbacks.py              # cost tracking → llm_usage
    ├── memory/
    │   ├── manager.py
    │   ├── extractor.py
    │   ├── importer.py
    │   ├── exporter.py
    │   └── dream.py                  # 4-phase nightly consolidation (Section 30D)
    ├── ingest/                       # ingestion skills' deterministic helpers
    │   ├── idea.py                   # links / articles / tweets
    │   ├── media.py                  # video / audio / PDF / screenshots / repos
    │   └── meeting.py                # transcripts
    ├── enrich/
    │   ├── tier.py                   # Tier 1/2/3 routing
    │   ├── alias.py                  # alias dedup
    │   └── provider.py               # LinkedIn-style external lookups (delegates to skills for actual lookup logic)
    ├── websearch/
    │   ├── engine.py
    │   ├── duckduckgo.py
    │   ├── jina_reader.py
    │   ├── wikipedia.py
    │   └── cross_ref.py
    ├── zettelkasten/
    │   ├── splitter.py
    │   ├── moc_generator.py
    │   ├── orphan_detector.py
    │   └── organizer.py
    ├── documents/
    │   ├── pdf.py                    # PyMuPDF
    │   ├── docx.py                   # python-docx
    │   └── html.py                   # nh3 → readability-lxml → markdown
    ├── sanitizer/
    │   └── html.py                   # nh3 config (Section 30F)
    ├── auth/
    │   ├── jwt.py
    │   ├── password.py               # argon2-cffi
    │   ├── mcp_token.py
    │   └── middleware.py             # OperationContext construction
    └── tests/
        ├── unit/
        ├── integration/
        ├── rls/                      # RLS isolation tests
        └── fixtures/
```

### 30J.2 Frontend (`clients/desktop/` — Phase 8)

```
clients/desktop/
├── forge.config.ts
├── vite.config.ts
├── package.json
├── tsconfig.json
└── src/
    ├── main/
    │   ├── main.ts
    │   ├── tray.ts
    │   ├── windows.ts
    │   ├── global-shortcut.ts
    │   ├── auto-launch.ts
    │   ├── ipc.ts
    │   ├── export.ts                 # Obsidian export IPC
    │   └── local-store.ts            # electron-store wrapper
    ├── renderer/
    │   ├── index.html
    │   ├── main.tsx
    │   ├── App.tsx
    │   ├── api/
    │   │   ├── client.ts
    │   │   ├── generated/            # output of `pnpm codegen` from openapi.json
    │   │   ├── ws.ts                 # WebSocket gateway client
    │   │   └── sse.ts                # SSE chat-completion client
    │   ├── views/
    │   │   ├── ChatView.tsx
    │   │   ├── EditorView.tsx
    │   │   ├── SettingsView.tsx
    │   │   ├── AdminView.tsx
    │   │   ├── LoginView.tsx
    │   │   ├── DashboardView.tsx
    │   │   └── PasswordChangeView.tsx
    │   ├── components/
    │   │   ├── chat/
    │   │   ├── editor/
    │   │   ├── floating/              # QuickChat widget, notification popups
    │   │   ├── intelligence/          # Vault intelligence widgets (orphan counts, hub detection, suggestion chips)
    │   │   ├── sidebar/              # VaultSidebar, TreeView, FileContextMenu
    │   │   ├── admin/
    │   │   ├── dashboard/            # DashboardView widgets (usage stats, vault health, cost breakdowns)
    │   │   ├── memory/
    │   │   └── shared/
    │   ├── modals/
    │   ├── contexts/
    │   ├── hooks/
    │   ├── utils/
    │   │   ├── sanitizer.ts          # DOMPurify config (Section 30F.1)
    │   │   └── clipboard.ts          # ClipboardHandler
    │   └── styles/                   # CSS modules with .sc- prefix
    ├── quickchat/                    # tray Quick Chat window
    │   ├── index.html
    │   ├── quickchat.tsx
    │   └── QuickChatView.tsx
    ├── platform/                     # browser/Electron abstraction
    │   ├── types.ts
    │   ├── electron.ts
    │   └── web.ts
    └── shared/
        ├── types.ts
        └── constants.ts
```

### 30J.3 Skills (`/etc/smartcopilot/skills/` and per-user)

```
/etc/smartcopilot/                              # system namespace (REQ-1400)
├── skills/
│   ├── RESOLVER.md
│   ├── conventions/
│   │   ├── quality.md
│   │   ├── brain-first.md
│   │   ├── model-routing.md
│   │   ├── test-before-bulk.md
│   │   └── cross-modal.yaml
│   └── <skill-name>/
│       ├── SKILL.md                            # YAML frontmatter + body (REQ-1420)
│       ├── code/                               # optional deterministic helpers
│       ├── tests/
│       │   ├── unit/
│       │   ├── integration/
│       │   └── resolver-trigger/
│       └── evals/
├── clients/                                    # client integration kit (Section 18A)
│   ├── claude-desktop/
│   ├── hermes/
│   │   └── skills/                             # Hermes-side skill pack (REQ-1502G)
│   └── generic-mcp/
└── recipes/                                    # data-research recipes (Section 21)

/vaults/private/{username}/skills/              # per-user override namespace (REQ-1401)
└── RESOLVER.md                                 # chains to system RESOLVER.md (REQ-1402)
```

---

## 30K. Non-Functional Requirements & Success Metrics

### 30K.1 Performance targets

| Metric                                | Target               |
| ------------------------------------- | -------------------- |
| Chat response start (first SSE token) | < 500 ms             |
| RAG search latency (hybrid)           | < 300 ms             |
| Bulk index 1000 pages                 | < 5 minutes          |
| Watcher → indexed                     | < 5 seconds          |
| MCP tool call (read)                  | < 200 ms server-side |
| WebSocket round-trip (notification)   | < 100 ms             |

### 30K.2 Scale targets

| Metric                    | Target         |
| ------------------------- | -------------- |
| Concurrent users          | 3–10           |
| Pages per user            | 500–5,000      |
| Active memories per user  | ≤ 200          |
| Max memories per user     | 500            |
| Total chunks per instance | 50,000–500,000 |

### 30K.3 Reliability

| Metric                     | Target                  |
| -------------------------- | ----------------------- |
| Container restart recovery | < 30 seconds            |
| Index reconciliation       | every 6 hours           |
| Memory Dream concurrency   | max 1 per advisory lock |
| Failed migration           | aborts boot (REQ-2530)  |

### 30K.4 Security

| Requirement             | Implementation                                                                     |
| ----------------------- | ---------------------------------------------------------------------------------- |
| Per-user data isolation | RLS on all multi-tenant tables (REQ-111, REQ-330)                                  |
| Provider-key encryption | Fernet AES-128 at rest (REQ-009, REQ-110)                                          |
| MCP token storage       | SHA-256 hash; plaintext returned exactly once (REQ-411)                            |
| Password storage        | argon2-cffi; mem ≥ 64 MiB, iter ≥ 3 (REQ-400)                                      |
| HTML sanitisation       | DOMPurify (client) + nh3 (server, mandatory) (Section 30F)                         |
| Trust boundary          | OperationContext on every call; `remote=true` blocks dangerous ops (REQ-2714–2717) |
| Admin enforcement       | `role='admin'` + 60-min fresh-auth on destructive ops (REQ-2303)                   |
| Rate limiting           | per-user sliding window: 30 req/min API, 60 tool calls/min agent                   |

### 30K.5 Success KPIs (post-launch)

| KPI                     | Target                                           | Measurement                                 |
| ----------------------- | ------------------------------------------------ | ------------------------------------------- |
| Daily active users      | ≥ 50 % of registered                             | login-event count / total users             |
| RAG search quality      | ≥ 80 % relevance                                 | thumbs-up rate on citations                 |
| Dream effectiveness     | active memory count stable ~200                  | `memories` count time series                |
| Agent task completion   | ≥ 90 % success rate                              | `tool_result.ok` / total calls              |
| Cost per user per month | < $5 on shared key tier                          | `llm_usage` aggregation per user            |
| MCP client adoption     | ≥ 80 % of users use at least one external client | distinct `mcp_tokens.last_used_at` per user |

---

## 30L. Quality Gates by Phase

| Phase | Gate                 | Pass criteria                                                                                               |
| ----- | -------------------- | ----------------------------------------------------------------------------------------------------------- |
| 1     | Container starts     | `docker run` → `GET /health` returns 200 within 30 s                                                        |
| 1     | Auth works           | Register → login → JWT → authenticated request succeeds                                                     |
| 1     | Watcher detects      | Create `.md` file → watcher event logged within 5 s                                                         |
| 1     | MCP stdio works      | Claude Code connects via stdio, lists tools, calls `brain_search`                                           |
| 1     | MCP HTTP works       | `curl POST http://localhost:8787/mcp -H "Authorization: Bearer ..."` → JSON-RPC tool list returned          |
| 2     | RAG with citations   | Chat message → hybrid search → answer cites retrieved pages                                                 |
| 2     | Auto-link extraction | Page write with `[[Foo]]` → row in `links` table within 1 s, no LLM call                                    |
| 2     | Hybrid beats vector  | Fixture corpus benchmark: hybrid Precision@5 > vector-only                                                  |
| 3     | Skills runtime       | RESOLVER.md trigger matches → skill loaded → executes within 100 ms (excluding LLM time)                    |
| 3     | Meeting ingest       | Pasted transcript → meeting page + person/company pages + typed `attended` links                            |
| 3     | Entity enrichment    | Name with 10+ mentions → Tier-3 dossier with role history and timeline                                      |
| 4     | Dream runs           | Trigger → 4 phases complete → consolidation summary in `dream_audit_log`                                    |
| 4     | Maintenance fixes    | Fixture vault with broken link → maintain run → link repaired or surfaced                                   |
| 5     | Web search           | `@web` query → ranked results, cross-vault references detected                                              |
| 5     | Workspace scoping    | Focus mode in workspace → RAG limited to `include_folders` ∩ NOT `exclude_folders`                          |
| 5     | Vault graph          | `GET /api/v1/vault/graph` returns valid Cytoscape.js JSON with `meta.truncated` flag                        |
| 6     | Admin user CRUD      | Admin creates/deletes users via REST; non-admin gets 403                                                    |
| 6     | Embedding migration  | Switch model → progress tracking → completion → search returns results                                      |
| 6     | Prometheus metrics   | `GET /metrics` returns request counts, latencies, MCP calls per tool                                        |
| 7     | MCP server registry  | Admin adds external MCP server → tools discovered → confirmed call succeeds                                 |
| 7     | DAG durability       | Submit parent-child job DAG → restart container → completes correctly                                       |
| 7     | Backup + restore     | Backup script runs → restore script reproduces full state on a fresh container                              |
| 8     | Tray + Quick Chat    | Close window → tray icon → global hotkey opens Quick Chat                                                   |
| 8     | Editor opens via SSE | Agent emits `client_request: open_editor` → Tiptap opens the file                                           |
| 8     | Obsidian export      | Configure vault path → export conversation + page → files appear in Obsidian with frontmatter and wikilinks |
| 8     | Performance          | All NFR targets in Section 30K met on a fixture corpus of 5,000 pages                                       |

---

## 30M. Assumptions, Constraints & Dependencies

### 30M.1 Assumptions
- Operators have Docker installed and can run containers.
- At least one LLM provider API key is available, or local Ollama is reachable from the container network.
- Vault files are markdown (`.md`) with optional YAML frontmatter.
- macOS or Windows for the Phase 8 Electron client (Linux for development).
- Network access to external LLM APIs is available from the container; fully offline operation is possible only with local Ollama and a local embedder.
- The encryption-key environment variable (`SMARTCOPILOT_FERNET_KEY`) persists across container restarts (mounted from a secret manager or env file).

### 30M.2 Constraints
- Single-process Python backend; no horizontal scaling beyond uvicorn workers within one container.
- 3–10 users maximum (per RLS + single PostgreSQL design).
- No real-time collaborative editing — users edit independently in their own clients.
- No mobile client.
- The encryption key is the master secret; losing it makes encrypted provider keys unrecoverable.
- The `apscheduler_jobs` table is owned by APScheduler; it MUST NOT be managed by Alembic migrations.

### 30M.3 Dependencies

| Dependency                   | Risk                                             | Mitigation                                                        |
| ---------------------------- | ------------------------------------------------ | ----------------------------------------------------------------- |
| LiteLLM library              | provider API drift                               | pin version; provider tests in CI                                 |
| pgvector extension           | must be on base image                            | use `pgvector/pgvector:pg16`                                      |
| MCP Python SDK               | breaking changes in v2                           | pin to `mcp>=1.25,<2`; transport tests in CI                      |
| watchdog                     | platform-specific behaviour (Linux inotify caps) | reconciliation every 6 h; content hash dedup                      |
| Tiptap (Phase 8)             | markdown round-trip lossiness                    | round-trip test on Day 1 of Phase 8; store frontmatter separately |
| react-complex-tree (Phase 8) | maintainer abandonment risk                      | fallback: `react-arborist` fork or `headless-tree`                |
| argon2-cffi                  | C dependency                                     | distributed wheels for amd64/arm64 on PyPI                        |
| Electron (Phase 8)           | major version cadence                            | pin; test on macOS + Windows in CI                                |
| openapi-typescript           | spec→TS drift                                    | pre-commit regen + CI diff check                                  |

---

## 30N. Risks & Mitigations

| Risk                                           | Severity | Mitigation                                                                                                                                                   |
| ---------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| PostgreSQL crash takes down API                | Medium   | supervisord auto-restart; external-DB mode supported                                                                                                         |
| HNSW recall degrades at 100K+ chunks           | Medium   | monitor metrics; per-user schema partitioning if needed                                                                                                      |
| File watcher misses Syncthing events           | Medium   | reconciliation every 6 h; content_hash dedup                                                                                                                 |
| LiteLLM update breaks providers                | Medium   | pin version; provider tests in CI                                                                                                                            |
| Tiptap markdown round-trip lossy (Phase 8)     | **High** | round-trip test on Day 1 of Phase 8; store frontmatter separately                                                                                            |
| Agent writes while user is editing             | **High** | watcher debounce 300 ms; conflict modal; OperationLog undo                                                                                                   |
| SSE drops behind reverse proxy                 | Medium   | document `flush_interval -1` / `proxy_buffering off`; client shows partial-response indicator                                                                |
| Embedding migration takes hours                | Medium   | progress tracking; cancellation; crash-safe resumption                                                                                                       |
| Memory Dream deletes wanted memories           | Medium   | archive (not delete); `dream_audit_log`; user restore via memory tab                                                                                         |
| Encryption key lost                            | **High** | document backup procedure; MultiFernet rotation in future revision                                                                                           |
| Users expect Obsidian-quality editor (Phase 8) | Low      | document "use Obsidian for advanced editing" workflow                                                                                                        |
| `captureFromClipboard` 10 s timeout            | Low      | suggest pasting into chat as fallback                                                                                                                        |
| **RLS context leak**                           | **High** | `RESET app.current_user_id` in `finally:` block; unit test asserts no GUC leak across pooled connections; route-level code review                            |
| Auto-link extraction false positives           | Medium   | confidence scoring; user can mark a link `removed` (negative training signal)                                                                                |
| Cascade re-enrichment storm on bulk rename     | Medium   | 1-hop limit (Section 30G.3); per-page debounce                                                                                                               |
| MCP server (external) crashes or hangs         | Medium   | health checks every 60 s; 3 failures → disconnect + exponential backoff; tool-call timeout 60 s; agent continues with built-in tools                         |
| MCP tool poisoning (malicious tool metadata)   | Medium   | nh3-sanitise all MCP outputs before re-entering LLM context; admin reviews discovered tools before enabling; `always_allow` only for trusted read-only tools |
| Memory import exceeds 500-per-user limit       | Low      | client-side validation; partial import; clear error                                                                                                          |
| Provider key rate-limits exhausted             | Medium   | per-user daily budget caps; `429 RATE_LIMITED` response with `retry_after_seconds`                                                                           |

---

## 30O. Reference Codebases & Resources

> **FOR AI AGENTS:** These repositories provide implementation patterns. Study them for architecture, not as code to copy. The product_requirements.md and v26.05.1 PRDs are the only normative sources for Smart Copilot itself.

### 30O.1 Primary architecture references

| Repository              | URL                                                      | What to study                                                                                                                                             |
| ----------------------- | -------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| obsidian-smart-composer | `https://github.com/glowingjade/obsidian-smart-composer` | RAG pipeline patterns, chat UI, citation rendering. Original conceptual fork target before Smart Copilot diverged into a self-hosted server architecture. |
| Infio-Copilot           | `https://github.com/infiolab/infio-copilot`              | 54K LOC Obsidian AI plugin. Provider abstraction, workspace isolation, Lexical `@mentions` (relevant to Phase 8 chat input). MIT-licensed.                |

### 30O.2 Architecture pattern references

| Repository            | URL                                               | What to study                                                                               |
| --------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| LibreChat             | `https://github.com/danny-avila/LibreChat`        | Multi-provider LLM chat UI, conversation management, plugin system                          |
| Open WebUI            | `https://github.com/open-webui/open-webui`        | Self-hosted LLM interface, RAG pipeline, document management                                |
| LiteLLM               | `https://github.com/BerriAI/litellm`              | Provider translation library — `acompletion`, `aembedding` APIs, callback system            |
| Anthropic MCP servers | `https://github.com/modelcontextprotocol/servers` | Reference implementations of MCP servers; useful templates for the external-server registry |

### 30O.3 Technology documentation

| Technology               | URL                                                             |
| ------------------------ | --------------------------------------------------------------- |
| FastAPI                  | `https://fastapi.tiangolo.com/`                                 |
| SQLAlchemy 2.0 (async)   | `https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html` |
| Alembic                  | `https://alembic.sqlalchemy.org/`                               |
| pgvector                 | `https://github.com/pgvector/pgvector`                          |
| LiteLLM                  | `https://docs.litellm.ai/`                                      |
| MCP specification        | `https://modelcontextprotocol.io/specification/2025-03-26`      |
| MCP Python SDK           | `https://github.com/modelcontextprotocol/python-sdk`            |
| APScheduler              | `https://apscheduler.readthedocs.io/`                           |
| watchdog                 | `https://python-watchdog.readthedocs.io/`                       |
| nh3                      | `https://nh3.readthedocs.io/`                                   |
| argon2-cffi              | `https://argon2-cffi.readthedocs.io/`                           |
| Electron Forge (Phase 8) | `https://www.electronforge.io/`                                 |
| Tiptap (Phase 8)         | `https://tiptap.dev/`                                           |
| Lexical (Phase 8)        | `https://lexical.dev/`                                          |
| Radix UI (Phase 8)       | `https://www.radix-ui.com/`                                     |
| DOMPurify (Phase 8)      | `https://github.com/cure53/DOMPurify`                           |

---

## 30P. AI Agent Implementation Guidance

> **FOR AI AGENTS:** This section provides pragmatic guidance for implementing this PRD. Read this before starting any phase.

### 30P.1 Start with the Skeleton

Before writing business logic:

1. **Set up the test infrastructure** (Appendix E): real PostgreSQL test db, `conftest.py` fixtures, RLS isolation tests.
2. **Add the file structure** (Section 30J): empty `__init__.py` files for every module.
3. **Run `smartcopilot doctor`** (REQ-2200) as the first smoke test.
4. **Verify OpenAPI spec auto-generates** (REQ-2700) from route definitions.

### 30P.2 Implementation Order

Within each phase, implement in this order to respect dependencies:

| Order | Module                              | Why First                                                 |
| ----- | ----------------------------------- | --------------------------------------------------------- |
| 1     | `auth/` + `dependencies.py`         | All other modules need `get_current_user` and RLS context |
| 2     | `models/` + migrations              | Schema must exist before any service uses it              |
| 3     | `services/`                         | Transport-agnostic core; tested without FastAPI overhead  |
| 4     | `routes/` + `mcp/server.py`         | Thin wrappers around services                             |
| 5     | `vault/` (watcher, parser, indexer) | Depends on schema + services                              |
| 6     | `rag/` + `llm/`                     | Depends on schema + services + vault                      |
| 7     | `skills/` + `agent/`                | Top of the stack; uses everything below                   |

### 30P.3 Every Service Function Must

```python
async def some_service_function(ctx: OperationContext, ...) -> SomeResponse:
    # 1. Assert OperationContext is present
    if ctx is None:
        raise ValueError("OperationContext required")
    
    # 2. Assert trust boundary if write operation
    if write_operation and ctx.remote:
        raise PermissionError("remote=true callers cannot write")
    
    # 3. Check RLS context is set (for unit tests)
    # assert ctx.user_id is not None
    
    # 4. Do work
    
    # 5. Log to audit_log if mutation
    if mutation:
        await audit_log(ctx, action="some_action", ...)
```

### 30P.4 PR Checklist

Before submitting a PR:

- [ ] All tests pass: `pytest server/app/tests/ -v`
- [ ] Drift test passes: `test_tool_rest_parity` finds no mismatches
- [ ] OpenAPI spec updated: `docs/openapi.json` regenerated
- [ ] RLS isolation test confirms user A cannot read user B's data
- [ ] `smartcopilot doctor` passes
- [ ] New requirements have corresponding test in `test_*.py`
- [ ] No `encrypted_key` in any Pydantic response schema
- [ ] No Fernet key or token hash in logs
- [ ] Code formatted with Ruff: `ruff format server/`
- [ ] Lint passes: `ruff check server/`

### 30P.5 When Requirements Conflict

| Conflict                 | Resolution Rule                                                                                  |
| ------------------------ | ------------------------------------------------------------------------------------------------ |
| PRD vs. `ui-spec.md`     | PRD wins for data contracts and API bindings; `ui-spec.md` wins for visual/interaction decisions |
| Two REQs contradict      | Earlier REQ (lower number) wins within same phase; later phase REQ wins across phases            |
| REQ vs. test             | Test reflects actual behavior; file an issue if REQ is wrong                                     |
| Section vs. Appendix     | Appendix provides context; Section is normative                                                  |
| Section 5 vs. Section 5A | Section 5 is normative (MUST/SHOULD); Section 5A is explanatory                                  |

---

## 31. Glossary

- **Auto-link extraction:** Zero-LLM, deterministic extraction of typed links from page bodies on every write.
- **Brain-first:** Convention requiring the agent to query the local brain before any external API/LLM call.
- **Compiled truth:** Above-the-`---` section of a page; current synthesized state, freely rewritable.
- **Hybrid RAG:** Retrieval pipeline fusing vector, BM25, and graph results via Reciprocal Rank Fusion.
- **MCP:** Model Context Protocol, the standardized agent-to-tool transport supporting stdio and HTTP modes.
- **Memory Dream:** Nightly consolidation cycle that maintains the brain (stale, orphans, links, citations, back-links, tags).
- **OperationContext:** Per-request trust object carrying user, transport, remote flag, and request id.
- **RESOLVER.md:** Dispatcher file mapping triggers to skills.
- **Reciprocal Rank Fusion (RRF):** Score = Σ 1/(60 + rank) across retrievers.
- **Skill:** Fat markdown workflow (SKILL.md + tests + evals + optional code) executed by the agent.
- **Skillpack:** Bundled set of skills shipped as the system default.
- **Timeline:** Below-the-`---` append-only event log section of a page.
- **Tier 1/2/3 enrichment:** Mention-count-driven dossier depth for entity pages.
- **Trust boundary:** The `remote=true` vs `remote=false` partition that limits dangerous operations.
- **Typed link:** A directed edge with a semantic type (`works_at`, `invested_in`, etc.) between a page and an entity.
- **Vault:** A markdown directory tree owned by a user (private) or shared.
- **Wikilink:** `[[type/slug]]` reference in markdown body.
- **`note_type`:** The Zettelkasten lifecycle kind of a page: `fleeting` (raw capture), `literature` (source notes), `permanent` (atomic Zettel), `archived_fleeting` (transferred from fleeting), `skill` (procedure), `moc` (map of content hub). Separate from `type` (dossier kind).
- **`enrichment_hash`:** xxhash64 of concatenated enrichment inputs; compared on write to decide whether re-enrichment is needed.
- **`content_hash`:** XXH64 (xxhash64) of the raw file bytes (frontmatter YAML + body) as stored on disk; represented as 16-character hex. Used to detect any change requiring re-parse + re-index.
- **`archived_fleeting`:** A `note_type` value indicating a page was promoted from fleeting capture to permanent storage.
- **`safeStorage`:** Electron API for OS-native encrypted credential storage (used for the desktop app's encrypted token store).
- **`gbrain`:** The legacy maintain pattern from Smart Copilot's predecessor: a nightly skill that runs `[stale → orphans → dead-link → citations → backlinks → tags]` in sequence per page, ensuring the brain stays consistent.

---

## Appendix A — Default Skill List (one-line definitions)

1. **signal-detector** — fires on every message; cheap-model parallel pass to capture original ideas + entity mentions.
2. **brain-ops** — read-enrich-write loop; canonical brain access pattern.
3. **ingest** — thin router; detects input type and delegates.
4. **idea-ingest** — links/articles/tweets → analyzed pages with author people pages and cross-links.
5. **media-ingest** — video/audio/PDF/screenshots/repos → structured pages.
6. **meeting-ingestion** — transcripts → meeting page + attendee enrichment.
7. **enrich** — tiered (T1/T2/T3) person/company enrichment.
8. **query** — 3-layer search with synthesis + citations; refuses to hallucinate.
9. **maintain** — periodic health: stale, orphans, dead links, citations, back-links, tags.
10. **citation-fixer** — repairs broken citation references.
11. **repo-architecture** — proposes vault/page-type architecture changes.
12. **publish** — render a page to publication-quality output.
13. **data-research** — run a parameterized recipe.
14. **daily-task-manager** — manage daily tasks, priorities, completions.
15. **daily-task-prep** — prepare today's task list from calendar + open threads.
16. **cron-scheduler** — register/unregister cron jobs to APScheduler.
17. **reports** — generate periodic reports (weekly, quarterly).
18. **cross-modal-review** — second-opinion review across modalities.
19. **webhook-transforms** — process external events arriving via webhook.
20. **testing** — validate skill health.
21. **skill-creator** — create new skills following the conformance standard.
22. **skillify** — meta-skill: orchestrate the 10-step loop to make a feature into a proper skill.
23. **skillpack-check** — validate every skill has SKILL.md, manifest coverage, resolver coverage.
24. **smoke-test** — post-restart health checks with auto-fix.
25. **minion-orchestrator** — background work via durable jobs; parent-child DAGs.
26. **soul-audit** — agent identity / "who am I" customization.
27. **setup** — first-boot system initialization.
28. **migrate** — migrate from Obsidian/Notion/Logseq/plain markdown.
29. **briefing** — daily briefing skill: meetings + active threads + open deals.

## Appendix B — Default Tool Surface (22 agent tools + 30+ MCP tools)

**22 agent tools** (Section 17): `search`, `query`, `get_page`, `put_page`, `update_compiled_truth`, `append_timeline`, `list_pages`, `delete_page`, `history`, `diff`, `revert`, `tags`, `backlinks`, `graph_traverse`, `entity_get`, `entity_merge`, `enrich_entity`, `ingest`, `recipe_run`, `skill_run`, `jobs_submit`, `maintain_run`.

**MCP tool surface** (Section 9.4) MUST additionally include: `brain.stats`, `brain.health`, `brain.entity.alias.add`, `ingest.idea`, `ingest.media`, `ingest.meeting`, `skill.list`, `skill.get`, `jobs.status`, `jobs.cancel`, `maintain.report`, plus all 22 agent tools surfaced under `brain.*` / `enrich.*` / `recipe.*` / `skill.*` / `jobs.*` / `maintain.*` namespaces.

## Appendix C — Default RLS Policies (pseudocode)

```sql
-- All multi-tenant tables follow this pattern.
ALTER TABLE pages ENABLE ROW LEVEL SECURITY;

-- Users see their own private-vault pages.
CREATE POLICY pages_owner_select ON pages
  FOR SELECT USING (
    vault_id IN (
      SELECT id FROM vaults
      WHERE (kind = 'private' AND owner_user_id = current_setting('app.current_user_id')::uuid)
         OR (kind = 'shared')
    )
  );

-- Writes restricted to the owner of the private vault, or any authenticated user
-- for shared vaults if shared-write is enabled in vault frontmatter.
CREATE POLICY pages_owner_write ON pages
  FOR ALL USING (
    vault_id IN (
      SELECT id FROM vaults
      WHERE (kind = 'private' AND owner_user_id = current_setting('app.current_user_id')::uuid)
         OR (kind = 'shared')
    )
  ) WITH CHECK (
    vault_id IN (
      SELECT id FROM vaults
      WHERE (kind = 'private' AND owner_user_id = current_setting('app.current_user_id')::uuid)
         OR (kind = 'shared')
    )
  );

-- System carve-out for maintenance jobs.
CREATE POLICY pages_system_full ON pages
  FOR ALL USING (current_setting('app.current_user_id')::uuid = '00000000-0000-0000-0000-000000000001'::uuid);
```

Equivalent policies MUST be defined for: `chunks`, `entities`, `links`, `timeline_events`, `tags`, `page_tags`, `mcp_tokens`, `provider_keys`, `sessions`, `recipes`, `skills` (where namespace='user'), `eval_candidates`, `memories`, `dream_audit_log`, `projects`, `operation_log`, `llm_usage`, `index_events`, `user_settings`, `conversations`, `messages`, `system_config`, `mcp_servers`. The `users` and `audit_log` tables MUST allow each user to read their own row, and admins to read all rows. System-only tables (`system_config`) MUST have a policy carves-out for the system maintenance UUID.

---

## Appendix D — Decision Log

> **FOR AI AGENTS:** This log documents the rationale behind non-obvious design decisions. Knowing *why* helps you make correct judgment calls on edge cases not explicitly covered by requirements.

### D.1 Architecture Decisions

| ID      | Decision                                                           | Rationale                                                                                                                                                                                       | Consequences                                                                                                                                           |
| ------- | ------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| DEC-001 | **RRF k = 60**                                                     | Standard from Cormack et al. 2009. Higher k reduces the impact of rank-position differences; lower k amplifies them. 60 is the documented safe default balancing recall and precision.          | If you change k, re-run the fixture benchmark (REQ-2404) and verify Precision@5 improves or holds.                                                     |
| DEC-002 | **Slug allowlist: `^[a-z0-9][a-z0-9\-]{0,127}$`**                  | Prevents RTL override attacks, XSS via wikilinks, and path traversal. Alphanumeric + hyphen is sufficient for Zettelkasten slugs.                                                               | Remote callers with non-matching slugs receive `VALIDATION_ERROR`. System callers bypass this check.                                                   |
| DEC-003 | **750ms debounce (REQ-912)**                                       | Balances responsiveness vs. keystroke storms during rapid editing. Obsidian-style editing typically produces events every 200-400ms.                                                            | Watcher coalesces events; if you lower below 500ms, expect re-index thrashing on long documents.                                                       |
| DEC-004 | **"Human always wins" conflict resolution (REQ-920)**              | Users editing their vault locally (Obsidian, etc.) are the source of truth. The API is an intelligent agent layer, not the editor.                                                              | DB is updated to match disk on conflict. API writes use atomic temp-file + rename to avoid partial writes.                                             |
| DEC-005 | **LiteLLM as library, not proxy**                                  | In-process import avoids network hop, reduces latency, and simplifies key management (one encrypt/decrypt per request vs. proxy token exchange).                                                | LiteLLM version must be pinned; breaking provider changes require container rebuild.                                                                   |
| DEC-006 | **APScheduler + SQLAlchemyJobStore (REQ-1900)**                    | Single PostgreSQL instance means one job store. External brokers (Redis/Celery) add operational complexity and failure modes. APScheduler survives container restarts via persistent job store. | Job serialization must handle UUIDs, JSONB, and circular references. Avoid lambda/cell job args.                                                       |
| DEC-007 | ** Fernet encryption for provider keys**                           | Fernet (AES-128-CBC + HMAC) provides authenticated encryption. Master key from env var is industry-standard pattern (12-factor apps).                                                           | Key rotation requires re-encrypting all stored keys; implement via `smartcopilot admin rotate-fernet` (REQ-2011).                                      |
| DEC-008 | **argon's memory=64MiB, iterations≥3**                             | OWASP 2023 recommendation for password hashing. Balances security vs. login latency (≤200ms per auth).                                                                                          | Adjust only if login latency exceeds NFR target; changing requires re-hashing existing passwords on next login.                                        |
| DEC-009 | **HNSW cosine vs. inner product**                                  | Cosine distance is embedding-model-agnostic (works with normalized and non-normalized embeddings). Inner product requires normalized embeddings for correctness.                                | Phase 1 uses `openai/text-embedding-3-small` which produces normalized embeddings — cosine and inner product produce identical results for this model. |
| DEC-010 | **watchdog thread → asyncio handoff via `call_soon_threadsafe()`** | watchdog runs in a separate thread; asyncio event loop runs in the main thread. Direct queue submission from watchdog thread would race with asyncio's thread-safety guarantees.                | Never call async code directly from the watchdog thread. Always use `loop.call_soon_threadsafe()`.                                                     |
| DEC-011 | **compile-truth boost +0.15 to RRF score**                         | Empirically determined: boosts above-the-fold content (the "current state") without dominating vector/BM25 signals. 0.15 is a 15% rank boost at position 1.                                     | Tune via `user_settings.settings.rag.compiled_truth_boost` (if implemented). Default 0.15 tested against ~1000 queries.                                |
| DEC-012 | **Backlink boost: `min(0.10, in_degree/100)`**                     | Caps contribution at 0.10 to prevent hub pages (highly connected) from dominating search. In-degree is uncapped; capping normalizes.                                                            | If hub pages are under-ranked, increase cap. If hub pages dominate, decrease cap or increase denominator.                                              |
| DEC-013 | **Single chunk threshold: 600 tokens**                             | Covers ~90% of Zettelkasten atomic notes. Above this, recursive splitting with markdown-aware separators provides better retrieval granularity.                                                 | Adjust via `rag.chunking.single_chunk_threshold`. Raising to 1000 increases single-chunk coverage but reduces retrieval precision for long notes.      |
| DEC-014 | **Memory Dream uses cheapest tier**                                | Consolidation is bulk summarization, not creative synthesis. Using `gpt-4o-mini` or `claude-haiku` reduces cost by ~10x vs. balanced tier.                                                      | Model must support JSON mode for structured consolidation output.                                                                                      |

### D.2 Operational Decisions

| ID      | Decision                                         | Rationale                                                                                                                                                                                        | Consequences                                                                                                                                                                            |
| ------- | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DEC-015 | **APScheduler in dedicated supervisord program** | Running APScheduler inside uvicorn workers causes duplicate job execution. Workers share no memory, and GIL doesn't serialize thread access to APScheduler internals.                            | Dedicated program is single-threaded; advisory locks (DEC-016) are the fallback if you ever split APScheduler across processes.                                                         |
| DEC-016 | **PostgreSQL advisory locks for concurrency**    | Advisory locks (`pg_try_advisory_lock`) are server-side, non-blocking, and survive connection drops.比 file locks or Redis more appropriate since Postgres is already the primary store.         | Lock key must be deterministic (e.g., `hashtext('dream')`). Lock is released on connection close; long-running jobs must hold the lock explicitly.                                      |
| DEC-017 | **First user is admin (REQ-2520)**               | Eliminates bootstrapping complexity. The bootstrap token is printed to stderr (not stored) so it's single-use by design.                                                                         | If no users exist, `/health` returns `setup_required: true`. Phase 8 client renders "Create Admin" form. Registration is disabled after first user (unless `allow_registration: true`). |
| DEC-018 | **SSE for chat, WebSocket for real-time**        | SSE is unidirectional (server→client) — ideal for streaming tokens. WebSocket is bidirectional — needed for indexing progress, job status, notifications. Mixing protocols is standard practice. | Reverse proxies (nginx, Caddy) need config for SSE streaming (disable buffering). SSE is not resumable; WebSocket reconnect uses exponential backoff.                                   |
| DEC-019 | **Claude Desktop stdio via mcp-remote shim**     | Claude Desktop does not natively support Streamable HTTP in v26.05. The `mcp-remote` npm package bridges HTTP → stdio.                                                                           | When Claude Desktop adds native HTTP transport, the shim becomes optional. Document both patterns in REQ-1501E.                                                                         |
| DEC-020 | **Hermes skill pack is client-side only**        | Smart Copilot skills execute server-side against the database/vault. Hermes skills instruct the Hermes LLM when to call which MCP tools. Mixing concerns would create circular dependencies.     | REQ-1499A through REQ-1499D define the layer contract. If Hermes skills replicate server logic, `smartcopilot client validate hermes` detects the breach.                               |

### D.3 Rejected Alternatives

| ID      | Rejected Option                  | Reason for Rejection                                                                                                                             |
| ------- | -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| REJ-001 | Redis/Celery for job queue       | Adds external broker; violates single-container P2. APScheduler + SQLAlchemyJobStore is sufficient for 3-10 users.                               |
| REJ-002 | LiteLLM as proxy service         | Network hop + additional failure mode. In-process import is simpler and lower latency.                                                           |
| REJ-003 | SQLite / PGLite as primary store | No pgvector support; ACID compliance concerns at scale. PostgreSQL is the primary store requirement (REQ-105, REQ-106, REQ-107).                 |
| REJ-004 | LLM-based link extraction        | Expensive (one LLM call per page write), non-deterministic, slow. Zero-LLM deterministic extraction is faster, cheaper, and reproducible.        |
| REJ-005 | Custom RBAC beyond admin/user    | Role explosion leads to complexity. Two roles are sufficient for homelab use cases. Admin can delegate via per-user MCP tokens.                  |
| REJ-006 | Real-time collaborative editing  | CRDT or OT implementation complexity unjustified for 3-10 user homelab. Users edit independently.                                                |
| REJ-007 | Mobile client                    | Out of scope for v1.0. MCP-first design means any MCP-capable mobile client (future) can connect.                                                |
| REJ-008 | VS Code extension                | Phase 8 (Electron) is the primary UI. VS Code extension would be a Phase 9+ consideration. MCP-first means Claude Code on desktop already works. |

---

## Appendix E — Test Skeleton

> **FOR AI AGENTS:** This appendix provides the canonical test file structure. Every module listed in Section 30J.1 should have a corresponding test file. Tests run against a real PostgreSQL test database (REQ-2400); mocking the DB layer is prohibited for integration tests.

### E.1 Test Directory Structure

```
server/app/tests/
├── unit/
│   ├── test_link_extractor.py          # [TEST] REQ-1160, REQ-1161
│   ├── test_chunker.py                # [TEST] REQ-1230, REQ-1231
│   ├── test_intent_classifier.py      # [TEST] REQ-1200
│   ├── test_fernet.py                # [TEST] REQ-2010
│   ├── test_password.py             # [TEST] REQ-400
│   ├── test_slug_validation.py      # [TEST] REQ-523, REQ-1020
│   └── test_resolver.py             # [TEST] REQ-1410, REQ-1411
├── integration/
│   ├── test_auth.py                 # [TEST] REQ-400–402, REQ-584
│   ├── test_pages.py                # [TEST] REQ-1000–1025
│   ├── test_search.py              # [TEST] REQ-1200–1209
│   ├── test_mcp_stdio.py          # [TEST] REQ-500, REQ-603
│   ├── test_mcp_http.py           # [TEST] REQ-501, REQ-603
│   ├── test_websocket.py          # [TEST] REQ-610, REQ-2760–2765
│   ├── test_skills.py            # [TEST] REQ-1400–1412
│   ├── test_ingest.py           # [TEST] REQ-1500–1543
│   └── test_dream.py          # [TEST] REQ-1800–1820
├── rls/
│   ├── test_rls_isolation.py   # [TEST] REQ-330, REQ-331, REQ-571
│   └── test_rls_context_leak.py # [TEST] REQ-340, REQ-571
├── drift/
│   ├── test_tool_rest_parity.py  # [TEST] REQ-2406
│   └── test_openapi_contract.py  # [TEST] REQ-2700–2704
├── fixtures/
│   ├── corpus/                   # ~1000 synthetic pages for benchmark (REQ-2404)
│   ├── corpus.yaml               # Fixture definition: page slugs, types, expected links
│   └── test_vault/              # Minimal vault for integration tests
└── conftest.py                  # [TEST] Shared fixtures: test_db, test_user, test_ctx
```

### E.2 Canonical Test Fixtures

```python
# conftest.py — shared fixtures
import pytest
import asyncio
from asyncpg import create_pool, connect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.models import User, Vault

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_db():
    """Create ephemeral test database. REQ-2400: real PostgreSQL, no mocking."""
    # Set up DATABASE_URL for test db (e.g., created via postgres fixture)
    engine = create_async_engine(os.environ["TEST_DATABASE_URL"])
    yield engine
    await engine.dispose()

@pytest.fixture
async def test_user(test_db):
    """Create test user in isolated schema."""
    # Creates user with hashed password, returns (user, plaintext_password)
    pass

@pytest.fixture
def test_ctx(test_user):
    """OperationContext for unit tests. REQ-520."""
    from app.auth.middleware import OperationContext
    return OperationContext(
        user_id=test_user.id,
        transport="test",
        remote=False,
        client_name="test-client",
        request_id=uuid.uuid4(),
    )
```

### E.3 Test Naming Convention

| Pattern                            | Meaning                                 |
| ---------------------------------- | --------------------------------------- |
| `test_<module>_<requirement>`      | Unit test for specific requirement      |
| `test_<feature>_<happy_path>`      | Integration test for feature end-to-end |
| `test_rls_<table>_<operation>`     | RLS isolation test                      |
| `test_mcp_<transport>_<tool_name>` | MCP tool integration test               |
| `test_fixtures_<corpus_name>`      | Fixture corpus validation               |

### E.4 Required Drift Tests

> **REQ-2406:** Every MCP tool MUST have a corresponding REST endpoint and vice versa.

```python
def test_tool_rest_parity():
    """Verify MCP tool surface matches REST endpoint surface."""
    mcp_tools = discover_mcp_tools()  # Parse server/app/mcp/tools.py
    rest_endpoints = discover_rest_endpoints()  # Parse server/app/routes/
    
    # Tools not in REST:
    extra_tools = mcp_tools - {tool_to_endpoint(t) for t in mcp_tools}
    assert not extra_tools, f"MCP tools without REST endpoints: {extra_tools}"
    
    # REST not in MCP:
    extra_routes = rest_endpoints - {endpoint_to_tool(r) for r in rest_endpoints}
    assert not extra_routes, f"REST endpoints without MCP tools: {extra_routes}"
```

### E.5 RLS Isolation Test Pattern

> **REQ-2401:** Assert user A cannot read user B's data via any service path.

```python
@pytest.mark.asyncio
async def test_rls_pages_isolation(test_db, test_user_a, test_user_b):
    """REQ-571: User A cannot read User B's private vault pages."""
    async with test_db.connect() as conn:
        # Set user A's context
        await conn.execute("SET app.current_user_id = %s", str(test_user_a.id))
        try:
            result = await conn.fetchrows(
                "SELECT * FROM pages WHERE vault_id = %s",
                str(test_user_b.private_vault.id),
            )
            assert len(result) == 0, "User A should not see User B's private pages"
        finally:
            await conn.execute("RESET app.current_user_id")

@pytest.mark.asyncio
async def test_rls_context_not_leaked(test_db, test_user):
    """REQ-571: Exiting request scope should not leak session GUC."""
    async with test_db.connect() as conn:
        await conn.execute("SET app.current_user_id = %s", str(test_user.id))
        # Simulate request completion
        await conn.execute("RESET app.current_user_id")
        # Verify GUC is cleared (no finally block needed if this passes)
        result = await conn.fetchval("SHOW app.current_user_id")
        assert result == "", f"GUC leaked: {result}"
```

### E.6 Auto-Link Extraction Test Coverage

> **REQ-1160:** Unit tests for code-fence stripping, within-page dedup, stale-link reconciliation, multi-type links, each typed-inference signal.

```python
# test_link_extractor.py
def test_strips_code_fences():
    """REQ-1160: Code fences must not produce false-positive links."""
    content = """
    See [[Person/jane]] for details.
    ```python
    links = extract_links('See [[Person/jane]] inside code')
    ```
    """
    links = extract_links(content)
    assert len(links) == 0, "Links inside code fences should be stripped"

def test_within_page_dedup():
    """REQ-1160: Multiple mentions of same target collapse to one link."""
    content = "Alice [[Person/alice]] and [[Person/alice]] again."
    links = extract_links(content)
    targets = [l["target"] for l in links]
    assert targets.count("Person/alice") == 1

def test_typed_inference_from_section_header():
    """REQ-1160: Section header '## Investments' infers type 'invested_in'."""
    content = """
    ## Investments
    We backed [[Company/acme]] in 2023.
    """
    links = extract_links(content)
    assert any(l["link_type"] == "invested_in" for l in links)

def test_multi_type_links():
    """REQ-1160: Same target may have multiple link types."""
    content = """
    ## Investments
    Jane [[Person/jane]] invested in [[Company/acme]].
    ## Advisory
    Jane [[Person/jane]] advises [[Company/acme]].
    """
    links = extract_links(content)
    jane_acme = [l for l in links if l["target"] == "Company/acme" and l["source"] == "Person/jane"]
    link_types = {l["link_type"] for l in jane_acme}
    assert "invested_in" in link_types
    assert "advises" in link_types
```

### E.7 Phase Acceptance Test Mapping

| Phase | Gate                 | Test File                                                     | Test Name           |
| ----- | -------------------- | ------------------------------------------------------------- | ------------------- |
| 1     | Container starts     | N/A                                                           | Manual `docker run` |
| 1     | Auth works           | `test_auth.py::test_register_creates_admin`                   | [TEST] REQ-400      |
| 1     | Watcher detects      | `test_vault.py::test_watcher_detects_file_change`             | [TEST] REQ-203      |
| 1     | MCP stdio works      | `test_mcp_stdio.py::test_stdio_lists_and_calls_tools`         | [TEST] REQ-500      |
| 1     | MCP HTTP works       | `test_mcp_http.py::test_http_returns_tool_list`               | [TEST] REQ-501      |
| 2     | RAG with citations   | `test_search.py::test_hybrid_search_returns_citations`        | [TEST] REQ-1221     |
| 2     | Auto-link extraction | `test_link_extractor.py::test_extracts_typed_links`           | [TEST] REQ-1100     |
| 2     | Hybrid beats vector  | `test_search.py::test_hybrid_precision_above_baseline`        | [TEST] REQ-2404     |
| 3     | Skills runtime       | `test_skills.py::test_resolver_matches_and_runs`              | [TEST] REQ-1410     |
| 3     | Meeting ingest       | `test_ingest.py::test_meeting_creates_attendee_pages`         | [TEST] REQ-1520     |
| 4     | Dream runs           | `test_dream.py::test_dream_consolidates_memories`             | [TEST] REQ-1800     |
| 5     | Web search           | `test_websearch.py::test_returns_ranked_results`              | [TEST] REQ-2720     |
| 6     | Admin user CRUD      | `test_admin.py::test_admin_creates_and_deletes_user`          | [TEST] REQ-2730     |
| 7     | MCP server registry  | `test_mcp_registry.py::test_external_server_tools_discovered` | [TEST] REQ-2740     |
| 8     | (Deferred)           |                                                               |                     |

---

## Appendix F — Common Pitfalls

> **FOR AI AGENTS:** These are known failure modes that have burned real implementations. Read before starting each module.

### F.1 Database & RLS

| Pitfall                                | Symptom                                                                   | Fix                                                                                                               |
| -------------------------------------- | ------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| **GUC leak across pooled connections** | User A sees User B's private pages after a request                        | Always `RESET app.current_user_id` in `finally:` block. Add `test_rls_context_not_leaked` to CI.                  |
| **Connection pool inherits SET**       | RLS silently broken after connection reuse                                | `pool.acquire()` returns a fresh connection; `acquire().connection` may not. Test with multiple concurrent users. |
| **Async session + sync psycopg2 mix**  | Migration runs but runtime fails with "connection already in transaction" | `env.py` uses sync psycopg2; runtime uses asyncpg. Never import sync DB code into async context.                  |
| **`SET LOCAL` instead of `SET`**       | GUC only lasts for transaction, not request                               | Use `SET` (session-level) not `SET LOCAL` (transaction-level). RLS policies apply to the session GUC.             |
| **RLS on `pg_catalog` tables**         | Unexpected auth failures                                                  | RLS only on application tables. `pg_catalog` tables are system tables and must not have RLS.                      |

### F.2 Async & Concurrency

| Pitfall                                     | Symptom                                   | Fix                                                                                                             |
| ------------------------------------------- | ----------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| **Blocking call in asyncio event loop**     | `watchdog` thread deadlocks; API hangs    | Use `loop.call_soon_threadsafe()` for all cross-thread → asyncio handoff. Never `await` inside watchdog thread. |
| **`asyncio.gather` + one failure**          | Partial results; hard to debug            | Always use `asyncio.gather(*tasks, return_exceptions=True)` and check results.                                  |
| **Asyncpg connection leak**                 | DB connections exhausted; API returns 500 | Use `async with` context managers for all `acquire()` / `connect()` calls. Add `max_connections` pool limit.    |
| **APScheduler double execution**            | Jobs run twice (index thrashing)          | Run APScheduler in dedicated supervisord program (not uvicorn worker). Or use advisory locks.                   |
| **Advisory lock not released on exception** | Subsequent Dream runs block forever       | Always wrap `pg_try_advisory_lock` in `try/finally`; release in `finally`.                                      |

### F.3 MCP & Tool Surface

| Pitfall                                       | Symptom                                        | Fix                                                                                                       |
| --------------------------------------------- | ---------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| **Tool result larger than transport limit**   | MCP HTTP returns 413 or drops response         | Stream large results. For `brain.search` with 100+ hits, paginate.                                        |
| **`remote=true` check missing on write path** | Malicious remote client writes outside vault   | Every write service function must assert `ctx.remote == False` or validate vault-relative path.           |
| **Token not hashed before storage**           | MCP tokens appear in logs or error messages    | Always `SHA256(token)` before storing. Return plaintext exactly once on creation.                         |
| **MCP tool schema drift**                     | Client tools don't match server                | Regenerate `tools.openapi.json` on every PR that changes tool surface. CI must fail on drift (REQ-1505B). |
| **External MCP server output not sanitized**  | Malicious MCP tool injects XSS via tool result | Always nh3-sanitize MCP outputs before returning to LLM (REQ-2801).                                       |

### F.4 LLM & Embedding

| Pitfall                                 | Symptom                                     | Fix                                                                                                              |
| --------------------------------------- | ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| **LiteLLM callback in wrong thread**    | `llm_usage` records have wrong `user_id`    | Ensure `OperationContext.user_id` is captured before entering async thread.                                      |
| **Embedding batch too large**           | Provider 413 or timeout                     | Default batch size 64; reduce for large models or slow providers. Add retry with exponential backoff.            |
| **Embedding dimension mismatch**        | pgvector rejected insert                    | `openai/text-embedding-3-small` → 1536. Verify `rag.embedding_dimensions` matches embedder output before insert. |
| **Stale embeddings after model change** | Old embeddings produce irrelevant search    | `enrichment_hash` must change on model change; backfill job re-embeds. Run after migration.                      |
| **LLM cost tracking missing**           | `llm_usage` table has null `cost_usd`       | Register LiteLLM callback on every `acompletion` / `aembedding` call.                                            |
| **Cheap tier not available**            | Fallback to expensive model; cost explosion | Verify cheap tier models are configured in `settings.yaml`. Default to balanced if cheap unavailable.            |

### F.5 Vault & File System

| Pitfall                             | Symptom                                                  | Fix                                                                                                                |
| ----------------------------------- | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| **File watcher miss on Syncthing**  | New files not indexed                                    | Reconciliation runs every 6h as fallback. Content hash dedup prevents unnecessary re-indexing.                     |
| **Partial file write**              | Indexer reads half-written file; corrupt chunks          | API writes use `temp_file + os.rename()` atomic pattern. DB transaction rolls back on file write failure.          |
| **`content_hash` computed wrong**   | Pages never re-indexed after edit                        | Hash must be `xxhash(raw_file_bytes)`. Python's `hash()` is not deterministic across runs.                         |
| **Wikilink resolution incorrect**   | `[[shared/Topic]]` resolves to private                   | Explicit prefix `[[shared/...]]` bypasses resolution order. Always check for prefix before applying default order. |
| **Slug collision after vault move** | PUT fails with 409 on moved file                         | `PUT /api/v1/pages/{slug}` is idempotent by slug. After `vault/move`, the new slug path is authoritative.          |
| **`compiled_truth` not boosted**    | Search returns timeline content instead of current state | Apply `+0.15` RRF boost to `kind='compiled_truth'` chunks (REQ-1014). Verify in fixture benchmark.                 |

### F.6 Skills & Agent

| Pitfall                                       | Symptom                                        | Fix                                                                                                         |
| --------------------------------------------- | ---------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| **Skill reads vault file without validation** | Path traversal via `../` in skill parameter    | All vault-relative paths from skills must pass slug validation (`^[a-z0-9][a-z0-9\-]{0,127}$`).             |
| **Skill calls LLM without tier declaration**  | Unintended expensive model used                | Skills must declare `tier: cheap                                                                            | balanced | strong` in frontmatter. Router validates. |
| **Agent refuses to answer (false positive)**  | Brain has data but agent says "no info"        | Check that RAG returned results. Agent refusal only triggers when `retrieved_evidence_count == 0`.          |
| **Brain-first convention violated**           | Agent calls external API before querying brain | System prompt must include "MUST `search` or `get_page` before any external API call." Verify in e2e test.  |
| **Skill chains infinite loop**                | Stack overflow on circular skill references    | RESOLVER.md trigger matching is top-to-bottom. Skills calling other skills must track depth. Max depth = 5. |
| **Skill result not cached**                   | Repeated LLM calls for same skill              | Skill results cached for `skill_cache_ttl_seconds` (default 300s). Bypass: re-run with `force: true`.       |

### F.7 Security & Trust Boundary

| Pitfall                                | Symptom                                          | Fix                                                                                         |
| -------------------------------------- | ------------------------------------------------ | ------------------------------------------------------------------------------------------- |
| **`encrypted_key` in response schema** | API key leaked in HTTP response                  | Pydantic response models must not include `encrypted_key` field. Use `Field(exclude=True)`. |
| **Fernet key in logs**                 | Encryption key appears in log lines              | Use structlog with secret redaction. Never `logger.info(f"key={key}")`.                     |
| **CORS allow-all**                     | Unauthorized cross-origin requests               | `cors_origins: ["http://localhost:*", "app://."]` in settings.yaml. Never `["*"]`.          |
| **Admin endpoint without fresh auth**  | Stolen session can perform destructive admin ops | 60-min fresh auth required for destructive operations (REQ-2303).                           |
| **HTML stored without sanitization**   | XSS via page content                             | All HTML passed through nh3 before storage. HTML must be converted to markdown.             |

### F.8 Deployment & Observability

| Pitfall                               | Symptom                                   | Fix                                                                                               |
| ------------------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------- |
| **Alembic migration fails**           | Container refuses to start                | Failed migrations abort boot (REQ-2530). Always write reversible migrations. Test downgrade path. |
| **`apscheduler_jobs` in Alembic**     | Migration tries to drop APScheduler table | `apscheduler_jobs` is managed by APScheduler, not Alembic. Exclude from migrations.               |
| **Health check false positive**       | `/readyz` returns 200 but system degraded | `/readyz` checks Postgres + pgvector + scheduler + watchdog + MCP HTTP. All must pass.            |
| **Prometheus metrics missing labels** | Aggregation by user not possible          | All metrics must include `user_id` label where user-attributable.                                 |
| **Structured log not JSON**           | Log aggregator can't parse                | FastAPI uvicorn logs must use JSON. Configure `uvicorn --log-config logging.json`.                |

---

## Appendix G — Backup & Restore Runbook (Operational)

### G.1 Backup (standard)
1. Ensure `SMARTCOPILOT_FERNET_KEY` is securely stored (password manager/secret store).
2. Run: `smartcopilot backup create --output /backups/smartcopilot-YYYY-MM-DD.tar.zst`
3. Run: `smartcopilot backup verify --input /backups/...tar.zst`

### G.2 Restore (fresh instance)
1. Start a fresh container with the same `SMARTCOPILOT_FERNET_KEY`.
2. Run: `smartcopilot backup restore --input /backups/...tar.zst`
3. Run: `smartcopilot backup verify --post-restore`

### G.3 Validation checklist
- `/readyz` returns 200
- MCP HTTP reachable
- Sample page retrieval works
- Search returns expected results

---

*End of Smart Copilot PRD v26.05.1 (DRAFT v0.5.1).*
