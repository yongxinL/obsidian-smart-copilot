"""smartcopilot page — vault CRUD subcommands (D-13)."""

from __future__ import annotations

import argparse
import uuid
from pathlib import Path

from app.auth.context import OperationContext, system_operation_context
from app.dependencies import session_with_rls
from app.services.pages import (
    PageNotFound,
    SharedVaultWriteDenied,
    TimelineViolation,
    get_page_history,
    list_pages,
    read_page,
    search_pages_fts,
    soft_delete_page,
    write_page,
)
from app.services.users import get_user_by_username, normalize_username
from app.services.vault_resolver import VaultNotFound, resolve_user_vault_id


def add_subparser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("page", help="vault page CRUD")
    psub = p.add_subparsers(dest="page_command", required=True)

    g = psub.add_parser("get", help="get a page by slug")
    g.add_argument("--user", required=True)
    g.add_argument("--slug", required=True)
    g.set_defaults(func=_handle_get)

    pp = psub.add_parser("put", help="write a page from a file")
    pp.add_argument("--user", required=True)
    pp.add_argument("--slug", required=True)
    pp.add_argument("--file", required=True, help="path to a markdown file")
    pp.set_defaults(func=_handle_put)

    rm = psub.add_parser("delete", help="soft-delete a page")
    rm.add_argument("--user", required=True)
    rm.add_argument("--slug", required=True)
    rm.set_defaults(func=_handle_delete)

    ls = psub.add_parser("list", help="list pages")
    ls.add_argument("--user", required=True)
    ls.add_argument("--limit", type=int, default=50)
    ls.set_defaults(func=_handle_list)

    sr = psub.add_parser("search", help="full-text search pages")
    sr.add_argument("--user", required=True)
    sr.add_argument("--query", required=True)
    sr.add_argument("--limit", type=int, default=20)
    sr.set_defaults(func=_handle_search)


async def _resolve_user_ctx(
    username: str, request_id: str
) -> tuple[OperationContext, uuid.UUID]:
    norm = normalize_username(username)
    sys_ctx = system_operation_context(
        client_name="cli", request_id=f"cli-{request_id}-resolve"
    )
    async for session in session_with_rls(sys_ctx):
        user = await get_user_by_username(session, norm)
        if user is None:
            print(f"error: user not found: {username}", file=__import__("sys").stderr)
            raise SystemExit(2)
        return OperationContext(
            user_id=user.id,
            role=user.role,
            transport="cli",
            remote=False,
            client_name="cli",
            request_id=f"cli-{request_id}",
        ), user.id
    raise SystemExit(2)  # pragma: no cover


async def _handle_get(args: argparse.Namespace) -> int:
    ctx, _ = await _resolve_user_ctx(args.user, "page-get")
    async for session in session_with_rls(ctx):
        try:
            vault_id = await resolve_user_vault_id(session, ctx.user_id)
            page = await read_page(session, vault_id=vault_id, slug=args.slug)
        except (VaultNotFound, PageNotFound) as exc:
            print(f"error: {exc}", file=__import__("sys").stderr)
            return 2
    print(f"slug={page.slug}")
    print(f"title={(page.frontmatter or {}).get('title')}")
    print(f"note_type={page.note_type}")
    print(f"updated_at={page.updated_at.isoformat()}")
    print("compiled_truth:")
    print(page.compiled_truth or "")
    print("timeline:")
    print(page.timeline or "")
    return 0


async def _handle_put(args: argparse.Namespace) -> int:
    ctx, _ = await _resolve_user_ctx(args.user, "page-put")
    raw = Path(args.file).read_bytes()
    async for session in session_with_rls(ctx):
        try:
            vault_id = await resolve_user_vault_id(session, ctx.user_id)
            page = await write_page(
                session, ctx, slug=args.slug, raw_content=raw, vault_id=vault_id
            )
            await session.commit()
        except VaultNotFound as exc:
            print(f"error: {exc}", file=__import__("sys").stderr)
            return 2
        except TimelineViolation as exc:
            print(f"error: timeline_violation: {exc}", file=__import__("sys").stderr)
            return 2
        except SharedVaultWriteDenied as exc:
            print(f"error: forbidden: {exc}", file=__import__("sys").stderr)
            return 2
        history = await get_page_history(session, ctx, page_id=page.id)
    version = history[0].version if history else 1
    print(f"slug={page.slug} page_id={page.id} version={version}")
    return 0


async def _handle_delete(args: argparse.Namespace) -> int:
    ctx, _ = await _resolve_user_ctx(args.user, "page-delete")
    async for session in session_with_rls(ctx):
        try:
            vault_id = await resolve_user_vault_id(session, ctx.user_id)
            page = await read_page(session, vault_id=vault_id, slug=args.slug)
            await soft_delete_page(session, ctx, page_id=page.id, reason="cli_delete")
            await session.commit()
        except (VaultNotFound, PageNotFound) as exc:
            print(f"error: {exc}", file=__import__("sys").stderr)
            return 2
    print(f"deleted slug={args.slug}")
    return 0


async def _handle_list(args: argparse.Namespace) -> int:
    ctx, _ = await _resolve_user_ctx(args.user, "page-list")
    async for session in session_with_rls(ctx):
        try:
            vault_id = await resolve_user_vault_id(session, ctx.user_id)
        except VaultNotFound as exc:
            print(f"error: {exc}", file=__import__("sys").stderr)
            return 2
        pages = await list_pages(session, ctx, vault_id=vault_id, limit=args.limit)
    for p in pages:
        print(f"{p.slug}\t{p.note_type}\t{p.updated_at.isoformat()}")
    return 0


async def _handle_search(args: argparse.Namespace) -> int:
    ctx, _ = await _resolve_user_ctx(args.user, "page-search")
    async for session in session_with_rls(ctx):
        try:
            vault_id = await resolve_user_vault_id(session, ctx.user_id)
        except VaultNotFound as exc:
            print(f"error: {exc}", file=__import__("sys").stderr)
            return 2
        try:
            hits = await search_pages_fts(
                session,
                ctx,
                vault_id=vault_id,
                query=args.query,
                limit=args.limit,
            )
        except ValueError as exc:
            print(f"error: validation: {exc}", file=__import__("sys").stderr)
            return 2
    for h in hits:
        snippet = (h.snippet or "").replace("\n", " ")
        print(f"{h.score:.4f}\t{h.slug}\t{snippet}")
    return 0
