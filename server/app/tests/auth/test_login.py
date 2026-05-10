"""Login endpoint — AUTH-02, AUTH-03."""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.integration]


def test_login_returns_jwt_pair():
    pytest.skip("Wave 0 stub — implemented in Plan 07")


def test_login_invalid_credentials_returns_401():
    pytest.skip("Wave 0 stub — implemented in Plan 07")


def test_refresh_token_stored_as_hash():
    pytest.skip("Wave 0 stub — implemented in Plan 07")


def test_refresh_rotation_revokes_old():
    pytest.skip("Wave 0 stub — implemented in Plan 07")


def test_old_refresh_replay_rejected():
    pytest.skip("Wave 0 stub — implemented in Plan 07")


def test_rate_limit_after_10_failures():
    pytest.skip("Wave 0 stub — implemented in Plan 07")


def test_rate_limit_response_envelope():
    pytest.skip("Wave 0 stub — implemented in Plan 07")


def test_successful_login_wipes_attempts():
    pytest.skip("Wave 0 stub — implemented in Plan 07")


def test_sliding_window_ages_out():
    pytest.skip("Wave 0 stub — implemented in Plan 07")