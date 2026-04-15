---
domain: backend
name: database
updated: 2026-04-15
confidence: 1.0
tags: [postgresql, pgvector, rls, sqlalchemy, alembic, asyncpg]
---
# Database Standards

> Source: PRD Decisions 1, 4, 5, 23; Section 5

## Rule: PostgreSQL-only RAG backend

All retrieval in PostgreSQL + pgvector: vector (HNSW), BM25 (tsvector), wikilink graph (recursive CTEs) — single query. No external search services. `RAGBackend` interface for future extension.

## Rule: SQLAlchemy 2.0 async ORM + Alembic migrations

All database operations via SQLAlchemy async ORM with asyncpg driver. Schema changes via Alembic migrations only. 17 models total.

## Rule: RLS on all 14 user-scoped tables

Content tables (documents, chunks, wikilinks): `namespace = 'shared' OR user_id = current_setting('app.current_user_id')::uuid`
Private tables (conversations, messages, memories, etc.): `user_id = current_setting('app.current_user_id')::uuid`
API keys: `user_id IS NULL OR user_id = current_setting('app.current_user_id')::uuid`

## Rule: Shared tables + RLS, not per-user schemas

Single table set with `user_id` + `namespace` columns. Never create per-user schemas.

## Rule: Hybrid namespace from day one

`/vaults/private/{username}/` + `/vaults/shared/`. SYSTEM_USER_ID `00000000-0000-0000-0000-000000000000` owns shared content.

## Rule: API keys encrypted with Fernet

API keys stored as `encrypted_key` using `cryptography.fernet.Fernet`. `ENCRYPTION_KEY` env var is the only secret. `encrypted_key` NEVER returned to client — only `display_hint`.

## Rule: xxhash for content and enrichment hashing

`content_hash`: XXH64 of raw file bytes (full file including frontmatter). `enrichment_hash`: XXH64 of `title + folder + tags + sorted(backlinks) + sorted(outlinks)`. Both stored as 16-character hex strings.

## Rule: Chunk replacement via SAVEPOINT

Atomic delete-and-recreate within SAVEPOINT. If embedding fails, DELETE rolls back and old chunks restored. Note is never unsearchable.
