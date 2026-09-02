import pytest
from conftest import FIXTURES
from test_coverage import make_spine, make_unit

from careerkit.brief import RenderKnobs, build_brief, render_brief
from careerkit.dataload import load_parsed_jd
from careerkit.jd import ParsedJD, Requirement
from careerkit.models import EvidenceUnit, Spine


def _figma(spine: Spine, units: list[EvidenceUnit], **kw: object) -> object:
    jd = load_parsed_jd(FIXTURES / "figma-jd-parsed.json")
    return build_brief(jd, units, spine, RenderKnobs(**kw))  # type: ignore[arg-type]


def test_education_is_verbatim_from_spine(spine: Spine, units: list[EvidenceUnit]) -> None:
    brief = _figma(spine, units)
    assert spine.education is not None
    assert brief.education == spine.education.items  # transcribed, never composed


def test_education_omitted_knob_empties_it(spine: Spine, units: list[EvidenceUnit]) -> None:
    brief = _figma(spine, units, education_placement="omitted")
    assert brief.education == []


@pytest.mark.private_corpus
def test_earlier_roles_compress_via_render_note(
    spine: Spine, units: list[EvidenceUnit]
) -> None:
    brief = _figma(spine, units)
    exp_ids = {r.role_id for r in brief.experience}
    # symantec + microsoft carry the "Earlier:" render_note -> compressed.
    assert "symantec-support" not in exp_ids
    assert "microsoft-qa" not in exp_ids
    assert any("Microsoft" in e for e in brief.earlier)


@pytest.mark.private_corpus
def test_omitted_role_appears_nowhere(spine: Spine, units: list[EvidenceUnit]) -> None:
    brief = _figma(spine, units)
    exp_ids = {r.role_id for r in brief.experience}
    assert "leasing-contract" not in exp_ids
    assert not any("leasing" in e.lower() for e in brief.earlier)


@pytest.mark.private_corpus
def test_ims_appears_as_continuity_even_with_no_jd_relevant_unit(
    spine: Spine, units: list[EvidenceUnit]
) -> None:
    # ims-operations has zero Figma relevance; the role still shows to avoid a
    # 2000-2011 gap, carrying its strongest unit as a single continuity line.
    brief = _figma(spine, units)
    ims = next(r for r in brief.experience if r.role_id == "ims")
    assert ims.continuity_only is True
    assert len(ims.units) == 1
    assert ims.units[0].continuity is True


@pytest.mark.private_corpus
def test_earliest_year_shown_compresses_older_roles(
    spine: Spine, units: list[EvidenceUnit]
) -> None:
    brief = _figma(spine, units, earliest_year_shown=2019)
    exp_ids = {r.role_id for r in brief.experience}
    assert "athenaonline" not in exp_ids  # ended 2018 < 2019
    assert "ims" not in exp_ids  # ended 2011 < 2019
    assert "linkedin-tc" in exp_ids  # ended 2025


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


@pytest.mark.private_corpus
def test_render_includes_verbatim_guard_and_education(
    spine: Spine, units: list[EvidenceUnit]
) -> None:
    md = render_brief(_figma(spine, units))
    assert "TRANSCRIBE VERBATIM" in md
    assert "General Assembly" in md  # a real spine education item, transcribed
    # The brief's own scaffolding (headings/labels) is em-dash-free house style;
    # transcribed unit content may contain em dashes and is the linter's job on
    # the final resume, not the brief's.
    scaffolding = [ln for ln in md.splitlines() if ln.startswith("#") or ln.startswith("- ")]
    assert not any("—" in ln for ln in scaffolding if "render_note" not in ln)


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
