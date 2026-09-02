"""Interview prep from a run: what the page claims, where each claim stops,
what must be settled before the room, and where the questions will land.

The pipeline already knows all of this. Every bullet cites a unit; every unit
carries the bounds the person set on it in their own words, the figures they
doubt, the strings that must never print, and the items still marked verify.
The gap report already knows which requirements are THIN or MISS or declined.
Until now that knowledge stopped at the document. A hiring manager reading the
page does not stop there: they probe the strongest-sounding line, and the
honest answer to that probe is the render note, not the bullet.

So this turns a run into the sheet to read the night before. Nothing here is
generated. It is the corpus, re-sorted around the questions.

What it cannot see: a probe about something the page does not claim, and any
question that depends on the interviewer having read the posting differently
from how it was parsed.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from careerkit.coverage import CoverageStatus, assess_jd
from careerkit.dataload import load_declined, load_parsed_jd, load_spine, load_units
from careerkit.models import DeclinedRecord, EvidenceUnit, Spine

_ID = re.compile(r"`([a-z0-9-]+)`")
_INTERVIEW = re.compile(r"\binterview", re.I)


class Claim(BaseModel):
    section: str
    text: str
    unit_ids: list[str]


class UnitPrep(BaseModel):
    unit_id: str
    claims: list[str]
    bounds: list[str]  # render_notes, verbatim: where the claim stops
    on_record: list[str]  # render_notes that already state an interview answer
    verify: list[str]
    provisional: bool
    safe_figures: list[str]
    doubted_figures: list[str]
    never_say: list[str]


class Probe(BaseModel):
    requirement: str
    status: str
    detail: str


class PrepSheet(BaseModel):
    company: str
    role: str
    units: list[UnitPrep] = Field(default_factory=list)
    probes: list[Probe] = Field(default_factory=list)
    unknown_terms: list[str] = Field(default_factory=list)


def claim_rows(claim_sheet: str) -> list[Claim]:
    """Rows of the Bullets-to-evidence table, in page order."""
    rows: list[Claim] = []
    for line in claim_sheet.splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[0] in {"Section", ""}:
            continue
        ids = _ID.findall(cells[2])
        if ids:
            rows.append(Claim(section=cells[0], text=cells[1], unit_ids=ids))
    return rows


def _unit_prep(unit: EvidenceUnit, claims: list[str]) -> UnitPrep:
    on_record = [n for n in unit.render_notes if _INTERVIEW.search(n)]
    bounds = [n for n in unit.render_notes if n not in on_record]
    return UnitPrep(
        unit_id=unit.id,
        claims=claims,
        bounds=bounds,
        on_record=on_record,
        verify=list(unit.verify),
        provisional=unit.status.value != "confirmed",
        safe_figures=[m.value for m in unit.metrics if not m.doubted],
        doubted_figures=[m.value for m in unit.metrics if m.doubted],
        never_say=list(unit.do_not_print),
    )


def _probes(
    jd_path: Path | None,
    units: list[EvidenceUnit],
    spine: Spine,
    declined: list[DeclinedRecord],
) -> tuple[list[Probe], list[str]]:
    if jd_path is None or not jd_path.exists():
        return [], []
    jd = load_parsed_jd(jd_path)
    probes: list[Probe] = []
    declined_text = {s: r.text for r in declined for s in r.skills}
    for cov in assess_jd(jd, units, spine, declined):
        if cov.status is CoverageStatus.HIT:
            continue
        weak = [s for s in cov.skills if s.status is not CoverageStatus.HIT]
        parts: list[str] = []
        for s in weak:
            if s.status is CoverageStatus.DECLINED:
                parts.append(f"{s.skill}: declined. On record: {declined_text.get(s.skill, '')}")
            elif s.status is CoverageStatus.THIN:
                parts.append(f"{s.skill}: rests on {', '.join(s.unit_ids) or 'nothing recent'}")
            elif s.status is CoverageStatus.MISS:
                parts.append(f"{s.skill}: nothing in the record")
        if cov.requirement.kind == "credential":
            parts.append("credential: answer with the path, never with an apology")
        if cov.requirement.kind == "tenure":
            parts.append("tenure: computed from the spine; do not improvise a number")
        probes.append(Probe(
            requirement=cov.requirement.text,
            status=cov.status.value,
            detail="; ".join(parts) or "not a capability gap",
        ))
    return probes, list(jd.unknown_terms)


def build_prep(run_dir: Path, data_dir: Path) -> PrepSheet:
    manifest = yaml.safe_load((run_dir / "manifest.yaml").read_text(encoding="utf-8")) or {}
    sheet_name = manifest.get("claim_sheet", "claim-sheet.md")
    claims = claim_rows((run_dir / sheet_name).read_text(encoding="utf-8"))

    spine = load_spine(data_dir / "spine.yaml")
    units = load_units(data_dir / "evidence")
    declined = load_declined(data_dir / "declined.yaml")
    by_id = {u.id: u for u in units}

    claimed: dict[str, list[str]] = {}
    for claim in claims:
        for uid in claim.unit_ids:
            claimed.setdefault(uid, []).append(f"{claim.section}: {claim.text}")

    prepped = [_unit_prep(by_id[uid], texts) for uid, texts in claimed.items() if uid in by_id]

    parsed = manifest.get("parsed_jd")
    jd_path = run_dir / parsed if parsed else None
    probes, unknown = _probes(jd_path, units, spine, declined)

    return PrepSheet(
        company=str(manifest.get("company", "")),
        role=str(manifest.get("role", "")),
        units=prepped,
        probes=probes,
        unknown_terms=unknown,
    )


def render(sheet: PrepSheet) -> str:
    out = [f"# Prep: {sheet.role} at {sheet.company}", ""]

    settle = [(u.unit_id, v) for u in sheet.units for v in u.verify]
    provisional = [u.unit_id for u in sheet.units if u.provisional]
    if settle or provisional:
        out += ["## Settle before the room", ""]
        for uid in provisional:
            out.append(f"- `{uid}` is on the page and still provisional. Confirm it or pull it.")
        for uid, item in settle:
            out.append(f"- `{uid}`: {item}")
        out.append("")

    never = [(u.unit_id, p) for u in sheet.units for p in u.never_say]
    doubted = [(u.unit_id, f, u.safe_figures) for u in sheet.units for f in u.doubted_figures]
    if never or doubted:
        out += ["## Figures and phrases to leave out", ""]
        for uid, f, safe in doubted:
            alt = f" Say {', '.join(safe)} instead." if safe else ""
            out.append(f"- `{uid}`: you doubt \"{f}\".{alt}")
        for uid, p in never:
            out.append(f"- `{uid}`: never \"{p}\".")
        out.append("")

    out += ["## What the page claims, and where each claim stops", ""]
    for u in sheet.units:
        out.append(f"### `{u.unit_id}`")
        out.append("")
        for c in u.claims:
            out.append(f"- Page: {c}")
        for b in u.bounds:
            out.append(f"- Bound: {b}")
        for r in u.on_record:
            out.append(f"- On record: {r}")
        if u.safe_figures:
            out.append(f"- Figures you can stand behind: {', '.join(u.safe_figures)}")
        out.append("")

    if sheet.probes:
        out += ["## Where the questions will land", ""]
        for p in sheet.probes:
            out.append(f"- **{p.status}** {p.requirement}")
            out.append(f"  {p.detail}")
        out.append("")
    if sheet.unknown_terms:
        out += ["## Terms the posting uses that the record does not map", ""]
        out += [f"- {t}" for t in sheet.unknown_terms]
        out.append("")
    return "\n".join(out)
