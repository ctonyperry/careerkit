from pathlib import Path

import pytest
from conftest import DATA_DIR

from careerkit.dataload import AliasTable, load_declined
from careerkit.models import EvidenceUnit, Spine, Status, Tier


@pytest.mark.private_corpus
def test_spine_loads_all_roles(spine: Spine) -> None:
    ids = {r.id for r in spine.roles}
    assert ids == {
        "symantec-support",
        "microsoft-qa",
        "ims",
        "athenaonline",
        "general-assembly",
        "leasing-contract",
        "linkedin-tc",
        "apple-xapi",
    }
    assert spine.identity.resume_header == "Tony Perry"


@pytest.mark.private_corpus
def test_role_end_years_parse_from_display_strings(spine: Spine) -> None:
    by_id = {r.id: r for r in spine.roles}
    assert by_id["microsoft-qa"].end_year() == 1999  # "Early 1999"
    assert by_id["apple-xapi"].end_year() == 2026  # "Jun 2026"
    assert by_id["ims"].end_year() == 2011


@pytest.mark.private_corpus
def test_all_evidence_units_load(units: list[EvidenceUnit]) -> None:
    # The corpus GROWS with every dogfood run (it is the byproduct), so assert
    # the invariant rather than a count that rots: every unit file on disk
    # parses into a unit.
    on_disk = sorted(p.stem for p in (DATA_DIR / "evidence").glob("*.yaml"))
    assert sorted(u.id for u in units) == on_disk
    assert len(units) >= 22  # migrated 17 + Figma/Ripple excavations

    by_id = {u.id: u for u in units}
    mcd = by_id["linkedin-mcdonalds"]
    assert mcd.tier is Tier.PRIMARY
    assert mcd.status is Status.CONFIRMED
    assert "scim" in mcd.skills
    # Excavated units land provisional + memory-tier (nothing auto-confirms);
    # apple-ux-research is the standing example still awaiting Tony's
    # confirmation. Do not pin units that later get confirmed (see CLAUDE.md:
    # the corpus grows and its verifies get resolved — assert the mechanism,
    # not per-unit status snapshots).
    assert by_id["apple-ux-research"].status is Status.PROVISIONAL


@pytest.mark.private_corpus
def test_link_defaults_to_none_and_accepts_a_url(units: list[EvidenceUnit]) -> None:
    # Optional public-artifact URL (repo, npm). Real data omits it -> None.
    for unit in units:
        assert unit.link is None
    linked = EvidenceUnit(
        id="u-linked",
        role=None,
        narrative="Shipped a thing.",
        skills=["python"],
        tier=Tier.PRIMARY,
        status=Status.CONFIRMED,
        link="https://github.com/ctonyperry/careerkit",
    )
    assert linked.link == "https://github.com/ctonyperry/careerkit"


@pytest.mark.private_corpus
def test_portfolio_units_have_no_role(units: list[EvidenceUnit]) -> None:
    dice = next(u for u in units if u.id == "project-dice-game")
    assert dice.role is None
    assert dice.kind == "portfolio-project"


def test_unit_skills_exist_in_alias_table(
    units: list[EvidenceUnit], aliases: AliasTable
) -> None:
    # Every tag on a unit must be a canonical tag; otherwise coverage
    # silently misses it.
    for unit in units:
        for skill in unit.skills:
            assert skill in aliases.canonical_tags, f"{unit.id}: unknown tag {skill}"


def test_shipped_declined_file_loads() -> None:
    # Grows only by Tony's confirmation (first records: 2026-08-24). Assert
    # the file parses and every record carries the required fields — never
    # pin the count (see CLAUDE.md: the corpus grows).
    records = load_declined(DATA_DIR / "declined.yaml")
    for rec in records:
        assert rec.text
        assert rec.date


def test_missing_declined_file_is_no_declines(tmp_path: Path) -> None:
    assert load_declined(tmp_path / "nope.yaml") == []


def test_declined_records_parse(tmp_path: Path) -> None:
    p = tmp_path / "declined.yaml"
    p.write_text(
        "declined:\n"
        "  - text: Never managed a Kubernetes cluster\n"
        "    skills: [infrastructure]\n"
        "    date: '2026'\n"
        "    note: asked in the Figma run\n",
        encoding="utf-8",
    )
    records = load_declined(p)
    assert len(records) == 1
    assert records[0].skills == ["infrastructure"]
    assert records[0].date == "2026"


def test_alias_resolution(aliases: AliasTable) -> None:
    assert aliases.resolve("single sign-on") == "sso"
    assert aliases.resolve("SAML") == "sso"  # case-insensitive
    assert aliases.resolve("scim") == "scim"  # canonical passes through
    assert aliases.resolve("blockchain") is None
