"""argon2 password hashing — AUTH-01."""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.unit]


def test_hash_verify_roundtrip():
    pytest.skip("Wave 0 stub — implemented in Plan 04")


def test_argon2_params_meet_owasp_minima():
    pytest.skip("Wave 0 stub — implemented in Plan 04")


def test_verify_returns_false_on_mismatch():
    pytest.skip("Wave 0 stub — implemented in Plan 04")


def test_check_needs_rehash_after_param_change():
    pytest.skip("Wave 0 stub — implemented in Plan 04")