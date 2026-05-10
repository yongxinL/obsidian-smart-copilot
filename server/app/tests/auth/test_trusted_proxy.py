"""Trusted proxy XFF integration — AUTH-08."""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.integration]


def test_xff_used_when_peer_trusted():
    pytest.skip("Wave 0 stub — implemented in Plan 07")


def test_xff_ignored_when_untrusted_peer():
    pytest.skip("Wave 0 stub — implemented in Plan 07")


def test_rate_limit_keys_on_xff_when_trusted():
    pytest.skip("Wave 0 stub — implemented in Plan 07")