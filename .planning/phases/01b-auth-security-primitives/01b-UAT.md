---
status: complete
phase: 01b-auth-security-primitives
source: [01B-01-SUMMARY.md, 01B-02-SUMMARY.md, 01B-03-SUMMARY.md, 01B-04-SUMMARY.md, 01B-05-SUMMARY.md, 01B-06-SUMMARY.md, 01B-07-SUMMARY.md, 01B-08-SUMMARY.md]
started: 2026-05-10T05:30:00Z
updated: 2026-05-10T06:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. CLI user creation
expected: Running `smartcopilot user create --username alice --role admin` creates a user without errors
result: pass

### 2. JWT access token issued on login
expected: After password verification, server issues a JWT access token (15 min TTL) and refresh token (30 day TTL)
result: pass

### 3. MCP bearer token generation
expected: `smartcopilot mcp token create --user alice` generates a 256-bit entropy token, displays plaintext once, and stores SHA-256 hash
result: pass

### 4. Fernet-encrypted provider keys
expected: Provider API keys stored via `smartcopilot provider key set` are encrypted at rest (not visible as plaintext in DB)
result: pass

### 5. Rate-limit blocks brute force
expected: After 10 failed login attempts within 15 minutes, the 11th attempt returns 429 before password check
result: pass

### 6. RLS isolation between users
expected: User A cannot see User B's pages, tokens, or sessions in database queries
result: skipped
reason: needs multi-user setup — can be verified separately

### 7. Trusted proxy XFF handling
expected: When X-Forwarded-For comes from an allowed CIDR, the client IP is extracted from the rightmost trusted hop
result: pass

### 8. Admin step-up fresh auth
expected: After `/api/v1/admin/reauth` with valid password, `admin_fresh_until` is stamped and protected routes accept requests for 60 minutes
result: pass

### 9. Fernet startup validation
expected: Server fails fast on startup with FATAL if SMARTCOPILOT_FERNET_KEY is not set
result: pass

### 10. MCP token revocation
expected: `smartcopilot mcp token revoke <id>` takes effect on next verify (revoked token rejected)
result: pass

## Summary

total: 10
passed: 9
issues: 0
pending: 0
skipped: 1

## Gaps

[none — all tests passed or intentionally skipped]
