from test_coverage import make_spine, make_unit

from careerkit.coverage import assess_jd
from careerkit.jd import ParsedJD, Requirement
from careerkit.models import DeclinedRecord
from careerkit.questions import generate_questions
from careerkit.report import render_gap_report
from careerkit.strategy import strategy_notes, tenure_findings


def _jd(requirements: list[Requirement]) -> ParsedJD:
    return ParsedJD(
        source="x",
        title_to_mirror="T",
        role_family="f",
        seniority="s",
        requirements=requirements,
    )


def test_report_renders_credential_note_and_tenure_math() -> None:
    reqs = [
        Requirement(
            id="degree",
            text="BS in Computer Science",
            skills=["front-end"],
            weight="required",
            kind="credential",
        ),
        Requirement(
            id="tenure",
            text="8+ years of experience",
            skills=[],
            weight="required",
            kind="tenure",
        ),
    ]
    spine = make_spine()
    units = [make_unit("u1", ["front-end"]), make_unit("u2", ["front-end"])]
    coverages = assess_jd(_jd(reqs), units, spine)
    report = render_gap_report(
        _jd(reqs),
        coverages,
        generate_questions(coverages),
        strategy_notes(coverages),
        tenure_findings(coverages, spine),
    )
    assert "## Tenure" in report
    assert "Requires 8+ years; spine shows 1999 to 2026 = 27 years" in report
    assert "## Strategy notes" in report
    assert "BS in Computer Science (credential, hard gate)" in report
    assert "—" not in report  # house style: no em dashes


def test_report_renders_declined_rows_and_notes() -> None:
    req = Requirement(
        id="r",
        text="Owns provisioning and front-end",
        skills=["scim", "front-end"],
        weight="required",
    )
    spine = make_spine()
    units = [make_unit("u1", ["front-end"]), make_unit("u2", ["front-end"])]
    declined = [DeclinedRecord(text="no scim", skills=["scim"])]
    coverages = assess_jd(_jd([req]), units, spine, declined)
    report = render_gap_report(
        _jd([req]),
        coverages,
        generate_questions(coverages),
        strategy_notes(coverages),
        tenure_findings(coverages, spine),
    )
    assert "scim: DECLINED" in report
    assert "(declined, compensable)" in report
    assert "—" not in report
