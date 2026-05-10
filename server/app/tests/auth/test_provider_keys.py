"""Provider key encrypted storage — AUTH-09, AUTH-10."""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.integration]


def test_encrypted_key_excluded_from_responses():
    pytest.skip("Wave 0 stub — implemented in Plan 06")


def test_user_key_takes_precedence_over_shared():
    pytest.skip("Wave 0 stub — implemented in Plan 06")


def test_shared_key_fallback_when_no_user_key():
    pytest.skip("Wave 0 stub — implemented in Plan 06")


def test_missing_provider_key_error():
    pytest.skip("Wave 0 stub — implemented in Plan 06")