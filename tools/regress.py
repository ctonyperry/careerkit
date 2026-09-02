"""Replay every shipped defect against the current gates.

Answers the question the defect corpus exists for: would today's pipeline catch
yesterday's mistakes? Each entry in evals/defects.yaml names the gate that
should now fire. This runs the real gate against the real text and reports
agreement, so a claim of enforcement cannot drift away from the code.

    python tools/regress.py [--verbose]

Exit 1 if any defect claiming mechanical enforcement is no longer caught.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).parent))
from _paths import CORPUS as CAREERKIT  # noqa: E402

sys.path.insert(0, str(ROOT / "tools"))

import metrics as metrics_mod  # noqa: E402

from careerkit.dataload import load_spine, load_units  # noqa: E402
from careerkit.linter import lint_resume  # noqa: E402
from careerkit.models import EvidenceUnit, Status, Tier  # noqa: E402


def _lint_rules(text: str, form: str, context: dict | None = None) -> set[str]:
    spine = load_spine(CAREERKIT / "data" / "spine.yaml")
    units = load_units(CAREERKIT / "data" / "evidence")
    # A few rules read the corpus rather than the sentence: do-not-print fires
    # on phrases some unit protects. A defect that depends on that carries the
    # phrase in `context`, so the replay works on any corpus, including the
    # fictional one CI runs on, and not only on the corpus the defect came from.
    if context and context.get("do_not_print"):
        units = [*units, EvidenceUnit(
            id="regress-fixture-context", role=None, narrative="fixture",
            skills=[], tier=Tier.MEMORY, status=Status.CONFIRMED,
            do_not_print=list(context["do_not_print"]),
        )]
    # Form matters: several rules are bullet-scoped or prose-scoped by design,
    # so replaying a cover-letter sentence as a bullet tests the wrong rule.
    if form == "prose":
        body = text
    else:
        body = text if text.lstrip().startswith(("-", "*")) else f"- {text}"
    return {f.rule for f in lint_resume(body, spine, units)}


def _metrics_signal(defect: dict) -> bool:
    """Metrics rules are measurements, not matchers: confirm the measure exists
    and is wired, rather than pretending a fragment can be scored."""
    return defect["enforced_by"].split(":", 1)[1] in {
        "skills_terms_unsupported",
        "jargon_absent_from_jd",
        "bullet_length_spread",
        "pages",
    } and hasattr(metrics_mod, defect["enforced_by"].split(":", 1)[1].replace("pages", "_page_count"))


def check(defect: dict) -> tuple[str, str]:
    """Return (verdict, detail). Verdict is CAUGHT / MISSED / HUMAN / MANUAL."""
    enforced = defect["enforced_by"]
    if enforced == "human":
        return "HUMAN", defect.get("note", "").split(".")[0]
    if defect.get("scope") in {"document", "run"}:
        # Needs a whole document (a summary, a parsed JD) or a whole run.
        return "MANUAL", f"{enforced} (needs {defect['scope']} context)"
    if enforced.startswith("lint:"):
        rule = enforced.split(":", 1)[1]
        form = defect.get("form", "bullet")
        context = defect.get("context")
        fired = _lint_rules(defect["text"], form, context)
        if rule not in fired:
            return "MISSED", f"{rule} did not fire"
        # The other half of a rule being right: a near-miss it must leave
        # alone. A rule that fires on everything is as useless as one that
        # fires on nothing, and only the second kind was being tested. Entries
        # opt in with `must_not_match`; the field is the fixture.
        near_miss = defect.get("must_not_match")
        if near_miss and rule in _lint_rules(near_miss, form, context):
            return "MISSED", f"{rule} also fires on its near-miss: {near_miss[:50]!r}"
        return "CAUGHT", rule
    if enforced.startswith("metrics:"):
        ok = _metrics_signal(defect)
        return ("CAUGHT", enforced) if ok else ("MISSED", f"{enforced} not wired")
    if enforced.startswith(("crosscheck:", "skill:")):
        # Both need a whole run or a whole document; the unit tests in
        # tests/test_crosscheck.py cover the crosscheck rules directly.
        return "MANUAL", enforced
    return "MISSED", f"unknown enforcement '{enforced}'"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    corpus = yaml.safe_load((ROOT / "evals" / "defects.yaml").read_text(encoding="utf-8"))
    defects = corpus["defects"]

    tally: dict[str, int] = {}
    failures: list[str] = []
    for defect in defects:
        verdict, detail = check(defect)
        tally[verdict] = tally.get(verdict, 0) + 1
        if verdict == "MISSED":
            failures.append(f"{defect['id']}: {detail}")
        if args.verbose or verdict == "MISSED":
            shipped = " (SHIPPED)" if defect.get("shipped") else ""
            print(f"{verdict:7} {defect['id']}{shipped}")
            if detail:
                print(f"        {detail}")

    total = len(defects)
    shipped = sum(1 for d in defects if d.get("shipped"))
    print(
        f"\n{total} defects on record, {shipped} of them actually shipped."
        f"\n  mechanically caught: {tally.get('CAUGHT', 0)}"
        f"\n  covered by run-level gates or the de-slop pass: {tally.get('MANUAL', 0)}"
        f"\n  human-only, by design: {tally.get('HUMAN', 0)}"
        f"\n  no longer caught: {tally.get('MISSED', 0)}"
    )
    if failures:
        print("\nREGRESSIONS:")
        for f in failures:
            print(f"  - {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
