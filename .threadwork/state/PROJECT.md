# Smart Copilot — Project Definition

## Vision

Smart Copilot is a self-hosted AI knowledge management system that brings Zettelkasten automation, a proactive knowledge agent, and hybrid RAG intelligence to markdown files. It consists of a Python/FastAPI backend running in a single Docker container (bundled with PostgreSQL 16 + pgvector) and an Electron desktop client connected via REST + SSE API. The system supports 3–10 users on a homelab server with per-user private vaults and a shared team knowledge base.

## Core Principles

| ID | Principle | Implication |
|---|---|---|
| P1 | Chat-first | Chat panel is the primary interface; the editor is a companion |
| P2 | Client-server separation | One Docker container runs everything server-side; Electron client is thin |
| P3 | Hybrid namespace from day one | Private vaults + shared knowledge; never retrofit sharing later |
| P4 | PostgreSQL does the heavy lifting | Vector search, BM25, graph traversal — all in one database |
| P5 | LiteLLM as library | No separate LLM gateway service; provider translation in-process |
| P6 | RAG quality over complexity | Contextual enrichment + hybrid retrieval covers 90% of use cases |
| P7 | API keys in the database | Never in env vars or config files; managed via admin UI |
| P8 | Memory hygiene via Dream cycles | Long-term memory automatically consolidated, not left to rot |
| P9 | Defense in depth | Sanitize untrusted content on both client (DOMPurify) and server (nh3) |
| P10 | Build must stay green | Every commit passes CI |

## Technology Stack

### Backend

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
| MCP | mcp >= 1.25 (Python SDK) | Pin to v1.x |
| Auth | python-jose (JWT) | stateless |
| Encryption | cryptography (Fernet) | API keys at rest |
| Hashing | xxhash | fast non-cryptographic (content_hash, enrichment_hash) |
| Validation | Pydantic v2 | |
| Process mgr | supervisord | PostgreSQL + FastAPI |

### Frontend

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
| File tree | react-complex-tree | |
| Components | Radix UI (15 primitives) | |
| Styling | CSS modules, `.sc-` prefix | |
| Icons | Lucide React (primary) + Material Symbols Outlined (fallback) | |
| Command | cmdk | |
| Diff | diff + react-diff-viewer-continued | |
| Graph | Cytoscape.js (lazy) | |
| Sanitize | DOMPurify | clipboard |
| Update | electron-updater | GitHub Releases |
| Local storage | electron-store | ESM-only |
| API | Generated from OpenAPI | auto-synced |
| Animation | motion/react (Framer Motion v11) | |

## Monorepo Structure

```
smart-copilot/
├── server/          # Python/FastAPI backend
├── client/          # Electron + React frontend
└── docs/            # PRD, UI spec, design assets
```

## Architecture Constraints

- Single Docker container via supervisord (PostgreSQL + FastAPI)
- No Redis, no Celery — asyncio + ProcessPoolExecutor only
- Single-process Python backend (no horizontal scaling)
- 3–10 concurrent users maximum
- PostgreSQL RLS for data isolation (14 user-scoped tables)
- ENCRYPTION_KEY env var is the only secret outside the database
- SSE for streaming (no WebSocket)
- REST for CRUD
- 27 locked architecture decisions (see PRD Section 4)

## Users

| Persona | Role | Vault Size |
|---|---|---|
| Alice (primary) | Knowledge worker, Zettelkasten practitioner | 500–5,000 notes |
| Bob (secondary) | Homelab admin, deploys and manages | N/A |
| Carol (tertiary) | Non-admin team member | 100–1,000 notes |

## Companion Documents

- `docs/product_requirements.md` — authoritative PRD (wins for data contracts, API bindings)
- `docs/ui-spec.md` — UI design specification (wins for visual/interaction decisions)
- `docs/design/prototype/` — HTML prototypes (illustrative only)
