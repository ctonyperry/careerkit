"""Deterministic per-kind handling for the requirements you do NOT excavate.

`capability` requirements flow through coverage + recovery questions
(questions.py). The other two kinds are handled here because a memory
interview is the wrong tool for them:

- `credential` ("BS in Computer Science"): a degree cannot be recovered from
  memory. No recovery question. Instead a strategy note: hard gate vs
  boilerplate ("or equivalent experience" detection), plus which adjacent
  evidence units compensate.
- `tenure` ("8+ years"): proven from the spine's dates, never claimed. The
  arithmetic is shown so the resume can defend it.

Declined skills (data/declined.yaml) also surface here as a strategy note:
a skill Tony has confirmed he has NOT done is not a gap to excavate, it is a
fit signal — compensate via adjacent units, or flag the JD as a poor fit.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from careerkit.coverage import (
    CoverageStatus,
    RequirementCoverage,
    career_span_years,
    earliest_start_year,
    reference_year,
)
from careerkit.models import Spine

# "or equivalent (experience)" turns a credential from a hard gate into
# boilerplate the candidate can satisfy with evidence.
_OR_EQUIVALENT_RE = re.compile(r"or equivalent", re.IGNORECASE)
# "8+ years", "10 years", "5 + years".
_YEARS_RE = re.compile(r"(\d+)\s*\+?\s*years?", re.IGNORECASE)


class StrategyNote(BaseModel):
    """A non-excavatable requirement's play: gate assessment + compensating units."""

    requirement_id: str
    requirement_text: str
    reason: Literal["credential", "declined"]
    hard_gate: bool
    compensating_unit_ids: list[str] = Field(default_factory=list)
    detail: str


class TenureFinding(BaseModel):
    """Spine-computed years vs a tenure requirement. `meets` is None if unparsed."""

    requirement_id: str
    requirement_text: str
    required_years: int | None
    actual_years: int
    meets: bool | None
    detail: str


def _compensating_unit_ids(
    cov: RequirementCoverage, *, exclude: CoverageStatus | None = None
) -> list[str]:
    """Adjacent evidence for the requirement's skills, first-seen order."""
    seen: list[str] = []
    for skill in cov.skills:
        if exclude is not None and skill.status is exclude:
            continue
        for uid in skill.unit_ids:
            if uid not in seen:
                seen.append(uid)
    return seen


def _credential_note(cov: RequirementCoverage) -> StrategyNote:
    boilerplate = bool(_OR_EQUIVALENT_RE.search(cov.requirement.text))
    hard_gate = not boilerplate
    units = _compensating_unit_ids(cov)
    if hard_gate:
        if units:
            detail = (
                "Hard credential gate (no 'or equivalent' language). Lead with "
                f"adjacent evidence: {', '.join(units)}. If the gate is strict, "
                "flag the JD as a poor fit."
            )
        else:
            detail = (
                "Hard credential gate (no 'or equivalent' language) and no "
                "adjacent evidence to compensate. Flag the JD as a poor fit."
            )
    else:
        if units:
            detail = (
                "'or equivalent experience' present: this is boilerplate, not a "
                f"gate. Compensate via adjacent evidence: {', '.join(units)}."
            )
        else:
            detail = (
                "'or equivalent experience' present: not a gate, but no adjacent "
                "evidence yet. Excavate compensating experience before applying."
            )
    return StrategyNote(
        requirement_id=cov.requirement.id,
        requirement_text=cov.requirement.text,
        reason="credential",
        hard_gate=hard_gate,
        compensating_unit_ids=units,
        detail=detail,
    )


def _declined_note(
    cov: RequirementCoverage, declined_skills: list[str]
) -> StrategyNote:
    # Compensating evidence comes from the requirement's OTHER (non-declined)
    # skills; the declined skill contributes nothing.
    units = _compensating_unit_ids(cov, exclude=CoverageStatus.DECLINED)
    hard_gate = not units
    tags = ", ".join(declined_skills)
    if units:
        detail = (
            f"Contains skills you've confirmed you have not done: {tags}. "
            f"Compensate via adjacent evidence: {', '.join(units)}."
        )
    else:
        detail = (
            f"Contains skills you've confirmed you have not done: {tags}, and no "
            "adjacent evidence compensates. Flag the JD as a poor fit."
        )
    return StrategyNote(
        requirement_id=cov.requirement.id,
        requirement_text=cov.requirement.text,
        reason="declined",
        hard_gate=hard_gate,
        compensating_unit_ids=units,
        detail=detail,
    )


def _tenure_finding(cov: RequirementCoverage, spine: Spine) -> TenureFinding:
    match = _YEARS_RE.search(cov.requirement.text)
    required = int(match.group(1)) if match else None
    actual = career_span_years(spine)
    math = f"{earliest_start_year(spine)} to {reference_year(spine)} = {actual} years"
    meets = None if required is None else actual >= required
    if required is None:
        detail = (
            f"Tenure requirement; spine shows {math}. No numeric threshold "
            "parsed from the requirement text."
        )
    else:
        verdict = "meets" if meets else "short of"
        detail = f"Requires {required}+ years; spine shows {math} ({verdict})."
    return TenureFinding(
        requirement_id=cov.requirement.id,
        requirement_text=cov.requirement.text,
        required_years=required,
        actual_years=actual,
        meets=meets,
        detail=detail,
    )


def strategy_notes(coverages: list[RequirementCoverage]) -> list[StrategyNote]:
    """Notes for the requirements you play around rather than excavate:

    credential requirements, and any requirement carrying a DECLINED skill.
    """
    notes: list[StrategyNote] = []
    for cov in coverages:
        if cov.requirement.kind == "credential":
            notes.append(_credential_note(cov))
        declined = [
            s.skill for s in cov.skills if s.status is CoverageStatus.DECLINED
        ]
        if declined:
            notes.append(_declined_note(cov, declined))
    return notes


def tenure_findings(
    coverages: list[RequirementCoverage], spine: Spine
) -> list[TenureFinding]:
    return [
        _tenure_finding(cov, spine)
        for cov in coverages
        if cov.requirement.kind == "tenure"
    ]
