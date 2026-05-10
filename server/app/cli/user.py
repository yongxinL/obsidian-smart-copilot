"""smartcopilot user — Phase 1b: create only."""
from __future__ import annotations

import argparse
import getpass
import os

from app.auth.context import system_operation_context
from app.dependencies import session_with_rls
from app.services.users import UsernameExists, create_user


def add_subparser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("user", help="user CRUD")
    usub = p.add_subparsers(dest="user_command", required=True)
    create = usub.add_parser("create", help="create a new user")
    create.add_argument("--username", required=True)
    create.add_argument("--role", choices=["admin", "user"], default="user")
    create.add_argument("--email", default=None)
    # WR-01: --password removed to prevent process-table exposure.
    # Use SMARTCOPILOT_NEW_PASSWORD env var for non-interactive use.
    create.set_defaults(func=_handle_create)


async def _handle_create(args: argparse.Namespace) -> int:
    # WR-01: env var for scripted use; secure prompt otherwise — never a CLI arg.
    password = os.environ.get("SMARTCOPILOT_NEW_PASSWORD") or getpass.getpass("Password: ")
    ctx = system_operation_context(client_name="cli", request_id="cli-user-create")
    user = None
    async for session in session_with_rls(ctx):
        try:
            user = await create_user(
                session,
                ctx,
                username=args.username,
                password_plain=password,
                role=args.role,
                email=args.email,
            )
        except UsernameExists as e:
            print(f"error: username exists: {e}", flush=True)
            return 2
        await session.commit()
    print(f"created user {user.username} (id={user.id}, role={user.role})", flush=True)
    return 0
