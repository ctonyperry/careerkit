"""Deterministic coverage math: JD requirements x evidence units.

Rules (implementation-design.md):
- MISS: no unit carries the tag.
- THIN: every matching unit is weak (MEMORY tier, provisional, or from a role
  outside the recency window), OR only a single unit matches. One piece of
  evidence for a JD-required skill is worth a recovery question.
- HIT: otherwise.
Requirement status is the WORST of its skills' statuses.
Recency is measured against the newest role end in the spine, not the clock,
so results are reproducible.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from careerkit.jd import ParsedJD, Requirement
from careerkit.models import DeclinedRecord, EvidenceUnit, Spine, Status, Tier

RECENCY_WINDOW_YEARS = 10


class CoverageStatus(StrEnum):
    DECLINED = "DECLINED"
    MISS = "MISS"
    THIN = "THIN"
    HIT = "HIT"


# DECLINED is the worst: a skill the user has confirmed he has NOT done should
# dominate its requirement's status so the fit problem surfaces.
_SEVERITY = {
    CoverageStatus.DECLINED: -1,
    CoverageStatus.MISS: 0,
    CoverageStatus.THIN: 1,
    CoverageStatus.HIT: 2,
}


def declined_skill_tags(declined: list[DeclinedRecord] | None) -> frozenset[str]:
    return frozenset(s for rec in (declined or []) for s in rec.skills)


class SkillCoverage(BaseModel):
    skill: str
    status: CoverageStatus
    unit_ids: list[str] = Field(default_factory=list)
    weak_reasons: dict[str, str] = Field(default_factory=dict)


class RequirementCoverage(BaseModel):
    requirement: Requirement
    status: CoverageStatus
    skills: list[SkillCoverage]


def reference_year(spine: Spine) -> int:
    years = [y for r in spine.roles if (y := r.end_year()) is not None]
    if not years:
        raise ValueError("spine has no parseable role end years")
    return max(years)


def earliest_start_year(spine: Spine) -> int:
    years = [y for r in spine.roles if (y := r.start_year()) is not None]
    if not years:
        raise ValueError("spine has no parseable role start years")
    return min(years)


def career_span_years(spine: Spine) -> int:
    """Total career length: earliest role start to latest role end.

    Deterministic tenure proof for `kind: tenure` requirements — the math a
    resume can defend, never a vibes-based 'years of experience' claim.
    """
    return reference_year(spine) - earliest_start_year(spine)


def _weak_reason(unit: EvidenceUnit, spine: Spine, ref_year: int) -> str | None:
    if unit.tier is Tier.MEMORY:
        return "memory-only"
    if unit.status is Status.PROVISIONAL:
        return "provisional"
    if unit.role is not None:
        role = spine.role_by_id(unit.role)
        if role is None:
            return f"unknown role ref: {unit.role}"
        end = role.end_year()
        if end is not None and ref_year - end > RECENCY_WINDOW_YEARS:
            return f"dated ({role.end})"
    return None  # portfolio projects (role: null) count as recent


def assess_skill(
    skill: str,
    units: list[EvidenceUnit],
    spine: Spine,
    declined_skills: frozenset[str] = frozenset(),
) -> SkillCoverage:
    # An explicit decline wins over any accidental evidence: never re-ask, never
    # surface as support.
    if skill in declined_skills:
        return SkillCoverage(skill=skill, status=CoverageStatus.DECLINED)

    matches = [u for u in units if skill in u.skills]
    if not matches:
        return SkillCoverage(skill=skill, status=CoverageStatus.MISS)

    ref_year = reference_year(spine)
    weak_reasons = {
        u.id: reason for u in matches if (reason := _weak_reason(u, spine, ref_year))
    }
    all_weak = len(weak_reasons) == len(matches)
    status = (
        CoverageStatus.THIN if all_weak or len(matches) == 1 else CoverageStatus.HIT
    )
    return SkillCoverage(
        skill=skill,
        status=status,
        unit_ids=[u.id for u in matches],
        weak_reasons=weak_reasons,
    )


def assess_requirement(
    requirement: Requirement,
    units: list[EvidenceUnit],
    spine: Spine,
    declined_skills: frozenset[str] = frozenset(),
) -> RequirementCoverage:
    skills = [assess_skill(s, units, spine, declined_skills) for s in requirement.skills]
    if not skills:
        # Skill-less requirements are the non-capability kinds (a tenure
        # requirement carries no skills). They are never coverage gaps; their
        # real assessment is the strategy note / tenure math in careerkit.strategy.
        return RequirementCoverage(
            requirement=requirement, status=CoverageStatus.HIT, skills=[]
        )
    worst = min(skills, key=lambda s: _SEVERITY[s.status])
    return RequirementCoverage(
        requirement=requirement, status=worst.status, skills=skills
    )


def assess_jd(
    jd: ParsedJD,
    units: list[EvidenceUnit],
    spine: Spine,
    declined: list[DeclinedRecord] | None = None,
) -> list[RequirementCoverage]:
    declined_skills = declined_skill_tags(declined)
    return [
        assess_requirement(r, units, spine, declined_skills) for r in jd.requirements
    ]
