# Smart Copilot — Client-Server Blueprint v0.2.3

**App name**: Smart Copilot
**Repository**: smart-copilot
**Architecture**: Client-server — Python backend (Docker) + Electron desktop client
**Status**: Pre-implementation — nothing built yet
**Target**: v1.0 release
**Blueprint version**: v0.2.3

**Supersedes:** This client-server blueprint is the single authoritative architecture document for Smart Copilot. Earlier reference documents — the Obsidian plugin blueprint (v1.0.2) and the standalone Electron feature comparison — predate the client-server pivot and reference features no longer in scope. Those documents remain useful as design history but should not be treated as current specifications.

**Changelog v0.2.2 → v0.2.3:**
- Removed: All remaining references to discarded RAG alternatives from changelog and supersedes note

**Changelog v0.2.1 → v0.2.2 (consistency audit fixes):**
- Fix: `conversations.project_id` changed from TEXT to `UUID REFERENCES projects(id) ON DELETE SET NULL` — was a type mismatch with `projects.id UUID`
- Fix: Tab 4f "Local LLM endpoints" removed from user settings — contradicted Decision 21 admin-only boundary; replaced with read-only info text showing admin-configured endpoints
- Fix: SSE `access_token` rationale corrected — POST-initiated SSE can carry headers; body field is a convenience fallback, not a necessity
- Fix: `POST /api/v1/auth/register` unprotected route clarified — returns 403 when `allow_registration: false` and users already exist
- Added: Supersedes note — older reference documents (plugin blueprint v1.0.2, standalone Electron feature comparison) predate the client-server pivot and should not be treated as current specifications
- Added: Server-only vs user-overridable settings boundary documented after `settings.yaml` section
- Added: Vault health endpoints — `GET /api/v1/vault/health`, `/vault/hubs`, `/vault/graph`, `/vault/index/events`
- Added: `conversations_user_updated` index on `conversations (user_id, updated_at DESC)`
- Added: APScheduler configured with `SQLAlchemyJobStore` for task persistence across container restarts
- Added: System health snapshot job documented — records `system_health` row every 15 minutes via APScheduler
- Added: Backup script writes `/config/backup-status.json`; `GET /api/v1/admin/health` reads it for Tab 5g "Last backup" display
- Added: Missing Pydantic schema files — `usage.py`, `status.py`, `models.py`, `health.py` in `app/schemas/`
- Added: User settings CRUD and `GET /api/v1/models` moved to Phase 2 (required by mode picker and model picker)
- Added: Phase 7 now explicitly references `POST /api/v1/conversations/{id}/export`
- Added: Phase 6 now explicitly references vault health/hubs/graph/index-events endpoints
- Added: CSRF protection documented as architectural constraint — not needed for Electron-only client (Bearer tokens, no cookies); must be added if API is ever exposed to browser-based clients
- Added: API key serialization safety — `encrypted_key` excluded from all Pydantic response schemas; plaintext key only accessed server-side at LLM call time, never returned to client
- Fixed: `dependencies.py` scoped to DB dependencies only (`get_db_session`, `get_db`); `auth/middleware.py` owns `get_current_user` and `require_admin`
- Fixed: `app/models/dream_audit.py` renamed to `dream_audit_log.py` — consistent with table name `dream_audit_log`
- Removed: `app/documents/epub.py` — EPUB never mentioned in tech stack, import workflows, or narrative

**Changelog v0.2.0 → v0.2.1:**
- Decision 22: VaultRegistry — file watcher path-to-user resolution via username folders mapped to UUIDs
- Decision 23: RLS connection lifecycle — SET/RESET `app.current_user_id` on every DB session checkout/return
- Decision 24: JWT authentication on every API call — full flow with Electron safeStorage, token refresh, SSE auth
- Added: `enrichment_hash` column on `documents` table for cascading re-embedding on wikilink changes
- Added: ChatCompletionRequest schema — full request body spec for `POST /api/v1/chat/completions`
- Added: Atomic chunk delete-and-recreate strategy within transactions
- Added: Memory management UI (Tab 4i) — edit, archive, delete, import, export memories
- Added: Memory API endpoints — update, restore, permanent delete, import, export
- Added: `POST /api/v1/conversations/{id}/regenerate` endpoint
- Added: Backup strategy section — database + vault + encryption key with automated script and restore procedure
- Added: OperationLog step schema with typed actions for undo support
- Added: OpenAPI spec sync workflow — codegen as pre-commit hook, CI validation
- Added: Implementation Phases — 8 phases across 16 weeks with quality gates
- Fixed: Memory storage mode simplified to database-only (removed vault-notes option)
- Fixed: Dream consolidation uses PostgreSQL advisory lock to prevent concurrent runs
- Fixed: Vault export path made explicit (relative to user's private vault root)
- Clarified: `frontmatterQuery` is an internal agent tool with no REST endpoint
- Clarified: `scheduleMaintenance` operates within admin-configured schedule ceiling
- Clarified: Fernet key rotation path via MultiFernet documented as future consideration

**Changelog v0.1.0 → v0.2.0:**
- Decision 20: Embedding dimension managed dynamically via admin UI + migration pipeline
- Decision 21: Role-based access control (admin vs user) with explicit permission boundaries
- Fix: HNSW index added on `memories.embedding` + supporting indexes
- Fix: `user_id` denormalized onto `messages` table for RLS performance
- Fix: supervisord startup uses `wait-for-pg.sh` with `pg_isready` polling + auto-migration
- Fix: `captureFromClipboard()` client-cooperative protocol with client-side normalization
- Added: `system_config` table for embedding model source of truth
- Added: `key_type` column on `llm_usage` for shared vs personal key cost tracking
- Added: `must_change_password` column on `users` for admin password reset flow
- Added: DOMPurify (client) + nh3 (server) for HTML sanitization
- Added: User Dashboard (Page 6a) with My Usage, Vault Health, System Status tabs
- Added: User Account settings tab (Tab 4h)
- Added: Embedding migration API endpoints + admin UI workflow
- Added: User-scoped usage/status API endpoints
- Added: SSE `client_request` event type for client-cooperative agent tools
- Expanded: Admin user management with password reset flow
- Expanded: API key management with user-provided key usage and cost separation

---

## Project Vision

Smart Copilot is a self-hosted AI knowledge management system that brings Zettelkasten automation, a proactive knowledge agent, and hybrid RAG intelligence to markdown files. It consists of a **Python backend** running in a single Docker container (bundled with PostgreSQL + pgvector) and an **Electron desktop client** connected via REST + SSE API.

The backend watches user markdown folders (which may be Obsidian vaults or plain directories), indexes all files into PostgreSQL with pgvector, and provides hybrid RAG search (vector + BM25 + wikilink graph traversal). An autonomous agent with 22 tools maintains the knowledge base: cleaning orphans, suggesting links, organizing files, and refactoring wikilinks when files move. A Memory Dream system automatically consolidates long-term memory, converting stale relative references to absolute timestamps, pruning contradictions, and keeping the memory index lean.

The Electron client is a **chat-first AI knowledge interface** with a split-pane Tiptap WYSIWYG editor. A system tray agent provides Quick Chat access via a global hotkey even when the main window is closed.

The system supports **3–10 users** on a homelab server with per-user private vaults and a shared team knowledge base — designed for small teams and families.

**Core principles:**
- Chat-first — the chat panel is the primary interface; the editor is a companion
- Client-server separation — one Docker container runs everything server-side, the Electron client is thin
- Hybrid namespace from day one — private vaults + shared knowledge, never retrofit sharing later
- PostgreSQL does the heavy lifting — vector search, BM25, graph traversal, all in one database
- LiteLLM as library — no separate LLM gateway service, provider translation happens in-process
- RAG quality over RAG complexity — contextual enrichment + hybrid retrieval covers 90% of use cases
- API keys in the database — never in environment variables or config files; managed via admin UI
- Memory hygiene via Dream cycles — long-term memory is automatically consolidated, not left to rot
- Defense in depth — sanitize untrusted content on both client (DOMPurify) and server (nh3)
- Build must stay green on every commit

---

## Technology Stack

### Backend (Python, single Docker container)

| Layer | Technology | Notes |
|---|---|---|
| Language | Python 3.12+ | |
| API framework | FastAPI | async, native SSE, OpenAPI spec generation |
| Database | PostgreSQL 16 + pgvector | bundled in same container via supervisord |
| DB driver | asyncpg | async PostgreSQL driver |
| ORM / migrations | SQLAlchemy 2.0 + Alembic | async ORM with migration support |
| LLM gateway | LiteLLM (library import) | translates OpenAI format → 100+ providers in-process |
| Background jobs | asyncio + ProcessPoolExecutor | in-process, no Celery, no Redis |
| Task scheduling | APScheduler | in-process cron-like scheduler |
| File watching | watchdog | inotify-based on Linux, polling fallback |
| Markdown parsing | markdown-it-py + python-frontmatter | frontmatter + wikilink extraction |
| HTML sanitization | nh3 | Rust-based (Ammonia/html5ever), defense-in-depth before readability-lxml |
| PDF processing | PyMuPDF (fitz) | text extraction, lazy-loaded |
| DOCX processing | python-docx | text extraction |
| HTML cleaning | readability-lxml | article extraction from web pages (after nh3 sanitization) |
| Web search | httpx | async HTTP client for DuckDuckGo, Jina, Wikipedia |
| Auth | python-jose (JWT) | stateless token auth |
| Encryption | cryptography (Fernet) | API key encryption at rest |
| Validation | Pydantic v2 | request/response models, settings validation |
| Process manager | supervisord | runs PostgreSQL + FastAPI in one container |
| OpenAPI codegen | openapi-typescript | generates TypeScript client types from FastAPI spec |
| Container | Docker | single image: Python app + PostgreSQL + pgvector |

### Frontend (TypeScript, Electron)

| Layer | Technology | Notes |
|---|---|---|
| Platform | Electron (latest stable) | macOS + Windows; Linux for development |
| Language | TypeScript 5.x | |
| Build | Vite (renderer) + esbuild (main process) | Electron Forge |
| Package manager | pnpm | |
| UI framework | React 18 | |
| Chat input | Lexical | rich text with @mentions |
| Editor | Tiptap v2 + @tiptap/markdown | split-pane WYSIWYG |
| Resizable panels | react-resizable-panels | chat / editor split |
| Component library | Radix UI (15 validated primitives) | |
| Styling | CSS modules with `.sc-` prefix | |
| Icons | Lucide React | |
| Command palette | cmdk | |
| Diff rendering | diff + react-diff-viewer-continued | |
| Graph visualization | Cytoscape.js (lazy-loaded) | |
| HTML sanitization | DOMPurify + @types/dompurify | clipboard paste sanitization in Electron renderer |
| Auto-update | electron-updater | |
| API client | Generated from OpenAPI spec | typed, auto-synced with backend |

### OpenAPI spec sync workflow

The backend auto-generates `openapi.json` from FastAPI route definitions on startup. During development, the client runs `pnpm codegen` which fetches `GET /openapi.json` from the running backend and generates TypeScript types + client functions via `openapi-typescript`. This runs as a pre-commit hook in the client repo. In CI, the client build fails if the generated types don't match the committed types — forcing the developer to regenerate after any API change. The spec is versioned as part of the backend's git history (committed as `docs/openapi.json` on each release).

---

## Architecture Overview

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
│                                                               │
│   Single Docker Container: Smart Copilot                     │
│   (supervisord manages both processes)                       │
│                                                               │
│   ┌─────────────────────────────────────────────────────┐   │
│   │ Process 1: FastAPI Backend (Python)                  │   │
│   │  ├── LiteLLM (library — all LLM providers)          │   │
│   │  ├── File Watcher (watchdog thread)                  │   │
│   │  ├── Index Queue (asyncio background tasks)          │   │
│   │  ├── Maintenance Scheduler (APScheduler)             │   │
│   │  ├── Memory Dream Consolidator (nightly cycle)       │   │
│   │  ├── RAG Engine (hybrid search orchestration)        │   │
│   │  ├── Agent Runner (22 tools)                         │   │
│   │  ├── nh3 HTML sanitizer (defense-in-depth)           │   │
│   │  └── Web Search (DuckDuckGo + Jina + Wikipedia)     │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                               │
│   ┌─────────────────────────────────────────────────────┐   │
│   │ Process 2: PostgreSQL 16 + pgvector                  │   │
│   │  ├── Vector search (HNSW indexes)                    │   │
│   │  ├── BM25 full-text search (tsvector + ts_rank_cd)   │   │
│   │  ├── Wikilink graph (adjacency + recursive CTEs)     │   │
│   │  ├── Chat history + conversations + messages         │   │
│   │  ├── Encrypted API keys (per-provider, per-user)     │   │
│   │  ├── Memory storage + dream audit log                │   │
│   │  ├── LLM usage tracking (cost, tokens, latency)      │   │
│   │  └── Row-Level Security (multi-tenant isolation)     │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                               │
└──────────────────────────────────────────────────────────────┘

External (user provides, not managed by Smart Copilot):
  - OpenAI / Anthropic / Gemini / DeepSeek / OpenRouter (cloud APIs)
  - Ollama / LM Studio / vLLM (local LLM servers, if desired)
```

### Why one container

PostgreSQL and the FastAPI backend are bundled into a single Docker image using supervisord. This means `docker run smart-copilot` starts everything — no docker-compose required for basic deployment. The trade-off (process isolation is weaker than separate containers) is acceptable for 3–10 users on a homelab. The Dockerfile builds on `pgvector/pgvector:pg16` and layers in the Python application.

For users who prefer separate containers (production, scaling, or managed PostgreSQL), the backend connects to any external PostgreSQL instance via `DATABASE_URL` — supervisord simply skips starting the internal PostgreSQL process.

---

## Architecture Decisions (Final — Do Not Relitigate)

### Decision 1 — PostgreSQL-only RAG backend

All retrieval uses PostgreSQL + pgvector. PostgreSQL handles vector search (HNSW), BM25 keyword search (tsvector), and wikilink graph traversal (recursive CTEs) — all three retrieval signals in a single database query.

Rationale: The hybrid approach (vector + BM25 + wikilink graph) significantly outperforms naive RAG. Wikilinks in a Zettelkasten are explicit relationship edges — no need for LLM-extracted entity graphs. PostgreSQL eliminates the need for separate vector DB, search engine, and graph DB services.

If a concrete query type later proves unserviceable by hybrid RAG, a `RAGBackend` interface allows adding a graph-based backend behind the same API without touching any feature code.

### Decision 2 — RAG quality strategy: hybrid retrieval + contextual enrichment

Hybrid scoring formula:
```
final_score = (0.5 × vector_cosine_similarity)
            + (0.3 × BM25_keyword_score)
            + (0.2 × wikilink_graph_proximity)
```

All three signals computed in a single PostgreSQL query using Reciprocal Rank Fusion (RRF).

**Contextual enrichment** — prepend metadata before embedding every note. A 15-word atomic note becomes a 60-word enriched document:
```
Note title: {title}
Folder: {folder path}
Tags: {tags}
Linked from: {backlink titles}
Links to: {outlink titles}
Content: {note body}
```

**Note type RAG treatment** — the ContextEnricher reads note type before embedding:
```
type: permanent  → full contextual enrichment, full RAG weight
type: literature → enriched with source metadata, medium RAG weight
type: fleeting   → minimal enrichment, low weight, expires after configurable days
type: project    → stripped of tasks/queries, prose only, excluded from knowledge index
type: structure  → indexed as navigation anchor only, never retrieved as content
type: conversation → agent recall only, never returned by knowledge or citation context
(inferred)       → NoteTypeClassifier infers from folder path + tags
```

Tasks, query blocks, and calendar/event frontmatter are stripped from all notes before embedding — they produce noise in the vector index.

### Decision 3 — LiteLLM as library, not service

LiteLLM is imported as a Python library (`from litellm import acompletion, aembedding`), not run as a separate Docker service. The backend is Python, so there is no need for a proxy server — provider translation happens in-process with zero network hops. Cost tracking uses LiteLLM's callback system logging to PostgreSQL.

### Decision 4 — Shared table + Row-Level Security for multi-tenancy

Single set of tables with `user_id` and `namespace` columns. PostgreSQL RLS enforces isolation at the database level. Each user sees their own private data plus shared knowledge automatically.

Namespace model:
- `private` — user's personal vault (filtered by `user_id`)
- `shared` — team knowledge base (visible to all)

Conversations, memories, LLM usage, and API keys are always private (user_id filter only, no shared access).

### Decision 5 — Hybrid namespace from day one

The filesystem structure maps directly to the access model:
```
/vaults/
  private/
    alice/     ← Alice's private Zettelkasten
    bob/       ← Bob's private notes
  shared/      ← Team knowledge base
```

Publishing a note from private to shared is an intentional act — move or copy the file. Cross-namespace wikilinks use explicit prefix: `[[shared/Topic]]`. Resolution priority: current namespace → shared → other published notes.

### Decision 6 — Single container (backend + PostgreSQL via supervisord)

The Docker image bundles PostgreSQL 16 + pgvector and the FastAPI Python backend. Supervisord manages both processes. No Redis, no Celery, no separate services. Background indexing uses asyncio + ProcessPoolExecutor. Task scheduling uses APScheduler. File watching runs as a thread in the backend process.

For users who want a managed or external PostgreSQL, setting `DATABASE_URL` and `EXTERNAL_DB=true` skips the internal PostgreSQL startup.

### Decision 7 — API keys stored encrypted in database, managed via admin UI

No API keys in environment variables, `.env` files, or config YAML. All LLM provider keys are stored in the `api_keys` table, encrypted at rest using Fernet symmetric encryption. The encryption key is the only secret in the environment (`ENCRYPTION_KEY`).

Admin users configure shared API keys via the Admin Dashboard. Regular users can optionally provide their own keys via User Settings (stored per-user, encrypted). The key resolution order: user's own key → admin-configured shared key → error.

### Decision 8 — SSE for streaming, REST for everything else

Chat responses stream via Server-Sent Events (SSE) over HTTP POST. Agent tool execution emits typed status events (tool_start, tool_result, thinking). All CRUD operations use standard REST. No WebSocket — SSE is simpler, works through proxies, and auto-reconnects.

### Decision 9 — Split-pane layout: chat left, editor right

Chat panel always visible. Editor panel opens on demand from citations, command palette, or agent actions. When no file is open, editor collapses and chat takes full width.

### Decision 10 — Original notes kept as literature notes after Zettel conversion (default)

When a note is split into atomic Zettel notes, the original is **kept by default** as a literature note — never silently deleted. The NoteSplitterModal offers three options:

| Option | Default | Behaviour | RAG treatment |
|---|---|---|---|
| **Keep as literature note** | ✅ yes | Renamed with `type: literature` frontmatter, linked from all child Zettel notes | Citation index only — never knowledge index |
| **Archive original** | no | Moved to configurable archive folder (e.g. `/archive/`) | Same as literature note |
| **Delete original** | no | Requires explicit confirmation dialog — cannot be undone | Removed from all indexes |

Delete requires a second confirmation modal: "This will permanently remove the original note. Your Zettel notes will remain. This cannot be undone." Default button is Cancel.

### Decision 11 — Two RAG retrieval contexts: knowledge and citation

`search()` accepts a `context` parameter controlling which note types are eligible:

| Context | Returns | Used by |
|---|---|---|
| `knowledge` | `type: permanent` notes only | Chat, link suggestions, agent general queries |
| `citation` | `type: literature` notes only | Agent citation tool, "where did I read about X?" queries |
| `all` | All indexed note types | Dashboard analytics, orphan detection, vault health |

Project notes are never returned by any context — only via `frontmatterQuery`. Conversation notes are never returned by `knowledge` or `citation` — only by `all` or the agent's `memoryRecall()`.

### Decision 12 — Composer-based mode system: prompt-scoped pills

Modes are named system-prompt bundles applied to the next message only. Not persistent tabs.

**Behaviour:**
- Single-select only — selecting a mode replaces any active mode, never stacks
- Displayed as a removable pill above the composer input: `[ Research mode ✕ ]`
- Pressing ✕ or sending the message clears the pill (prompt-scoped, not sticky)
- No mode pill active = default behaviour (Ask-equivalent, no system prompt override)
- Mode affects only: system prompt sent to LLM, capability flags (web search, agent tools, RAG scope)

**Mode definitions:**

| Mode | RAG scope | Web search | Agent tools | Semantic purpose |
|---|---|---|---|---|
| **Ask** | vault (private + shared) | off | off | Default Q&A over your notes |
| **Write** | current note in editor | off | off | Focused drafting, no retrieval noise |
| **Research** | vault + web | on (preset) | on | Full agent + web for investigation |
| **Focus** | active project only | off | off | Scoped to current project context |
| *(custom)* | configurable | configurable | configurable | User-defined |

Research mode sets the Web Search toggle to on as a convenience preset. The user can still turn web search off independently without exiting Research mode. The toggle is always the authoritative control — mode is just a preset.

**Mode library:**
- 4 built-in modes (Ask, Write, Research, Focus) — prompts are user-editable, resettable to default
- Unlimited custom mode definitions stored in user settings
- Up to 5 modes pinned to the composer picker (built-in + custom combined)
- Unpinned modes accessible via `⋯ → More modes` in the mode picker
- Built-in modes show `✎` indicator in settings when their prompt has been customised

**Mode data model:**
```python
class ModeConfig:
    id: str
    label: str
    is_built_in: bool
    system_prompt: str
    is_modified: bool            # true when built-in prompt changed from default
    rag_scope: str               # 'vault' | 'project' | 'note' | 'vault+web'
    web_search: bool             # initial state when mode is selected
    agent_tools: bool
```

### Decision 13 — Model selector via LiteLLM model list

Models are configured in the backend's settings. The client fetches available models via `GET /api/v1/models`. LiteLLM's model identifiers (e.g., `anthropic/claude-sonnet-4-20250514`, `ollama/qwen3:8b`) are the canonical IDs. Display name is derived by stripping the provider prefix.

**Behaviour:**
- Sticky within the conversation — set once, persists until manually changed
- On new conversation: reverts to project default model
- Each message records a `model_id` snapshot so history accurately shows which model produced each response

### Decision 14 — Chat history in PostgreSQL, vault export user-triggered

All conversations stored in PostgreSQL automatically. Vault export writes a markdown file to the user's watched folder on demand.

**Why vault export is user-triggered not automatic:** Writing to the vault is a meaningful act in a Zettelkasten system. Saving a conversation should be intentional.

**Vault export — deduplication rules:**
1. **User clicks "Save to Vault" twice** — `exported_path` is set after first export. Button changes to "Open in Vault". Second save is blocked.
2. **File was saved, then manually deleted, user tries again** — backend checks if file exists first. If gone, `exported_path` is cleared and export proceeds fresh.
3. **Sync collision (two devices)** — filename includes a short ID suffix: `2025-02-14 09-30 a3f8c9.md`.

**Delete confirmation behaviour:**
- Conversation saved to vault → delete from DB silently, vault file untouched
- Conversation not yet saved → modal warns "This conversation has not been saved to your vault. Delete anyway?" — default button is Cancel

**End-of-chat save prompt (opt-in, default off):** When enabled and the current conversation has not been saved, shows: `[Save to Vault]  [Not Now]  [Never]`. "Never" sets `never_export` on the record.

**Vault file format:**
```markdown
---
type: conversation
id: a3f8c921
date: 2025-02-14
mode: ask
model: openai/gpt-4o-mini
exported: 2025-02-14T09:45:00
---

# What is confirmation bias?

**You:** What is confirmation bias and how does it affect research?

**Smart Copilot:** Confirmation bias is the tendency to search for...

---

**You:** Can you give me an example from academic publishing?

**Smart Copilot:** A common example is...
```

**RAG treatment of exported vault files:** Conversation files get `type: conversation` frontmatter — never returned by `knowledge` or `citation` context. Accessible by `all` context and the agent's `memoryRecall()` tool.

**Vault export path:** Relative to the user's private vault root. Default: `{vault.base_path}/private/{username}/{chat_history.vault_export_folder}/`. With project subfolders enabled: `{vault.base_path}/private/{username}/{chat_history.vault_export_folder}/{project-name}/`. Example: `/vaults/private/alice/Smart Copilot/Research/2025-02-14 09-30 a3f8c9.md`.

### Decision 15 — Zettel note source backlink always written

Every permanent note created by the NoteSplitter or ZettelNoteBuilder gets a `source` frontmatter field:
```yaml
---
id: 202502141530
type: permanent
source: "[[Literature Note Title]]"
created: 2025-02-14
---
```

This backlink persists even if the literature note is later deleted — the Zettel note retains a record of its origin.

### Decision 16 — Citation system: markers in LLM output, rendered as badges

The system prompt instructs the LLM to output `[1]`, `[2]` markers when citing RAG context. The API response includes a `citations` array mapping markers to search results. The client renders clickable badges. Clicking opens the cited note in the editor panel.

### Decision 17 — File watcher bypassed for app-initiated writes

When the backend creates a file (NoteSplitter, agent vaultWrite), it writes to filesystem AND indexes directly. The watcher will also detect the change but skips files already indexed with matching content hash.

### Decision 18 — Memory Dream consolidation system

Long-term memory degrades over time: relative dates become meaningless, contradictory entries co-exist, debugging notes reference deleted files. The Memory Dream system runs a nightly consolidation cycle in 4 phases:

**Phase 1 — Orientation:** Survey existing memory structure. Count total memories per user, identify memory age distribution, flag memories with relative time references ("yesterday", "last week"), detect memories referencing non-existent notes.

**Phase 2 — Gather Signal:** Targeted search (not full transcript read — kept efficient) for: user corrections that override earlier memories, key architectural or preference decisions, recurring patterns across multiple conversations, facts that appear contradicted by newer facts.

**Phase 3 — Consolidation:** Execute transformations:
- Convert relative dates to absolute timestamps ("yesterday we decided X" → "on 2025-02-14 we decided X")
- Delete memories contradicted by newer entries (keep the newer one, log the deletion)
- Prune stale entries: memories referencing deleted notes, memories older than configurable threshold with no recent recall
- Merge duplicate memories into single authoritative entries
- Resolve conflicting preferences (last explicit statement wins)

**Phase 4 — Prune & Index:** Rebuild the memory index. Target: keep under 200 active memories per user for fast session startup. Archive (don't delete) pruned memories to `dream_audit_log` table. Generate a consolidation report accessible in the admin dashboard.

**Scheduling:** Dream triggers automatically when 24+ hours have passed AND 5+ chat sessions have occurred since the last cycle for a given user. Can also be triggered manually. Processes one user at a time.

### Decision 19 — Admin dashboard built into the app

No external dashboard. LLM usage, costs, indexing status, storage, vault health, API key management, user management, and system health are all tracked in PostgreSQL and served via admin API endpoints. The Electron client renders the dashboard. Standard users get a scoped User Dashboard (Page 6a) with their own usage, vault health, and system status. The full Admin Dashboard (Page 5) is admin-only.

### Decision 20 — Embedding dimension managed dynamically via admin UI + migration pipeline

The embedding model and its dimension are stored in the `system_config` table (not just in `settings.yaml`) so the backend has a single source of truth. The `chunks.embedding` and `memories.embedding` columns use `vector({N})` where N is read from `system_config` at database initialization time.

**Model change workflow:**

1. Admin opens Admin Dashboard → Tab 5c (Storage & Indexing) → "Embedding Model" section
2. Admin selects a new embedding model from the dropdown (populated from `settings.yaml` embedding_models list)
3. Frontend checks: does the new model's dimension differ from the current one?
   - **Same dimension** (e.g., switching between two 1536-dim models): show simple confirmation — "Re-embed all {N} chunks with {new model}? Estimated cost: ${X}, time: ~{Y} minutes." On confirm → `POST /api/v1/admin/embeddings/migrate` with `alter_column: false`
   - **Different dimension** (e.g., 1536 → 768): show a stronger warning — "This will change the embedding dimension from 1536 to 768. The HNSW index will be rebuilt. All {N} chunks and {M} memories will be re-embedded. During migration, search quality may be degraded. Estimated cost: ${X}, time: ~{Y} minutes." On confirm → `POST /api/v1/admin/embeddings/migrate` with `alter_column: true`
4. Backend migration pipeline:
   ```
   Phase 1: Update system_config → migration_status: "running"
   Phase 2: If alter_column=true:
              - DROP INDEX chunks_hnsw, memories_hnsw
              - ALTER TABLE chunks ALTER COLUMN embedding TYPE vector({new_dim})
              - ALTER TABLE memories ALTER COLUMN embedding TYPE vector({new_dim})
   Phase 3: Re-embed all chunks in batches (100 at a time)
              - Update embedding + embedding_model per chunk
              - Report progress via GET /api/v1/admin/embeddings/status
   Phase 4: Re-embed all active memories
   Phase 5: Rebuild HNSW indexes
   Phase 6: Update system_config → new model + dimension + migration_status: "idle"
   ```
5. During migration: search still works but returns degraded results (some chunks have old embeddings, some have new). The hybrid scorer's BM25 and wikilink signals compensate partially. Status bar in the client shows "⟳ Re-embedding: 67% complete"

**Cancellation:** `POST /api/v1/admin/embeddings/cancel` stops the batch processing. Chunks already re-embedded keep their new embeddings. The admin can either resume (re-trigger migrate) or roll back (trigger migrate with the original model).

**Startup validation:** On boot, the backend reads `system_config.embedding` and compares against the actual column dimension. If they disagree AND `migration_status` is `idle`, the backend refuses to start with a clear error. If `migration_status` is `running`, the backend resumes the migration from where it left off (crash recovery).

**Embedding model is strictly admin-only — enforced at three levels:**
1. **API level:** Embedding migration and estimate endpoints require `Depends(require_admin)`. Standard users receive 403.
2. **Settings level:** The RAG tab in user Settings (Tab 4c) shows the current embedding model as read-only display text — not a dropdown. Only the Admin Dashboard (Tab 5c) shows the change-model dropdown.
3. **Config level:** `settings.yaml` `rag.embedding_model` is a server-side config that users cannot override via `user_settings`.

**CLI fallback:** `smart-copilot migrate-embeddings` available as a recovery tool when the admin dashboard isn't accessible.

### Decision 21 — Two roles with explicit permission boundaries (admin vs user)

The system has exactly two roles: `admin` and `user`. No role hierarchy, no custom roles — complexity isn't justified for 3–10 users.

**First-run bootstrap:** The very first account created becomes admin automatically (`auth.first_user_is_admin: true`). The Login page detects this state via `GET /health` returning `{"setup_required": true}` and shows the "Create Admin Account" form instead of the login form.

**Admin-only capabilities:**

| Capability | Why admin-only |
|---|---|
| Create / delete users | User provisioning is an admin function |
| Reset another user's password | Password recovery without email infrastructure |
| Configure shared API keys | Shared keys affect all users' costs |
| Add / remove local LLM endpoints | Infrastructure change affecting all users |
| Change embedding model (trigger migration) | Causes full re-embed, affects all users |
| Force reindex (all users / all namespaces) | Resource-intensive operation |
| View LLM usage by user (cross-user) | Cost visibility across the team |
| View / trigger Memory Dream for other users | Privacy boundary — admin can audit but not read memory content |
| Access Admin Dashboard (Page 5, all tabs) | Aggregate metrics, system health |
| Manage `settings.yaml` overrides | Server-level config changes |

**User self-service capabilities:**

| Capability | Notes |
|---|---|
| Manage own API keys | Override shared keys with personal keys; used for LLM queries |
| Manage own modes, projects, settings | Stored in `user_settings` table |
| Change own password | Via Settings → Account |
| View own LLM usage and costs | User Dashboard — only their own data (RLS enforced) |
| View system status and provider availability | User Dashboard — read-only server health |
| Trigger Memory Dream for self | "Run Dream now" in their Memory panel |
| Force reindex own vault | Only their namespace |
| Export own conversations to vault | User-triggered vault export |
| All chat, RAG, agent, Zettelkasten features | Core functionality is role-independent |

**API enforcement:** Every admin endpoint checks `request.user.role == 'admin'` via a FastAPI dependency:

```python
from fastapi import Depends, HTTPException

async def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
```

**Client enforcement:** The Electron client hides admin UI elements (Admin Dashboard tab, user management, shared API key configuration) when the logged-in user's role is `user`. This is cosmetic only — the API dependency is the real gate.

**Password reset flow (no email):** Since this is a homelab system with no email infrastructure, password reset is admin-mediated:
- Admin clicks "Reset Password" on a user row in Tab 5e
- Backend generates a random temporary password
- Dialog shows: "Temporary password for {username}: `{password}`. This will only be shown once. The user must change their password on next login."
- User's next login with the temporary password forces a password change dialog before proceeding (enforced via `must_change_password` flag on user record)

### Decision 22 — VaultRegistry: file watcher path-to-user resolution

The file watcher monitors `/vaults/` but needs to determine which user owns each changed file. Every INSERT into `documents` and `chunks` requires a `user_id`.

**Vault path convention:** Folders use the username (human-readable). The VaultRegistry maps folder paths to UUIDs from the `users` table — the username is never parsed from the path at query time, it's only used as the folder name on disk.

```
/vaults/
  private/
    alice/     ← VaultRegistry maps this to alice's UUID from users table
    bob/       ← VaultRegistry maps this to bob's UUID from users table
  shared/      ← VaultRegistry maps this to SYSTEM_USER_ID constant
```

```python
class VaultRegistry:
    """Maps filesystem paths to (user_id, namespace) pairs."""
    _mappings: dict[str, tuple[UUID, str]]  # path_prefix → (user_id, namespace)

    async def rebuild(self, db: AsyncSession):
        self._mappings = {}
        base = settings.vault.base_path  # /vaults
        self._mappings[f"{base}/shared/"] = (SYSTEM_USER_ID, "shared")
        users = await db.execute(select(User))
        for user in users.scalars():
            self._mappings[f"{base}/private/{user.username}/"] = (user.id, "private")

    def resolve(self, filepath: str) -> tuple[UUID, str] | None:
        for prefix, identity in self._mappings.items():
            if filepath.startswith(prefix):
                return identity
        return None  # file outside any known vault — skip indexing
```

**Shared namespace ownership:** Files in `/vaults/shared/` are indexed with a dedicated `SYSTEM_USER_ID` (a UUID constant). RLS policies already handle visibility — shared rows are visible to all users. The system user never logs in.

**Registry refresh triggers:** backend startup, user created (`POST /api/v1/admin/users`), user deleted (`DELETE /api/v1/admin/users/{id}`).

**On user creation:** The backend creates the folder at `{vault.base_path}/private/{username}/` and registers the mapping in VaultRegistry.

**Watcher flow:** watchdog detects change → `VaultRegistry.resolve()` → `(user_uuid, namespace)` → `IndexQueue.enqueue()` → Indexer processes. Files outside any vault (resolve returns None) are logged and skipped.

**Why not UUID folders:** Users interact with these folders directly — in Obsidian, file managers, Syncthing. `/vaults/private/alice/` is immediately understandable; a UUID path is not. The registry indirection gives UUID stability internally while keeping the filesystem human-friendly.

### Decision 23 — RLS connection lifecycle: SET/RESET on every DB session

RLS depends on `current_setting('app.current_user_id')`. With asyncpg's connection pool, this must be SET on every checkout and RESET on return. Forgetting this leaks data across users.

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def get_db_session(user_id: UUID):
    """Acquire a connection, set RLS context, yield, then reset."""
    async with async_session_factory() as session:
        await session.execute(
            text("SET app.current_user_id = :uid"),
            {"uid": str(user_id)}
        )
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.execute(text("RESET app.current_user_id"))


async def get_db(current_user: User = Depends(get_current_user)):
    """FastAPI dependency: authenticated DB session with RLS context."""
    async with get_db_session(current_user.id) as session:
        yield session
```

**Rules:**
- Every route handler that queries RLS-protected tables uses `db: AsyncSession = Depends(get_db)`
- Background tasks (indexer, Dream, scheduler) that operate on behalf of a specific user call `get_db_session(user_id)` directly
- `GET /health` and unauthenticated routes use a separate dependency without RLS context
- Admin endpoints that need cross-user visibility use a superuser connection that bypasses RLS

### Decision 24 — JWT authentication on every API call

**Login flow:**
1. Client sends `POST /api/v1/auth/login` with username + password
2. Backend verifies password hash, returns:
   ```json
   {
     "access_token": "eyJ...",
     "refresh_token": "eyJ...",
     "user": {"id": "uuid", "username": "alice", "role": "user", "must_change_password": false}
   }
   ```
3. Client stores both tokens in Electron's `safeStorage` (encrypted at rest via OS keychain — macOS Keychain, Windows DPAPI)

**Every API call:** Client attaches `Authorization: Bearer {access_token}` header. Backend's `get_current_user` dependency validates JWT signature, checks expiry, extracts `user_id` and `role`. If expired → returns 401.

**Token refresh:** When the client receives a 401, it automatically calls `POST /api/v1/auth/refresh` with the refresh token. If valid → new token pair issued. If also expired → redirect to login. The API client wrapper handles this transparently.

**SSE authentication:** SSE connections (`POST /api/v1/chat/completions`) accept the access token in either the `Authorization` header or the request body. The body option exists as a fallback for clients where header injection on streaming requests is inconvenient. Backend validates before opening the stream.

**Token lifetimes:** Access token: 24 hours (configurable via `auth.jwt_expiry_minutes`). Refresh token: 30 days (configurable via `auth.jwt_refresh_expiry_days`). "Remember me" checkbox controls whether the refresh token persists across app restarts.

**Unprotected routes (no JWT required):** `GET /health`, `POST /api/v1/auth/login`, `POST /api/v1/auth/register` (first user only — returns 403 when `allow_registration: false` and users already exist), `POST /api/v1/auth/refresh`.

**CSRF protection:** Not implemented. The API is consumed exclusively by the Electron desktop client, which uses `Authorization: Bearer` headers for every request — not cookies. CSRF attacks require cookie-based auth, so this architecture is not vulnerable. If the API is ever exposed to a browser-based client (e.g., a web-based admin dashboard), CSRF protection (e.g., `SameSite` cookies or CSRF tokens) must be added. This is documented as a constraint, not a planned feature.

---

## Multi-Tenancy Model

### Database schema

```sql
-- ═══ SYSTEM CONFIG (server-wide settings source of truth) ═══
CREATE TABLE system_config (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Seeded on first run:
-- key: 'embedding', value: {"model": "openai/text-embedding-3-small", "dimensions": 1536, "migration_status": "idle"}

-- ═══ USERS & AUTH ═══
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'user',  -- 'admin' | 'user'
    must_change_password BOOLEAN DEFAULT false,  -- true after admin password reset
    last_dream_at TIMESTAMPTZ,
    sessions_since_dream INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ═══ API KEYS (encrypted at rest) ═══
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),       -- NULL = shared (admin-configured)
    provider TEXT NOT NULL,
    encrypted_key TEXT NOT NULL,
    display_hint TEXT,                         -- 'sk-...abc' (last 3 chars for identification)
    is_valid BOOLEAN DEFAULT true,
    last_tested_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (user_id, provider)
);

-- ═══ DOCUMENTS (source files) ═══
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    namespace TEXT NOT NULL DEFAULT 'private',
    path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    enrichment_hash TEXT,              -- hash(title+folder+tags+backlinks+outlinks); triggers re-embed when wikilinks change
    note_type TEXT DEFAULT 'permanent',
    frontmatter JSONB DEFAULT '{}',
    title TEXT,
    folder TEXT,
    tags TEXT[] DEFAULT '{}',
    word_count INT DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (user_id, namespace, path)
);

-- ═══ CHUNKS (embeddings + full-text) ═══
-- Note: embedding dimension is set dynamically at migration time
-- from system_config.embedding.dimensions (default: 1536)
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    namespace TEXT NOT NULL DEFAULT 'private',
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    enriched_content TEXT,
    embedding vector(1536),
    embedding_model TEXT,
    content_tsvector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', content)
    ) STORED,
    chunk_index INT DEFAULT 0
);

CREATE INDEX chunks_hnsw ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX chunks_fts ON chunks USING gin (content_tsvector);
CREATE INDEX chunks_user_ns ON chunks (user_id, namespace);
CREATE INDEX chunks_document ON chunks (document_id);

-- ═══ WIKILINKS (graph edges) ═══
CREATE TABLE wikilinks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_doc UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    target_doc UUID REFERENCES documents(id) ON DELETE SET NULL,
    target_name TEXT NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id),
    namespace TEXT NOT NULL DEFAULT 'private'
);

CREATE INDEX wikilinks_source ON wikilinks (source_doc);
CREATE INDEX wikilinks_target ON wikilinks (target_doc);
CREATE INDEX wikilinks_user ON wikilinks (user_id);

-- ═══ CONVERSATIONS ═══
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    title TEXT,
    model_id TEXT,
    mode_id TEXT,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    exported_path TEXT,
    never_export BOOLEAN DEFAULT false,
    web_search_enabled BOOLEAN DEFAULT false,
    relevant_note_enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX conversations_user_updated ON conversations (user_id, updated_at DESC);

-- ═══ MESSAGES (user_id denormalized from conversation for RLS performance) ═══
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    model_id TEXT,
    mode_id TEXT,
    citations JSONB,
    temperature FLOAT,
    max_tokens INT,
    system_prompt_override TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX messages_conversation ON messages (conversation_id, created_at);
CREATE INDEX messages_user ON messages (user_id);

-- Note: messages.user_id is denormalized from conversations.user_id to avoid
-- a correlated subquery in RLS evaluation. The API layer sets
-- messages.user_id = conversations.user_id on every insert.

-- ═══ MEMORIES ═══
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    content TEXT NOT NULL,
    embedding vector(1536),
    source_conversation_id UUID REFERENCES conversations(id),
    absolute_date TEXT,
    last_recalled_at TIMESTAMPTZ,
    recall_count INT DEFAULT 0,
    is_archived BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX memories_hnsw ON memories USING hnsw (embedding vector_cosine_ops);
CREATE INDEX memories_user ON memories (user_id);
CREATE INDEX memories_active ON memories (user_id, is_archived) WHERE is_archived = false;

-- ═══ DREAM AUDIT LOG ═══
CREATE TABLE dream_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    dream_run_at TIMESTAMPTZ NOT NULL,
    phase TEXT NOT NULL,
    action TEXT NOT NULL,
    memory_id UUID REFERENCES memories(id),
    old_content TEXT,
    new_content TEXT,
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ═══ PROJECTS ═══
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    include_folders TEXT[] DEFAULT '{}',
    exclude_folders TEXT[] DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    system_prompt TEXT,
    default_model_id TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ═══ OPERATION LOG (undo support) ═══
CREATE TABLE operation_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    operation_type TEXT NOT NULL,
    steps JSONB NOT NULL,
    undone BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ═══ LLM USAGE TRACKING ═══
CREATE TABLE llm_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    model TEXT NOT NULL,
    provider TEXT NOT NULL,
    prompt_tokens INT,
    completion_tokens INT,
    cost_usd NUMERIC(10,6),
    latency_ms INT,
    status TEXT,
    error_message TEXT,
    purpose TEXT,       -- 'chat' | 'embedding' | 'agent' | 'enrichment' | 'dream'
    key_type TEXT DEFAULT 'shared',  -- 'shared' | 'personal'
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX llm_usage_user_date ON llm_usage (user_id, created_at);
CREATE INDEX llm_usage_key_type ON llm_usage (user_id, key_type);

-- ═══ INDEX EVENTS ═══
CREATE TABLE index_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    namespace TEXT NOT NULL,
    event_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    chunks_created INT,
    embedding_model TEXT,
    processing_ms INT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ═══ SYSTEM HEALTH SNAPSHOTS ═══
CREATE TABLE system_health (
    id SERIAL PRIMARY KEY,
    db_size_bytes BIGINT,
    total_chunks INT,
    total_documents INT,
    index_queue_depth INT,
    pg_connections_active INT,
    recorded_at TIMESTAMPTZ DEFAULT now()
);

-- ═══ USER SETTINGS (per-user preferences) ═══
CREATE TABLE user_settings (
    user_id UUID PRIMARY KEY REFERENCES users(id),
    settings JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ═══ ROW-LEVEL SECURITY ═══
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

-- Content tables: user sees own + shared
CREATE POLICY tenant_isolation ON documents
    USING (namespace = 'shared' OR user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY tenant_isolation ON chunks
    USING (namespace = 'shared' OR user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY tenant_isolation ON wikilinks
    USING (namespace = 'shared' OR user_id = current_setting('app.current_user_id')::uuid);

-- Private tables: user sees own only (direct equality — no subquery)
CREATE POLICY private_only ON conversations
    USING (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY private_only ON messages
    USING (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY private_only ON memories
    USING (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY private_only ON dream_audit_log
    USING (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY private_only ON projects
    USING (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY private_only ON operation_log
    USING (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY private_only ON llm_usage
    USING (user_id = current_setting('app.current_user_id')::uuid);
CREATE POLICY private_only ON user_settings
    USING (user_id = current_setting('app.current_user_id')::uuid);

-- API keys: user sees own + shared (admin-created where user_id IS NULL)
CREATE POLICY api_key_access ON api_keys
    USING (user_id IS NULL OR user_id = current_setting('app.current_user_id')::uuid);
```

---

## API Key Management

### Encryption at rest

All API keys are encrypted using Fernet symmetric encryption before storage:

```python
from cryptography.fernet import Fernet

fernet = Fernet(os.environ["ENCRYPTION_KEY"])

def encrypt_key(plain_key: str) -> str:
    return fernet.encrypt(plain_key.encode()).decode()

def decrypt_key(encrypted_key: str) -> str:
    return fernet.decrypt(encrypted_key.encode()).decode()

def display_hint(plain_key: str) -> str:
    return f"...{plain_key[-4:]}" if len(plain_key) > 4 else "****"
```

**Serialization safety:** The `encrypted_key` column is excluded from all Pydantic response schemas by default. API responses (`GET /api/v1/admin/api-keys`, `GET /api/v1/settings/api-keys`) return only `id`, `provider`, `display_hint`, `is_valid`, `last_tested_at`, and `created_at` — never the encrypted or plaintext key. The `ApiKeyResponse` schema must not include `encrypted_key`. The plaintext key is only accessible server-side via `decrypt_key()` at the moment of LLM API call and is never logged, cached, or returned to the client.

### Key resolution order

When the backend needs an API key for a provider:
1. Check if the user has their own key for this provider → use it → track cost as `key_type: 'personal'`
2. Check if an admin-configured shared key exists (user_id IS NULL) → use it → track cost as `key_type: 'shared'`
3. No key available → return error to client with message "No API key configured for {provider}"

### User-provided API keys: motivation and behaviour

In a homelab team of 3–10 people, the admin typically configures shared API keys that everyone uses. But there are legitimate reasons a user might provide their own:

- **Cost separation** — a user doing heavy research doesn't want their costs charged to the shared pool
- **Model access** — user has an API key with access to models the shared key doesn't cover
- **Rate limits** — user hits the shared key's rate limit and wants to use their own quota
- **Privacy preference** — user prefers their queries go through their own API account

**Cost tracking distinguishes key ownership** via the `key_type` column on `llm_usage`. This enables the User Dashboard to show cost breakdowns by shared vs personal key usage.

**LiteLLM callback with key type tracking:**

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

**UI indication:** When a user has their own key configured for the active model's provider, the model picker shows a subtle indicator: `GPT-4o 🔑` (personal key) vs `GPT-4o` (shared key).

### Admin workflow

Admin configures shared keys via Admin Dashboard → Tab 5d (API Keys). These are available to all users. Users can optionally override with their own key via User Settings → Tab 4f (API Keys).

### Test connection

Both admin and user key management include a "Test" button that makes a minimal API call to verify the key is valid. Result stored as `is_valid` and `last_tested_at`.

### Key rotation (future consideration)

Fernet supports rotation via `MultiFernet`, which accepts a list of keys — encrypts with the first, decrypts by trying all. To rotate: generate a new key, set `ENCRYPTION_KEY=new_key,old_key` (comma-separated), and re-encrypt all stored keys via `smart-copilot rotate-keys` CLI command. This is not implemented in v1.0 but the architecture supports it without schema changes.

---

## HTML Sanitization

Smart Copilot handles untrusted HTML from multiple sources: clipboard paste, web page capture (Jina Reader), uploaded HTML files, and the `captureFromURL` agent tool. A defense-in-depth approach sanitizes at both client and server layers.

### Client-side: DOMPurify (Electron renderer)

DOMPurify uses the browser's native `DOMParser` to parse HTML, then walks the DOM tree to remove disallowed nodes. In Electron's Chromium renderer, this requires zero additional dependencies.

```typescript
import DOMPurify from 'dompurify';

const SANITIZE_CONFIG: DOMPurify.Config = {
  ALLOWED_TAGS: [
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'p', 'blockquote', 'pre',
    'ul', 'ol', 'li',
    'a', 'em', 'strong', 'code',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'img', 'br',
  ],
  ALLOWED_ATTR: [
    'href', 'src', 'alt', 'title',
    'colspan', 'rowspan',
  ],
  ALLOW_DATA_ATTR: false,
  ALLOW_ARIA_ATTR: false,
  ALLOW_UNKNOWN_PROTOCOLS: false,
};

DOMPurify.addHook('afterSanitizeAttributes', (node: Element) => {
  if (node.tagName === 'A') {
    node.setAttribute('rel', 'noopener noreferrer');
    const href = node.getAttribute('href');
    if (href && !/^(https?:|mailto:|#)/i.test(href)) {
      node.removeAttribute('href');
    }
  }
  if (node.tagName === 'IMG') {
    const src = node.getAttribute('src');
    if (src && !/^https?:/i.test(src)) {
      node.removeAttribute('src');
    }
  }
});

export function sanitizeClipboardHtml(dirtyHtml: string): string {
  return DOMPurify.sanitize(dirtyHtml, SANITIZE_CONFIG);
}
```

### Server-side: nh3 (Python, defense-in-depth)

nh3 is a Rust-based Python binding to the Ammonia HTML sanitizer using html5ever (Firefox's parser). It re-sanitizes all HTML before `readability-lxml` processing — this catches: direct API calls bypassing the client, server-side URL fetches that never touch Electron, and any client-side bypass.

```python
import nh3

html_cleaner = nh3.Cleaner(
    tags={
        "h1", "h2", "h3", "h4", "h5", "h6",
        "p", "blockquote", "pre",
        "ul", "ol", "li",
        "a", "em", "strong", "code",
        "table", "thead", "tbody", "tr", "td", "th",
        "img",
    },
    attributes={
        "a": {"href", "title"},
        "img": {"src", "alt", "title", "width", "height"},
        "td": {"colspan", "rowspan"},
        "th": {"colspan", "rowspan", "scope"},
    },
    clean_content_tags={"script", "style", "iframe", "object", "embed", "noscript"},
    url_schemes={"http", "https", "mailto"},
    link_rel="noopener noreferrer",
    strip_comments=True,
)

def sanitize_html(dirty_html: str) -> str:
    if not dirty_html:
        return ""
    return html_cleaner.clean(dirty_html)
```

### Sanitization flow by source

```
Clipboard paste → DOMPurify (client) → API → nh3 (server) → readability-lxml → markdown
URL capture     →                       API → nh3 (server) → readability-lxml → markdown
HTML upload     →                       API → nh3 (server) → readability-lxml → markdown
```

---

## Indexing Strategy

### Cascading re-enrichment on wikilink changes

The `documents.content_hash` tracks the raw file content. The `documents.enrichment_hash` tracks the inputs that affect contextual enrichment but aren't part of the note body: `hash(title + folder + tags + sorted(backlink_titles) + sorted(outlink_titles))`.

**Indexer flow on file change:**
1. File changed → compute `content_hash`
2. If `content_hash` unchanged AND `enrichment_hash` unchanged → skip (no work)
3. If `content_hash` changed → full re-process: parse, enrich, re-chunk, re-embed
4. If `content_hash` unchanged BUT `enrichment_hash` changed → re-enrich and re-embed existing chunks (note body didn't change, but context around it did)

**Cascade trigger:** After indexing any document, the indexer checks: "Did this document's wikilinks change?" If yes, mark all linked documents for `enrichment_hash` recalculation. Cascade depth is limited to 1 hop — changing note A triggers re-enrichment of note B (whose backlinks changed) but NOT note C (note B still links to it, so C's backlinks didn't change).

### Chunk replacement: atomic delete-and-recreate

When a document's content changes (`content_hash` differs), all chunks are replaced within a transaction:

```python
async def reindex_document(doc_id: UUID, new_content: str, session: AsyncSession):
    async with session.begin_nested():  # SAVEPOINT
        # 1. Delete old chunks
        await session.execute(delete(Chunk).where(Chunk.document_id == doc_id))
        # 2. Parse and chunk new content
        chunks = chunker.split(new_content)
        # 3. Enrich each chunk
        enriched = [enricher.enrich(chunk, doc_metadata) for chunk in chunks]
        # 4. Batch embed
        embeddings = await embedder.batch_embed(enriched)
        # 5. Insert new chunks
        for i, (chunk, enriched_text, embedding) in enumerate(
            zip(chunks, enriched, embeddings)
        ):
            session.add(Chunk(
                document_id=doc_id, user_id=doc.user_id, namespace=doc.namespace,
                content=chunk, enriched_content=enriched_text, embedding=embedding,
                embedding_model=current_embedding_model, chunk_index=i,
            ))
        # 6. Update document metadata
        doc.content_hash = new_hash
        doc.enrichment_hash = new_enrichment_hash
```

The `begin_nested()` SAVEPOINT ensures atomicity — if embedding fails midway, the DELETE rolls back and old chunks are restored. The note is never unsearchable.

For enrichment-only updates (`enrichment_hash` changed, `content_hash` didn't): update existing chunk rows' `enriched_content` and `embedding` in place rather than deleting and recreating.

---

## Hybrid RAG Search

All three retrieval signals computed in a single PostgreSQL query using Reciprocal Rank Fusion (RRF):

1. **Vector similarity** (weight 0.5) — pgvector HNSW index, cosine distance
2. **BM25 keyword search** (weight 0.3) — PostgreSQL `tsvector` + `ts_rank_cd`
3. **Wikilink graph proximity** (weight 0.2) — recursive CTE traversal up to 3 hops from context note

RLS automatically includes shared namespace rows alongside the user's private data.

**Note type classification** (frontmatter-driven with folder/tag inference):

| Type | Frontmatter | Purpose | RAG treatment |
|---|---|---|---|
| `permanent` | `type: permanent` | Single atomic idea | Full enrichment, full RAG weight, `knowledge` context |
| `literature` | `type: literature` | Summary of a source | Enriched with source metadata, `citation` context |
| `fleeting` | `type: fleeting` | Quick capture, inbox | Minimal enrichment, low weight, expires after N days |
| `project` | `type: project` | Planning, tasks, journaling | Excluded from knowledge RAG, only via `frontmatterQuery` |
| `structure` | `type: structure` | MOC / index note | Navigation anchor only, never retrieved as content |
| `conversation` | `type: conversation` | Saved chat history | Agent recall only |

If no `type:` frontmatter exists, Smart Copilot infers: notes in `/projects/` or `/journal/` → project, notes with `#fleeting` tag → fleeting, everything else → permanent.

---

## LLM Integration via LiteLLM

LiteLLM imported as a Python library:

```python
from litellm import acompletion, aembedding

api_key = await resolve_api_key(user_id, provider="anthropic")

response = await acompletion(
    model="anthropic/claude-sonnet-4-20250514",
    messages=messages,
    stream=True,
    api_key=api_key
)
```

**Supported providers** (no code changes to add new ones — just add key in admin UI):
- OpenAI, Anthropic, Google Gemini, DeepSeek, OpenRouter
- Ollama, LM Studio, vLLM, or any OpenAI-compatible endpoint

---

## Agent System

### 22 tools

**Auto-approve (read-only — no confirmation needed):**

| # | Tool | Description |
|---|---|---|
| 1 | `ragSearch(query, context)` | Hybrid RAG search — vector + BM25 + wikilink graph |
| 2 | `vaultRead(path)` | Read a note's full content |
| 3 | `detectOrphans()` | Find notes with zero incoming wikilinks |
| 4 | `suggestLinks(notePath)` | Find notes that should link to/from this note |
| 5 | `analyzeNote(notePath)` | Orphan status, connection count, note type, word count |
| 6 | `memoryRecall(query)` | Semantic search over user's memory store |
| 7 | `frontmatterQuery(field, op, value)` | Query notes by frontmatter (replaces Dataview DQL) |
| 8 | `reconcileIndex()` | Compare filesystem vs DB index, fix drift |
| 9 | `scheduleMaintenance(task, schedule)` | Register recurring maintenance tasks |
| 10 | `notifyUser(title, body)` | Send notification to Electron client via SSE |
| 11 | `openInEditor(path)` | Signal client to open file in Tiptap editor or external editor |

**Require user confirmation (write operations):**

| # | Tool | Description |
|---|---|---|
| 12 | `vaultWrite(path, content)` | Create, append, or replace a file + immediate indexing |
| 13 | `webSearch(query)` | Search web when toggle is on |
| 14 | `splitNote(notePath)` | Run NoteSplitter — H1/H2/H3 boundary splitting |
| 15 | `generateMOC(topic)` | Create Map of Content from related notes |
| 16 | `organizeVault()` | Suggest + apply folder reorganization |
| 17 | `captureFromURL(url)` | Jina Reader → nh3 sanitize → markdown → literature note → offer split |
| 18 | `captureFromClipboard()` | Client-cooperative: request clipboard, process, save as note |
| 19 | `moveAndRefactor(path, newPath)` | Move file + update all wikilinks |
| 20 | `batchOrganize(plan)` | Multi-file move with OperationLog for undo |
| 21 | `undoLastOrganize()` | Reverse last batch operation |
| 22 | `cleanOrphans(strategy)` | Archive / delete / suggest-merge orphan notes |

### Agent execution model

- Plan → execute → observe loop
- Max 10 tool calls per turn (configurable)
- Streams partial results to client via SSE while working
- Confirmation gate before all write/create/move operations
- OperationLog records multi-step operations for undo

**Tool-specific clarifications:**

`frontmatterQuery` executes as a direct database query within the AgentRunner's session. It has no corresponding REST endpoint — it's an internal tool only accessible through the agent. Users needing structured queries outside of agent mode use `POST /api/v1/search` with filter parameters.

`scheduleMaintenance` operates within the admin-configured schedule ceiling. `agent.maintenance_schedule` in `settings.yaml` sets the maximum frequency (weekly/daily/never). The agent can register specific tasks within those constraints (e.g., "run reconciliation next Sunday at 3am") but cannot override the admin's schedule to run more frequently than allowed. Registered tasks are persisted via APScheduler's `SQLAlchemyJobStore` (backed by PostgreSQL) and survive container restarts.

### OperationLog step schema

The `operation_log.steps` JSONB column uses a typed schema for undo support:

```python
class OperationStep(BaseModel):
    action: str               # "move" | "create" | "delete" | "update_links"
    source_path: str
    target_path: str | None   # for move/rename
    old_content: str | None   # for update_links (original file content before link rewrite)
    affected_links: list[str] # paths of files whose wikilinks were updated
    timestamp: datetime

class OperationRecord(BaseModel):
    operation_type: str       # "organize" | "batch_move" | "clean_orphans"
    steps: list[OperationStep]
    description: str          # human-readable: "Moved 23 notes to /concepts/ml/"
```

Undo processes steps in reverse: "move" → move back from `target_path` to `source_path`; "update_links" → restore `old_content`; "create" → delete the created file.

### Client-cooperative agent tools

Most agent tools execute entirely on the backend. Two tools require data from the Electron client that the backend cannot access directly:

| Tool | Client resource needed | Protocol |
|---|---|---|
| `captureFromClipboard()` | System clipboard contents | Request-response via SSE + REST |
| `openInEditor(path)` | Electron shell / window focus | Fire-and-forget via SSE |

**`captureFromClipboard()` protocol:**

```
1. Agent decides to call captureFromClipboard()
2. Backend emits SSE event:
   data: {"type":"client_request","data":{"request_id":"uuid","action":"read_clipboard","max_payload_bytes":5242880}}

3. Electron client receives event, reads clipboard, normalizes content:
   - Plain text: trim, normalize line endings, truncate at 500KB, strip null bytes
   - HTML: sanitize via DOMPurify (strip script/style/iframe/event handlers),
     preserve semantic markup, truncate at 1MB
   - URL: validate HTTP(S), strip tracking parameters (utm_*, fbclid, gclid)
   - Image: resize if >4096px, compress to ≤5MB PNG, base64 encode,
     re-encode via nativeImage to strip EXIF metadata
   - File path: send as text only — client does NOT read the file (security boundary)
   - Empty clipboard: respond with error payload

4. Client POSTs to backend:
   POST /api/v1/agent/client-response
   {
     "request_id": "uuid",
     "action": "read_clipboard",
     "content_type": "text/html",
     "content": "...",
     "content_length": 12345,
     "metadata": {
       "source_url": "...",
       "original_format": "text/html"
     }
   }

5. Backend re-sanitizes HTML via nh3 (defense-in-depth), then processes:
   - text/plain → NoteTypeClassifier → save as note
   - text/html → nh3 → readability-lxml → markdown → literature note → offer split
   - text/url → Jina Reader fetch → nh3 → markdown → literature note
   - image/png → vision LLM description → save as note with image reference

6. Agent requests user confirmation before creating the note
```

**Timeout:** If the client doesn't respond within 10 seconds (app minimized, window closed), the agent emits an error and continues without blocking: "Clipboard not available — client did not respond. Try pasting content directly into chat."

**`openInEditor(path)` protocol:** Fire-and-forget. Backend emits the SSE event, client opens the file. No response needed.

### Background agent (proactive mode, opt-in)

Runs on configurable schedule (APScheduler):
1. Check if vault health score drops below threshold → notify user
2. If orphan count exceeds threshold → suggest cleanup
3. If new notes lack wikilinks → suggest connections
4. Run scheduled maintenance tasks (reconcile index, etc.)
5. Run Memory Dream consolidation cycle (nightly)
6. Record system health snapshot every 15 minutes — inserts a row into `system_health` with database size, total chunks, total documents, active PostgreSQL connections, and index queue depth

**APScheduler persistence:** APScheduler is configured with `SQLAlchemyJobStore` pointed at the application's PostgreSQL database. This ensures that agent-registered maintenance tasks (via `scheduleMaintenance`) and recurring background jobs survive container restarts. The job store table is created automatically by APScheduler on first run.

---

## Memory Dream Consolidation System

### Problem

Long-term memory degrades over time in all persistent AI systems. After 10–15 sessions, accumulated memories become noise.

### Solution: 4-phase nightly consolidation

**Phase 1 — Orientation:** Survey existing memory structure for this user. Count total active memories, age distribution. Identify memories with relative time references. Detect memories referencing note paths that no longer exist.

**Phase 2 — Gather Signal:** Targeted search for: user corrections, key decisions that override earlier preferences, recurring patterns, contradicted facts. Uses LLM (purpose: `dream` in llm_usage tracking).

**Phase 3 — Consolidation:** Execute transformations (each logged to `dream_audit_log`):
- Date resolution: relative → absolute timestamps
- Contradiction deletion: keep newer, archive older with reason
- Stale pruning: memories referencing deleted notes → archived; memories older than 90 days with zero recalls → archived
- Duplicate merge: consolidate into single authoritative entry
- Preference resolution: last explicit statement wins

**Phase 4 — Prune & Index:** Count remaining active memories. If count exceeds 200: archive lowest-recall, oldest until under 200. Re-embed modified memories. Generate consolidation summary.

### Trigger conditions

Dream runs automatically when **both** conditions are met for a user:
1. **24+ hours** since the last Dream cycle
2. **5+ chat sessions** since the last Dream cycle

Additional triggers: manual via admin dashboard (per-user or all users), manual via user's Memory panel ("Run Dream now").

Execution: checked every hour by APScheduler. Processes one user at a time. Uses cheapest model (e.g., `gpt-4o-mini`). Skips users with fewer than 20 memories.

**Concurrency guard:** The APScheduler check acquires a PostgreSQL advisory lock (`pg_try_advisory_lock(hashtext('dream'))`) before processing. If the lock is held (a Dream run is already in progress), the check skips silently. This prevents overlapping runs if a Dream cycle exceeds 60 minutes. The lock is released when the cycle completes or errors.

**Memory storage is database-only.** Memories are stored in the `memories` PostgreSQL table. Users can export memories to markdown/JSON via the Memory settings tab (one-way export, similar to conversation vault export), and re-import on another instance. The database is always the canonical store. This keeps Dream consolidation simple — it operates entirely on SQL.

---

## Zettelkasten Workflows

### Workflow A — Import external document, then convert

For PDFs, web articles, DOCX files from outside the vault:

1. User uploads file via chat or uses "Import Document" command
2. Backend extracts clean text (HTML is sanitized via nh3 before readability-lxml) → saves as literature note
3. Full content stored in literature note body
4. Backend offers: "This note is {N} words — split into Zettel notes?"
5. If accepted → NoteSplitter runs (H1 > H2 > H3 boundaries, atomic permanent notes with source backlinks)
6. Literature note updated: links to all child Zettel notes
7. Client opens literature note in editor panel

### Workflow B — Chat conversation to Zettel note

1. User chats normally
2. "@zettel save this" or "Save this as a Zettel note"
3. AI distills insight into atomic note format
4. ZettelNotePreviewModal shows proposed note
5. User edits and accepts → backend writes + indexes immediately

### Workflow C — Convert existing long note in place

1. Command palette: "Split This Note" OR auto-offer when note exceeds min_word_count
2. Same NoteSplitter flow as Workflow A
3. Original note becomes literature note
4. Options: Keep as literature (default) / Archive / Delete (confirmation required)

---

## Web Search

**Free built-in (no API keys required):** DuckDuckGo, Jina AI Reader, Wikipedia API.

**Optional paid (admin configures API key in dashboard):** Tavily, Brave Search, SerpAPI.

Usage: `@web [query]` in chat, Web Search toggle in More drawer, Research mode auto-enables.

Cross-reference: compare web results against vault notes.

---

## API Design

### Chat completions request body

```python
class ChatCompletionRequest(BaseModel):
    conversation_id: UUID                          # existing conversation or new
    message: str                                   # user's message content

    # Model & mode (override conversation defaults)
    model_id: str | None = None                    # e.g. "openai/gpt-4o"; None = use conversation.model_id
    mode_id: str | None = None                     # e.g. "research"; None = no mode active

    # Context
    current_note_path: str | None = None           # for Write mode scoping; path relative to vault root
    file_references: list[str] = []                # @mention file paths from Lexical input

    # Per-message overrides (from Chat Settings popover)
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    frequency_penalty: float | None = None
    system_prompt_override: str | None = None      # takes precedence over mode prompt when non-empty

    # Toggles (from More drawer — per-conversation state)
    web_search_enabled: bool = False
    relevant_note_enabled: bool = True

    # Agent
    agent_enabled: bool = False                    # true when mode has agent_tools: true

    # Auth (for SSE — can't use headers after initial request)
    access_token: str | None = None                # alternative to Authorization header for SSE
```

**Backend processing flow:**
1. Validate `conversation_id` belongs to current user
2. Append user message to `messages` table (with `user_id` denormalized)
3. Build context: resolve `mode_id` → system prompt, apply `system_prompt_override` if non-empty
4. If `relevant_note_enabled`: run `ragSearch(message, context='knowledge')`, scope by mode's `rag_scope`
5. If `mode_id == 'write'` and `current_note_path` is set: restrict RAG to that single document only. If `current_note_path` is null (no file open): RAG disabled entirely, LLM uses conversation history only
6. If `file_references` is non-empty: fetch those specific documents as additional context
7. Resolve model from `model_id` → LiteLLM identifier, resolve API key (user → shared → error)
8. Call LiteLLM `acompletion()` with streaming
9. Stream tokens via SSE, recording the assistant message to DB on completion
10. If `agent_enabled`: run AgentRunner with tool results streamed as SSE events

### Endpoints

**Auth:**
- `POST /api/v1/auth/register` — create account (admin only, or first user auto-admin)
- `POST /api/v1/auth/login` — returns JWT access + refresh tokens
- `POST /api/v1/auth/refresh` — refresh JWT
- `POST /api/v1/auth/change-password` — user changes own password (requires current password)

**Chat:**
- `POST /api/v1/chat/completions` — streaming SSE chat with RAG context and citations
- `GET /api/v1/conversations` — list conversations (paginated, search, date filter)
- `GET /api/v1/conversations/{id}` — get conversation with messages
- `POST /api/v1/conversations` — create conversation
- `PATCH /api/v1/conversations/{id}` — update title, model, mode, etc.
- `DELETE /api/v1/conversations/{id}` — delete conversation
- `POST /api/v1/conversations/{id}/export` — export to vault as markdown
- `POST /api/v1/conversations/{id}/regenerate` — delete last assistant message and re-run completion; accepts optional overrides (model_id, temperature)

**Search:**
- `POST /api/v1/search` — hybrid RAG search (vector + BM25 + wikilink)
- `POST /api/v1/search/semantic` — vector-only search
- `POST /api/v1/search/keyword` — BM25-only search

**Documents:**
- `GET /api/v1/documents` — list indexed documents (paginated, filter by type/folder/tag)
- `GET /api/v1/documents/{id}` — get document metadata + content
- `PUT /api/v1/documents/{id}` — update document content (write to filesystem + reindex)
- `POST /api/v1/documents/upload` — upload file for import (PDF, DOCX, HTML)
- `GET /api/v1/documents/upload/{task_id}/status` — poll import progress

**Vault operations:**
- `POST /api/v1/vault/write` — create or update a file
- `POST /api/v1/vault/move` — move file + update wikilinks
- `POST /api/v1/vault/split` — split note into atomic Zettel notes
- `GET /api/v1/vault/orphans` — list orphan notes
- `GET /api/v1/vault/hubs` — list most-connected notes (highest incoming wikilink count, top N)
- `GET /api/v1/vault/health` — vault health score (composite: orphan %, link density, type coverage) + summary metrics
- `GET /api/v1/vault/graph` — wikilink graph as nodes + edges (for Cytoscape visualization)
- `GET /api/v1/vault/index/events` — user's recent index events (paginated, user's namespace only)
- `GET /api/v1/vault/links/suggestions/{doc_id}` — get link suggestions for a note
- `POST /api/v1/vault/organize` — get organization suggestions (dry run)
- `POST /api/v1/vault/organize/apply` — apply organization plan
- `POST /api/v1/vault/organize/undo` — undo last organization

**Agent:**
- `POST /api/v1/agent/client-response` — client responds to a `client_request` SSE event

**Web search:**
- `POST /api/v1/web/search` — search web via configured provider
- `POST /api/v1/web/fetch` — fetch and clean a URL via Jina Reader (nh3 sanitized)

**Memory:**
- `GET /api/v1/memories` — list user's memories (active only by default; `?archived=true` for archived)
- `POST /api/v1/memories` — create memory manually
- `PUT /api/v1/memories/{id}` — update memory content (re-embeds on save)
- `DELETE /api/v1/memories/{id}` — archive memory (soft delete)
- `DELETE /api/v1/memories/{id}/permanent` — hard-delete (requires `?confirm=true` param)
- `POST /api/v1/memories/{id}/restore` — restore archived memory to active
- `POST /api/v1/memories/search` — semantic search over memories
- `POST /api/v1/memories/import` — bulk import from JSON or markdown file
- `GET /api/v1/memories/export` — export all active memories as JSON
- `GET /api/v1/memories/dream/latest` — get latest Dream consolidation report
- `GET /api/v1/memories/dream/audit` — get Dream audit log
- `POST /api/v1/memories/dream/trigger` — manually trigger Dream cycle for self

**Projects:**
- `GET /api/v1/projects` — list projects
- `POST /api/v1/projects` — create project
- `PATCH /api/v1/projects/{id}` — update project
- `DELETE /api/v1/projects/{id}` — delete project

**Models:**
- `GET /api/v1/models` — list available LLM models (from config)
- `GET /api/v1/models/embedding` — list available embedding models

**User usage & status (all authenticated users):**
- `GET /api/v1/usage/summary` — user's own cost/token summary (30d, 7d, today)
- `GET /api/v1/usage/history` — user's own daily usage over time (for charts)
- `GET /api/v1/usage/recent` — user's last 20 LLM calls (purpose, model, cost, key_type)
- `GET /api/v1/usage/by-model` — user's own cost breakdown by model
- `GET /api/v1/status` — system status (public-safe subset of admin health)
- `GET /api/v1/status/providers` — which providers are available to this user (key status)

**Admin (require_admin):**
- `GET /api/v1/admin/overview` — dashboard overview (costs, storage, indexing, users)
- `GET /api/v1/admin/costs/by-provider` — cost breakdown by provider/model
- `GET /api/v1/admin/costs/by-user` — cost breakdown by user
- `GET /api/v1/admin/usage/history` — usage over time (for charts)
- `GET /api/v1/admin/health` — system health (PostgreSQL, disk, queue, watcher)
- `GET /api/v1/admin/users` — list users with stats
- `POST /api/v1/admin/users` — create user
- `DELETE /api/v1/admin/users/{id}` — delete user + all their data
- `POST /api/v1/admin/users/{id}/reset-password` — reset user password (returns temporary password)
- `POST /api/v1/admin/reindex` — force full reindex for a user/namespace
- `GET /api/v1/admin/index/status` — current indexing queue status
- `GET /api/v1/admin/api-keys` — list all shared API keys (hints only, never encrypted_key)
- `POST /api/v1/admin/api-keys` — add/update shared API key
- `DELETE /api/v1/admin/api-keys/{id}` — delete shared API key
- `POST /api/v1/admin/api-keys/{id}/test` — test a shared API key
- `GET /api/v1/admin/embeddings/estimate` — cost/time estimate for switching embedding model
- `POST /api/v1/admin/embeddings/migrate` — start embedding migration (new model + dimension)
- `GET /api/v1/admin/embeddings/status` — migration progress
- `POST /api/v1/admin/embeddings/cancel` — cancel in-progress migration
- `GET /api/v1/admin/dream/status` — Dream cycle status across all users
- `POST /api/v1/admin/dream/trigger/{user_id}` — trigger Dream for specific user

**User settings:**
- `GET /api/v1/settings` — get user's settings
- `PUT /api/v1/settings` — update user's settings
- `GET /api/v1/settings/modes` — get user's mode definitions
- `PUT /api/v1/settings/modes` — update mode definitions
- `GET /api/v1/settings/api-keys` — list user's own API keys (hints only)
- `POST /api/v1/settings/api-keys` — add/update user's own API key
- `DELETE /api/v1/settings/api-keys/{provider}` — delete user's own key for provider
- `POST /api/v1/settings/api-keys/{provider}/test` — test user's own key

**Health:**
- `GET /health` — backend health check (for Docker); returns `{"setup_required": true}` when no users exist

### SSE streaming format

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

---

## Docker Deployment

### Single container (recommended for homelab)

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

```ini
; supervisord.conf
[supervisord]
nodaemon=true
user=root

[program:postgresql]
command=/usr/lib/postgresql/16/bin/postgres -D /var/lib/postgresql/data -c config_file=/etc/postgresql/postgresql.conf
user=postgres
autostart=true
autorestart=true
priority=10
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:fastapi]
command=/app/scripts/wait-for-pg.sh
directory=/app
autostart=true
autorestart=true
priority=20
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
```

**wait-for-pg.sh** (polls PostgreSQL readiness before launching FastAPI + runs migrations):

```bash
#!/bin/bash
set -e

echo "Waiting for PostgreSQL to be ready..."
until pg_isready -h localhost -p 5432 -U postgres -q; do
  sleep 1
done
echo "PostgreSQL is ready. Running migrations..."

python3 -m alembic upgrade head

echo "Starting FastAPI..."
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

### Running the container

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

docker run -d \
  --name smart-copilot \
  -p 8000:8000 \
  -v smart-copilot-data:/var/lib/postgresql/data \
  -v /path/to/your/vaults:/vaults \
  -e ENCRYPTION_KEY=your-generated-key \
  smart-copilot:latest
```

### External PostgreSQL mode

```bash
docker run -d \
  --name smart-copilot \
  -p 8000:8000 \
  -v /path/to/your/vaults:/vaults \
  -e EXTERNAL_DB=true \
  -e DATABASE_URL=postgresql+asyncpg://copilot:password@your-pg-host:5432/copilot \
  -e ENCRYPTION_KEY=your-generated-key \
  smart-copilot:latest
```

When `EXTERNAL_DB=true`, supervisord skips starting the internal PostgreSQL process. pgvector extension must be installed on the external PostgreSQL instance.

---

## Backup Strategy

A complete Smart Copilot backup requires three components:

| Component | Contains | Location | Method |
|---|---|---|---|
| PostgreSQL database | All indexed data, conversations, memories, API keys (encrypted), usage logs, user accounts | Docker volume `smart-copilot-data` | pg_dump or volume snapshot |
| Vault files | User markdown files, the actual knowledge base | Host mount `/path/to/your/vaults` | rsync / Syncthing / filesystem backup |
| Encryption key | Decrypts all stored API keys | `ENCRYPTION_KEY` env var | Stored separately in a password manager or key escrow |

### Automated backup script (recommended for homelab)

```bash
#!/bin/bash
# smart-copilot-backup.sh — run via cron daily
set -euo pipefail

BACKUP_DIR="/backups/smart-copilot/$(date +%Y-%m-%d)"
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

# 1. Database backup (pg_dump inside the container)
echo "Backing up database..."
docker exec smart-copilot pg_dump -U postgres -Fc copilot \
  > "$BACKUP_DIR/database.dump"

# 2. Vault files backup (rsync for incremental efficiency)
echo "Backing up vault files..."
rsync -a --delete /path/to/your/vaults/ "$BACKUP_DIR/vaults/"

# 3. Server config backup
echo "Backing up configuration..."
docker cp smart-copilot:/config/settings.yaml "$BACKUP_DIR/settings.yaml"

# 4. Verify backup integrity
echo "Verifying database backup..."
pg_restore --list "$BACKUP_DIR/database.dump" > /dev/null 2>&1 \
  && echo "Database backup verified." \
  || echo "WARNING: Database backup may be corrupt!"

# 5. Clean old backups
find /backups/smart-copilot/ -maxdepth 1 -type d -mtime +$RETENTION_DAYS -exec rm -rf {} \;

# 6. Write status file for admin dashboard
docker exec smart-copilot sh -c \
  "echo '{\"last_backup\":\"$(date -Iseconds)\",\"backup_dir\":\"$BACKUP_DIR\"}' > /config/backup-status.json"

echo "Backup complete: $BACKUP_DIR"
```

**Cron entry:**
```
0 3 * * * /opt/smart-copilot/smart-copilot-backup.sh >> /var/log/smart-copilot-backup.log 2>&1
```

### Restore procedure

```bash
# 1. Stop the running container
docker stop smart-copilot

# 2. Restore database
docker run --rm \
  -v smart-copilot-data:/var/lib/postgresql/data \
  -v /backups/smart-copilot/2025-02-14:/backup \
  pgvector/pgvector:pg16 \
  pg_restore -U postgres -d copilot -c /backup/database.dump

# 3. Restore vault files
rsync -a /backups/smart-copilot/2025-02-14/vaults/ /path/to/your/vaults/

# 4. Restore config (if needed)
cp /backups/smart-copilot/2025-02-14/settings.yaml /path/to/config/settings.yaml

# 5. Start container (same ENCRYPTION_KEY — required!)
docker start smart-copilot
```

**CLI commands:**
```
smart-copilot backup --output /path/to/backup/    # runs pg_dump + rsync
smart-copilot restore --from /path/to/backup/      # runs pg_restore + rsync
```

**Critical: encryption key backup.** If the `ENCRYPTION_KEY` is lost, all stored API keys become unrecoverable. Store it in a password manager, a sealed envelope in a safe, or a dedicated secrets manager. The backup script deliberately does NOT include the encryption key — it should be stored separately from the data it protects.

**What's NOT backed up (and why):** HNSW indexes are rebuilt automatically from data on restore. The Docker image is pulled from registry. `settings.yaml` should be version-controlled or backed up with the script above.

**For NAS/Syncthing users:** If vaults are already synced via Syncthing or stored on a NAS with its own backup (snapshots, RAID), the vault rsync step can be skipped — only the database dump is needed.

---

## Backend Settings (server-side config)

File: `/config/settings.yaml`. Only non-secret configuration lives here — API keys are in the database.

```yaml
server:
  host: 0.0.0.0
  port: 8000
  log_level: info
  cors_origins:
    - "http://localhost:*"
    - "app://."

vault:
  base_path: /vaults
  watch_debounce_ms: 300
  reconciliation_interval_hours: 6

rag:
  hybrid_weights:
    vector: 0.5
    bm25: 0.3
    wikilink: 0.2
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
    - id: openai/gpt-4o
      display_name: GPT-4o
      capabilities: [chat, vision]
    - id: openai/gpt-4o-mini
      display_name: GPT-4o Mini
      capabilities: [chat]
    - id: anthropic/claude-sonnet-4-20250514
      display_name: Claude Sonnet 4
      capabilities: [chat]
    - id: anthropic/claude-haiku-4-5-20251001
      display_name: Claude Haiku 4.5
      capabilities: [chat]
    - id: gemini/gemini-2.5-pro
      display_name: Gemini 2.5 Pro
      capabilities: [chat, vision]
    - id: ollama/qwen3:8b
      display_name: Qwen3 8B (local)
      capabilities: [chat]
  embedding_models:
    - id: openai/text-embedding-3-small
      display_name: OpenAI Embedding Small
      dimensions: 1536
    - id: openai/text-embedding-3-large
      display_name: OpenAI Embedding Large
      dimensions: 3072
    - id: ollama/nomic-embed-text
      display_name: Nomic Embed (local)
      dimensions: 768
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
  link_suggestions:
    min_confidence: 0.7
    max_suggestions: 10
  id_format:
    use_timestamp: true
    separator: ""

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
  # Storage is always database (memories PostgreSQL table). No vault-notes option.
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

**Server-only vs user-overridable settings:** The following `settings.yaml` keys are server-wide and cannot be overridden per-user via `user_settings`: `server.*`, `vault.*`, `rag.embedding_model`, `rag.embedding_dimensions`, `llm.local_endpoints`, `llm.dream_model`, `auth.*`, `memory.dream.*`, `chat_history.max_conversations_per_user`. All other settings (RAG weights, top_k, temperature, zettelkasten preferences, agent confirmations, mode definitions, etc.) can be overridden per-user via the `user_settings` JSONB table. The `settings.yaml` values serve as defaults for new users. Settings tabs (4a–4i) show the effective value: user override if set, server default otherwise.

---

## Backend File Structure

```
server/
├── Dockerfile
├── supervisord.conf
├── requirements.txt
├── pyproject.toml
├── alembic.ini
├── alembic/
│   └── versions/
│
├── scripts/
│   └── wait-for-pg.sh              # polls pg_isready, runs alembic, launches uvicorn
│
├── app/
│   ├── main.py                      # FastAPI app, startup validation (embedding dimension check)
│   ├── config.py                    # Pydantic settings from YAML + env vars
│   ├── dependencies.py              # get_db_session (SET/RESET RLS), get_db (FastAPI DB dependency)
│   ├── encryption.py                # Fernet encrypt/decrypt for api_keys table
│   │
│   ├── api/
│   │   ├── auth.py                  # register, login, refresh, change-password
│   │   ├── chat.py                  # SSE streaming chat with RAG
│   │   ├── conversations.py         # CRUD
│   │   ├── search.py                # hybrid, semantic, keyword
│   │   ├── documents.py             # list, get, upload, import
│   │   ├── vault.py                 # write, move, split, organize, undo
│   │   ├── agent.py                 # client-response endpoint for client-cooperative tools
│   │   ├── web_search.py            # search, fetch URL
│   │   ├── memories.py              # CRUD + semantic search + dream endpoints
│   │   ├── projects.py              # CRUD
│   │   ├── models.py                # list LLM + embedding models
│   │   ├── usage.py                 # user-scoped usage/cost endpoints
│   │   ├── status.py                # public-safe system status for all users
│   │   ├── settings.py              # user settings + modes + user api keys
│   │   ├── admin.py                 # dashboard, health, users, shared api keys, dream, embeddings
│   │   └── health.py                # health check (includes setup_required flag)
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── api_key.py
│   │   ├── document.py
│   │   ├── chunk.py
│   │   ├── wikilink.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   ├── memory.py
│   │   ├── dream_audit_log.py
│   │   ├── project.py
│   │   ├── operation_log.py
│   │   ├── llm_usage.py
│   │   ├── index_event.py
│   │   ├── system_health.py
│   │   ├── system_config.py
│   │   └── user_settings.py
│   │
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── chat.py
│   │   ├── search.py
│   │   ├── document.py
│   │   ├── conversation.py
│   │   ├── vault.py
│   │   ├── memory.py
│   │   ├── project.py
│   │   ├── usage.py
│   │   ├── status.py
│   │   ├── models.py
│   │   ├── health.py
│   │   ├── admin.py
│   │   ├── settings.py
│   │   └── common.py
│   │
│   ├── rag/
│   │   ├── engine.py                # HybridRAGEngine
│   │   ├── context_enricher.py
│   │   ├── note_type.py
│   │   ├── embedder.py              # LiteLLM aembedding() wrapper with batching
│   │   ├── chunker.py
│   │   └── queries.py               # SQL queries for hybrid search + RRF
│   │
│   ├── vault/
│   │   ├── registry.py              # VaultRegistry: path prefix → (user_id, namespace) mapping
│   │   ├── watcher.py               # watchdog file watcher, calls registry.resolve()
│   │   ├── parser.py
│   │   ├── indexer.py               # IndexQueue: enrich → embed → upsert; enrichment_hash cascade
│   │   ├── link_graph.py
│   │   ├── link_refactorer.py
│   │   ├── operation_log.py
│   │   └── reconciler.py
│   │
│   ├── agent/
│   │   ├── runner.py
│   │   ├── tools.py
│   │   └── scheduler.py
│   │
│   ├── llm/
│   │   ├── gateway.py
│   │   ├── key_resolver.py          # resolve: user key → shared key → error + track key_type
│   │   ├── callbacks.py             # LiteLLM callbacks: cost tracking with key_type
│   │   └── prompts.py
│   │
│   ├── memory/
│   │   ├── manager.py
│   │   ├── extractor.py
│   │   ├── importer.py              # bulk import from JSON/markdown with duplicate detection
│   │   ├── exporter.py              # export active memories as JSON
│   │   └── dream.py                 # 4-phase consolidation with advisory lock
│   │
│   ├── websearch/
│   │   ├── engine.py
│   │   ├── duckduckgo.py
│   │   ├── jina_reader.py
│   │   ├── wikipedia.py
│   │   ├── tavily.py
│   │   ├── brave.py
│   │   └── cross_ref.py
│   │
│   ├── zettelkasten/
│   │   ├── splitter.py
│   │   ├── builder.py
│   │   ├── organizer.py
│   │   ├── moc_generator.py
│   │   └── orphan_detector.py
│   │
│   ├── documents/
│   │   ├── processor.py
│   │   ├── pdf.py
│   │   ├── docx.py
│   │   └── html.py                  # nh3 sanitize → readability-lxml → markdown
│   │
│   ├── capture/
│   │   ├── manager.py
│   │   └── web_clipper.py
│   │
│   ├── sanitizer/
│   │   └── html_sanitizer.py        # nh3 Cleaner configuration for defense-in-depth
│   │
│   └── auth/
│       ├── jwt.py
│       ├── password.py
│       └── middleware.py             # get_current_user + require_admin dependencies
```

---

## Electron Client File Structure

```
client/
├── forge.config.ts
├── vite.config.ts
├── package.json
├── tsconfig.json
│
├── src/
│   ├── main/
│   │   ├── main.ts
│   │   ├── tray.ts
│   │   ├── windows.ts
│   │   ├── global-shortcut.ts
│   │   ├── auto-launch.ts
│   │   └── ipc.ts
│   │
│   ├── renderer/
│   │   ├── index.html
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   │
│   │   ├── api/
│   │   │   ├── client.ts
│   │   │   ├── generated/
│   │   │   └── sse.ts                # includes client_request event handler
│   │   │
│   │   ├── views/
│   │   │   ├── ChatView.tsx
│   │   │   ├── SettingsView.tsx
│   │   │   ├── AdminView.tsx
│   │   │   ├── LoginView.tsx
│   │   │   ├── DashboardView.tsx      # User Dashboard (Page 6a)
│   │   │   └── PasswordChangeView.tsx # forced password change after admin reset
│   │   │
│   │   ├── components/
│   │   │   ├── chat/
│   │   │   ├── editor/
│   │   │   ├── floating/
│   │   │   ├── intelligence/
│   │   │   ├── admin/
│   │   │   ├── dashboard/             # User Dashboard tab components
│   │   │   │   ├── MyUsageTab.tsx
│   │   │   │   ├── VaultHealthTab.tsx
│   │   │   │   └── SystemStatusTab.tsx
│   │   │   ├── memory/                # Memory management components (Tab 4i)
│   │   │   │   ├── MemoryList.tsx     # searchable/sortable table with inline edit
│   │   │   │   ├── MemoryImport.tsx   # upload JSON/markdown, duplicate detection UI
│   │   │   │   └── MemoryDreamStatus.tsx
│   │   │   └── shared/
│   │   │
│   │   ├── modals/
│   │   ├── contexts/
│   │   ├── hooks/
│   │   │
│   │   ├── utils/
│   │   │   ├── sanitizer.ts           # DOMPurify configuration for clipboard HTML
│   │   │   └── clipboard.ts           # ClipboardHandler: read, detect type, normalize, sanitize
│   │   │
│   │   └── styles/
│   │
│   ├── quickchat/
│   │   ├── index.html
│   │   ├── quickchat.tsx
│   │   └── QuickChatView.tsx
│   │
│   └── shared/
│       ├── types.ts
│       └── constants.ts
```

---

## UI Pages & Components Inventory

### Page 1 — Login / Connection Setup

| Element | Type | Notes |
|---|---|---|
| Server URL | text input | Default: `http://localhost:8000`. Saved in Electron local storage |
| Connection test button | button | Tests `GET /health` before proceeding |
| Connection status indicator | badge | green/red/yellow |
| Username | text input | |
| Password | password input | |
| Login button | button | `POST /api/v1/auth/login` |
| "Remember me" | checkbox | Persists refresh token |
| First-run: Create admin account | form section | Shown when `/health` returns `setup_required: true` |
| — Admin username | text input | |
| — Admin email | text input | Optional |
| — Admin password | password input | With confirmation field |
| — Create Account button | button | `POST /api/v1/auth/register` |
| Forced password change | dialog | Shown when `must_change_password: true` after login |

---

### Page 2 — Main Chat View (split-pane)

_(Unchanged from v0.1.0 — see original blueprint for full specification of chat panel, editor panel, header row, assistive tools, floating surfaces, and status bar.)_

**Status bar addition — migration indicator:**

During an embedding migration:
```
2,347 notes · ⟳ Re-embedding: 67% complete · Connected ✅
```

**Model picker addition — personal key indicator:**

When user has their own key for the active model's provider:
```
● GPT-4o 🔑        ← personal key active
○ GPT-4o mini      ← shared key
```

---

### Page 3 — Floating Surfaces

_(Unchanged from v0.1.0 — see original blueprint for Chat History, Mode Picker, Model Picker, Chat Settings, More Options.)_

---

### Page 4 — Settings

Tab bar:
```
[ ⚙ General ]  [ Model ]  [ RAG ]  [ Modes ]  [ Features ]  [ API Keys ]  [ Advanced ]  [ Account ]  [ Memory ]
```

#### Tab 4a — General
_(Unchanged from v0.1.0)_

#### Tab 4b — Models
_(Unchanged from v0.1.0)_

#### Tab 4c — RAG

| Setting | Type | Default | Notes |
|---|---|---|---|
| Current Embedding Model | text (read-only) | from server | "openai/text-embedding-3-small (1536 dim)" — admin changes this in Admin Dashboard |
| Contextual Enrichment | toggle | on | |
| Top K results | number | 10 | |
| Vector weight | slider | 0.5 | Weights must sum to 1.0 |
| BM25 weight | slider | 0.3 | |
| Wikilink weight | slider | 0.2 | |
| Fleeting note expiry | number | 30 days | |
| Infer type from folder | toggle | on | |
| Fleeting folders | text list | /inbox/, /fleeting/ | |
| Project folders | text list | /projects/, /journal/ | |

#### Tab 4d — Modes
_(Unchanged from v0.1.0)_

#### Tab 4e — Features
_(Unchanged from v0.1.0)_

#### Tab 4f — API Keys (user's own)

| Element | Type | Notes |
|---|---|---|
| Info text | text | "Optionally provide your own API keys. If not set, shared keys configured by your admin will be used. Your key takes priority when set." |
| Provider list | rows | One row per provider: OpenAI, Anthropic, Gemini, DeepSeek, OpenRouter |
| — Provider row | row | Provider name · Key hint or "Not set" · Status ("Using your key ✅" / "Using shared key" / "No key ❌") · [Set Key] [Test] [Remove] |
| — Set Key dialog | modal | Password input + Save button |
| Local LLM info | text (read-only) | "Local LLM endpoints (Ollama, LM Studio) are configured by your admin." — lists available local endpoints if any are configured |

#### Tab 4g — Advanced
_(Unchanged from v0.1.0)_

#### Tab 4h — Account (new)

| Setting | Type | Notes |
|---|---|---|
| Username | text (read-only) | |
| Email | text input | User can update their own email |
| Change Password | button | Opens dialog: current password + new password + confirm |
| Role | text (read-only) | "Admin" or "User" |
| Account created | text (read-only) | Date |

#### Tab 4i — Memory (new)

| Element | Type | Notes |
|---|---|---|
| Active Memories | metric | "142 / 500 active memories" |
| Memory Dream status | card | Last run, sessions since, next estimate. "Run Dream now" button |
| **Memory list** | searchable table | Columns: Content (truncated), Source (conversation link), Created, Last Recalled, Recall Count |
| — Search | text input | Filters by content text |
| — Sort | dropdown | By: newest, oldest, most recalled, least recalled |
| — Edit | row action | Opens inline editor — user can rewrite memory content. Re-embeds on save |
| — Archive | row action | Soft-delete (`is_archived = true`). Can be restored from Archived tab |
| — Delete permanently | row action | Hard-delete with confirmation. "This cannot be undone." |
| **Archived memories** | expandable section | Same table structure, with "Restore" action instead of "Archive" |
| **Bulk actions** | toolbar | Select multiple → Archive / Delete / Export |
| **Add memory** | button | Opens dialog: content text area + optional source note reference. Creates + embeds |
| **Import memories** | button | Upload JSON or markdown file. Markdown: one memory per line (lines starting with `- ` have prefix stripped). JSON: array of `{content, created_at?}` objects. Each imported memory is embedded immediately |
| **Export memories** | button | Downloads all active memories as JSON: `[{content, created_at, recall_count, source_conversation_id}]`. Can be re-imported on another instance |

**Import validation:**
- Maximum 500 memories per import (matches `max_memories_per_user`)
- If import would exceed limit, show warning: "You have 142 active memories. Importing 400 would exceed your limit of 500. Import the first 358?" with options: Import partial / Cancel / Archive oldest to make room
- Duplicate detection: if imported memory content is >95% similar (cosine similarity) to an existing active memory, flag it: Skip / Import anyway / Replace existing

---

### Page 5 — Admin Dashboard (admin only)

Tab bar:
```
[ Overview ]  [ LLM Usage ]  [ Storage ]  [ API Keys ]  [ Users ]  [ Memory Dream ]  [ System ]
```

#### Tab 5a–5b — Overview, LLM Usage
_(Unchanged from v0.1.0)_

#### Tab 5c — Storage & Indexing

_(Existing content unchanged, plus new embedding section:)_

| Element | Type | Notes |
|---|---|---|
| Current Embedding Model | display | Model name + dimensions + chunk count |
| Change Embedding Model | dropdown + button | Triggers estimate → confirmation → migration |
| Migration progress | progress bar + text | Only shown during active migration |
| Cancel Migration | button | Only shown during active migration |
| _(existing storage/indexing elements)_ | | |

#### Tab 5d — API Keys (shared)
_(Unchanged from v0.1.0)_

#### Tab 5e — Users (expanded)

| Element | Type | Notes |
|---|---|---|
| User list | table | Username, Email, Role, Documents, Cost (30d), Last Active, Created |
| — Edit user | row action | Change role (admin ↔ user), update email |
| — Reset Password | row action | Generates temporary password shown once in dialog; sets `must_change_password: true` |
| — Delete user | row action | Requires typed confirmation of username. Deletes user + all DB records. Vault files on disk NOT deleted. |
| + Add User | button | Dialog: username (required), email (optional), temporary password (auto-generated, shown once), role (default: user) |

#### Tab 5f — Memory Dream
_(Unchanged from v0.1.0)_

#### Tab 5g — System Health

| Element | Type | Notes |
|---|---|---|
| Backend uptime | metric | |
| PostgreSQL connections | metric | active / max |
| PostgreSQL disk usage | metric + bar | |
| Health history | line chart | DB size, chunk count, connections over time (from `system_health` table, recorded every 15 minutes by APScheduler) |
| Vault path | text (read-only) | |
| Watcher status | indicator | Active / Paused / Error |
| Last backup | text | "Database: 2025-02-14 03:00 · Vault: synced via Syncthing" — read from `/config/backup-status.json` written by the automated backup script. `GET /api/v1/admin/health` reads this file if present |
| Backup reminder | warning card | Shown if `/config/backup-status.json` is missing or `last_backup` is older than 7 days: "No recent backup detected. See documentation for setup." |

---

### Page 6a — User Dashboard (all users)

Accessible from ⋯ panel options → "Dashboard" or Hub Home Screen "AI Insights" card.

Tab bar:
```
[ 📊 My Usage ]  [ 🏥 Vault Health ]  [ 🖥️ System Status ]
```

#### Tab 6a-1 — My Usage

| Element | Type | Notes |
|---|---|---|
| My Cost (30 days) | metric card | Total across all models |
| — Shared key cost | sub-metric | "Using team API keys" |
| — Personal key cost | sub-metric | "Using your own API keys" — only shown if user has personal keys |
| Cost trend | sparkline chart | Daily cost over 30 days |
| Cost by Model | horizontal bar chart | Grouped by model |
| Calls today | metric card | Count for current day |
| Token usage (30 days) | metric card | Sum of prompt + completion tokens |
| Recent Activity | compact table | Last 20 LLM calls: Time, Model, Purpose, Tokens, Cost, Key type |
| Memory Dream status | card | Last run, sessions since, next estimate |

#### Tab 6a-2 — Vault Health

| Element | Type | Notes |
|---|---|---|
| Vault Health Score | metric card | Composite: orphan %, link density, type coverage |
| Orphan Notes | metric + list | Action: suggest links / archive |
| Hub Notes | metric + list | Most-connected notes |
| Note Type Distribution | pie/bar chart | permanent / literature / fleeting / project / structure |
| Recent Indexing Activity | event list | User's namespace only |
| Link Suggestions | list with actions | One-click accept |
| Graph Visualization | Cytoscape panel | Click node → open in editor |

#### Tab 6a-3 — System Status

| Element | Type | Notes |
|---|---|---|
| Server Status | badge | Connected / Degraded / Offline |
| Backend Version | text | |
| PostgreSQL Status | badge | |
| Index Status | text + progress | User's namespace only |
| Embedding Model | text (read-only) | Current model + dimensions. No change button |
| Available LLM Providers | list | Provider name + status (key valid / expired / no key). No key values shown |
| API Key Status (personal) | per-provider rows | "OpenAI: using your key ✅" / "Anthropic: using shared key" / "Gemini: no key ❌" |
| Disk Usage | text | User's own storage footprint |

---

### Page 7 — Quick Chat Window (tray)
_(Unchanged from v0.1.0)_

### Page 8 — Modals
_(Unchanged from v0.1.0)_

### System Tray Menu
_(Unchanged from v0.1.0)_

---

### Navigation structure by role

```
Standard user sees:
  ⋯ Panel Options → Dashboard (Page 6a — My Usage / Vault Health / System Status)
  ⋯ Panel Options → Settings (Page 4 — all tabs including Account)

Admin user sees:
  ⋯ Panel Options → Dashboard (Page 6a — same as standard user, for own data)
  ⋯ Panel Options → Admin (Page 5 — full admin dashboard, all tabs)
  ⋯ Panel Options → Settings (Page 4 — same tabs)
```

---

## Implementation Phases

The backend and frontend develop in parallel against the OpenAPI spec. The backend is the critical path — the frontend can use mock data until endpoints are live.

### Phase 1 — Foundation (Weeks 1–2)

**Backend:** Docker container with supervisord + wait-for-pg.sh, Alembic migrations for full schema (including system_config, enrichment_hash), auth system (JWT, register, login, password change, require_admin, must_change_password), user management CRUD + password reset, VaultRegistry + file watcher (watchdog) + IndexQueue, markdown parser (frontmatter + wikilink extraction), NoteTypeClassifier.

**Frontend:** Electron shell with Forge + Vite, Login/connection setup page (Page 1) with first-run admin creation, API client generated from OpenAPI spec, auth flow (JWT safeStorage, refresh, forced password change).

**Quality gate:** Container starts, user can register, login, watcher detects file changes in a mounted vault.

### Phase 2 — RAG + Chat (Weeks 3–4)

**Backend:** ContextEnricher, Chunker, Embedder (LiteLLM aembedding with batching), HybridRAGEngine (vector + BM25 + wikilink CTE, single query), bulk initial indexing with progress, LiteLLM gateway + key resolver (user → shared → error) with key_type tracking, `POST /api/v1/chat/completions` with SSE streaming (ChatCompletionRequest schema), chat history CRUD, enrichment_hash + cascade re-embedding, nh3 sanitizer, user settings CRUD (`GET/PUT /api/v1/settings`, `GET/PUT /api/v1/settings/modes`), `GET /api/v1/models` endpoint.

**Frontend:** Chat panel with Lexical input + @mentions, SSE client for streaming (including client_request handler), message list with citation badges, chat history popover, model picker (grouped by provider, 🔑 indicator), mode picker with pill system, DOMPurify clipboard sanitizer.

**Quality gate:** User can chat with RAG context, see citations, switch models. Hybrid search returns weighted results.

### Phase 3 — Editor + Zettelkasten (Weeks 5–6)

**Backend:** NoteSplitter (H1/H2/H3 boundaries), ZettelNoteBuilder, document import (PDF via PyMuPDF, DOCX via python-docx, HTML via nh3 + readability-lxml), web clipper (Jina Reader + nh3), vault write/move/split endpoints, LinkRefactorer, OperationLog.

**Frontend:** Tiptap split-pane editor, react-resizable-panels, NoteSplitterModal, ZettelNotePreviewModal, file reference modal, Chat Settings popover + More Options drawer.

**Quality gate:** User can import a PDF, split into Zettel notes, edit in Tiptap. Write mode scopes RAG to the open file via `current_note_path`.

### Phase 4 — Agent + Memory (Weeks 7–8)

**Backend:** AgentRunner (plan-execute-observe, 22 tools), confirmation gate, client-cooperative tool protocol (captureFromClipboard with SSE round-trip), memory extraction/storage/recall, Memory Dream consolidation (4 phases, advisory lock), APScheduler, memory import/export endpoints.

**Frontend:** Agent tool banner, memory panel, confirmation modals, SSE client_request handler (clipboard normalization + POST back), Research mode wiring, Memory management tab (Tab 4i) with edit/archive/delete/import/export.

**Quality gate:** Agent completes a multi-tool Research query. Memory persists across sessions. Dream runs and consolidation report accessible. Memory import/export round-trips correctly.

### Phase 5 — Web Search + Projects (Weeks 9–10)

**Backend:** Web search engine (DuckDuckGo, Jina, Wikipedia free; Tavily/Brave/SerpAPI paid), CrossReferenceEngine, ProjectManager (folder/tag scoping), frontmatterQuery tool.

**Frontend:** Project switcher, project creation/edit modal, web search toggle, @web trigger, Focus mode scoping.

**Quality gate:** Projects scope RAG correctly. Web search returns results and cross-references vault.

### Phase 6 — Intelligence + Admin (Weeks 11–12)

**Backend:** Orphan detection, link suggestions, bidirectional gap detection, SmartOrganizer, MOC generator, vault health endpoints (`GET /api/v1/vault/health`, `/vault/hubs`, `/vault/graph`, `/vault/index/events`), admin endpoints (overview, usage, costs, health, dream status), user-scoped usage/status endpoints, embedding migration pipeline (estimate, migrate, cancel, status), regenerate endpoint.

**Frontend:** Vault Health dashboard (Tab 6a-2), User Dashboard — My Usage (Tab 6a-1) and System Status (Tab 6a-3), Admin Dashboard (all tabs, admin-only), graph visualization (Cytoscape, lazy-loaded), OrganizePreviewModal, LinkSuggestionModal, embedding migration UI.

**Quality gate:** Admin dashboard shows real usage data. User dashboard shows personal costs with shared/personal key breakdown. Embedding migration completes end-to-end.

### Phase 7 — Platform + Polish (Weeks 13–14)

**Backend + Frontend:** System tray agent, Quick Chat window, global hotkey (Cmd+Shift+Space), auto-launch on login, electron-updater, command palette (cmdk), diff modal, vault export (`POST /api/v1/conversations/{id}/export`), image understanding (vision models), settings UI polish (all tabs including Account and Memory), user API key management with provider status.

**Quality gate:** Full feature parity with blueprint. Tray agent works on macOS and Windows.

### Phase 8 — Beta + Launch (Weeks 15–16)

- 10+ beta users across macOS and Windows
- Performance targets: chat response start < 500ms, RAG search < 300ms, bulk index 1000 notes < 5 minutes
- Docker image published to GitHub Container Registry
- Backup script and restore procedure tested end-to-end
- README with screenshots, quick start guide
- Docker Compose example for advanced deployments (external PostgreSQL, Caddy reverse proxy)

---

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Single container: PostgreSQL crash takes down API | Medium | supervisord auto-restarts. wait-for-pg.sh ensures clean startup ordering. External DB mode for critical deployments |
| pgvector HNSW index recall degrades at 100K+ chunks | Medium | Monitor recall metrics. Per-user schemas if needed at scale |
| File watcher misses events during Syncthing sync | Medium | Periodic reconciliation every 6 hours. Content hash dedup |
| LiteLLM library update breaks provider compatibility | Medium | Pin LiteLLM version. Test provider calls in CI |
| Tiptap markdown round-trip loses frontmatter or wikilinks | High | Test on Day 1 of editor phase. Store frontmatter separately if needed |
| Agent writes to vault while user editing same file | High | Debounce watcher, detect external changes, show conflict dialog |
| SSE connections drop behind reverse proxy | Medium | Auto-reconnect in client. Caddy `flush_interval -1` if proxied |
| Embedding model change requires hours-long re-embed | Medium | Progress tracking via admin dashboard. Old embeddings remain searchable. Cancellation + crash recovery supported |
| Memory Dream deletes memories user wanted to keep | Medium | All actions logged to audit table. Archived, never hard-deleted. User can review and restore via Tab 4i |
| Encryption key lost → all API keys unrecoverable | High | Document backup procedure prominently. Key rotation via MultiFernet planned for future |
| Users expect Obsidian-quality editor | Low | Clear messaging: "Use Obsidian for advanced editing" |
| captureFromClipboard timeout when client minimized | Low | 10-second timeout, clear error message, suggest pasting into chat instead |
| RLS context leak across pooled connections | High | get_db_session always RESET on return. Code review gate: every DB route must use Depends(get_db) |
| Enrichment cascade re-embeds too many notes on bulk rename | Medium | Cascade limited to 1 hop. Bulk operations debounce cascades |
| Memory import exceeds user limit | Low | Client-side validation with partial import option |

---

## Glossary

| Term | Definition |
|---|---|
| Namespace | `private` (per-user) or `shared` (team knowledge) — controls RLS visibility |
| Contextual enrichment | Prepending metadata (title, folder, tags, wikilinks) before embedding |
| Hybrid RAG | Vector + BM25 + wikilink graph, combined via Reciprocal Rank Fusion |
| RRF | Reciprocal Rank Fusion — `score = Σ 1/(k + rank)` across retrieval signals |
| RLS | Row-Level Security — PostgreSQL feature enforcing per-user data isolation |
| Mode | Named system-prompt bundle that controls RAG scope, web search, and agent tools |
| Citation markers | `[1]`, `[2]` in LLM output mapped to source documents |
| OperationLog | JSON record of multi-step file operations enabling undo |
| Memory Dream | Nightly 4-phase consolidation cycle that prunes, merges, and timestamps memories |
| Fleeting note | Temporary note that expires from the index after N days |
| Literature note | Summary of an external source, used as citation reference |
| Permanent note | Atomic idea note — the core unit of a Zettelkasten |
| Fernet | Symmetric encryption scheme from Python's `cryptography` library |
| DOMPurify | Client-side HTML sanitizer using browser's native DOM parser (Electron) |
| nh3 | Server-side HTML sanitizer — Rust/Ammonia binding for Python (defense-in-depth) |
| Client-cooperative tool | Agent tool requiring data from Electron client via SSE request-response |
| key_type | Whether an LLM call used a `shared` (admin) or `personal` (user) API key |
| VaultRegistry | In-memory mapping from filesystem path prefix to `(user_id, namespace)` — resolves file ownership for the watcher |
| enrichment_hash | Hash of a document's enrichment inputs (title, folder, tags, backlinks, outlinks) — triggers re-embed when wikilinks change even if content doesn't |
| Advisory lock | PostgreSQL `pg_try_advisory_lock()` used to prevent concurrent Dream runs |
| safeStorage | Electron API for OS-encrypted storage (macOS Keychain, Windows DPAPI) — used for JWT tokens |
| SYSTEM_USER_ID | UUID constant representing the owner of shared namespace content — never logs in |
