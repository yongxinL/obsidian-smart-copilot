---
phase: 01a
plan: 02
subsystem: domain-models
tags: [sqlalchemy, postgresql, pgvector, alembic, migration]
dependency_graph:
  requires: []
  provides: [01a-03-alembic-migration]
  affects: [01b-authentication, 01c-vault-indexer]
tech_stack:
  added:
    - SQLAlchemy 2.0 (DeclarativeBase, Mapped, mapped_column)
    - pgvector (VECTOR type, VECTOR(1536) for embeddings)
    - PostgreSQL types (JSONB, ARRAY, TSVECTOR, ENUM, INET, BigInteger)
key_files:
  created:
    - server/app/models/base.py
    - server/app/models/__init__.py
    - server/app/models/user.py
    - server/app/models/session.py
    - server/app/models/mcp_token.py
    - server/app/models/provider_key.py
    - server/app/models/vault.py
    - server/app/models/page.py
    - server/app/models/page_version.py
    - server/app/models/chunk.py
    - server/app/models/entity.py
    - server/app/models/link.py
    - server/app/models/timeline_event.py
    - server/app/models/tag.py
    - server/app/models/job.py
    - server/app/models/audit_log.py
    - server/app/models/skill.py
    - server/app/models/recipe.py
    - server/app/models/eval_candidate.py
    - server/app/models/conversation.py
    - server/app/models/memory.py
    - server/app/models/dream_audit_log.py
    - server/app/models/project.py
    - server/app/models/operation_log.py
    - server/app/models/llm_usage.py
    - server/app/models/index_event.py
    - server/app/models/user_settings.py
    - server/app/models/system_config.py
    - server/app/models/mcp_server.py
    - server/app/models/golden_eval.py
  modified:
    - server/pyproject.toml (added F821 per-file-ignores for models/)
decisions:
  - "Enum types defined at module level using `PG_ENUM(..., name='...', create_constraint=True)`"
  - "Multi-table files: tag.py (tags + page_tags), conversation.py (conversations + messages), golden_eval.py (3 tables)"
  - "UUID imported from sqlalchemy (not uuid module) for type annotations in mapped_column"
  - "pgvector VECTOR(1536) for chunks.embedding (text-embedding-3-small dimension)"
  - "provider_keys.encrypted_key is LargeBinary (BYTEA) per security requirement"
metrics:
  duration: 1704s (~28 minutes)
  completed: 2026-05-10
  tasks: 4/4
  tables: 32
  files: 29 model files created
---

# Phase 01a Plan 02 Summary: Domain Model Modules

## One-liner
Complete SQLAlchemy domain model layer: 32 PostgreSQL tables across 28 model modules with VECTOR(1536) embeddings, BYTEA encrypted keys, and aggregate imports for Alembic autogenerate.

## What was built

### Model files created (28 domain modules + base.py + __init__.py)
- **server/app/models/base.py** — `Base(DeclarativeBase)` + `TimestampMixin` with `created_at`/`updated_at`
- **server/app/models/__init__.py** — aggregate import causing all tables to register on `Base.metadata`

**Auth + Identity (4 files):**
- `user.py` — users table (REQ-300): UUID PK, username, email, password_hash, role enum (admin/user)
- `session.py` — sessions table (REQ-301): JWT sessions with token_hash, expires_at
- `mcp_token.py` — mcp_tokens table (REQ-302): per-device bearer tokens
- `provider_key.py` — provider_keys table (REQ-303): encrypted_key as **LargeBinary (BYTEA)**

**Vault + Content (9 files):**
- `vault.py` — vaults table (REQ-304): private/shared with path
- `page.py` — pages table (REQ-305/305A): compiled_truth, frontmatter JSONB, soft delete
- `page_version.py` — page_versions table (REQ-306): version history
- `chunk.py` — chunks table (REQ-307): **VECTOR(1536)** embedding + **TSVECTOR** tsv
- `entity.py` — entities table (REQ-308): typed graph nodes with aliases ARRAY
- `link.py` — links table (REQ-309): page-to-entity with source_kind enum
- `timeline_event.py` — timeline_events table (REQ-310): append-only events
- `tag.py` — **tags + page_tags** (REQ-311): vault-scoped labels + join table

**Background Jobs + Audit (2 files):**
- `job.py` — jobs table (REQ-312): parent_id FK for DAG, kind/status enums, JSONB payload
- `audit_log.py` — audit_log table (REQ-313): BigInteger PK, INET for client IP

**Skills, Recipes, Eval (3 files):**
- `skill.py` — skills table (REQ-314): namespace enum (system/user)
- `recipe.py` — recipes table (REQ-315): YAML text, namespace scoping
- `eval_candidate.py` — eval_candidates table (REQ-316): golden/regression benchmarks

**Agent: Conversations, Memories (3 files):**
- `conversation.py` — **conversations + messages** (REQ-360/361): mcp_mode enum, citations JSONB
- `memory.py` — memories table (REQ-362): archived flag
- `dream_audit_log.py` — dream_audit_log table (REQ-363): consolidation run records

**Projects + Operation Log (2 files):**
- `project.py` — projects table (REQ-364): folder patterns, tag includes
- `operation_log.py` — operation_log table (REQ-365): low-level mutation tracking

**Observability (2 files):**
- `llm_usage.py` — llm_usage table (REQ-366): token/cost per conversation
- `index_event.py` — index_events table (REQ-367): per-page index lifecycle

**Configuration (3 files):**
- `user_settings.py` — user_settings table (REQ-368): user_id as PK/FK
- `system_config.py` — system_config table (REQ-369): key as PK (TEXT)
- `mcp_server.py` — mcp_servers table (REQ-370): external MCP registry

**Golden Eval (1 file):**
- `golden_eval.py` — **golden_query_suites + queries + runs** (REQ-372-374): benchmark suites

### Enum names introduced (for Plan 03 Alembic migration)
| Enum name | Table | Values |
|-----------|-------|--------|
| `users_role_enum` | users | admin, user |
| `vaults_kind_enum` | vaults | private, shared |
| `pages_type_enum` | pages | 10 types (person, company, concept, idea, project, meeting, note, media, inbox, system) |
| `pages_note_type_enum` | pages | compiled_truth, timeline, mixed |
| `chunks_kind_enum` | chunks | summary, detail, truth, event, enrichment |
| `entities_kind_enum` | entities | person, company, concept, idea, project |
| `links_source_kind_enum` | links | wikilink, enrichment, inferred |
| `jobs_kind_enum` | jobs | index_page, enrich_entity, dream_consolidate, embed_migration, backup, cleanup |
| `jobs_status_enum` | jobs | pending, running, success, failed, cancelled |
| `skills_namespace_enum` | skills | system, user |
| `recipes_namespace_enum` | recipes | system, user |
| `eval_candidates_kind_enum` | eval_candidates | golden, regression, manual |
| `conversations_mcp_mode_enum` | conversations | disabled, client, server |
| `messages_role_enum` | messages | system, user, assistant, tool |
| `dream_audit_log_kind_enum` | dream_audit_log | consolidate, audit, extract, backup |
| `dream_audit_log_status_enum` | dream_audit_log | success, partial, failed |
| `index_events_event_type_enum` | index_events | created, updated, deleted, re_indexed, error |
| `mcp_servers_type_enum` | mcp_servers | stdio, streamable_http |
| `golden_query_suites_scope_enum` | golden_query_suites | system, user |

### Schema verification
```
SUCCESS: 32 tables registered in Base.metadata
Tables: audit_log, chunks, conversations, dream_audit_log, entities,
  eval_candidates, golden_queries, golden_query_runs, golden_query_suites,
  index_events, jobs, links, llm_usage, mcp_servers, mcp_tokens, memories,
  messages, operation_log, page_tags, page_versions, pages, projects,
  provider_keys, recipes, sessions, skills, system_config, tags,
  timeline_events, user_settings, users, vaults
```

## Deviations from Plan

None - plan executed exactly as written. All 28 domain model module files created, 32 tables registered on `Base.metadata`, `VECTOR(1536)` on chunks.embedding, `LargeBinary` on provider_keys.encrypted_key, ruff clean.

## Commits

| Commit | Description |
|--------|-------------|
| `0fa6b14` | feat(01a-02): add models package skeleton — Base, TimestampMixin, app/__init__ |
| `8f49aa3` | feat(01a-02): add 12 core auth/vault/page/chunk/entity/link model files |
| `3165a88` | feat(01a-02): add 16 remaining domain model files |
| `f75707b` | feat(01a-02): add aggregate model imports in models/__init__.py |

## Self-Check

- All 29 model files exist under `server/app/models/`
- `import app.models` registers exactly 32 tables on `Base.metadata`
- `apscheduler_jobs` is NOT in `Base.metadata` (APScheduler manages it separately)
- `chunks.embedding` is `VECTOR(1536)`
- `provider_keys.encrypted_key` is `LargeBinary` (BYTEA)
- `cd server && ruff check app/` exits 0
- All enum names documented for Plan 03 migration

## Checkpoint Self-Check: PASSED
