"""Unmapped posting language, and what the person decided about it.

A parse puts every want it cannot map into `unknown_terms`. Until now that
was where the story ended: the same twenty terms would be asked again on
the next posting, and nothing changed a verdict when the person answered.

A decision has three honest outcomes, and each is a fact worth keeping:

    alias   the term means a tag the record already has; the alias table
            grows by this confirmation and nothing else
    gap     a real skill the person does not have; the want scores as a MISS
            from now on instead of being ignored, and it is never asked again
    ignore  not a skill, or not relevant; it stops appearing

Decisions live in data/terms.yaml beside declined.yaml, each with a note in
the person's words and a date. `careerkit terms` shows the queue across
every parsed posting; the decisions are flags, so a chat, a script or a
future interface can make them the same way.

What it cannot see: a term that means a skill the person has but no unit
records. That is a unit to write, not an alias to add, and only the person
knows.
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from careerkit.dataload import AliasTable, load_parsed_jd
from careerkit.jd import ParsedJD, Requirement

Decision = Literal["alias", "gap", "ignore"]
GAP_PREFIX = "gap:"


class TermDecision(BaseModel):
    term: str
    decision: Decision
    tag: str | None = None  # for alias
    note: str = ""
    date: str = ""


class QueueItem(BaseModel):
    term: str
    postings: list[str] = Field(default_factory=list)
    suggested_tag: str | None = None
    in_required_want: bool = False


def _norm(term: str) -> str:
    return re.sub(r"\s+", " ", term.strip().lower())


def load_terms(path: Path) -> list[TermDecision]:
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [TermDecision.model_validate(t) for t in raw.get("terms") or []]


def record(path: Path, decision: TermDecision) -> None:
    """Append one decision. Never rewrites what is there: the file is the
    person's record and the machine only adds to it."""
    decision = decision.model_copy(update={"date": decision.date or dt.date.today().isoformat()})
    existing = load_terms(path)
    if any(_norm(t.term) == _norm(decision.term) for t in existing):
        raise ValueError(f"{decision.term!r} already has a decision; edit terms.yaml to change it")
    if decision.decision == "alias" and not decision.tag:
        raise ValueError("an alias decision needs the tag it maps to")
    block = {"term": decision.term, "decision": decision.decision}
    if decision.tag:
        block["tag"] = decision.tag
    if decision.note:
        block["note"] = decision.note
    block["date"] = decision.date
    text = yaml.safe_dump([block], allow_unicode=True, sort_keys=False, width=88)
    text = "".join("  " + ln + "\n" for ln in text.splitlines())
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        header = ("# Decisions about posting language the parse could not map.\n"
                  "# alias: means a tag the record has. gap: a skill the person lacks; scores\n"
                  "# as a MISS. ignore: not a skill or not relevant. Grows only by the person.\n"
                  "terms:\n")
        path.write_text(header + text, encoding="utf-8")
    else:
        with path.open("a", encoding="utf-8") as f:
            f.write(text)


def alias_additions(terms: list[TermDecision]) -> dict[str, list[str]]:
    """Alias decisions as {tag: [term, ...]}, for the alias table to merge."""
    out: dict[str, list[str]] = {}
    for t in terms:
        if t.decision == "alias" and t.tag:
            out.setdefault(t.tag, []).append(t.term)
    return out


def suggest_tag(term: str, aliases: AliasTable) -> str | None:
    """A tag the term already resolves to, or one whose name or aliases the
    term contains. A suggestion, shown, never applied."""
    hit = aliases.resolve(term)
    if hit:
        return hit
    low = _norm(term)
    # A known phrase inside the term, as whole words: "data migration" carries
    # "migration"; "SCIM provisioning" carries "scim". Long phrases may match
    # inside a word ("opentelemetry" carries "telemetry"); short ones may not,
    # because "nat" inside "coordinating" once suggested networking.
    best: tuple[int, str] | None = None
    for phrase, tag in aliases.phrases.items():
        if len(phrase) < 4:
            continue
        whole = re.search(r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])", low)
        matched = bool(whole) or (len(phrase) >= 8 and phrase in low)
        if matched and (best is None or len(phrase) > best[0]):
            best = (len(phrase), tag)
    return best[1] if best else None


def build_queue(parsed_files: list[Path], terms: list[TermDecision],
                aliases: AliasTable) -> list[QueueItem]:
    decided = {_norm(t.term) for t in terms}
    items: dict[str, QueueItem] = {}
    for pf in parsed_files:
        jd = load_parsed_jd(pf)
        label = jd.company or pf.stem
        required_text = " ".join(r.text.lower() for r in jd.requirements
                                 if r.weight == "required" and not r.skills)
        for term in jd.unknown_terms:
            key = _norm(term)
            if key in decided or aliases.resolve(term):
                continue
            item = items.setdefault(
                key, QueueItem(term=term, suggested_tag=suggest_tag(term, aliases)))
            if label not in item.postings:
                item.postings.append(label)
            if key in required_text:
                item.in_required_want = True
    return sorted(items.values(),
                  key=lambda i: (-len(i.postings), not i.in_required_want, i.term.lower()))


def apply_decisions(jd: ParsedJD, terms: list[TermDecision]) -> ParsedJD:
    """Re-map a parse in the light of the decisions. A requirement with no
    tags whose text carries an alias term gets that tag; one carrying a gap
    term gets a synthetic gap tag that no unit can satisfy, so the want scores
    as a MISS. Ignored terms change nothing. Returns a new ParsedJD."""
    if not terms:
        return jd
    reqs: list[Requirement] = []
    for r in jd.requirements:
        if r.skills:
            reqs.append(r)
            continue
        low = r.text.lower()
        skills: list[str] = []
        for t in terms:
            if _norm(t.term) not in low:
                continue
            if t.decision == "alias" and t.tag and t.tag not in skills:
                skills.append(t.tag)
            elif t.decision == "gap":
                skills.append(f"{GAP_PREFIX}{t.term}")
        reqs.append(r.model_copy(update={"skills": skills}) if skills else r)
    return jd.model_copy(update={"requirements": reqs})


def render_queue(queue: list[QueueItem]) -> str:
    if not queue:
        return "Nothing to decide: every term in every parsed posting has a decision.\n"
    out = ["| Term | Postings | In a required want | Suggested tag |", "|---|---|---|---|"]
    for q in queue:
        out.append(f"| {q.term} | {len(q.postings)}: {', '.join(q.postings)[:60]} | "
                   f"{'yes' if q.in_required_want else ''} | {q.suggested_tag or ''} |")
    out += ["", f"{len(queue)} terms. Decide with:",
            '  careerkit terms --alias "<term>" <tag> --note "..."',
            '  careerkit terms --gap "<term>" --note "..."',
            '  careerkit terms --ignore "<term>" --note "..."']
    return "\n".join(out) + "\n"
