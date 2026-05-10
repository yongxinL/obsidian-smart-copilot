"""smartcopilot mcp token — create / list / revoke."""
from __future__ import annotations

import argparse
import uuid

from app.auth.context import OperationContext, system_operation_context
from app.dependencies import session_with_rls
from app.services.mcp_tokens import create_mcp_token, list_for_user, revoke_token
from app.services.users import get_user_by_username, normalize_username


def add_subparser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("mcp", help="MCP commands")
    msub = p.add_subparsers(dest="mcp_command", required=True)
    token = msub.add_parser("token", help="MCP bearer tokens")
    tsub = token.add_subparsers(dest="token_command", required=True)

    create = tsub.add_parser("create", help="create an MCP token (plaintext shown ONCE)")
    create.add_argument("--user", required=True, help="username")
    create.add_argument("--name", default=None)
    create.set_defaults(func=_handle_create)

    ls = tsub.add_parser("list", help="list MCP tokens for a user")
    ls.add_argument("--user", required=True)
    ls.set_defaults(func=_handle_list)

    rv = tsub.add_parser("revoke", help="revoke an MCP token by id")
    rv.add_argument("--id", required=True)
    rv.set_defaults(func=_handle_revoke)


async def _resolve_user_id(username: str) -> uuid.UUID:
    async for session in session_with_rls(system_operation_context()):
        user = await get_user_by_username(session, username)
        if user is None:
            raise SystemExit(f"error: user not found: {username}")
        return user.id
    raise SystemExit(f"error: user not found: {username}")  # pragma: no cover


async def _handle_create(args: argparse.Namespace) -> int:
    uid = await _resolve_user_id(normalize_username(args.user))
    ctx = OperationContext(
        user_id=uid,
        role="user",
        transport="cli",
        remote=False,
        client_name="cli",
        request_id="cli-mcp-create",
    )
    plaintext = None
    row = None
    async for session in session_with_rls(ctx):
        plaintext, row = await create_mcp_token(session, ctx, name=args.name)
        await session.commit()
    # IMPORTANT: plaintext shown ONCE — operator must save it now
    print(f"id={row.id}", flush=True)
    print(f"token={plaintext}", flush=True)
    print("WARNING: this token plaintext will not be shown again", flush=True)
    return 0


async def _handle_list(args: argparse.Namespace) -> int:
    uid = await _resolve_user_id(normalize_username(args.user))
    ctx = OperationContext(
        user_id=uid,
        role="user",
        transport="cli",
        remote=False,
        client_name="cli",
        request_id="cli-mcp-list",
    )
    rows = []
    async for session in session_with_rls(ctx):
        rows = await list_for_user(session, uid)
    if not rows:
        print("(no active tokens)")
    for r in rows:
        print(f"{r.id}\t{r.name or '-'}\tlast_used_at={r.last_used_at}")
    return 0


async def _handle_revoke(args: argparse.Namespace) -> int:
    token_id = uuid.UUID(args.id)
    # System context — revoke is admin-grade
    ctx = system_operation_context(client_name="cli", request_id="cli-mcp-revoke")
    async for session in session_with_rls(ctx):
        await revoke_token(session, token_id)
        await session.commit()
    print(f"revoked {token_id}")
    return 0
