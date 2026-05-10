"""MCP bearer token generation + SHA-256 hash helper (AUTH-04).

Plaintext shown ONCE at issuance; storage column holds only the SHA-256 hex.
Prefix scmcp_ makes leak detection / code search obvious.
Entropy: 256 bits via secrets.token_urlsafe(32).
"""

from __future__ import annotations

import hashlib
import secrets

PREFIX = "scmcp_"


def generate_token() -> tuple[str, str, str]:
    """Returns (plaintext, sha256_hex, last4).

    Plaintext is shown ONCE to the operator at issuance and never persisted.
    The DB stores only the sha256_hex; verify_token (Plan 06 services) hashes
    the candidate and looks up by hash.
    """
    raw = secrets.token_urlsafe(32)  # 32 bytes random -> ~43 base64 chars -> 256 bits
    plaintext = PREFIX + raw
    token_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    last4 = plaintext[-4:]
    return plaintext, token_hash, last4


def sha256_token_hash(plaintext: str) -> str:
    """Compute the storage hash for an inbound bearer plaintext (verify path)."""
    return hashlib.sha256(plaintext.encode()).hexdigest()
