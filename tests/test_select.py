from test_coverage import make_spine, make_unit

from careerkit.jd import ParsedJD, Requirement
from careerkit.models import Status, Tier
from careerkit.select import (
    BUDGETS,
    ONE_PAGE,
    PROJECTS_SECTION,
    LengthBudget,
    relevance,
    select_units,
    strength,
)


def _jd(*requirements: Requirement) -> ParsedJD:
    return ParsedJD(
        source="x",
        title_to_mirror="T",
        role_family="f",
        seniority="s",
        requirements=list(requirements),
    )


def _req(rid: str, skills: list[str], weight: str = "required") -> Requirement:
    return Requirement(id=rid, text=rid, skills=skills, weight=weight)  # type: ignore[arg-type]


def test_irrelevant_units_are_excluded() -> None:
    jd = _jd(_req("r", ["sso"]))
    units = [make_unit("u1", ["sso"]), make_unit("u2", ["python"])]
    sel = select_units(jd, units, make_spine(), ONE_PAGE)
    ids = {r.unit_id for r in sel.selected}
    assert ids == {"u1"}


def test_relevance_weights_required_over_preferred() -> None:
    weights = {"sso": 2, "ux": 1}
    assert relevance(make_unit("u", ["sso"]), weights) == 2
    assert relevance(make_unit("u", ["ux"]), weights) == 1
    assert relevance(make_unit("u", ["sso", "ux"]), weights) == 3


def test_strength_orders_tier_and_status() -> None:
    primary = make_unit("a", ["sso"], tier=Tier.PRIMARY, status=Status.CONFIRMED)
    memory_prov = make_unit("b", ["sso"], tier=Tier.MEMORY, status=Status.PROVISIONAL)
    assert strength(primary) > strength(memory_prov)


def test_ranking_prefers_relevance_then_strength() -> None:
    jd = _jd(_req("r1", ["sso"]), _req("r2", ["scim"], weight="preferred"))
    units = [
        make_unit("low-rel", ["scim"]),  # relevance 1
        make_unit("high-rel", ["sso"]),  # relevance 2
        make_unit("weak-high-rel", ["sso"], tier=Tier.MEMORY, status=Status.PROVISIONAL),
    ]
    sel = select_units(jd, units, make_spine(), ONE_PAGE)
    order = [r.unit_id for r in sel.selected]
    # same section (new-role); high relevance first, strong before weak.
    assert order == ["high-rel", "weak-high-rel", "low-rel"]


def test_per_section_cap_drops_extras_without_silence() -> None:
    budget = LengthBudget(name="tiny", max_total_units=10, max_per_section=2)
    jd = _jd(_req("r", ["sso"]))
    units = [make_unit(f"u{i}", ["sso"]) for i in range(4)]
    sel = select_units(jd, units, make_spine(), budget)
    assert len(sel.selected) == 2
    assert len(sel.dropped) == 2
    assert {r.unit_id for r in sel.selected} | {r.unit_id for r in sel.dropped} == {
        "u0",
        "u1",
        "u2",
        "u3",
    }


def test_total_cap_across_sections() -> None:
    budget = LengthBudget(name="tiny", max_total_units=1, max_per_section=5)
    jd = _jd(_req("r", ["sso"]))
    units = [make_unit("old", ["sso"], role="old-role"), make_unit("new", ["sso"])]
    sel = select_units(jd, units, make_spine(), budget)
    assert [r.unit_id for r in sel.selected] == ["new"]  # newest strength/recency wins
    assert [r.unit_id for r in sel.dropped] == ["old"]


def test_render_order_experience_newest_first_then_projects() -> None:
    jd = _jd(_req("r", ["sso", "tdd"]))
    units = [
        make_unit("old-role-unit", ["sso"], role="old-role"),
        make_unit("new-role-unit", ["sso"], role="new-role"),
        make_unit("project-unit", ["tdd"], role=None),
    ]
    sel = select_units(jd, units, make_spine(), ONE_PAGE)
    order = [r.unit_id for r in sel.selected]
    assert order == ["new-role-unit", "old-role-unit", "project-unit"]
    assert sel.selected[-1].section == PROJECTS_SECTION


def test_has_provisional_flag_drives_watermark() -> None:
    jd = _jd(_req("r", ["sso"]))
    prov = make_unit("p", ["sso"], tier=Tier.MEMORY, status=Status.PROVISIONAL)
    sel = select_units(jd, [prov], make_spine(), ONE_PAGE)
    assert sel.has_provisional is True


def test_budgets_registry_has_presets() -> None:
    assert set(BUDGETS) == {"one-page", "two-page"}


def test_target_affinity_promotes_evidence_about_the_employers_product() -> None:
    """Round-2 finding 4: for an Okta application the ranker cut the unit
    describing hands-on work inside customer Okta orgs, because its skill tags
    duplicated higher-ranked units. Skill tags cannot express "this is about
    the employer's product", so affinity is a separate signal."""
    jd = ParsedJD(
        source="jd.md",
        title_to_mirror="Senior Technical Consultant",
        role_family="consulting",
        seniority="senior",
        company="Okta",
        requirements=[
            Requirement(id="sso", text="SSO", skills=["sso"], weight="required")
        ],
    )
    about_target = make_unit("z-okta-exposure", ["sso"])
    about_target.narrative = "Worked inside customer Okta orgs on claim expressions."
    generic = make_unit("a-generic-sso", ["sso"])

    # Equal relevance and strength; unit_id would otherwise put 'a-generic' first.
    budget = LengthBudget(name="tiny", max_total_units=1, max_per_section=1)
    selection = select_units(jd, [generic, about_target], make_spine(), budget)
    assert [r.unit_id for r in selection.selected] == ["z-okta-exposure"]
    assert selection.selected[0].target_affinity == 1


def test_target_affinity_never_outranks_relevance() -> None:
    """A unit that mentions the company but answers less of the JD must not
    leapfrog one that answers more."""
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
    mentions_target = make_unit("a-mentions", ["sso"])
    mentions_target.narrative = "Some Okta exposure."
    more_relevant = make_unit("b-relevant", ["sso", "scim"])

    budget = LengthBudget(name="tiny", max_total_units=1, max_per_section=1)
    selection = select_units(jd, [mentions_target, more_relevant], make_spine(), budget)
    assert [r.unit_id for r in selection.selected] == ["b-relevant"]


def test_target_affinity_is_off_without_a_company() -> None:
    jd = ParsedJD(
        source="jd.md",
        title_to_mirror="X",
        role_family="y",
        seniority="senior",
        requirements=[
            Requirement(id="sso", text="SSO", skills=["sso"], weight="required")
        ],
    )
    unit = make_unit("u", ["sso"])
    unit.narrative = "Worked inside customer Okta orgs."
    selection = select_units(jd, [unit], make_spine(), ONE_PAGE)
    assert selection.selected[0].target_affinity == 0


def test_units_whose_substance_is_do_not_print_are_never_selected() -> None:
    """An artifact the author is not ready to share should not occupy a slot the
    writer cannot use. A protected detail inside a larger unit is different:
    that unit still selects, and the linter guards the phrase."""
    jd = ParsedJD(
        source="jd.md",
        title_to_mirror="X",
        role_family="y",
        seniority="senior",
        requirements=[
            Requirement(id="sso", text="SSO", skills=["sso"], weight="required")
        ],
    )
    unusable = make_unit("kit", ["sso"])
    unusable.narrative = "UX Telemetry Kit: the npm-published analytics module."
    unusable.do_not_print = ["UX Telemetry Kit"]

    protected_detail = make_unit("rollout", ["sso"])
    protected_detail.narrative = "Ran a company-wide rollout to two million workers."
    protected_detail.do_not_print = ["$10M"]  # a metric, not the narrative

    selection = select_units(jd, [unusable, protected_detail], make_spine(), ONE_PAGE)
    ids = [r.unit_id for r in selection.selected]
    assert "kit" not in ids
    assert "rollout" in ids
    assert selection.withheld_unit_ids == ["kit"]
