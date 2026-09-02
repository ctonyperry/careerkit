"""Every crosscheck rule, provoked on a run built from the fictional sample.

The rules were each written after a real document shipped the bug. The real
documents stay private; these reproduce the same shapes against Morgan Vale's
record, so the rules are exercised anywhere the repo is cloned.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

from careerkit.paths import REPO_ROOT, SAMPLE_CORPUS

sys.path.insert(0, str(REPO_ROOT / "tools"))

import crosscheck  # noqa: E402

SPINE = SAMPLE_CORPUS / "data" / "spine.yaml"
EVIDENCE = SAMPLE_CORPUS / "data" / "evidence"
CLEAN = REPO_ROOT / "examples" / "sample-run"


def _rules(findings: list[crosscheck.Finding]) -> set[str]:
    return {f.rule for f in findings}


def _blocking(findings: list[crosscheck.Finding]) -> set[str]:
    return {f.rule for f in findings if f.severity == crosscheck.BLOCK}


@pytest.fixture
def buggy(tmp_path: Path) -> Path:
    """The clean sample run, broken the four ways real runs have been broken."""
    run = tmp_path / "run"
    shutil.copytree(CLEAN, run)
    resume = (run / "resume.md").read_text(encoding="utf-8")
    # 1. spine-tense: the spine says Lantern ended Jun 2026; the page says Present.
    resume = resume.replace("Mar 2023 to Jun 2026", "Mar 2023 to Present")
    (run / "resume.md").write_text(resume, encoding="utf-8")
    # 2. cross-doc-drift: the letter dates the same role differently.
    # 3. jd-trace: a claim about the company, in the hint pattern, that the
    #    posting never makes.
    (run / "cover-letter.md").write_text(
        "At Lantern Analytics, 2023 to 2025, I led identity rollouts.\n\n"
        "Your posting says you are all-in on autonomous forklifts, and so am I.\n",
        encoding="utf-8",
    )
    manifest = (run / "manifest.yaml").read_text(encoding="utf-8")
    manifest = manifest.replace("documents:\n  - resume.md\n",
                                "documents:\n  - resume.md\n  - cover-letter.md\n")
    # 4. claim-sheet-empty: the manifest names a claim sheet with no table in it.
    manifest = manifest.replace("jd: examples/sample-corpus/jd/halcyon-solutions-engineer.md",
                                f"jd: {SAMPLE_CORPUS / 'jd' / 'halcyon-solutions-engineer.md'}")
    (run / "manifest.yaml").write_text(manifest, encoding="utf-8")
    (run / "claim-sheet.md").write_text("# Claim sheet\n\nNo table here.\n", encoding="utf-8")
    return run


def test_the_clean_sample_run_has_no_blockers() -> None:
    findings = crosscheck.run_checks(CLEAN, SPINE, EVIDENCE)
    assert not _blocking(findings), [f"{f.rule}: {f.excerpt}" for f in findings]


def test_completed_role_rendered_as_ongoing_blocks(buggy: Path) -> None:
    hits = [f for f in crosscheck.run_checks(buggy, SPINE, EVIDENCE) if f.rule == "spine-tense"]
    assert hits and all(f.severity == crosscheck.BLOCK for f in hits)
    assert any("lantern" in f.excerpt.lower() for f in hits)


def test_date_drift_between_documents_blocks(buggy: Path) -> None:
    assert "cross-doc-drift" in _blocking(crosscheck.run_checks(buggy, SPINE, EVIDENCE))


def test_claim_about_the_company_not_in_the_posting_blocks(buggy: Path) -> None:
    hits = [f for f in crosscheck.run_checks(buggy, SPINE, EVIDENCE) if f.rule == "jd-trace"]
    assert any(f.severity == crosscheck.BLOCK for f in hits)
    assert any("all-in on" in f.excerpt.lower() for f in hits)


def test_claim_sheet_without_a_table_is_reported(buggy: Path) -> None:
    assert "claim-sheet-empty" in _rules(crosscheck.run_checks(buggy, SPINE, EVIDENCE))


def test_dangling_reference_to_a_removed_bullet_blocks(tmp_path: Path) -> None:
    run = tmp_path / "run"
    shutil.copytree(CLEAN, run)
    resume = (run / "resume.md").read_text(encoding="utf-8")
    # Drop the rate-limit bullet; the next one now refers to a rollout that
    # is no longer on the page.
    lines = [ln for ln in resume.splitlines() if not ln.startswith("- Traced a SCIM")]
    lines = [ln.replace("- Answered enterprise security questionnaires",
                        "- After that rollout, answered enterprise security questionnaires")
             for ln in lines]
    (run / "resume.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    findings = crosscheck.run_checks(run, SPINE, EVIDENCE)
    assert "dangling-reference" in _rules(findings)


def test_missing_jd_blocks_rather_than_silently_skipping(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    (run / "resume.md").write_text("- A bullet.\n", encoding="utf-8")
    (run / "manifest.yaml").write_text(
        "company: Nowhere\njd: does/not/exist.md\ndocuments:\n  - resume.md\n",
        encoding="utf-8",
    )
    findings = crosscheck.run_checks(run, SPINE, EVIDENCE)
    assert "jd-missing" in _blocking(findings)


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
    findings = crosscheck.check_jd_trace(docs, jd.read_text(encoding="utf-8"), "Cart App (Block)")
    assert not findings, [f.excerpt for f in findings]
