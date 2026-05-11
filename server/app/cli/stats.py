"""smartcopilot stats — vault summary (D-13)."""

from __future__ import annotations

import argparse
import sys
import uuid

from app.auth.context import OperationContext, system_operation_context
from app.dependencies import session_with_rls
from app.services.pages import vault_stats
from app.services.users import get_user_by_username, normalize_username
from app.services.vault_resolver import VaultNotFound, resolve_user_vault_id


def add_subparser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("stats", help="vault page-count summary")
    p.add_argument("--user", required=True)
    p.set_defaults(func=_handle_stats)


async def _resolve_stats_user(username: str) -> tuple[OperationContext, uuid.UUID]:
    norm = normalize_username(username)
    sys_ctx = system_operation_context(
        client_name="cli", request_id="cli-stats-resolve"
    )
    async for session in session_with_rls(sys_ctx):
        user = await get_user_by_username(session, norm)
        if user is None:
            print(f"error: user not found: {username}", file=sys.stderr)
            raise SystemExit(2)
        return OperationContext(
            user_id=user.id,
            role=user.role,
            transport="cli",
            remote=False,
            client_name="cli",
            request_id="cli-stats",
        ), user.id
    raise SystemExit(2)  # pragma: no cover


async def _handle_stats(args: argparse.Namespace) -> int:
    ctx, _ = await _resolve_stats_user(args.user)
    async for session in session_with_rls(ctx):
        try:
            vault_id = await resolve_user_vault_id(session, ctx.user_id)
        except VaultNotFound as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        stats = await vault_stats(session, ctx, vault_id=vault_id)
    print(f"page_count={stats.live_pages}")
    print(f"deleted_page_count={stats.deleted_pages}")
    print(f"total_compiled_truth_bytes={stats.total_bytes}")
    print(
        f"last_indexed_at={stats.last_updated_at.isoformat() if stats.last_updated_at else 'never'}"
    )
    return 0
