import json

from conftest import SAMPLE_JD
from test_coverage import make_spine, make_unit

from careerkit.dataload import load_parsed_jd
from careerkit.jd import ParsedJD, Requirement
from careerkit.models import DeclinedRecord, EvidenceUnit, Spine
from careerkit.webexport import build_export


def _jd(*reqs: Requirement) -> ParsedJD:
    return ParsedJD(
        source="x",
        title_to_mirror="T",
        role_family="f",
        seniority="s",
        requirements=list(reqs),
    )


def test_wants_ranked_required_then_thinnest_declined_last() -> None:
    reqs = [
        Requirement(id="pref-hit", text="p", skills=["sso"], weight="preferred"),
        Requirement(id="req-miss", text="m", skills=["scim"], weight="required"),
        Requirement(id="req-hit", text="h", skills=["sso"], weight="required"),
        Requirement(id="req-declined", text="d", skills=["python"], weight="required"),
    ]
    units = [make_unit("u1", ["sso"]), make_unit("u2", ["sso"])]  # sso HIT, scim MISS
    declined = [DeclinedRecord(text="no py", skills=["python"])]
    payload = build_export(_jd(*reqs), units, make_spine(), declined)
    order = [w.id for w in payload.wants]
    assert order.index("req-miss") < order.index("req-hit")  # thinnest first
    assert order.index("req-hit") < order.index("pref-hit")  # required before preferred
    assert order[-1] == "req-declined"  # declined settled at the end
    assert payload.wants[order.index("req-declined")].state == "declined"


def test_skill_less_domain_want_is_uncoverable_not_green() -> None:
    # A want with no mappable skill tag (e.g. crypto custody) must not read covered.
    req = Requirement(id="crypto", text="crypto custody", skills=[], weight="preferred")
    payload = build_export(_jd(req), [], make_spine())
    want = payload.wants[0]
    assert want.coverable is False
    assert want.state == "open"


def test_tenure_want_state_reflects_the_math() -> None:
    req = Requirement(
        id="tenure", text="8+ years", skills=[], weight="required", kind="tenure"
    )
    payload = build_export(_jd(req), [], make_spine())
    want = payload.wants[0]
    assert want.tenure is not None
    assert want.state == "covered"  # make_spine spans 1999-2026, meets 8+
    assert want.coverable is True


def test_export_carries_spine_skeleton_and_locked_education(
    spine: Spine, units: list[EvidenceUnit]
) -> None:
    jd = load_parsed_jd(SAMPLE_JD)
    payload = build_export(jd, units, spine)
    assert payload.spine.education_locked is True
    assert spine.education is not None
    assert payload.spine.education_items == spine.education.items
    assert any(r.earlier for r in payload.spine.roles)  # the Earlier: render note
    assert any(r.omit for r in payload.spine.roles)  # the omit render note


def test_export_is_json_serializable_with_no_score(
    spine: Spine, units: list[EvidenceUnit]
) -> None:
    jd = load_parsed_jd(SAMPLE_JD)
    payload = build_export(jd, units, spine)
    blob = payload.model_dump_json()
    data = json.loads(blob)
    assert "wants" in data and "units" in data
    # No percentage/match-score gamification anywhere in the payload.
    assert "percent" not in blob.lower()
    assert "match_score" not in blob.lower()
