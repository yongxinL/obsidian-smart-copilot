# Smart Copilot — Requirements

## Functional Requirements

### Phase 1 — Foundation

**REQ-001: Single Container Deployment (F-DOCKER-01) — Must Have**
`docker run` starts PostgreSQL 16 + FastAPI via supervisord. `GET /health` returns 200 within 30 seconds. `wait-for-pg.sh` polls `pg_isready`. Alembic migrations run automatically. HEALTHCHECK triggers restart on failure. External PostgreSQL supported via `EXTERNAL_DB=true` + `DATABASE_URL`.

**REQ-002: Database Schema with RLS (F-SCHEMA-01) — Must Have**
All 14 RLS-protected tables with policies enabled. Content tables: `namespace = 'shared' OR user_id = current_setting(...)`. Private tables: `user_id = current_setting(...)`. `get_db_session` RESET in finally block. `system_config` seeded with embedding model on first run. 17 tables total including system_config, sessions, user_settings.

**REQ-003: JWT Authentication System (F-AUTH-01) — Must Have**
`POST /api/v1/auth/login` returns access + refresh tokens. Access: 24h, Refresh: 30d (configurable). `must_change_password` flag support. Automatic refresh on 401. Tokens in Electron safeStorage. "Remember me" toggle. 9 auth endpoints total.

**REQ-004: User Registration & Admin Bootstrap (F-AUTH-02) — Must Have**
First user becomes admin (`GET /health` returns `setup_required: true`). Admin creates users with temporary passwords. `must_change_password` enforced. Admin can reset passwords, update role/email. Delete user requires typed username confirmation. Username immutable.

**REQ-005: File Watcher + IndexQueue (F-IDX-01) — Must Have**
watchdog detects create/modify/delete/rename on `.md` files. Events debounced 300ms. VaultRegistry resolves path → (user_id, namespace). IndexQueue for async processing. App-initiated writes bypass watcher (content_hash dedup). Markdown parser extracts frontmatter + wikilinks. NoteTypeClassifier infers from frontmatter, folder, tags.

**REQ-006: Bulk Initial Indexing (F-IDX-02) — Must Have**
Detect unindexed vault, begin bulk processing. Progress reported via `GET /api/v1/vault/index/progress`. Chat available before indexing completes. Target: 1000 notes < 5 minutes.

### Phase 2 — RAG + Chat

**REQ-007: Hybrid RAG Search (F-RAG-01) — Must Have**
Three signals in single PostgreSQL query: vector cosine (0.5), BM25 keyword (0.3), wikilink graph proximity (0.2). Combined via RRF with k=60. Top K results (default: 10). RLS includes shared namespace. Wikilink graph recursive CTE, max 3 hops. Latency < 300ms. Three search contexts: knowledge (permanent), citation (literature), all.

**REQ-008: Contextual Enrichment Pipeline (F-RAG-02) — Must Have**
Prepend title, folder, tags, backlink/outlink titles before embedding. Note type determines enrichment level. enrichment_hash triggers re-embed on link changes. Cascade limited to 1 hop. Chunk replacement atomic via SAVEPOINT. Chunking: 512 tokens, 64 overlap, paragraph boundaries, single-chunk threshold 600.

**REQ-009: Multi-turn Chat with SSE Streaming (F-CHAT-01) — Must Have**
`POST /api/v1/chat/completions` opens SSE stream. Token streaming, citations before tokens, done event with usage. Response start < 500ms. @mention autocomplete via Lexical. File references as additional context. MCP mode toggle (disable/auto/manual) per conversation. 9 SSE event types.

**REQ-010: Chat History CRUD (F-CHAT-02) — Must Have**
Paginated, searchable, date-filterable conversations. Update title/model/mode. Delete with vault-save awareness. Regenerate last response. Auto-generate title on first message via LLM.

**REQ-011: LiteLLM Provider Routing + Key Resolution (F-LLM-01) — Must Have**
Support OpenAI, Anthropic, Gemini, DeepSeek, OpenRouter, Ollama, LM Studio, vLLM, OpenAI-compatible. Key resolution: user → shared → error. key_type tracking (personal/shared). LiteLLM callbacks log to llm_usage table.

**REQ-012: Mode System (F-CHAT-03) — Should Have**
Single-select prompt-scoped pills. 4 built-in modes (Ask, Write, Research, Focus) + custom. Research presets web search ON. Up to 5 pinned in picker. Built-in modes show edit indicator when modified, resettable to default.

**REQ-013: Model Selector (F-CHAT-04) — Should Have**
Grouped by provider. Sticky per conversation. New conversation → project default. Each message records model_id snapshot. Key indicator when personal key active.

**REQ-014: @web Client-Side Detection (F-CHAT-06) — Should Have**
Lexical detects `@web` as special command. Strips from message, sets `web_search_enabled: true`. Toggle visually flips ON.

**REQ-015: User Settings CRUD (F-SETTINGS-01) — Must Have**
`GET /api/v1/settings` returns merged (user override + server default). `PUT /api/v1/settings` updates partial overrides. Server-only settings not overridable. 8 settings endpoints. Settings resolution with null-reverts-to-default.

### Phase 3 — Editor + Zettelkasten

**REQ-016: Tiptap Split-Pane Editor (F-EDITOR-01) — Should Have**
Editor opens from citations, command palette, agent actions. Collapses when no file open. Tiptap v2 + @tiptap/markdown round-trip. react-resizable-panels with snap presets (65/35, 35/65). "Copy to Docs" action on AI messages when editor open.

**REQ-017: Note Splitting (F-ZETT-01) — Must Have**
NoteSplitter splits at H1 > H2 > H3 boundaries. Child notes: timestamp ID, type permanent, source backlink. Original handling: Keep as literature (default) / Archive / Delete (double confirmation). Auto-offer when note exceeds min_word_count. Preview modal with editable titles.

**REQ-018: Document Import (F-ZETT-02) — Should Have**
`POST /api/v1/documents/upload` accepts PDF (PyMuPDF), DOCX (python-docx), HTML (nh3 + readability-lxml). Extracted text saved as literature note. Offers split for large notes. Defense-in-depth sanitization.

**REQ-019: Chat → Zettel Capture (F-ZETT-03) — Should Have**
`@zettel` detected by Lexical, sets `zettel_capture: true`. Backend appends Zettel Capture Prompt. ZettelNotePreviewModal for editing. On accept, creates note with frontmatter and indexes immediately.

### Phase 4 — Agent + Memory

**REQ-020: Agent Runner (F-AGENT-01) — Must Have**
ReAct-style loop: Thought → Action → Observation. Max 10 tool calls per turn (configurable). Streams via SSE (tool_start, tool_result, tool_confirm). Continue/Stop at max_tool_calls. Error returned as observation for retry. Sequential execution for confirmation flow. Skill resolution before tool execution (trigger matching, namespace scoping, token budgeting). Per-mode tool filtering.

**REQ-021: Core Read-Only Agent Tools (F-AGENT-02) — Must Have**
11 auto-approve tools: ragSearch, vaultRead, detectOrphans, suggestLinks, analyzeNote, memoryRecall, frontmatterQuery, reconcileIndex, scheduleMaintenance, notifyUser, openInEditor.

**REQ-022: Core Write Agent Tools (F-AGENT-03) — Must Have**
11 confirmation-required tools: vaultWrite, webSearch, splitNote, generateMOC, organizeVault, captureFromURL, captureFromClipboard (client-cooperative protocol), moveAndRefactor, batchOrganize, undoLastOrganize, cleanOrphans.

**REQ-023: Confirmation Gate (F-AGENT-04) — Should Have**
Modal shows tool name, parameters, expected outcome. Approve or cancel. Configurable per type. MCP tool calls follow same gate. Admin configurable always_allow per MCP server.

**REQ-024: OperationLog with Undo (F-AGENT-05) — Should Have**
Steps recorded with typed schema (action, source_path, target_path, old_content, affected_links). Undo reverses steps. `POST /api/v1/vault/organize/undo`.

**REQ-025: Memory Extraction and Storage (F-MEM-01) — Must Have**
MemoryExtractor uses LLM to identify facts/preferences. Stored with embedding. Max 500 per user, 200 active. Manage: view, edit (re-embeds), archive, delete, import, export. Import duplicate detection (>95% cosine similarity).

**REQ-026: Memory Recall (F-MEM-02) — Must Have**
Semantic search over active memories. Updates last_recalled_at and recall_count. 12 memory endpoints total.

**REQ-027: Memory Dream Consolidation (F-MEM-03) — Should Have**
Triggers: 24+ hours AND 5+ sessions since last cycle. 4 phases: Orientation → Gather Signal → Consolidation → Prune & Index. All actions logged to dream_audit_log. Advisory lock prevents concurrent runs. Manual trigger via API and UI.

### Phase 5 — Web Search + Workspaces

**REQ-028: Web Search (F-SEARCH-01) — Should Have**
Free: DuckDuckGo + Jina Reader + Wikipedia (no keys). Paid (optional): Tavily, Brave, SerpAPI. Triggered by @web, toggle, or Research mode. Cross-reference with vault. 2 web search endpoints.

**REQ-029: Workspace RAG Scoping (F-WORK-01) — Should Have**
Workspaces define: include_folders, exclude_folders, tags, system_prompt, default_model. Focus mode restricts RAG to active workspace. Workspace switcher with conversation association. CRUD via /api/v1/projects.

### Phase 6 — Intelligence + Admin

**REQ-030: Vault Health Endpoints (F-VAULT-01) — Should Have**
Composite health score, orphan notes list, most-connected hubs, graph nodes + edges for Cytoscape, recent index events, link suggestions (per-note and vault-wide), user-scoped reindex (rate-limited 1/hour). 14 vault endpoints total.

**REQ-031: Admin Dashboard (F-ADMIN-01) — Must Have**
8 tabs: Overview, LLM Usage, Storage, API Keys, Users, Memory Dream, System Health, MCP Servers. Admin-only via require_admin. Client hides for non-admins. 27 admin endpoints total.

**REQ-032: LLM Usage Tracking (F-ADMIN-02) — Should Have**
Admin: cost by provider, by user, usage history. User: 30d/7d/today summary, by-model breakdown. Shared vs personal key attribution. Purpose breakdown (chat/embedding/agent/enrichment/dream). 6 user usage endpoints.

**REQ-033: Embedding Migration (F-ADMIN-03) — Should Have**
Estimate cost/time, start migration, progress tracking, cancellation. Search works (degraded) during migration. 6-phase pipeline with crash recovery. Admin-only enforced at API, settings, and config levels.

### Phase 7 — Platform + Polish

**REQ-034: System Tray Agent (F-PLATFORM-01) — Could Have**
Tray icon: Quick Chat, Search, Reindex, Settings, Quit. App continues when windows closed. Dynamic icon/tooltip for indexing status.

**REQ-035: Quick Chat Window (F-CHAT-05) — Could Have**
400×500 floating window. Shares auth with main window. Launched from tray or global hotkey.

**REQ-036: Global Hotkey (F-PLATFORM-02) — Could Have**
Cmd+Shift+Space (default, configurable). Electron globalShortcut API.

**REQ-037: MCP Client Integration — Should Have**
MCP Python SDK (v1.x). ToolRegistry merges built-in + MCP tools. stdio + Streamable HTTP transports. Admin UI for server configuration. Health checks (60s ping, 3 failures → disconnect + backoff). Hot reload (no restart). All MCP outputs sanitized. 5 admin MCP endpoints.

**REQ-038: Vault Export — Should Have**
`POST /api/v1/conversations/{id}/export` writes markdown to vault. Deduplication rules. End-of-chat save prompt (opt-in).

**REQ-039: Image Understanding — Should Have**
Image upload via More Options Drawer or paste. base64 in `images` field. LiteLLM vision-capable model format. Max 5MB. PNG, JPEG, WebP, GIF.

**REQ-040: Obsidian Export — Should Have**
Export buttons in editor toolbar, sidebar context menu, conversation header. Electron IPC for native folder dialog + batch file writing. Preserves frontmatter and wikilinks. Path traversal protection.

**REQ-041: Theme System — Could Have**
4 options: Light / Dark / Auto / Custom. Electron nativeTheme IPC bridge. Custom: accent + background colour pickers. Stored in electron-store (device-specific).

**REQ-042: Command Palette — Should Have**
cmdk integration for keyboard-driven navigation.

**REQ-043: Auto-updater — Should Have**
electron-updater with GitHub Releases.

**REQ-044: Web Client — Should Have**
Platform abstraction layer (electron.ts / web.ts). FastAPI serves built web client as static SPA. Browser-safe fallbacks. Platform-unavailable features hidden (not disabled).

### Phase 8 — Beta + Launch

**REQ-045: Backup Strategy (F-BACKUP-01) — Should Have**
Automated backup script (pg_dump + rsync + settings). 30-day retention. Restore procedure tested. backup-status.json for admin dashboard.

**REQ-046: Beta Testing — Must Have**
10+ beta users across macOS and Windows. All performance targets met. Docker image published to GHCR.

**REQ-047: Documentation — Must Have**
README with screenshots, quick start guide. Docker Compose example for advanced deployments.

---

## Non-Functional Requirements

### Performance

| ID | Metric | Target |
|---|---|---|
| NFR-001 | Chat response start | < 500ms |
| NFR-002 | RAG search latency | < 300ms |
| NFR-003 | Bulk index 1000 notes | < 5 minutes |
| NFR-004 | Watcher → indexed | < 5 seconds |

### Scale

| ID | Metric | Target |
|---|---|---|
| NFR-005 | Concurrent users | 3–10 |
| NFR-006 | Notes per user | 500–5,000 |
| NFR-007 | Active memories per user | ≤ 200 |
| NFR-008 | Max memories per user | 500 |

### Reliability

| ID | Metric | Target |
|---|---|---|
| NFR-009 | Container restart recovery | < 30 seconds |
| NFR-010 | Index reconciliation | Every 6 hours |
| NFR-011 | Dream concurrency | Max 1 concurrent run |

### Security

| ID | Requirement | Implementation |
|---|---|---|
| NFR-012 | Data isolation | RLS on all 14 user-scoped tables |
| NFR-013 | Key encryption | Fernet AES-128 at rest |
| NFR-014 | Token storage | Electron safeStorage (OS keychain) |
| NFR-015 | HTML sanitization | DOMPurify (client) + nh3 (server) |
| NFR-016 | Admin enforcement | API-level require_admin dependency |
| NFR-017 | Rate limiting | 30 req/min API, 60 tool calls/min agent |

---

## Explicitly Out of Scope (v1.0)

- LightRAG integration (deferred; RAGBackend interface supports future addition)
- FIM autocomplete (no in-app editor cursor integration)
- VS Code companion extension
- Mobile clients
- EPUB import
- Custom role hierarchies beyond admin/user
- Mobile-optimised layout (viewports < 768px)
- PWA manifest
- Offline mode

---

## API Surface Summary

~103 endpoints across 14 route groups:
- Auth: 9 endpoints
- Chat: 8 endpoints
- Search: 3 endpoints
- Documents: 5 endpoints
- Vault: 14 endpoints
- Agent: 2 endpoints
- Web Search: 2 endpoints
- Memory: 12 endpoints
- Projects: 4 endpoints
- Models: 2 endpoints
- User Usage & Status: 6 endpoints
- User Settings: 8 endpoints
- Admin: 27 endpoints
- Health: 1 endpoint
