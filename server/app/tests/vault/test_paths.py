"""Vault path safety tests — VAULT-01, VAULT-10.

Stubs: implemented when vault/paths.py lands in Wave 1.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.vault, pytest.mark.unit]


def test_safe_vault_path_resolves_within_root():
    pytest.skip("stub — implemented in Wave 1 (vault/paths.py)")


def test_safe_vault_path_rejects_dotdot_traversal():
    pytest.skip("stub — implemented in Wave 1 (vault/paths.py)")


def test_safe_vault_path_rejects_symlink_escape():
    pytest.skip("stub — implemented in Wave 1 (vault/paths.py)")


def test_slug_validation_accepts_valid():
    pytest.skip("stub — implemented in Wave 1 (vault/paths.py)")


def test_slug_validation_rejects_uppercase():
    pytest.skip("stub — implemented in Wave 1 (vault/paths.py)")


def test_slug_validation_rejects_leading_hyphen():
    pytest.skip("stub — implemented in Wave 1 (vault/paths.py)")


def test_slug_sanitizer_converts_watchdog_filename():
    pytest.skip("stub — implemented in Wave 1 (vault/paths.py)")
