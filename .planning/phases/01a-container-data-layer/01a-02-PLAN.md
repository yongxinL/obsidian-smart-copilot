---
phase: 01a
plan: 02
type: execute
wave: 2
depends_on: [01a-01]
files_modified:
  - server/app/__init__.py
  - server/app/models/__init__.py
  - server/app/models/base.py
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
autonomous: true
requirements: [INFRA-07]
must_haves:
  truths:
    - "All 28 domain model module files exist as importable Python modules (one file per domain per D-07; some files declare multiple closely-related tables)"
    - "Base.metadata enumerates every domain table from D-05"
    - "chunks.embedding column is typed VECTOR(1536) with text-embedding-3-small dimension (CLAUDE.md)"
    - "users, pages, page_versions, chunks, entities, links, timeline_events, tags, jobs, conversations, messages, memories, projects, llm_usage, index_events, user_settings, mcp_tokens, provider_keys, sessions, dream_audit_log, audit_log, skills, recipes, eval_candidates, mcp_servers, system_config, vaults, operation_log, golden_query_suites, golden_queries, golden_query_runs all appear in Base.metadata.tables"
    - "encrypted_key column on provider_keys is BYTEA"
    - "ruff check passes on all 28 domain model module files"
  artifacts:
    - path: "server/app/models/base.py"
      provides: "DeclarativeBase root class for all ORM models"
      contains: "class Base(DeclarativeBase)"
    - path: "server/app/models/__init__.py"
      provides: "Aggregate import of every model module so Base.metadata is complete"
      contains: "from app.models import"
    - path: "server/app/models/chunk.py"
      provides: "chunks table with VECTOR(1536) embedding column"
      contains: "VECTOR(1536)"
    - path: "server/app/models/provider_key.py"
      provides: "provider_keys with encrypted_key BYTEA"
      contains: "LargeBinary"
  key_links:
    - from: "models/__init__.py"
      to: "Base.metadata"
      via: "side-effect imports of every domain module"
      pattern: "from app.models\\.(user|session|page|chunk)"
    - from: "models/chunk.py"
      to: "pgvector.sqlalchemy.VECTOR"
      via: "VECTOR(1536) column type"
      pattern: "from pgvector.sqlalchemy import VECTOR"
---

<objective>
Per D-05, define ALL 28 domain model module files up-front (one file per domain per D-07; tag.py, conversation.py, and golden_eval.py each declare multiple closely-related tables) so the complete schema across all 7 phases is captured in a single migration in Plan 03. Per D-07, one file per domain. Each file declares table columns, primary keys, foreign keys, server-side defaults, and column types — but NO ORM relationships (those are added in later phases as services need them) and NO RLS POLICY definitions (CREATE POLICY is Phase 1b per D-09 / RESEARCH Open Question 3).

Purpose: Lock in the complete schema shape now so that subsequent phases never block on schema changes; subsequent phases add `0002_*`, `0003_*` migrations only when schema genuinely changes (D-06).

Output: 28 domain model module files (base.py + 27 domain modules) plus app/__init__.py and models/__init__.py — 31 files total — all linting clean.

Note on file count: Task 3 produces 16 model module files (some declare multiple closely-related tables per D-07). A 3a/3b split was considered (W1) but rejected — the work is mechanical schema-stub authoring with a single shared skeleton; splitting would inflate task count without reducing context cost or decision complexity, and the verify block already enumerates every file individually.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.planning/REQUIREMENTS.md
@.planning/phases/01a-container-data-layer/01a-CONTEXT.md
@.planning/phases/01a-container-data-layer/01a-RESEARCH.md
@docs/product_requirements_document_v26.05.md

<interfaces>
<!-- Base class and column types every model file imports. Use these directly. -->

From app/models/base.py (defined in Task 1 below):
```python
from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
```

Common column patterns used across models:
```python
import uuid
from sqlalchemy import UUID, String, Text, Integer, Boolean, BigInteger, ForeignKey, JSON, LargeBinary, Date
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, ENUM, INET
from sqlalchemy.orm import Mapped, mapped_column

# UUID primary key
id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

# Text array (PostgreSQL TEXT[])
aliases: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")

# JSONB
frontmatter: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")

# pgvector VECTOR(1536) — text-embedding-3-small per CLAUDE.md
from pgvector.sqlalchemy import VECTOR
embedding: Mapped[list[float] | None] = mapped_column(VECTOR(1536), nullable=True)
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create models package skeleton — base.py, app/__init__.py, models/__init__.py</name>
  <files>server/app/__init__.py, server/app/models/__init__.py, server/app/models/base.py</files>
  <read_first>
    - .planning/phases/01a-container-data-layer/01a-RESEARCH.md (Pattern 6: SQLAlchemy 2.0 DeclarativeBase + mapped_column)
    - server/pyproject.toml (verify Ruff config + Python 3.12 target are in place from Plan 01)
    - CLAUDE.md (SQLAlchemy 2.0 + asyncpg + pgvector constraints)
  </read_first>
  <action>
1. `server/app/__init__.py` — overwrite with empty file (placeholder existed from Plan 01 task 2):
```python
"""Smart Copilot server package."""
```

2. `server/app/models/base.py`:
```python
"""SQLAlchemy 2.0 declarative base + shared column mixins.

Per D-07, one file per domain. This module provides the shared `Base`
declarative class and timestamp mixin imported by every model file.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Root declarative class for all ORM models.

    Every model module (user.py, page.py, ...) inherits from this Base
    so that `Base.metadata` enumerates the complete schema for Alembic
    autogenerate (D-05, D-06).
    """


class TimestampMixin:
    """Standard created_at/updated_at columns (server-side defaults)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

3. `server/app/models/__init__.py` — placeholder; the full aggregate import (which causes side-effect registration of every model class with `Base.metadata`) is added in Task 4 after all 28 domain model module files exist. For now write only:
```python
"""Domain models package.

Aggregate imports are added once all model modules exist (Task 4).
Importing this package MUST cause every domain table to be registered
with Base.metadata so that Alembic autogenerate sees the complete schema.
"""
from app.models.base import Base, TimestampMixin

__all__ = ["Base", "TimestampMixin"]
```
  </action>
  <verify>
    <automated>test -f server/app/models/base.py && test -f server/app/models/__init__.py && test -f server/app/__init__.py && grep -q 'class Base(DeclarativeBase)' server/app/models/base.py && grep -q 'class TimestampMixin' server/app/models/base.py && (cd server && ruff check app/ 2>&1 | tail -3)</automated>
  </verify>
  <acceptance_criteria>
    - `server/app/models/base.py` declares `class Base(DeclarativeBase)` (exact substring)
    - `server/app/models/base.py` declares `class TimestampMixin` with both `created_at` and `updated_at` columns of type `DateTime(timezone=True)` and `server_default=func.now()`
    - `server/app/models/__init__.py` re-exports `Base` and `TimestampMixin`
    - `cd server && ruff check app/` exits 0
    - `cd server && python -c "from app.models import Base; assert hasattr(Base, 'metadata')"` exits 0
  </acceptance_criteria>
  <done>Base + mixin + package init created; ruff clean.</done>
</task>

<task type="auto">
  <name>Task 2: Create core auth/vault/page/chunk/entity/link domain models (12 files)</name>
  <files>server/app/models/user.py, server/app/models/session.py, server/app/models/mcp_token.py, server/app/models/provider_key.py, server/app/models/vault.py, server/app/models/page.py, server/app/models/page_version.py, server/app/models/chunk.py, server/app/models/entity.py, server/app/models/link.py, server/app/models/timeline_event.py, server/app/models/tag.py</files>
  <read_first>
    - .planning/phases/01a-container-data-layer/01a-RESEARCH.md (Complete Domain Model List table — column hints; Pattern 6 + 7 for chunk vector column)
    - docs/product_requirements_document_v26.05.md (§7.1 data model — column definitions for users, pages, chunks, entities, links)
    - server/app/models/base.py (shared Base + TimestampMixin contract)
    - CLAUDE.md (encrypted_key MUST be BYTEA on provider_keys; chunks.embedding MUST be VECTOR(1536))
  </read_first>
  <action>
Create the 12 model files for the auth + vault + page domain. Every file follows the same skeleton:

- `from __future__ import annotations`
- module docstring referencing the REQ ID from RESEARCH.md "Complete Domain Model List"
- imports from sqlalchemy, sqlalchemy.dialects.postgresql, app.models.base
- single ORM class inheriting Base (and TimestampMixin where the table needs created_at/updated_at)
- `__tablename__` matches table name from RESEARCH.md table
- Columns are STUBS — primary key, foreign keys, server-side default text fields, type-correct enums, JSONB fields. No ORM relationships, no validations.
- NO `__table_args__` for indexes — those go in the Alembic migration (Plan 03).

Use these enum values where applicable (from PRD §7.1 — read the PRD for exact enums; if PRD ambiguous, define as PostgreSQL ENUM with the values listed below):

| Model | Enum column | Values |
|-------|------------|--------|
| user | role | `admin`, `user` |
| vault | kind | `private`, `shared` |
| page | type | `person`, `company`, `concept`, `idea`, `project`, `meeting`, `note`, `media`, `inbox`, `system` |
| page | note_type | `compiled_truth`, `timeline`, `mixed` |
| chunk | kind | `summary`, `detail`, `truth`, `event`, `enrichment` |
| link | source_kind | `wikilink`, `enrichment`, `inferred` |

Define each enum as a module-level constant inside the relevant file using `sqlalchemy.dialects.postgresql.ENUM(..., name="<lowercase_table>_<col>_enum")` so Alembic captures the enum type.

CRITICAL columns (must be present exactly):

**user.py** — table `users`:
- `id` UUID PK; `username` String(64) UNIQUE NOT NULL; `email` String(255) UNIQUE; `password_hash` Text NOT NULL; `role` ENUM nullable=False default `'user'`; `is_active` Boolean default True; TimestampMixin

**session.py** — table `sessions`:
- `id` UUID PK; `user_id` UUID FK -> users.id ON DELETE CASCADE; `token_hash` Text NOT NULL UNIQUE; `expires_at` DateTime(timezone=True) NOT NULL; `created_at` DateTime(timezone=True) server_default now()

**mcp_token.py** — table `mcp_tokens`:
- `id` UUID PK; `user_id` UUID FK -> users.id ON DELETE CASCADE; `name` String(128); `token_hash` Text NOT NULL UNIQUE; `last_used_at` DateTime(timezone=True) NULL; `revoked_at` DateTime(timezone=True) NULL; TimestampMixin

**provider_key.py** — table `provider_keys`:
- `id` UUID PK; `user_id` UUID FK -> users.id ON DELETE CASCADE; `provider` String(64) NOT NULL; `encrypted_key` `LargeBinary` NOT NULL (THIS IS BYTEA per CLAUDE.md — test acceptance verifies); `key_hint` String(32) NOT NULL; TimestampMixin
- Add a `__table_args__ = (UniqueConstraint("user_id", "provider", name="uq_provider_keys_user_provider"),)`

**vault.py** — table `vaults`:
- `id` UUID PK; `owner_user_id` UUID FK -> users.id NULL (NULL = shared); `kind` ENUM (private/shared) NOT NULL; `path` Text NOT NULL UNIQUE; TimestampMixin

**page.py** — table `pages`:
- `id` UUID PK; `vault_id` UUID FK -> vaults.id ON DELETE CASCADE; `slug` String(256) NOT NULL; `type` ENUM page_type_enum NOT NULL; `note_type` ENUM page_note_type_enum NOT NULL default `'mixed'`; `frontmatter` JSONB NOT NULL server_default `'{}'`; `compiled_truth` Text default `''`; `content_hash` String(32) NOT NULL; `enrichment_hash` String(32) NULL; `deleted_at` DateTime(timezone=True) NULL; `delete_reason` Text NULL; TimestampMixin
- `__table_args__ = (UniqueConstraint("vault_id", "slug", name="uq_pages_vault_slug"),)`

**page_version.py** — table `page_versions`:
- `id` UUID PK; `page_id` UUID FK -> pages.id ON DELETE CASCADE; `version` Integer NOT NULL; `frontmatter` JSONB NOT NULL server_default `'{}'`; `compiled_truth` Text default `''`; `content_hash` String(32) NOT NULL; `created_at` server_default now()
- `__table_args__ = (UniqueConstraint("page_id", "version", name="uq_page_versions_page_version"),)`

**chunk.py** — table `chunks`:
```python
from pgvector.sqlalchemy import VECTOR
from sqlalchemy.dialects.postgresql import TSVECTOR
# Columns:
#   id UUID PK
#   page_id UUID FK -> pages.id ON DELETE CASCADE
#   kind ENUM chunk_kind_enum
#   text Text NOT NULL
#   enriched_content Text NULL
#   tsv  TSVECTOR (computed column — define as Column with sa.Computed("to_tsvector('english', coalesce(enriched_content, text))", persisted=True) ...) — set nullable=True
#   embedding VECTOR(1536) NULL  # text-embedding-3-small
#   TimestampMixin
```

**entity.py** — table `entities`:
- `id` UUID PK; `vault_id` UUID FK -> vaults.id; `kind` ENUM entity_kind_enum (person/company/concept/idea/project); `canonical_slug` String(256) NOT NULL; `aliases` ARRAY(Text) NOT NULL server_default `'{}'`; TimestampMixin
- `__table_args__ = (UniqueConstraint("vault_id", "canonical_slug", name="uq_entities_vault_slug"),)`

**link.py** — table `links`:
- `id` UUID PK; `src_page_id` UUID FK -> pages.id ON DELETE CASCADE; `dst_entity_id` UUID FK -> entities.id ON DELETE CASCADE; `link_type` String(64) NOT NULL; `confidence` `Numeric(3, 2)` NOT NULL server_default `'1.00'`; `source_kind` ENUM link_source_kind_enum NOT NULL; TimestampMixin

**timeline_event.py** — table `timeline_events`:
- `id` UUID PK; `page_id` UUID FK -> pages.id ON DELETE CASCADE; `event_date` Date NOT NULL; `source` String(64); `detail` Text NOT NULL; `created_at` server_default now()

**tag.py** — TWO tables: `tags` and `page_tags` (D-07 allows multi-table per file when domain is a join):
- `tags`: `id` UUID PK; `vault_id` UUID FK -> vaults.id; `name` String(64) NOT NULL; UniqueConstraint(vault_id, name); TimestampMixin
- `page_tags`: composite PK `(page_id, tag_id)`; both FK with ON DELETE CASCADE

For each file, run `cd server && ruff check app/models/<file>.py` after writing and fix any issues. Use the Write tool, never heredoc.
  </action>
  <verify>
    <automated>for f in user session mcp_token provider_key vault page page_version chunk entity link timeline_event tag; do test -f "server/app/models/$f.py" || { echo "missing $f"; exit 1; }; done && grep -q 'VECTOR(1536)' server/app/models/chunk.py && grep -q 'LargeBinary' server/app/models/provider_key.py && grep -q 'UniqueConstraint("user_id", "provider"' server/app/models/provider_key.py && grep -q 'TSVECTOR' server/app/models/chunk.py && (cd server && ruff check app/models/ 2>&1 | tail -3) && (cd server && python -c "from app.models import base; from app.models import user, session, mcp_token, provider_key, vault, page, page_version, chunk, entity, link, timeline_event, tag; tables = base.Base.metadata.tables; expected = {'users','sessions','mcp_tokens','provider_keys','vaults','pages','page_versions','chunks','entities','links','timeline_events','tags','page_tags'}; missing = expected - set(tables); assert not missing, f'missing {missing}'; print('OK', sorted(tables))")</automated>
  </verify>
  <acceptance_criteria>
    - All 12 files exist under `server/app/models/`
    - `chunk.py` contains the literal `VECTOR(1536)` (CLAUDE.md: text-embedding-3-small dimension)
    - `chunk.py` contains `TSVECTOR` (BM25 column for Phase 2a)
    - `provider_key.py` contains `LargeBinary` (BYTEA per CLAUDE.md `encrypted_key` requirement)
    - `provider_key.py` contains a `UniqueConstraint` on `("user_id", "provider")`
    - `page.py` contains `JSONB` for `frontmatter`
    - `page.py` contains `deleted_at` column (soft delete per VAULT-04 deferred-but-schema-now)
    - After importing all 12 modules, `Base.metadata.tables` contains exactly the 13 table names: `users, sessions, mcp_tokens, provider_keys, vaults, pages, page_versions, chunks, entities, links, timeline_events, tags, page_tags`
    - `cd server && ruff check app/models/` exits 0
  </acceptance_criteria>
  <done>12 core model files committed; chunks.embedding is VECTOR(1536); provider_keys.encrypted_key is BYTEA; ruff clean; metadata enumerates all 13 tables.</done>
</task>

<task type="auto">
  <name>Task 3: Create remaining 16 domain model files (jobs, audit, skills, conversations, agent, observability, config)</name>
  <files>server/app/models/job.py, server/app/models/audit_log.py, server/app/models/skill.py, server/app/models/recipe.py, server/app/models/eval_candidate.py, server/app/models/conversation.py, server/app/models/memory.py, server/app/models/dream_audit_log.py, server/app/models/project.py, server/app/models/operation_log.py, server/app/models/llm_usage.py, server/app/models/index_event.py, server/app/models/user_settings.py, server/app/models/system_config.py, server/app/models/mcp_server.py, server/app/models/golden_eval.py</files>
  <read_first>
    - .planning/phases/01a-container-data-layer/01a-RESEARCH.md (Complete Domain Model List — column hints for these 15 files)
    - docs/product_requirements_document_v26.05.md (§7.1 data model — full column definitions for jobs, audit_log, skills, recipes, conversations, messages, memories, projects, llm_usage)
    - server/app/models/base.py + server/app/models/user.py (FK target)
    - CLAUDE.md (RLS discipline — multi-tenant tables MUST have user_id NOT NULL; system tables NULL)
  </read_first>
  <action>
Create the remaining 16 domain model files. Same skeleton as Task 2 (no relationships, no indexes, stubs only).

Enum values for new tables:

| Model | Enum column | Values |
|-------|------------|--------|
| job | kind | `index_page`, `enrich_entity`, `dream_consolidate`, `embed_migration`, `backup`, `cleanup` |
| job | status | `pending`, `running`, `success`, `failed`, `cancelled` |
| skill | namespace | `system`, `user` |
| recipe | namespace | `system`, `user` |
| eval_candidate | kind | `golden`, `regression`, `manual` |
| conversation | mcp_mode | `disabled`, `client`, `server` |
| message | role | `system`, `user`, `assistant`, `tool` |
| dream_audit_log | kind | `consolidate`, `audit`, `extract`, `backup` |
| dream_audit_log | status | `success`, `partial`, `failed` |
| index_event | event_type | `created`, `updated`, `deleted`, `re_indexed`, `error` |
| mcp_server | type | `stdio`, `streamable_http` |

Required columns:

**job.py** — `jobs`:
- id UUID PK; parent_id UUID FK -> jobs.id NULL (DAG support, Phase 7); kind ENUM; status ENUM default `'pending'`; payload JSONB server_default `'{}'`; idempotency_key Text NULL UNIQUE; attempts Integer default 0; last_error Text NULL; scheduled_at DateTime(timezone=True) NULL; started_at DateTime(timezone=True) NULL; finished_at DateTime(timezone=True) NULL; TimestampMixin
- Note: `apscheduler_jobs` table is INTENTIONALLY NOT a model — APScheduler manages it (CLAUDE.md). Do NOT create that model.

**audit_log.py** — `audit_log`:
- id BigInteger autoincrement PK; user_id UUID FK -> users.id NULL; action String(128) NOT NULL; target_kind String(64); target_id String(128); request_id String(64); ip INET NULL; user_agent Text NULL; created_at server_default now()

**skill.py** — `skills`:
- id UUID PK; namespace ENUM; user_id UUID FK -> users.id NULL (NULL when namespace=`system`); name String(128) NOT NULL; description Text; manifest JSONB; TimestampMixin
- UniqueConstraint(namespace, user_id, name)

**recipe.py** — `recipes`:
- id UUID PK; namespace ENUM; user_id UUID FK -> users.id NULL; name String(128) NOT NULL; yaml Text NOT NULL; TimestampMixin
- UniqueConstraint(namespace, user_id, name)

**eval_candidate.py** — `eval_candidates`:
- id UUID PK; user_id UUID FK -> users.id ON DELETE CASCADE; kind ENUM; query Text NOT NULL; retrieved_slugs ARRAY(Text) server_default `'{}'`; metrics JSONB server_default `'{}'`; created_at server_default now()

**conversation.py** — TWO tables: `conversations` and `messages`:
- conversations: id UUID PK; user_id UUID FK -> users.id ON DELETE CASCADE; title String(256); mcp_mode ENUM default `'client'`; web_search_enabled Boolean default False; project_id UUID FK -> projects.id NULL; TimestampMixin
- messages: id UUID PK; conversation_id UUID FK -> conversations.id ON DELETE CASCADE; role ENUM; content Text NOT NULL; citations JSONB server_default `'[]'`; tool_calls JSONB server_default `'[]'`; created_at server_default now()
- IMPORTANT: `project_id` references `projects.id` which is defined in `project.py` below. Use `ForeignKey("projects.id", ondelete="SET NULL")` — string-based FK; do not import projects.

**memory.py** — `memories`:
- id UUID PK; user_id UUID FK -> users.id ON DELETE CASCADE; content Text NOT NULL; source_conversation_id UUID FK -> conversations.id NULL ON DELETE SET NULL; archived Boolean default False; TimestampMixin

**dream_audit_log.py** — `dream_audit_log`:
- id BigInteger autoincrement PK; user_id UUID FK -> users.id ON DELETE CASCADE NULL; run_at DateTime(timezone=True) NOT NULL server_default now(); kind ENUM; status ENUM; pages_processed Integer default 0; details JSONB server_default `'{}'`

**project.py** — `projects`:
- id UUID PK; user_id UUID FK -> users.id ON DELETE CASCADE; name String(128) NOT NULL; folder_patterns ARRAY(Text) server_default `'{}'`; tag_includes ARRAY(Text) server_default `'{}'`; system_prompt Text; TimestampMixin

**operation_log.py** — `operation_log`:
- id BigInteger autoincrement PK; user_id UUID FK -> users.id NULL; operation String(128) NOT NULL; target_kind String(64); target_id String(128); payload JSONB server_default `'{}'`; created_at server_default now()

**llm_usage.py** — `llm_usage`:
- id BigInteger autoincrement PK; user_id UUID FK -> users.id ON DELETE CASCADE; provider String(64) NOT NULL; model String(128) NOT NULL; input_tokens Integer NOT NULL default 0; output_tokens Integer NOT NULL default 0; cost_usd `Numeric(12, 6)` NOT NULL default 0; conversation_id UUID FK -> conversations.id NULL ON DELETE SET NULL; created_at server_default now()

**index_event.py** — `index_events`:
- id BigInteger autoincrement PK; user_id UUID FK -> users.id ON DELETE CASCADE NULL; event_type ENUM; page_slug String(256); details JSONB server_default `'{}'`; created_at server_default now()

**user_settings.py** — `user_settings`:
- user_id UUID PK FK -> users.id ON DELETE CASCADE; settings JSONB NOT NULL server_default `'{}'`; updated_at server_default now() onupdate now()

**system_config.py** — `system_config`:
- key Text PRIMARY KEY; value JSONB NOT NULL; updated_at server_default now() onupdate now()

**mcp_server.py** — `mcp_servers`:
- id UUID PK; name String(128) NOT NULL UNIQUE; type ENUM (stdio/streamable_http); command String(256); args ARRAY(Text) server_default `'{}'`; always_allow ARRAY(Text) server_default `'{}'`; enabled Boolean default True; TimestampMixin

**golden_eval.py** — THREE tables:
- `golden_query_suites`: id UUID PK; scope ENUM (system/user); user_id UUID FK -> users.id NULL; name String(128) NOT NULL; TimestampMixin
- `golden_queries`: id UUID PK; suite_id UUID FK -> golden_query_suites.id ON DELETE CASCADE; query Text NOT NULL; expected_slugs ARRAY(Text) server_default `'{}'`; tags ARRAY(Text) server_default `'{}'`; TimestampMixin
- `golden_query_runs`: id UUID PK; query_id UUID FK -> golden_queries.id ON DELETE CASCADE; metrics JSONB NOT NULL; ran_at server_default now()

For each file: write, ruff check the single file, fix issues, move on.
  </action>
  <verify>
    <automated>for f in job audit_log skill recipe eval_candidate conversation memory dream_audit_log project operation_log llm_usage index_event user_settings system_config mcp_server golden_eval; do test -f "server/app/models/$f.py" || { echo "missing $f"; exit 1; }; done && (cd server && ruff check app/models/ 2>&1 | tail -3) && (cd server && python -c "
from app.models import base, user, session, mcp_token, provider_key, vault, page, page_version, chunk, entity, link, timeline_event, tag
from app.models import job, audit_log, skill, recipe, eval_candidate, conversation, memory, dream_audit_log, project, operation_log, llm_usage, index_event, user_settings, system_config, mcp_server, golden_eval
tables = set(base.Base.metadata.tables.keys())
expected = {'users','sessions','mcp_tokens','provider_keys','vaults','pages','page_versions','chunks','entities','links','timeline_events','tags','page_tags','jobs','audit_log','skills','recipes','eval_candidates','conversations','messages','memories','dream_audit_log','projects','operation_log','llm_usage','index_events','user_settings','system_config','mcp_servers','golden_query_suites','golden_queries','golden_query_runs'}
missing = expected - tables
extra = tables - expected
assert not missing, f'missing tables: {missing}'
assert 'apscheduler_jobs' not in tables, 'apscheduler_jobs MUST NOT be in metadata (CLAUDE.md)'
print(f'OK {len(tables)} tables registered:', sorted(tables))
")</automated>
  </verify>
  <acceptance_criteria>
    - All 16 files exist under `server/app/models/` (each file declares 1-3 related tables; golden_eval.py and conversation.py declare multiple per D-07)
    - `Base.metadata.tables` contains all 32 tables: users, sessions, mcp_tokens, provider_keys, vaults, pages, page_versions, chunks, entities, links, timeline_events, tags, page_tags, jobs, audit_log, skills, recipes, eval_candidates, conversations, messages, memories, dream_audit_log, projects, operation_log, llm_usage, index_events, user_settings, system_config, mcp_servers, golden_query_suites, golden_queries, golden_query_runs
    - `apscheduler_jobs` is NOT in `Base.metadata.tables` (CLAUDE.md anti-pattern)
    - `cd server && ruff check app/models/` exits 0
    - `conversation.py` defines BOTH `Conversation` and `Message` classes
    - `golden_eval.py` defines all three classes for the three golden_query_* tables
    - Multi-tenant tables (memories, projects, llm_usage, eval_candidates) all have `user_id` FK NOT NULL with `ondelete="CASCADE"` (RLS prerequisite per CLAUDE.md; CREATE POLICY itself deferred to Phase 1b)
  </acceptance_criteria>
  <done>16 additional model files committed; total 32 tables in Base.metadata; apscheduler_jobs excluded; ruff clean.</done>
</task>

<task type="auto">
  <name>Task 4: Aggregate model imports in models/__init__.py + verify full schema registers</name>
  <files>server/app/models/__init__.py</files>
  <read_first>
    - server/app/models/ (every model file created in tasks 1-3)
    - .planning/phases/01a-container-data-layer/01a-RESEARCH.md (Pattern 4 alembic env.py expects all models importable)
  </read_first>
  <action>
Replace `server/app/models/__init__.py` with the full aggregate import. The purpose of this module is: importing `app.models` MUST trigger registration of every domain table on `Base.metadata`. This is what `alembic/env.py` (Plan 03) relies on for autogenerate.

```python
"""Domain models package — aggregate import for Alembic autogenerate.

Per D-05/D-06: every domain model defined up-front; single 0001_initial_schema.py
migration. Importing this package MUST cause every table to be registered with
Base.metadata so that alembic/env.py sees the complete schema.

Per D-07: one file per domain. The `tag` and `conversation` and `golden_eval`
modules each define multiple closely-related tables (page_tags join, messages,
golden_query_*); this is allowed under D-07.
"""
from app.models.base import Base, TimestampMixin

# Auth + identity
from app.models import user, session, mcp_token, provider_key  # noqa: F401

# Vault + content
from app.models import vault, page, page_version, chunk, entity, link  # noqa: F401
from app.models import timeline_event, tag  # noqa: F401

# Background jobs + audit
from app.models import job, audit_log  # noqa: F401

# Skills, recipes, eval
from app.models import skill, recipe, eval_candidate  # noqa: F401

# Agent: conversations, memories, dream
from app.models import conversation, memory, dream_audit_log  # noqa: F401

# Projects + operation log
from app.models import project, operation_log  # noqa: F401

# Observability
from app.models import llm_usage, index_event  # noqa: F401

# Configuration
from app.models import user_settings, system_config, mcp_server  # noqa: F401

# Golden eval (Phase 2b)
from app.models import golden_eval  # noqa: F401

__all__ = ["Base", "TimestampMixin"]
```

The `# noqa: F401` markers are required because Ruff's F401 rule flags unused imports; these imports are used for their side effects (model class registration). The Ruff config in pyproject.toml does NOT exempt F401 globally.
  </action>
  <verify>
    <automated>grep -c '^from app\.models import' server/app/models/__init__.py | xargs test 11 -le && (cd server && ruff check app/models/__init__.py) && (cd server && python -c "
import app.models
from app.models import Base
tables = sorted(Base.metadata.tables.keys())
expected = {'users','sessions','mcp_tokens','provider_keys','vaults','pages','page_versions','chunks','entities','links','timeline_events','tags','page_tags','jobs','audit_log','skills','recipes','eval_candidates','conversations','messages','memories','dream_audit_log','projects','operation_log','llm_usage','index_events','user_settings','system_config','mcp_servers','golden_query_suites','golden_queries','golden_query_runs'}
missing = expected - set(tables)
assert not missing, f'missing: {missing}'
print(f'OK total={len(tables)}')
")</automated>
  </verify>
  <acceptance_criteria>
    - `server/app/models/__init__.py` contains at least 11 lines starting with `from app.models import` (covers every model module group)
    - Every `from app.models import ...` line that imports model modules has a `# noqa: F401` marker (Ruff F401 compliance for side-effect imports)
    - `python -c "import app.models; print(len(app.models.Base.metadata.tables))"` prints `32`
    - `python -c "import app.models; assert 'apscheduler_jobs' not in app.models.Base.metadata.tables"` exits 0
    - `cd server && ruff check app/` exits 0 across the entire app/ tree
  </acceptance_criteria>
  <done>Importing app.models registers all 32 tables on Base.metadata; ruff clean across the full app/ tree; ready for Plan 03 alembic/env.py to consume.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| ORM column type -> PostgreSQL column | Schema-level type safety: encrypted_key MUST be BYTEA (LargeBinary), embedding MUST be VECTOR(1536) |
| models/ -> alembic autogenerate | Side-effect imports in `__init__.py` are the only mechanism by which Alembic discovers tables; missing import = silent schema gap in Plan 03 migration |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-1a-05 | Tampering | `provider_keys.encrypted_key` schema | mitigate | Column type is `LargeBinary` (BYTEA) per CLAUDE.md so Fernet ciphertext bytes round-trip without text encoding ambiguity. Acceptance criterion `grep -q 'LargeBinary' server/app/models/provider_key.py` enforces this |
| T-1a-06 | Information Disclosure | aggregate import in `models/__init__.py` | accept | Side-effect imports are required for Alembic autogenerate. Marked `# noqa: F401`; documented at module top so future reviewers understand intent |
| T-1a-07 | Denial of Service | `apscheduler_jobs` accidentally in Base.metadata | mitigate | No `apscheduler_jobs` model file is created. Acceptance criterion verifies `'apscheduler_jobs' not in Base.metadata.tables`. Plan 03 alembic/env.py adds an `include_object` filter as a second-line defense per Pitfall 4 |
</threat_model>

<verification>
- All 28 domain model module files exist under server/app/models/
- Importing `app.models` produces exactly 32 tables in `Base.metadata` (count verified)
- `chunks` table has `embedding` column of type `VECTOR(1536)` and `tsv` of type `TSVECTOR`
- `provider_keys.encrypted_key` is BYTEA (`LargeBinary` in SQLAlchemy)
- No `apscheduler_jobs` table appears anywhere in `Base.metadata.tables`
- `cd server && ruff check app/` exits 0
</verification>

<success_criteria>
- D-05 satisfied: complete schema in 28 domain model module files (one file per domain per D-07; tag/conversation/golden_eval each declare multiple closely-related tables)
- 32 tables registered on `Base.metadata` (D-05 complete schema)
- pgvector VECTOR(1536) on chunks.embedding (CLAUDE.md text-embedding-3-small)
- BYTEA on provider_keys.encrypted_key (CLAUDE.md crypto pattern)
- apscheduler_jobs intentionally excluded (CLAUDE.md anti-pattern)
- Ruff clean — establishes the convention for all subsequent phases
</success_criteria>

<output>
After completion, create `.planning/phases/01a-container-data-layer/01a-02-SUMMARY.md` with:
- Final list of model files (28 domain modules) and table count (32)
- Any enum names introduced (so Plan 03 alembic migration knows the type names)
- Any deviations from the spec (e.g., column types changed because PRD was more specific)
</output>
