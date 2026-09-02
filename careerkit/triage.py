"""The inbox, ranked.

Fifteen postings arrived in an afternoon once the capture button existed, and
the honest question was which of them to spend a run on. Each needs the same
two steps first: a parse (the LLM step, from the file on disk) and a verdict
(arithmetic over the coverage report). This does the second for every posting
that has the first, validates the parse against the alias table so an invented
tag cannot inflate a score, and ranks the lot so the person picks from one
table instead of fifteen files.

What it cannot see: whether the person wants the job, and anything a parse
got wrong that still uses real tags. Read the row before you run the run.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from careerkit.dataload import (
    load_aliases,
    load_declined,
    load_parsed_jd,
    load_spine,
    load_units,
)
from careerkit.inbox import pending
from careerkit.verdict import Verdict, build_verdict

_ORDER = {"apply": 0, "name-the-gap": 1, "hard-gate": 2, "parse-invalid": 3, "unparsed": 4}


class TriageRow(BaseModel):
    file: str
    company: str
    role: str
    state: str  # a verdict recommendation, or parse-invalid / unparsed
    parsed: str | None = None
    verdict: Verdict | None = None
    bad_tags: list[str] = Field(default_factory=list)

    @property
    def rank(self) -> int:
        return _ORDER.get(self.state, 9)


class Triage(BaseModel):
    rows: list[TriageRow] = Field(default_factory=list)


def parsed_path(jd_file: Path) -> Path:
    return jd_file.with_name(jd_file.stem + "-parsed.json")


def invalid_tags(jd_path: Path, canonical: frozenset[str]) -> list[str]:
    jd = load_parsed_jd(jd_path)
    bad = {s for r in jd.requirements for s in r.skills if s not in canonical}
    return sorted(bad)


def build_triage(inbox: Path, data_dir: Path) -> Triage:
    spine = load_spine(data_dir / "spine.yaml")
    units = load_units(data_dir / "evidence")
    declined = load_declined(data_dir / "declined.yaml")
    canonical = frozenset(load_aliases(data_dir / "skills.yaml").canonical_tags)

    rows: list[TriageRow] = []
    for name, company, role in pending(inbox):
        jd_file = inbox / name
        pp = parsed_path(jd_file)
        if not pp.exists():
            rows.append(TriageRow(file=name, company=company, role=role, state="unparsed"))
            continue
        bad = invalid_tags(pp, canonical)
        if bad:
            rows.append(TriageRow(file=name, company=company, role=role, state="parse-invalid",
                                  parsed=pp.name, bad_tags=bad))
            continue
        v = build_verdict(load_parsed_jd(pp), units, spine, declined)
        rows.append(TriageRow(file=name, company=company, role=role, state=v.recommendation,
                              parsed=pp.name, verdict=v))
    rows.sort(key=lambda r: (r.rank, -_hits(r), r.file))
    return Triage(rows=rows)


def _hits(row: TriageRow) -> int:
    return row.verdict.required_counts.get("HIT", 0) if row.verdict else 0


def _req(v: Verdict) -> str:
    c = v.required_counts
    return f"{c.get('HIT', 0)}/{c.get('THIN', 0)}/{c.get('MISS', 0)}/{c.get('DECLINED', 0)}"


def render(t: Triage) -> str:
    if not t.rows:
        return "Nothing pending.\n"
    out = ["| # | Company | Role | Verdict | Required HIT/THIN/MISS/DECL | Gate or gap "
           "| Unmapped |",
           "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(t.rows, 1):
        if r.verdict:
            v = r.verdict
            gate = "; ".join(v.hard_gates or v.name_in_the_letter)[:90]
            out.append(f"| {i} | {r.company} | {r.role} | **{r.state}** | {_req(v)} | {gate} | "
                       f"{len(v.unknown_terms)} |")
        elif r.state == "parse-invalid":
            out.append(f"| {i} | {r.company} | {r.role} | parse-invalid | | "
                       f"tags not in skills.yaml: {', '.join(r.bad_tags)} | |")
        else:
            out.append(f"| {i} | {r.company} | {r.role} | unparsed | | | |")
    out.append("")
    counts: dict[str, int] = {}
    for r in t.rows:
        counts[r.state] = counts.get(r.state, 0) + 1
    ordered = sorted(counts.items(), key=lambda kv: _ORDER.get(kv[0], 9))
    out.append(", ".join(f"{n} {k}" for k, n in ordered) + ".")
    unparsed = [r.file for r in t.rows if r.state == "unparsed"]
    if unparsed:
        out += ["", "Parse next (prompts/jd-parse.md, output beside the posting "
                    "as <name>-parsed.json):"]
        out += [f"- {f}" for f in unparsed]
    return "\n".join(out) + "\n"
