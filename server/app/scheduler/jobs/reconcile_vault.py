"""IDX-04: Lightweight vault reconciliation job (D-08).

Runs every 5 minutes via APScheduler. Detects filesystem ↔ DB drift:
  - Files on disk with no DB page → upsert
  - Files on disk with changed content_hash → re-index
  - DB pages (active) with no corresponding file → soft-delete

CLAUDE.md: module-level function, no closures — APScheduler pickles job args.
D-08: coalesce=True, max_instances=1 — one run at a time.
"""

from __future__ import annotations

from pathlib import Path

import structlog
import xxhash
from sqlalchemy import select

from app.auth.context import system_operation_context
from app.dependencies import session_with_rls
from app.models.page import Page
from app.models.vault import Vault
from app.services.pages import soft_delete_page, upsert_page
from app.vault.parser import parse_vault_file
from app.vault.paths import sanitize_filename_to_slug

log = structlog.get_logger("smart_copilot.reconciler")


async def reconcile_vault() -> None:
    """Lightweight reconciliation: compare content_hash vs DB pages.

    D-03: enforce_timeline=False — reconciler bypasses timeline enforcement
    (same as watchdog; human filesystem edits are trusted).
    """
    ctx = system_operation_context(
        request_id="reconcile_vault", client_name="scheduler"
    )
    async for session in session_with_rls(ctx):
        # 1. Load all vaults from DB
        vaults_result = await session.execute(select(Vault))
        vaults = vaults_result.scalars().all()

        for vault in vaults:
            vault_path = Path(vault.path)
            if not vault_path.exists():
                log.warning(
                    "vault_path_missing", vault_id=str(vault.id), path=str(vault_path)
                )
                continue

            # 2. Build disk inventory: slug -> (content_hash, full_path)
            disk_slugs: dict[str, tuple[str, Path]] = {}
            for md_file in vault_path.rglob("*.md"):
                try:
                    raw = md_file.read_bytes()
                except OSError:
                    continue
                slug = sanitize_filename_to_slug(md_file.name)
                if slug != Path(md_file.name).stem:
                    log.warning(
                        "slug_sanitized",
                        original=md_file.name,
                        slug=slug,
                        vault_id=str(vault.id),
                    )
                content_hash = xxhash.xxh64(raw).hexdigest()
                disk_slugs[slug] = (content_hash, md_file)

            # 3. Load DB inventory for this vault: slug -> (content_hash, page_id)
            pages_result = await session.execute(
                select(Page.id, Page.slug, Page.content_hash).where(
                    Page.vault_id == vault.id,
                    Page.deleted_at.is_(None),
                )
            )
            db_slugs: dict[str, tuple[str, object]] = {
                row.slug: (row.content_hash, row.id) for row in pages_result
            }

            # 4. Reconcile: files on disk not in DB OR hash changed
            for slug, (disk_hash, md_path) in disk_slugs.items():
                db_hash, _ = db_slugs.get(slug, (None, None))
                if db_hash == disk_hash:
                    continue  # IDX-03: skip unchanged
                try:
                    raw = md_path.read_bytes()
                    parsed = parse_vault_file(raw)
                    await upsert_page(
                        session,
                        ctx,
                        vault_id=vault.id,
                        slug=slug,
                        parsed=parsed,
                        enforce_timeline=False,  # D-03: reconciler is like watchdog
                    )
                    log.info("page_reconciled", slug=slug, vault_id=str(vault.id))
                except Exception as exc:  # noqa: BLE001
                    log.error("reconcile_upsert_failed", slug=slug, error=str(exc))

            # 5. Reconcile: DB pages with no corresponding disk file
            for slug, (_, page_id) in db_slugs.items():
                if slug not in disk_slugs:
                    try:
                        await soft_delete_page(
                            session,
                            ctx,
                            page_id=page_id,
                            reason="reconciler_file_missing",
                        )
                        log.info("page_soft_deleted", slug=slug, vault_id=str(vault.id))
                    except Exception as exc:  # noqa: BLE001
                        log.error(
                            "reconcile_soft_delete_failed", slug=slug, error=str(exc)
                        )

        await session.commit()
    log.info("reconcile_vault_complete")
