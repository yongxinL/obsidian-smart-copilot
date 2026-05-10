"""Wikilink resolution tests — VAULT-09.

Stubs: implemented when services/pages.py wikilink resolver lands in Wave 2.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.vault, pytest.mark.integration]


def test_private_namespace_routing():
    pytest.skip("stub — implemented in Wave 2 (services/pages.py resolve_wikilinks)")


def test_shared_namespace_routing():
    pytest.skip("stub — implemented in Wave 2 (services/pages.py resolve_wikilinks)")


def test_shortest_unique_path_alphabetical_tie():
    pytest.skip("stub — implemented in Wave 2 (services/pages.py resolve_wikilinks)")


def test_unresolved_forward_reference_allowed():
    pytest.skip("stub — implemented in Wave 2 (services/pages.py resolve_wikilinks)")


def test_resolved_links_stored_in_frontmatter_jsonb():
    pytest.skip("stub — implemented in Wave 2 (services/pages.py resolve_wikilinks)")


def test_display_alias_parsed():
    pytest.skip("stub — implemented in Wave 2 (services/pages.py resolve_wikilinks)")
