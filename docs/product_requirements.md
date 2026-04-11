# Smart Copilot — Product Requirements Document v1.0

**Product:** Smart Copilot
**Repository:** `smart-copilot` (monorepo: `server/` + `client/`)
**Document version:** PRD v1.0
**Derived from:** Client-Server Blueprint v0.2.3 (4 review cycles, 24 locked decisions)
**Status:** Ready for implementation — nothing built yet
**Target release:** v1.0
**Timeline:** 8 phases across 16 weeks
**Audience:** AI code assistants (Claude Code primary), human developers

---

## Table of Contents

1. [Executive Summary & Product Vision](#1-executive-summary--product-vision)
2. [Target Audience & User Personas](#2-target-audience--user-personas)
3. [Architecture & System Design](#3-architecture--system-design)
4. [Architecture Decisions — Final, Do Not Relitigate](#4-architecture-decisions--final-do-not-relitigate)
5. [Data Model & Database Schema](#5-data-model--database-schema)
6. [Epics, Features & Prioritization](#6-epics-features--prioritization)
7. [Phase 1 — Foundation (Weeks 1–2)](#7-phase-1--foundation-weeks-12)
8. [Phase 2 — RAG + Chat (Weeks 3–4)](#8-phase-2--rag--chat-weeks-34)
9. [Phase 3 — Editor + Zettelkasten (Weeks 5–6)](#9-phase-3--editor--zettelkasten-weeks-56)
10. [Phase 4 — Agent + Memory (Weeks 7–8)](#10-phase-4--agent--memory-weeks-78)
11. [Phase 5 — Web Search + Projects (Weeks 9–10)](#11-phase-5--web-search--projects-weeks-910)
12. [Phase 6 — Intelligence + Admin (Weeks 11–12)](#12-phase-6--intelligence--admin-weeks-1112)
13. [Phase 7 — Platform + Polish (Weeks 13–14)](#13-phase-7--platform--polish-weeks-1314)
14. [Phase 8 — Beta + Launch (Weeks 15–16)](#14-phase-8--beta--launch-weeks-1516)
15. [API Contract Reference](#15-api-contract-reference)
16. [SSE Streaming Protocol](#16-sse-streaming-protocol)
17. [Agent System — 22 Tools](#17-agent-system--22-tools)
18. [Memory Dream Consolidation System](#18-memory-dream-consolidation-system)
19. [Zettelkasten Workflows](#19-zettelkasten-workflows)
20. [HTML Sanitization Strategy](#20-html-sanitization-strategy)
21. [Indexing Strategy](#21-indexing-strategy)
22. [Server Configuration Reference](#22-server-configuration-reference)
23. [Docker Deployment](#23-docker-deployment)
24. [Backup Strategy](#24-backup-strategy)
25. [File Structure Reference](#25-file-structure-reference)
26. [UI Pages & Navigation](#26-ui-pages--navigation)
27. [Non-Functional Requirements & Success Metrics](#27-non-functional-requirements--success-metrics)
28. [Quality Gates by Phase](#28-quality-gates-by-phase)
29. [Assumptions, Constraints & Dependencies](#29-assumptions-constraints--dependencies)
30. [Risks & Mitigations](#30-risks--mitigations)
31. [Reference Codebases & Resources](#31-reference-codebases--resources)
32. [Glossary](#32-glossary)

---

## 1. Executive Summary & Product Vision

Smart Copilot is a **self-hosted AI knowledge management system** that brings Zettelkasten automation, a proactive knowledge agent, and hybrid RAG intelligence to markdown files. It consists of a **Python/FastAPI backend** running in a single Docker container (bundled with PostgreSQL 16 + pgvector) and an **Electron desktop client** connected via REST + SSE API.

The backend watches user markdown folders (which may be Obsidian vaults or plain directories), indexes all files into PostgreSQL with pgvector, and provides hybrid RAG search (vector + BM25 + wikilink graph traversal). An autonomous agent with 22 tools maintains the knowledge base: cleaning orphans, suggesting links, organizing files, and refactoring wikilinks when files move. A Memory Dream system automatically consolidates long-term memory, converting stale relative references to absolute timestamps, pruning contradictions, and keeping the memory index lean.

The Electron client is a **chat-first AI knowledge interface** with a split-pane Tiptap WYSIWYG editor. A system tray agent provides Quick Chat access via a global hotkey even when the main window is closed.

The system supports **3–10 users** on a homelab server with per-user private vaults and a shared team knowledge base — designed for small teams and families.

### 1.1 Core Principles (Non-Negotiable)

| ID | Principle | Implication |
|---|---|---|
| P1 | **Chat-first** | Chat panel is the primary interface; the editor is a companion |
| P2 | **Client-server separation** | One Docker container runs everything server-side; Electron client is thin |
| P3 | **Hybrid namespace from day one** | Private vaults + shared knowledge; never retrofit sharing later |
| P4 | **PostgreSQL does the heavy lifting** | Vector search, BM25, graph traversal — all in one database |
| P5 | **LiteLLM as library** | No separate LLM gateway service; provider translation in-process |
| P6 | **RAG quality over complexity** | Contextual enrichment + hybrid retrieval covers 90% of use cases |
| P7 | **API keys in the database** | Never in env vars or config files; managed via admin UI |
| P8 | **Memory hygiene via Dream cycles** | Long-term memory automatically consolidated, not left to rot |
| P9 | **Defense in depth** | Sanitize untrusted content on both client (DOMPurify) and server (nh3) |
| P10 | **Build must stay green** | Every commit passes CI |

### 1.2 Explicit Out-of-Scope for v1.0

- LightRAG integration (deferred; RAGBackend interface supports future addition)
- FIM autocomplete (no in-app editor cursor integration — editing is external)
- VS Code companion extension
- Mobile clients
- EPUB import
- Custom role hierarchies beyond admin/user

---

## 2. Target Audience & User Personas

### 2.1 Primary — Knowledge Worker (Alice)

**Role:** Zettelkasten practitioner, researcher, writer. **Vault:** 500–5,000 notes.
**Workflow:** Reads papers → imports as literature notes → splits into atomic Zettel → asks questions across vault → writes grounded in knowledge.
**Technical comfort:** Obsidian user, basic CLI, not a developer.

### 2.2 Secondary — Homelab Admin (Bob)

**Role:** Technical lead of a small team or family. **Responsibility:** Deploy, manage keys, monitor costs.
**Workflow:** `docker run` → configure API keys → create users → monitor dashboard.
**Technical comfort:** Docker, Linux, self-hosting.

### 2.3 Tertiary — Team Member (Carol)

**Role:** Non-admin user on shared instance. **Vault:** 100–1,000 notes.
**Workflow:** Open app → log in → chat with vault → save insights.
**Technical comfort:** Desktop app user, not technical.

---

## 3. Architecture & System Design

### 3.1 System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│              Electron Client (TypeScript)                     │
│  React + Tiptap + Lexical + Radix UI                        │
│  System tray agent + Quick Chat + Global hotkey              │
│  DOMPurify for clipboard HTML sanitization                   │
└──────────────────┬───────────────────────────────────────────┘
                   │ REST + SSE (OpenAPI spec)
                   │
┌──────────────────▼───────────────────────────────────────────┐
│   Single Docker Container (supervisord)                      │
│   ┌─────────────────────────────────────────────────────┐   │
│   │ Process 1: FastAPI Backend (Python)                  │   │
│   │  ├── LiteLLM (library — all LLM providers)          │   │
│   │  ├── File Watcher (watchdog) + Index Queue           │   │
│   │  ├── APScheduler (maintenance + Dream)               │   │
│   │  ├── RAG Engine (hybrid search)                      │   │
│   │  ├── Agent Runner (22 tools)                         │   │
│   │  ├── nh3 HTML sanitizer                              │   │
│   │  └── Web Search (DuckDuckGo + Jina + Wikipedia)     │   │
│   └─────────────────────────────────────────────────────┘   │
│   ┌─────────────────────────────────────────────────────┐   │
│   │ Process 2: PostgreSQL 16 + pgvector                  │   │
│   │  ├── Vector search (HNSW) + BM25 (tsvector)         │   │
│   │  ├── Wikilink graph (recursive CTEs)                 │   │
│   │  ├── Encrypted API keys + RLS isolation              │   │
│   │  └── Memory + Dream audit + Usage tracking           │   │
│   └─────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
External: OpenAI / Anthropic / Gemini / DeepSeek / OpenRouter / Ollama
```

### 3.2 Technology Stack — Backend

| Layer | Technology | Notes |
|---|---|---|
| Language | Python 3.12+ | |
| API | FastAPI | async, native SSE, OpenAPI generation |
| Database | PostgreSQL 16 + pgvector | bundled via supervisord |
| DB driver | asyncpg | async |
| ORM | SQLAlchemy 2.0 + Alembic | async ORM + migrations |
| LLM | LiteLLM (library import) | 100+ providers in-process |
| Background | asyncio + ProcessPoolExecutor | no Celery/Redis |
| Scheduling | APScheduler + SQLAlchemyJobStore | persistent across restarts |
| File watch | watchdog | inotify/polling |
| Markdown | markdown-it-py + python-frontmatter | |
| HTML sanitize | nh3 | Rust-based defense-in-depth |
| PDF | PyMuPDF (fitz) | lazy-loaded |
| DOCX | python-docx | |
| HTML clean | readability-lxml | after nh3 |
| HTTP | httpx | async |
| Auth | python-jose (JWT) | stateless |
| Encryption | cryptography (Fernet) | API keys at rest |
| Validation | Pydantic v2 | |
| Process mgr | supervisord | PostgreSQL + FastAPI |
| Codegen | openapi-typescript | TS client from spec |

### 3.3 Technology Stack — Frontend

| Layer | Technology | Notes |
|---|---|---|
| Platform | Electron (latest stable) | macOS + Windows; Linux dev only |
| Language | TypeScript 5.x | |
| Build | Vite (renderer) + esbuild (main) | Electron Forge |
| Package | pnpm | |
| UI | React 18 | |
| Chat input | Lexical | @mentions |
| Editor | Tiptap v2 + @tiptap/markdown | split-pane WYSIWYG |
| Panels | react-resizable-panels | |
| Components | Radix UI (15 primitives) | |
| Styling | CSS modules, `.sc-` prefix | |
| Icons | Lucide React | |
| Command | cmdk | |
| Diff | diff + react-diff-viewer-continued | |
| Graph | Cytoscape.js (lazy) | |
| Sanitize | DOMPurify | clipboard |
| Update | electron-updater | GitHub Releases |
| API | Generated from OpenAPI | auto-synced |

### 3.4 OpenAPI Spec Sync

Backend auto-generates `openapi.json` from FastAPI routes. Client runs `pnpm codegen` → fetches spec → generates TypeScript types via `openapi-typescript`. Pre-commit hook. CI fails if types don't match committed. Spec versioned as `docs/openapi.json`.

### 3.5 Multi-Tenancy

Namespace: `private` (per-user) or `shared` (all users). Filesystem: `/vaults/private/{username}/` and `/vaults/shared/`. Publishing = intentional file move. Cross-namespace links: `[[shared/Topic]]`. Conversations, memories, usage, keys = always private.

---

## 4. Architecture Decisions — Final, Do Not Relitigate

> **FOR AI AGENTS:** These 24 decisions are **locked**. Code contradicting them is a bug. Do not propose alternatives.

### Decision 1 — PostgreSQL-only RAG backend
All retrieval in PostgreSQL + pgvector: vector (HNSW), BM25 (tsvector), wikilink graph (recursive CTEs) — single query. `RAGBackend` interface allows future graph-based extension.

### Decision 2 — Hybrid retrieval + contextual enrichment
```
final_score = (0.5 × vector_cosine) + (0.3 × BM25) + (0.2 × wikilink_proximity)
```
RRF scoring. Enrichment prepends: title, folder, tags, backlinks, outlinks. Note type controls enrichment level. Strip tasks/queries/calendar before embedding.

### Decision 3 — LiteLLM as library
```python
from litellm import acompletion, aembedding
```
In-process, zero network hops. Callbacks log to PostgreSQL.

### Decision 4 — Shared tables + RLS
Single table set with `user_id` + `namespace`. No per-user schemas.

### Decision 5 — Hybrid namespace from day one
`/vaults/private/{username}/` + `/vaults/shared/`. Never retrofit.

### Decision 6 — Single container via supervisord
No Redis, no Celery. `EXTERNAL_DB=true` + `DATABASE_URL` for external PostgreSQL.

### Decision 7 — API keys encrypted in database
Fernet encryption. `ENCRYPTION_KEY` env var is only secret. `encrypted_key` NEVER returned to client.
```python
fernet = Fernet(os.environ["ENCRYPTION_KEY"])
def encrypt_key(plain_key: str) -> str:
    return fernet.encrypt(plain_key.encode()).decode()
def decrypt_key(encrypted_key: str) -> str:
    return fernet.decrypt(encrypted_key.encode()).decode()
```
Resolution: user key → shared key → error. Track `key_type`: personal/shared.

### Decision 8 — SSE for streaming, REST for CRUD
No WebSocket. POST-initiated SSE for chat.

### Decision 9 — Split-pane: chat left, editor right
Editor collapses when no file open.

### Decision 10 — Original notes kept as literature (default)
Keep (default) / Archive / Delete (double confirmation).

### Decision 11 — Two RAG contexts
`knowledge` (permanent), `citation` (literature), `all`. Project notes: frontmatterQuery only.

### Decision 12 — Prompt-scoped mode pills
Single-select, cleared after send. Ask/Write/Research/Focus/custom.
```python
class ModeConfig:
    id: str; label: str; is_built_in: bool; system_prompt: str
    is_modified: bool; rag_scope: str; web_search: bool; agent_tools: bool
```

### Decision 13 — Model selector via LiteLLM identifiers
Sticky per conversation. New conversation → project default. Each message records model_id.

### Decision 14 — Chat history in PostgreSQL, vault export user-triggered
Export path: `{vault}/private/{user}/{folder}/{project?}/{file}.md`

### Decision 15 — Zettel source backlink always written
`source: "[[Title]]"` persists even if original deleted.

### Decision 16 — Citation markers `[1]` `[2]` rendered as badges
System prompt instructs markers. API returns citations array.

### Decision 17 — Watcher bypassed for app-initiated writes
Write + index directly. Watcher skips matching content_hash.

### Decision 18 — Memory Dream 4-phase consolidation
See Section 18.

### Decision 19 — Admin dashboard in-app
No external dashboard.

### Decision 20 — Embedding dimension via admin UI + migration pipeline
`system_config` table = source of truth. Crash recovery. Admin-only at API/settings/config levels.

### Decision 21 — Two roles: admin, user
First user = admin. `require_admin` FastAPI dependency. Password reset admin-mediated.
```python
async def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
```

### Decision 22 — VaultRegistry path resolution
```python
class VaultRegistry:
    _mappings: dict[str, tuple[UUID, str]]
    async def rebuild(self, db):
        self._mappings[f"{base}/shared/"] = (SYSTEM_USER_ID, "shared")
        for user in users: self._mappings[f"{base}/private/{user.username}/"] = (user.id, "private")
    def resolve(self, filepath) -> tuple[UUID, str] | None:
        for prefix, identity in self._mappings.items():
            if filepath.startswith(prefix): return identity
        return None
```

### Decision 23 — RLS SET/RESET every session
```python
@asynccontextmanager
async def get_db_session(user_id: UUID):
    async with async_session_factory() as session:
        await session.execute(text("SET app.current_user_id = :uid"), {"uid": str(user_id)})
        try:
            yield session; await session.commit()
        except: await session.rollback(); raise
        finally:
            await session.execute(text("RESET app.current_user_id"))
```

### Decision 24 — JWT on every API call
safeStorage for tokens. 24h access, 30d refresh. SSE: header or body. CSRF not needed (Bearer only).

---

## 5. Data Model & Database Schema

> **FOR AI AGENTS:** Implement exactly via Alembic. The `enrichment_hash`, RLS policies, and denormalized `messages.user_id` are deliberate — do not simplify.

```sql
CREATE TABLE system_config (key TEXT PRIMARY KEY, value JSONB NOT NULL, updated_at TIMESTAMPTZ DEFAULT now());

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE, password_hash TEXT NOT NULL, role TEXT DEFAULT 'user',
    must_change_password BOOLEAN DEFAULT false, last_dream_at TIMESTAMPTZ,
    sessions_since_dream INT DEFAULT 0, created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID REFERENCES users(id),
    provider TEXT NOT NULL, encrypted_key TEXT NOT NULL, display_hint TEXT,
    is_valid BOOLEAN DEFAULT true, last_tested_at TIMESTAMPTZ, created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (user_id, provider)
);

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID NOT NULL REFERENCES users(id),
    namespace TEXT NOT NULL DEFAULT 'private', path TEXT NOT NULL, content_hash TEXT NOT NULL,
    enrichment_hash TEXT, note_type TEXT DEFAULT 'permanent', frontmatter JSONB DEFAULT '{}',
    title TEXT, folder TEXT, tags TEXT[] DEFAULT '{}', word_count INT DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT now(), UNIQUE (user_id, namespace, path)
);

CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID NOT NULL REFERENCES users(id),
    namespace TEXT NOT NULL DEFAULT 'private', document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL, enriched_content TEXT, embedding vector(1536), embedding_model TEXT,
    content_tsvector tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED, chunk_index INT DEFAULT 0
);
CREATE INDEX chunks_hnsw ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX chunks_fts ON chunks USING gin (content_tsvector);
CREATE INDEX chunks_user_ns ON chunks (user_id, namespace);
CREATE INDEX chunks_document ON chunks (document_id);

CREATE TABLE wikilinks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), source_doc UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    target_doc UUID REFERENCES documents(id) ON DELETE SET NULL, target_name TEXT NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id), namespace TEXT NOT NULL DEFAULT 'private'
);
CREATE INDEX wikilinks_source ON wikilinks (source_doc);
CREATE INDEX wikilinks_target ON wikilinks (target_doc);
CREATE INDEX wikilinks_user ON wikilinks (user_id);

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID NOT NULL REFERENCES users(id),
    title TEXT, model_id TEXT, mode_id TEXT, project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    exported_path TEXT, never_export BOOLEAN DEFAULT false, web_search_enabled BOOLEAN DEFAULT false,
    relevant_note_enabled BOOLEAN DEFAULT true, created_at TIMESTAMPTZ DEFAULT now(), updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX conversations_user_updated ON conversations (user_id, updated_at DESC);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id), role TEXT NOT NULL, content TEXT NOT NULL,
    model_id TEXT, mode_id TEXT, citations JSONB, temperature FLOAT, max_tokens INT,
    system_prompt_override TEXT, created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX messages_conversation ON messages (conversation_id, created_at);
CREATE INDEX messages_user ON messages (user_id);

CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID NOT NULL REFERENCES users(id),
    content TEXT NOT NULL, embedding vector(1536), source_conversation_id UUID REFERENCES conversations(id),
    absolute_date TEXT, last_recalled_at TIMESTAMPTZ, recall_count INT DEFAULT 0,
    is_archived BOOLEAN DEFAULT false, created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX memories_hnsw ON memories USING hnsw (embedding vector_cosine_ops);
CREATE INDEX memories_user ON memories (user_id);
CREATE INDEX memories_active ON memories (user_id, is_archived) WHERE is_archived = false;

CREATE TABLE dream_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID NOT NULL REFERENCES users(id),
    dream_run_at TIMESTAMPTZ NOT NULL, phase TEXT NOT NULL, action TEXT NOT NULL,
    memory_id UUID REFERENCES memories(id), old_content TEXT, new_content TEXT, reason TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID NOT NULL REFERENCES users(id),
    name TEXT NOT NULL, include_folders TEXT[] DEFAULT '{}', exclude_folders TEXT[] DEFAULT '{}',
    tags TEXT[] DEFAULT '{}', system_prompt TEXT, default_model_id TEXT, created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE operation_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID NOT NULL REFERENCES users(id),
    operation_type TEXT NOT NULL, steps JSONB NOT NULL, undone BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE llm_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID REFERENCES users(id),
    model TEXT NOT NULL, provider TEXT NOT NULL, prompt_tokens INT, completion_tokens INT,
    cost_usd NUMERIC(10,6), latency_ms INT, status TEXT, error_message TEXT,
    purpose TEXT, key_type TEXT DEFAULT 'shared', created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX llm_usage_user_date ON llm_usage (user_id, created_at);
CREATE INDEX llm_usage_key_type ON llm_usage (user_id, key_type);

CREATE TABLE index_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID REFERENCES users(id),
    namespace TEXT NOT NULL, event_type TEXT NOT NULL, file_path TEXT NOT NULL,
    chunks_created INT, embedding_model TEXT, processing_ms INT, created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE system_health (
    id SERIAL PRIMARY KEY, db_size_bytes BIGINT, total_chunks INT, total_documents INT,
    index_queue_depth INT, pg_connections_active INT, recorded_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE user_settings (
    user_id UUID PRIMARY KEY REFERENCES users(id), settings JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- RLS Policies (12 tables)
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE wikilinks ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE dream_audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE operation_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE llm_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;

-- Content: own + shared
CREATE POLICY tenant_isolation ON documents USING (namespace = 'shared' OR user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY tenant_isolation ON chunks USING (namespace = 'shared' OR user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY tenant_isolation ON wikilinks USING (namespace = 'shared' OR user_id = current_setting('app.current_user_id')::uuid);
-- Private: own only
CREATE POLICY private_only ON conversations USING (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY private_only ON messages USING (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY private_only ON memories USING (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY private_only ON dream_audit_log USING (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY private_only ON projects USING (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY private_only ON operation_log USING (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY private_only ON llm_usage USING (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY private_only ON user_settings USING (user_id = current_setting('app.current_user_id')::uuid);
-- API keys: own + shared (NULL user_id)
CREATE POLICY api_key_access ON api_keys USING (user_id IS NULL OR user_id = current_setting('app.current_user_id')::uuid);
```

---

## 6. Epics, Features & Prioritization

### 6.1 Epic Map

| Epic | Description | Phases |
|---|---|---|
| E1: Foundation | Docker, auth, schema, file watcher | 1 |
| E2: RAG & Chat | Hybrid search, streaming chat, citations | 2 |
| E3: Editor & Zettelkasten | Tiptap editor, note splitting, document import | 3 |
| E4: Agent & Memory | 22-tool agent, Memory Dream, clipboard protocol | 4 |
| E5: Web Search & Projects | Web search, project scoping, cross-referencing | 5 |
| E6: Intelligence & Admin | Dashboards, vault health, embedding migration | 6 |
| E7: Platform | Tray agent, Quick Chat, global hotkey, auto-update | 7 |
| E8: Launch | Beta testing, performance, documentation | 8 |

### 6.2 MoSCoW Prioritization

**Must Have** — v1.0 blocker:
F-AUTH-01/02, F-SCHEMA-01, F-DOCKER-01, F-IDX-01/02, F-RAG-01/02, F-CHAT-01/02, F-LLM-01, F-SETTINGS-01, F-ZETT-01, F-AGENT-01/02/03, F-MEM-01/02, F-ADMIN-01

**Should Have** — significant value:
F-CHAT-03/04, F-RAG-03, F-EDITOR-01, F-ZETT-02/03, F-AGENT-04/05/06/07, F-MEM-03, F-SEARCH-01, F-PROJ-01, F-VAULT-01, F-ADMIN-02/03, F-BACKUP-01

**Could Have** — nice for v1.0:
F-CHAT-05, F-PLATFORM-01/02/03/04, F-AGENT-08/09/10/11, F-INTEL-01/02/03, F-DASH-01, F-SEARCH-02/03

---

## 7. Phase 1 — Foundation (Weeks 1–2)

**Backend:** Docker container with supervisord + wait-for-pg.sh, Alembic migrations for full schema (including system_config, enrichment_hash), auth system (JWT, register, login, password change, require_admin, must_change_password), user management CRUD + password reset, VaultRegistry + file watcher (watchdog) + IndexQueue, markdown parser (frontmatter + wikilink extraction), NoteTypeClassifier.

**Frontend:** Electron shell with Forge + Vite, Login/connection setup page with first-run admin creation, API client generated from OpenAPI spec, auth flow (JWT safeStorage, refresh, forced password change).

### F-DOCKER-01: Single Container Deployment

**User Stories:**

**US-1.1:** As a homelab admin, I want to start Smart Copilot with a single `docker run` command.
- AC1: `docker run -d -p 8000:8000 -v smart-copilot-data:/var/lib/postgresql/data -v /path/to/vaults:/vaults -e ENCRYPTION_KEY=... smart-copilot:latest` starts both PostgreSQL and FastAPI
- AC2: `GET /health` returns 200 within 30 seconds of container start
- AC3: PostgreSQL ready before FastAPI starts (wait-for-pg.sh polls `pg_isready`)
- AC4: Alembic migrations run automatically before FastAPI begins serving
- AC5: HEALTHCHECK fails gracefully and triggers restart if backend is down

**US-1.2:** As a homelab admin, I want to use an external PostgreSQL instance.
- AC1: `EXTERNAL_DB=true` + `DATABASE_URL=postgresql+asyncpg://...` skips internal PostgreSQL
- AC2: Backend logs clear error if pgvector extension missing on external instance

### F-SCHEMA-01: Database Schema with RLS

**US-1.3:** As the system, I must enforce data isolation so users only see their own private data plus shared content.
- AC1: All 12 RLS-protected tables have policies enabled (see Section 5)
- AC2: Content tables use `namespace = 'shared' OR user_id = current_setting('app.current_user_id')::uuid`
- AC3: Private tables use `user_id = current_setting('app.current_user_id')::uuid`
- AC4: `get_db_session` always RESET in finally block (Decision 23)
- AC5: `system_config` seeded with embedding model on first run

### F-AUTH-01: JWT Authentication System

**US-1.4:** As a user, I want to log in with username and password.
- AC1: `POST /api/v1/auth/login` returns `{access_token, refresh_token, user}`
- AC2: Access token expires in 24h (configurable `auth.jwt_expiry_minutes`)
- AC3: Refresh token expires in 30d (configurable `auth.jwt_refresh_expiry_days`)
- AC4: Invalid credentials return 401
- AC5: `must_change_password: true` in response triggers forced password change

**US-1.5:** As the Electron client, I want to automatically refresh expired tokens.
- AC1: 401 response triggers `POST /api/v1/auth/refresh` with refresh token
- AC2: Valid refresh token returns new token pair
- AC3: Expired refresh token redirects to login
- AC4: Tokens stored in Electron safeStorage (macOS Keychain, Windows DPAPI)

**US-1.6:** As a user, I want "Remember me" to persist sessions across app restarts.
- AC1: Checked → refresh token persists in safeStorage
- AC2: Unchecked → refresh token cleared on app close

### F-AUTH-02: User Registration & Admin Bootstrap

**US-1.7:** As the first user, I want to create an admin account on first run.
- AC1: `GET /health` returns `{"setup_required": true}` when no users exist
- AC2: Login page shows "Create Admin Account" form when setup_required
- AC3: `POST /api/v1/auth/register` creates admin (role: admin) when no users exist
- AC4: After first user, `GET /health` returns `{"setup_required": false}`
- AC5: Subsequent register attempts return 403 when `allow_registration: false`

**US-1.8:** As an admin, I want to create user accounts and manage passwords.
- AC1: `POST /api/v1/admin/users` creates user with auto-generated temporary password
- AC2: Temp password shown once in dialog, never stored in plaintext
- AC3: `must_change_password` set to true on new user
- AC4: `POST /api/v1/admin/users/{id}/reset-password` generates temporary password
- AC5: `DELETE /api/v1/admin/users/{id}` requires typed username confirmation; deletes DB records, NOT vault files

### F-IDX-01: File Watcher + IndexQueue

**US-1.9:** As a user, when I save a markdown file, I want it indexed within seconds.
- AC1: watchdog detects create/modify/delete/rename on `.md` files
- AC2: Events debounced at 300ms (configurable `vault.watch_debounce_ms`)
- AC3: VaultRegistry resolves path to `(user_id, namespace)` or skips if outside known vaults
- AC4: IndexQueue enqueues file for async processing
- AC5: Indexer parses frontmatter + wikilinks, then (in Phase 2) enriches, chunks, embeds

**US-1.10:** As the system, when the backend creates a file, it must index directly.
- AC1: App-initiated writes bypass watcher, index directly
- AC2: Watcher detects same change but skips matching content_hash

**US-1.11:** As the system, the markdown parser must extract frontmatter and wikilinks.
- AC1: markdown-it-py + python-frontmatter extracts YAML frontmatter
- AC2: Regex or parser extracts `[[wikilinks]]` including aliases `[[target|display]]`
- AC3: NoteTypeClassifier infers type from frontmatter, folder path, and tags

### F-IDX-02: Bulk Initial Indexing

**US-1.12:** As a new user, I want all existing notes indexed with progress feedback.
- AC1: Backend detects unindexed vault, begins bulk processing
- AC2: Progress reported via API (current/total files, ETA)
- AC3: User can chat before indexing completes (partial results available)
- AC4: Target: 1000 notes in under 5 minutes

---

## 8. Phase 2 — RAG + Chat (Weeks 3–4)

**Backend:** ContextEnricher, Chunker, Embedder (LiteLLM aembedding with batching), HybridRAGEngine (vector + BM25 + wikilink CTE, single query), bulk initial indexing with progress, LiteLLM gateway + key resolver with key_type tracking, `POST /api/v1/chat/completions` with SSE streaming, chat history CRUD, enrichment_hash + cascade re-embedding, nh3 sanitizer, user settings CRUD, `GET /api/v1/models`.

**Frontend:** Chat panel with Lexical input + @mentions, SSE client for streaming, message list with citation badges, chat history popover, model picker, mode picker with pill system, DOMPurify clipboard sanitizer.

### F-RAG-01: Hybrid RAG Search

**US-2.1:** As a user, I want search to combine semantic meaning, keywords, AND link relationships.
- AC1: Three signals in single PostgreSQL query: vector cosine (weight 0.5), BM25 keyword (weight 0.3), wikilink graph proximity (weight 0.2)
- AC2: Combined via Reciprocal Rank Fusion (RRF)
- AC3: Returns top K results (default: 10, configurable)
- AC4: RLS includes shared namespace automatically
- AC5: Wikilink graph uses recursive CTE, max 3 hops from context note
- AC6: RAG search latency < 300ms

**US-2.2:** As a user, I want different search scopes for different contexts.
- AC1: `knowledge` context → permanent notes only
- AC2: `citation` context → literature notes only
- AC3: `all` context → all indexed types
- AC4: Project notes → only via frontmatterQuery
- AC5: Conversation notes → only via `all` or memoryRecall

### F-RAG-02: Contextual Enrichment Pipeline

**US-2.3:** As a user with short notes, I want enrichment to improve search quality.
- AC1: Prepend: title, folder, tags, backlink titles, outlink titles before content
- AC2: Note type determines enrichment level (see Decision 2)
- AC3: Tasks, query blocks, calendar frontmatter stripped before embedding
- AC4: NoteTypeClassifier infers from folder + tags when no frontmatter

**US-2.4:** As the system, when wikilinks change, linked notes must be re-enriched.
- AC1: `enrichment_hash` = `hash(title + folder + tags + sorted(backlinks) + sorted(outlinks))`
- AC2: Content unchanged + enrichment changed → re-enrich and re-embed existing chunks
- AC3: Cascade limited to 1 hop
- AC4: Chunk replacement atomic via SAVEPOINT:

```python
async def reindex_document(doc_id: UUID, new_content: str, session: AsyncSession):
    async with session.begin_nested():  # SAVEPOINT
        await session.execute(delete(Chunk).where(Chunk.document_id == doc_id))
        chunks = chunker.split(new_content)
        enriched = [enricher.enrich(chunk, doc_metadata) for chunk in chunks]
        embeddings = await embedder.batch_embed(enriched)
        for i, (chunk, enriched_text, embedding) in enumerate(
            zip(chunks, enriched, embeddings)
        ):
            session.add(Chunk(
                document_id=doc_id, user_id=doc.user_id, namespace=doc.namespace,
                content=chunk, enriched_content=enriched_text, embedding=embedding,
                embedding_model=current_embedding_model, chunk_index=i,
            ))
        doc.content_hash = new_hash
        doc.enrichment_hash = new_enrichment_hash
```

### F-CHAT-01: Multi-turn Chat with SSE Streaming

**US-2.5:** As a user, I want real-time streaming chat responses with citations.
- AC1: `POST /api/v1/chat/completions` opens SSE stream
- AC2: Tokens stream as `{"type":"token","data":{"content":"..."}}`
- AC3: Citations sent as `{"type":"citations","data":{"sources":[...]}}` before tokens
- AC4: Stream ends with `{"type":"done","data":{"usage":{...}}}`
- AC5: Chat response start < 500ms

**US-2.6:** As a user, I want to @mention files for precise context.
- AC1: Lexical editor supports @mention autocomplete
- AC2: Paths sent as `file_references` in ChatCompletionRequest
- AC3: Backend fetches those specific documents as additional context

**Request body schema:**
```python
class ChatCompletionRequest(BaseModel):
    conversation_id: UUID
    message: str
    model_id: str | None = None
    mode_id: str | None = None
    current_note_path: str | None = None
    file_references: list[str] = []
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    frequency_penalty: float | None = None
    system_prompt_override: str | None = None
    web_search_enabled: bool = False
    relevant_note_enabled: bool = True
    agent_enabled: bool = False
    access_token: str | None = None  # SSE fallback
```

**Backend processing flow:**
1. Validate conversation_id belongs to current user
2. Append user message to messages table (user_id denormalized)
3. Resolve mode_id → system prompt; apply system_prompt_override if non-empty
4. If relevant_note_enabled: ragSearch scoped by mode's rag_scope
5. If Write mode + current_note_path: RAG restricted to that document. No path → RAG disabled
6. If file_references non-empty: fetch those documents as additional context
7. Resolve model → LiteLLM identifier, resolve API key (user → shared → error)
8. Call LiteLLM acompletion() with streaming
9. Stream tokens via SSE, record assistant message to DB on completion
10. If agent_enabled: run AgentRunner with tool results streamed as SSE events

### F-CHAT-02: Chat History CRUD

**US-2.7:** As a user, I want to manage my conversation history.
- AC1: `GET /api/v1/conversations` — paginated, searchable, date filter
- AC2: `PATCH /api/v1/conversations/{id}` — update title, model, mode
- AC3: Delete behavior: saved to vault → silent DB delete; not saved → warning modal
- AC4: `POST /api/v1/conversations/{id}/regenerate` — delete last assistant message, re-run

### F-LLM-01: LiteLLM Provider Routing + Key Resolution

**US-2.8:** As a user, I want to use my preferred LLM provider.
- AC1: Providers: OpenAI, Anthropic, Gemini, DeepSeek, OpenRouter, Ollama, LM Studio, vLLM, OpenAI-compatible
- AC2: `GET /api/v1/models` returns models from server config
- AC3: Key resolution: user key → shared key → error with message

**US-2.9:** As the system, I must track LLM costs with key attribution.
- AC1: `key_type` column: 'personal' or 'shared'
- AC2: LiteLLM callbacks log to PostgreSQL llm_usage table:

```python
async def log_usage(kwargs, response, start_time, end_time):
    await db.execute("""
        INSERT INTO llm_usage (user_id, model, provider, prompt_tokens,
            completion_tokens, cost_usd, latency_ms, status, purpose,
            key_type, created_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,now())
    """, user_id, kwargs["model"], extract_provider(kwargs["model"]),
        response.usage.prompt_tokens, response.usage.completion_tokens,
        litellm.completion_cost(response),
        int((end_time - start_time).total_seconds() * 1000),
        "success", kwargs.get("purpose", "chat"),
        "personal" if used_personal_key else "shared")

litellm.success_callback = [log_usage]
litellm.failure_callback = [log_failure]
```

### F-CHAT-03: Mode System (Should Have)

**US-2.10:** As a user, I want modes to automatically configure AI behavior.
- AC1: Single-select; displayed as removable pill; cleared after send
- AC2: Research mode presets web search ON
- AC3: `GET/PUT /api/v1/settings/modes` for custom definitions
- AC4: Up to 5 pinned in picker; overflow via "More modes"
- AC5: Built-in modes show ✎ when customized; resettable

### F-CHAT-04: Model Selector (Should Have)

**US-2.11:** As a user, I want to choose and switch AI models.
- AC1: Grouped by provider; sticky per conversation
- AC2: New conversation → project default model
- AC3: Each message records model_id snapshot
- AC4: 🔑 indicator when personal key active

### F-SETTINGS-01: User Settings CRUD

**US-2.12:** As a user, I want to customize my preferences.
- AC1: `GET /api/v1/settings` returns effective (user override or server default)
- AC2: `PUT /api/v1/settings` updates overrides
- AC3: Server-only settings not overridable: `server.*`, `vault.*`, `rag.embedding_model`, `llm.local_endpoints`, `llm.dream_model`, `auth.*`, `memory.dream.*`, `chat_history.max_conversations_per_user`
- AC4: All other settings user-overridable via `user_settings` JSONB

---

## 9. Phase 3 — Editor + Zettelkasten (Weeks 5–6)

**Backend:** NoteSplitter, ZettelNoteBuilder, document import (PDF/DOCX/HTML), web clipper (Jina Reader + nh3), vault write/move/split endpoints, LinkRefactorer, OperationLog.

**Frontend:** Tiptap split-pane editor, react-resizable-panels, NoteSplitterModal, ZettelNotePreviewModal, Chat Settings popover + More Options drawer.

### F-EDITOR-01: Tiptap Split-Pane Editor (Should Have)

**US-3.1:** As a user, I want to view and edit notes alongside chat.
- AC1: Editor opens from citations, command palette, agent actions
- AC2: No file open → editor collapses, chat takes full width
- AC3: Tiptap v2 + @tiptap/markdown for round-trip conversion
- AC4: react-resizable-panels for adjustable split

**Risk:** Tiptap markdown round-trip may lose frontmatter or wikilinks. Test on Day 1. Store frontmatter separately if needed.

### F-ZETT-01: Note Splitting

**US-3.2:** As a user, I want to split long notes into atomic Zettel notes.
- AC1: NoteSplitter splits at H1 > H2 > H3 boundaries
- AC2: Child notes get: timestamp ID, `type: permanent`, `source: "[[Original Title]]"`
- AC3: Original handling: Keep as literature (default) / Archive / Delete (double confirmation)
- AC4: Literature note updated with links to all children
- AC5: Auto-offer when note exceeds min_word_count (default: 1000)

**US-3.3:** As a user, I want to preview proposed notes before accepting.
- AC1: NoteSplitterModal shows proposed child notes with editable titles
- AC2: Backend writes + indexes all notes immediately on accept

### F-ZETT-02: Document Import (Should Have)

**US-3.4:** As a user, I want to import external documents.
- AC1: `POST /api/v1/documents/upload` accepts PDF (PyMuPDF), DOCX (python-docx), HTML (nh3 + readability-lxml)
- AC2: Extracted text saved as literature note with `type: literature`
- AC3: Offers split for large notes
- AC4: HTML sanitized via nh3 before readability-lxml (defense-in-depth)

### F-ZETT-03: Chat → Zettel Capture (Should Have)

**US-3.5:** As a user, I want to save chat insights as atomic notes with "@zettel save this".
- AC1: AI distills chat context into atomic note
- AC2: ZettelNotePreviewModal for editing before save
- AC3: Backend writes + indexes immediately on accept

---

## 10. Phase 4 — Agent + Memory (Weeks 7–8)

**Backend:** AgentRunner (plan-execute-observe, 22 tools), confirmation gate, client-cooperative tool protocol, memory extraction/storage/recall, Memory Dream consolidation, APScheduler, memory import/export.

**Frontend:** Agent tool banner, memory panel, confirmation modals, SSE client_request handler, Research mode wiring, Memory management tab.

### F-AGENT-01: Agent Runner

**US-4.1:** As a user in Research mode, I want the agent to autonomously perform multi-step reasoning.
- AC1: Plan-execute-observe loop; max 10 tool calls per turn (configurable)
- AC2: Streams partial results via SSE (tool_start, tool_result events)
- AC3: All 22 tools available (see Section 17)

### F-AGENT-02: Core Read-Only Tools

**US-4.2:** As the agent, I need read-only tools that execute without user confirmation.
- AC1: `ragSearch(query, context)` — hybrid search, respects context scope
- AC2: `vaultRead(path)` — returns full file content; 404 if not found
- AC3: `detectOrphans()` — notes with zero incoming wikilinks
- AC4: `suggestLinks(notePath)` — related notes above min_confidence
- AC5: `analyzeNote(notePath)` — orphan status, connections, type, word count
- AC6: `memoryRecall(query)` — semantic search over memories

### F-AGENT-03: Core Write Tools

**US-4.3:** As the agent, I need write tools that require user confirmation.
- AC1: `vaultWrite(path, content)` — create/update file + immediate indexing
- AC2: `splitNote(notePath)` — run NoteSplitter with link refactoring
- AC3: `moveAndRefactor(path, newPath)` — move file + update all wikilinks

### F-AGENT-04: Confirmation Gate (Should Have)

**US-4.4:** As a user, I want to approve all write operations.
- AC1: Modal shows tool name, parameters, expected outcome
- AC2: Approve or cancel
- AC3: Configurable per type: `confirm_before_write/split/organize`

### F-AGENT-05: OperationLog with Undo (Should Have)

**US-4.5:** As a user, I want to undo multi-file operations.
- AC1: Steps recorded with typed schema:

```python
class OperationStep(BaseModel):
    action: str               # "move" | "create" | "delete" | "update_links"
    source_path: str
    target_path: str | None
    old_content: str | None   # for update_links
    affected_links: list[str]
    timestamp: datetime

class OperationRecord(BaseModel):
    operation_type: str       # "organize" | "batch_move" | "clean_orphans"
    steps: list[OperationStep]
    description: str
```

- AC2: Undo reverses steps: "move" → move back; "update_links" → restore old_content; "create" → delete
- AC3: `POST /api/v1/vault/organize/undo`

### F-MEM-01: Memory Extraction and Storage

**US-4.6:** As a user, I want the AI to remember facts from conversations.
- AC1: MemoryExtractor uses LLM to identify facts/preferences
- AC2: Stored in memories table with embedding
- AC3: Max 500 per user, 200 active (configurable)

**US-4.7:** As a user, I want to manage memories (view, edit, archive, delete, import, export).
- AC1: Searchable/sortable list in Settings Tab 4i
- AC2: Inline edit re-embeds on save
- AC3: Archive = soft delete; permanent delete requires confirmation
- AC4: Import from JSON or markdown; export as JSON
- AC5: Import duplicate detection: >95% cosine similarity → flag

### F-MEM-02: Memory Recall

**US-4.8:** As the system, I need to surface relevant memories during conversations.
- AC1: Semantic search over active memories
- AC2: Updates `last_recalled_at` and `recall_count`

### F-MEM-03: Memory Dream Consolidation (Should Have)

See [Section 18](#18-memory-dream-consolidation-system) for full specification.

**US-4.9:** As a user, I want memories automatically cleaned up.
- AC1: Triggers when 24+ hours AND 5+ sessions since last cycle
- AC2: 4 phases: Orientation → Gather Signal → Consolidation → Prune & Index
- AC3: All actions logged to dream_audit_log (archived, never hard-deleted)
- AC4: Advisory lock prevents concurrent runs
- AC5: "Run Dream now" button + API endpoint

---

## 11. Phase 5 — Web Search + Projects (Weeks 9–10)

### F-SEARCH-01: Web Search (Should Have)

**US-5.1:** As a user, I want to search the web from within chat.
- AC1: Free: DuckDuckGo + Jina Reader + Wikipedia (no keys required)
- AC2: Paid (optional): Tavily, Brave, SerpAPI
- AC3: Triggered by `@web`, toggle, or Research mode
- AC4: `POST /api/v1/web/search` and `POST /api/v1/web/fetch`

### F-PROJ-01: Project Scoping (Should Have)

**US-5.2:** As a user, I want projects to scope RAG to specific folders/tags.
- AC1: Projects define: include_folders, exclude_folders, tags, system_prompt, default_model
- AC2: Focus mode restricts RAG to active project
- AC3: Project switcher in header
- AC4: CRUD via /api/v1/projects

---

## 12. Phase 6 — Intelligence + Admin (Weeks 11–12)

### F-VAULT-01: Vault Health Endpoints (Should Have)

**US-6.1:** As a user, I want vault health metrics.
- AC1: `GET /api/v1/vault/health` — composite score
- AC2: `GET /api/v1/vault/orphans` — orphan notes list
- AC3: `GET /api/v1/vault/hubs` — most-connected notes
- AC4: `GET /api/v1/vault/graph` — nodes + edges for Cytoscape
- AC5: `GET /api/v1/vault/index/events` — recent index events

### F-ADMIN-01: Admin Dashboard

**US-6.2:** As an admin, I want a comprehensive management dashboard.
- AC1: 7 tabs: Overview, LLM Usage, Storage, API Keys, Users, Memory Dream, System
- AC2: Admin-only via `require_admin` dependency
- AC3: Client hides admin UI for non-admins (cosmetic; API is the real gate)

### F-ADMIN-02: LLM Usage Tracking (Should Have)

**US-6.3:** As an admin, I want cost breakdowns by user, model, provider.
**US-6.4:** As a user, I want to see my own costs with shared/personal breakdown.
- AC1: Admin: `/admin/costs/by-provider`, `/admin/costs/by-user`, `/admin/usage/history`
- AC2: User: `/usage/summary` (30d, 7d, today), `/usage/by-model`

### F-ADMIN-03: Embedding Migration (Should Have)

**US-6.5:** As an admin, I want to change embedding models with migration support.
- AC1: `/admin/embeddings/estimate` — cost/time estimate
- AC2: `/admin/embeddings/migrate` — start migration
- AC3: `/admin/embeddings/status` — progress
- AC4: `/admin/embeddings/cancel` — stop
- AC5: Search works (degraded) during migration
- AC6: Crash recovery: resume on restart

---

## 13. Phase 7 — Platform + Polish (Weeks 13–14)

### F-PLATFORM-01: System Tray Agent (Could Have)

**US-7.1:** As a user, I want Smart Copilot in my system tray.
- AC1: Tray icon with: Quick Chat, Search, Reindex, Settings, Quit
- AC2: App continues when all windows closed
- AC3: Dynamic icon/tooltip for indexing status

### F-CHAT-05: Quick Chat Window (Could Have)

**US-7.2:** As a user, I want a compact floating chat for quick questions.
- AC1: 400×500 floating window; shares auth with main window
- AC2: Launched from tray or global hotkey

### F-PLATFORM-02: Global Hotkey (Could Have)

- AC1: Cmd+Shift+Space (default, configurable)
- AC2: Electron globalShortcut API

### Additional Phase 7 deliverables:
- Auto-launch on login (electron auto-launch)
- electron-updater with GitHub Releases
- Command palette (cmdk)
- Diff modal (diff + react-diff-viewer-continued)
- Vault export (`POST /api/v1/conversations/{id}/export`)
- Image understanding (vision models)
- Settings UI polish (all 9 tabs)
- User API key management with provider status

---

## 14. Phase 8 — Beta + Launch (Weeks 15–16)

- 10+ beta users across macOS and Windows
- Performance targets met (see Section 27)
- Docker image published to GitHub Container Registry
- Backup script + restore procedure tested end-to-end
- README with screenshots, quick start guide
- Docker Compose example for advanced deployments (external PostgreSQL, Caddy reverse proxy)

---

## 15. API Contract Reference

> **FOR AI AGENTS:** Implement these endpoints exactly as specified. The OpenAPI spec auto-generated from FastAPI is the runtime source of truth, but these definitions are the design spec. Total: ~65 endpoints across 13 route groups.

### Auth (4 endpoints — Phase 1)

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/auth/register` | None | First user → admin. Returns 403 when registration disabled and users exist |
| POST | `/api/v1/auth/login` | None | Returns access + refresh tokens |
| POST | `/api/v1/auth/refresh` | None | Refresh token → new pair |
| POST | `/api/v1/auth/change-password` | JWT | Requires current password |

### Chat (7 endpoints — Phase 2, regenerate Phase 6)

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/chat/completions` | JWT | SSE streaming with RAG + citations |
| GET | `/api/v1/conversations` | JWT | Paginated, search, date filter |
| GET | `/api/v1/conversations/{id}` | JWT | With messages |
| POST | `/api/v1/conversations` | JWT | Create conversation |
| PATCH | `/api/v1/conversations/{id}` | JWT | Update title, model, mode |
| DELETE | `/api/v1/conversations/{id}` | JWT | Delete with confirmation logic |
| POST | `/api/v1/conversations/{id}/regenerate` | JWT | Delete last assistant message, re-run |
| POST | `/api/v1/conversations/{id}/export` | JWT | Export to vault as markdown |

### Search (3 endpoints — Phase 2)

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/search` | JWT | Hybrid: vector + BM25 + wikilink |
| POST | `/api/v1/search/semantic` | JWT | Vector-only |
| POST | `/api/v1/search/keyword` | JWT | BM25-only |

### Documents (5 endpoints — Phase 3)

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/documents` | JWT | Paginated, filter by type/folder/tag |
| GET | `/api/v1/documents/{id}` | JWT | Metadata + content |
| PUT | `/api/v1/documents/{id}` | JWT | Write to filesystem + reindex |
| POST | `/api/v1/documents/upload` | JWT | Import PDF, DOCX, HTML |
| GET | `/api/v1/documents/upload/{task_id}/status` | JWT | Poll import progress |

### Vault (11 endpoints — Phase 3 write ops, Phase 6 intelligence)

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/vault/write` | JWT | Create or update file |
| POST | `/api/v1/vault/move` | JWT | Move + update wikilinks |
| POST | `/api/v1/vault/split` | JWT | Split into atomic Zettel |
| GET | `/api/v1/vault/orphans` | JWT | Orphan notes list |
| GET | `/api/v1/vault/hubs` | JWT | Most-connected notes |
| GET | `/api/v1/vault/health` | JWT | Composite health score |
| GET | `/api/v1/vault/graph` | JWT | Nodes + edges for Cytoscape |
| GET | `/api/v1/vault/index/events` | JWT | User's recent index events |
| GET | `/api/v1/vault/links/suggestions/{doc_id}` | JWT | Link suggestions |
| POST | `/api/v1/vault/organize` | JWT | Dry run suggestions |
| POST | `/api/v1/vault/organize/apply` | JWT | Apply organization |
| POST | `/api/v1/vault/organize/undo` | JWT | Undo last organization |

### Agent (1 endpoint — Phase 4)

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/agent/client-response` | JWT | Client responds to client_request SSE event |

### Web Search (2 endpoints — Phase 5)

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/web/search` | JWT | Via configured provider |
| POST | `/api/v1/web/fetch` | JWT | Fetch + clean URL via Jina Reader + nh3 |

### Memory (12 endpoints — Phase 4)

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/memories` | JWT | Active by default; `?archived=true` for archived |
| POST | `/api/v1/memories` | JWT | Create manually |
| PUT | `/api/v1/memories/{id}` | JWT | Update content (re-embeds) |
| DELETE | `/api/v1/memories/{id}` | JWT | Archive (soft delete) |
| DELETE | `/api/v1/memories/{id}/permanent` | JWT | Hard-delete (requires `?confirm=true`) |
| POST | `/api/v1/memories/{id}/restore` | JWT | Restore archived |
| POST | `/api/v1/memories/search` | JWT | Semantic search |
| POST | `/api/v1/memories/import` | JWT | Bulk import JSON/markdown |
| GET | `/api/v1/memories/export` | JWT | Export all active as JSON |
| GET | `/api/v1/memories/dream/latest` | JWT | Latest Dream report |
| GET | `/api/v1/memories/dream/audit` | JWT | Dream audit log |
| POST | `/api/v1/memories/dream/trigger` | JWT | Manual trigger for self |

### Projects (4 endpoints — Phase 5)

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/projects` | JWT | List |
| POST | `/api/v1/projects` | JWT | Create |
| PATCH | `/api/v1/projects/{id}` | JWT | Update |
| DELETE | `/api/v1/projects/{id}` | JWT | Delete |

### Models (2 endpoints — Phase 2)

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/models` | JWT | Available LLM models |
| GET | `/api/v1/models/embedding` | JWT | Available embedding models |

### User Usage & Status (6 endpoints — Phase 6)

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/usage/summary` | JWT | 30d, 7d, today cost/tokens |
| GET | `/api/v1/usage/history` | JWT | Daily usage for charts |
| GET | `/api/v1/usage/recent` | JWT | Last 20 LLM calls |
| GET | `/api/v1/usage/by-model` | JWT | Cost breakdown by model |
| GET | `/api/v1/status` | JWT | Public-safe system status |
| GET | `/api/v1/status/providers` | JWT | Provider availability for user |

### User Settings (7 endpoints — Phase 2)

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/settings` | JWT | User's settings |
| PUT | `/api/v1/settings` | JWT | Update settings |
| GET | `/api/v1/settings/modes` | JWT | Mode definitions |
| PUT | `/api/v1/settings/modes` | JWT | Update modes |
| GET | `/api/v1/settings/api-keys` | JWT | User's keys (hints only) |
| POST | `/api/v1/settings/api-keys` | JWT | Add/update key |
| DELETE | `/api/v1/settings/api-keys/{provider}` | JWT | Delete key |
| POST | `/api/v1/settings/api-keys/{provider}/test` | JWT | Test key validity |

### Admin (16 endpoints — Phase 1 users, Phase 2 keys, Phase 6 rest)

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/admin/overview` | Admin | Dashboard overview |
| GET | `/api/v1/admin/costs/by-provider` | Admin | Cost by provider/model |
| GET | `/api/v1/admin/costs/by-user` | Admin | Cost by user |
| GET | `/api/v1/admin/usage/history` | Admin | Usage over time |
| GET | `/api/v1/admin/health` | Admin | System health; reads backup-status.json |
| GET | `/api/v1/admin/users` | Admin | List with stats |
| POST | `/api/v1/admin/users` | Admin | Create user |
| DELETE | `/api/v1/admin/users/{id}` | Admin | Delete user + DB data |
| POST | `/api/v1/admin/users/{id}/reset-password` | Admin | Returns temp password |
| POST | `/api/v1/admin/reindex` | Admin | Force full reindex |
| GET | `/api/v1/admin/index/status` | Admin | Index queue status |
| GET | `/api/v1/admin/api-keys` | Admin | Shared keys (hints only) |
| POST | `/api/v1/admin/api-keys` | Admin | Add/update shared key |
| DELETE | `/api/v1/admin/api-keys/{id}` | Admin | Delete shared key |
| POST | `/api/v1/admin/api-keys/{id}/test` | Admin | Test shared key |
| GET | `/api/v1/admin/embeddings/estimate` | Admin | Migration estimate |
| POST | `/api/v1/admin/embeddings/migrate` | Admin | Start migration |
| GET | `/api/v1/admin/embeddings/status` | Admin | Migration progress |
| POST | `/api/v1/admin/embeddings/cancel` | Admin | Cancel migration |
| GET | `/api/v1/admin/dream/status` | Admin | Dream status all users |
| POST | `/api/v1/admin/dream/trigger/{user_id}` | Admin | Trigger Dream for user |

### Health (1 endpoint — Phase 1)

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/health` | None | Returns setup_required flag when no users |

---

## 16. SSE Streaming Protocol

```
data: {"type":"status","data":{"description":"Searching knowledge base...","done":false}}

data: {"type":"citations","data":{"sources":[{"doc_id":"...","path":"...","title":"...","score":0.92,"excerpt":"..."}]}}

data: {"type":"token","data":{"content":"Based on"}}
data: {"type":"token","data":{"content":" your notes"}}

data: {"type":"tool_start","data":{"tool":"ragSearch","input":{"query":"neural networks"}}}
data: {"type":"tool_result","data":{"tool":"ragSearch","elapsed_ms":340,"result_count":5}}

data: {"type":"client_request","data":{"request_id":"uuid","action":"read_clipboard","max_payload_bytes":5242880}}

data: {"type":"done","data":{"usage":{"prompt_tokens":1200,"completion_tokens":450,"cost_usd":0.0034}}}
```

Event types: `status`, `citations`, `token`, `tool_start`, `tool_result`, `client_request`, `done`

---

## 17. Agent System — 22 Tools

### Auto-approve (read-only — no confirmation)

| # | Tool | Description |
|---|---|---|
| 1 | `ragSearch(query, context)` | Hybrid RAG search |
| 2 | `vaultRead(path)` | Read note content |
| 3 | `detectOrphans()` | Find orphan notes |
| 4 | `suggestLinks(notePath)` | Suggest wikilinks |
| 5 | `analyzeNote(notePath)` | Note analysis |
| 6 | `memoryRecall(query)` | Search memories |
| 7 | `frontmatterQuery(field, op, value)` | Query by frontmatter (internal only, no REST endpoint) |
| 8 | `reconcileIndex()` | Fix filesystem/DB drift |
| 9 | `scheduleMaintenance(task, schedule)` | Register tasks within admin ceiling; persisted via APScheduler SQLAlchemyJobStore |
| 10 | `notifyUser(title, body)` | Send notification via SSE |
| 11 | `openInEditor(path)` | Fire-and-forget SSE event |

### Require user confirmation (write operations)

| # | Tool | Description |
|---|---|---|
| 12 | `vaultWrite(path, content)` | Create/update file + immediate indexing |
| 13 | `webSearch(query)` | Search web when toggle on |
| 14 | `splitNote(notePath)` | NoteSplitter with link refactoring |
| 15 | `generateMOC(topic)` | Create Map of Content |
| 16 | `organizeVault()` | Suggest + apply folder reorganization |
| 17 | `captureFromURL(url)` | Jina Reader → nh3 → markdown → literature note |
| 18 | `captureFromClipboard()` | Client-cooperative protocol (see below) |
| 19 | `moveAndRefactor(path, newPath)` | Move + update all wikilinks |
| 20 | `batchOrganize(plan)` | Multi-file move with OperationLog |
| 21 | `undoLastOrganize()` | Reverse last batch operation |
| 22 | `cleanOrphans(strategy)` | Archive / delete / suggest-merge |

### captureFromClipboard Protocol

```
1. Agent calls captureFromClipboard()
2. Backend emits SSE: {"type":"client_request","data":{"request_id":"uuid","action":"read_clipboard"}}
3. Electron reads clipboard, normalizes:
   - Plain text: trim, normalize line endings, truncate 500KB
   - HTML: DOMPurify sanitize, truncate 1MB
   - URL: validate HTTP(S), strip tracking params
   - Image: resize if >4096px, compress ≤5MB PNG, base64, strip EXIF
   - File path: text only (client does NOT read file)
4. Client POSTs to /api/v1/agent/client-response
5. Backend re-sanitizes via nh3, processes by type
6. Agent requests confirmation before creating note
7. Timeout: 10 seconds → error + "Try pasting into chat instead"
```

### Background Agent (Proactive Mode, Opt-in)

Runs via APScheduler:
1. Check vault health → notify if below threshold
2. Orphan count exceeds threshold → suggest cleanup
3. New notes without wikilinks → suggest connections
4. Scheduled maintenance tasks (reconcile, etc.)
5. Memory Dream consolidation (nightly)
6. System health snapshot every 15 minutes → `system_health` table

---

## 18. Memory Dream Consolidation System

### Problem
After 10–15 sessions, accumulated memories become noise: relative dates meaningless, contradictions co-exist, references to deleted files persist.

### 4-Phase Nightly Cycle

**Phase 1 — Orientation:** Count active memories, age distribution, flag relative time references, detect broken note references.

**Phase 2 — Gather Signal:** LLM-targeted search for corrections, key decisions, recurring patterns, contradicted facts. Purpose: `dream` in llm_usage.

**Phase 3 — Consolidation** (each logged to dream_audit_log):
- Relative → absolute timestamps
- Contradiction deletion (keep newer, archive older)
- Stale pruning (deleted note refs, 90+ days with zero recalls)
- Duplicate merge
- Preference resolution (last explicit statement wins)

**Phase 4 — Prune & Index:** Archive excess over 200 active. Re-embed modified memories. Generate consolidation summary.

### Trigger Conditions
- Automatic: 24+ hours AND 5+ sessions since last cycle
- Manual: admin dashboard (per-user), user's Memory panel ("Run Dream now")
- Checked every hour by APScheduler
- One user at a time
- Uses cheapest model (e.g., gpt-4o-mini)
- Skips users with fewer than 20 memories

### Concurrency Guard
```python
# PostgreSQL advisory lock prevents overlapping runs
pg_try_advisory_lock(hashtext('dream'))
```

---

## 19. Zettelkasten Workflows

### Workflow A — Import External Document

1. User uploads via chat or "Import Document"
2. Backend extracts text (HTML: nh3 → readability-lxml) → saves as literature note
3. Offers: "This note is {N} words — split into Zettel notes?"
4. If accepted → NoteSplitter runs (H1 > H2 > H3, atomic permanents with source backlinks)
5. Literature note updated with links to children
6. Client opens literature note in editor

### Workflow B — Chat to Zettel

1. User chats normally
2. "@zettel save this"
3. AI distills to atomic format
4. ZettelNotePreviewModal for editing
5. Accept → write + index immediately

### Workflow C — Convert Existing Long Note

1. Command palette: "Split This Note" OR auto-offer when exceeds min_word_count
2. Same NoteSplitter flow
3. Original becomes literature note
4. Options: Keep (default) / Archive / Delete (confirmation required)

---

## 20. HTML Sanitization Strategy

### Client-side: DOMPurify (Electron renderer)

```typescript
import DOMPurify from 'dompurify';

const SANITIZE_CONFIG: DOMPurify.Config = {
  ALLOWED_TAGS: ['h1','h2','h3','h4','h5','h6','p','blockquote','pre',
    'ul','ol','li','a','em','strong','code','table','thead','tbody','tr','th','td','img','br'],
  ALLOWED_ATTR: ['href','src','alt','title','colspan','rowspan'],
  ALLOW_DATA_ATTR: false, ALLOW_ARIA_ATTR: false, ALLOW_UNKNOWN_PROTOCOLS: false,
};

// Hook: force rel=noopener on links, strip non-HTTP hrefs/srcs
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

### Server-side: nh3 (Python, defense-in-depth)

```python
import nh3

html_cleaner = nh3.Cleaner(
    tags={"h1","h2","h3","h4","h5","h6","p","blockquote","pre",
          "ul","ol","li","a","em","strong","code","table","thead","tbody","tr","td","th","img"},
    attributes={"a": {"href","title"}, "img": {"src","alt","title","width","height"},
                "td": {"colspan","rowspan"}, "th": {"colspan","rowspan","scope"}},
    clean_content_tags={"script","style","iframe","object","embed","noscript"},
    url_schemes={"http","https","mailto"},
    link_rel="noopener noreferrer", strip_comments=True,
)
```

### Flow by Source
```
Clipboard paste → DOMPurify (client) → API → nh3 (server) → readability-lxml → markdown
URL capture     →                       API → nh3 (server) → readability-lxml → markdown
HTML upload     →                       API → nh3 (server) → readability-lxml → markdown
```

---

## 21. Indexing Strategy

### Cascading Re-enrichment

`documents.content_hash` tracks raw content. `documents.enrichment_hash` tracks enrichment inputs: `hash(title + folder + tags + sorted(backlink_titles) + sorted(outlink_titles))`.

**Flow on file change:**
1. Compute content_hash
2. Both unchanged → skip
3. content_hash changed → full re-process (parse, enrich, chunk, embed)
4. content_hash same, enrichment_hash changed → re-enrich + re-embed existing chunks

**Cascade:** After indexing any document, check if wikilinks changed. If yes, mark linked documents for enrichment_hash recalculation. **Depth limited to 1 hop.**

### Chunk Replacement

Atomic delete-and-recreate within SAVEPOINT (see code in Phase 2 section). If embedding fails midway, DELETE rolls back and old chunks restored. Note is never unsearchable.

For enrichment-only updates: update existing rows' `enriched_content` and `embedding` in place.

---

## 22. Server Configuration Reference

File: `/config/settings.yaml` — only non-secret config. API keys are in the database.

```yaml
server:
  host: 0.0.0.0
  port: 8000
  log_level: info
  cors_origins: ["http://localhost:*", "app://."]

vault:
  base_path: /vaults
  watch_debounce_ms: 300
  reconciliation_interval_hours: 6

rag:
  hybrid_weights: { vector: 0.5, bm25: 0.3, wikilink: 0.2 }
  context_enrichment: true
  top_k: 10
  wikilink_max_hops: 3
  embedding_model: openai/text-embedding-3-small
  embedding_dimensions: 1536

llm:
  default_chat_model: openai/gpt-4o
  default_temperature: 0.7
  default_max_tokens: 4096
  dream_model: openai/gpt-4o-mini
  models:
    - { id: openai/gpt-4o, display_name: GPT-4o, capabilities: [chat, vision] }
    - { id: openai/gpt-4o-mini, display_name: GPT-4o Mini, capabilities: [chat] }
    - { id: anthropic/claude-sonnet-4-20250514, display_name: Claude Sonnet 4, capabilities: [chat] }
    - { id: anthropic/claude-haiku-4-5-20251001, display_name: Claude Haiku 4.5, capabilities: [chat] }
    - { id: gemini/gemini-2.5-pro, display_name: Gemini 2.5 Pro, capabilities: [chat, vision] }
    - { id: ollama/qwen3:8b, display_name: Qwen3 8B (local), capabilities: [chat] }
  embedding_models:
    - { id: openai/text-embedding-3-small, display_name: OpenAI Embedding Small, dimensions: 1536 }
    - { id: openai/text-embedding-3-large, display_name: OpenAI Embedding Large, dimensions: 3072 }
    - { id: ollama/nomic-embed-text, display_name: Nomic Embed (local), dimensions: 768 }
  local_endpoints: []

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
    original_note_handling: keep
    archive_folder: /archive/
  link_suggestions: { min_confidence: 0.7, max_suggestions: 10 }
  id_format: { use_timestamp: true, separator: "" }

agent:
  max_tool_calls_per_turn: 10
  confirm_before_write: true
  confirm_before_split: true
  confirm_before_organize: true
  proactive_mode: false
  maintenance_schedule: weekly

memory:
  auto_extract: true
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
  max_conversations_per_user: 0

auth:
  allow_registration: false
  first_user_is_admin: true
  jwt_expiry_minutes: 1440
  jwt_refresh_expiry_days: 30
```

**Server-only (not user-overridable):** `server.*`, `vault.*`, `rag.embedding_model`, `rag.embedding_dimensions`, `llm.local_endpoints`, `llm.dream_model`, `auth.*`, `memory.dream.*`, `chat_history.max_conversations_per_user`

**User-overridable:** Everything else (RAG weights, top_k, temperature, zettelkasten, agent, mode definitions, etc.)

---

## 23. Docker Deployment

### Dockerfile

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
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
```

### supervisord.conf

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
```

### wait-for-pg.sh

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

### Run Commands

```bash
# Generate encryption key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Standard deployment
docker run -d --name smart-copilot -p 8000:8000 \
  -v smart-copilot-data:/var/lib/postgresql/data \
  -v /path/to/vaults:/vaults \
  -e ENCRYPTION_KEY=your-key \
  smart-copilot:latest

# External PostgreSQL
docker run -d --name smart-copilot -p 8000:8000 \
  -v /path/to/vaults:/vaults \
  -e EXTERNAL_DB=true \
  -e DATABASE_URL=postgresql+asyncpg://copilot:pass@pg-host:5432/copilot \
  -e ENCRYPTION_KEY=your-key \
  smart-copilot:latest
```

---

## 24. Backup Strategy

Three components required:

| Component | Location | Method |
|---|---|---|
| PostgreSQL database | Docker volume | pg_dump daily |
| Vault files | Host mount | rsync / Syncthing |
| Encryption key | `ENCRYPTION_KEY` env var | Password manager (stored separately!) |

### Automated Backup Script

```bash
#!/bin/bash
# smart-copilot-backup.sh — run via cron daily
set -euo pipefail
BACKUP_DIR="/backups/smart-copilot/$(date +%Y-%m-%d)"
RETENTION_DAYS=30
mkdir -p "$BACKUP_DIR"

docker exec smart-copilot pg_dump -U postgres -Fc copilot > "$BACKUP_DIR/database.dump"
rsync -a --delete /path/to/your/vaults/ "$BACKUP_DIR/vaults/"
docker cp smart-copilot:/config/settings.yaml "$BACKUP_DIR/settings.yaml"

pg_restore --list "$BACKUP_DIR/database.dump" > /dev/null 2>&1 \
  && echo "DB verified." || echo "WARNING: backup may be corrupt!"

find /backups/smart-copilot/ -maxdepth 1 -type d -mtime +$RETENTION_DAYS -exec rm -rf {} \;

docker exec smart-copilot sh -c \
  "echo '{\"last_backup\":\"$(date -Iseconds)\",\"backup_dir\":\"$BACKUP_DIR\"}' > /config/backup-status.json"
```

**Cron:** `0 3 * * * /opt/smart-copilot/smart-copilot-backup.sh`

**Critical:** If `ENCRYPTION_KEY` is lost, all stored API keys are unrecoverable. Store separately from data.

---

## 25. File Structure Reference

### Backend

```
server/
├── Dockerfile
├── supervisord.conf
├── requirements.txt
├── pyproject.toml
├── alembic.ini
├── alembic/versions/
├── scripts/wait-for-pg.sh
└── app/
    ├── main.py                      # FastAPI app, startup validation
    ├── config.py                    # Pydantic settings from YAML + env
    ├── dependencies.py              # get_db_session, get_db
    ├── encryption.py                # Fernet encrypt/decrypt
    ├── api/
    │   ├── auth.py                  # register, login, refresh, change-password
    │   ├── chat.py                  # SSE streaming chat with RAG
    │   ├── conversations.py         # CRUD
    │   ├── search.py                # hybrid, semantic, keyword
    │   ├── documents.py             # list, get, upload, import
    │   ├── vault.py                 # write, move, split, organize, undo
    │   ├── agent.py                 # client-response endpoint
    │   ├── web_search.py            # search, fetch URL
    │   ├── memories.py              # CRUD + search + dream
    │   ├── projects.py              # CRUD
    │   ├── models.py                # list LLM + embedding models
    │   ├── usage.py                 # user-scoped usage/cost
    │   ├── status.py                # system status for all users
    │   ├── settings.py              # user settings + modes + keys
    │   ├── admin.py                 # all admin endpoints
    │   └── health.py                # health check
    ├── models/                      # 15 SQLAlchemy models
    │   ├── user.py, api_key.py, document.py, chunk.py, wikilink.py,
    │   ├── conversation.py, message.py, memory.py, dream_audit_log.py,
    │   ├── project.py, operation_log.py, llm_usage.py, index_event.py,
    │   ├── system_health.py, system_config.py, user_settings.py
    ├── schemas/                     # 15 Pydantic schemas
    │   ├── auth.py, chat.py, search.py, document.py, conversation.py,
    │   ├── vault.py, memory.py, project.py, usage.py, status.py,
    │   ├── models.py, health.py, admin.py, settings.py, common.py
    ├── rag/
    │   ├── engine.py                # HybridRAGEngine
    │   ├── context_enricher.py
    │   ├── note_type.py             # NoteTypeClassifier
    │   ├── embedder.py              # LiteLLM aembedding wrapper + batching
    │   ├── chunker.py
    │   └── queries.py               # SQL for hybrid search + RRF
    ├── vault/
    │   ├── registry.py              # VaultRegistry
    │   ├── watcher.py               # watchdog, calls registry.resolve()
    │   ├── parser.py                # markdown parsing
    │   ├── indexer.py               # IndexQueue: enrich → embed → upsert
    │   ├── link_graph.py
    │   ├── link_refactorer.py
    │   ├── operation_log.py
    │   └── reconciler.py
    ├── agent/
    │   ├── runner.py                # Plan-execute-observe loop
    │   ├── tools.py                 # 22 tool implementations
    │   └── scheduler.py             # APScheduler integration
    ├── llm/
    │   ├── gateway.py               # LiteLLM wrapper
    │   ├── key_resolver.py          # user → shared → error + key_type
    │   ├── callbacks.py             # Cost tracking
    │   └── prompts.py               # System prompts
    ├── memory/
    │   ├── manager.py
    │   ├── extractor.py
    │   ├── importer.py              # Bulk import with dedup
    │   ├── exporter.py
    │   └── dream.py                 # 4-phase consolidation
    ├── websearch/
    │   ├── engine.py, duckduckgo.py, jina_reader.py,
    │   ├── wikipedia.py, tavily.py, brave.py, cross_ref.py
    ├── zettelkasten/
    │   ├── splitter.py, builder.py, organizer.py,
    │   ├── moc_generator.py, orphan_detector.py
    ├── documents/
    │   ├── processor.py, pdf.py, docx.py,
    │   └── html.py                  # nh3 → readability-lxml → markdown
    ├── capture/
    │   ├── manager.py, web_clipper.py
    ├── sanitizer/
    │   └── html_sanitizer.py        # nh3 config
    └── auth/
        ├── jwt.py, password.py,
        └── middleware.py             # get_current_user + require_admin
```

### Frontend

```
client/
├── forge.config.ts
├── vite.config.ts
├── package.json
├── tsconfig.json
└── src/
    ├── main/
    │   ├── main.ts, tray.ts, windows.ts,
    │   ├── global-shortcut.ts, auto-launch.ts, ipc.ts
    ├── renderer/
    │   ├── index.html, main.tsx, App.tsx
    │   ├── api/
    │   │   ├── client.ts, generated/, sse.ts
    │   ├── views/
    │   │   ├── ChatView.tsx, SettingsView.tsx, AdminView.tsx,
    │   │   ├── LoginView.tsx, DashboardView.tsx, PasswordChangeView.tsx
    │   ├── components/
    │   │   ├── chat/, editor/, floating/, intelligence/,
    │   │   ├── admin/, dashboard/ (MyUsageTab, VaultHealthTab, SystemStatusTab),
    │   │   ├── memory/ (MemoryList, MemoryImport, MemoryDreamStatus),
    │   │   └── shared/
    │   ├── modals/, contexts/, hooks/
    │   ├── utils/
    │   │   ├── sanitizer.ts         # DOMPurify config
    │   │   └── clipboard.ts         # ClipboardHandler
    │   └── styles/
    ├── quickchat/
    │   ├── index.html, quickchat.tsx, QuickChatView.tsx
    └── shared/
        ├── types.ts, constants.ts
```

---

## 26. UI Pages & Navigation

### Page Map

| # | Page | Access | Phase |
|---|---|---|---|
| 1 | Login / Connection Setup | All | 1 |
| 2 | Main Chat View (split-pane) | All | 2–3 |
| 3 | Floating Surfaces (history, mode, model, settings popovers) | All | 2 |
| 4 | Settings (9 tabs) | All | 2–7 |
| 5 | Admin Dashboard (7 tabs) | Admin | 6 |
| 6a | User Dashboard (3 tabs: Usage, Vault Health, System Status) | All | 6 |
| 7 | Quick Chat Window (tray) | All | 7 |
| 8 | Modals (split, preview, organize, confirm, diff) | All | 3–7 |

### Settings Tabs
```
[ General ] [ Model ] [ RAG ] [ Modes ] [ Features ] [ API Keys ] [ Advanced ] [ Account ] [ Memory ]
```

### Admin Dashboard Tabs
```
[ Overview ] [ LLM Usage ] [ Storage ] [ API Keys ] [ Users ] [ Memory Dream ] [ System ]
```

### Navigation by Role
```
Standard user:
  ⋯ Panel Options → Dashboard (Page 6a)
  ⋯ Panel Options → Settings (Page 4)

Admin user:
  ⋯ Panel Options → Dashboard (Page 6a)
  ⋯ Panel Options → Admin (Page 5)
  ⋯ Panel Options → Settings (Page 4)
```

---

## 27. Non-Functional Requirements & Success Metrics

### Performance Targets

| Metric | Target |
|---|---|
| Chat response start | < 500ms |
| RAG search latency | < 300ms |
| Bulk index 1000 notes | < 5 minutes |
| Watcher → indexed | < 5 seconds |

### Scale Targets

| Metric | Target |
|---|---|
| Concurrent users | 3–10 |
| Notes per user | 500–5,000 |
| Active memories per user | ≤ 200 |
| Max memories per user | 500 |

### Reliability

| Metric | Target |
|---|---|
| Container restart recovery | < 30 seconds |
| Index reconciliation | Every 6 hours |
| Dream concurrency | Max 1 concurrent run |

### Security

| Requirement | Implementation |
|---|---|
| Data isolation | RLS on all 12 user-scoped tables |
| Key encryption | Fernet AES-128 at rest |
| Token storage | Electron safeStorage (OS keychain) |
| HTML sanitization | DOMPurify (client) + nh3 (server) |
| Admin enforcement | API-level `require_admin` dependency |

### Success KPIs (Post-Launch)

| KPI | Target | Measurement |
|---|---|---|
| Daily active users | ≥ 50% of registered | auth login count / total users |
| RAG search quality | ≥ 80% relevance | User thumbs-up on citations |
| Dream effectiveness | Memory count stable at ~200 | memories table count over time |
| Agent task completion | ≥ 90% success rate | tool_result success / total calls |
| Cost per user per month | < $5 shared key usage | llm_usage aggregation |

---

## 28. Quality Gates by Phase

| Phase | Gate | Pass Criteria |
|---|---|---|
| 1 | Container starts | `docker run` → `GET /health` 200 within 30s |
| 1 | Auth works | Register → login → JWT → authenticated request succeeds |
| 1 | Watcher detects | Create .md → watcher event logged |
| 2 | Chat with RAG | Message → hybrid search → citations in response |
| 2 | Model switch | Change model → new model used for next message |
| 3 | PDF → Zettel | Upload PDF → extract → split → atomic notes with backlinks |
| 3 | Editor opens | Click citation → Tiptap opens with note |
| 4 | Multi-tool | Research mode → agent uses ragSearch + webSearch + vaultWrite |
| 4 | Memory persists | Fact in chat → memoryRecall finds it in new conversation |
| 4 | Dream runs | Trigger → consolidation report shows actions |
| 5 | Project scoping | Create project → Focus mode → RAG limited to project |
| 5 | Web search | @web query → results displayed |
| 6 | Admin dashboard | Real usage data, costs, users, health |
| 6 | User dashboard | Personal costs with shared/personal breakdown |
| 6 | Embedding migration | Change model → progress → complete → search works |
| 7 | Tray agent | Close window → tray icon → Quick Chat via hotkey |
| 8 | Performance | All NFR targets met |

---

## 29. Assumptions, Constraints & Dependencies

### Assumptions
- Users have Docker installed and can run containers
- At least one LLM provider API key available (or local Ollama)
- Vault files are markdown (.md) with YAML frontmatter
- macOS or Windows for Electron client (Linux dev only)
- Network access to LLM APIs from Docker container

### Constraints
- Single-process Python backend (no horizontal scaling)
- 3–10 users maximum (RLS + single PostgreSQL)
- No real-time collaboration (users edit in their own editors)
- No mobile client
- ENCRYPTION_KEY must persist across container restarts

### Dependencies

| Dependency | Risk | Mitigation |
|---|---|---|
| LiteLLM library | API changes | Pin version; test in CI |
| pgvector extension | Must be on base image | Use pgvector/pgvector:pg16 |
| Electron | Major version updates | Pin; test on macOS + Windows |
| watchdog | Platform-specific behavior | Reconciliation every 6h |
| Tiptap | Markdown round-trip | Test Day 1 of Phase 3 |

---

## 30. Risks & Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| PostgreSQL crash takes down API | Medium | supervisord auto-restart; external DB mode |
| HNSW recall degrades at 100K+ chunks | Medium | Monitor metrics; per-user schemas if needed |
| File watcher misses Syncthing events | Medium | Reconciliation every 6h; content hash dedup |
| LiteLLM update breaks providers | Medium | Pin version; CI provider tests |
| Tiptap markdown round-trip lossy | **High** | Test Day 1 Phase 3; separate frontmatter storage |
| Agent writes while user editing | **High** | Debounce watcher; conflict dialog |
| SSE drops behind reverse proxy | Medium | Auto-reconnect; Caddy `flush_interval -1` |
| Embedding migration takes hours | Medium | Progress tracking; cancellation; crash recovery |
| Dream deletes wanted memories | Medium | Archived not deleted; audit log; Tab 4i restore |
| Encryption key lost | **High** | Document backup; MultiFernet rotation future |
| Users expect Obsidian-quality editor | Low | "Use Obsidian for advanced editing" |
| captureFromClipboard timeout | Low | 10s timeout; suggest pasting instead |
| RLS context leak | **High** | RESET in finally; code review: every route uses Depends(get_db) |
| Enrichment cascade on bulk rename | Medium | 1-hop limit; debounce |
| Memory import exceeds limit | Low | Client validation; partial import |

---

## 31. Reference Codebases & Resources

> **FOR AI AGENTS:** These repositories provide implementation patterns. Study them for architecture decisions, not to copy code directly.

### Primary References

| Repository | URL | What to Study |
|---|---|---|
| **obsidian-smart-composer** | `https://github.com/glowingjade/obsidian-smart-composer` | PgLite integration patterns, chat UI, RAG pipeline. Smart Copilot's original fork target. |
| **Infio-Copilot** | `https://github.com/infiolab/infio-copilot` | 54K LOC Obsidian AI plugin. State machine autocomplete, FIM prompts, Lexical @mentions, provider abstraction, workspace isolation. MIT licensed, 611+ stars. |

### Architecture Pattern References

| Repository | URL | What to Study |
|---|---|---|
| **LibreChat** | `https://github.com/danny-avila/LibreChat` | Multi-provider LLM chat UI, conversation management, plugin system |
| **Open WebUI** | `https://github.com/open-webui/open-webui` | Self-hosted LLM interface, RAG pipeline, document management |
| **LiteLLM** | `https://github.com/BerriAI/litellm` | Provider translation library. Study the `acompletion` and `aembedding` APIs and callback system |
| **OpenClaw** | Study client-server agent separation pattern | Client-server separation for agent systems |

### Technology Documentation

| Technology | Documentation |
|---|---|
| FastAPI | `https://fastapi.tiangolo.com/` |
| SQLAlchemy 2.0 Async | `https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html` |
| Alembic | `https://alembic.sqlalchemy.org/` |
| pgvector | `https://github.com/pgvector/pgvector` |
| LiteLLM | `https://docs.litellm.ai/` |
| Electron Forge | `https://www.electronforge.io/` |
| Tiptap | `https://tiptap.dev/` |
| Lexical | `https://lexical.dev/` |
| Radix UI | `https://www.radix-ui.com/` |
| APScheduler | `https://apscheduler.readthedocs.io/` |
| watchdog | `https://python-watchdog.readthedocs.io/` |
| DOMPurify | `https://github.com/cure53/DOMPurify` |
| nh3 | `https://nh3.readthedocs.io/` |

---

## 32. Glossary

| Term | Definition |
|---|---|
| **Namespace** | `private` (per-user) or `shared` (team) — controls RLS visibility |
| **Contextual enrichment** | Prepending metadata (title, folder, tags, wikilinks) before embedding |
| **Hybrid RAG** | Vector + BM25 + wikilink graph, combined via RRF |
| **RRF** | Reciprocal Rank Fusion — `score = Σ 1/(k + rank)` across signals |
| **RLS** | Row-Level Security — PostgreSQL per-user data isolation |
| **Mode** | Named system-prompt bundle controlling RAG scope, web, agent |
| **Citation markers** | `[1]`, `[2]` in LLM output mapped to source documents |
| **OperationLog** | JSON record of multi-step file operations for undo |
| **Memory Dream** | Nightly 4-phase memory consolidation cycle |
| **Permanent note** | Atomic idea — core Zettelkasten unit |
| **Literature note** | Summary of external source — citation reference |
| **Fleeting note** | Temporary note, expires from index after N days |
| **Fernet** | Symmetric encryption from Python's `cryptography` library |
| **DOMPurify** | Client-side HTML sanitizer (browser DOM parser) |
| **nh3** | Server-side HTML sanitizer (Rust/Ammonia, defense-in-depth) |
| **Client-cooperative tool** | Agent tool requiring Electron client data via SSE round-trip |
| **key_type** | Whether LLM call used `shared` or `personal` API key |
| **VaultRegistry** | In-memory path → (user_id, namespace) mapping |
| **enrichment_hash** | Hash of enrichment inputs — triggers re-embed on link changes |
| **Advisory lock** | PostgreSQL `pg_try_advisory_lock()` for Dream concurrency |
| **safeStorage** | Electron OS-encrypted storage (macOS Keychain, Windows DPAPI) |
| **SYSTEM_USER_ID** | UUID constant for shared namespace content owner (never logs in) |

---

*End of Smart Copilot PRD v1.0*
