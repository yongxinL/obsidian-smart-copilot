"""Vault file parser tests — VAULT-04, VAULT-05, VAULT-07.

NO FastAPI imports. NO SQLAlchemy imports.
"""

from __future__ import annotations

import pytest

from app.vault.parser import (
    BodyShape,
    VaultParseError,
    VaultTimelineError,
    assert_timeline_append_only,
    extract_wikilinks,
    parse_vault_file,
)

pytestmark = [pytest.mark.vault, pytest.mark.unit]


# ─── BodyShape enum ────────────────────────────────────────────────────────────


def test_body_shape_is_str_enum() -> None:
    """BodyShape members are strings so they can be used in comparisons."""
    assert BodyShape.compiled_truth_only == "compiled_truth_only"
    assert BodyShape.mixed == "mixed"
    assert BodyShape.empty == "empty"


# ─── parse_vault_file — compiled_truth_only ────────────────────────────────────


def test_parse_compiled_truth_only() -> None:
    """No separator → whole body is compiled_truth, timeline is empty."""
    raw = b"---\ntype: note\n---\nBody content\n"
    result = parse_vault_file(raw)

    assert result.body_shape == BodyShape.compiled_truth_only
    assert result.compiled_truth == "Body content"
    assert result.timeline == ""
    assert result.frontmatter["type"] == "note"


# ─── parse_vault_file — mixed ──────────────────────────────────────────────────


def test_parse_mixed_body() -> None:
    """Standalone ``---`` separates compiled_truth (above) from timeline (below)."""
    raw = b"---\n---\nAbove line\n---\nBelow line\n"
    result = parse_vault_file(raw)

    assert result.body_shape == BodyShape.mixed
    assert result.compiled_truth == "Above line"
    assert result.timeline == "Below line"


# ─── parse_vault_file — empty ──────────────────────────────────────────────────


def test_parse_empty_body() -> None:
    """Empty body (no content after frontmatter) → body_shape empty."""
    raw = b"---\n---\n"
    result = parse_vault_file(raw)

    assert result.body_shape == BodyShape.empty
    assert result.compiled_truth == ""
    assert result.timeline == ""


# ─── parse_vault_file — VaultParseError ───────────────────────────────────────


def test_multiple_separators_raises() -> None:
    """Two ``---`` separators in body raise VaultParseError."""
    raw = b"---\n---\nA\n---\nB\n---\nC\n"

    with pytest.raises(VaultParseError) as exc_info:
        parse_vault_file(raw)

    assert "Multiple compiled-truth/timeline separators found" in str(exc_info.value)


# ─── parse_vault_file — frontmatter types ─────────────────────────────────────


def test_frontmatter_page_types() -> None:
    """Page type is accessible in frontmatter dict after parsing."""
    raw = b"---\ntype: person\nname: Alice\n---\nAlice's content\n"
    result = parse_vault_file(raw)

    assert result.frontmatter["type"] == "person"
    assert result.frontmatter["name"] == "Alice"
    assert result.body_shape == BodyShape.compiled_truth_only


# ─── parse_vault_file — content_hash ──────────────────────────────────────────


def test_content_hash_dedup() -> None:
    """Same bytes produce the same hash; mutated bytes produce a different hash."""
    raw1 = b"---\n---\nContent\n"
    raw2 = b"---\n---\nDifferent\n"

    result1 = parse_vault_file(raw1)
    result2 = parse_vault_file(raw2)
    result1_again = parse_vault_file(raw1)

    assert result1.content_hash == result1_again.content_hash
    assert result1.content_hash != result2.content_hash
    # xxhash64 produces a 16-character hex string
    assert len(result1.content_hash) == 16


# ─── parse_vault_file — _resolved_links stripped (Pitfall 8) ──────────────────


def test_resolved_links_stripped_from_user_frontmatter() -> None:
    """_resolved_links in user frontmatter must be absent from ParsedPage.frontmatter.

    Pitfall 8: _resolved_links is a reserved system key. The parser strips it
    so user-provided data cannot overwrite computed resolved-link metadata.
    Other frontmatter keys (including similar-looking ones) are preserved.
    """
    raw = b"---\ntype: note\n_resolved_links:\n  - raw: [[Target]]\n---\nBody\n"
    result = parse_vault_file(raw)

    assert "_resolved_links" not in result.frontmatter
    # Other frontmatter keys (not matching _resolved_links) are preserved
    assert result.frontmatter["type"] == "note"


# ─── assert_timeline_append_only ───────────────────────────────────────────────


def test_timeline_append_only_accepts_extension() -> None:
    """Appending new lines to existing timeline is allowed."""
    existing = "line1\n"
    submitted = "line1\nline2\n"

    # Should not raise
    assert_timeline_append_only(existing, submitted)


def test_timeline_append_only_rejects_edit() -> None:
    """Editing an existing timeline line raises VaultTimelineError."""
    existing = "line1\n"
    submitted = "modified\nline2\n"

    with pytest.raises(VaultTimelineError) as exc_info:
        assert_timeline_append_only(existing, submitted)

    assert "append-only" in str(exc_info.value).lower()


def test_timeline_append_only_rejects_reorder() -> None:
    """Reordering existing timeline lines raises VaultTimelineError."""
    existing = "line1\nline2\n"
    submitted = "line2\nline1\nline3\n"

    with pytest.raises(VaultTimelineError):
        assert_timeline_append_only(existing, submitted)


# ─── extract_wikilinks ─────────────────────────────────────────────────────────


def test_wikilink_extraction() -> None:
    """extract_wikilinks returns correct dicts for private and shared wikilinks."""
    content = "See [[Topic]] and [[shared/Other|alias]] and [[shared/Deep/Page]]."
    links = extract_wikilinks(content)

    assert len(links) == 3

    # [[Topic]]
    assert links[0]["raw"] == "[[Topic]]"
    assert links[0]["target_text"] == "Topic"
    assert links[0]["namespace"] == "private"

    # [[shared/Other|alias]]
    assert links[1]["raw"] == "[[shared/Other|alias]]"
    assert links[1]["target_text"] == "shared/Other"
    assert links[1]["namespace"] == "shared"

    # [[shared/Deep/Page]]
    assert links[2]["target_text"] == "shared/Deep/Page"
    assert links[2]["namespace"] == "shared"


def test_wikilink_extraction_no_matches() -> None:
    """extract_wikilinks returns empty list when no [[...]] patterns present."""
    result = extract_wikilinks("No wikilinks here.")
    assert result == []


def test_wikilink_extraction_no_duplicates() -> None:
    """extract_wikilinks does not double-count overlapping patterns."""
    content = "[[A]][[B]]"
    links = extract_wikilinks(content)

    assert len(links) == 2
    assert [lk["target_text"] for lk in links] == ["A", "B"]
