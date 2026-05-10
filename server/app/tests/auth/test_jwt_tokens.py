"""AUTH-02 unit tests — JWT HS256 allowlist + claim discipline."""
from __future__ import annotations

import time
import uuid

import pytest
from jose import jwt
from jose.exceptions import JWTError

from app.auth.tokens import decode_access_jwt, issue_access_jwt

pytestmark = [pytest.mark.auth, pytest.mark.unit]

_SIGNING = "test-signing-key-min-32-bytes-for-hs256-aaaaaaaa"


def test_jwt_roundtrip_includes_sub_role_jti() -> None:
    uid = uuid.uuid4()
    token = issue_access_jwt(user_id=uid, role="admin", signing_key=_SIGNING, ttl_seconds=900)
    claims = decode_access_jwt(token, _SIGNING)
    assert claims["sub"] == str(uid)
    assert claims["role"] == "admin"
    assert "jti" in claims
    assert "exp" in claims and claims["exp"] > claims["iat"]


def test_decode_rejects_alg_none() -> None:
    # Construct an alg=none token directly (bypasses jwt.encode signing)
    import base64
    import json
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(json.dumps({"sub": "x", "role": "admin", "jti": "j", "exp": 9999999999}).encode()).rstrip(b"=").decode()
    unsigned = f"{header}.{payload}."
    with pytest.raises(JWTError):
        decode_access_jwt(unsigned, _SIGNING)


def test_decode_rejects_alg_confusion() -> None:
    # Token signed with RS256 must NOT verify under our HS256 decoder
    # (we don't have an RSA key here; the simpler proof: token signed with
    # a *different* algorithm is rejected by the algorithms=[ALGORITHM] gate)
    token_other_alg = jwt.encode(
        {"sub": "x", "role": "admin", "jti": "j", "exp": 9999999999, "iat": 0, "nbf": 0},
        _SIGNING,
        algorithm="HS512",  # different from our HS256 allowlist
    )
    with pytest.raises(JWTError):
        decode_access_jwt(token_other_alg, _SIGNING)


def test_jwt_expiry_enforced() -> None:
    # ttl=1 second; sleep beyond it
    token = issue_access_jwt(user_id=uuid.uuid4(), role="user", signing_key=_SIGNING, ttl_seconds=1)
    time.sleep(2)
    with pytest.raises(JWTError):
        decode_access_jwt(token, _SIGNING)


def test_decode_uses_explicit_algorithms_allowlist() -> None:
    """Source-level guard — Landmine #2. The decode body must include algorithms=[ALGORITHM]."""
    import inspect

    from app.auth import tokens as t
    src = inspect.getsource(t.decode_access_jwt)
    assert "algorithms=[ALGORITHM]" in src or 'algorithms=["HS256"]' in src, (
        "decode_access_jwt MUST pass algorithms=['HS256'] (non-empty list) — Landmine #2"
    )
    assert "algorithms=None" not in src and "algorithms=[]" not in src