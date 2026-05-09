# Requirements: Smart Copilot

**Defined:** 2026-05-09
**Core Value:** Users can query their personal knowledge vault through AI agents with hybrid retrieval and get grounded, cite-backed responses

## v1 Requirements

### Foundation (Phase 1)

- [ ] **FOUND-01**: User can register with email/password (argon2-cffi hashing, 10 fails/15min rate limit)
- [ ] **FOUND-02**: User can log in and receive access JWT + refresh token
- [ ] **FOUND-03**: Session persists with revocable refresh tokens (SHA-256 hashed)
- [ ] **FOUND-04**: Admin can create/delete users via CLI and REST
- [ ] **FOUND-05**: User can create named MCP bearer tokens (256-bit, shown once)
- [ ] **FOUND-06**: MCP tokens are revocable and track last_used_at
- [ ] **FOUND-07**: All admin operations are audited in audit_log
- [ ] **FOUND-08**: System runs as single Docker container with supervisord (nodaemon=true)
- [ ] **FOUND-09**: PostgreSQL 16 + pgvector as sole datastore (no Redis/Celery)
- [ ] **FOUND-10**: API keys encrypted at rest with Fernet (never in Pydantic responses)
- [ ] **FOUND-11**: Multi-tenant isolation via PostgreSQL RLS (GUC session context)

### MCP Server (Phase 1)

- [ ] **MCP-01**: MCP server supports stdio mode (`smartcopilot mcp serve --stdio`)
- [ ] **MCP-02**: MCP server supports HTTP mode (Streamable HTTP, port 8787)
- [ ] **MCP-03**: MCP bearer token auth with per-user RLS context
- [ ] **MCP-04**: All MCP tools call same service layer as REST API

### Vault & Pages (Phase 1)

- [ ] **VAULT-01**: Private vaults at `/vaults/private/{username}/`
- [ ] **VAULT-02**: Shared vault at `/vaults/shared/`
- [ ] **VAULT-03**: Path traversal and symlink escape blocked
- [ ] **PAGE-01**: Pages support compiled-truth + timeline convention (--- separator)
- [ ] **PAGE-02**: Pages support frontmatter (YAML JSONB)
- [ ] **PAGE-03**: Page CRUD with content-hash dedup
- [ ] **PAGE-04**: Watchdog file indexer with thread→asyncio handoff
- [ ] **PAGE-05**: Soft delete with deleted_at, deleted_by, delete_reason

### REST + WebSocket (Phase 1)

- [ ] **API-01**: REST API with OpenAPI generation
- [ ] **API-02**: WebSocket gateway for real-time updates
- [ ] **API-03**: SSE stream for chat completions
- [ ] **API-04**: Admin REST endpoints for all admin operations

### RAG (Phase 2)

- [ ] **RAG-01**: Chunking with compiled_truth/timeline/frontmatter kinds
- [ ] **RAG-02**: Embeddings via LiteLLM with HNSW index (1536 dim default)
- [ ] **RAG-03**: BM25 tsvector index with websearch_to_tsquery
- [ ] **RAG-04**: Hybrid retrieval with Reciprocal Rank Fusion (RRF)
- [ ] **RAG-05**: Multi-query expansion + intent classification
- [ ] **RAG-06**: 4-layer dedup (page-level, chunk-level, semantic, RRF)

### Auto-Link Extraction (Phase 2)

- [ ] **LINK-01**: Zero-LLM deterministic wikilink extraction on every page write
- [ ] **LINK-02**: Typed entities: person, company, concept, idea
- [ ] **LINK-03**: Typed links with confidence, context_excerpt
- [ ] **LINK-04**: Graph queries via recursive CTEs (who works at X, what did Y invest in)

### Agent Surface (Phase 2)

- [ ] **AGENT-01**: 22-tool agent surface
- [ ] **AGENT-02**: Brain-first system prompt (query brain before external API)
- [ ] **AGENT-03**: Skill run tool with RESOLVER.md dispatcher

### Skills System (Phase 3)

- [ ] **SKILL-01**: Skills as first-class workflow primitive
- [ ] **SKILL-02**: RESOLVER.md dispatcher
- [ ] **SKILL-03**: System namespace for default skills
- [ ] **SKILL-04**: Per-user namespace for user skills
- [ ] **SKILL-05**: Default ingest skills: idea-ingest, media-ingest, meeting-ingestion

### Entity Enrichment (Phase 3)

- [ ] **ENRICH-01**: Tiered entity enrichment (person, company, concept)
- [ ] **ENRICH-02**: Entity canonicalization and alias management
- [ ] **ENRICH-03**: Compiled-truth + timeline on enriched entities

### Data Research (Phase 3)

- [ ] **RESEARCH-01**: Data-research recipes
- [ ] **RESEARCH-02**: Web search (DuckDuckGo, Jina Reader, Wikipedia)

### Memory Dream (Phase 4)

- [ ] **DREAM-01**: Nightly Memory Dream consolidation cycle
- [ ] **DREAM-02**: Stale page detection and flagging
- [ ] **DREAM-03**: Orphan page detection
- [ ] **DREAM-04**: Dead link audit
- [ ] **DREAM-05**: Citation re-check
- [ ] **DREAM-06**: Back-link enforcement
- [ ] **DREAM-07**: Tag consistency maintenance
- [ ] **DREAM-08**: Maintenance report via MCP and REST

### Projects & Workspaces (Phase 5)

- [ ] **PROJ-01**: Project/workspace scoped queries (folder patterns, tags)
- [ ] **PROJ-02**: include_folders, exclude_folders, tag_includes, tag_excludes
- [ ] **PROJ-03**: Optional system_prompt and default_model per project

### Vault Intelligence (Phase 5)

- [ ] **INTEL-01**: Orphan endpoint
- [ ] **INTEL-02**: Hub detection endpoint
- [ ] **INTEL-03**: Link suggestion endpoint
- [ ] **INTEL-04**: Vault graph endpoint
- [ ] **INTEL-05**: Vault organize endpoints (organize/apply/undo)

### Admin & Observability (Phase 6)

- [ ] **ADMIN-01**: User CRUD via REST
- [ ] **ADMIN-02**: Shared API keys management
- [ ] **ADMIN-03**: Embedding migration with progress tracking
- [ ] **ADMIN-04**: Dream status and triggers
- [ ] **ADMIN-05**: MCP server registration (add external MCP servers)
- [ ] **ADMIN-06**: Prometheus /metrics endpoint
- [ ] **ADMIN-07**: Structured JSON logs
- [ ] **ADMIN-08**: Audit log query endpoint
- [ ] **ADMIN-09**: Real per-user usage and cost via REST

### Platform (Phase 7)

- [ ] **PLAT-01**: MCP server registry (admin-configurable external servers)
- [ ] **PLAT-02**: Durable-job DAGs (minion-orchestrator)
- [ ] **PLAT-03**: Job cancellation
- [ ] **PLAT-04**: Rate limits
- [ ] **PLAT-05**: Deterministic backup automation script
- [ ] **PLAT-06**: Verified restore procedure

### Electron Client (Phase 8)

- [ ] **UI-01**: Electron/TypeScript/React desktop client
- [ ] **UI-02**: Chat-first UI with split-pane Tiptap editor
- [ ] **UI-03**: Vault sidebar
- [ ] **UI-04**: System tray + Quick Chat with global hotkey
- [ ] **UI-05**: DOMPurify clipboard sanitization
- [ ] **UI-06**: electron-store local settings
- [ ] **UI-07**: electron-updater auto-update via GitHub Releases
- [ ] **UI-08**: SSE streaming chat (citations, tool_start/result, confirm modals)
- [ ] **UI-09**: Obsidian export feature

### Testing (Cross-phase)

- [ ] **TEST-01**: pytest + pytest-asyncio suite against real PostgreSQL
- [ ] **TEST-02**: RLS isolation tests
- [ ] **TEST-03**: End-to-end phase acceptance tests

## v2 Requirements

### Future

- **GOLDEN-01**: Golden query evaluation system for retrieval regression tests
- **SEMANTIC-01**: Semantic hash for normalized page representation
- **COLLAB-01**: Real-time multi-user collaborative editing

## Out of Scope

| Feature | Reason |
|---------|--------|
| LightRAG / GraphRAG | Zero-LLM approach only |
| Redis / Celery / RabbitMQ | PostgreSQL does everything |
| LiteLLM as separate proxy | In-process library only |
| SQLite / DuckDB / PGLite | PostgreSQL only |
| Mobile clients | Desktop-first |
| VS Code extension | MCP is the integration point |
| Custom RBAC beyond admin/user | Two roles only |
| LLM-based link extraction | Deterministic only |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 through FOUND-11 | Phase 1 | Pending |
| MCP-01 through MCP-04 | Phase 1 | Pending |
| VAULT-01 through VAULT-03 | Phase 1 | Pending |
| PAGE-01 through PAGE-05 | Phase 1 | Pending |
| API-01 through API-04 | Phase 1 | Pending |
| RAG-01 through RAG-06 | Phase 2 | Pending |
| LINK-01 through LINK-04 | Phase 2 | Pending |
| AGENT-01 through AGENT-03 | Phase 2 | Pending |
| SKILL-01 through SKILL-05 | Phase 3 | Pending |
| ENRICH-01 through ENRICH-03 | Phase 3 | Pending |
| RESEARCH-01 through RESEARCH-02 | Phase 3 | Pending |
| DREAM-01 through DREAM-08 | Phase 4 | Pending |
| PROJ-01 through PROJ-03 | Phase 5 | Pending |
| INTEL-01 through INTEL-05 | Phase 5 | Pending |
| ADMIN-01 through ADMIN-09 | Phase 6 | Pending |
| PLAT-01 through PLAT-06 | Phase 7 | Pending |
| UI-01 through UI-09 | Phase 8 | Pending |
| TEST-01 through TEST-03 | Cross-phase | Pending |

**Coverage:**
- v1 requirements: 68 total
- Mapped to phases: 68
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-09*
*Last updated: 2026-05-09 after initial extraction from PRD v26.05.1*