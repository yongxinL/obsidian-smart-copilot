"""Vault path utilities — confinement, slug validation, filename sanitisation.

References: VAULT-01 (path traversal prevention via os.path.realpath on BOTH
root AND candidate), VAULT-10 (slug validation regex).

NO FastAPI imports. NO SQLAlchemy imports.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# VAULT-10: slug must match ^[a-z0-9][a-z0-9-]{0,127}$
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,127}$")

# Used by sanitize_filename_to_slug to replace invalid characters
_INVALID_SLUG_CHAR_RE = re.compile(r"[^a-z0-9-]")


class PathTraversalError(PermissionError):
    """Raised when a vault path escape is detected (symlink escape or ``..`` traversal)."""


class InvalidSlugError(ValueError):
    """Raised when a slug does not match the required pattern ^[a-z0-9][a-z0-9-]{0,127}$."""


def validate_slug(slug: str) -> None:
    """Validate a slug against VAULT-10 regex.

    Raises InvalidSlugError if slug does not match ``^[a-z0-9][a-z0-9-]{0,127}$``.
    """
    if not _SLUG_RE.match(slug):
        raise InvalidSlugError(
            f"Invalid slug {slug!r}; must match ^[a-z0-9][a-z0-9-]{{0,127}}$ "
            "(lowercase letters, digits, hyphens; cannot start with hyphen)"
        )


def safe_vault_path(vault_root: str, slug: str) -> Path:
    """Resolve and confine a slug to vault_root.

    VAULT-01 (MITIGATE T-01c03-01): Calls os.path.realpath on BOTH vault_root
    AND the candidate path before relative_to(). This correctly handles:
      - ``..`` traversal attempts in the slug
      - Symlink escapes (``vault/evil -> /etc/passwd``)
      - Mixed path components

    ``Path.is_relative_to()`` alone is STRING-ONLY and does NOT follow symlinks —
    it must never be used as the sole path check.

    Raises PathTraversalError on any escape attempt.
    """
    # Resolve root to canonical absolute path (follows symlinks)
    root = Path(os.path.realpath(vault_root))
    # Resolve candidate to canonical absolute path
    candidate = Path(os.path.realpath(root / f"{slug}.md"))

    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise PathTraversalError(
            f"Path traversal attempt detected: slug {slug!r} resolves to "
            f"{candidate} which is outside vault root {root}"
        ) from exc

    return candidate


def sanitize_filename_to_slug(filename: str) -> str:
    """Convert a filesystem filename to a valid vault slug.

    Used when the watchdog indexes a file that may not have a valid slug
    (e.g., ``My Note!.md`` → ``my-note``).

    Rules:
    1. Take the stem (filename without extension).
    2. Lowercase, replace invalid characters with hyphens, strip leading/trailing hyphens.
    3. Truncate to 128 characters.
    4. Fall back to ``untitled`` if result is empty.
    """
    stem = Path(filename).stem.strip()
    slug = _INVALID_SLUG_CHAR_RE.sub("-", stem.lower())
    slug = slug.strip("-")
    # Truncate to 128 (slug regex allows 1 + 127 = 128 total)
    slug = slug[:128]
    if not slug:
        slug = "untitled"
    return slug
