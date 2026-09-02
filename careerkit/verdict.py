"""The honest verdict, first.

Every run so far began with a fit verdict written by hand at the top of the
manifest: how many requirements land, which are thin, which the person has
ruled out, and whether the posting states a gate they do not meet. The parts
of that which are arithmetic over the coverage report are computed here, so
the verdict comes before the drafting and not after, and so "do not apply"
is a thing the tool can say.

What it cannot see: whether the person wants the job, and whether a HIT is
the story worth telling. Both stay with the person.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from careerkit.coverage import CoverageStatus, RequirementCoverage, assess_jd
from careerkit.jd import ParsedJD
from careerkit.models import DeclinedRecord, EvidenceUnit, Spine
from careerkit.strategy import strategy_notes, tenure_findings
from careerkit.terms import GAP_PREFIX, TermDecision, apply_decisions

Recommendation = Literal["apply", "name-the-gap", "unmapped", "hard-gate"]


class Verdict(BaseModel):
    jd_source: str
    title: str
    company: str | None
    recommendation: Recommendation
    required_counts: dict[str, int] = Field(default_factory=dict)
    preferred_counts: dict[str, int] = Field(default_factory=dict)
    # Wants the parse could not map to any tag. The coverage engine scores
    # an empty skills list as HIT, which on the first real inbox turned a
    # posting with twenty unmapped terms into 10/0/0/0. These are neither
    # covered nor missing until the alias table says which.
    unmapped_required: list[str] = Field(default_factory=list)
    unmapped_preferred: list[str] = Field(default_factory=list)
    hard_gates: list[str] = Field(default_factory=list)
    tenure: list[str] = Field(default_factory=list)
    credentials: list[str] = Field(default_factory=list)
    name_in_the_letter: list[str] = Field(default_factory=list)
    expect_probing: list[str] = Field(default_factory=list)
    say_no_plainly: list[str] = Field(default_factory=list)
    unknown_terms: list[str] = Field(default_factory=list)


def _counts(covs: list[RequirementCoverage]) -> dict[str, int]:
    out = {s.value: 0 for s in CoverageStatus}
    for c in covs:
        out[c.status.value] += 1
    return out


def _weak_detail(cov: RequirementCoverage, declined_text: dict[str, str]) -> str:
    parts = []
    for s in cov.skills:
        if s.status is CoverageStatus.HIT:
            continue
        if s.status is CoverageStatus.DECLINED:
            parts.append(f"{s.skill}: declined ({declined_text.get(s.skill, 'on record')})")
        elif s.status is CoverageStatus.THIN:
            parts.append(f"{s.skill}: rests on {', '.join(s.unit_ids) or 'nothing recent'}")
        elif s.skill.startswith(GAP_PREFIX):
            parts.append(f"{s.skill[len(GAP_PREFIX):]}: a gap you recorded")
        else:
            parts.append(f"{s.skill}: nothing in the record")
    return f"{cov.requirement.text}. " + "; ".join(parts) if parts else cov.requirement.text


def build_verdict(
    jd: ParsedJD,
    units: list[EvidenceUnit],
    spine: Spine,
    declined: list[DeclinedRecord] | None = None,
    terms: list[TermDecision] | None = None,
) -> Verdict:
    declined = declined or []
    jd = apply_decisions(jd, terms or [])
    declined_text = {s: r.text for r in declined for s in r.skills}
    coverages = assess_jd(jd, units, spine, declined)

    capability = [c for c in coverages if c.requirement.kind == "capability"]
    mapped = [c for c in capability if c.requirement.skills]
    unmapped = [c for c in capability if not c.requirement.skills]
    required = [c for c in mapped if c.requirement.weight == "required"]
    preferred = [c for c in mapped if c.requirement.weight == "preferred"]
    unmapped_required = [c.requirement.text for c in unmapped
                         if c.requirement.weight == "required"]
    unmapped_preferred = [c.requirement.text for c in unmapped
                          if c.requirement.weight != "required"]

    weight = {c.requirement.id: c.requirement.weight for c in coverages}
    hard_gates: list[str] = []
    credentials: list[str] = []
    for note in strategy_notes(coverages):
        is_required = weight.get(note.requirement_id) == "required"
        if note.reason == "credential":
            # The strategy engine words a credential as a gate whatever its
            # weight. A preferred credential is a preference.
            credentials.append(note.detail if is_required
                               else f"{note.requirement_text}: preferred, not a gate.")
        # A fully declined PREFERRED requirement is a plain no, not a gate.
        if note.hard_gate and is_required:
            hard_gates.append(f"{note.requirement_text}: {note.detail}")

    tenure_lines: list[str] = []
    for f in tenure_findings(coverages, spine):
        tenure_lines.append(f.detail)
        if f.meets is False:
            hard_gates.append(f"{f.requirement_text}: {f.detail}")

    name = [_weak_detail(c, declined_text) for c in required
            if c.status in (CoverageStatus.MISS, CoverageStatus.DECLINED)]
    probing = [_weak_detail(c, declined_text) for c in required if c.status is CoverageStatus.THIN]
    say_no = [_weak_detail(c, declined_text) for c in preferred
              if c.status is CoverageStatus.DECLINED
              or any(s.skill.startswith(GAP_PREFIX) for s in c.skills)]

    hits = sum(1 for c in required if c.status is CoverageStatus.HIT)
    if hard_gates:
        rec: Recommendation = "hard-gate"
    elif name:
        rec = "name-the-gap"
    elif len(unmapped_required) > hits:
        # More of what is required went unmapped than was answered. The
        # honest call is not "apply"; it is "map these first, then look".
        rec = "unmapped"
    else:
        rec = "apply"

    return Verdict(
        jd_source=jd.source,
        title=jd.title_to_mirror,
        company=jd.company,
        recommendation=rec,
        required_counts=_counts(required),
        preferred_counts=_counts(preferred),
        unmapped_required=unmapped_required,
        unmapped_preferred=unmapped_preferred,
        hard_gates=hard_gates,
        tenure=tenure_lines,
        credentials=credentials,
        name_in_the_letter=name,
        expect_probing=probing,
        say_no_plainly=say_no,
        unknown_terms=list(jd.unknown_terms),
    )


_HEADLINE = {
    "apply": "Apply.",
    "name-the-gap": "Apply, and name the gap.",
    "hard-gate": (
        "The posting states a gate you do not meet. Applying means applying past it, "
        "and no document should argue it."
    ),
    "unmapped": (
        "More of what is required went unmapped than was answered. Add the aliases, "
        "or accept those wants as gaps, before reading the coverage."
    ),
}


def _fmt_counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{n} {k}" for k, n in counts.items() if n)


def render(v: Verdict) -> str:
    where = f" at {v.company}" if v.company else ""
    out = [f"# Verdict: {v.title}{where}", "", f"**{_HEADLINE[v.recommendation]}**", ""]
    out.append(f"Required capabilities: {_fmt_counts(v.required_counts) or 'none'}"
               + (f", plus {len(v.unmapped_required)} the parse could not map"
                  if v.unmapped_required else "") + ".")
    if any(v.preferred_counts.values()) or v.unmapped_preferred:
        out.append(f"Preferred: {_fmt_counts(v.preferred_counts) or 'none'}"
                   + (f", plus {len(v.unmapped_preferred)} unmapped"
                      if v.unmapped_preferred else "") + ".")
    for t in v.tenure:
        out.append(f"Tenure: {t}")
    for c in v.credentials:
        out.append(f"Credential: {c}")
    out.append("")
    if v.hard_gates:
        out += ["## The gate", ""] + [f"- {g}" for g in v.hard_gates] + [""]
    if v.unmapped_required:
        out += ["## Required, and the record has no tag for it", ""]
        out += [f"- {g}" for g in v.unmapped_required] + [""]
    if v.name_in_the_letter:
        out += ["## Name in the letter", ""] + [f"- {g}" for g in v.name_in_the_letter] + [""]
    if v.expect_probing:
        out += ["## Expect probing", ""] + [f"- {g}" for g in v.expect_probing] + [""]
    if v.say_no_plainly:
        out += ["## Say no plainly if asked", ""] + [f"- {g}" for g in v.say_no_plainly] + [""]
    if v.unknown_terms:
        out += ["## Terms the record does not map", ""] + [f"- {t}" for t in v.unknown_terms] + [""]
    return "\n".join(out)
