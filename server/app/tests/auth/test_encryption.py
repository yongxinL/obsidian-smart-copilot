"""Fernet encryption — AUTH-09."""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.unit]


def test_fernet_roundtrip():
    pytest.skip("Wave 0 stub — implemented in Plan 03")


def test_missing_fernet_key_raises_FernetKeyMissing():
    pytest.skip("Wave 0 stub — implemented in Plan 03")


def test_decrypt_does_not_use_ttl():
    pytest.skip("Wave 0 stub — implemented in Plan 03")


def test_multifernet_decrypts_with_secondary_key():
    pytest.skip("Wave 0 stub — implemented in Plan 03")