# Roadmap: Smart Copilot

**Defined:** 2026-05-09
**Phases:** 8
**Requirements:** 68 (mapped: 68, unmapped: 0)

## Phase Map

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|-------------------|
| 1 | Foundation | Docker, auth, schema, file watcher, vault, MCP, REST+WS | FOUND-01..11, MCP-01..04, VAULT-01..03, PAGE-01..05, API-01..04 | 5 criteria |
| 2 | RAG + Agent | Chunking, embedding, hybrid retrieval, auto-links, 22-tool agent | RAG-01..06, LINK-01..04, AGENT-01..03 | 2 criteria |
| 3 | Skills + Ingestion | Skills runtime, ingest skills, entity enrichment, recipes | SKILL-01..05, ENRICH-01..03, RESEARCH-01..02 | 1 criterion |
| 4 | Memory Dream | Nightly consolidation, brain maintenance, report | DREAM-01..08 | 1 criterion |
| 5 | Web + Workspaces | Web search, projects, vault intelligence endpoints | PROJ-01..03, INTEL-01..05 | 3 criteria |
| 6 | Admin + Observability | Admin REST, embedding migration, Prometheus, audit | ADMIN-01..09 | 1 criterion |
| 7 | Platform | MCP registry, DAG jobs, backups, rate limits | PLAT-01..06 | 1 criterion |
| 8 | Electron Client | Desktop UI, tray, Obsidian export | UI-01..09 | 1 criterion |

---

## Phase 1: Foundation

**Goal:** Provision Docker container, authentication, database schema, file watcher, MCP server, REST + WebSocket API

**Mode:** mvp

**Success Criteria:**
1. New user created via CLI, MCP token issued
2. Claude Code connects via stdio and successfully brain_put / brain_get / brain_search
3. REST API serves authenticated requests with proper RLS isolation
4. WebSocket gateway delivers real-time updates
5. Admin can operate fully via CLI without UI

**Requirements:** FOUND-01, FOUND-02, FOUND-03, FOUND-04, FOUND-05, FOUND-06, FOUND-07, FOUND-08, FOUND-09, FOUND-10, FOUND-11, MCP-01, MCP-02, MCP-03, MCP-04, VAULT-01, VAULT-02, VAULT-03, PAGE-01, PAGE-02, PAGE-03, PAGE-04, PAGE-05, API-01, API-02, API-03, API-04

---

## Phase 2: RAG + Agent

**Goal:** Implement hybrid retrieval, zero-LLM auto-link extraction, and 22-tool agent surface

**Mode:** mvp

**Success Criteria:**
1. Graph queries (who works at X, what did Y invest in) return correct typed-link traversals
2. Hybrid search beats vector-only on fixture corpus

**Requirements:** RAG-01, RAG-02, RAG-03, RAG-04, RAG-05, RAG-06, LINK-01, LINK-02, LINK-03, LINK-04, AGENT-01, AGENT-02, AGENT-03

---

## Phase 3: Skills + Ingestion

**Goal:** Build skills system, default ingest skills, entity enrichment, and data-research recipes

**Mode:** mvp

**Success Criteria:**
1. Pasted meeting transcript triggers meeting-ingestion, creates/updates person and company pages with compiled-truth + timeline, emits typed links

**Requirements:** SKILL-01, SKILL-02, SKILL-03, SKILL-04, SKILL-05, ENRICH-01, ENRICH-02, ENRICH-03, RESEARCH-01, RESEARCH-02

---

## Phase 4: Memory Dream

**Goal:** Implement nightly Memory Dream consolidation and continuous brain maintenance

**Mode:** mvp

**Success Criteria:**
1. Scheduled job runs, repairable defects auto-fixed, unrepairable ones surfaced in report

**Requirements:** DREAM-01, DREAM-02, DREAM-03, DREAM-04, DREAM-05, DREAM-06, DREAM-07, DREAM-08

---

## Phase 5: Web + Workspaces

**Goal:** Implement web search, projects/workspaces, and vault intelligence endpoints

**Mode:** mvp

**Success Criteria:**
1. @web queries return ranked results
2. Project-scoped queries restrict RAG to the project
3. Orphan/hub endpoints return correct counts on fixture vault

**Requirements:** PROJ-01, PROJ-02, PROJ-03, INTEL-01, INTEL-02, INTEL-03, INTEL-04, INTEL-05

---

## Phase 6: Admin + Observability

**Goal:** Full admin REST + CLI surfaces, embedding migration, Prometheus metrics, audit log query

**Mode:** mvp

**Success Criteria:**
1. Admin can register new user, swap embedding models with progress tracking, view real per-user usage and cost via REST, observe metrics in Prometheus format

**Requirements:** ADMIN-01, ADMIN-02, ADMIN-03, ADMIN-04, ADMIN-05, ADMIN-06, ADMIN-07, ADMIN-08, ADMIN-09

---

## Phase 7: Platform

**Goal:** MCP server registry, durable-job DAGs, backup automation, rate limits

**Mode:** mvp

**Success Criteria:**
1. Admin adds new MCP server, agent discovers and uses its tools with confirmation gates; scheduled DAG of dependent jobs runs to completion across container restart

**Requirements:** PLAT-01, PLAT-02, PLAT-03, PLAT-04, PLAT-05, PLAT-06

---

## Phase 8: Electron Client

**Goal:** Build Electron/TypeScript/React desktop client consuming documented REST + WebSocket API

**Mode:** mvp

**Success Criteria:**
1. End-to-end walkthrough — new user logs in via Electron client, chats with brain, accepts put_page confirmation, opens resulting note in Tiptap editor, exports conversation to configured Obsidian vault path

**Requirements:** UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, UI-07, UI-08, UI-09

---

*Roadmap defined: 2026-05-09*
*Last updated: 2026-05-09 after initial extraction from PRD v26.05.1*