"""careerkit as an MCP server, so a chat can drive the pipeline.

The commands already exist and take files. This exposes the ones a
conversation wants as tools: the inbox, the triage table, a verdict, the
queue of unmapped language and a decision on one term, the prep sheet, the
outcomes ledger, what has gone stale. Nothing here drafts prose and nothing
here edits the corpus except by appending a decision the person made.

    careerkit mcp            # stdio; point Claude Desktop at this

Where the person lives comes from the same two environment variables as
everything else: CAREERKIT_CORPUS and CAREERKIT_RUNS.

What it cannot see: the same things the commands cannot. It adds no
judgement; it puts the existing ones within reach of a conversation.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from careerkit.dataload import (
    load_aliases,
    load_declined,
    load_parsed_jd,
    load_spine,
    load_units,
)
from careerkit.paths import corpus_dir

INSTRUCTIONS = """careerkit: an evidence-grounded resume pipeline. The corpus is the person's
own record, confirmed by them. Never invent a fact about the person. A term
decision (alias, gap, ignore) is the person's call: ask, then record what
they said in their words. Verdicts and triage are arithmetic over the record;
whether the person wants the job stays with them."""


def _data_dir() -> Path:
    return corpus_dir(quiet=True) / "data"


def _runs_root() -> Path:
    root = os.environ.get("CAREERKIT_RUNS")
    if not root:
        raise RuntimeError(
            "CAREERKIT_RUNS is not set; it must name the directory holding jd-inbox/ and runs/")
    return Path(root).expanduser()


def _inbox() -> Path:
    return _runs_root() / "jd-inbox"


def _resolve(path: str) -> Path:
    p = Path(path).expanduser()
    if p.is_absolute():
        return p
    for base in (_runs_root(), _runs_root() / "runs", _inbox()):
        if (base / p).exists():
            return base / p
    return p


def inbox_pending() -> str:
    """Postings captured and not yet run: file, company, role."""
    from careerkit.inbox import pending

    rows = pending(_inbox())
    if not rows:
        return "Nothing pending."
    return "\n".join(f"{f}  {c} / {r}" for f, c, r in rows) + f"\n{len(rows)} pending"


def triage_table() -> str:
    """Every pending posting with a parse: verdict, coverage, unmapped wants, ranked."""
    from careerkit.triage import build_triage, render

    return render(build_triage(_inbox(), _data_dir()))


def verdict_for(parsed_jd: str) -> str:
    """The fit verdict for one parsed posting (a *-parsed.json path)."""
    from careerkit.terms import load_terms
    from careerkit.verdict import build_verdict, render

    data = _data_dir()
    jd = load_parsed_jd(_resolve(parsed_jd))
    v = build_verdict(jd, load_units(data / "evidence"), load_spine(data / "spine.yaml"),
                      load_declined(data / "declined.yaml"), load_terms(data / "terms.yaml"))
    return render(v)


def terms_queue(limit: int = 40, required_only: bool = False) -> str:
    """Posting language no parse could map, across the inbox, most-used first.
    required_only keeps the terms sitting in a required want."""
    from careerkit.terms import build_queue, load_terms, render_queue

    data = _data_dir()
    queue = build_queue(sorted(_inbox().glob("*-parsed.json")), load_terms(data / "terms.yaml"),
                        load_aliases(data / "skills.yaml"))
    if required_only:
        queue = [q for q in queue if q.in_required_want]
    total = len(queue)
    text = render_queue(queue[:limit])
    if total > limit:
        text += f"\n(showing {limit} of {total})\n"
    return text


def terms_decide(term: str, decision: str, tag: str | None = None, note: str = "") -> str:
    """Record the person's decision on one term. decision is alias (with tag),
    gap, or ignore. note is their reason in their words. Never decide for them."""
    from careerkit.terms import TermDecision, record

    if decision not in ("alias", "gap", "ignore"):
        return "decision must be alias, gap or ignore"
    data = _data_dir()
    if decision == "alias":
        if not tag:
            return "an alias needs the tag it maps to"
        if tag not in load_aliases(data / "skills.yaml").canonical_tags:
            return f"{tag!r} is not a tag in skills.yaml; an alias can only point at one"
    try:
        record(data / "terms.yaml", TermDecision(term=term, decision=decision, tag=tag, note=note))
    except ValueError as exc:
        return str(exc)
    return f"recorded: {term!r} -> {decision}" + (f" {tag}" if tag else "")


def prep_sheet(run_dir: str) -> str:
    """The night-before sheet for a run directory: bounds, open items, probes."""
    from careerkit.prep import build_prep, render

    return render(build_prep(_resolve(run_dir), _data_dir()))


def outcomes_table() -> str:
    """Every run: captured, status, exported, sent, outcome."""
    from careerkit.outcomes import build_ledger, render

    return render(build_ledger(_runs_root()))


def stale_units(older_than_days: int | None = None) -> str:
    """Units never dated or not re-confirmed recently, weakest first."""
    from careerkit.stale import render
    from careerkit.stale import stale_units as _stale

    return render(_stale(load_units(_data_dir() / "evidence"), older_than_days=older_than_days))


TOOLS = [inbox_pending, triage_table, verdict_for, terms_queue, terms_decide,
         prep_sheet, outcomes_table, stale_units]


def _safe(fn: Any) -> Any:
    """A missing environment variable or file is an answer the chat can
    relay, not a stack trace it cannot."""
    import functools

    @functools.wraps(fn)
    def wrapped(*args: Any, **kwargs: Any) -> str:
        try:
            return fn(*args, **kwargs)
        except (RuntimeError, FileNotFoundError, SystemExit) as exc:
            return f"careerkit could not answer: {exc}"

    return wrapped


def build_server() -> Any:
    from mcp.server.mcpserver import MCPServer

    server = MCPServer("careerkit", instructions=INSTRUCTIONS)
    for fn in TOOLS:
        server.tool()(_safe(fn))
    return server


def main() -> int:
    build_server().run("stdio")
    return 0
