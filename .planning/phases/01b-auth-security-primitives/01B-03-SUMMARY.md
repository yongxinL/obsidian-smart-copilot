---
phase: "1b"
plan: "03"
name: encryption-fernet
subsystem: auth
tags: [AUTH-09, encryption, fernet, security]
dependency_graph:
  requires: []
  provides: [encrypt_provider_key, decrypt_provider_key, fernet(), FernetKeyMissing]
  affects: [services/provider_keys.py, server/app/main.py]
tech_stack:
  added: [cryptography (Fernet, MultiFernet)]
  patterns: [lazy singleton, import-safe module, source-level TTL gate]
key_files:
  created:
    - server/app/encryption.py
    - server/app/tests/auth/test_encryption.py
    - server/app/tests/auth/__init__.py
  modified: []
decisions:
  - "MultiFernet([primary]) from day 1 — D-24; rotation deferred to post-Phase-5 but seam present"
  - "Lazy fernet() accessor defers key validation to first call — import-safe, testable"
  - "Landmine #4: decrypt_provider_key body contains NO ttl= (source-level AST test guard)"
threat_refs: [T-1b-01, T-1b-09]
---
# Phase 1b Plan 03: Fernet Encryption Summary

**One-liner:** Fernet/MultiFernet seam with import-safe lazy initialization, Landmine #4 source-level TTL guard.

## What Was Built

### `server/app/encryption.py`

Pure Python module providing:

- `encrypt_provider_key(plaintext: str) -> bytes` — Fernet AES-128-CBC + HMAC-SHA256 encrypt
- `decrypt_provider_key(ciphertext: bytes) -> str` — decrypt, **never passes ttl=**
- `fernet() -> MultiFernet` — lazy singleton; validates `SMARTCOPILOT_FERNET_KEY` on first call
- `FernetKeyMissing` — raised when key is empty/missing
- `_reset_fernet_cache_for_tests()` — test helper to clear singleton between tests

Key design decisions:

- **MultiFernet from day 1 (D-24):** Rotation in the future is `MultiFernet([new, primary])` — one-line change, no call-site touch. Fernet ciphertexts produced now still decrypt under any future MultiFernet that includes this key.
- **Import-safe:** Module does zero I/O at import time. Container fail-on-startup is wired in Plan 07 (`main.py`), not here.
- **Landmine #4 enforced at source level:** `test_decrypt_does_not_use_ttl` uses AST parsing to strip docstrings and comments before checking for `ttl=` in the function body.

### `server/app/tests/auth/test_encryption.py`

Four unit tests (all passing):

| Test | Purpose |
|------|---------|
| `test_fernet_roundtrip` | Encrypt/decrypt preserves arbitrary UTF-8 plaintext |
| `test_missing_fernet_key_raises_FernetKeyMissing` | Empty key raises `FernetKeyMissing` with env-var name |
| `test_decrypt_does_not_use_ttl` | AST-parse body; fail if `ttl=` appears (Landmine #4 guard) |
| `test_multifernet_decrypts_with_secondary_key` | Rotation seam validated: `[new, old]` MultiFernet decrypts both old and new ciphertexts |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Critical] Test for Landmine #4 needed AST parsing, not line filtering**

- **Found during:** Task 2 (implementing test_encryption.py)
- **Issue:** Initial `test_decrypt_does_not_use_ttl` used simple line filtering (`non_comment = "\n".join(...)`). The Fernet import comment (`# NOTE: do NOT pass ttl=.`) and the docstring in `decrypt_provider_key` both contained `ttl=` text, causing a false-positive failure.
- **Fix:** Replaced line filtering with AST parsing that strips docstrings before checking the body.
- **Files modified:** `server/app/tests/auth/test_encryption.py`
- **Commit:** `d1b30bf`

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: at-rest-encryption | server/app/encryption.py | Fernet AES-128-CBC + HMAC-SHA256 at provider key boundary; key compromise = full disclosure |

## Known Stubs

None. All artifacts for this plan are fully implemented.

## Verification

```bash
cd server && ruff check app/encryption.py app/tests/auth/test_encryption.py
cd server && pytest -x -q app/tests/auth/test_encryption.py
# Expected: 4 passed
cd server && pytest -x -q app/tests/integration/
# Expected: 7 passed (Phase 1a tests remain green)
```

## Commits

| Hash | Message |
|------|---------|
| `d1b30bf` | feat(01b-03): add Fernet/MultiFernet seam for provider API keys at rest |

## Metrics

- **Duration:** ~5 min
- **Files created:** 3
- **Tests added:** 4
- **Phase 1a regression:** None (7 integration tests still pass)