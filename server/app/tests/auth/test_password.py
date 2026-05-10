"""AUTH-01 unit tests — argon2 password hashing."""
from __future__ import annotations

import pytest
from argon2 import PasswordHasher

from app.auth.password import _HASHER, hash_password, needs_rehash, verify_password

pytestmark = [pytest.mark.auth, pytest.mark.unit]


async def test_hash_verify_roundtrip() -> None:
    h = await hash_password("p@ssw0rd!")
    assert h.startswith("$argon2id$")
    assert await verify_password(h, "p@ssw0rd!") is True


def test_argon2_params_meet_owasp_minima() -> None:
    # PRD §8 / D-23 — these are the hardcoded minima
    assert _HASHER.time_cost >= 3
    assert _HASHER.memory_cost >= 64 * 1024
    assert _HASHER.parallelism >= 1
    assert _HASHER.hash_len == 32
    assert _HASHER.salt_len == 16


async def test_verify_returns_false_on_mismatch() -> None:
    h = await hash_password("correct")
    result = await verify_password(h, "WRONG")
    # Landmine #3 — must not raise
    assert result is False


async def test_check_needs_rehash_after_param_change() -> None:
    # Build a weaker hash (time_cost=2) and assert needs_rehash flags it
    weak = PasswordHasher(time_cost=2, memory_cost=64 * 1024, parallelism=1)
    weak_hash = weak.hash("x")
    assert needs_rehash(weak_hash) is True

    # A hash built with the current settings should NOT need rehash
    current_hash = await hash_password("x")
    assert needs_rehash(current_hash) is False