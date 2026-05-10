"""Watchdog tests — IDX-01, IDX-02, IDX-03.

Stubs: implemented when vault/watcher.py real impl lands in Wave 3.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.vault, pytest.mark.integration]


def test_file_detection_latency():
    pytest.skip("stub — implemented in Wave 3 (vault/watcher.py)")


def test_handoff_api_uses_run_coroutine_threadsafe():
    pytest.skip("stub — implemented in Wave 3 (vault/watcher.py)")


def test_hash_dedup_skips_unchanged_file():
    pytest.skip("stub — implemented in Wave 3 (vault/watcher.py)")


def test_debounce_coalesces_rapid_events():
    pytest.skip("stub — implemented in Wave 3 (vault/watcher.py)")


def test_on_deleted_triggers_soft_delete():
    pytest.skip("stub — implemented in Wave 3 (vault/watcher.py)")
