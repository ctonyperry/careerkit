"""Deterministic evidence selection and ranking for a resume draft.

The LLM writer sees ONLY what this module selects. That constraint is
load-bearing: in the v1 failure the writer saw the whole corpus and wandered
into impressive-but-irrelevant material (session-learnings step 1). Here the
writer never ranks (it ranks by fluency); it receives a fixed, ordered,
capped set of units and writes only those.

Ranking, in strict priority order:
  1. relevance to the JD's skills (required weighted over preferred),
  2. target affinity (is this unit about the employer's own product?),
  3. evidence strength (tier, then confirmed over provisional),
  4. recency (role end year; portfolio projects count as current).

Units with zero JD relevance are excluded outright. Caps come from the length
budget, applied per section (a spine role, or "projects") and overall. Units
cut by a cap are reported in `dropped`, never silently discarded.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from careerkit.coverage import reference_year
from careerkit.jd import ParsedJD
from careerkit.models import EvidenceUnit, Spine, Status, Tier

PROJECTS_SECTION = "projects"

_REQUIREMENT_WEIGHT = {"required": 2, "preferred": 1}
_TIER_SCORE = {Tier.PRIMARY: 3, Tier.DOC: 2, Tier.MEMORY: 1}

# Words that identify no company on their own.
_GENERIC_COMPANY_TOKENS = frozenset(
    ["app", "inc", "corp", "corporation", "labs", "group", "company", "holdings",
     "technologies", "systems", "solutions", "software", "services", "the", "and", "via"]
)


def target_affinity(unit: EvidenceUnit, company: str | None) -> int:
    """1 when a unit is about the target company's own product.

    Relevance is skill-tag overlap, and tags cannot express "this evidence is
    about the employer's product". For an Okta application the ranker cut the
    unit describing hands-on work inside customer Okta orgs, because its tags
    duplicated higher-ranked units (session-learnings, round 2, finding 4).

    Deliberately a tiebreaker below relevance, not a bonus added to it: a unit
    that mentions the company but does not answer the JD must never leapfrog
    one that does.
    """
    if not company:
        return 0
    tokens = [
        t
        for t in re.findall(r"[A-Za-z][A-Za-z0-9']+", company)
        if len(t) >= 4 and t.lower() not in _GENERIC_COMPANY_TOKENS
    ]
    if not tokens:
        return 0
    pattern = re.compile(r"\b(?:" + "|".join(re.escape(t) for t in tokens) + r")\b", re.I)
    haystack = " ".join([unit.id, unit.narrative, *unit.render_notes])
    return 1 if pattern.search(haystack) else 0


class LengthBudget(BaseModel):
    name: str
    max_total_units: int
    max_per_section: int


# Calibrated against examples/figma-resume-FINAL: a dense one-page senior resume
# runs ~7-8 units, LinkedIn carrying the most. Two-page roughly doubles headroom.
ONE_PAGE = LengthBudget(name="one-page", max_total_units=10, max_per_section=5)
TWO_PAGE = LengthBudget(name="two-page", max_total_units=16, max_per_section=7)
BUDGETS: dict[str, LengthBudget] = {b.name: b for b in (ONE_PAGE, TWO_PAGE)}


class RankedUnit(BaseModel):
    unit_id: str
    section: str  # spine role id, or PROJECTS_SECTION
    relevance: int
    strength: int
    recency: int
    provisional: bool  # feeds the draft watermark
    target_affinity: int = 0  # 1 when the unit is about the employer's product


class ResumeSelection(BaseModel):
    length: str
    selected: list[RankedUnit] = Field(default_factory=list)  # render order
    dropped: list[RankedUnit] = Field(default_factory=list)  # relevant, cut by caps
    withheld_unit_ids: list[str] = Field(default_factory=list)  # unusable: do_not_print
    has_provisional: bool = False


def jd_skill_weights(jd: ParsedJD) -> dict[str, int]:
    """Each JD skill mapped to its strongest requirement weight."""
    weights: dict[str, int] = {}
    for req in jd.requirements:
        w = _REQUIREMENT_WEIGHT[req.weight]
        for skill in req.skills:
            weights[skill] = max(weights.get(skill, 0), w)
    return weights


def relevance(unit: EvidenceUnit, weights: dict[str, int]) -> int:
    return sum(w for skill, w in weights.items() if skill in unit.skills)


def strength(unit: EvidenceUnit) -> int:
    return _TIER_SCORE[unit.tier] + (1 if unit.status is Status.CONFIRMED else 0)


def is_withheld(unit: EvidenceUnit) -> bool:
    """True when a unit cannot be rendered at all, because the strings it is
    forbidden to print are its own substance.

    A do_not_print entry usually protects a detail the surrounding unit can
    survive without (the doubted $10M figure sits in a metric, not the
    McDonald's narrative). But when the protected phrase IS the narrative, as
    with an artifact Tony is not ready to share, selecting the unit spends a
    slot the writer can never use and dangles it in front of them anyway.
    """
    return any(p.lower() in unit.narrative.lower() for p in unit.do_not_print if p.strip())


def _section_of(unit: EvidenceUnit) -> str:
    return unit.role if unit.role is not None else PROJECTS_SECTION


def _recency(unit: EvidenceUnit, spine: Spine, ref_year: int) -> int:
    if unit.role is None:
        return ref_year  # portfolio projects are current, like in coverage
    role = spine.role_by_id(unit.role)
    if role is None:
        return 0
    return role.end_year() or 0


def _section_order_key(section: str, spine: Spine) -> tuple[int, int]:
    """Experience roles newest-first, then the projects section."""
    if section == PROJECTS_SECTION:
        return (1, 0)
    role = spine.role_by_id(section)
    end = (role.end_year() if role else 0) or 0
    return (0, -end)


def select_units(
    jd: ParsedJD,
    units: list[EvidenceUnit],
    spine: Spine,
    budget: LengthBudget,
) -> ResumeSelection:
    weights = jd_skill_weights(jd)
    ref_year = reference_year(spine)

    ranked = [
        RankedUnit(
            unit_id=u.id,
            section=_section_of(u),
            relevance=rel,
            strength=strength(u),
            recency=_recency(u, spine, ref_year),
            provisional=u.status is Status.PROVISIONAL,
            target_affinity=target_affinity(u, jd.company),
        )
        for u in units
        if (rel := relevance(u, weights)) > 0 and not is_withheld(u)
    ]
    # Best first; unit_id ascending breaks ties for a stable, reproducible order.
    # Target affinity sits directly below relevance: among units that answer the
    # JD equally well, the one about the employer's own product wins.
    ranked.sort(
        key=lambda r: (-r.relevance, -r.target_affinity, -r.strength, -r.recency, r.unit_id)
    )

    admitted: list[RankedUnit] = []
    dropped: list[RankedUnit] = []
    per_section: dict[str, int] = {}
    for r in ranked:
        full = len(admitted) >= budget.max_total_units
        section_full = per_section.get(r.section, 0) >= budget.max_per_section
        if full or section_full:
            dropped.append(r)
        else:
            admitted.append(r)
            per_section[r.section] = per_section.get(r.section, 0) + 1

    admitted.sort(
        key=lambda r: (
            _section_order_key(r.section, spine),
            -r.relevance,
            -r.strength,
            -r.recency,
            r.unit_id,
        )
    )
    return ResumeSelection(
        length=budget.name,
        withheld_unit_ids=[
            u.id for u in units if relevance(u, weights) > 0 and is_withheld(u)
        ],
        selected=admitted,
        dropped=dropped,
        has_provisional=any(r.provisional for r in admitted),
    )
