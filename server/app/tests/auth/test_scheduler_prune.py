"""APScheduler prune_login_attempts job — AUTH-03 (D-09)."""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.integration]


def test_prune_login_attempts_deletes_old_rows():
    pytest.skip("Wave 0 stub — implemented in Plan 07")


def test_prune_login_attempts_keeps_recent_rows():
    pytest.skip("Wave 0 stub — implemented in Plan 07")