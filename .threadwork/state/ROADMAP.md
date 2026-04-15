# Smart Copilot — Roadmap

## Milestone 1: Foundation & Core Intelligence
> Docker, auth, schema, file watcher, hybrid RAG, streaming chat, citations

### Phase 1 — Foundation (Weeks 1–2)
**Backend:** Docker container (supervisord + wait-for-pg.sh), Alembic migrations (full schema including system_config, enrichment_hash, sessions), auth system (JWT, register, login, password change, require_admin, must_change_password), user management CRUD + password reset, VaultRegistry + file watcher (watchdog) + IndexQueue, markdown parser (frontmatter + wikilink extraction), NoteTypeClassifier, Workspace CRUD (UI-only, RAG scoping Phase 5), indexing progress endpoint.

**Frontend:** Electron shell (Forge + Vite), Login/connection setup with first-run admin creation, API client generated from OpenAPI spec, auth flow (JWT safeStorage, refresh, forced password change).

**Features:** F-DOCKER-01, F-SCHEMA-01, F-AUTH-01, F-AUTH-02, F-IDX-01, F-IDX-02

**Quality gates:**
- `docker run` → `GET /health` 200 within 30s
- Register → login → JWT → authenticated request succeeds
- Create .md → watcher event logged

### Phase 2 — RAG + Chat (Weeks 3–4)
**Backend:** ContextEnricher, Chunker, Embedder (LiteLLM aembedding with batching), HybridRAGEngine (vector + BM25 + wikilink CTE, single query), bulk initial indexing with progress, LiteLLM gateway + key resolver with key_type tracking, `POST /api/v1/chat/completions` with SSE streaming, chat history CRUD, enrichment_hash + cascade re-embedding, nh3 sanitizer, user settings CRUD, `GET /api/v1/models`.

**Frontend:** Chat panel with Lexical input + @mentions, SSE client for streaming, message list with citation badges, chat history popover, model picker, mode picker with pill system, DOMPurify clipboard sanitizer.

**Features:** F-RAG-01, F-RAG-02, F-CHAT-01, F-CHAT-02, F-LLM-01, F-CHAT-03, F-CHAT-04, F-CHAT-06, F-SETTINGS-01

**Quality gates:**
- Message → hybrid search → citations in response
- Change model → new model used for next message

---

## Milestone 2: Editor, Zettelkasten & Agent
> Split-pane editor, note splitting, document import, 22-tool agent, memory system

### Phase 3 — Editor + Zettelkasten (Weeks 5–6)
**Backend:** NoteSplitter, ZettelNoteBuilder, document import (PDF/DOCX/HTML), web clipper (Jina Reader + nh3), vault write/move/split endpoints, LinkRefactorer, OperationLog.

**Frontend:** Collapsible vault sidebar (tree view + list view, react-complex-tree), Tiptap split-pane editor, react-resizable-panels, NoteSplitterModal, ZettelNotePreviewModal, Chat Settings popover + More Options drawer.

**Features:** F-EDITOR-01, F-ZETT-01, F-ZETT-02, F-ZETT-03

**Quality gates:**
- Upload PDF → extract → split → atomic notes with backlinks
- Click citation → Tiptap opens with note
- Browse vault in sidebar, open note in editor, tree reflects vault structure

### Phase 4 — Agent + Memory (Weeks 7–8)
**Backend:** AgentRunner (plan-execute-observe, 22 tools), confirmation gate, client-cooperative tool protocol (captureFromClipboard with SSE round-trip), memory extraction/storage/recall, Memory Dream consolidation (4 phases, advisory lock), APScheduler, skill resolution engine.

**Frontend:** Agent tool banner, memory panel, confirmation modals, SSE client_request handler, Research mode wiring, Memory management, Skills management.

**Features:** F-AGENT-01, F-AGENT-02, F-AGENT-03, F-AGENT-04, F-AGENT-05, F-MEM-01, F-MEM-02, F-MEM-03

**Quality gates:**
- Research mode → agent uses ragSearch + webSearch + vaultWrite
- Fact in chat → memoryRecall finds it in new conversation
- Trigger Dream → consolidation report shows actions

---

## Milestone 3: Web Search, Workspaces & Administration
> Web search, project scoping, admin dashboard, vault health, embedding migration

### Phase 5 — Web Search + Workspaces (Weeks 9–10)
**Backend:** Web search engine (DuckDuckGo, Jina, Wikipedia free; Tavily/Brave/SerpAPI paid), CrossReferenceEngine, ProjectManager (folder/tag scoping — activates existing workspace definitions), frontmatterQuery tool.

**Frontend:** Workspace RAG scoping wired to existing Workspace switcher and creation/edit modal, web search toggle, @web trigger, Focus mode scoping.

**Features:** F-SEARCH-01, F-WORK-01

**Quality gates:**
- Create project → Focus mode → RAG limited to project
- @web query → results displayed

### Phase 6 — Intelligence + Admin (Weeks 11–12)
**Backend:** Vault health endpoints, admin dashboard data endpoints, LLM usage tracking, embedding migration pipeline.

**Frontend:** Admin Dashboard (8 tabs), User Dashboard, vault health visualizations, embedding migration UI.

**Features:** F-VAULT-01, F-ADMIN-01, F-ADMIN-02, F-ADMIN-03, F-INTEL-01, F-DASH-01

**Quality gates:**
- Admin dashboard shows real usage data, costs, users, health
- Change embedding model → progress → complete → search works

---

## Milestone 4: Platform, Polish & Launch
> System tray, Quick Chat, MCP integration, Obsidian export, themes, beta testing

### Phase 7 — Platform + Polish (Weeks 13–14)
**Backend:** MCP client integration (ToolRegistry, stdio + Streamable HTTP transports, health checks), vault export endpoint, image understanding support.

**Frontend:** System tray agent, Quick Chat window, global hotkey, auto-launch, electron-updater, command palette (cmdk), diff modal, vault export, image upload, Settings UI polish (all tabs), user API key management, MCP admin UI, Obsidian export, theme system (Light/Dark/Auto/Custom).

**Features:** F-PLATFORM-01, F-PLATFORM-02, F-CHAT-05, MCP integration, Obsidian export, themes, Settings polish

**Quality gates:**
- Close window → tray icon → Quick Chat via hotkey
- Admin adds MCP server → agent discovers tools → tool calls work with confirmation gate
- Export note and conversation → files appear in Obsidian vault

### Phase 8 — Beta + Launch (Weeks 15–16)
**Deliverables:**
- 10+ beta users across macOS and Windows
- All performance targets met (Section 27)
- Docker image published to GitHub Container Registry
- Backup script + restore procedure tested end-to-end (F-BACKUP-01)
- README with screenshots, quick start guide
- Docker Compose example for advanced deployments

**Quality gates:**
- All NFR targets met
- Backup + restore tested end-to-end
