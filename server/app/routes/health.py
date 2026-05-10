"""Health endpoint. Phase 1a returns shallow {status: ok} only.

Per CONTEXT.md Claude's Discretion: full DB/pgvector/Fernet checks deferred
to Phase 6 (smartcopilot doctor).
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
