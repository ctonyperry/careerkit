"""CLI entry point.

careerkit gap --jd <parsed-jd.json> [--data data] [--out gap-report.md]

The JD parse is an LLM step done in Claude Code chat using prompts/jd-parse.md;
this command consumes its JSON output and runs the deterministic pipeline.
"""

from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

from careerkit.brief import RenderKnobs, build_brief, render_brief
from careerkit.coverage import assess_jd
from careerkit.dataload import (
    load_declined,
    load_parsed_jd,
    load_spine,
    load_units,
)
from careerkit.deslop import deslop_text
from careerkit.finalize import finalization_gate, render_finalization
from careerkit.linter import Severity, lint_resume
from careerkit.paths import corpus_dir
from careerkit.questions import generate_questions
from careerkit.report import render_gap_report
from careerkit.select import BUDGETS
from careerkit.session import IngestSession, write_session
from careerkit.strategy import strategy_notes, tenure_findings
from careerkit.webexport import export_payload_json

_DATA_HELP = "career data directory (default: $CAREERKIT_CORPUS/data, else the sample corpus)"


def _data_dir(args: argparse.Namespace) -> Path:
    """--data wins; otherwise the corpus careerkit.paths knows about."""
    if getattr(args, "data", None):
        return Path(args.data)
    return corpus_dir() / "data"


def _cmd_gap(args: argparse.Namespace) -> int:
    data_dir = _data_dir(args)
    jd = load_parsed_jd(Path(args.jd))
    spine = load_spine(data_dir / "spine.yaml")
    units = load_units(data_dir / "evidence")
    declined = load_declined(data_dir / "declined.yaml")

    coverages = assess_jd(jd, units, spine, declined)
    questions = generate_questions(coverages)
    notes = strategy_notes(coverages)
    tenure = tenure_findings(coverages, spine)
    report = render_gap_report(jd, coverages, questions, notes, tenure)

    out = Path(args.out)
    out.write_text(report, encoding="utf-8")
    print(f"Wrote {out} ({len(questions)} recovery questions)")
    return 0


def _cmd_resume(args: argparse.Namespace) -> int:
    data_dir = _data_dir(args)
    jd = load_parsed_jd(Path(args.jd))
    spine = load_spine(data_dir / "spine.yaml")
    units = load_units(data_dir / "evidence")

    knobs = RenderKnobs(
        length=args.length,
        register_choice=args.register,
        education_placement=args.education_placement,
        earliest_year_shown=args.earliest_year_shown,
    )
    brief = build_brief(jd, units, spine, knobs)
    report = render_brief(brief)

    out = Path(args.out)
    out.write_text(report, encoding="utf-8")
    watermark = " [DRAFT: provisional units selected]" if brief.is_draft else ""
    print(f"Wrote {out} ({len(brief.experience)} experience roles){watermark}")
    print("Next: write the resume in chat using prompts/resume-write.md")
    return 0


def _cmd_lint(args: argparse.Namespace) -> int:
    data_dir = _data_dir(args)
    spine = load_spine(data_dir / "spine.yaml")
    units = load_units(data_dir / "evidence")
    text = Path(args.draft).read_text(encoding="utf-8")
    jd = load_parsed_jd(Path(args.jd)) if args.jd else None

    findings = lint_resume(text, spine, units, jd)
    blockers = [f for f in findings if f.severity is Severity.BLOCK]
    warnings = [f for f in findings if f.severity is Severity.WARN]
    for f in findings:
        print(f"{f.severity.value:5} L{f.line} [{f.rule}] {f.message} :: {f.excerpt}")
    print(f"{len(blockers)} blocking, {len(warnings)} advisory")
    return 1 if blockers else 0


def _cmd_ingest_session(args: argparse.Namespace) -> int:
    session = IngestSession.model_validate_json(
        Path(args.session).read_text(encoding="utf-8")
    )
    date = args.date or datetime.date.today().isoformat()
    result = write_session(session, _data_dir(args), date)
    for uid in result.created_units:
        print(f"+ evidence/{uid}.yaml (provisional)")
    for wid in result.added_declines:
        print(f"~ declined: {wid}")
    print(
        f"Wrote {len(result.created_units)} provisional unit(s), "
        f"{len(result.added_declines)} decline(s). Re-run `careerkit export` to refresh the UI."
    )
    return 0


def _cmd_verdict(args: argparse.Namespace) -> int:
    from careerkit.verdict import build_verdict, render

    data_dir = _data_dir(args)
    jd = load_parsed_jd(Path(args.jd))
    v = build_verdict(jd, load_units(data_dir / "evidence"), load_spine(data_dir / "spine.yaml"),
                      load_declined(data_dir / "declined.yaml"))
    text = render(v)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"Wrote {args.out} ({v.recommendation})")
    else:
        print(text)
    return 0


def _cmd_outcomes(args: argparse.Namespace) -> int:
    import os

    from careerkit.outcomes import build_ledger, render

    root = args.runs or os.environ.get("CAREERKIT_RUNS")
    if not root:
        print("give --runs or set CAREERKIT_RUNS to the directory holding runs/", file=sys.stderr)
        return 2
    print(render(build_ledger(Path(root))))
    return 0


def _cmd_init(args: argparse.Namespace) -> int:
    import shutil

    from careerkit.paths import SAMPLE_CORPUS

    dest = Path(args.dest)
    if dest.exists() and any(dest.iterdir()):
        print(f"{dest} exists and is not empty; refusing to overwrite it", file=sys.stderr)
        return 2
    shutil.copytree(SAMPLE_CORPUS, dest, dirs_exist_ok=True)
    message = f"""Copied the sample corpus to {dest}.
Every line in it is fiction. Replace data/spine.yaml first, then delete the
sample evidence and write your own, one unit per thing you did. Then:
    export CAREERKIT_CORPUS={dest}
    careerkit stale        # what still needs a date and a name
    careerkit verdict --jd <parsed-jd.json>"""
    print(message)
    return 0


def _cmd_prep(args: argparse.Namespace) -> int:
    from careerkit.prep import build_prep, render

    sheet = build_prep(Path(args.run), _data_dir(args))
    text = render(sheet)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"Wrote {args.out} ({len(sheet.units)} cited units, {len(sheet.probes)} probes)")
    else:
        print(text)
    return 0


def _cmd_stale(args: argparse.Namespace) -> int:
    from careerkit.dataload import load_units
    from careerkit.stale import render, stale_units

    units = load_units(_data_dir(args) / "evidence")
    entries = stale_units(units, older_than_days=args.older_than)
    print(render(entries))
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    blob = export_payload_json(Path(args.jd), _data_dir(args))
    out = Path(args.out)
    out.write_text(blob, encoding="utf-8")
    print(f"Wrote {out}")
    return 0


def _cmd_deslop(args: argparse.Namespace) -> int:
    src = Path(args.draft)
    cleaned, changes = deslop_text(src.read_text(encoding="utf-8"))
    out = Path(args.out) if args.out else src
    out.write_text(cleaned, encoding="utf-8")
    if changes:
        for c in changes:
            print(f"- {c}")
        print(f"Wrote {out}")
    else:
        print(f"No mechanical slop to fix; {out} unchanged")
    return 0


def _cmd_finalize(args: argparse.Namespace) -> int:
    data_dir = _data_dir(args)
    jd = load_parsed_jd(Path(args.jd))
    spine = load_spine(data_dir / "spine.yaml")
    units = load_units(data_dir / "evidence")
    draft_text = Path(args.draft).read_text(encoding="utf-8")

    knobs = RenderKnobs(
        length=args.length,
        register_choice=args.register,
        education_placement=args.education_placement,
        earliest_year_shown=args.earliest_year_shown,
    )
    report = finalization_gate(jd, units, spine, knobs, draft_text)
    print(render_finalization(report))
    return 0 if report.is_ready else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="careerkit")
    sub = parser.add_subparsers(dest="command", required=True)

    gap = sub.add_parser("gap", help="coverage analysis + recovery questions for a JD")
    gap.add_argument("--jd", required=True, help="parsed JD json (see prompts/jd-parse.md)")
    gap.add_argument("--data", default=None, help=_DATA_HELP)
    gap.add_argument("--out", default="gap-report.md", help="output markdown path")
    gap.set_defaults(func=_cmd_gap)

    resume = sub.add_parser(
        "resume", help="assemble the writer brief (selected units + render knobs)"
    )
    resume.add_argument("--jd", required=True, help="parsed JD json (see prompts/jd-parse.md)")
    resume.add_argument("--data", default=None, help=_DATA_HELP)
    resume.add_argument(
        "--length", default="one-page", choices=sorted(BUDGETS), help="length budget"
    )
    resume.add_argument(
        "--register", default=None, help="register/voice choice (The author picks; never auto)"
    )
    resume.add_argument(
        "--education-placement",
        default="present",
        choices=["present", "bottom-minimal", "omitted"],
        help="education section placement",
    )
    resume.add_argument(
        "--earliest-year-shown",
        type=int,
        default=None,
        help="compress roles ending before this year to an Earlier: line",
    )
    resume.add_argument("--out", default="resume-brief.md", help="output markdown path")
    resume.set_defaults(func=_cmd_resume)

    lint = sub.add_parser(
        "lint", help="mechanical house-style lint of a written resume draft"
    )
    lint.add_argument("draft", help="resume draft markdown to check")
    lint.add_argument("--data", default=None, help=_DATA_HELP)
    lint.add_argument(
        "--jd",
        default=None,
        help="parsed JD json; enables the jd-mirroring check on the summary",
    )
    lint.set_defaults(func=_cmd_lint)

    ingest = sub.add_parser(
        "ingest-session", help="persist a web UI excavation session into the corpus"
    )
    ingest.add_argument("session", help="session JSON exported from the web UI")
    ingest.add_argument("--data", default=None, help=_DATA_HELP)
    ingest.add_argument("--date", default=None, help="decline date (default: today)")
    ingest.set_defaults(func=_cmd_ingest_session)

    export = sub.add_parser(
        "export", help="dump the web UI JSON payload (spine, ranked wants, units)"
    )
    export.add_argument("--jd", required=True, help="parsed JD json")
    export.add_argument("--data", default=None, help=_DATA_HELP)
    export.add_argument("--out", default="web-payload.json", help="output JSON path")
    export.set_defaults(func=_cmd_export)

    deslop = sub.add_parser(
        "deslop", help="optional final pass: auto-fix mechanical slop (em dashes, spacing)"
    )
    deslop.add_argument("draft", help="resume draft markdown to clean")
    deslop.add_argument(
        "--out", default=None, help="output path (default: overwrite the draft in place)"
    )
    deslop.set_defaults(func=_cmd_deslop)

    verdict = sub.add_parser("verdict", help="the fit verdict, computed before any drafting")
    verdict.add_argument("--jd", required=True, help="parsed JD json")
    verdict.add_argument("--data", default=None, help=_DATA_HELP)
    verdict.add_argument("--out", default=None, help="write markdown here instead of stdout")
    verdict.set_defaults(func=_cmd_verdict)

    outcomes = sub.add_parser("outcomes", help="every run in one table: status, sent, outcome")
    outcomes.add_argument("--runs", default=None, help="runs directory (default: $CAREERKIT_RUNS)")
    outcomes.set_defaults(func=_cmd_outcomes)

    init = sub.add_parser("init", help="copy the sample corpus to start your own")
    init.add_argument("dest", help="directory to create")
    init.set_defaults(func=_cmd_init)

    prep = sub.add_parser(
        "prep", help="interview prep sheet from a run: bounds, open items, probes"
    )
    prep.add_argument("--run", required=True, help="run directory (manifest.yaml, claim-sheet.md)")
    prep.add_argument("--data", default=None, help=_DATA_HELP)
    prep.add_argument("--out", default=None, help="write markdown here instead of stdout")
    prep.set_defaults(func=_cmd_prep)

    stale = sub.add_parser(
        "stale", help="units by how long since they were last confirmed; the re-ask list"
    )
    stale.add_argument("--data", default=None, help=_DATA_HELP)
    stale.add_argument(
        "--older-than", type=int, default=None, metavar="DAYS",
        help="only units not confirmed within this many days (undated always shown)",
    )
    stale.set_defaults(func=_cmd_stale)

    finalize = sub.add_parser(
        "finalize", help="just-in-time confirmation gate for a written draft"
    )
    finalize.add_argument("draft", help="resume draft markdown")
    finalize.add_argument("--jd", required=True, help="parsed JD json (same one used to write)")
    finalize.add_argument("--data", default=None, help=_DATA_HELP)
    finalize.add_argument(
        "--length", default="one-page", choices=sorted(BUDGETS), help="length budget"
    )
    finalize.add_argument("--register", default=None, help="register/voice choice")
    finalize.add_argument(
        "--education-placement",
        default="present",
        choices=["present", "bottom-minimal", "omitted"],
    )
    finalize.add_argument("--earliest-year-shown", type=int, default=None)
    finalize.set_defaults(func=_cmd_finalize)

    args = parser.parse_args(argv)
    # Render notes quote people, and people use dashes and accents. A Windows
    # console defaulting to cp1252 turned those into "?" on the prep sheet.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    sys.exit(main())
