from test_coverage import make_spine, make_unit

from careerkit.brief import RenderKnobs
from careerkit.finalize import finalization_gate, render_finalization
from careerkit.jd import ParsedJD, Requirement
from careerkit.models import EvidenceUnit, Spine


def _jd(*reqs: Requirement) -> ParsedJD:
    return ParsedJD(
        source="x",
        title_to_mirror="T",
        role_family="f",
        seniority="s",
        requirements=list(reqs),
    )


def _kinds(report: object) -> set[str]:
    return {g.kind for g in report.gates}  # type: ignore[attr-defined]


def test_clean_selection_and_draft_is_ready() -> None:
    jd = _jd(Requirement(id="r", text="t", skills=["sso"], weight="required"))
    units = [make_unit("u1", ["sso"]), make_unit("u2", ["sso"])]  # confirmed, no verify
    report = finalization_gate(jd, units, make_spine(), RenderKnobs(), "- Did SSO work.")
    assert report.is_ready is True
    assert report.gates == []


def test_provisional_unit_is_a_gate(
    spine: Spine, units: list[EvidenceUnit]
) -> None:
    # enablement pulls in at least one provisional unit from the real corpus
    # (which unit it is changes as the corpus grows; the contract does not).
    jd = _jd(Requirement(id="r", text="t", skills=["enablement"], weight="required"))
    report = finalization_gate(jd, units, spine, RenderKnobs(), "- clean draft")
    assert "provisional-unit" in _kinds(report)
    assert report.is_ready is False


def test_open_verifies_from_selected_units_are_gates() -> None:
    # Synthetic, not corpus-coupled: dogfooding resolves real [VERIFY]s over
    # time, so pinning this to a live unit's text rots. The contract is that
    # every open [VERIFY] on a SELECTED unit becomes a gate.
    jd = _jd(Requirement(id="r", text="t", skills=["sso"], weight="required"))
    unit = make_unit("u-verify", ["sso"])
    unit.verify = ["confirm the 250k figure", "name the satisfaction instrument"]
    report = finalization_gate(jd, [unit], make_spine(), RenderKnobs(), "- clean draft")

    verifies = [g for g in report.gates if g.kind == "open-verify"]
    assert {g.detail for g in verifies} == set(unit.verify)
    assert all(g.unit_id == "u-verify" for g in verifies)
    assert report.is_ready is False


def test_lint_blocker_in_draft_gates_finalize() -> None:
    jd = _jd(Requirement(id="r", text="t", skills=["sso"], weight="required"))
    units = [make_unit("u1", ["sso"]), make_unit("u2", ["sso"])]
    report = finalization_gate(
        jd, units, make_spine(), RenderKnobs(), "- Owned delivery — end to end."
    )
    assert "lint-blocker" in _kinds(report)
    assert report.is_ready is False


def test_render_ready_and_not_ready() -> None:
    jd = _jd(Requirement(id="r", text="t", skills=["sso"], weight="required"))
    units = [make_unit("u1", ["sso"]), make_unit("u2", ["sso"])]
    ready = finalization_gate(jd, units, make_spine(), RenderKnobs(), "- clean")
    assert "READY" in render_finalization(ready)

    blocked = finalization_gate(
        jd, units, make_spine(), RenderKnobs(), "- Bad — em dash."
    )
    md = render_finalization(blocked)
    assert "NOT READY" in md
    assert "Lint blockers" in md
