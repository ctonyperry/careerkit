"""Assemble the writer brief: the ONLY thing the in-chat resume writer sees.

Deterministic. Takes the ranked selection (select.py) and the spine and lays
out a resume skeleton the constrained LLM writer fills in:

- Experience roles from the spine, newest-first, each with its selected units.
- Timeline continuity: a visible role with no JD-relevant unit still appears
  (a gap in employment reads worse than an off-topic line). It gets its single
  strongest unit, flagged continuity -> the writer gives it ONE factual line
  and does not mine it. This keeps the "writer sees only relevant evidence"
  discipline while avoiding gaps, matching the IMS line in the FINAL resume.
- Earliest-year-shown / Earlier compression (render knob + spine render_notes).
- Education transcribed VERBATIM from the spine (the writer never composes it;
  the hallucinated-diploma failure). Placement is a knob.

The writer prompt is prompts/resume-write.md; this module never calls an LLM.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Literal

from pydantic import BaseModel, Field

from careerkit.jd import ParsedJD
from careerkit.models import Car, EvidenceUnit, Metric, Spine, SpineRole, Status
from careerkit.select import (
    BUDGETS,
    PROJECTS_SECTION,
    ResumeSelection,
    select_units,
    strength,
)

EducationPlacement = Literal["present", "bottom-minimal", "omitted"]


class RenderKnobs(BaseModel):
    length: str = "one-page"
    # Named register_choice (not "register") to avoid shadowing a BaseModel attr.
    register_choice: str | None = None
    education_placement: EducationPlacement = "present"
    # Roles ending before this year compress to the "Earlier:" line.
    earliest_year_shown: int | None = None


class BriefUnit(BaseModel):
    unit_id: str
    narrative: str
    car: Car | None = None
    metrics: list[Metric] = Field(default_factory=list)
    render_notes: list[str] = Field(default_factory=list)
    link: str | None = None
    verify: list[str] = Field(default_factory=list)
    provisional: bool = False
    continuity: bool = False


class BriefRole(BaseModel):
    role_id: str
    title: str
    org: str
    start: str
    end: str
    context_notes: list[str] = Field(default_factory=list)
    units: list[BriefUnit] = Field(default_factory=list)
    continuity_only: bool = False


class ResumeBrief(BaseModel):
    name: str
    title_to_mirror: str
    contact: str
    jd_source: str
    role_family: str
    seniority: str
    register_choice: str | None = None
    length: str = "one-page"
    is_draft: bool = False  # any selected unit provisional -> watermark the output
    experience: list[BriefRole] = Field(default_factory=list)
    earlier: list[str] = Field(default_factory=list)  # "title at org"
    projects: list[BriefUnit] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)  # verbatim spine items
    education_placement: EducationPlacement = "present"
    dropped_unit_ids: list[str] = Field(default_factory=list)
    # Dropped units that are about the employer's own product. Ranking is skill
    # relevance, and such a unit can rank below the cut while being unusually
    # persuasive for that specific employer. Promoting it would let weak
    # evidence beat strong, so it is surfaced instead of moved.
    dropped_target_affinity_ids: list[str] = Field(default_factory=list)
    withheld_unit_ids: list[str] = Field(default_factory=list)


def _omitted(role: SpineRole) -> bool:
    return any("omit from resume" in n.lower() for n in role.render_notes)


def _compressed(role: SpineRole, knobs: RenderKnobs) -> bool:
    if any("earlier:" in n.lower() for n in role.render_notes):
        return True
    end = role.end_year()
    return (
        knobs.earliest_year_shown is not None
        and end is not None
        and end < knobs.earliest_year_shown
    )


def _to_brief_unit(unit: EvidenceUnit, *, continuity: bool = False) -> BriefUnit:
    return BriefUnit(
        unit_id=unit.id,
        narrative=unit.narrative,
        car=unit.car,
        metrics=unit.metrics,
        render_notes=unit.render_notes,
        link=unit.link,
        verify=unit.verify,
        provisional=unit.status is Status.PROVISIONAL,
        continuity=continuity,
    )


def _contact(spine: Spine) -> str:
    i = spine.identity
    return f"{i.location} · {i.email} · {i.phone} · {i.linkedin}"


def build_brief(
    jd: ParsedJD,
    units: list[EvidenceUnit],
    spine: Spine,
    knobs: RenderKnobs,
) -> ResumeBrief:
    budget = BUDGETS[knobs.length]
    selection: ResumeSelection = select_units(jd, units, spine, budget)
    units_by_id = {u.id: u for u in units}

    selected_by_section: dict[str, list[EvidenceUnit]] = defaultdict(list)
    for r in selection.selected:
        selected_by_section[r.section].append(units_by_id[r.unit_id])

    exp_roles = [
        role
        for role in spine.roles
        if role.type != "education" and not _omitted(role)
    ]
    exp_roles.sort(key=lambda role: -(role.end_year() or 0))

    experience: list[BriefRole] = []
    earlier: list[str] = []
    for role in exp_roles:
        if _compressed(role, knobs):
            earlier.append(f"{role.title} at {role.org}")
            continue

        role_units = selected_by_section.get(role.id, [])
        brief_units = [_to_brief_unit(u) for u in role_units]
        continuity_only = False
        if not brief_units:
            # Fill a timeline gap with this role's single strongest unit, if any.
            corpus = [u for u in units if u.role == role.id]
            if corpus:
                best = max(corpus, key=lambda u: (strength(u), u.id))
                brief_units = [_to_brief_unit(best, continuity=True)]
                continuity_only = True

        experience.append(
            BriefRole(
                role_id=role.id,
                title=role.title,
                org=role.org,
                start=role.start,
                end=role.end,
                context_notes=role.render_notes,
                units=brief_units,
                continuity_only=continuity_only,
            )
        )

    projects = [_to_brief_unit(u) for u in selected_by_section.get(PROJECTS_SECTION, [])]

    education: list[str] = []
    if knobs.education_placement != "omitted" and spine.education is not None:
        education = list(spine.education.items)

    return ResumeBrief(
        name=spine.identity.resume_header,
        title_to_mirror=jd.title_to_mirror,
        contact=_contact(spine),
        jd_source=jd.source,
        role_family=jd.role_family,
        seniority=jd.seniority,
        register_choice=knobs.register_choice or jd.register_choice,
        length=knobs.length,
        is_draft=selection.has_provisional,
        experience=experience,
        earlier=earlier,
        projects=projects,
        education=education,
        education_placement=knobs.education_placement,
        dropped_unit_ids=[r.unit_id for r in selection.dropped],
        withheld_unit_ids=selection.withheld_unit_ids,
        dropped_target_affinity_ids=[
            r.unit_id for r in selection.dropped if r.target_affinity
        ],
    )


def _render_unit(u: BriefUnit) -> list[str]:
    flags = []
    if u.continuity:
        flags.append("CONTINUITY: one factual line only, do not expand")
    if u.provisional:
        flags.append("PROVISIONAL: draft only, needs confirmation before finalize")
    header = f"- unit `{u.unit_id}`" + (f"  [{'; '.join(flags)}]" if flags else "")
    lines = [header, f"  - narrative: {u.narrative}"]
    if u.car:
        for part in ("challenge", "action", "result"):
            val = getattr(u.car, part)
            if val:
                lines.append(f"  - {part}: {val}")
    for m in u.metrics:
        lines.append(f"  - metric ({m.tier.value}): {m.value}")
    if u.link:
        lines.append(f"  - link: {u.link}")
    for note in u.render_notes:
        lines.append(f"  - render_note: {note}")
    for v in u.verify:
        lines.append(f"  - [VERIFY]: {v}")
    return lines


def render_brief(brief: ResumeBrief) -> str:
    """Markdown the in-chat writer consumes. See prompts/resume-write.md."""
    lines: list[str] = [f"# Resume Brief: {brief.title_to_mirror}", ""]
    if brief.is_draft:
        lines += [
            "> DRAFT: selection includes provisional units. The written resume "
            "must be watermarked DRAFT and its provisional bullets confirmed "
            "before finalize.",
            "",
        ]
    lines += [
        "## Target",
        "",
        f"- Name (verbatim): {brief.name}",
        f"- Contact (verbatim): {brief.contact}",
        f"- Title to mirror: {brief.title_to_mirror}",
        f"- JD source: {brief.jd_source}",
        f"- Role family: {brief.role_family}",
        f"- Seniority: {brief.seniority}",
        f"- Register: {brief.register_choice or 'UNSET (ask Tony to pick)'}",
        f"- Length: {brief.length}",
        "",
        "## Experience (newest first; write only from the units listed)",
        "",
    ]
    for role in brief.experience:
        lines.append(f"### {role.title} | {role.org} ({role.start} – {role.end})")
        for note in role.context_notes:
            lines.append(f"- role_note: {note}")
        if not role.units:
            lines.append("- (no evidence; render a single factual line from the spine)")
        for u in role.units:
            lines += _render_unit(u)
        lines.append("")

    if brief.earlier:
        lines += ["## Earlier (single compressed line)", ""]
        lines += [f"- {e}" for e in brief.earlier]
        lines.append("")

    if brief.projects:
        lines += ["## Projects", ""]
        for u in brief.projects:
            lines += _render_unit(u)
        lines.append("")

    lines += ["## Education (TRANSCRIBE VERBATIM; never compose or add credentials)", ""]
    if brief.education_placement == "omitted":
        lines.append("- Omitted per render knob (ATS forms may still force a value).")
    elif not brief.education:
        lines.append("- (spine carries no education items)")
    else:
        placement = (
            "bottom, minimal" if brief.education_placement == "bottom-minimal" else "present"
        )
        lines.append(f"- Placement: {placement}")
        lines += [f"- {item}" for item in brief.education]
    lines.append("")

    if brief.dropped_unit_ids:
        lines += [
            "## Not selected (relevant units cut by the length budget; not silent)",
            "",
            f"- {', '.join(brief.dropped_unit_ids)}",
            "",
        ]
    if brief.withheld_unit_ids:
        lines += [
            "### Withheld (relevant, but marked do_not_print)",
            "",
            (
                "Not selected and not available to write from. The protected "
                "phrase is the unit's own substance, so there is nothing left to "
                "render. Do not work around this:"
            ),
            "",
            f"- {', '.join(brief.withheld_unit_ids)}",
            "",
        ]
    if brief.dropped_target_affinity_ids:
        lines += [
            "### Cut, but about the target company",
            "",
            (
                "These rank below the cut on skill relevance, which cannot express "
                "\"this evidence is about the employer's own product\". They are "
                "usually worth carrying in the cover letter rather than forcing "
                "onto the resume:"
            ),
            "",
            f"- {', '.join(brief.dropped_target_affinity_ids)}",
            "",
        ]
    return "\n".join(lines)
