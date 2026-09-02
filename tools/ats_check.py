"""ATS readiness, checked against what applicant tracking systems actually do.

    python tools/ats_check.py runs/<run-dir>

## What the research says, because it changes the target

The widely repeated claim that ATS auto-reject 75% of resumes traces to a 2012
sales pitch by Preptel, a company that folded in 2013 and never published a
methodology. A 2026 survey of recruiters found 92% say their systems do NOT
automatically reject on formatting, design, missing keywords, or a low AI match
score. Greenhouse in particular does not algorithmically score resumes at all;
it parses them into fields and routes them to human scorecards.

So optimising for a rejection algorithm is optimising against something that
mostly is not there. Two mechanisms are real:

1. **Recruiter boolean FULL-TEXT search.** Greenhouse's own documentation
   describes boolean queries and a Full Text Search toggle over the text of
   resumes and internal notes: "you can search for job titles, skills,
   locations, and other keywords". Note what that is and is not. It is search
   over the document text, not a filter on a structured title field, and
   Greenhouse's documented filters are a different feature entirely
   (prospects, rejected applications, closed jobs). Their docs rank nothing:
   titles, skills and locations are listed together.

   So the target is being FINDABLE in full text. A term that never appears
   cannot be matched, whatever field a reader might imagine it living in. At
   400 to 2000+ applicants, search is used to order the review queue rather
   than to reject, but if a reviewer only opens the hits, the practical effect
   on everyone else is similar. That is a reason to be findable, not a reason
   to believe in an auto-rejecter.

2. **Criteria filters applied by people.** Harvard Business School and
   Accenture found 88% of employers agree qualified candidates are screened out
   for not matching exact job-description criteria, and 49% of companies
   eliminate candidates with an employment gap of six months or more. Those are
   human policies executed through the tool, and a gap is worth knowing about
   before someone else finds it.

## What this tool therefore checks

  ats-parse-risk      characters and structures that break field extraction
  ats-term-missing    a searchable JD noun absent from the resume, SPLIT by
                      whether the corpus can support it
  ats-title-absent    the JD's job title appears nowhere in the resume text,
                      so a full-text search for it cannot match
  ats-employment-gap  a spine gap of six months or more, which nearly half of
                      employers filter on

The split on ats-term-missing is the whole point. A term the corpus supports is
a legitimate win: the evidence is there and the document happened to use a
different synonym. A term the corpus does not support is a fabrication with a
keyword rationale, and this tool will never recommend adding one. That boundary
is the same one crosscheck's jd-trace rule enforces.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from _paths import CORPUS, EVIDENCE  # noqa: E402

# Separators and glyphs that survive a modern parser inconsistently. The risk
# is concentrated in the contact block and the title line, which are the two
# fields an ATS extracts into structured columns and a recruiter searches on.
RISKY_GLYPHS = {"\u2192": "right arrow", "\u2014": "em dash", "\u2013": "en dash",
                "\u2022": "bullet char", "\t": "tab"}

# Section headings parsers are trained to recognise. Inventive headings are a
# real cost here: content under an unrecognised heading may not land in a field.
STANDARD_HEADINGS = {
    "experience", "work experience", "professional experience", "employment",
    "education", "skills", "technical skills", "certifications", "projects",
    "summary", "professional summary", "current work",
}

STOP = set(["a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "had", "has", "have", "in", "into", "is", "it", "its", "of", "on", "or", "that", "the", "their", "them", "then", "there", "these", "they", "this", "to", "was", "were", "with", "which", "who", "our", "we", "you", "your", "i", "will", "not", "can", "do", "does", "what", "how", "when", "where", "all", "any", "more", "most", "us", "able", "about", "across", "also", "been", "being", "both", "each", "other", "than", "very", "your", "you'll", "they're", "we're", "it's", "role", "roles", "job", "jobs", "work", "working", "team", "teams", "company", "companies", "help", "helps", "make", "makes", "turn", "turns", "every", "person", "people", "new", "alongside", "understand", "understanding", "actually", "own", "owns", "real", "especially", "familiarity", "familiar", "serve", "serves", "success", "ideally", "comfortable", "strong", "required", "preferred", "nice", "including", "include", "includes", "experience", "experienced", "ability", "able"])


@dataclass
class Finding:
    rule: str
    severity: str
    detail: str

    def __str__(self) -> str:
        return f"{self.severity:<5} [{self.rule}] {self.detail}"


def _corpus_text() -> str:
    parts = [p.read_text(encoding="utf-8", errors="replace") for p in EVIDENCE.glob("*.yaml")]
    for extra in ((CORPUS / "data" / "spine.yaml"), (CORPUS / "career-data.md")):
        if extra.exists():
            parts.append(extra.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts).lower()


def _searchable_terms(parsed: dict) -> list[str]:
    """Nouns a recruiter would type into a search box.

    Read from the PARSED requirements and unknown_terms, never the raw posting.
    The first version scanned the whole JD and dutifully reported that the
    resume was missing "Intelligems", "Ventures" and "Fred", which come from
    the About-the-company section and the investor list. Nobody searches a
    candidate pipeline for the founder's first name. Requirements are where the
    hiring criteria live, so that is the only text worth scanning.
    """
    jd_text = "\n".join(
        [r.get("text", "") for r in parsed.get("requirements", [])]
        + list(parsed.get("unknown_terms", []))
    )
    terms: dict[str, int] = {}
    for m in re.finditer(r"[A-Za-z][A-Za-z0-9+#./-]{2,}", jd_text):
        w = m.group(0)
        low = w.lower().strip(".")
        if low in STOP or len(low) < 3:
            continue
        proper = w[0].isupper() and m.start() > 0 and jd_text[m.start() - 2 : m.start()] not in {". ", "* ", "\n\n"}
        acronym = w.isupper() and len(w) > 1
        compound = any(c in w for c in "/+#-.") and not w.islower()
        if proper or acronym or compound:
            terms[low] = terms.get(low, 0) + 1
    return [t for t, c in sorted(terms.items(), key=lambda x: -x[1]) if c >= 2]


MONTH_WORDS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
# The spine records real human dates: "Summer 1998", "Early 2000", "~2018".
# Dropping what will not parse is the worst option for a gap detector, because
# a dropped role reads as unemployment. The first version did exactly that and
# reported a phantom 156-month gap by losing two roles.
VAGUE = {"early": 2, "spring": 4, "mid": 6, "summer": 7, "fall": 10,
         "autumn": 10, "late": 11, "winter": 1}


def _to_months(v, *, is_start: bool) -> int | None:
    """Calendar position in months, read CONSERVATIVELY.

    A bare year as a start means January, as an end means December: the widest
    plausible span. Widening spans shrinks computed gaps, so this reports only
    gaps that must exist rather than gaps an imprecise date could imply.
    """
    s = str(v).strip().lower().lstrip("~")
    m = re.match(r"([a-z]+)\.?\s+(\d{4})", s)
    if m:
        word, year = m.group(1)[:3], int(m.group(2))
        if word in MONTH_WORDS:
            return year * 12 + MONTH_WORDS[word]
        full = m.group(1)
        if full in VAGUE:
            return year * 12 + VAGUE[full]
    m = re.match(r"(\d{4})$", s)
    if m:
        return int(m.group(1)) * 12 + (1 if is_start else 12)
    return None


def _spine_gaps(min_months: int = 6) -> list[str]:
    """Uncovered stretches in the employment timeline.

    Merges intervals rather than walking consecutive pairs, because roles
    overlap (the 2018 accelerator sits inside other spans) and a pairwise scan
    reports overlap as a gap.
    """
    spine = yaml.safe_load((CORPUS / "data" / "spine.yaml").read_text(encoding="utf-8"))
    spans: list[tuple[int, int, str]] = []
    unparsed: list[str] = []
    for r in spine.get("roles", []):
        if not isinstance(r, dict):
            continue
        a = _to_months(r.get("start"), is_start=True)
        b = _to_months(r.get("end"), is_start=False)
        if a and b:
            spans.append((a, b, str(r.get("id", "?"))))
        else:
            unparsed.append(str(r.get("id", "?")))
    if not spans:
        return []
    spans.sort()
    # Each merged block keeps the role it STARTS with and the role it ENDS
    # with, so a gap can name the two roles actually either side of it.
    merged: list[list] = [[spans[0][0], spans[0][1], spans[0][2], spans[0][2]]]
    for a, b, rid in spans[1:]:
        if a <= merged[-1][1] + 1:
            if b >= merged[-1][1]:
                merged[-1][1], merged[-1][3] = b, rid
        else:
            merged.append([a, b, rid, rid])
    out = []
    for prev, nxt in zip(merged, merged[1:], strict=False):
        gap = nxt[0] - prev[1]
        if gap >= min_months:
            out.append(f"{gap} months between the end of {prev[3]} and the start of {nxt[2]}")
    if unparsed:
        out.append(f"NOT SCORED, unparseable dates on: {', '.join(unparsed)}")
    return out


def check(run: Path) -> list[Finding]:
    findings: list[Finding] = []
    resume_path = run / "resume.md"
    if not resume_path.exists():
        return [Finding("ats-missing-input", "BLOCK", f"no resume.md in {run}")]
    resume = resume_path.read_text(encoding="utf-8")
    low = resume.lower()

    # 1. Parse risk. Weighted to where it costs: contact block and role titles.
    lines = resume.splitlines()
    contact = next((ln for ln in lines[:8] if "@" in ln), "")
    for glyph, name in RISKY_GLYPHS.items():
        if glyph in contact:
            findings.append(Finding("ats-parse-risk", "BLOCK",
                                    f"{name} in the contact line, which is the block an ATS "
                                    f"extracts into name/email/phone fields"))
        elif glyph in resume:
            where = [ln.strip()[:60] for ln in lines if glyph in ln][:1]
            sev = "WARN" if not any(ln.startswith("###") for ln in lines if glyph in ln) else "BLOCK"
            findings.append(Finding("ats-parse-risk", sev,
                                    f"{name} present{' in a role title line' if sev == 'BLOCK' else ''}"
                                    f": {where[0] if where else ''}"))

    for ln in lines:
        if ln.startswith("## "):
            h = ln[3:].strip().lower()
            if h not in STANDARD_HEADINGS:
                findings.append(Finding("ats-parse-risk", "WARN",
                                        f"non-standard section heading {h!r}; content under an "
                                        f"unrecognised heading may not land in a parsed field"))

    # 2. Searchable-term coverage, split by whether the corpus can back it.
    parsed = run / "jd-parsed.json"
    if parsed.exists():
        parsed_jd = json.loads(parsed.read_text(encoding="utf-8"))
        corpus = _corpus_text()
        supported, unsupported = [], []
        for term in _searchable_terms(parsed_jd):
            if term in low:
                continue
            (supported if term in corpus else unsupported).append(term)
        if supported:
            findings.append(Finding(
                "ats-term-missing", "WARN",
                "absent from the resume BUT supported by the corpus, so using their "
                "word is legitimate: " + ", ".join(supported[:12])))
        if unsupported:
            findings.append(Finding(
                "ats-term-missing", "INFO",
                "absent and unsupported by the corpus. Do not add these; they are "
                "the gap, not an oversight: " + ", ".join(unsupported[:12])))

        # 3. Title. Recruiters search titles first.
        title = parsed_jd.get("title_to_mirror", "")
        if title and title.lower() not in low:
            head = [w for w in title.lower().split() if w not in STOP]
            if not all(w in low for w in head):
                findings.append(Finding("ats-title-absent", "WARN",
                                        f"the target title {title!r} appears nowhere in the "
                                        f"resume text, so a full-text search for it cannot "
                                        f"match. Not a ranking claim: titles are one of several "
                                        f"things searched, alongside skills and tools"))

    # 4. Employment gaps. Nearly half of employers filter on six months or more.
    for gap in _spine_gaps():
        findings.append(Finding("ats-employment-gap", "INFO",
                                f"{gap}. 49% of companies filter on gaps of 6+ months "
                                f"(HBS/Accenture). Know it before they raise it."))
    return findings


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
    warn = sum(1 for f in findings if f.severity == "WARN")
    print(f"{blocking} blocking, {warn} advisory, "
          f"{len(findings) - blocking - warn} informational")
    return 1 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
