"""The finalization gate: draft -> final, just-in-time.

A draft can render instantly from provisional units (watermarked). Finalizing
is the trust gate: before a specific resume prints, the human must own only the
marks and [VERIFY]s THAT resume touches (not the whole corpus). This module
computes that checklist deterministically from the selection that built the
draft, plus a clean-lint requirement. It reports; it never flips confirmation
itself. The author is the trust gate; this is the gate's checklist.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from careerkit.brief import BriefUnit, RenderKnobs, build_brief
from careerkit.jd import ParsedJD
from careerkit.linter import Severity, lint_resume
from careerkit.models import EvidenceUnit, Spine

GateKind = Literal["provisional-unit", "open-verify", "lint-blocker"]


class Gate(BaseModel):
    kind: GateKind
    unit_id: str | None = None
    detail: str


class FinalizationReport(BaseModel):
    jd_source: str
    is_ready: bool
    gates: list[Gate] = Field(default_factory=list)


def _selected_brief_units(
    jd: ParsedJD, units: list[EvidenceUnit], spine: Spine, knobs: RenderKnobs
) -> list[BriefUnit]:
    brief = build_brief(jd, units, spine, knobs)
    selected: list[BriefUnit] = []
    for role in brief.experience:
        selected += role.units
    selected += brief.projects
    return selected


def finalization_gate(
    jd: ParsedJD,
    units: list[EvidenceUnit],
    spine: Spine,
    knobs: RenderKnobs,
    draft_text: str,
) -> FinalizationReport:
    gates: list[Gate] = []
    for bu in _selected_brief_units(jd, units, spine, knobs):
        if bu.provisional:
            gates.append(
                Gate(
                    kind="provisional-unit",
                    unit_id=bu.unit_id,
                    detail=(
                        f"Provisional unit '{bu.unit_id}' is used; confirm it "
                        "(status -> confirmed) before this resume prints."
                    ),
                )
            )
        for item in bu.verify:
            gates.append(Gate(kind="open-verify", unit_id=bu.unit_id, detail=item))

    for f in lint_resume(draft_text, spine, units, jd):
        if f.severity is Severity.BLOCK:
            gates.append(
                Gate(
                    kind="lint-blocker",
                    unit_id=None,
                    detail=f"L{f.line} [{f.rule}] {f.message}",
                )
            )

    return FinalizationReport(jd_source=jd.source, is_ready=not gates, gates=gates)


def render_finalization(report: FinalizationReport) -> str:
    lines = [f"# Finalization gate: {report.jd_source}", ""]
    if report.is_ready:
        lines += [
            "READY. No provisional units, open [VERIFY]s, or lint blockers touch "
            "this resume. The author's final confirmation is the last step.",
            "",
        ]
        return "\n".join(lines)

    order: list[tuple[GateKind, str]] = [
        ("lint-blocker", "## Lint blockers (fix these first)"),
        ("provisional-unit", "## Provisional units to confirm"),
        ("open-verify", "## Open [VERIFY]s to resolve or mark"),
    ]
    lines.append(f"NOT READY: {len(report.gates)} open gate(s).")
    lines.append("")
    for kind, header in order:
        group = [g for g in report.gates if g.kind == kind]
        if not group:
            continue
        lines += [header, ""]
        for g in group:
            tag = f"`{g.unit_id}`: " if g.unit_id else ""
            lines.append(f"- {tag}{g.detail}")
        lines.append("")
    return "\n".join(lines)
