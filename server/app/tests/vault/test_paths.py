"""Vault path safety tests — VAULT-01, VAULT-10.

NO FastAPI imports. NO SQLAlchemy imports.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.vault.paths import (
    InvalidSlugError,
    PathTraversalError,
    safe_vault_path,
    sanitize_filename_to_slug,
    validate_slug,
)

pytestmark = [pytest.mark.vault, pytest.mark.unit]


# ─── safe_vault_path ───────────────────────────────────────────────────────────


def test_safe_vault_path_resolves_within_root(tmp_path: Path) -> None:
    """safe_vault_path returns a Path inside the vault root for a valid slug."""
    vault_root = str(tmp_path / "vault")
    os.makedirs(vault_root, exist_ok=True)

    result = safe_vault_path(vault_root, "my-note")

    assert result.is_absolute()
    assert str(result).endswith("my-note.md")
    assert vault_root in str(result)


def test_safe_vault_path_rejects_dotdot_traversal(tmp_path: Path) -> None:
    """safe_vault_path raises PathTraversalError on ``..`` traversal."""
    vault_root = str(tmp_path / "vault")
    os.makedirs(vault_root, exist_ok=True)

    with pytest.raises(PathTraversalError):
        safe_vault_path(vault_root, "../etc")


def test_safe_vault_path_rejects_symlink_escape(tmp_path: Path) -> None:
    """safe_vault_path raises PathTraversalError when a symlink escapes the vault.

    Uses os.path.realpath on BOTH root and candidate. A string-only check
    (Path.is_relative_to without realpath) would NOT catch this attack.
    """
    vault_root = str(tmp_path / "vault")
    os.makedirs(vault_root, exist_ok=True)
    os.makedirs(tmp_path / "outside", exist_ok=True)
    secret_file = tmp_path / "outside" / "secret.txt"
    secret_file.write_text("sensitive data")

    # Create a symlink inside vault pointing to the secret file
    evil_link = Path(vault_root) / "evil.md"
    os.symlink(str(secret_file), str(evil_link))

    with pytest.raises(PathTraversalError):
        safe_vault_path(vault_root, "evil")


# ─── validate_slug ─────────────────────────────────────────────────────────────


def test_slug_validation_accepts_valid() -> None:
    """Valid slugs pass without error."""
    validate_slug("my-note")
    validate_slug("a")
    # 128 chars total: 1 leading + 127 body
    validate_slug("a" + "b" * 127)


def test_slug_validation_rejects_uppercase() -> None:
    """Uppercase letters raise InvalidSlugError."""
    with pytest.raises(InvalidSlugError):
        validate_slug("My-Note")


def test_slug_validation_rejects_leading_hyphen() -> None:
    """Leading hyphen raises InvalidSlugError."""
    with pytest.raises(InvalidSlugError):
        validate_slug("-bad")


def test_slug_validation_rejects_too_long() -> None:
    """Slug longer than 128 chars raises InvalidSlugError."""
    with pytest.raises(InvalidSlugError):
        validate_slug("a" * 129)


# ─── sanitize_filename_to_slug ────────────────────────────────────────────────


def test_slug_sanitizer_converts_watchdog_filename() -> None:
    """sanitize_filename_to_slug converts a natural-language filename to a slug."""
    result = sanitize_filename_to_slug("My Note!.md")

    assert result.startswith("my-note")
    assert result == result.lower()
    assert "_" not in result  # no underscores preserved as hyphens


def test_slug_sanitizer_falls_back_to_untitled() -> None:
    """sanitize_filename_to_slug returns ``untitled`` for a filename with no stem."""
    # A pure extension with no stem (just dots)
    result = sanitize_filename_to_slug("...")

    assert result == "untitled"


def test_slug_sanitizer_truncates_to_128() -> None:
    """sanitize_filename_to_slug truncates result to 128 chars."""
    long_name = "a" * 200 + ".md"
    result = sanitize_filename_to_slug(long_name)

    assert len(result) <= 128
