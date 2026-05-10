"""Vault file parser tests — VAULT-04, VAULT-05, VAULT-07.

Stubs: implemented when vault/parser.py lands in Wave 1.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.vault, pytest.mark.unit]


def test_parse_compiled_truth_only():
    pytest.skip("stub — implemented in Wave 1 (vault/parser.py)")


def test_parse_timeline_only():
    pytest.skip("stub — implemented in Wave 1 (vault/parser.py)")


def test_parse_mixed_body():
    pytest.skip("stub — implemented in Wave 1 (vault/parser.py)")


def test_parse_empty_body():
    pytest.skip("stub — implemented in Wave 1 (vault/parser.py)")


def test_multiple_separators_raises():
    pytest.skip("stub — implemented in Wave 1 (vault/parser.py)")


def test_frontmatter_page_types():
    pytest.skip("stub — implemented in Wave 1 (vault/parser.py)")


def test_content_hash_dedup():
    pytest.skip("stub — implemented in Wave 1 (vault/parser.py)")


def test_resolved_links_stripped_from_user_frontmatter():
    pytest.skip("stub — implemented in Wave 1 (vault/parser.py)")


def test_wikilink_extraction():
    pytest.skip("stub — implemented in Wave 1 (vault/parser.py)")


def test_timeline_append_only_accepts_extension():
    pytest.skip("stub — implemented in Wave 1 (vault/parser.py)")


def test_timeline_append_only_rejects_edit():
    pytest.skip("stub — implemented in Wave 1 (vault/parser.py)")
