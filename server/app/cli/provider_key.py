"""smartcopilot provider key — Phase 1b: set only."""

from __future__ import annotations

import argparse
import getpass
import os

from app.auth.context import OperationContext, system_operation_context
from app.dependencies import session_with_rls
from app.services.provider_keys import set_provider_key
from app.services.users import get_user_by_username, normalize_username


def add_subparser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("provider", help="provider key commands")
    psub = p.add_subparsers(dest="provider_command", required=True)
    key = psub.add_parser("key", help="provider key CRUD")
    ksub = key.add_subparsers(dest="key_command", required=True)
    set_ = ksub.add_parser("set", help="set or replace a provider key")
    set_.add_argument("--user", required=True)
    set_.add_argument("--provider", required=True)
    # WR-01: --key removed to prevent process-table exposure.
    # Use SMARTCOPILOT_PROVIDER_KEY env var for non-interactive use.
    set_.set_defaults(func=_handle_set)


async def _handle_set(args: argparse.Namespace) -> int:
    # WR-01: env var for scripted use; secure prompt otherwise — never a CLI arg.
    plaintext = os.environ.get("SMARTCOPILOT_PROVIDER_KEY") or getpass.getpass(
        "Provider key: "
    )
    # Resolve target user
    user = None
    async for session in session_with_rls(system_operation_context()):
        user = await get_user_by_username(session, normalize_username(args.user))
        if user is None:
            print(f"error: user not found: {args.user}")
            return 2
    # Set key under target user's RLS context
    ctx = OperationContext(
        user_id=user.id,
        role=user.role,
        transport="cli",
        remote=False,
        client_name="cli",
        request_id="cli-provider-set",
    )
    row = None
    async for session in session_with_rls(ctx):
        row = await set_provider_key(
            session, ctx, provider=args.provider, plaintext=plaintext
        )
        await session.commit()
    print(f"set provider_key id={row.id} provider={row.provider} hint={row.key_hint}")
    return 0
