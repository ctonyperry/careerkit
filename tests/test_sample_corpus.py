"""The public contract, exercised end to end on the fictional sample corpus.

Every behaviour here was first asserted against one real person's record in
the historical tests. Those still run when that record is present. These run
everywhere, on a corpus that ships with the repo, and they are the tests a
second person's corpus is expected to keep passing too: nothing here names a
unit that only the sample has except through the fixtures below.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from careerkit.brief import RenderKnobs, build_brief, render_brief
from careerkit.coverage import CoverageStatus, assess_jd
from careerkit.dataload import load_declined, load_parsed_jd, load_spine, load_units
from careerkit.finalize import finalization_gate
from careerkit.jd import ParsedJD, Requirement
from careerkit.models import Status
from careerkit.paths import SAMPLE_CORPUS
from careerkit.questions import generate_questions
from careerkit.strategy import strategy_notes, tenure_findings
from careerkit.webexport import build_export

DATA = SAMPLE_CORPUS / "data"
JD = SAMPLE_CORPUS / "jd" / "halcyon-solutions-engineer-parsed.json"


@pytest.fixture(scope="module")
def sample():
    spine = load_spine(DATA / "spine.yaml")
    units = load_units(DATA / "evidence")
    declined = load_declined(DATA / "declined.yaml")
    jd = load_parsed_jd(JD)
    return spine, units, declined, jd


def _status(coverages, skill: str) -> CoverageStatus:
    return {s.skill: s.status for cov in coverages for s in cov.skills}[skill]


def test_sample_corpus_loads_and_every_tag_is_canonical(sample, aliases) -> None:
    spine, units, declined, _ = sample
    assert spine.identity.resume_header == "Morgan Vale"
    assert {r.id for r in spine.roles} >= {"lantern", "brightline", "northwind"}
    for unit in units:
        for skill in unit.skills:
            assert skill in aliases.canonical_tags, f"{unit.id}: unknown tag {skill}"
    assert declined


def test_superseded_unit_is_gone_but_its_file_remains(sample) -> None:
    _, units, _, _ = sample
    ids = {u.id for u in units}
    assert "lantern-reporting" in ids
    assert "lantern-reporting-old" not in ids
    assert (DATA / "evidence" / "lantern-reporting-old.yaml").exists()


def test_gap_report_finds_the_hits_the_decline_and_the_credential(sample) -> None:
    spine, units, declined, jd = sample
    coverages = assess_jd(jd, units, spine, declined)
    assert _status(coverages, "sso") is CoverageStatus.HIT
    assert _status(coverages, "scim") is CoverageStatus.HIT
    assert _status(coverages, "infrastructure") is CoverageStatus.DECLINED
    notes = strategy_notes(coverages)
    reasons = {n.reason for n in notes}
    assert reasons == {"credential", "declined"}
    # "or equivalent experience" makes the degree boilerplate, not a gate.
    assert not next(n for n in notes if n.reason == "credential").hard_gate
    # Declined skills never come back as recovery questions.
    asked = {s for q in generate_questions(coverages) for s in q.skills}
    assert "infrastructure" not in asked


def test_tenure_is_computed_from_the_spine_not_typed(sample) -> None:
    spine, units, declined, jd = sample
    (finding,) = tenure_findings(assess_jd(jd, units, spine, declined), spine)
    assert finding.required_years == 5
    assert finding.actual_years == 17  # 2009 to 2026, from the spine
    assert finding.meets is True


def test_brief_compresses_omits_and_keeps_continuity(sample) -> None:
    spine, units, _, jd = sample
    brief = build_brief(jd, units, spine, RenderKnobs())
    shown = {r.role_id for r in brief.experience}
    assert "helpdesk-early" not in shown  # "Earlier:" render note
    assert any("Cascade Credit Union" in e for e in brief.earlier)
    assert "staffing-contract" not in shown  # "Omit from resumes"
    assert not any("staffing" in e.lower() for e in brief.earlier)
    assert brief.education == spine.education.items  # transcribed, never composed


def test_a_role_with_nothing_relevant_still_shows_as_continuity(sample) -> None:
    """A gap on the page is a screening filter; a role with no JD-relevant
    unit still renders, carrying one continuity line, so the timeline holds."""
    spine, units, _, _ = sample
    jd = ParsedJD(source="x", title_to_mirror="T", role_family="f", seniority="s",
                  requirements=[Requirement(id="r", text="SSO only", skills=["sso"],
                                            weight="required")])
    brief = build_brief(jd, units, spine, RenderKnobs())
    northwind = next(r for r in brief.experience if r.role_id == "northwind")
    assert northwind.continuity_only is True
    assert len(northwind.units) == 1 and northwind.units[0].continuity is True


def test_earliest_year_shown_drops_older_roles(sample) -> None:
    spine, units, _, jd = sample
    brief = build_brief(jd, units, spine, RenderKnobs(earliest_year_shown=2017))
    shown = {r.role_id for r in brief.experience}
    assert "northwind" not in shown  # ended 2016
    assert "lantern" in shown


def test_a_provisional_unit_makes_the_brief_a_draft_and_blocks_finalize(sample) -> None:
    spine, units, _, jd = sample
    provisional = [u for u in units if u.status is Status.PROVISIONAL]
    assert provisional, "the sample corpus must carry a provisional unit"
    brief = build_brief(jd, units, spine, RenderKnobs())
    assert brief.is_draft is True
    assert "DRAFT" in render_brief(brief)
    report = finalization_gate(jd, units, spine, RenderKnobs(), "- clean draft")
    assert report.is_ready is False
    assert any(g.kind == "provisional-unit" for g in report.gates)


def test_export_carries_the_skeleton(sample) -> None:
    spine, units, _, jd = sample
    payload = build_export(jd, units, spine)
    assert payload.spine.education_locked is True
    assert any(r.earlier for r in payload.spine.roles)
    assert any(r.omit for r in payload.spine.roles)


def test_sample_run_directory_is_complete() -> None:
    run = SAMPLE_CORPUS.parent / "sample-run"
    for name in ("manifest.yaml", "resume.md", "claim-sheet.md", "jd-parsed.json"):
        assert (run / name).exists(), name
    assert Path(JD).read_bytes() == (run / "jd-parsed.json").read_bytes()
