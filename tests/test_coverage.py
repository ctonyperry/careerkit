from careerkit.coverage import (
    CoverageStatus,
    assess_requirement,
    assess_skill,
    declined_skill_tags,
    reference_year,
)
from careerkit.jd import Requirement
from careerkit.models import (
    DeclinedRecord,
    EvidenceUnit,
    Identity,
    Spine,
    SpineRole,
    Status,
    Tier,
)


def make_spine() -> Spine:
    return Spine(
        identity=Identity(
            legal_name="Test Person",
            goes_by="Test",
            resume_header="Test Person",
            email="t@example.com",
            phone="000",
            linkedin="linkedin.com/in/test",
            location="Nowhere",
        ),
        roles=[
            SpineRole(id="old-role", org="OldCo", title="Dev", start="1999", end="2005"),
            SpineRole(id="new-role", org="NewCo", title="Dev", start="2019", end="Jun 2026"),
        ],
    )


def make_unit(
    uid: str,
    skills: list[str],
    role: str | None = "new-role",
    tier: Tier = Tier.PRIMARY,
    status: Status = Status.CONFIRMED,
) -> EvidenceUnit:
    return EvidenceUnit(
        id=uid,
        role=role,
        narrative="Did a specific thing.",
        skills=skills,
        tier=tier,
        status=status,
    )


def test_reference_year_is_max_role_end(spine_units: None = None) -> None:
    assert reference_year(make_spine()) == 2026


def test_no_matching_units_is_miss() -> None:
    cov = assess_skill("scim", [make_unit("u1", ["sso"])], make_spine())
    assert cov.status is CoverageStatus.MISS
    assert cov.unit_ids == []


def test_single_strong_unit_is_thin() -> None:
    cov = assess_skill("sso", [make_unit("u1", ["sso"])], make_spine())
    assert cov.status is CoverageStatus.THIN


def test_two_strong_units_is_hit() -> None:
    units = [make_unit("u1", ["sso"]), make_unit("u2", ["sso"])]
    cov = assess_skill("sso", units, make_spine())
    assert cov.status is CoverageStatus.HIT
    assert set(cov.unit_ids) == {"u1", "u2"}


def test_only_memory_tier_units_is_thin() -> None:
    units = [
        make_unit("u1", ["sso"], tier=Tier.MEMORY, status=Status.PROVISIONAL),
        make_unit("u2", ["sso"], tier=Tier.MEMORY, status=Status.PROVISIONAL),
    ]
    cov = assess_skill("sso", units, make_spine())
    assert cov.status is CoverageStatus.THIN
    assert "u1" in cov.weak_reasons


def test_only_old_role_units_is_thin() -> None:
    # old-role ended 2005; reference year 2026 -> beyond the recency window
    units = [make_unit("u1", ["sso"], role="old-role"), make_unit("u2", ["sso"], role="old-role")]
    cov = assess_skill("sso", units, make_spine())
    assert cov.status is CoverageStatus.THIN


def test_portfolio_unit_counts_as_recent() -> None:
    units = [make_unit("u1", ["tdd"], role=None), make_unit("u2", ["tdd"])]
    cov = assess_skill("tdd", units, make_spine())
    assert cov.status is CoverageStatus.HIT


def test_declined_skill_reports_declined_and_ignores_evidence() -> None:
    declined = frozenset({"scim"})
    # Even with two strong units, an explicit decline wins.
    units = [make_unit("u1", ["scim"]), make_unit("u2", ["scim"])]
    cov = assess_skill("scim", units, make_spine(), declined)
    assert cov.status is CoverageStatus.DECLINED
    assert cov.unit_ids == []


def test_declined_is_the_worst_requirement_status() -> None:
    req = Requirement(
        id="r",
        text="Owns provisioning and SSO",
        skills=["sso", "scim"],
        weight="required",
    )
    units = [make_unit("u1", ["sso"]), make_unit("u2", ["sso"])]  # sso is HIT
    cov = assess_requirement(req, units, make_spine(), frozenset({"scim"}))
    assert cov.status is CoverageStatus.DECLINED
    by_skill = {s.skill: s.status for s in cov.skills}
    assert by_skill == {"sso": CoverageStatus.HIT, "scim": CoverageStatus.DECLINED}


def test_declined_skill_tags_flattens_records() -> None:
    records = [
        DeclinedRecord(text="never ran a data center", skills=["infrastructure"]),
        DeclinedRecord(text="no k8s", skills=["aws", "infrastructure"]),
    ]
    assert declined_skill_tags(records) == frozenset({"infrastructure", "aws"})
    assert declined_skill_tags(None) == frozenset()


def test_requirement_status_is_worst_of_its_skills() -> None:
    req = Requirement(
        id="r1",
        text="Owns identity integrations",
        skills=["sso", "scim"],
        weight="required",
    )
    units = [make_unit("u1", ["sso"]), make_unit("u2", ["sso"])]
    cov = assess_requirement(req, units, make_spine())
    assert cov.status is CoverageStatus.MISS  # scim has nothing
    by_skill = {s.skill: s.status for s in cov.skills}
    assert by_skill == {"sso": CoverageStatus.HIT, "scim": CoverageStatus.MISS}
