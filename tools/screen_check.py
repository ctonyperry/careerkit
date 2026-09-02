"""The first human pass: seven seconds, six fixation points, an F-pattern.

    python tools/screen_check.py runs/<run-dir>

`ats_check.py` covers the machine. This covers the person who reads next, and
they are the gate that actually rejects. The two need different tools because
they fail differently: a parser fails on glyphs and fields, a human fails on
what they did not reach in time.

## What the research says

TheLadders' 2018 eye-tracking study put the initial scan at 7.4 seconds, and
later work has it drifting shorter as recruiter workload rises. Across studies
roughly 80% of that attention lands on six fixations:

    1 name   2 current job title   3 current company   4 employment dates
    5 previous job title and company   6 education

The scan follows an F-pattern: horizontal across the top, a shorter horizontal
sweep below it, then vertical down the left edge. The left edge means the first
few words of every bullet are read and the rest of the line often is not.

And from Harvard Business School and Accenture: 88% of employers agree
qualified candidates are screened out for not matching exact job-description
criteria. That is the failure this tool is really about. If a stated
requirement is met but the evidence sits in the second sentence of the ninth
bullet, a seven-second reader has not met it.

## Checks

  screen-fixation-risk    a fixation point is missing, ambiguous, or works
                          against the target
  screen-left-edge        a bullet opens on words carrying no information, so
                          the vertical scan gets nothing from it
  screen-requirement-far  a REQUIRED qualification whose evidence appears
                          nowhere above the fold

None of these are about adding claims. They are about where the claims already
made are sitting.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from panel import above_the_fold  # noqa: E402

# Openers that tell a vertical scan nothing. Not banned words: a bullet may
# legitimately start here, it just spends its most-read position on nothing.
LOW_INFO_OPENERS = {
    "was", "were", "is", "are", "had", "has", "have", "did", "does",
    "worked", "helped", "assisted", "supported", "participated", "involved",
    "responsible", "handled", "various", "multiple", "several", "successfully",
    "the", "a", "an", "this", "that", "it", "there",
}

STOP = set(["a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "had", "has", "have", "in", "into", "is", "it", "its", "of", "on", "or", "that", "the", "their", "them", "then", "there", "these", "they", "this", "to", "was", "were", "with", "which", "who", "our", "we", "you", "your", "i"])


@dataclass
class Finding:
    rule: str
    severity: str
    detail: str

    def __str__(self) -> str:
        return f"{self.severity:<5} [{self.rule}] {self.detail}"


def _roles(resume: str) -> list[str]:
    return [ln[4:].strip() for ln in resume.splitlines() if ln.startswith("### ")]


def _bullets(resume: str) -> list[str]:
    return [ln.strip()[2:].strip() for ln in resume.splitlines() if ln.strip().startswith("- ")]


def _distinctive(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9+#./-]{3,}", text)
            if w.lower() not in STOP}


def check(run: Path) -> list[Finding]:
    out: list[Finding] = []
    rp = run / "resume.md"
    if not rp.exists():
        return [Finding("screen-missing-input", "BLOCK", f"no resume.md in {run}")]
    resume = rp.read_text(encoding="utf-8")
    fold = above_the_fold(resume)
    fold_terms = _distinctive(fold)
    roles = _roles(resume)

    # --- Fixations 2 and 5: the current and previous role lines.
    parsed_path = run / "jd-parsed.json"
    target = ""
    if parsed_path.exists():
        target = json.loads(parsed_path.read_text(encoding="utf-8")).get("title_to_mirror", "")
    # The bolded line under the name sits in the F-pattern's top horizontal
    # sweep, so it shares fixation-2 attention with the first role heading. A
    # check that ignored it would report a miss the reader does not experience.
    tagline = ""
    for ln in resume.splitlines()[:6]:
        if ln.strip().startswith("**") and ln.strip().endswith("**"):
            tagline = ln.strip().strip("*")
            break
    if roles and target:
        current = roles[0]
        head = current.split("·")[0].strip()
        shared = _distinctive(head) & _distinctive(target)
        if shared:
            pass
        elif _distinctive(tagline) & _distinctive(target):
            out.append(Finding(
                "screen-fixation-risk", "INFO",
                f"the most recent role reads {head!r} against a target of {target!r} and "
                f"shares no words, but the tagline {tagline!r} carries the target in the "
                f"same top sweep. The scan has something to hold; the role line is still "
                f"the weaker half of that fixation."))
        if not shared and not (_distinctive(tagline) & _distinctive(target)):
            nxt = roles[1].split("·")[0].strip() if len(roles) > 1 else ""
            rescued = bool(_distinctive(nxt) & _distinctive(target))
            out.append(Finding(
                "screen-fixation-risk", "WARN" if rescued else "BLOCK",
                f"fixation 2 is the most-read line after the name, and it reads "
                f"{head!r} against a target of {target!r}, sharing no words. "
                + (f"Fixation 5, {nxt!r}, does connect, so the scan can recover on the "
                   f"second role." if rescued
                   else "Fixation 5 does not connect either, so the top of the page "
                        "gives a seven-second reader nothing to hold onto.")))

    # --- Fixation 6: education, which is read even when nobody asks for it.
    if "## Education" not in resume:
        out.append(Finding("screen-fixation-risk", "WARN",
                           "no education section; it is one of the six fixations and its "
                           "absence is itself read"))

    # --- F-pattern left edge.
    def _weak_opener(b: str) -> bool:
        w = b.split()[0].strip("*") if b.split() else ""
        # An all-caps token is an acronym ("IT Manager"), not the pronoun "it".
        if w.isupper() and len(w) > 1:
            return False
        return w.lower() in LOW_INFO_OPENERS
    weak = [b for b in _bullets(resume) if _weak_opener(b)]
    if weak:
        out.append(Finding(
            "screen-left-edge", "WARN",
            f"{len(weak)} bullet(s) open on a word carrying no information, and the "
            f"vertical scan reads the left edge: "
            + "; ".join(b[:44] for b in weak[:3])))

    # --- Age signal. The author, 2026-08-26: "I thought we had something in place to
    # catch obvious tells of my age?" There was not. Worse, the canonical
    # summary opener MANDATES one. This does not decide the policy; it counts
    # what a reader can compute. Any year more than fifteen back, and any
    # spelled-out tenure over fifteen, is a tell. The conventional advice is a
    # fifteen-year window with older roles undated or compressed.
    from datetime import date
    horizon = date.today().year - 15
    # A year preceded by a product name is a product, not a date: "Windows
    # 2000" was flagged as an age tell on the check's first run.
    dated = re.sub(r"\b(Windows|Office|Server|Visual Studio|SQL Server)\s+(19|20)\d\d\b",
                   " ", resume)
    old_years = sorted({int(y) for y in re.findall(r"\b(19\d\d|20[0-2]\d)\b", dated)
                        if int(y) < horizon})
    tenure = re.findall(r"\b(sixteen|seventeen|eighteen|nineteen|twenty(?:-\w+)?|thirty(?:-\w+)?)\s+years\b",
                        resume, re.I)
    if old_years or tenure:
        bits = []
        if tenure:
            bits.append(f"tenure stated as {tenure[0]!r}")
        if old_years:
            bits.append(f"{len(old_years)} year(s) older than {horizon}: "
                        + ", ".join(str(y) for y in old_years))
        out.append(Finding(
            "screen-age-signal", "WARN",
            "; ".join(bits) + ". A reader can subtract. Whether to show it is a policy "
            "decision, not a gate decision; this only makes it visible."))

    # --- Required qualifications that never surface above the fold.
    if parsed_path.exists():
        parsed = json.loads(parsed_path.read_text(encoding="utf-8"))
        far = []
        for r in parsed.get("requirements", []):
            if r.get("weight") != "required" or r.get("kind") in {"credential", "tenure"}:
                continue
            want = _distinctive(r.get("text", ""))
            # A requirement counts as reachable if a few of its distinctive
            # words appear above the fold. Deliberately loose: this reports
            # placement, and a stricter rule would just report vocabulary.
            if len(want & fold_terms) < 2:
                far.append(r.get("id", "?"))
        if far:
            out.append(Finding(
                "screen-requirement-far", "WARN",
                f"{len(far)} required qualification(s) have no echo above the fold, and "
                f"88% of employers screen on exact-criteria mismatch: " + ", ".join(far[:6])))
    return out


def main(argv: list[str]) -> int:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure:
        reconfigure(encoding="utf-8", errors="replace")
    if len(argv) != 2:
        print(__doc__)
        return 2
    findings = check(Path(argv[1]))
    for f in findings:
        print(f)
    blocking = sum(1 for f in findings if f.severity == "BLOCK")
    print(f"{blocking} blocking, {len(findings) - blocking} advisory")
    return 1 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
