"""RLS isolation tests for pages — VAULT-02.

Stubs: implemented in Wave 2 alongside services/pages.py.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.vault, pytest.mark.integration]


def test_user_a_cannot_read_user_b_pages():
    pytest.skip("stub — implemented in Wave 2 (VAULT-02 RLS isolation)")


def test_guc_not_leaked_after_page_request():
    pytest.skip("stub — implemented in Wave 2 (VAULT-02 RLS isolation)")
