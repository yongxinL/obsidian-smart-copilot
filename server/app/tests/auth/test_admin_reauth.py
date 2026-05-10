"""Step-up fresh authentication — AUTH-06, AUTH-07."""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.integration]


def test_role_enum_is_admin_or_user():
    pytest.skip("Wave 0 stub — implemented in Plan 07")


def test_non_admin_forbidden_from_admin_route():
    pytest.skip("Wave 0 stub — implemented in Plan 07")


def test_reauth_sets_admin_fresh_until():
    pytest.skip("Wave 0 stub — implemented in Plan 07")


def test_destructive_route_403_without_fresh_auth():
    pytest.skip("Wave 0 stub — implemented in Plan 07")


def test_admin_reauth_required_envelope_shape():
    pytest.skip("Wave 0 stub — implemented in Plan 07")


def test_fresh_auth_expires_after_60_minutes():
    pytest.skip("Wave 0 stub — implemented in Plan 07")


def test_reauth_unsupported_factor_returns_not_implemented():
    pytest.skip("Wave 0 stub — implemented in Plan 07")