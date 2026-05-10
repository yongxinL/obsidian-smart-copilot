"""Shared vault policy tests — VAULT-03.

Stubs: implemented in Wave 2 alongside services/pages.py.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.vault, pytest.mark.integration]


def test_any_user_can_read_shared_vault():
    pytest.skip("stub — implemented in Wave 2 (VAULT-03 shared vault)")


def test_admin_only_write_policy_blocks_non_admin():
    pytest.skip("stub — implemented in Wave 2 (VAULT-03 shared vault)")
