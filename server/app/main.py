"""FastAPI application factory.

D-09: this module manages app lifecycle ONLY. It does NOT create the engine.
D-24: Fernet key required at startup — container exits non-zero if missing.
D-27: structlog redaction processor configured in lifespan startup.

Error envelope discipline (BLOCKER #3): every route raises
HTTPException(detail={"error": {"code": ..., "message": ...}}). FastAPI's
default handler wraps that in {"detail": ...} — clients then see
body["detail"]["error"]["code"]. We register a global exception handler that
returns JSONResponse(content=exc.detail) so clients see body["error"]["code"]
directly.
"""
from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.auth.middleware import TrustedProxyMiddleware
from app.database import engine  # import triggers connect event registration
from app.encryption import FernetKeyMissing, fernet
from app.logging.redaction import configure_logging
from app.routes.admin import router as admin_router
from app.routes.auth import router as auth_router
from app.routes.health import router as health_router
from app.routes.pages import router as pages_router
from app.routes.search import router as search_router
from app.routes.vault import router_capabilities as vault_capabilities_router
from app.routes.vault import router_vault as vault_router
from app.settings import settings


def _fail_startup_if_missing_secrets() -> None:
    """D-24 + Phase 1b success criterion #4: refuse to start without keys."""
    try:
        fernet()  # validates SMARTCOPILOT_FERNET_KEY
    except FernetKeyMissing as e:
        print(f"FATAL: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"FATAL: SMARTCOPILOT_FERNET_KEY is set but invalid: {e}", file=sys.stderr)
        sys.exit(1)
    if not settings.jwt_signing_key:
        print(
            "FATAL: JWT_SIGNING_KEY env var is required to start",
            file=sys.stderr,
        )
        sys.exit(1)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    _fail_startup_if_missing_secrets()
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="Smart Copilot", version="0.0.0", lifespan=lifespan)
    app.add_middleware(
        TrustedProxyMiddleware,
        trust_proxy=settings.smartcopilot_trust_proxy,
        allowlist_cidrs=settings.smartcopilot_trusted_proxy_cidrs,
    )

    # BLOCKER #3 closure — flatten HTTPException(detail={"error": {...}}) to
    # body["error"][...] (otherwise the default handler wraps in body["detail"]).
    @app.exception_handler(HTTPException)
    async def _flatten_http_error(request: Request, exc: HTTPException) -> JSONResponse:  # noqa: ARG001
        payload = exc.detail
        # If a route raised HTTPException with a non-dict detail (string/int),
        # fall back to the default {"detail": ...} shape.
        if not isinstance(payload, dict):
            payload = {"detail": payload}
        return JSONResponse(status_code=exc.status_code, content=payload)

    # REST-04: also flatten RequestValidationError to {error:{code,message}} shape.
    @app.exception_handler(RequestValidationError)
    async def _flatten_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:  # noqa: ARG001
        # Extract the first meaningful error message from the validation errors.
        errors = exc.errors()
        message = "; ".join(
            f"{'.'.join(str(x) for x in e.get('loc', []))}: {e.get('msg', 'invalid')}"
            for e in errors
        )
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "validation_error", "message": message}},
        )

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(pages_router)
    app.include_router(search_router)
    app.include_router(vault_capabilities_router)
    app.include_router(vault_router)
    return app


app = create_app()