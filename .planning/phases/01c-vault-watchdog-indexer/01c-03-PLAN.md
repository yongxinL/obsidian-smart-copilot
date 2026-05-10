---
phase: 01c
plan: 03
type: execute
wave: 1
depends_on:
  - "01c-01"
  - "01c-02"
files_modified:
  - server/app/vault/__init__.py
  - server/app/vault/parser.py
  - server/app/vault/paths.py
  - server/app/tests/vault/test_paths.py
  - server/app/tests/vault/test_parser.py
autonomous: true
requirements:
  - VAULT-01
  - VAULT-04
  - VAULT-05
  - VAULT-07
  - VAULT-10

must_haves:
  truths:
    - "parse_vault_file returns ParsedPage with correct compiled_truth, timeline, body_shape, content_hash"
    - "Multiple --- separators in body raise VaultParseError"
    - "assert_timeline_append_only rejects edits, accepts appends"
    - "extract_wikilinks returns list of dicts with raw/target_text/namespace"
    - "_resolved_links key stripped from user frontmatter before returning ParsedPage"
    - "safe_vault_path rejects .. traversal and symlink escapes using os.path.realpath on BOTH paths"
    - "validate_slug rejects slugs not matching ^[a-z0-9][a-z0-9-]{0,127}$"
    - "test_paths.py unit tests pass (not SKIP)"
    - "test_parser.py unit tests pass (not SKIP)"
  artifacts:
    - path: "server/app/vault/parser.py"
      provides: "BodyShape, ParsedPage, parse_vault_file, assert_timeline_append_only, extract_wikilinks, VaultParseError, VaultTimelineError"
      contains: "class BodyShape"
    - path: "server/app/vault/paths.py"
      provides: "safe_vault_path, validate_slug, sanitize_filename_to_slug, PathTraversalError, InvalidSlugError"
      contains: "_SLUG_RE"
    - path: "server/app/tests/vault/test_paths.py"
      provides: "Passing unit tests for VAULT-01 and VAULT-10"
    - path: "server/app/tests/vault/test_parser.py"
      provides: "Passing unit tests for VAULT-04, VAULT-05, VAULT-07"
  key_links:
    - from: "server/app/vault/parser.py"
      to: "python-frontmatter"
      via: "frontmatter.loads(raw.decode('utf-8')) strips YAML block, returns post.content"
      pattern: "frontmatter.loads"
    - from: "server/app/vault/paths.py"
      to: "os.path.realpath"
      via: "VAULT-01: realpath on BOTH root AND candidate before relative_to()"
      pattern: "os.path.realpath"
---

<objective>
Implement `vault/parser.py` and `vault/paths.py` — pure functions with no DB or FastAPI imports. Then replace the Wave 0 stubs in `test_paths.py` and `test_parser.py` with real passing unit tests.

Purpose: These pure-function modules are consumed by the page service (Wave 2) and watchdog (Wave 3). Building them first with test coverage de-risks all downstream work.

Output: `vault/parser.py`, `vault/paths.py`, two test files with passing unit tests.
</objective>

<context>
@.planning/phases/01c-vault-watchdog-indexer/01c-CONTEXT.md
@.planning/phases/01c-vault-watchdog-indexer/01c-RESEARCH.md

<interfaces>
<!-- What the page service (Plan 04) will import from this plan's output -->
```python
from app.vault.parser import (
    ParsedPage, BodyShape, VaultParseError, VaultTimelineError,
    parse_vault_file, assert_timeline_append_only, extract_wikilinks,
)
from app.vault.paths import (
    safe_vault_path, validate_slug, sanitize_filename_to_slug,
    PathTraversalError, InvalidSlugError,
)
```

<!-- python-frontmatter API (installed, v1.1.0) -->
```python
import frontmatter
post = frontmatter.loads(raw_str)   # raw_str = raw_bytes.decode("utf-8")
post.metadata   # dict — YAML frontmatter keys
post.content    # str — body WITHOUT frontmatter block (and without leading ---)
```

<!-- xxhash API (installed, v3.7.0) -->
```python
import xxhash
xxhash.xxh64(raw_bytes).hexdigest()  # -> 16-char hex string
```

<!-- Analog: auth/password.py — pure function module pattern -->
```python
"""Module docstring referencing decisions.
NO FastAPI imports. NO DB imports.
"""
from __future__ import annotations
# stdlib only + mandated third-party pure libs
class SomeDomainError(Exception): ...  # one-liner error classes
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement vault/parser.py and vault/paths.py</name>
  <read_first>
    - server/app/vault/__init__.py (current content — may be minimal stub)
    - server/app/auth/password.py (pure function module pattern for imports/docstring/error style)
    - server/app/services/users.py (lines 18-21 — one-liner error class pattern: class X(Exception): ...)
    - .planning/phases/01c-vault-watchdog-indexer/01c-RESEARCH.md (Pattern 1: safe_vault_path; Pattern 2: parse_vault_file; Pattern 3: timeline diff; Pitfall 1: Path.is_relative_to is string-only; Pitfall 8: _resolved_links strip)
    - .planning/phases/01c-vault-watchdog-indexer/01c-CONTEXT.md (D-01 separator algorithm, D-02/D-03, D-05 body_shape, D-09 wikilink regex)
    - parse_vault_file(b"---\ntype: note\n---\nBody\n") -> body_shape=compiled_truth_only, compiled_truth="Body", timeline=""
    - parse_vault_file(b"---\n---\nAbove\n---\nBelow\n") -> body_shape=mixed, compiled_truth="Above", timeline="Below"
    - parse_vault_file(b"---\n---\nA\n---\nB\n---\nC") -> raises VaultParseError (two separators)
    - parse_vault_file with frontmatter containing _resolved_links -> _resolved_links absent from ParsedPage.frontmatter
    - assert_timeline_append_only("line1\n", "line1\nline2\n") -> no exception (append allowed)
    - assert_timeline_append_only("line1\n", "modified\nline2\n") -> raises VaultTimelineError
    - extract_wikilinks("See [[Topic]] and [[shared/Other|alias]]") -> [{raw:"[[Topic]]", target_text:"Topic", namespace:"private"}, {raw:"[[shared/Other|alias]]", target_text:"shared/Other", namespace:"shared"}]
    - safe_vault_path("/vault", "my-note") -> Path("/vault/my-note.md") within root
    - safe_vault_path("/vault", "../../../etc") -> raises PathTraversalError
    - validate_slug("my-note-123") -> no exception
    - validate_slug("My-Note") -> raises InvalidSlugError (uppercase)
    - validate_slug("-bad") -> raises InvalidSlugError (leading hyphen)
    - sanitize_filename_to_slug("My Note!.md") -> starts with "my-note"
  </behavior>
  <action>
**CRITICAL IMPLEMENTATION RULES (read before writing any code):**
- VAULT-01: `safe_vault_path` MUST call `os.path.realpath()` on BOTH `vault_root` AND `root / f"{slug}.md"` before `relative_to()`. `Path.is_relative_to()` is string-only and does NOT resolve symlinks. Never shortcut this.
- D-01: The separator scan looks for lines where `line.strip() == "---"`. It raises VaultParseError on the SECOND occurrence.
- D-05: `BodyShape` is a Python `str, Enum` — NOT stored in DB.
- Pitfall 8: Call `fm.pop("_resolved_links", None)` immediately after `fm: dict = dict(post.metadata)`.
- D-discretion: wikilink regex is `re.compile(r"\[\[([^\]]+)\]\]")` — simple, no markdown-it plugin.
- No FastAPI imports, no SQLAlchemy imports anywhere in parser.py or paths.py.

**1. Update `server/app/vault/__init__.py`:**
Replace contents with: `"""Vault filesystem utilities — parser, path safety, and watchdog."""`

**2. Create `server/app/vault/parser.py`**. Key elements:
- Module docstring referencing D-01, D-02, D-05, VAULT-07, Pitfall 8
- `from __future__ import annotations` first
- Imports: `re`, `dataclasses.dataclass`, `enum.Enum`, `frontmatter`, `xxhash`
- `_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")` compiled at module level
- `class BodyShape(str, Enum)` with values: `compiled_truth_only`, `timeline_only`, `mixed`, `empty`
- `@dataclass class ParsedPage` with fields: `frontmatter: dict`, `compiled_truth: str`, `timeline: str`, `body_shape: BodyShape`, `content_hash: str`
- `class VaultParseError(Exception): ...`
- `class VaultTimelineError(Exception): ...`
- `def parse_vault_file(raw_bytes: bytes) -> ParsedPage:` — follow D-01 algorithm exactly
- `def assert_timeline_append_only(existing_timeline: str, submitted_timeline: str) -> None:` — line-based prefix check
- `def extract_wikilinks(content: str) -> list[dict]:` — returns `[{raw, target_text, namespace}]`, namespace="shared" if target_text starts with "shared/"

**3. Create `server/app/vault/paths.py`**. Key elements:
- Module docstring referencing VAULT-01, VAULT-10
- `from __future__ import annotations` first
- Imports: `os`, `re`, `pathlib.Path`
- `_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{0,127}$")` compiled at module level
- `_INVALID_SLUG_CHAR_RE = re.compile(r"[^a-z0-9\-]")` for sanitizer
- `class PathTraversalError(PermissionError): ...`
- `class InvalidSlugError(ValueError): ...`
- `def validate_slug(slug: str) -> None:` — raises InvalidSlugError if not matched
- `def safe_vault_path(vault_root: str, slug: str) -> Path:` — realpath on both paths, relative_to check, raises PathTraversalError
- `def sanitize_filename_to_slug(filename: str) -> str:` — stem → lower → replace invalid → truncate 128 → lstrip("-") → fallback "untitled"
  </action>
  <verify>
    <automated>cd /home/yongxin.Li/Documents/nexora/smart-copilot/server && python -c "from app.vault.parser import parse_vault_file, BodyShape, VaultParseError; from app.vault.paths import validate_slug, InvalidSlugError; r=parse_vault_file(b'---\ntype: note\n---\nHello\n'); assert r.body_shape==BodyShape.compiled_truth_only; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `server/app/vault/parser.py` exists and imports without error
    - `server/app/vault/paths.py` exists and imports without error
    - `from app.vault.parser import ParsedPage, BodyShape, VaultParseError, VaultTimelineError, parse_vault_file, assert_timeline_append_only, extract_wikilinks` succeeds
    - `from app.vault.paths import safe_vault_path, validate_slug, sanitize_filename_to_slug, PathTraversalError, InvalidSlugError` succeeds
    - parser.py contains `_WIKILINK_RE = re.compile(` (wikilink regex compiled at import time)
    - parser.py contains `fm.pop("_resolved_links", None)` (Pitfall 8 guard)
    - paths.py contains `os.path.realpath(vault_root)` AND `os.path.realpath(root /` (both sides realpathd)
    - paths.py contains `_SLUG_RE = re.compile(r"^[a-z0-9]`
    - Neither file contains `from fastapi` or `from sqlalchemy` imports
  </acceptance_criteria>
  <done>vault/parser.py and vault/paths.py implemented as pure-function modules; no FastAPI/SQLAlchemy imports; all public functions present and importable</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Replace test_paths.py and test_parser.py stubs with real unit tests</name>
  <read_first>
    - server/app/tests/vault/test_paths.py (current stub content — read all stubs to know which to replace)
    - server/app/tests/vault/test_parser.py (current stub content — read all stubs to know which to replace)
    - server/app/vault/parser.py (just created — read to understand exact API and error messages)
    - server/app/vault/paths.py (just created — read to understand exact API)
    - .planning/phases/01c-vault-watchdog-indexer/01c-RESEARCH.md (Pitfall 1: symlink escape test must include actual symlink fixture)
  </read_first>
  <files>server/app/tests/vault/test_paths.py, server/app/tests/vault/test_parser.py</files>
  <behavior>
    - test_safe_vault_path_resolves_within_root: safe_vault_path("/tmp/vault", "my-note") returns Path ending in "/my-note.md" that is within the root
    - test_safe_vault_path_rejects_dotdot_traversal: safe_vault_path("/tmp/vault", "../etc") raises PathTraversalError
    - test_safe_vault_path_rejects_symlink_escape: create symlink inside vault pointing outside, safe_vault_path resolves it and raises PathTraversalError
    - test_slug_validation_accepts_valid: validate_slug("my-note") passes, validate_slug("a") passes, validate_slug("a" + "b" * 127) passes (128 chars total)
    - test_slug_validation_rejects_uppercase: validate_slug("My-Note") raises InvalidSlugError
    - test_slug_validation_rejects_leading_hyphen: validate_slug("-bad") raises InvalidSlugError
    - test_slug_sanitizer_converts_watchdog_filename: sanitize_filename_to_slug("My Note!.md") returns "my-note-" prefix or similar
    - test_parse_compiled_truth_only: parse_vault_file returns body_shape=compiled_truth_only, timeline=""
    - test_parse_mixed_body: parse_vault_file with --- separator returns mixed, splits correctly
    - test_parse_empty_body: parse_vault_file(b"---\n---\n") returns body_shape=empty
    - test_multiple_separators_raises: raises VaultParseError
    - test_resolved_links_stripped: frontmatter with _resolved_links key -> ParsedPage.frontmatter has no _resolved_links
    - test_content_hash_dedup: same bytes produce same hash; different bytes produce different hash
    - test_timeline_append_only_accepts_extension: no exception when appending
    - test_timeline_append_only_rejects_edit: raises VaultTimelineError when existing line is modified
    - test_wikilink_extraction: extract_wikilinks("[[A]] [[shared/B|alias]]") returns correct dicts
  </behavior>
  <action>
**CRITICAL: These are unit tests (no DB, no fixtures). Use `tmp_path` from pytest for filesystem tests. Every test must be deterministic.**

**Replace `server/app/tests/vault/test_paths.py`** with real tests. Key implementation points:
- Import `pytest`, `pathlib.Path` and the vault functions: `safe_vault_path, validate_slug, sanitize_filename_to_slug, PathTraversalError, InvalidSlugError`
- `pytestmark = [pytest.mark.vault, pytest.mark.unit]`
- For `test_safe_vault_path_rejects_symlink_escape`: create `tmp_path / "vault"` as root, create `tmp_path / "secret.txt"`, create symlink `vault_root / "evil.md" -> ../../secret.txt`, then call `safe_vault_path(str(vault_root), "evil")` and expect `PathTraversalError`. Note: the symlink test verifies that `os.path.realpath` is used (string-only checks would NOT catch this).
- For slug length tests: `"a" * 128` is 128 chars and matches `^[a-z0-9][a-z0-9-]{0,127}$` (1 leading + 127 body). `"a" * 129` should fail (too long).
- Use `pytest.raises(PathTraversalError)` and `pytest.raises(InvalidSlugError)` context managers.

**Replace `server/app/tests/vault/test_parser.py`** with real tests. Key implementation points:
- Import `pytest` and `parse_vault_file, BodyShape, VaultParseError, assert_timeline_append_only, extract_wikilinks, VaultTimelineError`
- `pytestmark = [pytest.mark.vault, pytest.mark.unit]`
- Test body: `b"---\ntype: note\n---\nBody content\n"` → compiled_truth_only, compiled_truth contains "Body content"
- Test mixed: `b"---\n---\nAbove line\n---\nBelow line\n"` → mixed, compiled_truth="Above line", timeline="Below line"
- Test empty body: `b"---\n---\n"` or `b""` → body_shape=empty
- Test multiple separators: `b"---\n---\nA\n---\nB\n---\nC\n"` (two standalone `---` in body) → VaultParseError
- Test _resolved_links stripped: raw bytes with frontmatter `_resolved_links: [...]` → ParsedPage.frontmatter has no `_resolved_links` key
- Test content_hash: same bytes → same hash string; mutated bytes → different hash
- Test timeline append allows extension: `assert_timeline_append_only("line1", "line1\nline2")` → no exception
- Test timeline rejects edit: `assert_timeline_append_only("line1", "modified")` → VaultTimelineError
- Test wikilink extraction: `extract_wikilinks("See [[Topic]] and [[shared/B|alias]]")` → list with 2 items, second has namespace="shared", target_text="shared/B"
- Test frontmatter page types (VAULT-05): parse a file with `type: person` in frontmatter → ParsedPage.frontmatter["type"] == "person"
  </action>
  <verify>
    <automated>cd /home/yongxin.Li/Documents/nexora/smart-copilot/server && python -m pytest app/tests/vault/test_paths.py app/tests/vault/test_parser.py -x -q --no-header 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - `pytest app/tests/vault/test_paths.py -x -q` exits 0 with all tests PASSED (no SKIP)
    - `pytest app/tests/vault/test_parser.py -x -q` exits 0 with all tests PASSED (no SKIP)
    - test_safe_vault_path_rejects_symlink_escape test exists in test_paths.py (symlink escape is tested, not just dotdot)
    - test_multiple_separators_raises exists in test_parser.py
    - test_resolved_links_stripped_from_user_frontmatter exists in test_parser.py
    - No test in either file calls `pytest.skip()` (all stubs replaced)
    - No test has unused fixture parameters
  </acceptance_criteria>
  <done>test_paths.py and test_parser.py contain real passing unit tests covering VAULT-01, VAULT-04, VAULT-05, VAULT-07, VAULT-10; all tests pass; symlink escape test is present</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| user input → parse_vault_file | Raw bytes from filesystem or API; frontmatter parsed with python-frontmatter (PyYAML safe_load — no arbitrary object construction) |
| user slug → safe_vault_path | Slug used to construct filesystem path; realpath + relative_to guard prevents escape |
| user frontmatter → ParsedPage | _resolved_links stripped before returning to prevent user injection of system key |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-01c03-01 | Tampering / EoP | safe_vault_path | mitigate | `os.path.realpath` on both root and candidate before `relative_to()` — never use `Path.is_relative_to()` alone |
| T-01c03-02 | Tampering | _resolved_links injection | mitigate | `fm.pop("_resolved_links", None)` in parse_vault_file before returning |
| T-01c03-03 | DoS | YAML bomb in frontmatter | accept | python-frontmatter uses PyYAML safe_load internally — no arbitrary tag execution; bomb limited to YAML expansion which has practical limits |
| T-01c03-04 | Tampering | Timeline mutation via API | mitigate | assert_timeline_append_only enforces prefix invariant; raises VaultTimelineError on any mutation |
</threat_model>

<verification>
```bash
cd /home/yongxin.Li/Documents/nexora/smart-copilot/server

# Import check
python -c "
from app.vault.parser import parse_vault_file, BodyShape, VaultParseError, VaultTimelineError, assert_timeline_append_only, extract_wikilinks
from app.vault.paths import safe_vault_path, validate_slug, sanitize_filename_to_slug, PathTraversalError, InvalidSlugError
print('All imports OK')
"

# Unit tests must all pass (no SKIP)
python -m pytest app/tests/vault/test_paths.py app/tests/vault/test_parser.py -v --no-header

# Full vault test suite (stubs in other files still SKIP cleanly)
python -m pytest app/tests/vault/ -q --no-header 2>&1 | tail -5
```
</verification>

<success_criteria>
- `vault/parser.py` and `vault/paths.py` created as pure-function modules
- No FastAPI or SQLAlchemy imports in either module
- All public functions importable and correct per behavior spec
- `pytest app/tests/vault/test_paths.py app/tests/vault/test_parser.py` exits 0 with all tests PASSED
- Symlink escape test is present and exercises `os.path.realpath` invariant
- _resolved_links strip test is present and passing
</success_criteria>

<output>
After completion, create `.planning/phases/01c-vault-watchdog-indexer/01c-03-SUMMARY.md`
</output>
