---
domain: backend
name: rag
updated: 2026-04-15
confidence: 1.0
tags: [rag, hybrid-search, rrf, enrichment, chunking, pgvector]
---
# RAG Standards

> Source: PRD Decision 2; F-RAG-01, F-RAG-02; Section 21

## Rule: Hybrid retrieval with three signals

`final_score = (0.5 × vector_cosine) + (0.3 × BM25) + (0.2 × wikilink_proximity)`

Combined via Reciprocal Rank Fusion (RRF) with k=60 in a single PostgreSQL query. Weights are user-configurable but must sum to 1.0.

## Rule: Contextual enrichment before embedding

Prepend metadata before embedding every note:
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

Enrichment prefix < 25% of total embedded text.

## Rule: Chunking parameters

| Parameter | Default |
|---|---|
| chunk_size_tokens | 512 |
| chunk_overlap_tokens | 64 |
| min_chunk_tokens | 50 |
| respect_boundaries | paragraph |
| single_chunk_threshold | 600 |

Separator hierarchy: `\n## ` → `\n### ` → `\n\n` → `\n- ` → `\n` → `. ` → ` `. Code blocks and blockquotes never split mid-block.

## Rule: Three search contexts

| Context | Returns |
|---|---|
| knowledge | permanent notes only |
| citation | literature notes only |
| all | all indexed types except skill |

Skill notes excluded from ALL RAG contexts. Project notes only via frontmatterQuery. Conversation notes only via `all` or memoryRecall.

## Rule: Cascading re-enrichment limited to 1 hop

When wikilinks change, linked documents marked for enrichment_hash recalculation. Depth limited to 1 hop. Never cascade further.

## Rule: Note type gating at indexer

`archived_fleeting` and `skill` types skip the enrich → chunk → embed pipeline entirely. documents record created (metadata), but no chunks rows.
