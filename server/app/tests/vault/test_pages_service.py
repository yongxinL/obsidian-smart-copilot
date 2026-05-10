"""Page service integration tests — VAULT-04, VAULT-06, VAULT-08.

Stubs: implemented when services/pages.py lands in Wave 2.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.vault, pytest.mark.integration]


def test_timeline_append_only():
    pytest.skip("stub — implemented in Wave 2 (services/pages.py)")


def test_note_type_defaults_to_fleeting():
    pytest.skip("stub — implemented in Wave 2 (services/pages.py)")


def test_versioning_inserts_page_version_on_update():
    pytest.skip("stub — implemented in Wave 2 (services/pages.py)")


def test_soft_delete_sets_deleted_at_and_deleted_by():
    pytest.skip("stub — implemented in Wave 2 (services/pages.py)")


def test_dedup_skips_reindex_when_hash_unchanged():
    pytest.skip("stub — implemented in Wave 2 (services/pages.py)")


def test_write_page_creates_index_event():
    pytest.skip("stub — implemented in Wave 2 (services/pages.py)")
