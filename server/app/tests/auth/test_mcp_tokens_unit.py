"""AUTH-04 unit tests — MCP bearer token entropy + hashing."""

from __future__ import annotations

import hashlib

import pytest

from app.auth.mcp_tokens import PREFIX, generate_token, sha256_token_hash

pytestmark = [pytest.mark.auth, pytest.mark.unit]


def test_token_is_256_bits() -> None:
    """secrets.token_urlsafe(32) provides 32 bytes = 256 bits of entropy."""
    plaintext, _, _ = generate_token()
    body = plaintext.removeprefix(PREFIX)
    # urlsafe base64 of 32 raw bytes = 43 chars (no padding)
    assert len(body) >= 43
    # Ensure two consecutive calls produce different tokens (sanity check on entropy)
    assert generate_token()[0] != plaintext


def test_token_uses_scmcp_prefix() -> None:
    plaintext, _, last4 = generate_token()
    assert plaintext.startswith("scmcp_")
    assert plaintext.endswith(last4)


def test_hash_is_sha256_hex() -> None:
    plaintext, token_hash, _ = generate_token()
    assert token_hash == hashlib.sha256(plaintext.encode()).hexdigest()
    assert len(token_hash) == 64  # sha256 hex
    assert all(c in "0123456789abcdef" for c in token_hash)
    # Verify path agrees
    assert sha256_token_hash(plaintext) == token_hash
