# Smart Copilot — Product Requirements Document (Node.js Edition)

**Version:** v26.05-node
**Status:** DRAFT
**Document type:** Authoritative product specification
**Audience:** Implementing AI coding agent
**Based on:** Original v26.05 PRD, inspired by gbrain (github.com/garrytan/gbrain) architecture patterns

---

## Table of Contents

1. [Executive Summary](#1-executive-summary--product-vision)
2. [Product Overview](#2-product-overview)
3. [Goals and Non-Goals](#3-goals-and-non-goals)
4. [System Architecture](#4-system-architecture)
5. [Technology Stack](#5-technology-stack)
6. [Engine Abstraction (Dual Engine)](#6-engine-abstraction-dual-engine)
7. [Phase Plan](#7-phase-plan)
8. [CLI (First-Class Surface)](#8-cli-first-class-surface)
9. [MCP Server](#9-mcp-server)
10. [REST API](#10-rest-api)
11. [Hybrid RAG Pipeline](#11-hybrid-rag-pipeline)
12. [AI Gateway](#12-ai-gateway)
13. [Zero-LLM Auto-Link Extraction](#13-zero-llm-auto-link-extraction)
14. [Agent System](#14-agent-system)
15. [Skills System](#15-skills-system)
16. [Schema Packs](#16-schema-packs)
17. [Minions (Durable Job Queue)](#17-minions-durable-job-queue)
18. [Memory Dream + Brain Maintenance](#18-memory-dream--brain-maintenance)
19. [Multi-Tenancy & Namespace Model](#19-multi-tenancy--namespace-model)
20. [Security & Trust Boundary](#20-security--trust-boundary)
21. [Deployment Topologies](#21-deployment-topologies)
22. [Phase 8 — Electron Client + Streaming + Platform Hardening](#22-phase-8--electron-client--streaming--platform-hardening)
23. [File Structure Reference](#23-file-structure-reference)

---

## 1. Executive Summary & Product Vision

Smart Copilot is a **self-hosted AI knowledge brain** for homelab teams (3–10 users) that combines a typed knowledge graph, hybrid RAG retrieval, a skills-based workflow system, and a Zettelkasten workflow over a plain-markdown vault. The system is **MCP-first**: all functionality is exposed through a Model Context Protocol server (stdio + HTTP with OAuth 2.1) and a parallel REST API. The primary user-facing frontend is the CLI + any MCP-capable agent (Hermes, Claude Desktop, etc.); an optional Electron desktop client ships at Phase 8.

The backend runs as a **Node.js 20+** process with a **dual-engine architecture**: PGLite (in-process Postgres via WASM) for personal use with zero server dependencies, or PostgreSQL 16 + pgvector for team deployments. It watches markdown vault directories via chokidar, parses pages on the **compiled-truth + timeline** convention, extracts typed wikilinks deterministically with zero LLM calls, and indexes content into pgvector HNSW + tsvector BM25 + a typed-link graph.

A 30+ tool MCP surface drives read/write operations, ingestion, enrichment, and maintenance. A nightly **Memory Dream** consolidation cycle and a continuous autopilot loop keep citations fixed, dead links audited, orphans surfaced, and stale pages flagged. A **skills system** (RESOLVER.md dispatcher, system namespace) encodes workflows as fat markdown files the agent reads and executes.

Any MCP-compliant agent can connect — including Hermes, Claude Code, Claude Desktop, Cursor, Cowork, and Perplexity. **CLI and MCP agents are the primary frontend** in early phases; an optional **Electron desktop client** is available at Phase 8. The REST API serves admin tools, automation scripts, and the Electron client.

### 1.1 Core Principles

| ID | Principle | Implication |
|----|-----------|-------------|
| P1 | **MCP-first** | All capabilities exposed via MCP from Phase 1 |
| P2 | **Standard Node.js** | Node.js 20+, npm, standard toolchain |
| P3 | **Dual engine** | PGLite for personal, Postgres + pgvector for teams |
| P4 | **AI SDK provider routing** | Vercel AI SDK for LLM calls; custom gateway for cost tracking |
| P5 | **Zero-LLM auto-link extraction** | Typed wikilinks extracted deterministically on every page write |
| P6 | **Brain-first** | Agent MUST query local brain before any external API call |
| P7 | **Multi-source from day one** | Named content repos inside one brain; per-source isolation |
| P8 | **Trust boundary** | Remote callers blocked from dangerous ops; admin ops always local |
| P9 | **Memory hygiene via Dream cycles** | Long-term memory consolidated nightly |
| P10 | **Spec-first, agent-second** | This PRD is fully self-contained |

---

## 2. Product Overview

Smart Copilot stores knowledge as plain markdown files using the **compiled-truth + timeline** convention: a horizontal-rule separator splits each page into an above-the-line "current understanding" (rewritable) and a below-the-line "append-only timeline" (event log). Indexing layers — pgvector HNSW, BM25 tsvector, and a typed wikilink graph — feed a hybrid RAG pipeline using Reciprocal Rank Fusion with post-fusion boost stages (backlink, salience, recency, graph signals) and an optional cross-encoder reranker.

A **dual database engine** powers the system: **PGLite** (PostgreSQL 17 compiled to WASM, embedded in-process) for personal use with zero server dependencies, or **PostgreSQL 16 + pgvector** for team/scale deployments. Both engines implement the same `BrainEngine` interface — the user chooses at init time and can switch later.

A **schema pack system** allows page types to be user-defined via YAML manifests (`scp-base`, `scp-recommended`, or custom packs). Each pack declares path prefixes that map to page types (e.g., `people/` → `person`, `companies/` → `company`), typed edges, and extractable facts.

---

## 3. Goals and Non-Goals

### 3.1 Goals
- **REQ-001** Provide a multi-tenant knowledge brain with per-user/page isolation enforced at the database level.
- **REQ-002** Expose all functionality through MCP (stdio + HTTP with OAuth 2.1) and REST.
- **REQ-003** Allow full operation without a UI via the CLI binary and curl-able REST endpoints.
- **REQ-004** Deliver hybrid retrieval (vector + BM25 + graph) with RRF fusion, post-fusion boosts, and optional reranker.
- **REQ-005** Auto-extract typed links on every page write with zero LLM calls.
- **REQ-006** Run a nightly Memory Dream consolidation and continuous autopilot maintenance.
- **REQ-007** Support skills as first-class workflow primitives with a RESOLVER.md dispatcher and system namespace.
- **REQ-008** Ship as a standard Node.js 20+ package (npm install, no runtime dependencies).
- **REQ-009** Support PGLite (in-process, zero-config) and PostgreSQL + pgvector (scalable) via the same codebase.
- **REQ-010** Encrypt all third-party API keys at rest using libsodium or Node.js built-in `crypto`.

### 3.2 Non-Goals
- **REQ-011** Must NOT depend on Redis, RabbitMQ, or external brokers.
- **REQ-012** Must NOT include LightRAG, GraphRAG, or LLM-based link extraction.
- **REQ-013** LiteLLM MUST NOT be used (use Vercel AI SDK + custom gateway instead).
- **REQ-014** SQLite, DuckDB, and other embedded stores MUST NOT be used (PGLite is the zero-config engine).
- **REQ-015** The Electron desktop client is deferred to Phase 8. Early phases use CLI + MCP agents (Hermes, etc.) as the primary frontend.

---

## 4. System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  MCP-capable agents (primary frontend)                             │
│  Hermes · Claude Desktop · Claude Code · Cursor · Perplexity      │
└─────────────────────────┬────────────────────────────────────────┘
                          │ MCP (stdio + Streamable HTTP)
                          │
┌─────────────────────────▼────────────────────────────────────────┐
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Electron Desktop Client (Phase 8 — optional)            │    │
│  │  React + Lexical + Radix UI                              │    │
│  └─────────────────────────┬────────────────────────────────┘    │
│                            │ REST                                 │
│                            ▼                                      │
│  Smart Copilot — Node.js 20+                                     │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  CLI Surface (scp)                                       │  │
│  │   ├── scp init             — create/configure a brain    │  │
│  │   ├── scp serve            — MCP server (stdio + HTTP)   │  │
│  │   ├── scp search / think   — query the brain             │  │
│  │   ├── scp capture          — quick page create           │  │
│  │   ├── scp import           — bulk markdown import        │  │
│  │   ├── scp embed            — manage embeddings            │  │
│  │   ├── scp eval             — run benchmarks              │  │
│  │   ├── scp admin            — user/token management       │  │
│  │   └── scp doctor           — health check                │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │  MCP Server (stdio + Streamable HTTP)                      │  │
│  │   ├── 30+ MCP tools (brain.* / enrich.* / skill.* / etc.) │  │
│  │   └── OAuth 2.1 with DCR + PKCE                           │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │  REST API (Express, embedded in CLI)                      │  │
│  │   ├── Admin endpoints (/admin/users, /admin/tokens, etc.) │  │
│  │   └── OpenAPI spec generation                             │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │  Autopilot (continuous maintenance loop)                  │  │
│  │   ├── Sync filesystem → DB                                │  │
│  │   ├── Embed stale chunks                                  │  │
│  │   ├── Extract links + takes                                │  │
│  │   ├── Orphan detection                                    │  │
│  │   └── Dream cycle (nightly)                               │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │  In-process subsystems:                                   │  │
│  │   ├── Hybrid RAG engine (RRF + boosts + reranker)         │  │
│  │   ├── AI Gateway (Vercel AI SDK + recipe system)          │  │
│  │   ├── Auto-link extractor (zero-LLM, regex-based)         │  │
│  │   ├── Skills runtime (RESOLVER.md dispatcher)             │  │
│  │   ├── Minions job queue (Postgres-backed)                 │  │
│  │   ├── Embedder (batched, version-tracked)                 │  │
│  │   ├── Web search (DuckDuckGo, Jina, Wikipedia)            │  │
│  │   └── Encryption (libsodium) · Password hashing (argon2)  │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │  Engine: PGLite or PostgreSQL + pgvector                  │  │
│  │   ├── HNSW vector index · GIN tsvector · recursive CTEs   │  │
│  │   ├── Row-Level Security (Postgres) / file-level (PGLite) │  │
│  │   ├── Minions job store · audit log · llm_usage           │  │
│  │   └── Encrypted provider keys                             │  │
│  └────────────────────────────────────────────────────────────┘  │
│  Volumes (Postgres mode): /data (Postgres) · /vaults (markdown)  │
└──────────────────────────────────────────────────────────────────┘
External providers: OpenAI · Anthropic · Google · DeepSeek
                    OpenRouter · Ollama (local) · custom OpenAI-compatible
```

### 4.1 Data Model

All tables are created by both PGLite and Postgres engines. The schema uses migrations via version-tracked SQL files in `src/core/schema/migrations/`.

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| `pages` | id, slug, source_id, title, body, compiled_truth, timeline, page_type, metadata (JSONB), content_hash, created_at, updated_at | Primary page store. `content_hash` enables dedup on write. |
| `page_versions` | id, page_id, snapshot (JSONB), version_number, created_by, created_at | Append-only version history. Snapshot captures full page state at version time. |
| `chunks` | id, page_id, chunk_index, content, embedding (vector), content_hash | Embedding chunks. Rebuilt when page changes. |
| `entities` | id, name, page_id, entity_type, metadata (JSONB) | Named entities extracted from pages. |
| `links` | id, source_page_id, target_page_id, link_type, context, created_at | Typed wikilinks between pages. Zero-LLM extracted. |
| `takes` | id, page_id, claim, claim_type (factual|opinion|prediction|decision), weight (float 0-1), confidence, source, resolution (nullable), calibrated_confidence (nullable) | Atomic claims with type classification, importance weighting, resolution tracking, and calibration curves for accuracy measurement. `weight` controls memory decay rate. |
| `files` | id, page_id, filename, mime_type, size, storage_path, content_hash, created_at | Binary asset metadata (images, PDFs, attachments). Actual content stored on filesystem or S3. |
| `timeline_events` | id, page_id, event_type, data (JSONB), created_at | Append-only timeline entries below the compiled-truth divider. |
| `conversations` | id, user_id, title, session_metadata (JSONB), created_at, updated_at | Persisted agent conversation sessions. |
| `messages` | id, conversation_id, role, content, metadata (JSONB), citations (JSONB), created_at | Individual messages within conversations. Citations array links back to source pages. |
| `memories` | id, user_id, type, content, context_page_id, importance (float), decay_at, created_at | Hot memory with decay. Retrieved alongside hybrid search for context continuity. |
| `users` | id, username, password_hash (argon2), role, created_at | User accounts. |
| `sources` | id, name, description, vault_path, created_at | Named content repos. Slugs unique per source. |
| `mcp_tokens` | id, user_id, token_hash, scopes (text[]), source_ids (uuid[]), expires_at | OAuth 2.1 access tokens. Scope-gated. |
| `provider_keys` | id, service, key_encrypted (AES-256-GCM), user_id (nullable) | Encrypted third-party API keys. |
| `jobs` / `job_dependencies` / `job_logs` | id, type, status, payload (JSONB), priority, created_at | Minions job queue. Crash-safe via two-phase commit. |
| `audit_logs` | id, user_id, action, resource, details (JSONB), timestamp | Immutable audit trail for admin operations. |
| `llm_usage` | id, user_id, provider, model, tokens_in, tokens_out, cost, timestamp | Per-request cost tracking. Powers usage dashboards. |
| `config` | key, value (JSONB), source_id (nullable), user_id (nullable) | Layered config: per-user → per-source → brain-wide. |
| `query_cache` | query_hash, response (JSONB), embedding (vector), similarity_threshold, created_at | Semantic search cache. Evicted by age or threshold miss. |
| `tags` | id, name, source_id | Tag registry. Consistency maintained by Dream cycle. |
| `page_tags` | page_id, tag_id | Many-to-many page-tag mapping. |
| `code_symbols` | id, page_id, symbol_name, symbol_type (function/class/import/export), parent_symbol, line_start, line_end, signature, doc_comment | AST nodes extracted from code files via tree-sitter. Enables code-level semantic search. |

### 4.2 Content-Dedup on Page Write

On every `put_page`, compute SHA-256 of (normalized body + frontmatter). If `content_hash` matches an existing page, skip indexing (embedding, link extraction, timeline update) and return the existing slug. This prevents wasted re-indexing on identical writes.

### 4.3 OperationContext Pattern

Every request carries an `OperationContext`:

```typescript
interface OperationContext {
  userId: string;
  sourceId: string;
  role: 'admin' | 'user';
  trustLevel: 'local' | 'stdio' | 'remote';
  requestId: string;  // for audit correlation
}
```

The context flows through all engine operations and enforces:
- **Row-level filtering**: queries are scoped to `source_id` and user's accessible sources
- **Trust boundary**: remote callers cannot invoke shell jobs or destructive admin ops
- **Audit logging**: every mutating operation is logged with context.requestId
---

## 5. Technology Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Language | TypeScript 5.x | strict mode, ESM |
| Runtime | Node.js 20+ | LTS, npm standard toolchain |
| Database (personal) | PGLite (Postgres 17 via WASM) | in-process, zero-config |
| Database (team) | PostgreSQL 16 + pgvector | self-hosted or Supabase |
| DB driver | `postgres.js` + `pgvector` npm | async, native |
| ORM | Raw SQL | no ORM; `sql` tagged template literals |
| LLM | Vercel AI SDK (`ai`, `@ai-sdk/*`) | provider SDKs + custom gateway |
| Embedding | Vercel AI SDK + recipe system | ZeroEntropy default, 16+ providers |
| MCP SDK | `@modelcontextprotocol/sdk` ^1.29 | stdio + Streamable HTTP |
| REST | Express 5 | embedded in CLI binary |
| Background jobs | Minions (Postgres-backed job queue) | custom BullMQ-style queue |
| File watching | chokidar | native, battle-tested |
| Markdown | `gray-matter` + `marked` | frontmatter parse + render |
| HTML sanitization | `sanitize-html` | defense-in-depth |
| PDF extraction | `pdf-parse` | lazy-loaded on demand |
| DOCX extraction | `mammoth.js` | |
| HTML cleanup | `@mozilla/readability` | |
| HTTP client | native `fetch` (Node.js built-in) | |
| Auth | `oauth4webapi` + `argon2` | OAuth 2.1 + password hashing |
| Encryption | Node.js `crypto` (AES-256-GCM) | API keys at rest |
| Config | `js-yaml` + env vars | layered config resolution |
| Validation | `zod` | |
| CLI framework | `commander` or `clack` | |
| Testing | `vitest` | |
| Codegen | `openapi-typescript` | TS client from OpenAPI spec |

### 5.1 Key Library Versions (Pinned)

```
@modelcontextprotocol/sdk: ^1.29.0
ai: ^6.0.0
@ai-sdk/openai: ^3.0.0
@ai-sdk/anthropic: ^3.0.0
@ai-sdk/google: ^3.0.0
@ai-sdk/openai-compatible: ^2.0.0
@electric-sql/pglite: ^0.4.0
pgvector: ^0.2.0
postgres: ^3.4.0
chokidar: ^4.0.0
gray-matter: ^4.0.0
marked: ^18.0.0
zod: ^4.0.0
express: ^5.0.0
argon2: ^0.41.0
```

---

## 6. Engine Abstraction (Dual Engine)

### 6.1 BrainEngine Interface

The system uses a `BrainEngine` interface that defines ~47 operations. Two implementations exist:

- **PGLiteEngine**: In-process PostgreSQL via WASM. Zero server dependencies. Default for personal use.
- **PostgresEngine**: Connects to PostgreSQL 16 + pgvector. For team/scale deployments.

Key operations on the interface:
- `getPage(slug)` / `putPage(slug, page)` / `deletePage(slug)` — page CRUD
- `searchKeyword(query)` / `searchVector(embedding)` — search primitives
- `getLinks(slug)` / `getBacklinks(slug)` / `traverseGraph(slug, depth)` — graph operations
- `addLinksBatch(links)` / `addTimelineEntriesBatch(entries)` — bulk inserts
- `listSlugs()` / `listPages(filters)` — enumeration
- `transaction(fn)` — atomic multi-step operations
- `getConfig(key)` / `setConfig(key, value)` — DB-backed config

### 6.2 Engine Factory

```typescript
// engine-factory.ts
export async function createEngine(config: EngineConfig): Promise<BrainEngine> {
  switch (config.engine) {
    case 'pglite':
      return new PGLiteEngine();
    case 'postgres':
      return new PostgresEngine();
  }
}
```

The factory uses dynamic imports so PGLite's WASM bundle is never loaded for Postgres users and vice versa.

### 6.3 Config Resolution Chain

Config resolution order: per-call flag → env var → per-source DB key → brain-wide DB key → config file → defaults. Seven-tier precedence.

---

## 7. Phase Plan

### 7.1 Phase 1 — Foundation + CLI + MCP
- **REQ-200** Scaffold TypeScript project, BrainEngine interface, PGLite engine, Postgres engine.
- **REQ-201** Implement `scp init` (interactive setup), `scp doctor` (health check).
- **REQ-202** Implement page CRUD with frontmatter parsing, compiled-truth/timeline split.
- **REQ-203** Implement `scp serve` (MCP stdio + HTTP with OAuth 2.1).
- **REQ-204** Implement chokidar-based vault indexer (thread-safe file watching).
- **REQ-205** Implement users, MCP tokens, encrypted provider keys.
- **REQ-205a** Implement content-hash dedup on page write (SHA-256, skip indexing on duplicate).
- **REQ-205b** Implement Row-Level Security policies for all multi-tenant tables.
- **REQ-206** Implement REST API (Express) with admin endpoints.
- **REQ-207** Implement CLI: `scp capture`, `scp search`, `scp get`.
- **REQ-208** Phase 1 acceptance: user creates brain, imports markdown, queries via MCP.

### 7.2 Phase 2 — Hybrid RAG + Auto-Link + Agent
- **REQ-210** Implement chunking, AI gateway, embedding pipeline, HNSW index population.
- **REQ-210a** Implement 4-layer search dedup (exact slug, content-hash, near-duplicate cosine, URL citation).
- **REQ-210b** Implement conversation/memory data models and CRUD.
- **REQ-211** Implement BM25 tsvector search with pg_trgm.
- **REQ-212** Implement zero-LLM auto-link extraction (entity refs, typed links, frontmatter edges).
- **REQ-213** Implement hybrid search (keyword → vector → RRF → post-fusion boosts → reranker → dedup).
- **REQ-214** Implement the 30+ tool MCP surface and brain-first system prompt.
- **REQ-215** Implement `scp think` (synthesized answer with citations + gap analysis).
- **REQ-216** Phase 2 acceptance: graph queries return correct typed-link traversals; hybrid search beats vector-only on a fixture corpus.

### 7.3 Phase 3 — Skills + Ingestion + Schema Packs
- **REQ-220** Implement skills system: RESOLVER.md dispatcher, system namespace.
- **REQ-220a** Implement `OperationContext` pattern for request-scoped auth, source isolation, and audit correlation.
- **REQ-220b** Implement per-user skills namespace (user skills override system on match).
- **REQ-221** Implement schema packs: `scp-base`, `scp-recommended`, custom pack authoring.
- **REQ-222** Ship default ingestion skills: `idea-ingest`, `media-ingest`, `meeting-ingestion`.
- **REQ-223** Implement tiered entity enrichment.
- **REQ-224** Implement `scp schema` CLI (list, detect, suggest, use, review-candidates).
- **REQ-225** Phase 3 acceptance: pasted meeting transcript triggers ingestion skill, creates people/company pages with typed links.

### 7.4 Phase 4 — Memory Dream + Autopilot + Minions
- **REQ-230** Implement Minions job queue (Postgres-backed, crash-safe, two-phase persistence).
- **REQ-230a** Implement page versioning (`page_versions` table, version CRUD, restore).
- **REQ-231** Implement autopilot loop: sync → embed → extract → reconcile.
- **REQ-232** Implement nightly Memory Dream: stale-page detection, orphan detection, dead-link audit, citation audit, contradiction detection (compare takes/claims across pages for conflicting statements).
- **REQ-233** Implement `scp eval` (LongMemEval, replay, A/B, calibration curves for claim accuracy).
- **REQ-234** Phase 4 acceptance: autopilot runs continuously; Dream cycle produces a maintenance report.

### 7.5 Phase 5 — Web Search + Code Index + Workspaces + Intelligence
- **REQ-240** Implement web search skill (DuckDuckGo, Jina Reader, Wikipedia).
- **REQ-240a** Implement code index using tree-sitter WASM: parse source files into AST nodes (functions, classes, imports) stored in `code_symbols` table. Enable natural-language → code search via hybrid RAG over code chunks.
- **REQ-241** Implement project/workspace scoping (folder/tag-scoped contexts).
- **REQ-242** Implement vault intelligence endpoints (orphans, hubs, link suggestions, vault graph).
- **REQ-243** Phase 5 acceptance: scoped queries restrict RAG to a project; intelligence endpoints return correct counts.

### 7.6 Phase 6 — Admin Surfaces + Observability
- **REQ-250** Implement admin CLI: user CRUD, token management, embedding migration.
- **REQ-251** Implement Prometheus `/metrics`, structured JSON logs, audit log query.
- **REQ-252** Phase 6 acceptance: admin can manage users, view usage/cost, observe metrics.

### 7.7 Phase 7 — Platform Polish + MCP Registry
- **REQ-260** Implement MCP server registry (admin-configurable external MCP servers).
- **REQ-261** Implement DAG jobs (parent-child Minions), job cancellation, rate limits.
- **REQ-262** Implement backup automation and verified restore.
- **REQ-263** Phase 7 acceptance: admin adds external MCP server; DAG jobs run across restart.

### 7.8 Phase 8 — Electron Client + Streaming + Platform Hardening
- **REQ-270** Build the Electron/TypeScript/React desktop client (chat-first UI, split-pane editor, vault sidebar, system tray).
- **REQ-271** Implement Obsidian export, electron-store settings, auto-update via GitHub Releases.
- **REQ-272** Implement WebSocket gateway for real-time agent-server events (filesystem changes → push, job completion callbacks).
- **REQ-273** Implement SSE streaming for long-running operations (`/think/stream`, enrichment jobs, Dream cycle progress).
- **REQ-274** Implement backup automation with verified restore (pg_dump/pg_restore for Postgres, PGLite file snapshot for personal mode).
- **REQ-275** Phase 8 acceptance: end-to-end Electron walkthrough — login, chat, put_page, export. WebSocket push on file change. SSE streaming for think endpoint. Backup+restore round-trip passes.

---

## 8. CLI (First-Class Surface)

The CLI is the primary user surface (not just admin tools):

### 8.1 Core Commands

| Command | Purpose |
|---------|---------|
| `scp init` | Create/configure a brain (interactive or `--pglite`/`--supabase`) |
| `scp doctor` | Health check — verifies DB, config, embeddings, graph integrity |
| `scp serve` | Start MCP server (stdio default, `--http` for HTTP mode with OAuth) |
| `scp capture` | Quick page create (stdin, file, or inline text) |
| `scp search` | Raw hybrid search — returns ranked pages with scores |
| `scp think` | Synthesized answer with citations + gap analysis |
| `scp import` | Bulk import markdown files from a directory |
| `scp embed` | Manage embeddings (stale re-embed, provider migration) |
| `scp schema` | Schema pack management (list, detect, suggest, use) |
| `scp eval` | Run benchmarks (LongMemEval, replay, A/B comparison, calibration curves) |
| `scp admin` | User/token/usage management |
| `scp skillpack` | Skillpack management (install, list, remove, publish, check) |
| `scp remote` | Remote brain operations (ping, doctor) |

### 8.2 CLI Architecture

```typescript
// cli.ts — main entry point
// Uses commander or clack for subcommand routing
// Calls BrainEngine methods directly (no MCP needed for local CLI)
// All DB-bound commands go through engine-factory.ts
```

---

## 9. MCP Server

### 9.1 Transports
- **stdio mode**: For Claude Code, Cursor, Windsurf — spawned as subprocess.
- **Streamable HTTP mode**: For Claude Desktop, Perplexity, ChatGPT — HTTP server with OAuth 2.1.

### 9.2 Auth
- OAuth 2.1 with Dynamic Client Registration (DCR)
- PKCE for browser-based clients
- Scope-gated: `read` / `write` / `admin`
- Per-client source scoping (write to one source, federated reads across multiple)

### 9.3 Tools Surface (30+)

| Tool | Description |
|------|-------------|
| `brain_search` | Hybrid search across brain |
| `brain_get_page` | Get page by slug (with fuzzy resolution) |
| `brain_put_page` | Create/update page with auto-link |
| `brain_delete_page` | Soft-delete a page |
| `brain_list_pages` | List pages with filters |
| `brain_graph_query` | Graph traversal by slug |
| `brain_traverse_paths` | Edge-based graph traversal |
| `brain_capture` | Quick page create |
| `enrich_extract` | Run entity extraction |
| `skill_run` | Execute a skill by name |
| `skill_list` | List available skills |
| `recipe_list` | List data-research recipes |
| `recipe_run` | Execute a recipe |
| `jobs_list` | List active/completed jobs |
| `jobs_submit` | Submit a new job |
| `jobs_cancel` | Cancel a running job |
| `maintain_orphans` | List orphan pages |
| `maintain_dead_links` | List broken wikilinks |
| `maintain_dream` | Trigger manual dream cycle |
| `admin_create_user` | (admin scope) Create user |
| `admin_list_tokens` | (admin scope) List MCP tokens |
| `admin_revoke_token` | (admin scope) Revoke token |
| `schema_list` | List available schema packs |
| `schema_use` | Activate a schema pack |
| `schema_detect` | Propose page types from filesystem |
| `skillpack_install` | Install a skillpack from path or URL |
| `skillpack_list` | List installed skillpacks |
| `skillpack_remove` | Remove a skillpack |
| `skillpack_check` | Validate skillpack integrity |

---

## 10. REST API

### 10.1 Design
- Express 5 embedded in the CLI binary
- OpenAPI spec auto-generated from route definitions
- All routes consumed by MCP clients and automation scripts
- Parallel to MCP surface (same service layer)

### 10.2 Full Endpoint Catalog

All endpoints are prefixed with `/api/v1`. Admin endpoints require `role=admin`. All responses are JSON with standard error shape `{ error: string, code: string, requestId: string }`.

**Auth**
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/login` | JWT login (password) |
| POST | `/auth/refresh` | Refresh JWT session |
| POST | `/auth/logout` | Invalidate session |
| POST | `/auth/oauth/authorize` | OAuth 2.1 authorization |
| POST | `/auth/oauth/token` | OAuth 2.1 token exchange |
| GET | `/auth/oauth/register` | DCR client registration |

**Pages**
| Method | Path | Description |
|--------|------|-------------|
| GET | `/pages` | List pages (filters: source_id, page_type, tag, query) |
| GET | `/pages/:slug` | Get page by slug |
| PUT | `/pages/:slug` | Create or update page |
| DELETE | `/pages/:slug` | Soft-delete page |
| POST | `/pages/:slug/restore` | Restore soft-deleted page |
| GET | `/pages/:slug/versions` | List version history |
| GET | `/pages/:slug/versions/:version` | Get specific version |
| POST | `/pages/:slug/versions/:version/restore` | Restore version |
| GET | `/pages/:slug/timeline` | Get timeline entries |
| POST | `/pages/:slug/timeline` | Add timeline entry |
| GET | `/pages/:slug/links` | Get outbound links |
| GET | `/pages/:slug/backlinks` | Get inbound links |
| GET | `/pages/:slug/takes` | Get takes/claims |
| POST | `/pages/:slug/takes` | Add take |

**Search & Query**
| Method | Path | Description |
|--------|------|-------------|
| GET | `/search` | Hybrid search (params: q, mode, source_id, limit) |
| POST | `/think` | Synthesized answer with citations |
| POST | `/think/stream` | SSE-streamed synthesized answer |
| GET | `/graph/query/:slug` | Graph traversal by slug |
| GET | `/graph/traverse` | Edge-based graph traversal (params: from, type, depth) |
| GET | `/graph/neighbors/:slug` | Direct neighbors in graph |

**Conversations**
| Method | Path | Description |
|--------|------|-------------|
| GET | `/conversations` | List user's conversations |
| POST | `/conversations` | Create conversation |
| GET | `/conversations/:id` | Get conversation with messages |
| DELETE | `/conversations/:id` | Delete conversation |
| POST | `/conversations/:id/messages` | Add message |
| GET | `/conversations/:id/messages` | List messages |

**Skills & Schema**
| Method | Path | Description |
|--------|------|-------------|
| GET | `/skills` | List available skills |
| POST | `/skills/:name/run` | Execute a skill |
| GET | `/schema` | List schema packs |
| POST | `/schema/use` | Activate a schema pack |
| POST | `/schema/detect` | Propose page types |
| POST | `/enrich/extract` | Run entity extraction on a page |

**Jobs**
| Method | Path | Description |
|--------|------|-------------|
| GET | `/jobs` | List jobs (filters: status, type) |
| POST | `/jobs` | Submit a job |
| GET | `/jobs/:id` | Get job status |
| POST | `/jobs/:id/cancel` | Cancel a job |

**Admin (admin only)**
| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/users` | List users |
| POST | `/admin/users` | Create user |
| DELETE | `/admin/users/:id` | Deactivate user |
| GET | `/admin/tokens` | List MCP tokens |
| POST | `/admin/tokens` | Create MCP token |
| DELETE | `/admin/tokens/:id` | Revoke token |
| GET | `/admin/usage` | Usage stats (cost, requests by user/provider) |
| GET | `/admin/usage/:user_id` | Per-user usage breakdown |
| GET | `/admin/metrics` | Prometheus `/metrics` format |
| GET | `/admin/health` | Deep health check (DB, embeddings, graph) |
| POST | `/admin/embed/migrate` | Migrate embeddings to new provider/dimensions |
| GET | `/admin/audit-log` | Query audit log (filters: user, action, date range) |
| POST | `/admin/dream` | Trigger manual Dream cycle |
| GET | `/admin/report/maintenance` | Latest maintenance report |

**Watcher / System**
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check |
| POST | `/capture` | Quick page create (minimal fields) |
| GET | `/intelligence/orphans` | List orphan pages |
| GET | `/intelligence/hubs` | List hub pages (high backlink count) |
| GET | `/intelligence/dead-links` | List broken wikilinks |
| GET | `/intelligence/suggest-links` | Link suggestions |

---

## 11. Hybrid RAG Pipeline

### 11.1 Pipeline Stages

```
query → intent classify (regex) → expansion (opt-in, Haiku)
       → hybrid search:
           ├── vector (HNSW on chunk embeddings)
           ├── keyword (BM25 via tsvector)
           └── RRF fusion → top N
        → post-fusion boosts:
            ├── backlink boost (log-compressed)
            ├── salience boost (emotional weight + takes)
            ├── recency boost (per-prefix half-life decay)
            ├── source-tier boost (SQL CASE: curated sources weighted higher than bulk)
            └── graph signals (adjacency/cross-source/hub detection)
       → reranker (opt-in, ZeroEntropy zerank-2)
       → token budget enforcement (per-mode bundle)
        → deduplication (4-layer: exact slug, content-hash overlap, near-duplicate embedding cosine >0.97, same-url citation dedup)
```

### 11.2 Search Modes
- **conservative**: No expansion, no reranker, lower limit
- **balanced** (default): Reranker on, expansion off, 20 results
- **tokenmax**: Expansion on, reranker on, 40 results, higher token budget

### 11.3 RRF Fusion

```typescript
const RRF_K = 60;
// Per-list K weighting for intent-aware fusion
function effectiveRrfK(baseK: number, weight: number): number {
  return baseK / weight;  // higher weight = lower K = more influence
}
```

### 11.4 Post-Fusion Boosts

Each boost stage mutates scores in place with bounded factors:
- **Backlink**: `factor = 1 + 0.05 * log(1 + count)` — range [1.0, ~1.23]
- **Recency**: `factor = 1 + coefficient * halflife / (halflife + daysOld)` — per-prefix config
- **Salience**: `factor = 1 + k * log(1 + score)` — k=0.15 (on) or 0.30 (strong)
- **Graph signals**: adjacency boost + cross-source boost + session demote
- **Source-tier boost**: SQL CASE expression assigns higher weight to curated sources (e.g., manual notes, writing) over bulk-imported ones (e.g., web captures) — range [1.0, 1.5]

A floor-ratio gate (default 0.85) prevents weak results from leapfrogging legitimate hits.

---

## 12. AI Gateway

### 12.1 Architecture

```
configureGateway(config) → reads provider config
  ├── embed(texts)        → embedding across any supported provider
  ├── embedOne(text)      → convenience wrapper
  ├── embedQuery(text)    → query-side embedding (asymmetric encoding)
  ├── expand(query)       → query expansion (Haiku)
  ├── chat(messages)      → LLM chat (with fallback chain)
  ├── rerank(query, docs) → cross-encoder reranking
  └── isAvailable(tp)     → provider availability check
```

### 12.2 Recipe System

Each provider is a "recipe" with:
- `id`: unique provider name
- `implementation`: `native-openai`, `native-anthropic`, `native-google`, `openai-compatible`
- `touchpoints`: which capabilities (embedding, expansion, chat, reranker)
- `models`: allowed model IDs
- `auth_env`: required/optional env vars
- `base_url_default`: default API base URL
- Provider-specific compat shims (Voyage base64 translation, ZeroEntropy URL rewrite)

### 12.3 Supported Providers (at launch)
- OpenAI (text-embedding-3-small/large, GPT-4, GPT-4o)
- Anthropic (Claude Haiku, Sonnet, Opus)
- Google (Gemini, Gecko embeddings)
- ZeroEntropy (zembed-1, zerank-2) — DEFAULT
- Voyage (voyage-3/large/code)
- OpenRouter (unified API)
- Ollama (local, fully offline)
- OpenAI-compatible (any provider)
- LiteLLM proxy (if user runs one separately)

---

## 13. Zero-LLM Auto-Link Extraction

### 13.1 Extraction Pipeline

On every `put_page`:

1. Extract entity refs from markdown body:
   - `[Name](path)` markdown links → entity refs
   - `[[dir/slug]]` Obsidian wikilinks → entity refs
   - `[[source-id:dir/slug]]` qualified wikilinks → entity refs
   - Bare slug references in prose → entity refs

2. Extract frontmatter-derived edges:
   - `company: "Stripe"` on person pages → `works_at` edge
   - `key_people: [Alice, Bob]` on company pages → `works_at` (incoming)
   - `investors: [Sequoia]` on deal pages → `invested_in` (incoming)
   - `attendees: [Alice]` on meeting pages → `attended` (incoming)

3. Typed link inference (deterministic, zero LLM):
   - Per-edge context window (~240 chars) matched against verb patterns
   - Page-role priors (partner page → company refs bias to `invested_in`)
   - Fallthrough to `mentions` when no pattern matches

### 13.2 Edge Types
| Edge Type | Direction | Source |
|-----------|-----------|--------|
| `works_at` | person → company | `company:` frontmatter, `works at` verb |
| `founded` | person → company | `founded:` frontmatter, `founded` verb |
| `invested_in` | company/fund/people → company | `investors:` frontmatter, investment verbs |
| `advises` | person → company | advisory verbs, `advisor` role prior |
| `attended` | person → meeting | `attendees:` frontmatter, `attended` verb |
| `mentions` | any → any | fallthrough reference |
| `related_to` | any → any | `see_also:` frontmatter |

### 13.3 Slug Resolution
- Priority: exact getPage → dir-hint + slugify → pg_trgm fuzzy match → hybrid search (live mode only)
- Batch mode (migration) skips the search fallback for deterministic backfill
- Per-resolver cache: same name → same slug across one extract run

---

## 14. Agent System

### 14.1 Agent Runner
- ReAct loop: Thought → Action → Observation
- Brain-first system prompt (query local brain before any external API call)
- 30+ MCP tools available to the agent
- Refusal-on-insufficient-evidence enforced at prompt level

### 14.2 Minions (Sub-Agent Queue)
- BullMQ-style, Postgres-native job queue
- Durable subagents (LLM tool loops that survive crashes via two-phase pending→done persistence)
- Shell jobs with audit trail
- Child jobs with cascading timeouts
- Rate leases for outbound providers
- Attachments via S3/Supabase storage

---

## 15. Skills System

### 15.1 Dispatcher
- `RESOLVER.md` at the root of the skills directory
- Maps trigger patterns (file path, user message intent, MCP tool call) to skill names
- System namespace only (Phase 1)

### 15.2 Skill Format
```markdown
---
name: meeting-ingestion
description: Process meeting transcripts into structured pages
trigger: "mermaid timeline"
model: cheap  # provider tier hint
---
## Workflow
1. Read the transcript from the user's message
2. Extract attendees, date, key decisions
3. Create/update people pages for attendees
4. Create a meeting page with compiled-truth summary
5. Add timeline entries for key decisions
```

### 15.3 Default Skill Pack (43 skills)

The system ships with 43 curated skills (aligned with gbrain's curated set), stored in the system namespace. All skills use the same YAML-frontmatter + markdown-body format.

**Capture & Ingest (9)**
- `capture` — quick capture of ideas, links, articles, tweets
- `idea-ingest` — capture ideas with typed links
- `media-ingest` — process video/audio/PDF/screenshots
- `image-ingest` — OCR extraction from images (screenshots, photos of documents)
- `meeting-ingestion` — process meeting transcripts
- `ingest` — generic file/directory ingestion
- `webhook-transforms` — process incoming webhook payloads
- `signal-detector` — detect and capture signals from various inputs
- `data-research` — structured data research workflows

**Enrich & Query (5)**
- `enrich` — tiered entity enrichment
- `query` — brain query and synthesis
- `cross-modal-review` — cross-reference across page types
- `reports` — generate periodic reports
- `briefing` — produce daily/standing briefings

**Maintain & Audit (7)**
- `maintain` — brain maintenance operations
- `citation-fixer` — fix broken citations
- `brain-ops` — vault operations and maintenance
- `soul-audit` — vault health and completeness audit
- `quality` — writing conventions and quality checks
- `smoke-test` — run smoke tests
- `testing` — test workflows

**Setup & Config (6)**
- `setup` — initial brain setup
- `migrate` — data migration workflows
- `cron-scheduler` — schedule recurring tasks
- `daily-task-manager` — manage daily tasks
- `daily-task-prep` — prepare daily context
- `model-routing` — which model to use per task

**Skills Management (5)**
- `skill-creator` — scaffold new skills
- `skillify` — convert content into skills
- `skillpack-check` — validate skill pack integrity
- `skillpack-install` — install skillpacks
- `skillpack-publish` — publish skillpacks

**Agent & Job (5)**
- `minion-orchestrator` — manage sub-agent DAGs
- `repo-architecture` — repository structure conventions
- `publish` — publish content workflows
- `zettelkasten` — Zettelkasten atomic note workflow
- `brain-first` — brain-first lookup discipline

**Utility (6)**
- `idea` — idea management
- `project` — project management
- `task` — task management
- `note` — note-taking workflows
- `doc` — document management
- `template` — template management

### 15.4 Installable Skillpacks

Skillpacks are distributable bundles of skills. A skillpack is a directory or `.tar.gz` archive containing `MANIFEST.md` + `SKILL.md` files. The manifest declares:
- `name`, `version`, `description`
- `min_scp_version` — minimum Smart Copilot version
- `dependencies` — other required skillpacks
- `conflicts` — incompatible skillpacks
- `skills[]` — list of included skills with trigger summaries

CLI commands:
```
scp skillpack install <path|url>   # install from local path or URL (validates RSL, copies SKILL.md files)
scp skillpack list                  # list installed skillpacks
scp skillpack remove <name>         # remove a skillpack
scp skillpack publish <path>        # publish to registry (optional, Phase 7)
scp skillpack check <path>          # validate skillpack integrity
```

Installation copies skills into the system namespace (`skills/`) or user override directory. Schema compatibility is validated at load time. The 43-system-skill pack ships embedded in the npm package.

---

## 16. Schema Packs

### 16.1 Concept
A schema pack declares:
- `page_types[]` — name + path_prefixes + extractable fields + edge types
- `takes_kinds[]` — allowed claim types
- `extends` — parent pack to inherit from

### 16.2 Bundled Packs
- **scp-base** (default): `people/`, `companies/`, `concepts/`, `meetings/`, `daily/`, `originals/`, `writing/`, etc.
- **scp-recommended**: extends base with `source/`, `place/`, `trip/`, `conversation/`, `personal/`, `civic/`, `project/`, etc.

### 16.3 CLI
```
scp schema active                   # current pack
scp schema list                     # available packs
scp schema detect                   # propose types from filesystem
scp schema suggest                  # LLM-refined proposals
scp schema review-candidates        # human gate
scp schema use my-pack              # activate
```

### 16.4 Type Inference
```typescript
// Path prefix matching against schema pack
function inferTypeFromPack(filePath: string, pack: SchemaPack): PageType {
  for (const pt of pack.page_types) {
    for (const prefix of pt.path_prefixes) {
      if (filePath.includes(prefix)) return pt.name;
    }
  }
  return 'concept';
}
```

---

## 17. Minions (Durable Job Queue)

### 17.1 Architecture
- Postgres-native job queue (no Redis)
- Tables: `jobs`, `job_dependencies`, `job_logs`
- States: `pending → running → completed | failed | cancelled`
- Two-phase commit for crash safety: `pending → executing → done`

### 17.2 API
```
jobs.submit(type, payload, opts?) → jobId
jobs.cancel(jobId)
jobs.list(filters?) → Job[]
jobs.get(jobId) → Job
```

### 17.3 Features
- Parent-child DAGs (minion-orchestrator skill)
- Job cancellation (SIGTERM to subprocess, abort signal to LLM call)
- Rate limits (per-provider, per-user, per-job-type)
- Retry with exponential backoff
- Timeout enforcement

---

## 18. Memory Dream + Brain Maintenance

### 18.1 Dream Cycle (Nightly, 5 Phases)

1. **Stale detection**: Pages with `updated_at > 90 days` and no recent retrievals are flagged
2. **Consolidation**: Merge duplicate entities, fix citations, deduplicate takes
3. **Tag consistency**: Normalize tag casing, merge duplicate tags, remove orphan `page_tags` entries
4. **Synthesis**: Cross-reference disconnected pages, propose new links
5. **Cleanup**: Hard-delete soft-deleted pages older than 72h, archive old job logs

### 18.2 Autopilot (Continuous)

Runs on a timer (default: every 5 minutes):
```
sync: filesystem → DB (import new/changed files)
embed: re-embed stale chunks
extract: re-extract links + takes from changed pages
reconcile: detect filesystem/DB drift
orphans: scan for pages with zero inbound links
```

### 18.3 Maintenance Report
Emitted after each Dream cycle. Consumable via MCP and REST:
- Stale pages count + slugs
- Orphans count + slugs
- Dead links count + broken targets
- Citations fixed
- Contradictions found

---

## 19. Multi-Tenancy & Namespace Model

### 19.1 Sources
Every page belongs to a `source_id`. Slugs are unique per source, not globally.

Two-level hierarchy:
- **Brain** = database (one PGLite file or Postgres DB)
- **Source** = named content repo inside a brain

### 19.2 Isolation
- Personal sources: private to one user
- Shared sources: readable by all authenticated users
- Write access to shared sources governed by a global policy

### 19.3 Cross-Source References
- Unqualified wikilinks `[[dir/slug]]` resolve within current source → other local sources → shared
- Qualified wikilinks `[[source-id:dir/slug]]` target a specific source directly

---

## 20. Security & Trust Boundary

### 20.1 Trust Model
- **Local CLI** (`scp` on the host): full access
- **MCP stdio**: full access (subprocess of the user's agent)
- **MCP HTTP (remote)**: restricted — no shell execution, no destructive admin ops

### 20.2 Row-Level Security (Postgres Engine)

Postgres engine uses RLS to enforce multi-tenant isolation. PGLite engine mirrors the same logic at the application layer.

```sql
-- Pages: users see only their accessible sources
CREATE POLICY pages_source_isolation ON pages
  USING (source_id IN (SELECT accessible_sources(current_user_id())));

-- Conversations: private to owner
CREATE POLICY conversations_owner ON conversations
  USING (user_id = current_user_id());

-- Tokens: admin sees all, users see own
CREATE POLICY tokens_visibility ON mcp_tokens
  USING (role = 'admin' OR user_id = current_user_id());

-- Admin tables: admin only
CREATE POLICY admin_only ON audit_logs
  USING (role = 'admin');
```

Source access is determined by a `user_sources` join table: personal sources are private to one user, shared sources are visible to all authenticated users, and write access is governed by the source's write policy.

### 20.3 Encryption
- Provider API keys encrypted at rest with AES-256-GCM
- JWT sessions for REST API
- OAuth 2.1 with PKCE for MCP HTTP

### 20.4 Admin Operations
- Admin REST endpoints require `role='admin'` AND fresh authentication
- Admin CLI commands require the user be in the `admin` group

---

## 21. Deployment Topologies

### 21.1 Topology 1 — Single Brain (Personal)

```
┌────────────────┐
│   one machine  │
│  ┌──────────┐  │
│  │  scp    │──┼──→  ~/.smartcopilot/  →  PGLite or Supabase
│  │   CLI    │  │
│  └──────────┘  │
└────────────────┘
```

One local DB. All commands work directly. `scp serve` exposes to MCP.

### 21.2 Topology 2 — Cross-Machine Thin Client

```
┌────────────┐                    ┌──────────────────┐
│  agent     │                    │    brain-host    │
│  machine   │  HTTP MCP / OAuth  │  ┌────────────┐  │
│  (no DB)   │───────────────────→│  │  scp      │──┼──→ Postgres
│            │                    │  │ serve --http│  │   (Supabase)
└────────────┘                    │  └────────────┘  │
                                  │  (with autopilot)│
                                  └──────────────────┘
```

Agent consumes a brain hosted remotely. Local machine has no DB — queries, embeddings, indexing all happen on the host.

### 21.3 Topology 3 — Split Engine (Multi-Worktree)

```
┌─────────────────────────────────────────────┐
│  one machine                                 │
│  ┌─ worktree A ──────────────┐               │
│  │  SMARTCOPILOT_HOME=A/.smartcopilot │ → PGLite (A) │
│  │  scp serve --port 3001    │               │
│  └───────────────────────────┘               │
│  ┌─ worktree B ──────────────┐               │
│  │  SMARTCOPILOT_HOME=B/.smartcopilot │ → PGLite (B) │
│  │  scp serve --port 3002    │               │
│  └───────────────────────────┘               │
└─────────────────────────────────────────────┘
```

Per-Conductor-worktree code indexes. Artifacts (plans, learnings) go to a shared brain.

---

## 22. Phase 8 — Electron Client + Streaming + Platform Hardening

The final phase adds an optional desktop client and production hardening:

**Electron Desktop Client (optional)**
- React 18 + Lexical chat input + Tiptap editor
- Radix UI primitives, Lucide + Material Symbols icons
- DOMPurify clipboard sanitization
- Generated TS client from OpenAPI spec
- System tray + Quick Chat, Obsidian export, auto-update

**Streaming + Hardening**
- WebSocket gateway for real-time agent-server events
- SSE streaming for long-running operations
- Backup automation with verified restore

**Architecture note:** The CLI and MCP-capable agents (Hermes, etc.) remain the primary frontend throughout all phases. The Electron client is an optional addition for users who prefer a dedicated desktop application.

---

## 23. File Structure Reference

```
smart-copilot/
├── package.json              # npm workspace root
├── package-lock.json
├── tsconfig.json
├── src/
│   ├── cli.ts                # CLI entry point
│   ├── core/
│   │   ├── index.ts          # public exports
│   │   ├── engine.ts         # BrainEngine interface
│   │   ├── engine-factory.ts # createEngine() with dynamic import
│   │   ├── pglite-engine.ts  # PGLiteEngine implementation
│   │   ├── postgres-engine.ts# PostgresEngine implementation
│   │   ├── types.ts          # shared types (Page, Chunk, SearchResult, etc.)
│   │   ├── operations.ts     # high-level ops (put_page with auto-link)
│   │   ├── config.ts         # layered config resolution
│   │   ├── markdown.ts       # parse/serialize markdown (gray-matter)
│   │   ├── link-extraction.ts# entity extraction + typed link inference
│   │   ├── code-index.ts     # tree-sitter WASM code symbol extraction
│   │   ├── embed.ts          # embedding pipeline
│   │   ├── import-file.ts    # file import logic
│   │   ├── sync.ts           # filesystem↔DB sync utilities
│   │   ├── ai/
│   │   │   ├── gateway.ts    # AI gateway (embed, chat, expand, rerank)
│   │   │   ├── types.ts      # AI types (GatewayConfig, Recipe, Touchpoint)
│   │   │   ├── model-resolver.ts
│   │   │   ├── dims.ts       # embedding dimension tracking
│   │   │   ├── errors.ts     # AIConfigError, AITransientError
│   │   │   ├── defaults.ts   # default model/dimension constants
│   │   │   └── recipes/      # 16+ provider recipes
│   │   ├── search/
│   │   │   ├── hybrid.ts     # hybridSearch with full pipeline
│   │   │   ├── intent.ts     # regex-based query classification
│   │   │   ├── expansion.ts  # multi-query expansion
│   │   │   ├── rerank.ts     # cross-encoder reranker
│   │   │   ├── dedup.ts      # result deduplication
│   │   │   ├── token-budget.ts# per-mode token budget enforcement
│   │   │   ├── mode.ts       # search mode bundles
│   │   │   ├── query-cache.ts# semantic query cache
│   │   │   └── recency-decay.ts # per-prefix decay constants
│   │   ├── minions/
│   │   │   ├── queue.ts      # job queue core
│   │   │   ├── worker.ts     # job execution
│   │   │   └── types.ts      # job types
│   │   ├── agents/
│   │   │   └── ...
│   │   └── schema/
│   │       ├── pack.ts       # schema pack loading
│   │       └── defaults/     # scp-base, scp-recommended
│   ├── mcp/
│   │   ├── server.ts         # MCP server (stdio + HTTP)
│   │   ├── tools.ts          # tool exposure
│   │   └── auth.ts           # OAuth 2.1
│   ├── routes/
│   │   ├── admin.ts          # admin REST endpoints
│   │   ├── pages.ts          # page CRUD REST endpoints
│   │   └── search.ts         # search REST endpoints
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── fixtures/
├── clients/
│   └── desktop/              # Phase 8 (deferred)
└── skills/                   # bundled skills
    ├── RESOLVER.md
    └── <skill-name>/
        └── SKILL.md
```

---

## Appendix A — Key Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Engine abstraction | `BrainEngine` interface | Swap PGLite ↔ Postgres without code changes |
| AI provider | Vercel AI SDK (not LiteLLM) | Mature TypeScript SDK, broad provider coverage |
| Embedding default | ZeroEntropy zembed-1 | Faster (2.2x) and cheaper (2.6x) than OpenAI |
| Job queue | Custom Minions (not Bull/Agenda) | Zero Redis dependency, full Postgres back compat |
| OAuth | OAuth 2.1 + DCR + PKCE | Industry standard, required by ChatGPT MCP |
| Search | Intent-weighted RRF + boosts | Proven +31.4 P@5 over vector-only |
| Schema | Pack-based type inference | User-extendable, no engine fork needed |
| Deployment | Standard Node.js | `npm run start`, no runtime dependency |
