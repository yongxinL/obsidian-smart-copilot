"""Reconciliation job tests — IDX-04.

Stubs: implemented when scheduler/jobs/reconcile_vault.py lands in Wave 3.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.vault, pytest.mark.integration]


def test_reconcile_picks_up_new_file():
    pytest.skip("stub — implemented in Wave 3 (scheduler/jobs/reconcile_vault.py)")


def test_reconcile_soft_deletes_missing_file():
    pytest.skip("stub — implemented in Wave 3 (scheduler/jobs/reconcile_vault.py)")


def test_reconcile_skips_unchanged_hash():
    pytest.skip("stub — implemented in Wave 3 (scheduler/jobs/reconcile_vault.py)")
