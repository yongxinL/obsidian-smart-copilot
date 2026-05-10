"""Fernet/MultiFernet seam for provider API keys at rest (D-24).

AUTH-09 / PRD §24.2: provider keys are encrypted with Fernet AES-128-CBC + HMAC.
MultiFernet is wired from day 1 so rotation is a one-line list extension later.

Landmine #4: decrypt_provider_key MUST NOT pass ttl= — Fernet's TTL is
"seconds since ciphertext was created", which would silently expire valid
at-rest keys. Default ttl=None disables expiry. CI grep gate in Plan 08
rejects any decrypt(...,ttl=...) call.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, MultiFernet

from app.settings import settings


class FernetKeyMissing(RuntimeError):
    """Raised when SMARTCOPILOT_FERNET_KEY is empty or missing at startup."""


_cached: MultiFernet | None = None


def _build_multifernet() -> MultiFernet:
    """Build the MultiFernet from settings.smartcopilot_fernet_key.

    Why MultiFernet from day 1 (D-24): future rotation is `MultiFernet([new, primary])`
    — one-line change, no call-site touches. Fernet ciphertexts produced now
    will still decrypt under any future MultiFernet that includes this key.
    """
    key = settings.smartcopilot_fernet_key
    if not key:
        raise FernetKeyMissing("SMARTCOPILOT_FERNET_KEY env var is required to start")
    primary = Fernet(key.encode() if isinstance(key, str) else key)
    return MultiFernet([primary])


def fernet() -> MultiFernet:
    """Lazy accessor — first call validates the env var; subsequent calls reuse.

    Container fail-on-startup wiring lives in Plan 07's main.py — this module
    stays import-safe (no work at import time) so tests can swap settings.
    """
    global _cached
    if _cached is None:
        _cached = _build_multifernet()
    return _cached


def encrypt_provider_key(plaintext: str) -> bytes:
    """Encrypt a provider API key plaintext for at-rest storage in BYTEA."""
    return fernet().encrypt(plaintext.encode())


def decrypt_provider_key(ciphertext: bytes) -> str:
    """Decrypt a stored provider key.

    IMPORTANT (Landmine #4): do NOT pass ttl=. Provider keys are at-rest with
    no expiry — Fernet's TTL would silently expire valid stored keys, breaking
    all LLM calls 24h after key creation. Default ttl=None is correct for
    at-rest secrets.
    """
    return fernet().decrypt(ciphertext).decode()


def _reset_fernet_cache_for_tests() -> None:
    """Test-only helper to clear the MultiFernet cache after monkey-patching settings."""
    global _cached
    _cached = None
