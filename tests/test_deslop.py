from test_coverage import make_spine

from careerkit.deslop import deslop_text
from careerkit.linter import lint_resume


def test_em_dash_becomes_a_comma() -> None:
    cleaned, changes = deslop_text("Owned delivery — end to end.")
    assert cleaned == "Owned delivery, end to end."
    assert any("em dash" in c for c in changes)


def test_em_dash_separator_in_a_label_line() -> None:
    cleaned, _ = deslop_text("Certificate — Portland Community College, 2012")
    assert cleaned == "Certificate, Portland Community College, 2012"


def test_pass_never_merges_lines() -> None:
    # An em dash at a line edge must not eat the newline.
    cleaned, _ = deslop_text("first line —\nsecond line")
    assert "\n" in cleaned
    assert cleaned.splitlines()[0].rstrip() == "first line,"


def test_clean_text_is_unchanged() -> None:
    text = "Delivered a $10M program, end to end."
    cleaned, changes = deslop_text(text)
    assert cleaned == text
    assert changes == []


def test_idempotent() -> None:
    text = "A — B  —  C ,  and D ."
    once, _ = deslop_text(text)
    twice, changes = deslop_text(once)
    assert twice == once
    assert changes == []


def test_deslop_clears_the_em_dash_lint_blocker() -> None:
    spine = make_spine()
    dirty = "- Owned delivery — end to end."
    assert any(f.rule == "em-dash" for f in lint_resume(dirty, spine, []))
    cleaned, _ = deslop_text(dirty)
    assert not any(f.rule == "em-dash" for f in lint_resume(cleaned, spine, []))
