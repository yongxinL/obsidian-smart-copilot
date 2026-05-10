"""AUTH-09 unit tests — Fernet provider-key encryption."""
from __future__ import annotations

import pytest
from cryptography.fernet import Fernet, MultiFernet

from app.encryption import (
    FernetKeyMissing,
    _reset_fernet_cache_for_tests,
    decrypt_provider_key,
    encrypt_provider_key,
    fernet,
)

pytestmark = [pytest.mark.auth, pytest.mark.unit]


@pytest.fixture(autouse=True)
def _isolate_cache():
    _reset_fernet_cache_for_tests()
    yield
    _reset_fernet_cache_for_tests()


def _set_key(monkeypatch, value: str) -> None:
    from app import settings as settings_mod

    monkeypatch.setattr(settings_mod.settings, "smartcopilot_fernet_key", value)


def test_fernet_roundtrip(monkeypatch) -> None:
    _set_key(monkeypatch, Fernet.generate_key().decode())
    plaintext = "sk-anthropic-test-XXXXXXXX"
    ciphertext = encrypt_provider_key(plaintext)
    assert isinstance(ciphertext, bytes)
    assert ciphertext != plaintext.encode()
    assert decrypt_provider_key(ciphertext) == plaintext


def test_missing_fernet_key_raises_FernetKeyMissing(monkeypatch) -> None:
    _set_key(monkeypatch, "")
    with pytest.raises(FernetKeyMissing) as excinfo:
        fernet()
    assert "SMARTCOPILOT_FERNET_KEY" in str(excinfo.value)


def test_decrypt_does_not_use_ttl() -> None:
    """Source-level guard — Landmine #4. decrypt_provider_key body must NOT pass ttl=."""
    import ast
    import inspect

    from app import encryption

    src = inspect.getsource(encryption.decrypt_provider_key)
    # Parse to AST to strip docstrings and comments — only function body remains.
    tree = ast.parse(src)
    func_def = tree.body[0]
    func_body = func_def.body
    # Remove docstring if present (first Expr node with a Str/Constant)
    if (
        func_body
        and isinstance(func_body[0], ast.Expr)
        and isinstance(func_body[0].value, (ast.Str, ast.Constant))
    ):
        func_body = func_body[1:]
    # Rebuild lines from AST node (simplified: just the function body lines)
    # Simpler approach: strip comment-only lines and lines inside docstring.
    lines = src.splitlines()
    # Remove docstring lines (between triple-quote delimiters or line-start triple-quote)
    # For simplicity, collect only non-comment, non-docstring lines
    in_docstring = False
    stripped = []
    for line in lines:
        stripped_line = line.strip()
        # Detect triple-quote boundaries
        if '"""' in stripped_line or "'''" in stripped_line:
            # Count occurrences — toggle in_docstring when odd number of delimiters
            # Simple heuristic: if line starts/ends with """ or contains """ once, toggle
            dbl = stripped_line.count('"""')
            sgl = stripped_line.count("'''")
            total = dbl + sgl
            if total % 2 == 1:
                in_docstring = not in_docstring
                continue
        if in_docstring:
            continue
        if not stripped_line.startswith("#"):
            stripped.append(line)
    body = "\n".join(stripped)
    assert (
        "ttl=" not in body
    ), "decrypt_provider_key MUST NOT pass ttl= (Landmine #4)"


def test_multifernet_decrypts_with_secondary_key(monkeypatch) -> None:
    """D-24 seam: a ciphertext produced by an old key still decrypts after rotation
    when the old key is appended to the MultiFernet list.

    Phase 1b ships single-key MultiFernet, but the seam must already hold."""
    old_key = Fernet.generate_key()
    new_key = Fernet.generate_key()

    # 1. Encrypt under the old key
    _set_key(monkeypatch, old_key.decode())
    old_ciphertext = encrypt_provider_key("sk-old")
    _reset_fernet_cache_for_tests()

    # 2. After rotation: the MultiFernet is [new, old] — both decrypt the old ciphertext
    _set_key(monkeypatch, new_key.decode())
    # Manually simulate a multi-key MultiFernet (Phase 1b's _build_multifernet returns single-key)
    # For this test, monkeypatch the cache directly
    from app import encryption as enc_mod

    enc_mod._cached = MultiFernet([Fernet(new_key), Fernet(old_key)])

    assert decrypt_provider_key(old_ciphertext) == "sk-old"
    # New writes use the primary (new) key
    new_ciphertext = encrypt_provider_key("sk-new")
    assert decrypt_provider_key(new_ciphertext) == "sk-new"