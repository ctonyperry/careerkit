"""Export a single JSON payload for the web UI (the deterministic engine's
contract with the front-end).

The web UI holds NO coverage/ranking logic; Python stays the single source of
deterministic truth (a red-team requirement). This assembles everything a JD's
session needs: the spine skeleton, the ranked wants queue with coverage state,
the evidence units for the document surface, and declined records.

Ranking mirrors ux-brief.md: required before preferred, then thinnest evidence
first, with declined wants settled at the end. No percentage/score anywhere.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from careerkit.coverage import CoverageStatus, RequirementCoverage, assess_jd
from careerkit.dataload import (
    load_declined,
    load_parsed_jd,
    load_spine,
    load_units,
)
from careerkit.jd import ParsedJD
from careerkit.models import DeclinedRecord, EvidenceUnit, Spine
from careerkit.questions import generate_questions
from careerkit.strategy import (
    StrategyNote,
    TenureFinding,
    strategy_notes,
    tenure_findings,
)

_WEIGHT_RANK = {"required": 0, "preferred": 1}
_STATUS_RANK = {
    CoverageStatus.MISS: 0,
    CoverageStatus.THIN: 1,
    CoverageStatus.HIT: 2,
    CoverageStatus.DECLINED: 3,
}


class WantSkill(BaseModel):
    skill: str
    status: str
    unit_ids: list[str] = Field(default_factory=list)


class Want(BaseModel):
    id: str
    text: str  # the JD's own words, quoted; never invented achievement text
    weight: str
    kind: str
    status: str  # HIT | THIN | MISS | DECLINED
    state: str  # open | covered | declined  (lead-attached/deferred are UI-runtime)
    coverable: bool  # false = domain want with no skill tag (honest, not green)
    skills: list[WantSkill] = Field(default_factory=list)
    question: str | None = None
    strategy_notes: list[StrategyNote] = Field(default_factory=list)
    tenure: TenureFinding | None = None


class RoleOut(BaseModel):
    id: str
    org: str
    title: str
    start: str
    end: str
    type: str | None = None
    omit: bool = False
    earlier: bool = False


class SpineOut(BaseModel):
    name: str
    contact: str
    roles: list[RoleOut] = Field(default_factory=list)
    education_items: list[str] = Field(default_factory=list)
    education_locked: bool = True  # never editable in the draft view


class UnitOut(BaseModel):
    id: str
    role: str | None
    headline: str  # informational-register line, templated from the unit
    tier: str
    status: str
    skills: list[str] = Field(default_factory=list)
    metrics: list[dict[str, str]] = Field(default_factory=list)
    link: str | None = None
    render_notes: list[str] = Field(default_factory=list)
    open_verifies: int = 0


class ExportPayload(BaseModel):
    jd_source: str
    title_to_mirror: str
    role_family: str
    seniority: str
    register_choice: str | None = None
    spine: SpineOut
    wants: list[Want] = Field(default_factory=list)
    units: list[UnitOut] = Field(default_factory=list)
    declined: list[DeclinedRecord] = Field(default_factory=list)


def _omitted(render_notes: list[str]) -> bool:
    return any("omit from resume" in n.lower() for n in render_notes)


def _earlier(render_notes: list[str]) -> bool:
    return any("earlier:" in n.lower() for n in render_notes)


def _headline(unit: EvidenceUnit) -> str:
    # Informational register: the first sentence of the narrative, no LLM prose.
    first = unit.narrative.strip().split(". ", 1)[0]
    return first.rstrip(".") + "."


def _want_state(
    cov: RequirementCoverage, coverable: bool, tenure: TenureFinding | None
) -> str:
    if cov.status is CoverageStatus.DECLINED:
        return "declined"
    if tenure is not None:
        return "covered" if tenure.meets else "open"
    if not coverable:
        return "open"  # domain want with no evidence tag: honestly still open
    return "covered" if cov.status is CoverageStatus.HIT else "open"


def build_export(
    jd: ParsedJD,
    units: list[EvidenceUnit],
    spine: Spine,
    declined: list[DeclinedRecord] | None = None,
) -> ExportPayload:
    coverages = assess_jd(jd, units, spine, declined)
    questions = {q.requirement_id: q.text for q in generate_questions(coverages)}
    notes_by_req: dict[str, list[StrategyNote]] = {}
    for note in strategy_notes(coverages):
        notes_by_req.setdefault(note.requirement_id, []).append(note)
    tenure_by_req = {t.requirement_id: t for t in tenure_findings(coverages, spine, units)}

    wants: list[Want] = []
    for cov in coverages:
        req = cov.requirement
        coverable = bool(req.skills) or req.kind == "tenure"
        tenure = tenure_by_req.get(req.id)
        wants.append(
            Want(
                id=req.id,
                text=req.text,
                weight=req.weight,
                kind=req.kind,
                status=cov.status.value,
                state=_want_state(cov, coverable, tenure),
                coverable=coverable,
                skills=[
                    WantSkill(skill=s.skill, status=s.status.value, unit_ids=s.unit_ids)
                    for s in cov.skills
                ],
                question=questions.get(req.id),
                strategy_notes=notes_by_req.get(req.id, []),
                tenure=tenure,
            )
        )

    def rank(w: Want) -> tuple[int, int, int, str]:
        declined = 1 if w.state == "declined" else 0
        weight = _WEIGHT_RANK.get(w.weight, 9)
        severity = _STATUS_RANK.get(CoverageStatus(w.status), 9)
        return (declined, weight, severity, w.id)

    wants.sort(key=rank)

    idn = spine.identity
    contact = f"{idn.location} · {idn.email} · {idn.phone} · {idn.linkedin}"
    roles = [
        RoleOut(
            id=r.id,
            org=r.org,
            title=r.title,
            start=r.start,
            end=r.end,
            type=r.type,
            omit=_omitted(r.render_notes),
            earlier=_earlier(r.render_notes),
        )
        for r in spine.roles
    ]
    spine_out = SpineOut(
        name=idn.resume_header,
        contact=contact,
        roles=roles,
        education_items=list(spine.education.items) if spine.education else [],
    )

    units_out = [
        UnitOut(
            id=u.id,
            role=u.role,
            headline=_headline(u),
            tier=u.tier.value,
            status=u.status.value,
            skills=u.skills,
            metrics=[{"value": m.value, "tier": m.tier.value} for m in u.metrics],
            link=u.link,
            render_notes=u.render_notes,
            open_verifies=len(u.verify),
        )
        for u in units
    ]

    return ExportPayload(
        jd_source=jd.source,
        title_to_mirror=jd.title_to_mirror,
        role_family=jd.role_family,
        seniority=jd.seniority,
        register_choice=jd.register_choice,
        spine=spine_out,
        wants=wants,
        units=units_out,
        declined=list(declined or []),
    )


def export_payload_json(jd_path: Path, data_dir: Path) -> str:
    jd = load_parsed_jd(jd_path)
    spine = load_spine(data_dir / "spine.yaml")
    units = load_units(data_dir / "evidence")
    declined = load_declined(data_dir / "declined.yaml")
    payload: ExportPayload = build_export(jd, units, spine, declined)
    return payload.model_dump_json(indent=2)
