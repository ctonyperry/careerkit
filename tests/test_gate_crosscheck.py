"""Regression tests: every check must catch the bug that motivated it.

The `buggy-run` fixture is not synthetic. It is a trimmed copy of what the
2026-08-24 chat session actually exported to Google Drive before review.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import crosscheck  # noqa: E402
from conftest import DATA_DIR  # noqa: E402

SPINE = DATA_DIR / "spine.yaml"
BUGGY = ROOT / "tests" / "gate_fixtures" / "buggy-run"
# The shipped run lives in the private runs directory, wherever that is.
_RUNS = Path(os.environ.get("CAREERKIT_RUNS", ROOT / "runs"))
CASHAPP = _RUNS / "runs" / "2026-08-24-cashapp-sr-solutions-engineer"

pytestmark = pytest.mark.private_corpus


@pytest.fixture(scope="module")
def buggy() -> list[crosscheck.Finding]:
    return crosscheck.run_checks(BUGGY, SPINE)


def _rules(findings: list[crosscheck.Finding]) -> set[str]:
    return {f.rule for f in findings}


def test_catches_completed_role_rendered_as_ongoing(buggy: list) -> None:
    hits = [f for f in buggy if f.rule == "spine-tense"]
    assert hits, "Apple ended Jun 2026 in the spine; '2025 - Present' must block"
    assert all(f.severity == crosscheck.BLOCK for f in hits)
    assert any("apple" in f.excerpt.lower() for f in hits)


def test_catches_date_drift_between_resume_and_cover_letter(buggy: list) -> None:
    hits = [f for f in buggy if f.rule == "cross-doc-drift"]
    assert hits, "resume says Apple is ongoing while the letter says it wrapped up"
    assert all(f.severity == crosscheck.BLOCK for f in hits)


def test_catches_cross_jd_contamination(buggy: list) -> None:
    """The Okta phrase 'all-in on' asserting something about Block, in a Cash
    App letter whose JD never mentions AI."""
    hits = [f for f in buggy if f.rule == "jd-trace"]
    assert hits
    assert any(f.severity == crosscheck.BLOCK for f in hits), (
        "a hint-pattern claim about the company must BLOCK, not merely warn"
    )
    assert any("all-in on ai" in f.excerpt.lower() for f in hits)


def test_catches_missing_claim_attribution(buggy: list) -> None:
    assert "claim-sheet-empty" in _rules(buggy)


def test_buggy_run_fails_the_gate(buggy: list) -> None:
    assert any(f.severity == crosscheck.BLOCK for f in buggy)


@pytest.mark.skipif(not CASHAPP.exists(), reason="set CAREERKIT_RUNS to the private runs directory")
def test_shipped_cashapp_run_has_no_blockers() -> None:
    """The corrected run must pass the deterministic gate.

    Note the known limitation this documents: 'Block builds the same way'
    survives word-overlap because the JD does contain 'building', even though
    the actual assertion (Block builds WITH AI AGENTS) is nowhere in the JD.
    Semantic contamination of that kind is the adversarial eval pass's job,
    not this tool's.
    """
    findings = crosscheck.run_checks(CASHAPP, SPINE)
    blockers = [f for f in findings if f.severity == crosscheck.BLOCK]
    assert not blockers, [f"{f.rule}: {f.excerpt}" for f in blockers]


def test_missing_jd_blocks_rather_than_silently_skipping(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    (run / "resume.md").write_text("- A bullet.\n", encoding="utf-8")
    (run / "manifest.yaml").write_text(
        "company: Nowhere\njd: does/not/exist.md\ndocuments:\n  - resume.md\n",
        encoding="utf-8",
    )
    findings = crosscheck.run_checks(run, SPINE)
    assert "jd-missing" in _rules(findings)
    assert any(f.severity == crosscheck.BLOCK for f in findings)


def test_company_token_matching_is_word_bounded(tmp_path: Path) -> None:
    """'App' must not match 'Apple'/'applied'; 'Block' must not match
    'renewal-blocking'. This bug made the first run of the check unusable."""
    jd = tmp_path / "jd.md"
    jd.write_text("We want a solutions engineer for merchant integrations.", encoding="utf-8")
    docs = {
        "resume.md": (
            "- Turned a renewal-blocking problem into a product improvement.\n"
            "- Built a classic ASP web app at Apple, applied across teams.\n"
        )
    }
    findings = crosscheck.check_jd_trace(
        docs, jd.read_text(encoding="utf-8"), "Cash App (Block)"
    )
    assert not findings, [f.excerpt for f in findings]
