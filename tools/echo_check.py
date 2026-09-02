"""Repetition and sentence-shape density: what five blind critics all said.

    python tools/echo_check.py runs/<run-dir>

On 2026-08-26 the writing critic read all five packages, blind, one per
package, with no knowledge of each other. Three complaints came back from
nearly every one of them, which is what separates a rule from an opinion:

  1. The same fact is stated in the tagline, the summary, the role heading,
     the italic subtitle, AND the first bullet. Five of five packages. One
     critic counted an employer named four times inside four lines; another
     found a role subtitle that was a verbatim copy of the summary sentence
     eighteen lines above it.
  2. Colon-then-enumeration is the default sentence. Five of five. "Once it is
     a device; five times it is a template, and the reader stops registering
     what follows the colon as an argument."
  3. Doubled-verb openers where the second verb never earns its place:
     "Built and shipped", "Planned and delivered", "Scoped and built".

All three are counting problems, so they belong in a tool rather than in a
reviewer's patience. None of them is about truth, and none can block: a
document may legitimately repeat, and the threshold is a judgment. They are
reported as densities so a drift is visible before a reader has to name it.

What this cannot see: whether a repetition is deliberate emphasis. That is
still the reader's call, which is why every finding names the location.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

STOP = set(["a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "had", "has", "have", "in", "into", "is", "it", "its", "of", "on", "or", "that", "the", "their", "them", "then", "there", "these", "they", "this", "to", "was", "were", "with", "which", "who", "our", "we", "you", "your", "i", "not", "can", "do", "does", "what", "how", "when", "where", "all", "any", "more", "most", "us", "able", "about", "across", "also", "been", "being", "both", "each", "other", "than", "very", "own", "real"])

# The second verb in these pairs restates the first. A person picks one.
DOUBLED_VERB = re.compile(
    r"^(built and shipped|planned and delivered|scoped and built|designed and built"
    r"|built and delivered|created and launched|developed and deployed"
    r"|managed and maintained|led and delivered)\b",
    re.I,
)


@dataclass
class Finding:
    rule: str
    severity: str
    detail: str

    def __str__(self) -> str:
        return f"{self.severity:<5} [{self.rule}] {self.detail}"


def _phrases(text: str, n: int = 3) -> set[str]:
    """Content n-grams, stopwords stripped, so only substantive repeats count."""
    words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9'/-]*", text)]
    words = [w for w in words if w not in STOP]
    return {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}


def _split(resume: str) -> tuple[list[str], list[str]]:
    """(furniture, bullets). Furniture is everything a reader meets before the
    evidence: the tagline, the summary, role headings and italic subtitles."""
    furniture, bullets = [], []
    # The skills line and education block are deliberately redundant with the
    # bullets: Tony calls the skills line keyword insurance, and it is there to
    # be searched, not read. Counting their echoes would flag the one repetition
    # that is doing its job.
    skip = False
    for line in resume.splitlines():
        s = line.strip()
        if s.startswith("## "):
            skip = s[3:].strip().lower() in {"technical skills", "skills", "education"}
        if skip or not s or s.startswith("# ") or "@" in s:
            continue
        if s.startswith("- ") or s.startswith("* "):
            bullets.append(s[2:])
        elif s.startswith("#") or s.startswith("**") or (s.startswith("*") and s.endswith("*")):
            furniture.append(s.strip("#*").strip())
        else:
            furniture.append(s)
    return furniture, bullets


def check(run: Path) -> list[Finding]:
    out: list[Finding] = []
    rp = run / "resume.md"
    if not rp.exists():
        return [Finding("echo-missing-input", "BLOCK", f"no resume.md in {run}")]
    resume = rp.read_text(encoding="utf-8")
    furniture, bullets = _split(resume)

    # 1. A fact stated in the furniture and again in a bullet.
    furn_phrases: dict[str, str] = {}
    for f in furniture:
        for p in _phrases(f):
            furn_phrases.setdefault(p, f)
    echoed: dict[str, tuple[str, str]] = {}
    for b in bullets:
        for p in _phrases(b):
            if p in furn_phrases:
                echoed[p] = (furn_phrases[p], b)
    if echoed:
        for p, (f, b) in list(echoed.items())[:4]:
            out.append(Finding(
                "echo-restated", "WARN",
                f'"{p}" appears in the furniture and again in a bullet. '
                f'Furniture: "{f[:56]}". Bullet: "{b[:56]}"'))
        if len(echoed) > 4:
            out.append(Finding("echo-restated", "WARN",
                               f"{len(echoed) - 4} further restated phrase(s) not listed"))

    # 2. Colon-then-enumeration density.
    colon_lists = [b for b in bullets if re.search(r":\s+\w+.*,", b)]
    if len(colon_lists) >= 3:
        out.append(Finding(
            "echo-colon-default", "WARN",
            f"{len(colon_lists)} of {len(bullets)} bullets use colon-then-list. Once it is a "
            f"device, repeatedly it is a template and the reader stops reading past the colon."))

    # 3. Doubled-verb openers.
    doubled = [b for b in bullets if DOUBLED_VERB.match(b.strip())]
    if doubled:
        out.append(Finding(
            "echo-doubled-verb", "WARN",
            f"{len(doubled)} bullet(s) open on a verb pair whose second verb restates the "
            f"first: " + "; ".join(b.split(",")[0][:38] for b in doubled[:3])))

    # 4. Repeated furniture phrases: the same idea worded three ways.
    seen: dict[str, int] = {}
    for f in furniture:
        for p in _phrases(f, 2):
            seen[p] = seen.get(p, 0) + 1
    thrice = [p for p, c in seen.items() if c >= 3]
    if thrice:
        out.append(Finding(
            "echo-furniture", "WARN",
            "phrase(s) repeated three or more times across tagline, summary and "
            "headings: " + ", ".join(sorted(thrice)[:5])))
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
    print(f"{len(findings)} advisory")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
