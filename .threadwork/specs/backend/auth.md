---
domain: backend
name: auth
updated: 2025-01-01
confidence: 0.9
tags: [auth, jwt, security, tokens, passwords, sessions]
---
# Authentication Standards

## Rule: Use jose for JWT operations (not jsonwebtoken)

`jose` is the recommended JWT library for modern JS/TS runtimes (works in Edge, Cloudflare Workers, Deno, and Node).
`jsonwebtoken` is Node.js-only and uses synchronous crypto.

```typescript
// ✅ Correct: use jose
import { SignJWT, jwtVerify } from 'jose';

const secret = new TextEncoder().encode(process.env.JWT_SECRET);

export async function signToken(payload: Record<string, unknown>): Promise<string> {
  return new SignJWT(payload)
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime('1h')
    .sign(secret);
}

export async function verifyToken(token: string) {
  const { payload } = await jwtVerify(token, secret);
  return payload;
}
```

```typescript
// ❌ Anti-pattern: avoid jsonwebtoken
import jwt from 'jsonwebtoken'; // sync, Node.js only
```

---

## Rule: Store JWTs in httpOnly cookies, not localStorage

httpOnly cookies are not accessible from JavaScript — they prevent XSS token theft.
localStorage is readable by any script on the page.

```typescript
// ✅ Correct: httpOnly cookie
response.cookies.set('auth-token', token, {
  httpOnly: true,
  secure: process.env.NODE_ENV === 'production',
  sameSite: 'lax',
  maxAge: 60 * 60, // 1 hour in seconds
  path: '/',
});
```

```typescript
// ❌ Anti-pattern: localStorage
localStorage.setItem('token', token); // XSS vulnerable
```

---

## Rule: Always hash passwords with bcrypt (cost factor ≥ 12)

Never store plaintext passwords. Never use MD5, SHA1, or SHA256 for passwords — they are not password-specific.

```typescript
// ✅ Correct
import bcrypt from 'bcryptjs';

const SALT_ROUNDS = 12;

export async function hashPassword(password: string): Promise<string> {
  return bcrypt.hash(password, SALT_ROUNDS);
}

export async function verifyPassword(password: string, hash: string): Promise<boolean> {
  return bcrypt.compare(password, hash);
}
```

---

## Rule: Implement refresh token rotation

Access tokens should be short-lived (15min–1h). Refresh tokens should be rotated on each use (prevents token reuse after theft).

```typescript
// ✅ Correct pattern: invalidate old refresh token, issue new one
async function refreshTokens(refreshToken: string) {
  const stored = await db.refreshToken.findUnique({ where: { token: refreshToken } });
  if (!stored || stored.expiresAt < new Date()) throw new Error('Invalid refresh token');

  // Rotate: delete old, create new
  await db.refreshToken.delete({ where: { id: stored.id } });
  const newRefreshToken = await db.refreshToken.create({
    data: { userId: stored.userId, expiresAt: addDays(new Date(), 30) }
  });

  const accessToken = await signToken({ sub: stored.userId });
  return { accessToken, refreshToken: newRefreshToken.token };
}
```
