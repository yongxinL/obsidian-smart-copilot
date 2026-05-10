"""JWT issuance and decoding — HS256 with explicit allowlist (Landmine #2).

AUTH-02 / D-04: claims = sub, role, jti, iat, exp, nbf.
Landmine #2: algorithms=["HS256"] (non-empty list) is non-negotiable.
Never algorithms=None, never algorithms=[]. Floor: python-jose >= 3.4.
CVE-2024-33663 (alg confusion) and CVE-2025-61152 (alg=none) fixed in 3.4.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from jose import jwt

ALGORITHM = "HS256"


def issue_access_jwt(
    *,
    user_id: uuid.UUID,
    role: str,
    signing_key: str,
    ttl_seconds: int,
    session_id: uuid.UUID | None = None,
) -> str:
    """Issue a short-lived (D-01: 15-min default) HS256 JWT.

    When `session_id` is provided (refresh-issued tokens carry it), embed
    it as the optional `sid` claim. Plan 05 task 05-01's `validate_jwt`
    reads it into AuthResult.session_id; Plan 06 task 06-04's
    require_fresh_auth uses it to load sessions.admin_fresh_until.
    """
    now = datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "role": role,
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
    }
    if session_id is not None:
        claims["sid"] = str(session_id)
    return jwt.encode(claims, signing_key, algorithm=ALGORITHM)


def decode_access_jwt(token: str, signing_key: str) -> dict:
    """Decode with explicit algorithms allowlist — Landmine #2.

    Raises jose.JWTError on any failure (signature, expiry, missing claim,
    wrong algorithm, alg=none). Caller maps to transport-specific 401.
    """
    return jwt.decode(
        token,
        signing_key,
        algorithms=[ALGORITHM],  # MUST be non-empty list — never None / never []
        options={"require": ["sub", "role", "jti", "exp"]},
    )