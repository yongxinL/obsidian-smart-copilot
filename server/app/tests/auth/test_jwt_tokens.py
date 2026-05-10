"""JWT encode/decode — AUTH-02."""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.unit]


def test_jwt_roundtrip_includes_sub_role_jti():
    pytest.skip("Wave 0 stub — implemented in Plan 04")


def test_decode_rejects_alg_none():
    pytest.skip("Wave 0 stub — implemented in Plan 04")


def test_decode_rejects_alg_confusion():
    pytest.skip("Wave 0 stub — implemented in Plan 04")


def test_jwt_expiry_enforced():
    pytest.skip("Wave 0 stub — implemented in Plan 04")