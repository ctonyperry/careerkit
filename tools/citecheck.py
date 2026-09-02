"""Check that what a resume says is present in the units it cites.

The hole this fills has now cost two packages. `finalize` validates the BRIEF's
selection, so a unit added as a deliberate CP2 override is invisible to it.
`crosscheck` compares documents against the JD and against each other. Neither
one opens the cited evidence and asks whether the sentence is actually in there.

Both escapes had the same shape. One package claimed React at Apple: true, author-
confirmed, and recorded on `javascript-frameworks` rather than on
`apple-xapi-library` where the claim sat. Another claimed SME on APIs
"their engineering teams built against": true, and resting on a provisional
unit that was not in the selection. To anyone holding the corpus in their head
both read as supported. To a verifier reading only the cited unit, both read as
invented, and a verifier is what a reference check is.

    python tools/citecheck.py runs/<run-dir>

Three checks:

  cite-missing-unit    a claim sheet cites a unit id that does not exist
  cite-provisional     a cited unit is provisional, or has an open verify
  cite-term-unfound    a distinctive term in a bullet appears in none of the
                       units cited for that section

What it deliberately does not do: judge meaning. A bullet can use only words
that appear in its unit and still misrepresent it, which is why the reviewer
panel exists. This catches the mechanical half, where a term entered the
document from somewhere other than the evidence.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from _paths import CORPUS, EVIDENCE  # noqa: E402

# A term is "distinctive" if it is unlikely to arrive by ordinary sentence
# construction: capitalised mid-sentence, an acronym, or carrying a digit.
ACRONYM = re.compile(r"^[A-Z][A-Za-z]*[A-Z][A-Za-z0-9]*$")
HAS_DIGIT = re.compile(r"\d")
CAPITALISED = re.compile(r"^[A-Z][a-z]{2,}$")
TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9.#+/-]*|\d[\w.%+]*")

# Words that are capitalised for reasons other than being a proper noun, or
# that belong to resume furniture rather than to any claim.
FURNITURE = {
    "The", "This", "That", "These", "Those", "Their", "There", "They",
    "A", "An", "And", "But", "For", "Not", "Now", "Then", "When", "Where",
    "Built", "Ran", "Wrote", "Owned", "Carried", "Planned", "Worked",
    "Diagnosed", "Design", "Unblocked", "Turned", "Brokered", "Windows",
    "Framework", "Currently", "Thirty", "Primary", "Sr", "Jun", "Sep", "Jan",
    "Feb", "Mar", "Apr", "May", "Jul", "Aug", "Oct", "Nov", "Dec",
}


@dataclass
class Finding:
    rule: str
    severity: str
    detail: str
    excerpt: str = ""

    def __str__(self) -> str:
        tail = f" :: {self.excerpt}" if self.excerpt else ""
        return f"{self.severity:<5} [{self.rule}] {self.detail}{tail}"


def _unit_text(unit_id: str) -> str | None:
    path = EVIDENCE / f"{unit_id}.yaml"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _unit_data(unit_id: str) -> dict:
    return yaml.safe_load((EVIDENCE / f"{unit_id}.yaml").read_text(encoding="utf-8"))


def _claim_rows(claim_sheet: str) -> list[tuple[str, str, list[str]]]:
    """(section, claim, [unit ids]) from the Bullets-to-evidence table."""
    rows = []
    for line in claim_sheet.splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[0] in {"Section", ""}:
            continue
        ids = re.findall(r"`([a-z0-9-]+)`", cells[2])
        if ids:
            rows.append((cells[0], cells[1], ids))
    return rows


def _resume_sections(resume: str) -> dict[str, list[str]]:
    """Bullets keyed by the role or section heading they sit under."""
    out: dict[str, list[str]] = {}
    current = "top"
    for line in resume.splitlines():
        s = line.strip()
        if s.startswith("### "):
            current = s[4:].strip()
        elif s.startswith("## "):
            current = s[3:].strip()
        elif s.startswith("- "):
            out.setdefault(current, []).append(s[2:].strip())
    return out


_ORG_NOISE = {"inc", "corp", "llc", "the", "and", "company", "group", "via", "contract"}


def _role_keys() -> list[tuple[str, set[str]]]:
    """(role id, org tokens) from the spine, so a heading that names an
    employer maps to the role without this file knowing any employer. Until
    2026-08-27 the employer names were a literal tuple here, which is to say
    the gate only worked for one person."""
    spine = yaml.safe_load((CORPUS / "data" / "spine.yaml").read_text(encoding="utf-8"))
    out = []
    for r in spine.get("roles", []):
        if not isinstance(r, dict) or "id" not in r:
            continue
        tokens = {t for t in re.findall(r"[a-z]{3,}", str(r.get("org", "")).lower())
                  if t not in _ORG_NOISE}
        tokens.add(r["id"].lower())
        out.append((r["id"], tokens))
    return out


_ROLE_KEYS: list[tuple[str, set[str]]] | None = None


def _section_key(heading: str) -> str:
    """Match a resume heading to a claim-sheet Section cell, loosely: the role
    whose employer name shares the most words with the heading, else a fixed
    non-role section, else the heading itself."""
    global _ROLE_KEYS
    if _ROLE_KEYS is None:
        _ROLE_KEYS = _role_keys()
    words = set(re.findall(r"[a-z0-9-]{3,}", heading.lower()))
    best, best_score = None, 0
    for role_id, tokens in _ROLE_KEYS:
        score = len(words & tokens)
        if score > best_score:
            best, best_score = role_id, score
    if best:
        return best
    h = heading.lower()
    for key in ("project", "skill", "selected", "earlier"):
        if key in h:
            return key
    return h


def _distinctive(text: str) -> set[str]:
    # Markdown emphasis is not text. A "**Label.** Sentence" bullet hid the
    # sentence boundary behind the asterisks, so the sentence's first word was
    # read as a proper noun and blocked; and until 2026-09-02 the Selected
    # Work section was never checked at all, because its heading matched no
    # claim-sheet section, so the escape had no chance to show.
    text = text.replace("*", "").replace("_", " ")
    # Sentence-initial capitals are grammar, not evidence. A bullet often runs
    # to several sentences, so "first word" means first of any sentence.
    starts = {m.end() - 1 for m in re.finditer(r"[.!?:]\s+\S", text)}
    starts.add(next((i for i, c in enumerate(text) if not c.isspace()), 0))
    terms = set()
    for m in TOKEN.finditer(text):
        w = m.group(0)
        bare = w.strip(".,;:")
        if not bare or bare in FURNITURE:
            continue
        first = m.start() in starts
        if ACRONYM.match(bare) or HAS_DIGIT.search(bare) or CAPITALISED.match(bare) and not first:
            terms.add(bare)
    return terms


def _spine_role_ids() -> set[str]:
    spine = yaml.safe_load((CORPUS / "data" / "spine.yaml").read_text(encoding="utf-8"))
    return {r["id"] for r in spine.get("roles", []) if isinstance(r, dict) and "id" in r}


def _spine_role_text(role_id: str) -> str:
    spine = yaml.safe_load((CORPUS / "data" / "spine.yaml").read_text(encoding="utf-8"))
    for r in spine.get("roles", []):
        if isinstance(r, dict) and r.get("id") == role_id:
            return yaml.safe_dump(r, allow_unicode=True)
    return ""


def check(run: Path) -> list[Finding]:
    findings: list[Finding] = []
    sheet = run / "claim-sheet.md"
    resume = run / "resume.md"
    if not sheet.exists() or not resume.exists():
        return [Finding("cite-missing-input", "BLOCK",
                        f"need claim-sheet.md and resume.md in {run}")]

    rows = _claim_rows(sheet.read_text(encoding="utf-8"))
    if not rows:
        return [Finding("cite-missing-input", "BLOCK",
                        "no Bullets-to-evidence table found in claim-sheet.md")]

    # Pool the cited evidence per section, and vet each unit as we go.
    pools: dict[str, list[str]] = {}
    seen: set[str] = set()
    for section, _, ids in rows:
        key = _section_key(section)
        for uid in ids:
            text = _unit_text(uid)
            if text is None:
                if uid in _spine_role_ids():
                    # A claim can legitimately rest on a spine role rather than
                    # an evidence unit: the compressed "Earlier" line is dates
                    # and titles, which is exactly what the spine is for.
                    pools.setdefault(key, []).append(_spine_role_text(uid))
                    continue
                findings.append(Finding("cite-missing-unit", "BLOCK",
                                        f"claim sheet cites `{uid}`, which is neither an "
                                        f"evidence unit nor a spine role"))
                continue
            pools.setdefault(key, []).append(text)
            if uid in seen:
                continue
            seen.add(uid)
            data = _unit_data(uid)
            if data.get("status") != "confirmed":
                findings.append(Finding(
                    "cite-provisional", "BLOCK",
                    f"`{uid}` is status: {data.get('status')} and is cited as settled fact"))
            if data.get("verify"):
                findings.append(Finding(
                    "cite-provisional", "WARN",
                    f"`{uid}` has {len(data['verify'])} open verify item(s)",
                    str(data["verify"][0])[:90]))

    # Everything the spine and the conventions file legitimately supply.
    ground = "\n".join([
        (CORPUS / "data" / "spine.yaml").read_text(encoding="utf-8"),
        (CORPUS / "career-data.md").read_text(encoding="utf-8"),
    ])

    for heading, bullets in _resume_sections(resume.read_text(encoding="utf-8")).items():
        key = _section_key(heading)
        pool = "\n".join(pools.get(key, []))
        if not pool:
            continue
        haystack = (pool + ground).lower()
        for bullet in bullets:
            for term in sorted(_distinctive(bullet)):
                low = term.lower()
                # A plural is the same claim as its singular. "RFPs" against a
                # unit saying "the RFP stage" is a false positive, and a gate
                # that cries wolf gets waved through.
                variants = {low, low.rstrip("s"), low + "s"}
                if any(v and v in haystack for v in variants):
                    continue
                if low not in haystack:
                    findings.append(Finding(
                        "cite-term-unfound", "BLOCK",
                        f"'{term}' appears in no unit cited for {heading!r}",
                        bullet[:80]))
    return findings


def main(argv: list[str]) -> int:
    # Findings quote the documents, which carry arrows, middots and accents.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(argv) != 2:
        print(__doc__)
        return 2
    findings = check(Path(argv[1]))
    for f in findings:
        print(f)
    blocking = sum(1 for f in findings if f.severity == "BLOCK")
    advisory = len(findings) - blocking
    print(f"{blocking} blocking, {advisory} advisory")
    return 1 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
