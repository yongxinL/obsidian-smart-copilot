"""smartcopilot doctor — D-14 system health smoke (CLI-02)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import text

from app.auth.context import system_operation_context
from app.dependencies import session_with_rls
from app.encryption import FernetKeyMissing, fernet
from app.settings import settings


def add_subparser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("doctor", help="report system health (D-14)")
    p.set_defaults(func=_handle_doctor)


async def _handle_doctor(args: argparse.Namespace) -> int:  # noqa: ARG001
    overall_ok = True

    # 1. Fernet key
    try:
        fernet()
        print("fernet_key: OK")
    except FernetKeyMissing:
        print("fernet_key: MISSING — set SMARTCOPILOT_FERNET_KEY", file=sys.stderr)
        overall_ok = False
    except ValueError as exc:
        print(f"fernet_key: INVALID — {exc}", file=sys.stderr)
        overall_ok = False

    # 2. inotify limit
    try:
        watches = int(Path("/proc/sys/fs/inotify/max_user_watches").read_text().strip())
        print(f"inotify_max_user_watches: {watches}")
    except OSError:
        print("inotify_max_user_watches: (unreadable — not Linux?)")

    # 3. CORS config — Phase 1d settings has no cors origins yet (added in Phase 6).
    #    Surface "none configured" so doctor is forward-compatible.
    cors_origins = getattr(settings, "cors_allow_origins", None)
    if cors_origins:
        print(f"cors_config: {','.join(cors_origins)}")
    else:
        print("cors_config: none configured")

    # 4. MCP token storage mode (D-14)
    print("mcp_token_storage: sha256-hashed")

    # 5. DB connection + pgvector extension
    try:
        ctx = system_operation_context(client_name="cli", request_id="cli-doctor")
        async for session in session_with_rls(ctx):
            await session.execute(text("SELECT 1"))
            print("db_connection: OK")
            row = (
                await session.execute(
                    text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
                )
            ).scalar_one_or_none()
            if row:
                print("db_pgvector_extension: OK")
            else:
                print("db_pgvector_extension: not loaded")
    except Exception as exc:  # noqa: BLE001
        print(f"db_connection: ERROR — {exc}", file=sys.stderr)
        overall_ok = False

    return 0 if overall_ok else 1
