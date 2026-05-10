"""Vault file parser — frontmatter, compiled-truth/timeline, wikilinks.

References: D-01 (separator algorithm), D-02/D-03 (timeline append-only),
D-05 (BodyShape), VAULT-07 (content-hash via xxhash64), VAULT-09 (wikilink
regex), Pitfall 8 (_resolved_links strip from user frontmatter).

NO FastAPI imports. NO SQLAlchemy imports.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

import frontmatter
import xxhash

_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


class BodyShape(StrEnum):
    compiled_truth_only = "compiled_truth_only"
    timeline_only = "timeline_only"
    mixed = "mixed"
    empty = "empty"


@dataclass
class ParsedPage:
    frontmatter: dict
    compiled_truth: str
    timeline: str
    body_shape: BodyShape
    content_hash: str  # xxhash64 hexdigest of raw_bytes


class VaultParseError(ValueError):
    """Raised when vault file structure is invalid (e.g., multiple separators)."""


class VaultTimelineError(ValueError):
    """Raised when timeline content violates append-only constraint."""


def parse_vault_file(raw_bytes: bytes) -> ParsedPage:
    """Parse raw vault file bytes into structured fields.

    D-01 separator algorithm:
    1. Strip YAML frontmatter block (python-frontmatter handles this).
    2. Scan body for first standalone ``---`` line.
    3. Content above = compiled_truth, content below = timeline.
    4. At most one separator per page; raise VaultParseError on second.
    5. No separator → whole body = compiled_truth, timeline = "".

    PITFALL 8: ``_resolved_links`` is a reserved system key. Strip it from
    user-provided frontmatter before returning so user cannot inject stale or
    arbitrary resolved-link data into the system.
    """
    content_hash = xxhash.xxh64(raw_bytes).hexdigest()
    post = frontmatter.loads(raw_bytes.decode("utf-8", errors="replace"))
    fm: dict = dict(post.metadata)

    # Pitfall 8: strip reserved _resolved_links key from user frontmatter
    fm.pop("_resolved_links", None)

    body: str = post.content  # body WITHOUT frontmatter block

    # D-01: scan for first standalone --- separator
    lines = body.split("\n")
    sep_idx = None
    for i, line in enumerate(lines):
        if line.strip() == "---":
            if sep_idx is not None:
                raise VaultParseError(
                    "Multiple compiled-truth/timeline separators found "
                    "(at most one --- separator is allowed per page)"
                )
            sep_idx = i

    if sep_idx is None:
        compiled_truth = body
        timeline = ""
        if body.strip():
            body_shape = BodyShape.compiled_truth_only
        else:
            body_shape = BodyShape.empty
    else:
        compiled_truth = "\n".join(lines[:sep_idx]).rstrip()
        timeline = "\n".join(lines[sep_idx + 1 :]).lstrip()
        if compiled_truth and timeline:
            body_shape = BodyShape.mixed
        elif timeline:
            body_shape = BodyShape.timeline_only
        else:
            body_shape = BodyShape.compiled_truth_only

    return ParsedPage(
        frontmatter=fm,
        compiled_truth=compiled_truth,
        timeline=timeline,
        body_shape=body_shape,
        content_hash=content_hash,
    )


def assert_timeline_append_only(
    existing_timeline: str, submitted_timeline: str
) -> None:
    """Assert that submitted_timeline is an append-only extension of existing_timeline.

    D-02: Raises VaultTimelineError if any existing timeline line is edited,
    deleted, or reordered. Only new entries appended at the end are allowed.
    """
    # Normalise: keep all non-empty lines, preserve order
    existing_lines = [ln for ln in existing_timeline.splitlines() if ln.strip()]
    submitted_lines = [ln for ln in submitted_timeline.splitlines() if ln.strip()]

    # Append-only: all existing lines must appear at the start of submitted lines
    if submitted_lines[: len(existing_lines)] != existing_lines:
        raise VaultTimelineError(
            "Timeline is append-only; existing entries cannot be edited, "
            "deleted, or reordered."
        )


def extract_wikilinks(content: str) -> list[dict]:
    """Extract all [[wikilink]] patterns from content.

    Returns a list of dicts with keys:
      - raw: the full [[...]] match string
      - target_text: the link target (text before | in [[target|display]])
      - namespace: "shared" if target_text starts with "shared/", else "private"

    D-09: Uses simple regex (backslash-backslash-bracket) pattern — no markdown-it plugin needed.
    The regex matches [[...]] with any content inside that does not contain ].
    """
    results = []
    for match in _WIKILINK_RE.finditer(content):
        raw = match.group(0)
        inner = match.group(1)
        # Split on "|" for display alias; everything before "|" is the target
        target_text = inner.split("|")[0].strip()
        namespace = "shared" if target_text.startswith("shared/") else "private"
        results.append(
            {
                "raw": raw,
                "target_text": target_text,
                "namespace": namespace,
            }
        )
    return results
