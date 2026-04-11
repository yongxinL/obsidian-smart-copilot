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
│   │  ├── Agent Runner (22 built-in tools + MCP tools)    │   │
│   │  ├── MCP Client (external tool servers)              │   │
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
| MCP | mcp >= 1.25 (Python SDK) | MCP client for external tool servers. Stdio + Streamable HTTP transports. Pin to v1.x. |
| Auth | python-jose (JWT) | stateless |
| Encryption | cryptography (Fernet) | API keys at rest |
| Hashing | xxhash | fast non-cryptographic hashing for content_hash and enrichment_hash |
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
| File tree | react-complex-tree | Accessible tree view with drag-and-drop, inline rename, virtualization. Actively maintained, zero dependencies, W3C compliant. Evaluate react-arborist (richer API but unmaintained since June 2025) as alternative during Phase 3 Day 1. |
| Components | Radix UI (15 primitives) | |
| Styling | CSS modules, `.sc-` prefix | |
| Icons | Lucide React | |
| Command | cmdk | |
| Diff | diff + react-diff-viewer-continued | |
| Graph | Cytoscape.js (lazy) | |
| Sanitize | DOMPurify | clipboard |
| Update | electron-updater | GitHub Releases |
| Local storage | electron-store | Atomic JSON persistence for client-only settings (Obsidian vault path, last-used export folders, sidebar state). ESM-only. |
| API | Generated from OpenAPI | auto-synced |

### 3.4 OpenAPI Spec Sync

Backend auto-generates `openapi.json` from FastAPI routes. Client runs `pnpm codegen` → fetches spec → generates TypeScript types via `openapi-typescript`. Pre-commit hook. CI fails if types don't match committed. Spec versioned as `docs/openapi.json`.

### 3.5 Multi-Tenancy

Namespace: `private` (per-user) or `shared` (all users). Filesystem: `/vaults/private/{username}/` and `/vaults/shared/`. Publishing = intentional file move. Cross-namespace links: `[[shared/Topic]]`. Conversations, memories, usage, keys = always private.

### 3.6 Wikilink Resolution

Within a namespace, unqualified wikilinks (`[[Topic]]`) resolve via shortest-unique-path matching (Obsidian-compatible). If ambiguous after path matching, the alphabetically-first path wins (deterministic, debuggable). Cross-namespace resolution order: user's current namespace → shared namespace. Explicit prefix `[[shared/Topic]]` bypasses resolution order.

### 3.7 Fleeting Note Expiry

Fleeting notes older than `fleeting_expiry_days` (default: 30) are moved to the archive folder (`zettelkasten.splitter.archive_folder`, default `/archive/`) by the reconciler during its periodic run. The note's `note_type` frontmatter is updated to `archived_fleeting` and the document record's `note_type` column is updated accordingly. `archived_fleeting` notes are removed from all RAG indexes (not searchable) but remain on disk in the archive folder. The file move is recorded in `operation_log` for undo support. The reconciler processes expiry once per `vault.reconciliation_interval_hours` (default: 6 hours). Files are never auto-deleted — only explicit user action or the `cleanOrphans` agent tool removes files permanently.

---

## 4. Architecture Decisions — Final, Do Not Relitigate

> **FOR AI AGENTS:** These 24 decisions are **locked**. Code contradicting them is a bug. Do not propose alternatives.

### Decision 1 — PostgreSQL-only RAG backend
All retrieval in PostgreSQL + pgvector: vector (HNSW), BM25 (tsvector), wikilink graph (recursive CTEs) — single query. `RAGBackend` interface allows future graph-based extension.

### Decision 2 — Hybrid retrieval + contextual enrichment

**Hybrid scoring formula:**

final_score = (0.5 × vector_cosine) + (0.3 × BM25) + (0.2 × wikilink_proximity)

Combined via Reciprocal Rank Fusion (RRF) in a single PostgreSQL query.

**Wikilink graph proximity** uses binary scoring: notes reachable within `wikilink_max_hops` (default: 3) from the context note score 1.0; unreachable notes score 0.0. The recursive CTE returns a set of reachable document IDs which are boosted in RRF ranking.

```sql
WITH RECURSIVE graph_reach AS (
    SELECT target_doc AS doc_id, 1 AS hops
    FROM wikilinks WHERE source_doc = $seed_doc_id
    UNION
    SELECT w.target_doc, gr.hops + 1
    FROM graph_reach gr
    JOIN wikilinks w ON w.source_doc = gr.doc_id
    WHERE gr.hops < $max_hops AND w.target_doc != $seed_doc_id
)
SELECT DISTINCT doc_id FROM graph_reach;
```

**Seed resolution:** `$seed_doc_id` is resolved per backend processing flow step 4a. Three cases:
1. `current_note_path` set → document ID looked up by path → full 3-signal RRF
2. No path but prior citations exist → highest-scored cited doc from last message → opportunistic 3-signal RRF
3. Neither → `seed_doc_id = NULL` → wikilink signal zeroed → 2-signal RRF (vector + BM25 only)

Case 3 is the default for new conversations with no file open. This is acceptable — the wikilink signal adds value primarily when the user has established a context note.

**Contextual enrichment** — prepend metadata before embedding every note. A 15-word atomic note becomes a 60-word enriched document:

```
Title: {title}
Type: {note_type}
Folder: {folder path}
Tags: {tags}
Links to: {outlink titles}
Linked from: {backlink titles}
---
{note body with [[wikilinks]] resolved to plain text titles}
```

Priority order for enrichment fields: title (highest — disambiguates topic), tags (adds keyword coverage for BM25), backlink titles (positions note in graph), outlink titles, folder path, note type. Exclude dates, raw YAML syntax, file paths, and IDs from enrichment — use these as metadata columns for filtering instead. Enrichment prefix should be under 25% of total embedded text.

**Chunking strategy:**

| Parameter | Default | Description |
|---|---|---|
| `chunk_size_tokens` | 512 | Target chunk size. Short notes get a single chunk. |
| `chunk_overlap_tokens` | 64 | ~12.5% overlap at boundaries |
| `min_chunk_tokens` | 50 | Chunks shorter than this merge into previous |
| `respect_boundaries` | `paragraph` | Split at `\n\n` when possible, fall back to sentence (`. `), never mid-sentence |
| `frontmatter_handling` | `strip` | YAML frontmatter stripped before chunking; used only for contextual enrichment |
| `single_chunk_threshold` | 600 | Notes ≤600 tokens after frontmatter stripping → single chunk (no splitting) |

**Separator hierarchy for recursive splitting:** `\n## ` → `\n### ` → `\n\n` → `\n- ` → `\n` → `. ` → ` `. Code blocks and blockquotes are never split mid-block.

**Why 512 tokens:** Atomic Zettel notes average 100–300 words (~130–400 tokens). With enrichment prefix (~100–150 tokens), total embedding input is 230–550 tokens — within text-embedding-3-small's 8191-token limit. Literature notes (1,000–5,000 words) get 2–10 chunks at paragraph boundaries.

**Note type RAG treatment** — the ContextEnricher reads note type before embedding:

| Type | Frontmatter | Purpose | RAG treatment |
|---|---|---|---|
| `permanent` | `type: permanent` | Single atomic idea | Full enrichment, full RAG weight, `knowledge` context |
| `literature` | `type: literature` | Summary of a source | Enriched with source metadata, `citation` context |
| `fleeting` | `type: fleeting` | Quick capture, inbox | Minimal enrichment, low weight, expires after configurable days |
| `project` | `type: project` | Planning, tasks | Excluded from knowledge RAG, only via `frontmatterQuery` |
| `structure` | `type: structure` | MOC / index note | Navigation anchor only, never retrieved as content |
| `conversation` | `type: conversation` | Saved chat history | Agent recall only |
| `archived_fleeting` | `type: archived_fleeting` | Expired fleeting note, moved to archive | Removed from all indexes — not searchable. Retained on disk for reference. |
| `skill` | `type: skill` | Procedural instructions for the agent — templates, conventions, workflows | **Not chunked or embedded.** The indexer creates a `documents` record (for metadata queries) but skips the enrich → chunk → embed pipeline entirely. Loaded explicitly by agent runner via trigger matching (Decision 26). Never appears in any RAG context. |

If no `type:` frontmatter exists, Smart Copilot infers: notes in `/projects/` or `/journal/` → project, notes with `#fleeting` tag → fleeting, everything else → permanent. Tasks, query blocks, and calendar/event frontmatter are stripped from all notes before embedding.

**Content and enrichment hashing:** `content_hash` uses xxhash (XXH64) of the raw file bytes (full file including frontmatter YAML). `enrichment_hash` uses xxhash (XXH64) of the concatenated enrichment inputs (`title + folder + tags + sorted(backlinks) + sorted(outlinks)`). Both stored as 16-character hex strings.

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

### Decision 9 — Three-panel layout: sidebar, chat, editor
Collapsible vault sidebar (default: collapsed), chat panel (always visible), editor panel (opens on demand from citations, command palette, or agent actions). When sidebar is collapsed and no file is open, chat takes full width. Layout details in Section 26, Page 2.

### Decision 10 — Original notes kept as literature notes after Zettel conversion (default)

When a note is split into atomic Zettel notes, the original is **kept by default** as a literature note — never silently deleted. The NoteSplitterModal offers three options:

| Option | Default | Behaviour | RAG treatment |
|---|---|---|---|
| **Keep as literature note** | ✅ yes | Renamed with `type: literature` frontmatter, linked from all child Zettel notes | Citation index only — never knowledge index |
| **Archive original** | no | Moved to configurable archive folder (e.g. `/archive/`) | Same as literature note |
| **Delete original** | no | Requires explicit confirmation dialog — cannot be undone | Removed from all indexes |

Delete requires a second confirmation modal with text: "This will permanently remove the original note. Your Zettel notes will remain. This cannot be undone." Default button is Cancel.

### Decision 11 — Two RAG retrieval contexts: knowledge and citation

`search()` accepts a `context` parameter controlling which note types are eligible:

| Context | Returns | Used by |
|---|---|---|
| `knowledge` | `type: permanent` notes only | Chat, link suggestions, agent general queries |
| `citation` | `type: literature` notes only | Agent citation tool, "where did I read about X?" queries |
| `all` | All indexed note types except `skill` | Dashboard analytics, orphan detection, vault health |

Project notes are never returned by any context — only via `frontmatterQuery`. Conversation notes are never returned by `knowledge` or `citation` — only by `all` or the agent's `memoryRecall()`.

Skill notes (`type: skill`) are excluded from all RAG contexts including `all`. They are loaded deterministically by the agent's skill resolution step (see Decision 26), never retrieved probabilistically. To find skills, the agent uses a dedicated metadata query, not ragSearch.

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

Research mode sets the Web Search toggle to on as a convenience preset. The user can still turn web search off independently without exiting Research mode. **The toggle is always the authoritative control — mode is just a preset.**

Write mode requires `current_note_path`. When no file is open in the editor, RAG is disabled and the LLM operates on conversation history only.

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

**Mode library:**
- 4 built-in modes (Ask, Write, Research, Focus) — prompts are user-editable, resettable to default
- Unlimited custom mode definitions stored in user settings
- Up to 5 modes pinned to the composer picker (built-in + custom combined)
- Unpinned modes accessible via `⋯ → More modes` in the mode picker
- Built-in modes show `✎` indicator in settings when their prompt has been customised; `Reset to default` button appears alongside the indicator

### Decision 13 — Model selector via LiteLLM identifiers

Models are configured in `settings.yaml` (`llm.models` list). The client fetches available models via `GET /api/v1/models`. LiteLLM's model identifiers are the canonical IDs — format is `provider/model-name` (e.g., `anthropic/claude-sonnet-4-20250514`, `openai/gpt-4o`, `ollama/qwen3:8b`). Each model entry in config includes `id`, `display_name`, and `capabilities`.

**Display name derivation:** Use the explicit `display_name` from config when available. For auto-discovered models (e.g., Ollama models not pre-configured), derive display name by stripping the provider prefix and formatting: `ollama/qwen3:8b` → `Qwen3 8B`.

**Behaviour:**
- Sticky within the conversation — set once, persists until manually changed
- On new conversation: reverts to project default model (`llm.default_chat_model`)
- Each message records a `model_id` snapshot so history accurately shows which model produced each response
- Model picker groups by provider, shows 🔑 indicator when personal API key is active for that provider

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

**RAG treatment:** Conversation files get `type: conversation` frontmatter — never returned by `knowledge` or `citation` context. Accessible by `all` context and the agent's `memoryRecall()` tool.

**Vault export path:** Relative to the user's private vault root. Default: `{vault.base_path}/private/{username}/{chat_history.vault_export_folder}/`. With project subfolders enabled: `{vault.base_path}/private/{username}/{chat_history.vault_export_folder}/{project-name}/`.

**Conversation title auto-generation:** On first user message, if `conversation.title` is null, the backend generates a title via a lightweight LLM call (same model, max 10 tokens, purpose: `enrichment` in llm_usage tracking) and updates the conversation record. The client receives the title in the `done` SSE event payload: `{"type":"done","data":{"usage":{...},"title":"Generated title here"}}`.

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

**Embedding model is strictly admin-only — enforced at three levels:**
1. **API level:** Embedding migration and estimate endpoints require `Depends(require_admin)`. Standard users receive 403.
2. **Settings level:** The RAG tab in user Settings (Tab 4c) shows the current embedding model as read-only display text — not a dropdown. Only the Admin Dashboard (Tab 5c) shows the change-model dropdown.
3. **Config level:** `settings.yaml` `rag.embedding_model` is a server-side config that users cannot override via `user_settings`.

**Migration pipeline (6 phases):**

1. Update `system_config` → `migration_status: "running"`
2. If `alter_column=true`:
   - DROP INDEX `chunks_hnsw`, `memories_hnsw`
   - ALTER TABLE chunks ALTER COLUMN embedding TYPE vector({new_dim})
   - ALTER TABLE memories ALTER COLUMN embedding TYPE vector({new_dim})
   - **Warning:** ALTER COLUMN holds an ACCESS EXCLUSIVE lock. For vaults under 50K chunks, this typically completes in under 60 seconds. The admin UI shows an estimated lock duration before confirmation: "This will lock the database for approximately {estimated_seconds} seconds. All users will experience brief search unavailability. Proceed?" Estimation formula: ~1 second per 1,000 chunks. A create-new-column/backfill/swap pattern is deferred to a future version.
3. Re-embed all chunks in batches (100 at a time). Update embedding + embedding_model per chunk. Report progress via `GET /api/v1/admin/embeddings/status`
4. Re-embed all active memories
5. Rebuild HNSW indexes
6. Update `system_config` → new model + dimension + `migration_status: "idle"`

**Cancellation:** `POST /api/v1/admin/embeddings/cancel` stops the batch processing. Chunks already re-embedded keep their new embeddings. The admin can either resume (re-trigger migrate) or roll back (trigger migrate with the original model).

**Startup validation:** On boot, the backend reads `system_config.embedding` and compares against the actual column dimension. If they disagree AND `migration_status` is `idle`, the backend refuses to start with a clear error. If `migration_status` is `running`, the backend resumes the migration from where it left off (crash recovery).

**CLI fallback:** `smart-copilot migrate-embeddings` available as a recovery tool when the admin dashboard isn't accessible.

### Decision 21 — Two roles: admin, user
First user = admin. `require_admin` FastAPI dependency. Password reset admin-mediated.
```python
async def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
```
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

**Client enforcement:** The Electron client hides admin UI elements (Admin Dashboard tab, user management, shared API key configuration) when the logged-in user's role is `user`. This is cosmetic only — the API dependency is the real gate.

**Password reset flow (no email):** Since this is a homelab system with no email infrastructure, password reset is admin-mediated:
- Admin clicks "Reset Password" on a user row in Tab 5e
- Backend generates a random temporary password
- Dialog shows: "Temporary password for {username}: `{password}`. This will only be shown once. The user must change their password on next login."
- User's next login with the temporary password forces a password change dialog before proceeding (enforced via `must_change_password` flag on user record)

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
**SYSTEM_USER_ID:** `00000000-0000-0000-0000-000000000000` — a well-known UUID constant committed to the codebase. Used as the owner of all shared namespace content. Never logs in. RLS policies handle visibility — shared rows are visible to all users.

**Registry refresh triggers:** Backend startup, user created (`POST /api/v1/admin/users`), user deleted (`DELETE /api/v1/admin/users/{id}`).

**On user creation:** The backend creates the folder at `{vault.base_path}/private/{username}/` and registers the mapping in VaultRegistry.

**Watcher flow:** watchdog detects change → `VaultRegistry.resolve()` → `(user_uuid, namespace)` → `IndexQueue.enqueue()` → Indexer processes. Files outside any known vault (resolve returns None) are logged and skipped.

**Why not UUID folders:** Users interact with these folders directly — in Obsidian, file managers, Syncthing. `/vaults/private/alice/` is immediately understandable; a UUID path is not.

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
**Rules:**
- Every route handler that queries RLS-protected tables uses `db: AsyncSession = Depends(get_db)`
- Background tasks (indexer, Dream, scheduler) that operate on behalf of a specific user call `get_db_session(user_id)` directly
- `GET /health` and unauthenticated routes use a separate dependency without RLS context
- Admin endpoints that need cross-user visibility use a superuser connection that bypasses RLS

### Decision 24 — JWT on every API call
safeStorage for tokens. 24h access, 30d refresh. SSE: header or body. CSRF not needed (Bearer only).

**Unprotected routes (no JWT required):** `GET /health`, `POST /api/v1/auth/login`, `POST /api/v1/auth/register` (first user only — returns 403 when `allow_registration: false` and users already exist), `POST /api/v1/auth/refresh`.

**CSRF protection:** Not implemented. The API is consumed exclusively by the Electron desktop client, which uses `Authorization: Bearer` headers for every request — not cookies. CSRF attacks require cookie-based auth, so this architecture is not vulnerable. If the API is ever exposed to a browser-based client (e.g., a web-based admin dashboard), CSRF protection (e.g., `SameSite` cookies or CSRF tokens) must be added. This is documented as a constraint, not a planned feature.

### Decision 25 — MCP client: external tool integration via Model Context Protocol

Smart Copilot acts as an **MCP client** — it connects to external MCP servers and adds their tools to the agent's tool registry. The backend uses the official `mcp` Python SDK (v1.x) for connection management.

**Supported transports:**
- **stdio:** Backend spawns the MCP server as a subprocess. Best for locally-installed servers (e.g., `npx @modelcontextprotocol/server-filesystem /path`). The Docker container must have Node.js available for npm-based servers — include in Dockerfile or document as optional dependency.
- **Streamable HTTP:** Backend connects to a remote MCP server over HTTP. Best for network-accessible services. Supports authentication via headers (Bearer tokens, API keys).
- **SSE (legacy):** Supported for backward compatibility but not recommended for new integrations.

**Tool registry architecture:** The agent runner maintains a unified `ToolRegistry` that merges built-in tools with MCP-provided tools:

```python
class ToolRegistry:
    """Unified registry for built-in + MCP tools."""
    
    _builtin_tools: dict[str, BuiltinToolHandler]      # name → handler
    _mcp_sessions: dict[str, ClientSession]             # qualified_name → session
    _mcp_tool_map: dict[str, str]                       # qualified_name → original_name
    _all_schemas: list[dict]                             # OpenAI function-calling format
    _exit_stack: AsyncExitStack                          # Manages MCP connection lifecycles

    async def connect_mcp_server(self, server_name: str, config: MCPServerConfig):
        """Connect to MCP server, discover tools, add to registry."""
        # ... transport-specific connection ...
        for tool in (await session.list_tools()).tools:
            qualified = f"mcp_{server_name}_{tool.name}"
            self._mcp_sessions[qualified] = session
            self._mcp_tool_map[qualified] = tool.name
            self._all_schemas.append({
                "type": "function",
                "function": {
                    "name": qualified,
                    "description": f"[{server_name}] {tool.description}",
                    "parameters": tool.inputSchema,
                }
            })

    async def call_tool(self, name: str, arguments: dict) -> str:
        if name in self._builtin_tools:
            return await self._builtin_tools[name](**arguments)
        if name in self._mcp_sessions:
            result = await self._mcp_sessions[name].call_tool(
                self._mcp_tool_map[name], arguments
            )
            # Treat all MCP outputs as untrusted — sanitize before re-entering context
            return sanitize_tool_output(result)
        raise ValueError(f"Unknown tool: {name}")
```

**Tool namespacing:** MCP tools are prefixed as `mcp_{server_name}_{tool_name}` to prevent collisions with built-in tools. The LLM sees the qualified name; the registry resolves it to the correct session and original tool name.

**Confirmation gate:** MCP tool calls follow the same confirmation gate as built-in tools (F-AGENT-04). By default, all MCP tool calls require user confirmation. Admins can configure per-server `always_allow` lists for trusted read-only tools:

```yaml
mcp:
  servers:
    filesystem:
      command: "npx"
      args: ["-y", "@modelcontextprotocol/server-filesystem", "/data"]
      always_allow: ["read_file", "list_directory"]   # Auto-approve these tools
```

Tools not in `always_allow` trigger the `tool_confirm` SSE event and require user approval via `POST /api/v1/agent/approve`.

**Connection lifecycle:**
1. On backend startup: connect to all enabled MCP servers in config
2. Health check: periodic `ping` every 60 seconds; 3 consecutive failures → mark server as unavailable, attempt reconnection with exponential backoff (max 30s, max 5 retries)
3. On shutdown: graceful close via `AsyncExitStack.aclose()`
4. Hot reload: admin changes MCP config via UI → backend disconnects old, connects new (no restart required)

**Security:**
- All MCP tool outputs are treated as untrusted data — sanitized before re-entering LLM context
- Tool inputs validated against the JSON Schema from `list_tools()` before forwarding
- stdio servers receive only explicitly-configured environment variables (not the full process env)
- Admin can disable individual MCP servers or tools via the UI without removing configuration
- All MCP tool calls are logged to `llm_usage` table with `purpose: 'mcp_tool'` and `provider: '{server_name}'`

**Authentication for HTTP-based MCP servers:** Auth tokens are stored in the `api_keys` table with `provider = 'mcp:{server_name}'`, encrypted via Fernet (per Decision 7). The admin enters the token via Tab 5h's "Add MCP Server" dialog. At connection time, the MCP client reads the decrypted token and injects it as an `Authorization: Bearer {token}` header. Tokens are never stored in settings.yaml, environment variables, or config files.

**What MCP is NOT in Smart Copilot:** MCP does not replace the vault filesystem, the file watcher, or the indexing pipeline. The server-local vault at `/vaults/` remains the source of truth. MCP is purely an agent extension mechanism for connecting to external services.

### Decision 26 — Skills: deterministic instruction loading

Skills are markdown files in the vault with `type: skill` frontmatter. They provide procedural instructions (templates, conventions, workflows) that the agent loads deterministically before executing matching actions.

**Skill frontmatter schema:**

```yaml
---
type: skill
title: "Literature Note Template"
description: "Defines structure for literature notes created from imports"
triggers:
  tools: [captureFromURL, splitNote]      # Load when agent calls these tools
  modes: [research]                        # Load when this mode is active
  folders: [/projects/thesis/]             # Load when operating on files in these folders
  manual: true                             # User can invoke via @skill command (future)
enabled: true
priority: 10                               # Lower = higher priority (for ordering multiple matches)
---

## Instructions

When creating a literature note from an imported document:
1. Use this title format: "{Author} — {Title} ({Year})"
2. Include source URL in frontmatter...
```

**MCP tool triggers (Phase 7):** When MCP tools are available, skill triggers can reference them using the qualified name format: `mcp_{server}_{tool}`. Example: `triggers.tools: [mcp_zotero_search, captureFromURL]` matches both the MCP tool and the built-in tool. Skill authors can find available MCP tool names in Settings → Tab 4j (the skill editor shows a tool name picker when MCP is enabled).

**Namespace scoping:**
- **System skills** live in `/vaults/shared/skills/`. Owned by SYSTEM_USER_ID, visible to all users. Admin creates and maintains them.
- **User skills** live in `/vaults/private/{username}/skills/`. Owned by the user, visible only to them. Users create and modify freely.
- **Resolution order:** user skill → system skill (matching the API key resolution pattern from Decision 7). When both a user skill and a system skill match the same trigger, the user skill wins.
- **Conflict rule:** If multiple skills match the same trigger at the same scope level, they are concatenated in `priority` order (lowest number first). Total prepended skill content is capped at `agent.max_skill_tokens` (default: 2000) to avoid context overflow with local LLMs.

**Agent resolution step:** Before the agent executes a tool or begins a turn in a mode, the agent runner queries:

```sql
SELECT d.path, d.content, d.frontmatter
FROM documents d
WHERE d.note_type = 'skill'
  AND d.frontmatter->>'enabled' != 'false'
  AND (d.user_id = $current_user_id OR d.namespace = 'shared')
ORDER BY
  CASE WHEN d.user_id = $current_user_id THEN 0 ELSE 1 END,
  (d.frontmatter->>'priority')::int NULLS LAST
```

The runner then filters results client-side against the current trigger context (tool name, active mode, file path). Matched skill content is prepended to the tool-specific context or mode system prompt.

**Skills are not a new endpoint group.** Skills are documents — they are created via `POST /api/v1/vault/write`, listed via `GET /api/v1/documents?note_type=skill`, read via `GET /api/v1/documents/{id}`. No new API endpoints are needed.

**Token budget:** `agent.max_skill_tokens` (default: 2000) limits the total prepended skill content. Skills exceeding the budget are truncated with a warning in the agent's observation: "Skill content truncated at {N} tokens. Consider splitting into smaller skills."

---

## 5. Data Model & Database Schema

> **FOR AI AGENTS:** Implement exactly via Alembic. The `enrichment_hash`, RLS policies, and denormalized `messages.user_id` are deliberate — do not simplify.

> **Note on DDL ordering:** The schema below is presented in logical grouping order, not execution order. The `conversations` table references `projects(id)` which is defined later in this listing. Alembic migrations handle dependency ordering automatically. Do not execute this DDL verbatim as a single script without reordering.

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
    content TEXT NOT NULL, embedding vector(1536), embedding_model TEXT,
    source_conversation_id UUID REFERENCES conversations(id),
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

-- ═══ APSCHEDULER (auto-created) ═══
-- APScheduler's SQLAlchemyJobStore creates and manages its own table(s) automatically
-- on first run. Do NOT include in Alembic migrations — APScheduler handles DDL internally.
-- The job store table persists scheduled maintenance tasks and Dream check jobs across
-- container restarts.

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
F-CHAT-03/04, F-CHAT-06, F-EDITOR-01, F-ZETT-02/03, F-AGENT-04/05, F-MEM-03, F-SEARCH-01, F-PROJ-01, F-VAULT-01, F-ADMIN-02/03, F-BACKUP-01

**Could Have** — nice for v1.0:
F-CHAT-05, F-PLATFORM-01/02, F-INTEL-01, F-DASH-01

**Feature ID mapping (IDs not defined as full feature sections):**

| ID | Definition | Phase |
|---|---|---|
| F-BACKUP-01 | Automated backup script + restore procedure (see Section 24). QG: backup + restore tested end-to-end. | 8 |
| F-INTEL-01 | Vault intelligence features: orphan detection, link suggestions, bidirectional gap detection, smart organizer, MOC generation. Covered by F-VAULT-01 endpoints + agent tools #3–5, #15–16, #22. | 6 |
| F-DASH-01 | User Dashboard (Page 6a): My Usage, Vault Health, System Status tabs. Covered by `/usage/*` and `/status/*` endpoints. | 6 |

**Removed from MoSCoW** (previously listed but redundant with other feature IDs or not scoped for v1.0):
- F-RAG-03, F-AGENT-06 through F-AGENT-11, F-INTEL-02/03, F-SEARCH-02/03, F-PLATFORM-03/04 — these IDs were listed in error. The functionality they covered is either already captured by other feature IDs (e.g., agent tools #6–22 are covered by F-AGENT-01/02/03) or is out-of-scope for v1.0. Do not implement features under these IDs.

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
    reasoning_effort: str | None = None          # 'low' | 'medium' | 'high' — only sent to models that support it; ignored otherwise
    system_prompt_override: str | None = None
    web_search_enabled: bool = False
    relevant_note_enabled: bool = True
    agent_enabled: bool = False
    # Special commands (set by Lexical client-side detection)
    zettel_capture: bool = False              # @zettel detected — triggers Zettel capture workflow
    access_token: str | None = None  # SSE fallback
```

**Backend processing flow:**
1. Validate conversation_id belongs to current user
2. Append user message to messages table (user_id denormalized)
3. Resolve mode_id → system prompt; apply system_prompt_override if non-empty
4. If relevant_note_enabled: ragSearch scoped by mode's rag_scope
4a. Resolve wikilink graph seed: if `current_note_path` is set, look up its `documents.id` via `(user_id, namespace, path)` as `seed_doc_id` for the wikilink graph CTE in Decision 2. If `current_note_path` is null and the conversation has prior assistant messages with citations, use the highest-scored cited document from the most recent message as the seed (opportunistic graph proximity). If neither condition is met, `seed_doc_id` is null and the wikilink proximity signal in RRF is zeroed — the query runs as a 2-signal hybrid (vector + BM25 only). This fallback is intentional and acceptable for first-message queries with no file context.
5. If Write mode + current_note_path: RAG restricted to that document. No path → RAG disabled
6. If file_references non-empty: fetch those documents as additional context
7. Resolve model → LiteLLM identifier, resolve API key (user → shared → error)
8. Call LiteLLM acompletion() with streaming. If reasoning_effort is set and the model supports it (checked via model capabilities in config), pass it as a provider-specific parameter. If the model doesn't support it, ignore silently.
9. Stream tokens via SSE, record assistant message to DB on completion
10. If agent_enabled: run AgentRunner with tool results streamed as SSE events

### F-CHAT-02: Chat History CRUD

**US-2.7:** As a user, I want to manage my conversation history.
- AC1: `GET /api/v1/conversations` — paginated, searchable, date filter
- AC2: `PATCH /api/v1/conversations/{id}` — update title, model, mode
- AC3: Delete behavior: saved to vault → silent DB delete; not saved → warning modal
- AC4: `POST /api/v1/conversations/{id}/regenerate` — delete last assistant message, re-run
- AC5: On first user message, if `conversation.title` is null, backend generates a title via LLM (max 10 tokens, purpose: `enrichment`). Title returned in `done` SSE event payload.

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
- AC5: Built-in modes show `✎` indicator in Settings when their system prompt has been modified from default. "Reset to default" button appears alongside the indicator.

### F-CHAT-04: Model Selector (Should Have)

**US-2.11:** As a user, I want to choose and switch AI models.
- AC1: Grouped by provider; sticky per conversation
- AC2: New conversation → project default model
- AC3: Each message records model_id snapshot
- AC4: 🔑 indicator when personal key active

### F-CHAT-06: @web Client-Side Detection

**US-2.13:** As a user, I want to type `@web` as a shortcut for web search.
- AC1: Lexical detects `@web` as a special command prefix (like @mentions)
- AC2: Client strips `@web` from the message text
- AC3: Client sets `web_search_enabled: true` in ChatCompletionRequest
- AC4: Web Search toggle visually flips to ON as confirmation
- AC5: `@web` is a convenience shortcut — equivalent to manually enabling the toggle

### F-SETTINGS-01: User Settings CRUD

**US-2.12:** As a user, I want to customize my preferences.
- AC1: `GET /api/v1/settings` returns effective (user override or server default)
- AC2: `PUT /api/v1/settings` updates overrides
- AC3: Server-only settings not overridable: `server.*`, `vault.*`, `rag.embedding_model`, `llm.local_endpoints`, `llm.dream_model`, `auth.*`, `memory.dream.*`, `chat_history.max_conversations_per_user`
- AC4: All other settings user-overridable via `user_settings` JSONB

---

## 9. Phase 3 — Editor + Zettelkasten (Weeks 5–6)

**Backend:** NoteSplitter, ZettelNoteBuilder, document import (PDF/DOCX/HTML), web clipper (Jina Reader + nh3), vault write/move/split endpoints, LinkRefactorer, OperationLog.

**Frontend:** Collapsible vault sidebar (tree view + list view, react-complex-tree), Tiptap split-pane editor, react-resizable-panels, NoteSplitterModal, ZettelNotePreviewModal, Chat Settings popover + More Options drawer.

**Quality gate:** User can browse vault in sidebar, open notes in Tiptap editor, import a PDF, split into Zettel notes. Write mode scopes RAG to the open file via `current_note_path`. Sidebar tree reflects vault structure and updates on file changes.

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
- AC1: Lexical detects `@zettel` as a special command prefix, sets `zettel_capture: true` in ChatCompletionRequest, and passes full message text (including `@zettel`) to the LLM
- AC2: Backend, on seeing `zettel_capture: true`, appends the Zettel Capture Prompt from Section 16.5 (System Prompt Templates) to the system prompt. Section 16.5 is the authoritative source for all prompt text.
- AC3: ZettelNotePreviewModal presents the LLM's output for user editing before save
- AC4: On accept, backend creates note with frontmatter (`id`, `type: permanent`, `source: "[[conversation title]]"`, `created`, suggested tags) and indexes immediately

---

## 10. Phase 4 — Agent + Memory (Weeks 7–8)

**Backend:** AgentRunner (plan-execute-observe, 22 tools), confirmation gate, client-cooperative tool protocol (captureFromClipboard with SSE round-trip), memory extraction/storage/recall, Memory Dream consolidation (4 phases, advisory lock), APScheduler, skill resolution engine (trigger matching, namespace scoping, token budgeting). Endpoints: `POST /api/v1/agent/client-response`, `POST /api/v1/agent/approve` (2 agent endpoints), all 12 Memory endpoints (CRUD + semantic search + dream + import/export), `POST /api/v1/vault/organize/undo` (requires OperationLog).

**Frontend:** Agent tool banner, memory panel, confirmation modals, SSE client_request handler, Research mode wiring, Memory management tab, Skills management section in Settings (Tab 4j).

### F-AGENT-01: Agent Runner

**US-4.1:** As a user in Research mode, I want the agent to autonomously perform multi-step reasoning.
- AC1: ReAct-style loop: Thought → Action → Observation → repeat
- AC2: Max 10 tool calls per turn (configurable `agent.max_tool_calls_per_turn`)
- AC3: Streams partial results via SSE (tool_start, tool_result, tool_confirm events)
- AC4: All mode-appropriate tools available (see per-mode tool lists below)
- AC5: At max_tool_calls: emit message "I've reached the maximum number of actions (10) for this turn." Client shows [Continue] (resets counter, resumes loop) and [Stop] (ends turn)
- AC6: On tool failure: error returned as tool observation so LLM can retry or adapt strategy
- AC7: `parallel_tool_calls: false` — forces sequential execution for confirmation flow

**Loop structure:**

```
1. Build system prompt with mode-specific tool definitions
2. Send messages + tool definitions to LLM via LiteLLM
3. LLM responds with either:
   a. Text content → stream to client via SSE, end turn
   b. Tool call(s) → check if confirmation required
      - Auto-approve tool → execute, append result as observation, goto 2
      - Write tool → emit tool_confirm SSE event, pause loop, await /api/v1/agent/approve
        - Approved → execute, append result, resume loop
        - Rejected → append "User declined. Reason: {reason}." as observation, resume loop
4. Loop continues until LLM emits text-only response OR tool_call_count >= max_tool_calls
5. At max_tool_calls → summarize progress, offer continuation
```

### Skill Resolution

Before the agent executes a tool call or begins a turn, the agent runner resolves matching skills:

1. Query all `type: skill` documents accessible to the current user (own + shared namespace)
2. Filter by trigger match: does the skill's `triggers.tools` list include the current tool? Does `triggers.modes` include the active mode? Does `triggers.folders` match the file being operated on?
3. Order by scope (user before system) then by `priority` (lowest first)
4. Concatenate matched skill content up to `agent.max_skill_tokens` (default: 2000)
5. Prepend to the tool's context (for tool triggers) or the mode's system prompt (for mode triggers)

Skill resolution is transparent to the LLM — skills appear as additional system instructions, not as a separate tool call. Skills are cached in memory per user session and invalidated when the file watcher detects changes to files with `type: skill` frontmatter.

**Per-mode tool filtering (hardcoded in v1.0):**

| Mode | Tools available | Tool numbers |
|---|---|---|
| **Ask** | Read-only only | #1–6 |
| **Write** | ragSearch, vaultRead, memoryRecall (scoped to current note) | #1, #2, #6 |
| **Research** | All 22 tools | #1–22 |
| **Focus** | Read-only + frontmatterQuery (scoped to project) | #1–7 |
| **Custom** | `agent_tools: true` → all 22; `agent_tools: false` → #1–6 | Configurable |

**Context management within a turn:** The agent sees all previous tool results in its context window for the current turn. Each tool result is formatted as:

```
[Tool: ragSearch] Input: {"query": "neural networks", "context": "knowledge"}
[Result]: 5 results found. Top: "Backpropagation basics" (score: 0.91), ...
```

When accumulated tool results exceed ~4,000 tokens, older results are summarized (keeping the 3 most recent in full) to prevent context overflow.

**Tool definitions:** All 22 tools × ~200 tokens each ≈ 4,400 tokens of system prompt overhead. Prompt caching (OpenAI automatic, Anthropic `cache_control`, Gemini automatic) reduces the per-call cost to near zero. Tool definitions placed as a static prefix at the start of every request to maximize cache hits.

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
- AC5: Import duplicate detection: >95% cosine similarity to existing active memory → flag with three options: **Skip** (don't import this memory), **Import anyway** (create duplicate), **Replace existing** (archive old, import new)

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

**Backend:** Web search engine (DuckDuckGo, Jina, Wikipedia free; Tavily/Brave/SerpAPI paid), CrossReferenceEngine, ProjectManager (folder/tag scoping), frontmatterQuery tool. Endpoints: `POST /api/v1/web/search`, `POST /api/v1/web/fetch` (2 web search endpoints), `GET/POST/PATCH/DELETE /api/v1/projects` (4 project endpoints).

**Frontend:** Project switcher, project creation/edit modal, web search toggle, @web trigger, Focus mode scoping.

**Quality gate:** Projects scope RAG correctly. Web search returns results and cross-references vault.

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
- AC6: `POST /api/v1/vault/reindex` — user-scoped full reindex of own namespace. Rate-limited: max 1 per hour per user. Returns 202 Accepted.

### F-ADMIN-01: Admin Dashboard

**US-6.2:** As an admin, I want a comprehensive management dashboard.
- AC1: 8 tabs: Overview, LLM Usage, Storage, API Keys, Users, Memory Dream, System, MCP Servers (Phase 7)
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
- Vault export — complete implementation of `POST /api/v1/conversations/{id}/export` (endpoint defined in Phase 2 Chat group, deferred to Phase 7)
- Image understanding (vision models)
- Settings UI polish (all 10 tabs)
- User API key management with provider status
- MCP client support: `mcp` Python SDK integration, ToolRegistry (unified built-in + MCP tools), stdio + Streamable HTTP transports, admin UI for server configuration (Tab 5h), health checks + auto-reconnection, 5 new admin endpoints
- Obsidian export: "Export to Obsidian" buttons in editor toolbar, document list context menu, and conversation header. Electron IPC for native folder dialog + batch file writing with progress. Markdown output preserves frontmatter and wikilinks in Obsidian-compatible format.

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

> **FOR AI AGENTS:** Implement these endpoints exactly as specified. The OpenAPI spec auto-generated from FastAPI is the runtime source of truth, but these definitions are the design spec. Total: ~98 endpoints across 14 route groups.

### Auth (6 endpoints — Phase 1)

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/auth/register` | None | First user → admin. Returns 403 when registration disabled and users exist |
| POST | `/api/v1/auth/login` | None | Returns access + refresh tokens |
| POST | `/api/v1/auth/refresh` | None | Refresh token → new pair |
| POST | `/api/v1/auth/change-password` | JWT | Requires current password |
| GET | `/api/v1/auth/me` | JWT | Returns current user profile: id, username, email, role, created_at. Used by Tab 4h (Account) and to refresh user data after admin changes. |
| PATCH | `/api/v1/auth/me` | JWT | Update current user's profile (email only for v1.0). Returns updated user object. |

### Chat (8 endpoints — Phase 2; export endpoint deferred to Phase 7)

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/chat/completions` | JWT | SSE streaming with RAG + citations |
| GET | `/api/v1/conversations` | JWT | Paginated, search, date filter |
| GET | `/api/v1/conversations/{id}` | JWT | With messages |
| POST | `/api/v1/conversations` | JWT | Create conversation |
| PATCH | `/api/v1/conversations/{id}` | JWT | Update title, model, mode |
| DELETE | `/api/v1/conversations/{id}` | JWT | Delete with confirmation logic |
| POST | `/api/v1/conversations/{id}/regenerate` | JWT | Delete last assistant message, re-run |
| POST | `/api/v1/conversations/{id}/export` | JWT | Export to vault as markdown. **Ships in Phase 7** — depends on vault write pipeline and Tiptap editor. Endpoint stub may exist in Phase 2 (returns 501) but full implementation deferred. |

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

### Vault (13 endpoints — Phases 2, 3, 4, 6)

| Method | Path | Auth | Phase | Notes |
|---|---|---|---|---|
| POST | `/api/v1/vault/write` | JWT | 3 | Create or update file |
| POST | `/api/v1/vault/move` | JWT | 3 | Move + update wikilinks |
| POST | `/api/v1/vault/split` | JWT | 3 | Split into atomic Zettel |
| GET | `/api/v1/vault/orphans` | JWT | 6 | Orphan notes list |
| GET | `/api/v1/vault/hubs` | JWT | 6 | Most-connected notes |
| GET | `/api/v1/vault/health` | JWT | 6 | Composite health score |
| GET | `/api/v1/vault/graph` | JWT | 6 | Nodes + edges for Cytoscape |
| GET | `/api/v1/vault/index/events` | JWT | 6 | User's recent index events |
| GET | `/api/v1/vault/links/suggestions/{doc_id}` | JWT | 6 | Link suggestions for a note |
| POST | `/api/v1/vault/organize` | JWT | 6 | Dry run suggestions (SmartOrganizer) |
| POST | `/api/v1/vault/organize/apply` | JWT | 6 | Apply organization plan |
| POST | `/api/v1/vault/organize/undo` | JWT | 4 | Undo last organization (requires OperationLog from F-AGENT-05) |
| POST | `/api/v1/vault/reindex` | JWT | 2 | Trigger full reindex of the current user's namespace only. Returns 202 Accepted with task status. Rate-limited: max 1 per hour per user. |

### Graph Visualization Response Schema

`GET /api/v1/vault/graph` returns the wikilink graph in native Cytoscape.js format.

**Query parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `namespace` | string | `all` | Filter: `private`, `shared`, or `all` |
| `note_type` | string | `all` | Filter: `permanent`, `literature`, etc. Comma-separated for multiple |
| `seed_doc_id` | UUID | none | If set, return only nodes within `max_hops` of this document (ego-graph) |
| `max_hops` | int | 3 | Only used with `seed_doc_id` |
| `max_nodes` | int | 500 | Cap on returned nodes. Highest `incoming_count` nodes kept when truncated |
| `min_links` | int | 0 | Exclude nodes with fewer than N total links (hides isolates) |

**Response body:**

```json
{
  "nodes": [
    {
      "data": {
        "id": "doc-uuid-1",
        "label": "Backpropagation basics",
        "note_type": "permanent",
        "namespace": "private",
        "is_orphan": false,
        "incoming_count": 5,
        "outgoing_count": 3,
        "word_count": 247,
        "folder": "/concepts/ml/",
        "updated_at": "2025-02-14T09:30:00Z"
      }
    }
  ],
  "edges": [
    {
      "data": {
        "id": "link-uuid-1",
        "source": "doc-uuid-1",
        "target": "doc-uuid-2"
      }
    }
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

The `nodes` and `edges` arrays are in native Cytoscape.js format — the client passes them directly to `cy.add()` without transformation. `meta.truncated` is true when `max_nodes` cap was reached.

**Why `max_nodes: 500` default:** Cytoscape.js Canvas renderer handles < 1,000 elements smoothly. At 5,000 nodes, rendering slows without WebGL. The default keeps the UI responsive. Users exploring the full graph can increase the limit or use `seed_doc_id` for focused neighborhood exploration.

**Client-side styling** (no additional backend work needed):
- **Hub scaling:** `mapData(incoming_count, 0, max, 12, 60)` on node width/height
- **Orphan highlighting:** `node[?is_orphan]` → dashed border, reduced opacity
- **Note type shapes:** permanent=ellipse, literature=rectangle, structure=diamond
- **Community coloring:** Computed client-side via Cytoscape.js Louvain extension, or normalized-degree hub_score proxy in a future version

**Recommended layout:** fCoSE (force-directed with spectral initialization) with `quality: 'draft'` for initial render, `packComponents: true` for disconnected subgraphs.

### Agent (2 endpoints — Phase 4)

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/agent/client-response` | JWT | Client responds to client_request SSE event |
| POST | `/api/v1/agent/approve` | JWT | Approve or reject a pending write tool confirmation |

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

### User Settings (8 endpoints — Phase 2)

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

### Admin (26 endpoints — Phase 1 users, Phase 2 keys, Phase 6 rest, Phase 7 MCP)

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
| GET | `/api/v1/admin/mcp/servers` | Admin | List configured MCP servers with status (connected/disconnected/error) and discovered tools |
| POST | `/api/v1/admin/mcp/servers` | Admin | Add or update an MCP server configuration |
| DELETE | `/api/v1/admin/mcp/servers/{name}` | Admin | Remove an MCP server |
| POST | `/api/v1/admin/mcp/servers/{name}/toggle` | Admin | Enable/disable a server without removing config |
| POST | `/api/v1/admin/mcp/servers/{name}/reconnect` | Admin | Force reconnect to a server |

### Health (1 endpoint — Phase 1)

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/health` | None | Returns setup_required flag when no users |

### Error Response Schema (all endpoints)

All error responses use a standard format:

```json
{
  "detail": "Human-readable error message",
  "code": "MACHINE_READABLE_CODE"
}
```

| HTTP Status | Code | Usage |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Request body validation failed |
| 401 | `UNAUTHORIZED` | Missing or invalid JWT |
| 403 | `FORBIDDEN` | Insufficient role (e.g., user accessing admin endpoint) |
| 404 | `NOT_FOUND` | Resource does not exist or not visible via RLS |
| 409 | `CONFLICT` | Resource already exists (e.g., duplicate username) |
| 429 | `RATE_LIMITED` | Per-user rate limit exceeded. Body includes `retry_after_seconds` |
| 500 | `INTERNAL_ERROR` | Unexpected server error |

---

## 16. SSE Streaming Protocol

**Authentication:** The POST request body may include `access_token` as a fallback when header injection on streaming requests is inconvenient. The backend validates the token from either the `Authorization: Bearer` header or the body field before opening the stream.

```
data: {"type":"status","data":{"description":"Searching knowledge base...","done":false}}

data: {"type":"citations","data":{"sources":[{"doc_id":"...","path":"...","title":"...","score":0.92,"excerpt":"..."}]}}

data: {"type":"token","data":{"content":"Based on"}}
data: {"type":"token","data":{"content":" your notes"}}

data: {"type":"tool_start","data":{"tool":"ragSearch","input":{"query":"neural networks"}}}
data: {"type":"tool_result","data":{"tool":"ragSearch","elapsed_ms":340,"result_count":5}}

data: {"type":"tool_confirm","data":{"tool":"vaultWrite","input":{"path":"/notes/new.md","content":"..."},"description":"Create new note: new.md","call_id":"uuid"}}

data: {"type":"client_request","data":{"request_id":"uuid","action":"read_clipboard","max_payload_bytes":5242880}}

data: {"type":"client_request","data":{"request_id":"uuid","action":"open_editor","path":"/notes/example.md"}}

data: {"type":"notification","data":{"title":"3 orphan notes detected","body":"Run cleanOrphans to review.","severity":"info"}}

data: {"type":"done","data":{"usage":{"prompt_tokens":1200,"completion_tokens":450,"cost_usd":0.0034},"title":"Auto-generated title"}}
```

**Event types:** `status`, `citations`, `token`, `tool_start`, `tool_result`, `tool_confirm`, `client_request`, `notification`, `done`

**`tool_confirm`** — emitted when the agent requests a write operation requiring user approval. The client shows a confirmation modal. User response sent to `POST /api/v1/agent/approve` with `call_id` and `approved: true/false`.

**`client_request`** — emitted when the agent needs data or action from the Electron client. The `action` field determines client behavior:
- `read_clipboard` — client reads system clipboard, normalizes content, and responds via `POST /api/v1/agent/client-response` within 10 seconds. See captureFromClipboard protocol in Section 17.
- `open_editor` — client opens the specified `path` in the Tiptap editor panel (or focuses it if already open). **Fire-and-forget: no response expected.** The client should ignore the `request_id` for this action. If the file does not exist, the client shows a toast notification: "File not found: {path}".

**`notification`** — emitted by the proactive background agent for vault health alerts, maintenance results, and indexing completion. Severity levels: `info`, `warning`, `action_required`. Electron client renders as system notifications (Notification API) when the main window is not focused, or as toast notifications when it is.

**`done`** — includes `title` field when the conversation title was auto-generated on first message (null otherwise).

**Citation markers scoping:** Citation markers (`[1]`, `[2]`) are scoped per-message. Each assistant response cites only the RAG sources retrieved for that specific user message. Previous messages' citations are not re-referenced.

---

## 16.5. System Prompt Templates

> **FOR AI AGENTS:** These are the default system prompts. Mode prompts are user-editable via Settings Tab 4d. The citation instruction block is always appended regardless of mode.

### Base System Prompt (prepended to all modes)

```
You are Smart Copilot, an AI knowledge assistant that helps users manage their Zettelkasten. You have access to the user's note vault via RAG search. When answering questions, draw on relevant notes from the vault and cite your sources.

Rules:
- When you reference information from the user's notes, cite the source using numbered markers: [1], [2], etc.
- Each marker corresponds to a source note provided in the context below.
- Only cite notes actually provided in your context — never fabricate citations.
- If no relevant notes are found, say so and answer from general knowledge.
- Be concise and direct. The user is a knowledge worker, not a novice.
```

### Citation Instruction Block (always appended after RAG context)

```
The following notes were retrieved from the user's vault. Reference them using [N] markers in your response.

{for each source}
[{N}] {note.title} ({note.path})
---
{chunk.content}
---
{/for each}

Cite sources inline when you reference specific information from them. Multiple citations like [1][3] are fine. Do not cite sources you don't actually reference.
```

### Mode-Specific Prompts

**Ask mode (default):**

```
Answer the user's question using their vault notes as context. If the vault contains relevant information, cite it. If not, answer from general knowledge and note that the answer isn't grounded in their notes.
```

**Write mode:**

```
You are helping the user draft or edit content in their current note. Focus exclusively on the writing task. Do not search broadly — use only the current note's content and conversation history as context. Be a writing partner: suggest improvements, continue drafts, restructure paragraphs, and refine language.
```

**Research mode:**

```
You are conducting research on behalf of the user. Use all available tools: search the vault, search the web, read notes, and create new notes as needed. Think step by step. Explain your reasoning as you go. When you find relevant information, synthesize it into a clear answer with citations from both vault notes and web sources.
```

**Focus mode:**

```
Answer the user's question using only notes within the active project scope. Do not search outside the project's folders and tags. If the answer requires information outside the project, say so rather than guessing.
```

### Zettel Capture Prompt (appended when `zettel_capture: true`)

```
The user has requested a Zettel capture. Distill the relevant insight from this conversation into a single atomic note. Output your response in this exact format:

**Title:** [descriptive title — a complete thought, not just a topic]
**Body:** [the atomic idea in 1-3 paragraphs — one idea only, self-contained]
**Tags:** [3-5 relevant tags as comma-separated list]

Do not include frontmatter — the system adds it automatically. The title should be specific enough to distinguish this note from others on the same topic.
```

### Agent Tool Selection Prompt (prepended when `agent_enabled: true`)

```
You have access to the following tools. Use them to accomplish the user's request.

Rules for tool use:
- Call tools one at a time (sequential execution).
- Stop calling tools and provide your final answer once you have enough information.
- Do not make redundant tool calls (same tool with same arguments).
- For write operations (creating files, moving files, organizing), the user will be asked to confirm before execution.
- If a tool fails, read the error message and try a different approach.
- If you reach the maximum number of tool calls, summarize your progress and findings so far.
```

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
| 7 | `frontmatterQuery(field, op, value)` | Query by frontmatter. Executes as a parameterized SQL query on the agent runner's authenticated DB session. No LLM invocation. Supports operators: `eq`, `contains`, `gt`, `lt`, `gte`, `lte`, `in`, `exists`. Returns matching document metadata (id, path, title, note_type, frontmatter). Internal only — no REST endpoint. |
| 8 | `reconcileIndex()` | Fix filesystem/DB drift |
| 9 | `scheduleMaintenance(task, schedule)` | Register tasks within admin ceiling; persisted via APScheduler SQLAlchemyJobStore |
| 10 | `notifyUser(title, body)` | Send notification via SSE |
| 11 | `openInEditor(path)` | Emits `client_request` SSE event with `action: "open_editor"`. Fire-and-forget — no client response expected. |

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

**`scheduleMaintenance` operational notes:**
- No REST endpoint exposes the APScheduler job list in v1.0. Scheduled tasks are agent-internal and not visible in any UI.
- **Admin recovery:** If a scheduled task needs to be inspected or removed manually, admins can query APScheduler's internal tables directly via `psql` against the application database. APScheduler's table name defaults to `apscheduler_jobs`.
- **Candidate for future phase:** A read-only admin endpoint (`GET /api/v1/admin/scheduled-tasks`) listing active jobs with next-run times would improve observability. Not scoped for v1.0.

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

### Tool invocation: pipeline vs agent loop

Tools are invoked in two distinct ways:

1. **Pipeline invocation (always active):** The chat completion pipeline calls `ragSearch` and `memoryRecall` internally to build RAG context for every message, regardless of mode or `agent_enabled` flag. This is not visible as a tool call to the user — it's part of how the system builds context. This is why all modes benefit from hybrid search even when `agent_tools: false`.

2. **Agent loop invocation (Research mode and custom modes with `agent_tools: true`):** The LLM explicitly calls tools via the ReAct loop (Thought → Action → Observation). Tool calls are visible in the chat as `tool_start` / `tool_result` SSE events. Only modes with `agent_tools: true` and `agent_enabled: true` in the request activate the agent loop.

The per-mode tool availability table below applies only to **agent loop invocation** — which tools the LLM can explicitly call when the agent is active. For modes where `agent_tools: false` (Ask, Write, Focus by default), the agent loop is not active, but pipeline invocation of ragSearch and memoryRecall still occurs transparently.

### Per-Mode Tool Availability (hardcoded v1.0)

| Mode | Available tools | Tool numbers |
|---|---|---|
| **Ask** | ragSearch, vaultRead, detectOrphans, suggestLinks, analyzeNote, memoryRecall | #1–6 |
| **Write** | ragSearch, vaultRead, memoryRecall (RAG scoped to current note) | #1, #2, #6 |
| **Research** | All 22 tools | #1–22 |
| **Focus** | All read-only tools + frontmatterQuery (RAG scoped to project) | #1–7 |
| **Custom** | `agent_tools: true` → all 22; `agent_tools: false` → read-only only (#1–6) | Configurable |

Tool lists are hardcoded per mode in v1.0. Custom per-mode tool selection is deferred to a future version.

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

### Chunking Strategy

**Note type gating:** The indexer checks `note_type` before chunking. Types `archived_fleeting` and `skill` skip the enrich → chunk → embed pipeline entirely — the `documents` record is created/updated (with frontmatter, path, content_hash) but no `chunks` rows are produced. All other note types proceed through the full pipeline.

**Atomic notes (≤ `single_chunk_threshold` tokens):** Embedded as a single chunk. No splitting. The enrichment prefix is prepended, and the entire note is embedded as one unit. This covers ~90% of Zettelkasten permanent notes.

**Literature notes and long notes (> `single_chunk_threshold` tokens):** Split using recursive character splitting with markdown-aware separators:

- **Separator hierarchy:** `\n## ` → `\n### ` → `\n\n` → `\n- ` → `\n` → `. ` → ` `
- **Chunk size:** 512 tokens (configurable `rag.chunking.chunk_size_tokens`)
- **Overlap:** 64 tokens (~12.5%, configurable `rag.chunking.chunk_overlap_tokens`)
- **Minimum chunk:** 50 tokens — shorter fragments merge into the previous chunk
- **Code blocks and blockquotes** are never split mid-block

Each chunk receives the same contextual enrichment prefix. For literature notes, chunks also receive a section header trail (e.g., `Section: Chapter 3 > Key Findings`) when headers are present.

**Frontmatter handling:** YAML frontmatter is stripped before chunking. Frontmatter fields are used only for contextual enrichment (prepended separately) and metadata columns (for filtering). `[[Wikilinks]]` in note body are resolved to plain-text titles before embedding — the double-bracket syntax adds no semantic value to embeddings.

**Configurable parameters** (admin-configurable via Admin Tab 5c — changes trigger full reindex with confirmation):

```yaml
rag:
  chunking:
    chunk_size_tokens: 512
    chunk_overlap_tokens: 64
    min_chunk_tokens: 50
    respect_boundaries: paragraph  # paragraph | sentence | none
    frontmatter_handling: strip    # strip | include_first_chunk
    single_chunk_threshold: 600
```

### Cascading Re-enrichment

`documents.content_hash` uses xxhash (XXH64) of the raw file bytes (full file including frontmatter YAML), stored as 16-character hex string. `documents.enrichment_hash` uses xxhash (XXH64) of the concatenated enrichment inputs (`title + folder + tags + sorted(backlink_titles) + sorted(outlink_titles)`), stored as 16-character hex string.

**Flow on file change:**
1. Compute content_hash
2. Both unchanged → skip
3. content_hash changed → full re-process (parse, enrich, chunk, embed)
4. content_hash same, enrichment_hash changed → re-enrich + re-embed existing chunks

**Cascade:** After indexing any document, check if wikilinks changed. If yes, mark linked documents for enrichment_hash recalculation. **Depth limited to 1 hop.**

### Chunk Replacement

Atomic delete-and-recreate within SAVEPOINT (see code in Phase 2 section). If embedding fails midway, DELETE rolls back and old chunks restored. Note is never unsearchable.

For enrichment-only updates: update existing rows' `enriched_content` and `embedding` in place.

### Hybrid RAG Query Reference

The following SQL demonstrates the complete hybrid search query combining all three retrieval signals via Reciprocal Rank Fusion. This is the core of `rag/queries.py`.

```sql
-- Hybrid RAG search: vector + BM25 + wikilink graph proximity
-- Combined via Reciprocal Rank Fusion (RRF) with k=60
-- RLS automatically scopes to current user's private + shared data

WITH
-- Signal 1: Vector cosine similarity (weight 0.5)
vector_ranked AS (
    SELECT
        c.document_id,
        c.content,
        c.enriched_content,
        1 - (c.embedding <=> $1::vector) AS cosine_score,
        ROW_NUMBER() OVER (ORDER BY c.embedding <=> $1::vector ASC) AS rank
    FROM chunks c
    JOIN documents d ON d.id = c.document_id
    WHERE d.note_type = ANY($3::text[])  -- note type filter (e.g., {'permanent'} for knowledge context)
    ORDER BY c.embedding <=> $1::vector ASC
    LIMIT $2  -- top_k candidates (default: 50, wider than final top_k for fusion)
),

-- Signal 2: BM25 keyword search (weight 0.3)
bm25_ranked AS (
    SELECT
        c.document_id,
        c.content,
        c.enriched_content,
        ts_rank_cd(c.content_tsvector, websearch_to_tsquery('english', $4)) AS bm25_score,
        ROW_NUMBER() OVER (
            ORDER BY ts_rank_cd(c.content_tsvector, websearch_to_tsquery('english', $4)) DESC
        ) AS rank
    FROM chunks c
    JOIN documents d ON d.id = c.document_id
    WHERE c.content_tsvector @@ websearch_to_tsquery('english', $4)
      AND d.note_type = ANY($3::text[])
    ORDER BY bm25_score DESC
    LIMIT $2
),

-- Signal 3: Wikilink graph reachability (weight 0.2, binary scoring)
-- Returns all documents reachable within max_hops from seed document
graph_reachable AS (
    SELECT DISTINCT doc_id FROM (
        WITH RECURSIVE graph_hop AS (
            -- Hop 1: direct forward links from seed
            SELECT target_doc AS doc_id, 1 AS hops
            FROM wikilinks
            WHERE source_doc = $5::uuid  -- seed_doc_id (context note)
              AND target_doc IS NOT NULL

            UNION

            -- Hop 2+: follow links outward
            SELECT w.target_doc, gh.hops + 1
            FROM graph_hop gh
            JOIN wikilinks w ON w.source_doc = gh.doc_id
            WHERE gh.hops < $6  -- wikilink_max_hops (default: 3)
              AND w.target_doc IS NOT NULL
              AND w.target_doc != $5::uuid
        )
        SELECT doc_id FROM graph_hop
    ) reachable
),

-- Reciprocal Rank Fusion
rrf_scores AS (
    -- Vector signal
    SELECT document_id, 0.5 / (60.0 + rank) AS rrf_score, 'vector' AS source
    FROM vector_ranked

    UNION ALL

    -- BM25 signal
    SELECT document_id, 0.3 / (60.0 + rank) AS rrf_score, 'bm25' AS source
    FROM bm25_ranked

    UNION ALL

    -- Graph signal: all reachable docs ranked by their best vector score (if present)
    -- Documents not in vector results but graph-reachable still get a boost
    SELECT gr.doc_id AS document_id,
           0.2 / (60.0 + COALESCE(vr.rank, 100)) AS rrf_score,
           'graph' AS source
    FROM graph_reachable gr
    LEFT JOIN vector_ranked vr ON vr.document_id = gr.doc_id
),

-- Aggregate: sum RRF scores per document
combined AS (
    SELECT
        document_id,
        SUM(rrf_score) AS final_score,
        BOOL_OR(source = 'vector') AS has_vector,
        BOOL_OR(source = 'bm25') AS has_bm25,
        BOOL_OR(source = 'graph') AS has_graph
    FROM rrf_scores
    GROUP BY document_id
    ORDER BY SUM(rrf_score) DESC
    LIMIT $7  -- final top_k (default: 10)
)

-- Final result with document metadata
SELECT
    c.document_id,
    d.path,
    d.title,
    d.note_type,
    d.folder,
    d.tags,
    c.final_score,
    c.has_vector,
    c.has_bm25,
    c.has_graph,
    -- Return the best matching chunk content for each document
    (SELECT content FROM chunks ch
     WHERE ch.document_id = c.document_id
     ORDER BY ch.embedding <=> $1::vector ASC
     LIMIT 1) AS best_chunk_content,
    (SELECT enriched_content FROM chunks ch
     WHERE ch.document_id = c.document_id
     ORDER BY ch.embedding <=> $1::vector ASC
     LIMIT 1) AS best_chunk_enriched
FROM combined c
JOIN documents d ON d.id = c.document_id
ORDER BY c.final_score DESC;
```

**Parameters:**
- `$1`: Query embedding vector (from `aembedding(query_text)`)
- `$2`: Candidate pool size (default: 50 — wider than final top_k)
- `$3`: Allowed note types array (e.g., `{'permanent'}` for knowledge, `{'literature'}` for citation)
- `$4`: Raw query text (for BM25 `websearch_to_tsquery`)
- `$5`: Seed document UUID (context note for graph proximity; NULL if no context note)
- `$6`: Max graph hops (default: 3)
- `$7`: Final top_k results (default: 10)

**When `$5` (seed_doc_id) is NULL:** The graph_reachable CTE returns zero rows, and only vector + BM25 signals contribute to scoring. This happens when: no file is open in the editor, the user is in a new conversation with no context, or the mode doesn't provide a seed.

**RRF k parameter (60):** Standard value from the original RRF paper (Cormack et al., 2009). Higher k reduces the impact of rank position differences; lower k amplifies them. 60 is a safe default.

---

## 22. Server Configuration Reference

File: `/config/settings.yaml` — only non-secret config. API keys are in the database.

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
  hybrid_weights: { vector: 0.5, bm25: 0.3, wikilink: 0.2 }
  context_enrichment: true
  top_k: 10
  wikilink_max_hops: 3
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
  max_skill_tokens: 2000             # Max total tokens from matched skills prepended per turn
  skill_cache_ttl_seconds: 300       # How long to cache resolved skills per user (0 = no cache)

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

# ═══ MCP — External Tool Servers ═══
mcp:
  enabled: false                          # Master switch for MCP client
  connection_timeout_seconds: 10          # Per-server startup timeout
  tool_call_timeout_seconds: 60           # Per-tool-call timeout
  health_check_interval_seconds: 60
  max_retries: 5
  servers: {}                             # Configured via Admin UI (Tab 5h) — see below
  # Example server configs (typically managed via UI, not YAML):
  # servers:
  #   web-crawler:
  #     type: stdio
  #     command: "npx"
  #     args: ["-y", "@anthropic/mcp-server-fetch"]
  #     env: {}
  #     always_allow: ["fetch"]
  #     enabled: true
  #   remote-api:
  #     type: streamable-http
  #     url: "https://api.example.com/mcp"
  #     auth_key_provider: "mcp:remote-api"    # References api_keys table (provider = "mcp:remote-api")
  #     always_allow: []
  #     enabled: true
```

**Server-only (not user-overridable):** `server.*`, `vault.*`, `rag.embedding_model`, `rag.embedding_dimensions`, `rag.chunking.*`, `llm.local_endpoints`, `llm.dream_model`, `auth.*`, `memory.dream.*`, `chat_history.max_conversations_per_user`, `mcp.*`

**Admin-configurable via Admin UI (not just settings.yaml):** `rag.chunking.*` (Tab 5c — changes trigger full reindex), `vault.health_weights` and `vault.health_thresholds` (Tab 5g), `server.rate_limit.*` (Tab 5g)

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
**MCP stdio servers (Phase 7, optional):** If the admin configures MCP servers that use npm/npx (e.g., `npx @modelcontextprotocol/server-filesystem`), the Docker image must include Node.js. Two approaches:
1. **Include by default:** Add `apt-get install -y nodejs npm` to the Dockerfile. Adds ~80MB to image size but enables npm-based MCP servers out of the box.
2. **Document as optional:** Keep the base image lean. Document that admins who want npm-based MCP servers should extend the image: `FROM smart-copilot:latest` → `RUN apt-get install -y nodejs npm`.

Recommended: Option 2 (document as optional). Most MCP servers can also be installed globally and referenced by absolute path, avoiding the need for npx. Python-based MCP servers work without Node.js.

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

**Worker configuration note:** `--workers 2` is safe because each uvicorn worker process runs an independent asyncpg connection pool. The RLS `SET/RESET app.current_user_id` operates per-connection within each worker's pool — there is no cross-worker connection sharing or context leakage. The `VaultRegistry` in-memory mapping is rebuilt independently in each worker on startup and after user create/delete events.

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
    │   ├── mcp_admin.py             # MCP server CRUD + toggle + reconnect endpoints
    │   └── health.py                # health check
    ├── models/                      # 16 SQLAlchemy models
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
    │   ├── skills.py                # Skill resolution: trigger matching, caching, token budgeting
    │   └── scheduler.py             # APScheduler integration
    ├── mcp/
    │   ├── client.py                # MCP client connection manager (AsyncExitStack lifecycle)
    │   ├── registry.py              # ToolRegistry: merges built-in + MCP tools
    │   ├── config.py                # MCPServerConfig Pydantic model
    │   └── health.py                # Health check loop, reconnection with backoff
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
    │   ├── global-shortcut.ts, auto-launch.ts, ipc.ts,
    │   ├── export.ts                # Obsidian export IPC: folder dialog, batch write, progress
    │   ├── local-store.ts           # electron-store wrapper for client-only settings
    ├── renderer/
    │   ├── index.html, main.tsx, App.tsx
    │   ├── api/
    │   │   ├── client.ts, generated/, sse.ts
    │   ├── views/
    │   │   ├── ChatView.tsx, SettingsView.tsx, AdminView.tsx,
    │   │   ├── LoginView.tsx, DashboardView.tsx, PasswordChangeView.tsx
    │   ├── components/
    │   │   ├── chat/, editor/, floating/, intelligence/,
    │   │   ├── sidebar/ (VaultSidebar, TreeView, ListView, FileContextMenu, SidebarSearch),
    │   │   ├── admin/, dashboard/ (MyUsageTab, VaultHealthTab, SystemStatusTab),
    │   │   ├── memory/ (MemoryList, MemoryImport, MemoryDreamStatus),
    │   │   └── shared/
    │   ├── modals/, contexts/, hooks/
    │   ├── utils/
    │   │   ├── sanitizer.ts         # DOMPurify config
    │   │   └── clipboard.ts         # ClipboardHandler
    │   └── styles/
    ├── quickchat/
    │   ├── index.html
    │   ├── quickchat.tsx
    │   └── QuickChatView.tsx
    └── shared/
        ├── types.ts, constants.ts
```

---

## 26. UI Pages & Navigation

### Page Map

| # | Page | Access | Phase |
|---|---|---|---|
| 1 | Login / Connection Setup | All | 1 |
| 2 | Main Chat View (three-panel: sidebar + chat + editor) | All | 2–3 |
| 3 | Floating Surfaces (history, mode, model, settings popovers) | All | 2 |
| 4 | Settings (10 tabs) | All | 2–7 |
| 5 | Admin Dashboard (8 tabs) | Admin | 6–7 |
| 6a | User Dashboard (3 tabs: Usage, Vault Health, System Status) | All | 6 |
| 7 | Quick Chat Window (tray) | All | 7 |
| 8 | Modals (split, preview, organize, confirm, diff) | All | 3–7 |

### Page 2 — Main Chat View Layout

```
┌──────────┬──────────────────────────┬──────────────────────────┐
│ Sidebar  │     Chat Panel           │    Editor Panel          │
│ (toggle) │     (always visible)     │    (opens on demand)     │
│          │                          │                          │
│ 📁 Tree  │                          │                          │
│ or 📋    │                          │                          │
│ List     │                          │                          │
│          │                          │                          │
│ [220px]  │    [flex]                │    [flex, resizable]     │
└──────────┴──────────────────────────┴──────────────────────────┘
```

**Sidebar behavior:**
- Default state: **collapsed** (chat-first experience)
- Toggle: header button or keyboard shortcut `Cmd/Ctrl+B`
- Width: 220px fixed when expanded; 0px when collapsed (no rail)
- When sidebar is collapsed, chat panel takes full width (or shares with editor when a file is open)
- Sidebar state persisted across sessions via `user_settings`

**Two view modes** (toggle button in sidebar header):

**Tree view** — hierarchical folder structure reflecting the vault layout on the server. Folders expand/collapse. Files show note type icon (📝 permanent, 📖 literature, ⚡ fleeting, 🎯 project, 🔧 skill, 📁 structure). Drag-and-drop moves files between folders (calls `POST /api/v1/vault/move`). Inline rename via F2 or double-click on filename (calls `PUT /api/v1/documents/{id}`).

**List view** — flat, sortable, filterable table. Columns: Name, Type, Folder, Updated. Filters: note type dropdown, folder dropdown, tag dropdown, text search. Sort: by name, updated, type. Calls `GET /api/v1/documents` with filter/sort parameters. Supports multi-select for batch operations.

**Context menu** (right-click on file or folder):
- Open in editor (click also works)
- Open in new window (Electron `new BrowserWindow`)
- Rename (inline edit)
- Move to... (folder picker dialog)
- Export to Obsidian (see A24 — greyed out if no vault path configured)
- Copy path
- Delete (confirmation required)

**Context menu on folder:**
- New note here
- New skill here (creates skill template)
- Collapse/Expand all
- Export folder to Obsidian

**Data source:** Tree is built client-side from `GET /api/v1/documents` response. The `folder` and `path` fields on each document are sufficient to reconstruct the full tree. For vaults under 10,000 notes (target audience), this is trivially fast. Tree updates incrementally via SSE `notification` events when the indexer processes new files.

**Search bar:** At top of sidebar, filters both tree and list views. Debounced 300ms. In tree view, search expands matching paths and dims non-matching nodes. In list view, search filters the table.

### Settings Tabs
```
[ General ] [ Model ] [ RAG ] [ Modes ] [ Features ] [ API Keys ] [ Advanced ] [ Account ] [ Memory ] [ Skills ]
```

### Admin Dashboard Tabs
```
[ Overview ] [ LLM Usage ] [ Storage ] [ API Keys ] [ Users ] [ Memory Dream ] [ System ] [ MCP Servers ]
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

### Floating Surface Contents

**Chat Settings Popover** (gear icon in composer area):

| Element | Type | Notes |
|---|---|---|
| System prompt override | textarea | Per-message override; takes precedence over mode prompt when non-empty |
| Temperature | slider | 0.0–2.0, default from model config |
| Max tokens | number input | Model-specific maximum |
| Top-P | slider | 0.0–1.0 |
| Frequency penalty | slider | 0.0–2.0 |
| Reasoning effort | dropdown | low / medium / high — only shown for models that support it |

All per-message overrides — reset on new conversation.

**More Options Drawer** (⋯ button in composer area):

| Element | Type | Notes |
|---|---|---|
| Web search | toggle | Per-conversation; flipped ON automatically by Research mode and @web |
| Relevant notes | toggle | Per-conversation; controls whether RAG context is included |
| Agent tools | toggle | Hidden when active mode has `agent_tools: false` |
| File attachment | button | Triggers document upload (PDF, DOCX, HTML) |
| Image upload | button | Triggers vision model flow |

### Obsidian Export UI

Export buttons appear in three locations when Obsidian vault path is configured (hidden otherwise):

**1. Editor panel toolbar:** Export icon (↗ or Obsidian logo) — exports the currently open note. On click: writes file to `{vault_path}/{notes_subfolder}/{folder_structure}/{filename}.md`. Toast confirmation: "Exported to ~/Documents/Obsidian/Smart Copilot/Notes/{filename}.md". If file exists, overwrites silently (the server vault is authoritative).

**2. Sidebar context menu:** "Export to Obsidian" on individual files and folders. Folder export writes all contained files preserving folder structure. Batch export shows progress: "Exporting {current}/{total} notes..." with cancel button.

**3. Chat panel conversation menu:** "Export to Obsidian" on conversation header (⋯ menu). Writes conversation as markdown file to `{vault_path}/{conversations_subfolder}/{title}.md`.

**Export format — Notes:**
Files are written as-is from the server vault — the markdown content with frontmatter is already Obsidian-compatible. Wikilinks (`[[Target]]` and `[[Target|Alias]]`) are preserved. No format conversion needed.

**Export format — Conversations:**
```yaml
---
type: conversation
title: "{conversation.title}"
model: "{conversation.model_id}"
mode: "{conversation.mode_id}"
exported_at: "{ISO timestamp}"
source: smart-copilot
tags:
  - smart-copilot-export
---

## User
{message content}

## Assistant
{message content with citation markers preserved}
```

**Filename sanitization:** Strip `\/:*?"<>|#^[]` characters, collapse whitespace, limit to 200 characters. Preserve spaces (Obsidian handles them natively).

**IPC architecture:** All filesystem operations execute in the Electron main process via `ipcMain.handle`. The renderer calls `window.electronAPI.exportMarkdownFiles(destFolder, files)`. Main process validates paths (prevent traversal), creates directories recursively, writes files, and reports progress via `webContents.send('export:progress', {current, total, currentFile})`. Path traversal protection: `path.resolve(fullPath).startsWith(path.resolve(destFolder))` — reject if false.

### Settings Tab Field Specifications

#### Tab 4a — General

| Setting | Type | Default | Notes |
|---|---|---|---|
| Theme | dropdown | `system` | Options: `light`, `dark`, `system` |
| Language | dropdown | `en` | Display language. English only for v1.0; placeholder for future i18n. Read-only for now. |
| Notification sounds | toggle | on | Play sound on system notifications |
| Show indexing progress in status bar | toggle | on | |
| Default new note location | text input | `/` | Relative path within user's vault. Where `vaultWrite` and Zettel capture create notes when no specific path is given. |
| Date format | dropdown | `YYYY-MM-DD` | Options: `YYYY-MM-DD`, `DD/MM/YYYY`, `MM/DD/YYYY`. Used in frontmatter `created` field and vault export filenames. |
| Confirm before deleting conversations | toggle | on | Show warning modal before deleting unsaved conversations |
| End-of-chat save prompt | toggle | off | When enabled and conversation not saved, shows `[Save to Vault] [Not Now] [Never]` on chat end (see Decision 14) |
| Obsidian vault path | text input + Browse button | *(empty)* | Local filesystem path to user's Obsidian vault (e.g., `~/Documents/Obsidian/`). Browse button opens native folder picker via `dialog.showOpenDialog`. When empty, all "Export to Obsidian" buttons are hidden throughout the UI. Path validated on set: must be an existing directory. Persisted locally via `electron-store` (not sent to server — this is a client-only setting). |
| Export subfolder for notes | text input | `Smart Copilot/Notes` | Subfolder within the Obsidian vault where exported notes are placed. Created automatically on first export. |
| Export subfolder for conversations | text input | `Smart Copilot/Conversations` | Subfolder for exported conversations. |

#### Tab 4b — Model

| Setting | Type | Default | Notes |
|---|---|---|---|
| Default chat model | dropdown | from server config | Populated from `GET /api/v1/models`. Sticky — overrides the server default for this user. |
| Default temperature | slider | 0.7 | 0.0–2.0 |
| Default max tokens | number | 4096 | Model-specific upper bound shown |
| Default top-P | slider | 1.0 | 0.0–1.0 |
| Default frequency penalty | slider | 0.0 | 0.0–2.0 |
| Default reasoning effort | dropdown | `medium` | Options: `low`, `medium`, `high`. Only applied to models that support it; ignored silently for others. |
| Vision model | dropdown | from server config | Used for image understanding. Filtered to models with `vision` capability. |

These defaults apply to new conversations. Per-conversation overrides are set via the Chat Settings Popover.

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

| Element | Type | Notes |
|---|---|---|
| Mode list | reorderable list | Shows all modes (built-in + custom). Drag to reorder. First 5 appear in composer picker; rest overflow to "More modes". |
| — Mode row | row | Label · RAG scope badge · Web/Agent icons · [Edit] [Pin/Unpin] |
| — Built-in indicator | badge | Built-in modes show `✎` when their system prompt has been modified from default |
| **Edit mode dialog** | modal | Opens on [Edit] or [+ New Mode] |
| — Mode label | text input | Required. Max 20 characters. |
| — System prompt | textarea | The prompt sent to the LLM when this mode is active. Built-in modes show "Reset to default" button when modified. |
| — RAG scope | dropdown | Options: `vault` (private + shared), `project` (active project only), `note` (current note in editor), `vault+web` (vault + web search). |
| — Web search default | toggle | off | Initial state of the web search toggle when this mode is selected. User can still override. |
| — Agent tools | toggle | off | When on, all 22 agent tools available. When off, agent loop not activated (pipeline RAG still runs). |
| + New Mode | button | Opens Edit mode dialog with empty fields. |
| Delete custom mode | row action | Only on custom modes. Requires confirmation. Built-in modes cannot be deleted. |

Source: Decision 12. The 4 built-in modes (Ask, Write, Research, Focus) are pre-configured and resettable to defaults. Custom modes are stored in `user_settings` via `GET/PUT /api/v1/settings/modes`.

#### Tab 4e — Features

| Setting | Type | Default | Notes |
|---|---|---|---|
| Auto-extract memories from conversations | toggle | on | Maps to `memory.auto_extract` |
| Agent confirmation: before file write | toggle | on | Maps to `agent.confirm_before_write` |
| Agent confirmation: before note split | toggle | on | Maps to `agent.confirm_before_split` |
| Agent confirmation: before vault organize | toggle | on | Maps to `agent.confirm_before_organize` |
| Agent max tool calls per turn | number | 10 | Maps to `agent.max_tool_calls_per_turn`. Range: 1–25. |
| Web search: max results | number | 5 | Maps to `web_search.max_results`. Range: 1–20. |
| Web search: cross-reference vault | toggle | on | Maps to `web_search.cross_reference_vault`. When on, web results are compared against vault notes. |
| Web search: Wikipedia lookup | toggle | on | Maps to `web_search.wikipedia_lookup`. Include Wikipedia as a free search source. |
| Auto-offer note splitting | toggle | on | Maps to `zettelkasten.splitter.auto_offer_split`. Offer to split notes exceeding min word count. |
| Min word count for split offer | number | 1000 | Maps to `zettelkasten.splitter.min_word_count` |
| Original note handling after split | dropdown | `keep` | Options: `keep` (as literature note), `archive`, `ask` (always prompt). Maps to `zettelkasten.splitter.original_note_handling`. |

#### Tab 4f — API Keys (user's own)

| Element | Type | Notes |
|---|---|---|
| Info text | text | "Optionally provide your own API keys. If not set, shared keys configured by your admin will be used. Your key takes priority when set." |
| Provider list | rows | One row per provider: OpenAI, Anthropic, Gemini, DeepSeek, OpenRouter |
| — Provider row | row | Provider name · Key hint or "Not set" · Status ("Using your key ✅" / "Using shared key" / "No key ❌") · [Set Key] [Test] [Remove] |
| — Set Key dialog | modal | Password input + Save button |
| Local LLM info | text (read-only) | "Local LLM endpoints (Ollama, LM Studio) are configured by your admin." Lists available local endpoints from `settings.yaml` if any are configured, or "None configured" if empty. Not editable by users — this is a server-only setting. |

#### Tab 4g — Advanced

| Setting | Type | Default | Notes |
|---|---|---|---|
| Zettel ID format: use timestamp | toggle | on | Maps to `zettelkasten.id_format.use_timestamp`. When off, uses random alphanumeric ID. |
| Zettel ID separator | text input | (empty) | Maps to `zettelkasten.id_format.separator`. Inserted between date components in timestamp IDs (e.g., `-` produces `2025-02-14-1530`). |
| Chat export: include timestamps | toggle | off | Maps to `chat_history.include_timestamps`. Include per-message timestamps in vault export files. |
| Chat export: project subfolders | toggle | on | Maps to `chat_history.project_subfolder`. Organize exported chats into subfolders by project. |
| Chat export: folder name | text input | `Smart Copilot` | Maps to `chat_history.vault_export_folder`. Folder name within user's vault for exported conversations. |
| Link suggestion min confidence | slider | 0.7 | Maps to `zettelkasten.link_suggestions.min_confidence`. Range: 0.0–1.0. |
| Link suggestion max count | number | 10 | Maps to `zettelkasten.link_suggestions.max_suggestions`. Range: 1–50. |
| Proactive agent mode | toggle | off | Maps to `agent.proactive_mode`. When on, background agent runs scheduled vault health checks and cleanup suggestions. Requires tray agent (Phase 7). |
| Reset all settings to defaults | button | — | Clears all user overrides from `user_settings`. Requires confirmation dialog: "This will reset all settings to server defaults. Your API keys, modes, and projects will not be affected." |

#### Tab 4h — Account

| Setting | Type | Notes |
|---|---|---|
| Username | text (read-only) | |
| Email | text input | User can update their own email. Saves via `PATCH /api/v1/auth/me`. |
| Change Password | button | Opens dialog: current password + new password + confirm. Calls `POST /api/v1/auth/change-password`. |
| Role | text (read-only) | "Admin" or "User" |
| Account created | text (read-only) | Date |

Source: Decision 21 (password reset flow, role definitions). Profile data loaded via `GET /api/v1/auth/me` (see Section 15, Auth endpoints).

#### Tab 4i — Memory

| Element | Type | Notes |
|---|---|---|
| Active Memories | metric | "142 / 500 active memories" |
| Memory Dream status | card | Last run, sessions since, next estimate. "Run Dream now" button (calls `POST /api/v1/memories/dream/trigger`). |
| **Memory list** | searchable table | Columns: Content (truncated), Source (conversation link), Created, Last Recalled, Recall Count |
| — Search | text input | Filters by content text |
| — Sort | dropdown | By: newest, oldest, most recalled, least recalled |
| — Edit | row action | Opens inline editor — user can rewrite memory content. Re-embeds on save (`PUT /api/v1/memories/{id}`). |
| — Archive | row action | Soft-delete (`DELETE /api/v1/memories/{id}`). Can be restored from Archived tab. |
| — Delete permanently | row action | Hard-delete with confirmation (`DELETE /api/v1/memories/{id}/permanent?confirm=true`). "This cannot be undone." |
| **Archived memories** | expandable section | Same table structure, with "Restore" action (`POST /api/v1/memories/{id}/restore`) instead of "Archive". Loaded via `GET /api/v1/memories?archived=true`. |
| **Bulk actions** | toolbar | Select multiple → Archive / Delete / Export |
| **Add memory** | button | Opens dialog: content text area + optional source note reference. Creates + embeds (`POST /api/v1/memories`). |
| **Import memories** | button | Upload JSON or markdown file (`POST /api/v1/memories/import`). Markdown: one memory per line (lines starting with `- ` have prefix stripped). JSON: array of `{content, created_at?}` objects. Each imported memory is embedded immediately. |
| **Export memories** | button | Downloads all active memories as JSON (`GET /api/v1/memories/export`): `[{content, created_at, recall_count, source_conversation_id}]`. Can be re-imported on another instance. |

**Import validation:**
- Maximum 500 memories per import (matches `max_memories_per_user`)
- If import would exceed limit, show warning: "You have 142 active memories. Importing 400 would exceed your limit of 500. Import the first 358?" with options: Import partial / Cancel / Archive oldest to make room
- Duplicate detection: if imported memory content is >95% similar (cosine similarity) to an existing active memory, flag it: Skip / Import anyway / Replace existing

Source: F-MEM-01 US-4.7. All endpoints referenced exist in the Memory group (Section 15).

### Admin Dashboard Tab Field Specifications

#### Tab 5a — Overview

| Element | Type | Notes |
|---|---|---|
| Total Users | metric card | Count from `GET /api/v1/admin/overview` |
| Total Documents | metric card | Across all namespaces |
| Total Chunks | metric card | |
| Total Cost (30 days) | metric card | Sum across all users, all providers |
| Cost trend | sparkline chart | Daily total cost over 30 days |
| Active Conversations (7 days) | metric card | Conversations with messages in last 7 days |
| Index Queue Depth | metric card | Current pending items. Green when 0, yellow when > 0. |
| System Health Summary | status row | PostgreSQL: ✅ · Watcher: ✅ · Index: idle · Dream: last run 2h ago |
| Top Users by Cost (30d) | compact table | Username, Cost, Calls — top 5. Links to Tab 5b for full breakdown. |
| Recent Activity | event list | Last 10 system events: user logins, reindex triggers, Dream runs, embedding migrations |

Source: `GET /api/v1/admin/overview` provides all aggregate data.

#### Tab 5b — LLM Usage

| Element | Type | Notes |
|---|---|---|
| Total Cost (30 days) | metric card | With comparison to prior 30 days (↑12% or ↓5%) |
| Total Tokens (30 days) | metric card | Prompt + completion combined |
| Cost by Provider | horizontal bar chart | Grouped by provider (OpenAI, Anthropic, etc.) from `GET /api/v1/admin/costs/by-provider` |
| Cost by User | horizontal bar chart | Per-user breakdown from `GET /api/v1/admin/costs/by-user` |
| Cost by Model | horizontal bar chart | Per-model breakdown (drill-down from provider chart) |
| Usage Over Time | line chart | Daily cost and token count over 30/60/90 days from `GET /api/v1/admin/usage/history`. Toggle between cost and tokens. |
| Shared vs Personal Key Usage | stacked bar chart | Shows proportion of shared key cost vs personal key cost per user |
| Purpose Breakdown | pie chart | chat / embedding / agent / enrichment / dream — from `llm_usage.purpose` |
| Date range picker | control | Filters all charts. Presets: 7d, 30d, 90d, custom range. |

Source: F-ADMIN-02, `llm_usage` table with `key_type` and `purpose` columns.

#### Tab 5c — Storage & Indexing

| Element | Type | Notes |
|---|---|---|
| **Indexing Status** | section header | |
| Documents indexed | metric | Total across all namespaces, with per-namespace breakdown (private users + shared) |
| Chunks in database | metric | |
| Index queue depth | metric + indicator | Green when 0. Shows count and estimated time if > 0. |
| Force Reindex | button + dropdown | Dropdown: select user namespace or "All". Calls `POST /api/v1/admin/reindex`. Confirmation dialog: "This will re-index all {N} documents in {namespace}. Estimated time: ~{M} minutes." |
| Index queue status | live table | Current queue from `GET /api/v1/admin/index/status`: file path, status (pending/processing/failed), queued at |
| **Embedding Model** | section header | |
| Current Embedding Model | display | Model name + dimensions + total chunk count. e.g., "openai/text-embedding-3-small (1536 dim) · 12,847 chunks" |
| Change Embedding Model | dropdown + button | Populated from `settings.yaml` `llm.embedding_models` list. On select, calls `GET /api/v1/admin/embeddings/estimate` and shows: "Re-embed all {N} chunks with {new model}? Estimated cost: ${X}, time: ~{Y} minutes." If dimension changes, stronger warning per Decision 20. |
| Migration progress | progress bar + text | Only shown during active migration. From `GET /api/v1/admin/embeddings/status`. Shows: "⟳ Re-embedding: 67% complete (8,607 / 12,847 chunks)" |
| Cancel Migration | button | Only shown during active migration. Calls `POST /api/v1/admin/embeddings/cancel`. |
| **Chunking Configuration** | section header | |
| Chunk size (tokens) | number input | Default: 512. Changes trigger full reindex with confirmation dialog: "Changing chunking parameters requires re-indexing all {N} documents across all namespaces. Estimated time: ~{M} minutes. Proceed?" |
| Chunk overlap (tokens) | number input | Default: 64 |
| Min chunk (tokens) | number input | Default: 50 |
| Single-chunk threshold (tokens) | number input | Default: 600 |
| Boundary respect | dropdown | Options: `paragraph`, `sentence`, `none`. Default: `paragraph` |
| **Storage** | section header | |
| PostgreSQL disk usage | metric + bar | Total database size |
| Chunks storage | metric | Size of chunks table (data + indexes) |
| Vector index size | metric | HNSW index size |

Source: Decision 20 (embedding migration), F-ADMIN-03, Section 22 "Admin-configurable via Admin UI" note for chunking.

#### Tab 5d — API Keys (shared)

| Element | Type | Notes |
|---|---|---|
| Info text | text | "Shared API keys are available to all users. Users can override with their own keys in Settings → API Keys." |
| Provider list | table | One row per configured provider. Columns: Provider, Key Hint, Status, Last Tested, Actions |
| — Provider row | row | Provider name (e.g., "OpenAI") · Key hint ("...abc") or "Not set" · Status badge (Valid ✅ / Invalid ❌ / Not tested ⚠️) · Last tested date · [Test] [Edit] [Delete] |
| — Test button | action | Calls `POST /api/v1/admin/api-keys/{id}/test`. Makes minimal API call, updates `is_valid` and `last_tested_at`. Shows inline result. |
| — Edit button | action | Opens dialog: password input for new key + Save. Calls `POST /api/v1/admin/api-keys`. Never shows existing key — only hint. |
| — Delete button | action | Confirmation: "Remove shared {provider} key? Users without personal keys will lose access to {provider} models." Calls `DELETE /api/v1/admin/api-keys/{id}`. |
| + Add Provider Key | button | Dialog: provider dropdown (from `settings.yaml` model list, deduplicated) + password input + Save |
| **Local LLM Endpoints** | section header | |
| Endpoint list | editable list | Add/remove OpenAI-compatible endpoints (Ollama, LM Studio, vLLM). Fields: URL, display name. Maps to `llm.local_endpoints` in `settings.yaml`. |
| — Test endpoint | action | Makes a `GET /v1/models` call to the endpoint URL to verify connectivity. |

Source: Decision 7 (encryption, resolution order), Decision 21 (admin-only for shared keys and local endpoints). `encrypted_key` is never returned — only `display_hint`.

#### Tab 5e — Users

| Element | Type | Notes |
|---|---|---|
| User list | table | Columns: Username, Email, Role, Documents, Cost (30d), Last Active, Created |
| — Edit user | row action | Change role (admin ↔ user), update email |
| — Reset Password | row action | Generates temporary password shown once in dialog; sets `must_change_password: true` |
| — Delete user | row action | Requires typed confirmation of username. Deletes user + all DB records. Vault files on disk NOT deleted |
| + Add User | button | Dialog: username (required), email (optional), temporary password (auto-generated, shown once), role (default: user) |

#### Tab 5f — Memory Dream

| Element | Type | Notes |
|---|---|---|
| Dream Status Overview | summary row | "Dream enabled: ✅ · Last system-wide run: 3h ago · Next check: in 57min" |
| **Per-User Dream Status** | table | From `GET /api/v1/admin/dream/status`. Columns: Username, Active Memories, Last Dream, Sessions Since, Next Eligible, Status, Actions |
| — Status | badge | `idle` (waiting for trigger conditions), `eligible` (conditions met, queued), `running`, `skipped` (< 20 memories) |
| — Trigger Dream | row action | Calls `POST /api/v1/admin/dream/trigger/{user_id}`. Confirmation: "Run Memory Dream consolidation for {username} now?" |
| — View Audit Log | row action | Expands inline or opens modal showing that user's `dream_audit_log` entries: timestamp, phase, action, old content → new content, reason |
| **Dream Configuration** | section | Read-only display of `memory.dream.*` settings from `settings.yaml`. Not editable in UI — change via config file. Shows: check interval, min hours between runs, min sessions, stale threshold, min memories to run. |
| **Recent Dream Activity** | event list | Last 10 Dream runs across all users: username, timestamp, actions taken (e.g., "Archived 3 stale, merged 2 duplicates, resolved 5 dates"), duration |

Source: Section 18 (Memory Dream system), Decision 18, `dream_audit_log` table. Note: admin can view Dream status and trigger runs but cannot read individual memory content (Decision 21 privacy boundary).

#### Tab 5g — System Health

| Element | Type | Notes |
|---|---|---|
| Backend uptime | metric | |
| PostgreSQL connections | metric | active / max |
| PostgreSQL disk usage | metric + bar | |
| Health history | line chart | DB size, chunk count, connections over time (from `system_health` table, recorded every 15 minutes by APScheduler) |
| Vault path | text (read-only) | |
| Watcher status | indicator | Active / Paused / Error |
| Rate limit config | inputs | `max_requests_per_minute`, `max_agent_tool_calls_per_minute` — admin-configurable |
| Health weights | sliders | orphan, density, type_coverage, freshness — must sum to 1.0 |
| Health thresholds | inputs | green and yellow thresholds (0.0–1.0) |
| Last backup | text | "Database: 2025-02-14 03:00 · Vault: synced via Syncthing" — read from `/config/backup-status.json` written by the automated backup script. `GET /api/v1/admin/health` reads this file if present |
| Backup reminder | warning card | Shown if `/config/backup-status.json` is missing or `last_backup` is older than 7 days: "No recent backup detected. See documentation for setup." |

#### Tab 5h — MCP Servers

| Element | Type | Notes |
|---|---|---|
| MCP master toggle | toggle | Maps to `mcp.enabled`. When off, no MCP connections are attempted and all MCP tools are removed from the agent's tool list. |
| **Server List** | table | From `GET /api/v1/admin/mcp/servers`. Columns: Name, Type (stdio/http), Status (🟢 connected / 🔴 disconnected / 🟡 connecting), Tools (count), Actions. |
| — Status detail | expandable row | Shows: transport type, command or URL, discovered tools list (name + description), last health check, error message if any, connection uptime. |
| — Toggle | row action | Enable/disable without removing config. `POST /api/v1/admin/mcp/servers/{name}/toggle`. |
| — Reconnect | row action | Force reconnect. `POST /api/v1/admin/mcp/servers/{name}/reconnect`. |
| — Edit | row action | Opens edit dialog (same as Add dialog, pre-populated). |
| — Remove | row action | Confirmation required. `DELETE /api/v1/admin/mcp/servers/{name}`. |
| + Add MCP Server | button | Dialog with fields: Name (identifier), Type (stdio/streamable-http dropdown), Command + Args (for stdio), URL (for HTTP), Auth Token (for HTTP servers, stored Fernet-encrypted in api_keys table — never in YAML or env vars), Environment Variables (key-value, for stdio — supports `${env:VAR}` syntax), Always Allow (comma-separated tool names), Enabled toggle. |
| **Discovered Tools** | section | Aggregated list of all tools from all connected MCP servers. Columns: Qualified Name (`mcp_{server}_{tool}`), Server, Description, Auto-approve (✅ if in always_allow). Admin can toggle individual tool visibility (hidden tools are not passed to the LLM). |
| **Connection Log** | event list | Last 20 MCP connection events: server name, timestamp, event (connected/disconnected/error/reconnecting), message. |

Note: MCP server configuration is admin-only. Users see MCP-provided tools in the agent's tool list but cannot add, remove, or configure MCP servers. The confirmation gate applies to all MCP tool calls not in `always_allow`.

### User Dashboard Tab Field Specifications

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
| Vault Health Score | metric card | Composite score displayed as percentage. Formula: `(w_orphan × (1 - orphan_ratio)) + (w_density × min(avg_links / 3, 1)) + (w_type × type_coverage) + (w_fresh × (1 - stale_ratio))`. Default weights: 0.4, 0.3, 0.2, 0.1. Thresholds: ≥80% green, 50–79% yellow, <50% red |
| Orphan Notes | metric + list | Action: suggest links / archive |
| Hub Notes | metric + list | Most-connected notes (highest incoming wikilink count) |
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
| Rate limiting | Per-user sliding window: 30 req/min API, 60 tool calls/min agent. In-memory counter, resets on restart. |

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
| 3 | Sidebar works | Browse vault in sidebar, open note in editor, tree reflects vault structure and updates on file changes |
| 4 | Multi-tool | Research mode → agent uses ragSearch + webSearch + vaultWrite |
| 4 | Memory persists | Fact in chat → memoryRecall finds it in new conversation |
| 4 | Dream runs | Trigger → consolidation report shows actions |
| 5 | Project scoping | Create project → Focus mode → RAG limited to project |
| 5 | Web search | @web query → results displayed |
| 6 | Admin dashboard | Real usage data, costs, users, health |
| 6 | User dashboard | Personal costs with shared/personal breakdown |
| 6 | Embedding migration | Change model → progress → complete → search works |
| 7 | Tray agent | Close window → tray icon → Quick Chat via hotkey |
| 7 | MCP works | Admin can add an MCP server, agent discovers its tools, tool calls work with confirmation gate |
| 7 | Obsidian export | User configures vault path, exports a note and a conversation, files appear in Obsidian vault with correct frontmatter and wikilinks |
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
| react-complex-tree | Maintainer abandonment | Fallback: react-arborist fork or headless-tree |
| mcp Python SDK | Breaking changes in v2 | Pin to v1.x (`mcp>=1.25,<2`); test transport compatibility in CI |

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
| MCP server crashes or hangs | Medium | Health check pings every 60s; 3 failures → disconnect + exponential backoff reconnection. Tool call timeout: 60s. Agent continues with built-in tools when MCP is unavailable. |
| MCP tool poisoning (malicious tool metadata) | Medium | All MCP tool outputs sanitized before re-entering LLM context. Admin reviews discovered tools before enabling. Per-server `always_allow` lists only for trusted read-only operations. |
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
| MCP Specification | `https://modelcontextprotocol.io/specification/2025-03-26` |
| MCP Python SDK | `https://github.com/modelcontextprotocol/python-sdk` |

---

## 32. Glossary

| Term | Definition |
|---|---|
| **Advisory lock** | PostgreSQL `pg_try_advisory_lock()` for Dream concurrency |
| **Archived fleeting** | Expired fleeting note moved to archive folder; `note_type: archived_fleeting`; removed from all RAG indexes but retained on disk |
| **Citation markers** | `[1]`, `[2]` in LLM output mapped to source documents |
| **Client-cooperative tool** | Agent tool requiring Electron client data via SSE round-trip |
| **Contextual enrichment** | Prepending metadata (title, folder, tags, wikilinks) before embedding |
| **DOMPurify** | Client-side HTML sanitizer (browser DOM parser) |
| **enrichment_hash** | Hash of enrichment inputs — triggers re-embed on link changes |
| **Fernet** | Symmetric encryption from Python's `cryptography` library |
| **Fleeting note** | Temporary note, expires from index after N days |
| **Hybrid RAG** | Vector + BM25 + wikilink graph, combined via RRF |
| **key_type** | Whether LLM call used `shared` or `personal` API key |
| **Literature note** | Summary of external source — citation reference |
| **MCP** | Model Context Protocol — open standard for connecting AI systems to external tool servers. Smart Copilot acts as an MCP client, connecting to admin-configured servers and adding their tools to the agent's registry. |
| **Memory Dream** | Nightly 4-phase memory consolidation cycle |
| **Mode** | Named system-prompt bundle controlling RAG scope, web, agent |
| **Namespace** | `private` (per-user) or `shared` (team) — controls RLS visibility |
| **nh3** | Server-side HTML sanitizer (Rust/Ammonia, defense-in-depth) |
| **OperationLog** | JSON record of multi-step file operations for undo |
| **Permanent note** | Atomic idea — core Zettelkasten unit |
| **RLS** | Row-Level Security — PostgreSQL per-user data isolation |
| **RRF** | Reciprocal Rank Fusion — `score = Σ 1/(k + rank)` across signals |
| **safeStorage** | Electron OS-encrypted storage (macOS Keychain, Windows DPAPI) |
| **Skill** | Markdown file with `type: skill` frontmatter containing procedural instructions. Loaded deterministically by agent runner via trigger matching — not retrieved by RAG. Supports system-level (shared) and user-level (private) scoping. |
| **SYSTEM_USER_ID** | UUID constant for shared namespace content owner (never logs in) |
| **ToolRegistry** | Unified registry merging Smart Copilot's 22 built-in agent tools with dynamically discovered tools from connected MCP servers. Handles namespacing, dispatch, and confirmation gate integration. |
| **VaultRegistry** | In-memory path → (user_id, namespace) mapping |

---
*End of Smart Copilot PRD v1.0*