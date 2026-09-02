from conftest import SAMPLE_JD
from test_coverage import make_spine, make_unit

from careerkit.brief import RenderKnobs, build_brief, render_brief
from careerkit.dataload import load_parsed_jd
from careerkit.jd import ParsedJD, Requirement
from careerkit.models import EvidenceUnit, Spine


def _sample(spine: Spine, units: list[EvidenceUnit], **kw: object) -> object:
    jd = load_parsed_jd(SAMPLE_JD)
    return build_brief(jd, units, spine, RenderKnobs(**kw))  # type: ignore[arg-type]


def test_education_is_verbatim_from_spine(spine: Spine, units: list[EvidenceUnit]) -> None:
    brief = _sample(spine, units)
    assert spine.education is not None
    assert brief.education == spine.education.items  # transcribed, never composed


def test_education_omitted_knob_empties_it(spine: Spine, units: list[EvidenceUnit]) -> None:
    brief = _sample(spine, units, education_placement="omitted")
    assert brief.education == []










def test_draft_watermark_when_a_provisional_unit_is_selected(
    spine: Spine, units: list[EvidenceUnit]
) -> None:
    # enablement is carried by both confirmed and provisional units in the
    # real corpus; naming them here would rot as the corpus grows. The
    # is_draft assertion below is what guards the premise.
    jd = ParsedJD(
        source="x",
        title_to_mirror="T",
        role_family="f",
        seniority="s",
        requirements=[Requirement(id="r", text="t", skills=["enablement"], weight="required")],
    )
    brief = build_brief(jd, units, spine, RenderKnobs())
    assert brief.is_draft is True
    md = render_brief(brief)
    assert "DRAFT" in md




def test_dropped_target_affinity_units_are_surfaced_separately() -> None:
    """A unit about the employer's own product can rank below the cut on skill
    relevance alone. Promoting it would let weak evidence beat strong, so the
    brief names it instead, pointed at the cover letter."""
    jd = ParsedJD(
        source="jd.md",
        title_to_mirror="Senior Technical Consultant",
        role_family="consulting",
        seniority="senior",
        company="Okta",
        requirements=[
            Requirement(id="sso", text="SSO", skills=["sso"], weight="required"),
            Requirement(id="scim", text="SCIM", skills=["scim"], weight="required"),
        ],
    )
    # Fill the section cap (5 per role) with strictly more relevant units, so
    # the affinity unit is the one the budget cuts.
    strong = [make_unit(f"a-strong-{i}", ["sso", "scim"]) for i in range(5)]
    about_target = make_unit("z-okta", ["sso"])  # lower relevance, same section
    about_target.narrative = "Worked inside customer Okta orgs on claim expressions."

    brief = build_brief(jd, [*strong, about_target], make_spine(), RenderKnobs())
    assert "z-okta" in brief.dropped_unit_ids
    assert brief.dropped_target_affinity_ids == ["z-okta"]

    rendered = render_brief(brief)
    assert "Cut, but about the target company" in rendered
