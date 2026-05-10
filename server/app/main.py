"""FastAPI application factory.

D-09: this module manages app lifecycle ONLY. It does NOT create the engine
(that lives in database.py and is initialized at import time so the connect
event listener registers before the first connection is opened).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import engine  # import triggers connect event registration
from app.routes.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="Smart Copilot", version="0.0.0", lifespan=lifespan)
    app.include_router(health_router)
    return app


app = create_app()
