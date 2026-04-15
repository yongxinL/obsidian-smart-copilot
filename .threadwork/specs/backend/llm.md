---
domain: backend
name: llm
updated: 2026-04-15
confidence: 1.0
tags: [litellm, llm, providers, embedding, streaming]
---
# LLM Integration Standards

> Source: PRD Decisions 3, 7, 13; F-LLM-01

## Rule: LiteLLM as in-process library — no gateway service

```python
from litellm import acompletion, aembedding
```

Zero network hops. No separate LLM gateway container. Callbacks log to PostgreSQL.

## Rule: Model IDs use LiteLLM format

`provider/model-name` is the canonical format: `anthropic/claude-sonnet-4-20250514`, `openai/gpt-4o`, `ollama/qwen3:8b`. The `GET /api/v1/models` endpoint returns models from server config.

## Rule: Key resolution order

User personal key → shared key → error with message. Track `key_type` (personal/shared) on every LLM call in `llm_usage` table.

## Rule: LiteLLM callbacks for cost tracking

```python
litellm.success_callback = [log_usage]
litellm.failure_callback = [log_failure]
```

Log to `llm_usage` table: user_id, model, provider, prompt_tokens, completion_tokens, cost_usd, latency_ms, status, purpose, key_type.

## Rule: Purpose tracking on all LLM calls

Every LLM call must set a `purpose` field: `chat`, `embedding`, `agent`, `enrichment`, `dream`, `mcp_tool`.
