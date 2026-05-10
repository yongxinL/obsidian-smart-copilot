"""argon2id password hashing with asyncio.to_thread offload (D-23, Landmine #6).

PRD §8 / D-23: time_cost=3, memory_cost=64 MiB, parallelism=1, hash_len=32, salt_len=16.
Override: parallelism=1 (NOT default 4) — homelab CPU is shared.

Landmine #6: argon2 is intentionally CPU-bound (~50-200ms per call). A naive
sync call from FastAPI starves the event loop under login burst. Every hash
and verify call MUST go through asyncio.to_thread.

Landmine #3: PasswordHasher.verify raises VerifyMismatchError on mismatch
(does NOT return False). The wrapper catches all three exception subclasses
and returns False so callers can write `if await verify_password(...): ...`.
"""

from __future__ import annotations

import asyncio

from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)

from app.settings import settings

_HASHER: PasswordHasher = PasswordHasher(
    time_cost=settings.argon2_time_cost,
    memory_cost=settings.argon2_memory_cost,
    parallelism=settings.argon2_parallelism,
    hash_len=32,
    salt_len=16,
)


async def hash_password(plaintext: str) -> str:
    """Hash a plaintext password. Offloaded to a thread to keep the event loop hot."""
    return await asyncio.to_thread(_HASHER.hash, plaintext)


async def verify_password(stored_hash: str, plaintext: str) -> bool:
    """Verify; returns False on mismatch (DOES NOT propagate VerifyMismatchError)."""
    try:
        await asyncio.to_thread(_HASHER.verify, stored_hash, plaintext)
        return True
    except (VerifyMismatchError, InvalidHashError, VerificationError):
        return False


def needs_rehash(stored_hash: str) -> bool:
    """Cheap, runs in-loop (no thread). Caller rehashes after a successful login."""
    return _HASHER.check_needs_rehash(stored_hash)
