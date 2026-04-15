---
domain: backend
name: auth
updated: 2026-04-15
confidence: 1.0
tags: [auth, jwt, security, tokens, passwords, python, fastapi]
---
# Authentication Standards

> Source: PRD Decisions 21, 23, 24; F-AUTH-01, F-AUTH-02

## Rule: Use python-jose for JWT operations

The backend uses `python-jose` for stateless JWT authentication. Access tokens: 24h. Refresh tokens: 30d. Both configurable via settings.yaml.

```python
# ✅ Correct: python-jose
from jose import jwt, JWTError

def create_access_token(user_id: UUID, secret: str, expires_minutes: int = 1440) -> str:
    payload = {"sub": str(user_id), "exp": datetime.utcnow() + timedelta(minutes=expires_minutes)}
    return jwt.encode(payload, secret, algorithm="HS256")
```

## Rule: Store tokens in Electron safeStorage, not localStorage

Electron safeStorage uses OS-level encryption (macOS Keychain, Windows DPAPI). Tokens are never stored in localStorage or cookies.

CSRF protection is not implemented because the API uses `Authorization: Bearer` headers exclusively (not cookies). If the API is ever exposed to a browser-based client, CSRF protection must be added.

## Rule: Unprotected routes are explicitly listed

Only these routes require no JWT: `GET /health`, `POST /api/v1/auth/login`, `POST /api/v1/auth/register` (first user only), `POST /api/v1/auth/refresh`.

## Rule: Two roles only — admin and user

First user = admin. `require_admin` FastAPI dependency for admin-only endpoints. No custom role hierarchies.

```python
async def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
```

## Rule: Hash passwords with argon2-cffi

Never store plaintext passwords. Use `argon2-cffi` directly (not via passlib). argon2-cffi's API is straightforward; the passlib wrapper adds unnecessary abstraction.

```python
# ✅ Correct: argon2-cffi directly
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

ph = PasswordHasher()

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(password: str, hash: str) -> bool:
    try:
        return ph.verify(hash, password)
    except VerifyMismatchError:
        return False
```

## Rule: RLS SET/RESET every database session

Every route handler uses `Depends(get_db)` which sets and resets `app.current_user_id`. RESET must be in the `finally` block. Background tasks use `get_db_session(user_id)` directly.

```python
@asynccontextmanager
async def get_db_session(user_id: UUID):
    async with async_session_factory() as session:
        await session.execute(text("SET app.current_user_id = :uid"), {"uid": str(user_id)})
        try:
            yield session; await session.commit()
        except: await session.rollback(); raise
        finally:
            await session.execute(text("RESET app.current_user_id"))
```
