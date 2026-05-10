---
phase: 1b
plan: "03"
name: encryption-fernet
wave: 1
depends_on: ["01"]
requirements: [AUTH-09]
files_modified:
  - server/app/encryption.py
  - server/app/tests/auth/test_encryption.py
autonomous: true
must_haves:
  truths:
    - "encrypt_provider_key(plaintext) round-trips through decrypt_provider_key(ciphertext) for any UTF-8 string"
    - "decrypt_provider_key NEVER passes ttl= to Fernet.decrypt — provider keys are at-rest with no expiry (Landmine #4)"
    - "fernet() accessor raises FernetKeyMissing if SMARTCOPILOT_FERNET_KEY is empty/missing"
    - "Internal cipher is MultiFernet([primary]) from day 1 — adding rotation key later is a one-line list extension (D-24)"
    - "Module is import-safe — calling fernet() is required to trigger key validation; no work happens at module import time"
  artifacts:
    - path: "server/app/encryption.py"
      provides: "encrypt_provider_key, decrypt_provider_key, fernet(), FernetKeyMissing"
    - path: "server/app/tests/auth/test_encryption.py"
      provides: "4 unit tests — fernet roundtrip + missing-key + ttl-not-passed + multifernet seam (Wave 0 stubs implemented)"
  key_links:
    - from: "server/app/encryption.py"
      to: "server/app/settings.py:smartcopilot_fernet_key"
      via: "lazy module-level singleton via fernet() accessor"
      pattern: "settings.smartcopilot_fernet_key"
threat_refs: [T-1b-01, T-1b-09]
---

<plan_objective>
Land `server/app/encryption.py` — the Fernet/MultiFernet seam used by `services/provider_keys.py` (Plan 06) to encrypt provider API keys at rest. The module exposes `encrypt_provider_key(str) -> bytes`, `decrypt_provider_key(bytes) -> str`, a lazy `fernet()` accessor, and a `FernetKeyMissing` exception. `MultiFernet` is wired from day 1 (D-24) so future rotation is a one-line settings change. `decrypt_provider_key` MUST NOT pass `ttl=` (Landmine #4 — would silently expire valid stored keys). Tests for these properties are implemented in this plan (turning the Wave-0 stubs from Plan 01 into real tests).
</plan_objective>

<threat_model>

## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Disk/DB at-rest provider_keys.encrypted_key (BYTEA) ↔ runtime memory | Master Fernet key gates the boundary; key compromise = full provider-key disclosure |
| Container startup ↔ runtime requests | Container MUST refuse to start if SMARTCOPILOT_FERNET_KEY is absent — silent acceptance of empty key would mean provider_keys decrypt with a random per-process key (rotation/data corruption surface) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-1b-01 | I (Information Disclosure) | encrypted_key BYTEA at rest in provider_keys | mitigate | All writes go through `encrypt_provider_key`; reads via `decrypt_provider_key`. Fernet AES-128-CBC + HMAC-SHA256 authenticates every ciphertext (constant-time). Plan 06 + CI grep gate ensures `Field(exclude=True)` keeps the column out of every Pydantic response model. |
| T-1b-09 | A (Availability — boot) + I | container start with no Fernet key | mitigate | `fernet()` raises `FernetKeyMissing("SMARTCOPILOT_FERNET_KEY env var is required to start")` on first call when settings field is empty. Plan 07 wires `fernet()` into `main.py` lifespan/module-load so uvicorn refuses to start. Documented in `.env.example` (Plan 01) with `python -c "Fernet.generate_key()"` snippet. |

</threat_model>

<read_first_global>
- server/app/database.py (lazy/eager singleton pattern; module structure to mirror)
- server/app/settings.py (smartcopilot_fernet_key field — already present from Phase 1a)
- .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md D-24 (MultiFernet from day 1), D-28 (Field(exclude=True) — Plan 06 not 03)
- .planning/phases/01b-auth-security-primitives/01b-RESEARCH.md §"Pattern 5" (lines 482-525), §"Landmine #4" (Fernet TTL footgun, lines 873-888)
- .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md "server/app/encryption.py (NEW — utility / Fernet seam)" section
- server/app/tests/auth/test_encryption.py (Wave 0 stubs created in Plan 01 — turn into real tests)
</read_first_global>

<tasks>

<task type="auto" tdd="true">
  <id>03-01</id>
  <name>Task 1: Implement encryption.py — Fernet/MultiFernet wrapper</name>
  <read_first>
    - server/app/database.py (singleton + module-docstring + `from __future__ import annotations` + `from app.settings import settings` pattern)
    - .planning/phases/01b-auth-security-primitives/01b-RESEARCH.md §"Pattern 5" code block (lines 484-525)
    - .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md "server/app/encryption.py (NEW)" section
    - server/app/tests/auth/test_encryption.py (Wave 0 stubs — drive the implementation)
  </read_first>
  <behavior>
    - `encrypt_provider_key(plaintext: str) -> bytes` returns Fernet ciphertext bytes.
    - `decrypt_provider_key(ciphertext: bytes) -> str` returns the original plaintext.
    - `decrypt_provider_key` calls `fernet().decrypt(ciphertext)` with NO `ttl=` argument — passing ttl would silently expire stored keys (Landmine #4).
    - `fernet()` raises `FernetKeyMissing("SMARTCOPILOT_FERNET_KEY env var is required to start")` if `settings.smartcopilot_fernet_key` is empty/falsy.
    - `fernet()` returns a `MultiFernet` instance from day 1, even when only one key is configured (D-24).
    - The cached `MultiFernet` is module-level lazy — built on first call to `fernet()`, not at import time.
    - A test helper `_reset_fernet_cache()` (or equivalent) clears the singleton so tests can swap settings.
  </behavior>
  <action>
    Create `server/app/encryption.py`:

    ```python
    """Fernet/MultiFernet seam for provider API keys at rest (D-24).

    AUTH-09 / PRD §24.2: provider keys are encrypted with Fernet AES-128-CBC + HMAC.
    MultiFernet is wired from day 1 so rotation is a one-line list extension later.

    Landmine #4: decrypt_provider_key MUST NOT pass ttl= — Fernet's TTL is
    "seconds since ciphertext was created", which would silently expire valid
    at-rest keys. Default ttl=None disables expiry. CI grep gate in Plan 08
    rejects any decrypt(...,ttl=...) call.
    """
    from __future__ import annotations

    from cryptography.fernet import Fernet, MultiFernet

    from app.settings import settings


    class FernetKeyMissing(RuntimeError):
        """Raised when SMARTCOPILOT_FERNET_KEY is empty or missing at startup."""


    _cached: MultiFernet | None = None


    def _build_multifernet() -> MultiFernet:
        """Build the MultiFernet from settings.smartcopilot_fernet_key.

        Why MultiFernet from day 1 (D-24): future rotation is `MultiFernet([new, primary])`
        — one-line change, no call-site touches. Fernet ciphertexts produced now
        will still decrypt under any future MultiFernet that includes this key.
        """
        key = settings.smartcopilot_fernet_key
        if not key:
            raise FernetKeyMissing(
                "SMARTCOPILOT_FERNET_KEY env var is required to start"
            )
        primary = Fernet(key.encode() if isinstance(key, str) else key)
        return MultiFernet([primary])


    def fernet() -> MultiFernet:
        """Lazy accessor — first call validates the env var; subsequent calls reuse.

        Container fail-on-startup wiring lives in Plan 07's main.py — this module
        stays import-safe (no work at import time) so tests can swap settings.
        """
        global _cached
        if _cached is None:
            _cached = _build_multifernet()
        return _cached


    def encrypt_provider_key(plaintext: str) -> bytes:
        """Encrypt a provider API key plaintext for at-rest storage in BYTEA."""
        return fernet().encrypt(plaintext.encode())


    def decrypt_provider_key(ciphertext: bytes) -> str:
        """Decrypt a stored provider key.

        IMPORTANT (Landmine #4): do NOT pass ttl=. Provider keys are at-rest with
        no expiry — Fernet's TTL would silently expire valid stored keys, breaking
        all LLM calls 24h after key creation. Default ttl=None is correct for
        at-rest secrets.
        """
        return fernet().decrypt(ciphertext).decode()


    def _reset_fernet_cache_for_tests() -> None:
        """Test-only helper to clear the MultiFernet cache after monkey-patching settings."""
        global _cached
        _cached = None
    ```

    Module is import-safe — `from app.encryption import ...` triggers no IO/key access. Container startup-fail wiring is the responsibility of Plan 07 (`main.py`).
  </action>
  <acceptance_criteria>
    - `test -f server/app/encryption.py`
    - `grep -q "from cryptography.fernet import Fernet, MultiFernet" server/app/encryption.py` returns 0
    - `grep -q "class FernetKeyMissing(RuntimeError)" server/app/encryption.py` returns 0
    - `grep -q "MultiFernet(\[primary\])" server/app/encryption.py` returns 0
    - **CI grep gate (T-1b-01 / Landmine #4):** `! grep -E 'decrypt\([^)]*ttl=' server/app/encryption.py` returns 0 (no ttl= argument anywhere)
    - Module is import-safe (no eager work, no failure at import): `cd server && SMARTCOPILOT_FERNET_KEY= python -c "import app.encryption; print('ok')"` prints `ok`
    - `cd server && ruff check app/encryption.py` exits 0
  </acceptance_criteria>
  <done>encrypt/decrypt round-trip works; missing key raises FernetKeyMissing; MultiFernet is the cached cipher; ttl= never passed.</done>
  <threat_ref>T-1b-01</threat_ref>
</task>

<task type="auto">
  <id>03-02</id>
  <name>Task 2: Implement test_encryption.py (turn Wave-0 stubs into real tests)</name>
  <read_first>
    - server/app/tests/auth/test_encryption.py (Wave 0 stubs from Plan 01 — same test names retained)
    - server/app/encryption.py (just created — public API)
    - .planning/phases/01b-auth-security-primitives/01b-RESEARCH.md §"Validation Architecture" rows for AUTH-09 (4 unit tests + 1 integration; this plan covers the unit tests; integration sits in Plan 06)
  </read_first>
  <action>
    Replace the four `pytest.skip("Wave 0 stub …")` bodies in `server/app/tests/auth/test_encryption.py` with real implementations. Use `monkeypatch` and `_reset_fernet_cache_for_tests()` to swap keys per-test:

    ```python
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
        import inspect
        from app import encryption
        src = inspect.getsource(encryption.decrypt_provider_key)
        # Allow whitespace variations; reject any ttl= keyword in the body
        non_comment = "\n".join(line for line in src.splitlines() if not line.strip().startswith("#"))
        assert "ttl=" not in non_comment, "decrypt_provider_key MUST NOT pass ttl= (Landmine #4)"


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
    ```

    Ensure file imports/structure compiles. Other Wave-0 test files (e.g. test_password.py) remain skipped — those land in Plan 04.
  </action>
  <acceptance_criteria>
    - `cd server && pytest -x -q app/tests/auth/test_encryption.py` exits 0 (4 tests pass)
    - All four canonical test names present: `for n in test_fernet_roundtrip test_missing_fernet_key_raises_FernetKeyMissing test_decrypt_does_not_use_ttl test_multifernet_decrypts_with_secondary_key; do grep -q "def $n" server/app/tests/auth/test_encryption.py || { echo "missing $n"; exit 1; }; done` exits 0
    - No remaining skips in this file: `! grep -q 'pytest.skip("Wave 0 stub' server/app/tests/auth/test_encryption.py` returns 0
    - `cd server && ruff check app/tests/auth/test_encryption.py` exits 0
    - Phase 1a tests still green: `cd server && pytest -q app/tests/integration/` exits 0
  </acceptance_criteria>
  <done>4 unit tests pass; Landmine #4 source-level gate enforced; MultiFernet rotation seam validated.</done>
  <threat_ref>T-1b-01</threat_ref>
</task>

</tasks>

<verification>
  <command>cd server && ruff check app/encryption.py app/tests/auth/test_encryption.py && pytest -x -q app/tests/auth/test_encryption.py</command>
  <expected>4 unit tests pass; no skipped tests in test_encryption.py; ruff clean.</expected>
</verification>

<must_haves>

## Truths
- `encrypt_provider_key`/`decrypt_provider_key` round-trip preserves arbitrary UTF-8 plaintext.
- `decrypt_provider_key` body contains NO `ttl=` (source-level test enforces).
- `fernet()` raises `FernetKeyMissing` when env var is empty.
- MultiFernet seam validated by a test that wires `[new, old]` and decrypts ciphertext from either key.
- Module is import-safe (no work at import time; key validation deferred to first `fernet()` call).

## Artifacts
- `server/app/encryption.py` — Fernet/MultiFernet seam.
- `server/app/tests/auth/test_encryption.py` — 4 implemented unit tests (replacing Plan 01 stubs).

## Key Links
- `encryption.fernet()` ← `settings.smartcopilot_fernet_key` (lazy).
- Container fail-on-startup wire-up deferred to Plan 07 (`main.py`).
- Plan 06 `services/provider_keys.py` consumes `encrypt_provider_key`/`decrypt_provider_key`.

</must_haves>

<output>
Append per-task rows to `.planning/phases/01b-auth-security-primitives/01B-VALIDATION.md`. Create `01B-03-SUMMARY.md` documenting MultiFernet seam choice and Landmine #4 source-level gate.
</output>
