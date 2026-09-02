"""The record that outlives the search.

A runs directory holds one manifest per application. Each already says what
was captured, drafted, gated and sent. None of them said what came back, and
nothing read across them: six packages out, and the only way to know how
many had answered was to open six files.

This reads every manifest and tabulates it. Two optional manifest fields
carry the other half:

    outcome: no response | screen | interview | offer | rejected | withdrawn
    outcome_date: 2026-09-10
    outcome_notes: free text, in the person's words

What it cannot see: why. A rejection with no reason given is a row, not a
lesson, until the person writes one down.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class RunRow(BaseModel):
    run: str
    company: str
    role: str
    captured: str
    status: str
    exported: bool
    sent: bool
    outcome: str
    outcome_date: str
    outcome_notes: str


class Ledger(BaseModel):
    rows: list[RunRow] = Field(default_factory=list)

    def by_status(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self.rows:
            out[r.status] = out.get(r.status, 0) + 1
        return dict(sorted(out.items()))

    def by_outcome(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self.rows:
            if r.sent:
                key = r.outcome or "no response yet"
                out[key] = out.get(key, 0) + 1
        return dict(sorted(out.items()))


def _runs_root(path: Path) -> Path:
    """Accept the runs directory itself or the directory that contains it."""
    return path / "runs" if (path / "runs").is_dir() else path


def _sent(manifest: dict) -> bool:
    """Only the status says sent. An export block means a document exists
    somewhere shareable, and three packages sat exported and unsent for a
    week; counting them as sent would have put three phantom applications
    in the ledger."""
    return str(manifest.get("status", "")).lower() in {"sent", "applied", "submitted"}


def build_ledger(path: Path) -> Ledger:
    rows: list[RunRow] = []
    for m in sorted(_runs_root(path).glob("*/manifest.yaml")):
        data = yaml.safe_load(m.read_text(encoding="utf-8")) or {}
        rows.append(RunRow(
            run=m.parent.name,
            company=str(data.get("company", "")),
            role=str(data.get("role", "")),
            captured=str(data.get("captured", "")),
            status=str(data.get("status", "")),
            exported=bool(data.get("export")),
            sent=_sent(data),
            outcome=str(data.get("outcome", "") or ""),
            outcome_date=str(data.get("outcome_date", "") or ""),
            outcome_notes=str(data.get("outcome_notes", "") or ""),
        ))
    rows.sort(key=lambda r: (r.captured, r.run))
    return Ledger(rows=rows)


def render(ledger: Ledger) -> str:
    if not ledger.rows:
        return "No runs found.\n"
    out = ["| Captured | Company | Role | Status | Exported | Sent | Outcome |",
           "|---|---|---|---|---|---|---|"]
    for r in ledger.rows:
        outcome = r.outcome + (f" ({r.outcome_date})" if r.outcome_date else "")
        out.append(f"| {r.captured} | {r.company} | {r.role} | {r.status} | "
                   f"{'yes' if r.exported else ''} | {'yes' if r.sent else ''} | {outcome} |")
    out.append("")
    sent = sum(1 for r in ledger.rows if r.sent)
    exported = sum(1 for r in ledger.rows if r.exported and not r.sent)
    tail = f", {exported} exported and not sent" if exported else ""
    out.append(f"{len(ledger.rows)} runs, {sent} sent{tail}.")
    if sent:
        came_back = ", ".join(f"{n} {k}" for k, n in ledger.by_outcome().items())
        out.append(f"Of the sent: {came_back}.")
    out.append("By status: " + ", ".join(f"{n} {k}" for k, n in ledger.by_status().items()) + ".")
    notes = [(r.company, r.outcome_notes) for r in ledger.rows if r.outcome_notes]
    if notes:
        out += ["", "## In the person's words", ""] + [f"- **{c}**: {n}" for c, n in notes]
    return "\n".join(out) + "\n"
