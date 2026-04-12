---
domain: backend
name: api-design
updated: 2025-01-01
confidence: 0.9
tags: [api, rest, http, responses, errors, typescript]
---
# API Design Standards

## Rule: Use consistent response envelope format

All API responses must use a consistent envelope:

```typescript
// ✅ Success response
{
  "data": { ... },
  "meta": { "timestamp": "2025-08-01T12:00:00Z" }
}

// ✅ Error response
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Email is required",
    "details": { "field": "email" }
  }
}
```

```typescript
// ❌ Anti-pattern: inconsistent shapes
{ "user": { ... } }   // different key each endpoint
{ "status": "error", "msg": "bad" }  // no structure
```

---

## Rule: Use HTTP status codes correctly

| Status | When to use |
|--------|-------------|
| 200 | Successful GET, PUT, PATCH |
| 201 | Successful POST (resource created) |
| 204 | Successful DELETE (no body) |
| 400 | Validation error, malformed request |
| 401 | Not authenticated |
| 403 | Authenticated but not authorized |
| 404 | Resource not found |
| 409 | Conflict (e.g., duplicate email) |
| 422 | Unprocessable entity (business logic rejection) |
| 500 | Unexpected server error |

Never return 200 for errors. Never return 500 for client errors.

---

## Rule: Validate all input at the API boundary

All request bodies, query params, and path params must be validated before use. Use Zod for schema validation in TypeScript projects.

```typescript
// ✅ Correct
import { z } from 'zod';

const createUserSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8).max(100),
  name: z.string().min(1).max(100),
});

export async function POST(req: Request) {
  const body = await req.json();
  const result = createUserSchema.safeParse(body);
  if (!result.success) {
    return Response.json({ error: { code: 'VALIDATION_ERROR', details: result.error.flatten() } }, { status: 400 });
  }
  // result.data is now typed and validated
}
```

---

## Rule: Never expose internal errors to clients

Catch all errors in API handlers. Log the full error internally but return only a safe message to the client.

```typescript
// ✅ Correct
try {
  const user = await createUser(data);
  return Response.json({ data: user }, { status: 201 });
} catch (err) {
  console.error('[createUser]', err);
  return Response.json({ error: { code: 'INTERNAL_ERROR', message: 'Failed to create user' } }, { status: 500 });
}
```
