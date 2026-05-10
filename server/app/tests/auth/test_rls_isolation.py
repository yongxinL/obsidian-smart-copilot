"""RLS isolation tests — TEST-02 (headline)."""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.integration]


def test_no_guc_leak_after_request():
    pytest.skip("Wave 0 stub — implemented in Plan 05+08")


def test_user_b_sees_empty_guc():
    pytest.skip("Wave 0 stub — implemented in Plan 05+08")


def test_cross_user_read_blocked():
    pytest.skip("Wave 0 stub — implemented in Plan 05+08")


def test_system_context_bypass():
    pytest.skip("Wave 0 stub — implemented in Plan 05+08")


def test_pool_reset_scrubs_guc():
    pytest.skip("Wave 0 stub — implemented in Plan 05+08")