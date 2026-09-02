"""Markdown gap-report writer. No em dashes in generated text (house style)."""

from __future__ import annotations

from careerkit.coverage import CoverageStatus, RequirementCoverage
from careerkit.jd import ParsedJD
from careerkit.questions import RecoveryQuestion
from careerkit.strategy import StrategyNote, TenureFinding

_STATUS_LABEL = {
    CoverageStatus.HIT: "HIT",
    CoverageStatus.THIN: "THIN",
    CoverageStatus.MISS: "MISS",
    CoverageStatus.DECLINED: "DECLINED",
}

_GATE_LABEL = {
    ("credential", True): "hard gate",
    ("credential", False): "boilerplate",
    ("declined", True): "no workaround",
    ("declined", False): "compensable",
}


def render_gap_report(
    jd: ParsedJD,
    coverages: list[RequirementCoverage],
    questions: list[RecoveryQuestion],
    strategy_notes: list[StrategyNote] | None = None,
    tenure_findings: list[TenureFinding] | None = None,
) -> str:
    strategy_notes = strategy_notes or []
    tenure_findings = tenure_findings or []
    lines: list[str] = [
        f"# Gap Report: {jd.title_to_mirror}",
        "",
        f"- Source JD: {jd.source}",
        f"- Role family: {jd.role_family}",
        f"- Seniority: {jd.seniority}",
        f"- Title to mirror: {jd.title_to_mirror}",
        "",
        "## Coverage",
        "",
        "| Requirement | Status | Skill detail |",
        "|---|---|---|",
    ]
    for cov in coverages:
        detail = "; ".join(
            f"{s.skill}: {_STATUS_LABEL[s.status]}"
            + (f" ({', '.join(s.unit_ids)})" if s.unit_ids else "")
            for s in cov.skills
        )
        lines.append(
            f"| {cov.requirement.text} | {_STATUS_LABEL[cov.status]} | {detail} |"
        )

    weak_notes = [
        f"- {s.skill} / {uid}: {reason}"
        for cov in coverages
        for s in cov.skills
        for uid, reason in s.weak_reasons.items()
    ]
    if weak_notes:
        lines += ["", "### Why thin evidence is thin", ""] + weak_notes

    if jd.unknown_terms:
        lines += [
            "",
            "## Unknown JD terms (confirm as aliases in data/skills.yaml or dismiss)",
            "",
        ] + [f"- {t}" for t in jd.unknown_terms]

    if tenure_findings:
        lines += ["", "## Tenure (computed from the spine, never asked)", ""]
        for f in tenure_findings:
            lines.append(f"- {f.requirement_text}: {f.detail}")

    if strategy_notes:
        lines += [
            "",
            "## Strategy notes (non-excavatable requirements)",
            "",
        ]
        for note in strategy_notes:
            gate = _GATE_LABEL[(note.reason, note.hard_gate)]
            lines.append(f"### {note.requirement_text} ({note.reason}, {gate})")
            lines += ["", note.detail, ""]

    lines += ["", "## Recovery questions", ""]
    if not questions:
        lines.append("None. Every requirement has solid coverage.")
    for i, q in enumerate(questions, 1):
        lines += [f"### Q{i} ({q.requirement_id})", "", q.text, ""]

    lines += [
        "---",
        "Answers become new evidence units (status: provisional, tier: MEMORY)",
        "after a defensibility check. Nothing auto-confirms; Tony is the trust gate.",
        "",
    ]
    return "\n".join(lines)
