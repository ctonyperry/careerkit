from test_coverage import make_spine, make_unit

from careerkit.coverage import assess_jd, assess_requirement, career_span_years
from careerkit.jd import ParsedJD, Requirement
from careerkit.models import DeclinedRecord
from careerkit.strategy import strategy_notes, tenure_findings


def _jd(requirements: list[Requirement]) -> ParsedJD:
    return ParsedJD(
        source="x",
        title_to_mirror="T",
        role_family="f",
        seniority="s",
        requirements=requirements,
    )


def _declined(*skills: str) -> DeclinedRecord:
    return DeclinedRecord(text="confirmed not done", skills=list(skills))


# --- credential -------------------------------------------------------------


def test_credential_hard_gate_when_no_equivalent_language() -> None:
    req = Requirement(
        id="degree",
        text="Bachelor's degree in Computer Science",
        skills=["front-end"],
        weight="required",
        kind="credential",
    )
    units = [make_unit("u1", ["front-end"]), make_unit("u2", ["front-end"])]
    coverages = assess_jd(_jd([req]), units, make_spine())
    notes = strategy_notes(coverages)
    assert len(notes) == 1
    note = notes[0]
    assert note.reason == "credential"
    assert note.hard_gate is True
    assert note.compensating_unit_ids == ["u1", "u2"]
    assert "poor fit" in note.detail


def test_credential_boilerplate_when_or_equivalent_present() -> None:
    req = Requirement(
        id="degree",
        text="BS in Computer Science or equivalent experience",
        skills=["front-end"],
        weight="required",
        kind="credential",
    )
    units = [make_unit("u1", ["front-end"])]
    coverages = assess_jd(_jd([req]), units, make_spine())
    note = strategy_notes(coverages)[0]
    assert note.hard_gate is False
    assert "boilerplate" in note.detail
    assert "u1" in note.detail


def test_capability_requirement_yields_no_strategy_note() -> None:
    req = Requirement(id="r", text="Owns SSO", skills=["sso"], weight="required")
    coverages = assess_jd(_jd([req]), [], make_spine())
    assert strategy_notes(coverages) == []


# --- declined ---------------------------------------------------------------


def test_declined_skill_produces_a_strategy_note_with_compensating_units() -> None:
    req = Requirement(
        id="r",
        text="Owns provisioning and front-end",
        skills=["scim", "front-end"],
        weight="required",
    )
    units = [make_unit("u1", ["front-end"]), make_unit("u2", ["front-end"])]
    coverages = assess_jd(_jd([req]), units, make_spine(), [_declined("scim")])
    notes = strategy_notes(coverages)
    assert len(notes) == 1
    note = notes[0]
    assert note.reason == "declined"
    assert note.hard_gate is False  # front-end evidence compensates
    assert note.compensating_unit_ids == ["u1", "u2"]
    assert "scim" in note.detail


def test_fully_declined_requirement_is_a_hard_no_workaround() -> None:
    req = Requirement(
        id="r", text="Runs the data center", skills=["infrastructure"], weight="required"
    )
    coverages = assess_jd(_jd([req]), [], make_spine(), [_declined("infrastructure")])
    note = strategy_notes(coverages)[0]
    assert note.hard_gate is True
    assert "poor fit" in note.detail


# --- tenure -----------------------------------------------------------------


def test_tenure_math_is_computed_from_the_spine() -> None:
    # make_spine: earliest start 1999, latest end 2026 -> 27 years.
    assert career_span_years(make_spine()) == 27
    req = Requirement(
        id="tenure",
        text="8+ years of professional experience",
        skills=[],
        weight="required",
        kind="tenure",
    )
    coverages = assess_jd(_jd([req]), [], make_spine())
    findings = tenure_findings(coverages, make_spine())
    assert len(findings) == 1
    f = findings[0]
    assert f.required_years == 8
    assert f.actual_years == 27
    assert f.meets is True
    assert "1999 to 2026 = 27 years" in f.detail


def test_tenure_short_when_span_below_requirement() -> None:
    req = Requirement(
        id="tenure",
        text="40 years of experience",
        skills=[],
        weight="required",
        kind="tenure",
    )
    f = tenure_findings(assess_jd(_jd([req]), [], make_spine()), make_spine())[0]
    assert f.meets is False
    assert "short of" in f.detail


def test_tenure_without_parseable_number_reports_span_only() -> None:
    req = Requirement(
        id="tenure",
        text="Seasoned professional",
        skills=[],
        weight="required",
        kind="tenure",
    )
    f = tenure_findings(assess_jd(_jd([req]), [], make_spine()), make_spine())[0]
    assert f.required_years is None
    assert f.meets is None


def test_non_tenure_requirements_produce_no_findings() -> None:
    req = Requirement(id="r", text="Owns SSO", skills=["sso"], weight="required")
    coverages = assess_jd(_jd([req]), [], make_spine())
    assert tenure_findings(coverages, make_spine()) == []


def test_requirement_kind_defaults_to_capability() -> None:
    assert assess_requirement(
        Requirement(id="r", text="t", skills=["sso"], weight="required"),
        [],
        make_spine(),
    ).requirement.kind == "capability"
