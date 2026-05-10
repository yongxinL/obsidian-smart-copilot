"""OpenAPI spec freshness tests — VAULT-11.

Stubs: implemented when scripts/regen_openapi.py and pre-commit hook land in Wave 4.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.vault, pytest.mark.integration]


def test_openapi_json_exists_and_is_valid_json():
    pytest.skip("stub — implemented in Wave 4 (scripts/regen_openapi.py)")


def test_openapi_spec_matches_live_app():
    pytest.skip("stub — implemented in Wave 4 (scripts/regen_openapi.py)")
