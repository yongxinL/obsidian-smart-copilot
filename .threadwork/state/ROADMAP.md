# Smart Copilot — Roadmap

**Timeline:** 8 phases across 16 weeks  
**Status:** Phase 1 ready to plan

---

## Milestone 1: Foundation + Core Intelligence (Phases 1–4)

### Phase 1 — Foundation (Weeks 1–2)
**Epic E1: Foundation**

Backend:
- Docker container: supervisord + wait-for-pg.sh + Alembic auto-migration
- Full database schema with RLS (all 14 tables, system_config seed)
- JWT auth system: register, login, refresh, change-password, require_admin, must_change_password
- User management CRUD + password reset (admin-mediated)
- VaultRegistry + file watcher (watchdog) + IndexQueue
- Markdown parser (frontmatter + wikilink extraction) + NoteTypeClassifier
- Workspace: `projects` **table only** (needed for FK constraints on `conversations.project_id`). **No `/api/v1/projects` API endpoints. No Workspace UI beyond the structural route stub at `/workspace` (empty 3-pane shell).** Full Workspace CRUD + UI ships in Phase 5 (F-WORK-01).
- Indexing progress endpoint (`GET /api/v1/vault/index/progress`)
- Health endpoint with `setup_required` flag

Frontend:
- Electron shell with Forge + Vite
- Login page: standard login form + first-run "Create Admin Account" variant
- API client generated from OpenAPI spec
- Auth flow: JWT safeStorage, refresh, forced password change dialog
- Home page (Page 2) — initial version with stat cards
- Workspace page (Page 4) — initial 3-pane layout (CRUD only)
- System Settings (Page 7) — Users tab, Auth & Advanced tab, System Health tab
- Customize (Page 5) — initial shell
- Chat History (Page 6) — initial version

**Quality Gate:** `docker run` → `GET /health` 200 within 30s. Register → login → JWT → authenticated request succeeds. Create .md → watcher event logged.

---

### Phase 2 — RAG + Chat (Weeks 3–4)
**Epic E2: RAG & Chat**

Backend:
- ContextEnricher + Chunker + Embedder (LiteLLM aembedding, batching, xxhash)
- HybridRAGEngine: vector + BM25 + wikilink CTE, single PostgreSQL query, RRF
- Bulk initial indexing with progress
- LiteLLM gateway + key resolver (user → shared → error, key_type tracking)
- `POST /api/v1/chat/completions` with SSE streaming (token, citations, done events)
- Chat history CRUD (conversations + messages)
- enrichment_hash + cascade re-embedding (1-hop limit, SAVEPOINT atomic)
- nh3 HTML sanitizer integration
- User settings CRUD (`GET/PUT /api/v1/settings`)
- `GET /api/v1/models` and `GET /api/v1/models/embedding`
- `POST /api/v1/conversations` + Conversation backend processing flow (10 steps)
- `POST /api/v1/vault/reindex` (user's namespace)

Frontend:
- Chat panel (Page 3): Lexical input + @mentions + @web + SSE client + message list
- Citation badges [1][2] in message content
- Chat history popover with search + date filter
- Model picker (grouped by provider, 🔑 indicator)
- Mode picker with pill system (Ask/Write/Research/Focus)
- DOMPurify clipboard sanitizer
- Right utility sidebar: Sources / Suggested Tasks / Deep Dive
- MCP toggle (3-state) in chat input toolbar
- Chat Settings popover (temperature, max_tokens, top-p, frequency penalty, reasoning effort)
- More Options Drawer (web search toggle, relevant notes, agent tools, file/image upload)
- System Settings → Models & Inference tab, RAG & Knowledge tab, Shared API Keys tab

**Quality Gate:** Message → hybrid search → citations in response. Change model → new model used. RAG latency < 300ms (NFR-002). **Bulk index 1000 notes < 5 minutes (NFR-003)** — full embedding pipeline end-to-end, measured from `POST /api/v1/vault/reindex` (or first-run auto-trigger) to `GET /api/v1/vault/index/progress` reporting `status: "complete"`. This is the perf target moved from REQ-006 Phase 1 scope; it requires the Phase 2 Embedder.

---

### Phase 3 — Editor + Zettelkasten (Weeks 5–6)
**Epic E3: Editor & Zettelkasten**

Backend:
- NoteSplitter + ZettelNoteBuilder (H1>H2>H3 boundaries, atomic permanents)
- Document import: PDF (PyMuPDF), DOCX (python-docx), HTML (nh3 → readability-lxml)
- Web clipper: Jina Reader + nh3
- Vault write/move/split endpoints (`POST /api/v1/vault/write|move|split`)
- LinkRefactorer: update wikilinks on file move
- OperationLog: JSONB steps for undo support
- Document endpoints: `GET/GET/{id}/PUT /api/v1/documents`, upload + status poll
- Avatar upload (`PATCH /api/v1/auth/me/avatar`)
- Sessions list + revoke (`GET/DELETE /api/v1/auth/sessions`)

Frontend:
- Collapsible vault sidebar: react-complex-tree tree view + flat list view
- Tiptap v2 split-pane editor with react-resizable-panels
- Two snap presets: Chat-focused (65/35) and Write-focused (35/65)
- "Copy to Docs" action on AI message bubbles
- NoteSplitterModal: editable child note titles, original handling options
- ZettelNotePreviewModal: edit before save
- Write mode scopes RAG to open file via `current_note_path`
- Sidebar tree updates on file changes (watch via polling or SSE)
- File context menu (rename, move, split, export, delete)
- User Profile Modal (Profile / Appearance / AI & Chat tabs)

**Quality Gate:** Upload PDF → extract → split → atomic notes with backlinks. Click citation → Tiptap opens. Browse vault in sidebar, sidebar reflects vault structure.

---

### Phase 4 — Agent + Memory (Weeks 7–8)
**Epic E4: Agent & Memory**

Backend:
- AgentRunner: ReAct plan-execute-observe loop (max 10 tool calls, SSE events)
- 22 built-in tools (see PRD §17)
- Confirmation gate: `tool_confirm` SSE → `POST /api/v1/agent/approve`
- `captureFromClipboard` SSE round-trip protocol (10s timeout)
- `POST /api/v1/agent/client-response` endpoint
- Skill resolution engine: trigger matching, namespace scoping, token budgeting
- Memory extraction/storage/recall (12 Memory endpoints)
- Memory Dream consolidation: 4-phase cycle, advisory lock, APScheduler, `dream_audit_log`
- Background agent (APScheduler): proactive checks, reconciliation, health snapshots
- `POST /api/v1/vault/organize/undo` (OperationLog from Phase 3)

Frontend:
- Agent tool banner (SSE tool_start / tool_result / tool_confirm events)
- Confirmation modals for write tools
- SSE `client_request` handler (clipboard read)
- Research mode fully wired (agent_enabled: true, all 22 tools)
- Memory panel: Customize → Memory tab (CRUD, import, export, Dream status)
- Skills management: Customize → My Skills tab

**Quality Gate:** Research mode → agent uses ragSearch + webSearch + vaultWrite (all 3 in one turn). Fact in chat → memoryRecall finds it in new conversation. Trigger Dream → consolidation report shows actions.

---

## Milestone 2: Intelligence + Distribution (Phases 5–6)

### Phase 5 — Web Search + Projects (Weeks 9–10)
**Epic E5: Web Search & Projects**

Backend:
- Web search integration: DuckDuckGo (free), Jina Reader, Wikipedia, Tavily/Brave/SerpAPI (paid optional)
- `POST /api/v1/web/search` and `POST /api/v1/web/fetch`
- Project/Workspace RAG scoping activated: Focus mode restricts RAG to project include_folders + tags
- `GET /api/v1/documents` with `project_id` filter applying workspace rules server-side
- `GET /api/v1/conversations` with `project_id` filter
- `POST /api/v1/conversations` with `project_id` body param
- Cross-reference vault with web search results

Frontend:
- Workspace page: workspace dropdown functional with project scoping
- IN SCOPE pane reflects active project's include_folders + tags
- Focus mode wired to project context
- Web search results displayed in Sources sidebar
- Wikipedia cross-reference rendering
- System Settings → Web Search tab

**Quality Gate:** Create project → Focus mode → RAG limited to project. `@web` query → results shown. Workspace filter on Chat History page functional.

---

### Phase 6 — Intelligence + Admin (Weeks 11–12)
**Epic E6: Intelligence & Admin**

Backend:
- Vault intelligence: `GET /api/v1/vault/orphans|hubs|health|graph|links/suggestions`
- SmartOrganizer: `POST /api/v1/vault/organize` (dry run) + `POST /api/v1/vault/organize/apply`
- Wikilink graph visualization via Cytoscape.js-compatible response
- Admin dashboard endpoints: overview, costs by provider/user, usage history, health, index status, dream status
- Cross-user visibility for admin via superuser connection (bypasses RLS)
- User-scoped usage endpoints: summary, history, recent, by-model
- System status endpoints: `GET /api/v1/status` + `/status/providers`
- Embedding model migration pipeline (6 phases, crash recovery, cancellation)
- `GET /api/v1/admin/embeddings/estimate|status|cancel|migrate`

Frontend:
- Admin Dashboard (Page 8): all 8 tabs fully implemented
- Home page intelligence sections: Link Suggestions + Memory Snapshot + Usage & Performance + Vault Health collapsibles
- Vault knowledge graph visualization (Cytoscape.js, lazy-loaded)
- System Settings → Admin-only tabs fully wired: Shared API Keys, Users, MCP Servers (stub), Storage & Indexing
- Customize → My Modes with prompt editing + `✎` indicator + Reset to default
- `GET /api/v1/vault/index/events` for user's index activity

**Quality Gate:** Admin dashboard shows real usage data, costs, users, health. Change embedding model → progress bar → complete → search works. Vault health score reflects actual orphan/hub/type counts.

---

## Milestone 3: Platform + Launch (Phases 7–8)

### Phase 7 — Platform + Polish (Weeks 13–14)
**Epic E7: Platform**

Backend:
- MCP client: mcp Python SDK v1.x, ToolRegistry (built-in + MCP unified), stdio + Streamable HTTP transports
- MCP health checks + auto-reconnection with exponential backoff
- 5 new admin endpoints: `GET/POST /api/v1/admin/mcp/servers`, `DELETE/{name}`, `POST/{name}/toggle`, `POST/{name}/reconnect`
- MCP tool output sanitization before re-entering LLM context
- MCP auth tokens stored in `api_keys` table (provider = `mcp:{server_name}`)
- `POST /api/v1/conversations/{id}/export` (vault export as markdown) — full implementation
- Vision model support: base64 images in ChatCompletionRequest → LiteLLM multimodal

Frontend:
- System tray icon + Quick Chat window (global hotkey, Electron only)
- Auto-updater via electron-updater (GitHub Releases)
- Theme system: Light / Dark / Auto / Custom via Electron nativeTheme
- Obsidian export: editor toolbar + sidebar context menu + conversation header
- Vision model: image upload via More Options Drawer or paste
- Admin Dashboard → MCP Servers tab (Tab H): server management, discovered tools, connection log
- System Settings → MCP Servers tab fully functional
- Skill editor: tool name picker when MCP enabled
- Platform abstraction layer: `pnpm build:web` target (StaticFiles from FastAPI)
- Settings UI polish: all 10 System Settings tabs fully complete
- User API key management: Customize → API Keys tab with provider status

**Quality Gate:** Close window → tray → Quick Chat via hotkey. Admin adds MCP server → agent discovers tools → tool call with confirmation gate. Obsidian export: note + conversation appear with correct frontmatter and wikilinks.

---

### Phase 8 — Beta + Launch (Weeks 15–16)
**Epic E8: Launch**

- 10+ beta users across macOS and Windows
- All NFR performance targets met (< 500ms chat start, < 300ms RAG, 1000 notes < 5min)
- Automated backup script + restore procedure tested end-to-end
- Docker image published to GitHub Container Registry
- README with screenshots + quick start guide
- Docker Compose example: external PostgreSQL + Caddy reverse proxy
- `smart-copilot migrate-embeddings` CLI fallback documented and tested
- Security review: RLS leak check, key exposure audit, MCP sandboxing verification

**Quality Gate:** All NFR targets met. Docker image published. Backup + restore verified end-to-end.

---

## Phase → Feature ID Cross-Reference

| Phase | Must Have | Should Have | Could Have |
|-------|-----------|-------------|------------|
| 1 | F-DOCKER-01, F-SCHEMA-01, F-AUTH-01, F-AUTH-02, F-IDX-01, F-IDX-02 | — | — |
| 2 | F-RAG-01, F-RAG-02, F-CHAT-01, F-CHAT-02, F-LLM-01, F-SETTINGS-01 | F-CHAT-03, F-CHAT-04, F-CHAT-06 | — |
| 3 | F-ZETT-01 | F-EDITOR-01, F-ZETT-02, F-ZETT-03 | — |
| 4 | F-AGENT-01, F-AGENT-02, F-MEM-01, F-MEM-02, F-ADMIN-01 | F-AGENT-03, F-AGENT-04, F-AGENT-05, F-MEM-03 | — |
| 5 | — | F-SEARCH-01, F-WORK-01 | — |
| 6 | — | F-VAULT-01, F-ADMIN-02, F-ADMIN-03 | F-INTEL-01, F-DASH-01 |
| 7 | — | — | F-PLATFORM-01, F-PLATFORM-02 |
| 8 | F-BACKUP-01 | — | — |
