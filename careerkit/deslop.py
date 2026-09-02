"""Optional final de-slop pass: deterministic, safe, mechanical rewrites.

Tony's model (this session): rather than BLOCK the writer on mechanical style
nits, run a de-slop pass as an optional last step that just fixes them, like a
formatter. This module only does transformations that are SAFE to apply blind:
an em dash becomes a comma, stray whitespace collapses. It never rewrites a
claim.

The judgment-heavy slop (invented credentials, unsourced numbers, puffery,
self-rating, atmosphere-poses, defensive framing) is NOT auto-fixable, because
the fix is a rewrite of the underlying claim. That stays with the linter
(reports) and the semantic critique (advises). De-slop cleans; it never edits
meaning.
"""

from __future__ import annotations

import re

EM_DASH = "—"

# Whitespace classes exclude newlines so a pass never merges or reflows lines.
_EM_DASH_RE = re.compile(r"[^\S\n]*—[^\S\n]*")
_SPACE_BEFORE_PUNCT_RE = re.compile(r"[^\S\n]+([,.;:])")
_MULTISPACE_RE = re.compile(r"[^\S\n]{2,}")
_TRAILING_WS_RE = re.compile(r"[^\S\n]+$", re.MULTILINE)


def deslop_text(text: str) -> tuple[str, list[str]]:
    """Return (cleaned_text, human-readable list of changes applied)."""
    changes: list[str] = []

    em = text.count(EM_DASH)
    if em:
        text = _EM_DASH_RE.sub(", ", text)
        changes.append(f"replaced {em} em dash(es) with a comma")

    before = text
    text = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", text)
    if text != before:
        changes.append("removed space(s) before punctuation")

    before = text
    text = _MULTISPACE_RE.sub(" ", text)
    if text != before:
        changes.append("collapsed repeated spaces")

    before = text
    text = _TRAILING_WS_RE.sub("", text)
    if text != before:
        changes.append("trimmed trailing whitespace")

    return text, changes
