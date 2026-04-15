---
domain: backend
name: api-design
updated: 2026-04-15
confidence: 1.0
tags: [api, rest, sse, fastapi, pydantic, errors]
---
# API Design Standards

> Source: PRD Sections 15–16; ~103 endpoints across 14 route groups

## Rule: Use FastAPI with Pydantic v2 for validation

All request bodies validated via Pydantic BaseModel schemas. All response models typed. FastAPI auto-generates OpenAPI spec consumed by the frontend codegen pipeline.

## Rule: Standard error response format

```json
{
  "detail": "Human-readable error message",
  "code": "MACHINE_READABLE_CODE"
}
```

| Status | Code | Usage |
|---|---|---|
| 400 | VALIDATION_ERROR | Request body validation failed |
| 401 | UNAUTHORIZED | Missing or invalid JWT |
| 403 | FORBIDDEN | Insufficient role |
| 404 | NOT_FOUND | Resource not found or not visible via RLS |
| 409 | CONFLICT | Resource already exists |
| 429 | RATE_LIMITED | Per-user rate limit exceeded (include retry_after_seconds) |
| 500 | INTERNAL_ERROR | Unexpected server error |

## Rule: SSE for streaming, REST for CRUD

No WebSocket. Chat uses POST-initiated SSE. 9 SSE event types: status, citations, token, tool_start, tool_result, tool_confirm, client_request, notification, done. SSE stream not resumable — each POST is self-contained.

## Rule: API versioning via path prefix

All endpoints under `/api/v1/`. Health check at `/health` (no version prefix).

## Rule: OpenAPI spec is the runtime source of truth

Backend auto-generates `openapi.json` from FastAPI routes. Client runs `pnpm codegen` to generate TypeScript types. CI fails if types don't match committed spec.
