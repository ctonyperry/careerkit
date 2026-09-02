"""Mechanical resume linter: deterministic, mostly blocking.

The house-style lane from implementation-design.md. Objective rules BLOCK; the
one inherently fuzzy rule (rhythm) only WARNs rather than risk blocking a good
resume on a heuristic. The semantic lane (atmosphere-poses, defensive framing)
is advisory and lives in prompts/resume-critique.md, not here.

Blocking rules:
- em dashes (en dashes in date ranges are fine),
- banned puffery / filler phrases,
- self-rating phrases,
- tricolons in PROSE (resume bullets are the scope-of-work exception),
- numbers with no source unit and no [VERIFY],
- education that does not trace to the spine (the hallucinated-diploma guard).

Advisory (WARN) rules:
- rhythm (every sentence in a bullet is long),
- jd-mirroring: the summary paraphrases the JD back at the reader instead of
  telling the career's trajectory. Advisory because the line between "grounded
  in the same domain" and "parroting the posting" is a judgment call.
"""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel

from careerkit.jd import ParsedJD
from careerkit.models import EvidenceUnit, Spine

EM_DASH = "—"

BANNED_PHRASES = (
    "results-driven",
    "results driven",
    "proven track record",
    "track record of success",
    "detail-oriented",
    "team player",
    "hard-working",
    "hard worker",
    "self-starter",
    "go-getter",
    "think outside the box",
    "synergy",
    "world-class",
    "best-in-class",
    "rockstar",
    "ninja",
    "wear many hats",
)

SELF_RATING = (
    "expert in",
    "expert-level",
    "expert level",
    "guru",
    "highly skilled",
    "highly proficient",
    "passionate about",
    "seasoned",
    "extensive experience",
)

# Casting yourself in a role rather than describing what you did. Distinct from
# self-rating: "expert in X" claims a level, "the technical voice" claims a
# part. Three blind reviewers flagged "the technical voice" across three
# packages on 2026-08-26, and the author agreed. The actions underneath always say it
# better, because a reader who concludes it trusts it.
SELF_CASTING = (
    "the technical voice",
    "the go-to",
    "go-to person",
    "the person who",
    "the one who",
    "trusted advisor",
    "thought leader",
)

# A superlative standing in for a figure. Flagged in four packages on
# 2026-08-26: "at a scale the platform had never handled" sits in bullets that
# elsewhere give real numbers freely, which is what makes the one withheld
# number conspicuous. Either the figure is available, in which case use it, or
# it is not, in which case the clause is asserting importance rather than
# reporting.
# Bare "at a scale" was in this list and fired on "at a scale of roughly two
# million users", which carries the figure the rule exists to demand. The
# first negative fixture in the defect corpus caught it. The boast is the
# superlative, so only superlatives are listed.
SCALE_BOAST = (
    "at a scale the platform had never",
    "at a scale the platform had not",
    "at a scale nobody had",
    "never handled before",
    "had never seen before",
    "had not handled before",
    "unprecedented scale",
    "like never before",
)

# Formal or archaic registers in prose that is otherwise flat and American.
# "Latterly" was flagged in two packages as a spike into legal-brief English.
REGISTER_SPIKE = (
    "latterly",
    "heretofore",
    "aforementioned",
    "utilise",
    "whilst",
    "amongst",
    "endeavoured",
)

# Credentials a model tends to hallucinate for non-traditional paths.
_CREDENTIAL_WORDS = (
    "bachelor",
    "master",
    "b.s.",
    "b.a.",
    "m.s.",
    "m.b.a.",
    "mba",
    "associate degree",
    "diploma",
    "doctorate",
    "ph.d",
    "phd",
)

_BULLET_RE = re.compile(r"^\s*[-*•●]\s+")
_HEADING_RE = re.compile(r"^\s*#{1,6}\s+|^[A-Z][A-Z &]{3,}$")
_TRICOLON_RE = re.compile(r",[^,]+,\s*and\s", re.IGNORECASE)
_VERIFY_RE = re.compile(r"\[VERIFY\]", re.IGNORECASE)
# Claim numbers: a figure carrying a magnitude/unit/plus, i.e. a metric rather
# than a bare year. These are the fabrication risk. Letter units need a word
# boundary (so "months" is not read as "m"); % and + do not.
_CLAIM_NUMBER_RE = re.compile(
    r"\$?~?\d[\d,\.]*\s?(?:kb|mb|gb|million|billion|thousand|k|m|b|x)\b"
    r"|\$?~?\d[\d,\.]*%"
    r"|\d[\d,\.]*\+",
    re.IGNORECASE,
)


# Tenure claims: "31 years", "15+ years", "six years", "thirty-one years".
# These are the characteristic hallucination of this system. A fabricated
# aggregate feels like arithmetic rather than a claim, so it slips past the
# instinct to check a source, and _CLAIM_NUMBER_RE deliberately exempts bare
# years so nothing else catches it. Two shipped on 2026-08-24.
_WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "thirty": 30, "forty": 40, "fifty": 50,
}
for _tens, _tv in (("twenty", 20), ("thirty", 30), ("forty", 40), ("fifty", 50)):
    for _ones, _ov in list(_WORD_NUMBERS.items())[:9]:
        _WORD_NUMBERS[f"{_tens}-{_ones}"] = _tv + _ov

_TENURE_RE = re.compile(
    r"\b(\d{1,2})\s*\+?\s*(?:\+|plus)?\s*(?:years?|yrs?)\b"
    r"|\b([a-z]+(?:-[a-z]+)?)\s+(?:years?|yrs?)\b",
    re.IGNORECASE,
)


# Harvard, Yale and MIT all give the same first rule: a bullet opens with an
# action verb. A bullet that opens with an article is a noun phrase instead,
# and noun-phrase openers are where clumsy compression breeds: "The API
# subject-matter expert customer engineering teams built against" drops its
# relative pronoun and garden-paths the reader through "expert customer".
# WARN, not BLOCK: "A $10M program reaching ~2M users" is a deliberate,
# defensible front-load of the number.
_ARTICLE_OPENER_RE = re.compile(r"^\s*[-*•●]\s+(the|a|an)\b", re.IGNORECASE)


class Severity(StrEnum):
    BLOCK = "BLOCK"
    WARN = "WARN"


class Finding(BaseModel):
    rule: str
    severity: Severity
    line: int
    excerpt: str
    message: str


def _norm_number(token: str) -> str:
    return re.sub(r"[\s,~$]", "", token).lower()


def _is_bullet(line: str) -> bool:
    return bool(_BULLET_RE.match(line))


def _is_heading(line: str) -> bool:
    return bool(_HEADING_RE.match(line.strip()))


def _source_numbers(units: list[EvidenceUnit], spine: Spine) -> set[str]:
    blob: list[str] = []
    for u in units:
        blob.append(u.narrative)
        if u.car:
            blob += [u.car.challenge or "", u.car.action or "", u.car.result or ""]
        blob += [m.value for m in u.metrics if not m.doubted]
    for role in spine.roles:
        blob += [role.start, role.end]
    numbers: set[str] = set()
    for text in blob:
        for m in _CLAIM_NUMBER_RE.findall(text):
            numbers.add(_norm_number(m))
    return numbers


def _check_line_phrases(line: str, lineno: int) -> list[Finding]:
    findings: list[Finding] = []
    low = line.lower()
    if EM_DASH in line:
        findings.append(
            Finding(
                rule="em-dash",
                severity=Severity.BLOCK,
                line=lineno,
                excerpt=line.strip(),
                message="Em dash is banned house style. Use a comma, colon, or split the sentence.",
            )
        )
    for phrase in BANNED_PHRASES:
        if phrase in low:
            findings.append(
                Finding(
                    rule="banned-phrase",
                    severity=Severity.BLOCK,
                    line=lineno,
                    excerpt=phrase,
                    message=f"Filler/puffery phrase '{phrase}'. Replace with a concrete action.",
                )
            )
    for phrase in SELF_RATING:
        if phrase in low:
            findings.append(
                Finding(
                    rule="self-rating",
                    severity=Severity.BLOCK,
                    line=lineno,
                    excerpt=phrase,
                    message=f"Self-rating phrase '{phrase}'. Let the evidence rate you.",
                )
            )
    for phrase in SELF_CASTING:
        if phrase in low:
            findings.append(
                Finding(
                    rule="self-casting",
                    severity=Severity.BLOCK,
                    line=lineno,
                    excerpt=phrase,
                    message=(
                        f"'{phrase}' casts a role instead of describing an action. "
                        "Name what was done and let the reader assign the role."
                    ),
                )
            )
    for phrase in SCALE_BOAST:
        if phrase in low:
            findings.append(
                Finding(
                    rule="scale-boast",
                    severity=Severity.BLOCK,
                    line=lineno,
                    excerpt=phrase,
                    message=(
                        f"'{phrase}' is a superlative standing in for a number. "
                        "Give the figure, or cut the clause."
                    ),
                )
            )
    for phrase in REGISTER_SPIKE:
        if phrase in low:
            findings.append(
                Finding(
                    rule="register-spike",
                    severity=Severity.WARN,
                    line=lineno,
                    excerpt=phrase,
                    message=(
                        f"'{phrase}' is a register spike in otherwise plain prose. "
                        "Use the ordinary word."
                    ),
                )
            )
    if _ARTICLE_OPENER_RE.match(line):
        findings.append(
            Finding(
                rule="bullet-opener",
                severity=Severity.WARN,
                line=lineno,
                excerpt=line.strip()[:60],
                message=(
                    "Bullet opens with an article, so it leads with a noun phrase "
                    "rather than the action. Lead with the verb, or keep the "
                    "noun opener deliberately (a front-loaded number can earn it)."
                ),
            )
        )
    if not _is_bullet(line) and not _is_heading(line) and _TRICOLON_RE.search(line):
        # WARN, not BLOCK: distinguishing a slop tricolon from a legitimate
        # rhetorical sentence is not mechanical (the approved FINAL summary is a
        # three-part sentence). Flag for a human look; never block on it.
        findings.append(
            Finding(
                rule="tricolon",
                severity=Severity.WARN,
                line=lineno,
                excerpt=line.strip(),
                message="Possible three-item list in prose. Fine if scope-of-work; check for slop.",
            )
        )
    return findings


def _check_numbers(line: str, lineno: int, allowed: set[str]) -> list[Finding]:
    if _VERIFY_RE.search(line):
        return []
    findings: list[Finding] = []
    for token in _CLAIM_NUMBER_RE.findall(line):
        if _norm_number(token) not in allowed:
            findings.append(
                Finding(
                    rule="number-without-source",
                    severity=Severity.BLOCK,
                    line=lineno,
                    excerpt=token.strip(),
                    message=(
                        f"Figure '{token.strip()}' is in no source unit. Source it or "
                        "mark it [VERIFY]; never fabricate a metric."
                    ),
                )
            )
    return findings


def _spine_spans(spine: Spine) -> set[int]:
    """Every tenure figure the timeline can actually justify.

    Two shapes are legitimate: the whole career, and one role.

    A third family, role-start through to the present, was removed on
    2026-08-25 after the defect corpus caught it permitting the very figure the
    rule exists to block: AthenaOnline started in 2011, so 2026 minus 2011 made
    "fifteen years of customer-facing consulting" computable. Any span crossing
    role boundaries is an aggregate someone summed by hand.
    """
    starts = [y for r in spine.roles if (y := r.start_year()) is not None]
    ends = [y for r in spine.roles if (y := r.end_year()) is not None]
    if not starts or not ends:
        return set()
    newest, oldest = max(ends), min(starts)

    spans: set[int] = set()

    def add(value: int) -> None:
        # Accept the floor and ceiling: a role running Jun 2019 to Sep 2025 is
        # honestly "six years" and defensibly "seven".
        spans.update({value, value + 1})

    add(newest - oldest)
    for role in spine.roles:
        start, end = role.start_year(), role.end_year()
        if start is None or end is None:
            continue
        add(end - start)
    return spans


def _tenure_numbers(line: str) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for match in _TENURE_RE.finditer(line):
        digits, word = match.group(1), match.group(2)
        if digits:
            out.append((match.group(0).strip(), int(digits)))
        elif word and word.lower() in _WORD_NUMBERS:
            out.append((match.group(0).strip(), _WORD_NUMBERS[word.lower()]))
    return out


def _check_tenure(
    line: str, lineno: int, spans: set[int], sourced: set[int]
) -> list[Finding]:
    findings: list[Finding] = []
    for excerpt, value in _tenure_numbers(line):
        if value in spans or value in sourced:
            continue
        findings.append(
            Finding(
                rule="tenure-not-computed",
                severity=Severity.BLOCK,
                line=lineno,
                excerpt=excerpt,
                message=(
                    f"'{excerpt}' matches no span the spine can compute and no "
                    "source unit. Tenure is computed from the timeline or it is "
                    f"absent. Computable spans: {sorted(spans)}."
                ),
            )
        )
    return findings


def _sourced_tenures(units: list[EvidenceUnit]) -> set[int]:
    """Tenure figures a unit itself carries (e.g. '~4 years as Microsoft's
    go-to API contact'), which are claims about a relationship rather than a
    spine role and are legitimately quotable."""
    out: set[int] = set()
    for unit in units:
        text = " ".join(
            [unit.narrative, *(m.value for m in unit.metrics), *unit.render_notes]
        )
        for _, value in _tenure_numbers(text):
            out.update({value, value + 1})
    return out


def _check_do_not_print(
    line: str, lineno: int, protected: dict[str, str]
) -> list[Finding]:
    """Strings the corpus marks as never-send, whatever else says otherwise."""
    findings: list[Finding] = []
    lowered = line.lower()
    for phrase, unit_id in protected.items():
        if phrase.lower() in lowered:
            findings.append(
                Finding(
                    rule="do-not-print",
                    severity=Severity.BLOCK,
                    line=lineno,
                    excerpt=phrase,
                    message=(
                        f"'{phrase}' is marked do_not_print on `{unit_id}`. See "
                        "that unit's render notes for why; do not override here."
                    ),
                )
            )
    return findings


def _protected_phrases(units: list[EvidenceUnit]) -> dict[str, str]:
    return {p: u.id for u in units for p in u.do_not_print if p.strip()}


def _education_lines(lines: list[str]) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    in_section = False
    for i, line in enumerate(lines, 1):
        if _is_heading(line):
            in_section = "education" in line.lower()
            continue
        if in_section and line.strip():
            out.append((i, line))
    return out


def _check_education(lines: list[str], spine: Spine) -> list[Finding]:
    if spine.education is None:
        return []
    spine_blob = " ".join(spine.education.items).lower()
    findings: list[Finding] = []
    for lineno, line in _education_lines(lines):
        low = line.lower()
        for word in _CREDENTIAL_WORDS:
            if word in low and word not in spine_blob:
                findings.append(
                    Finding(
                        rule="education-not-in-spine",
                        severity=Severity.BLOCK,
                        line=lineno,
                        excerpt=line.strip(),
                        message=(
                            f"Credential '{word}' is not in the spine's education. The "
                            "education section renders verbatim; never invent a credential."
                        ),
                    )
                )
    return findings


# Words too common to signal that a summary is echoing the posting.
_STOPWORDS = frozenset(
    (
        "a", "above", "across", "after", "again", "all", "an", "and", "any", "are",
        "as", "at", "be", "been", "before", "being", "below", "both", "but", "by",
        "can", "did", "do", "does", "done", "down", "during", "each", "few", "for",
        "from", "further", "had", "has", "have", "he", "her", "here", "his", "how",
        "i", "if", "in", "into", "is", "it", "its", "made", "make", "makes", "may",
        "might", "more", "most", "must", "no", "not", "of", "off", "on", "once",
        "only", "or", "other", "our", "out", "over", "own", "same", "shall", "she",
        "should", "so", "some", "such", "than", "that", "the", "their", "them", "then",
        "there", "these", "they", "this", "those", "through", "to", "under", "up",
        "us", "very", "via", "was", "we", "were", "what", "when", "where", "which",
        "who", "whom", "why", "will", "with", "would", "you", "your",
    )
)

# Generic resume/business vocabulary: shared with any JD, so not evidence of
# mirroring on its own.
_GENERIC = frozenset(
    (
        "ability", "able", "business", "client", "clients", "companies", "company",
        "customer", "customers", "experience", "include", "includes", "including",
        "new", "product", "products", "role", "skill", "skills", "strong", "team",
        "teams", "technical", "technologies", "technology", "user", "users", "work",
        "working", "works", "year", "years",
    )
)


def _content_words(text: str) -> set[str]:
    words = re.findall(r"[a-z][a-z-]{2,}", text.lower())
    return {w for w in words if w not in _STOPWORDS and w not in _GENERIC}


def _summary_lines(lines: list[str]) -> list[tuple[int, str]]:
    """Prose lines before the first section heading, excluding name/contact/title.

    The summary is structurally the riskiest line on a resume: it is the only
    place with no evidence unit anchoring it. Two failure modes live here.
    Atmosphere is one (handled by the semantic lane). Mirroring the JD is the
    other, and it is what this finds.

    Two header layouts ship, and both must be read. The original puts the
    summary in the preamble (name, title, contact, then prose). The newer one
    puts it under an explicit "## Summary" heading; scanning only the preamble
    there stopped at the heading and checked nothing, so jd-mirroring silently
    never ran on those resumes.
    """
    out: list[tuple[int, str]] = []
    in_summary_section = False
    for lineno, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith("## "):
            # Enter an explicit Summary section; any other section ends the scan.
            in_summary_section = s.lower().lstrip("# ").startswith("summary")
            if not in_summary_section and out:
                break
            continue
        if not s or s.startswith("#") or _is_bullet(line):
            continue
        if s.startswith("**") and s.endswith("**"):  # the title-mirror line
            continue
        if "@" in s or "·" in s:  # contact line
            continue
        out.append((lineno, s))
    return out


# How many distinctive JD words a summary may share before it reads as an echo.
JD_MIRROR_THRESHOLD = 5


def _check_jd_mirroring(lines: list[str], jd: ParsedJD | None) -> list[Finding]:
    if jd is None:
        return []
    jd_words = _content_words(" ".join(r.text for r in jd.requirements))
    findings: list[Finding] = []
    for lineno, line in _summary_lines(lines):
        shared = sorted(_content_words(line) & jd_words)
        if len(shared) >= JD_MIRROR_THRESHOLD:
            findings.append(
                Finding(
                    rule="jd-mirroring",
                    severity=Severity.WARN,
                    line=lineno,
                    excerpt=line[:60],
                    message=(
                        "Summary echoes the JD ("
                        + ", ".join(shared[:6])
                        + "). The bullets already argue fit; the summary should "
                        "tell the career's trajectory instead."
                    ),
                )
            )
    return findings


def _check_rhythm(lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for lineno, line in enumerate(lines, 1):
        if not _is_bullet(line):
            continue
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", line) if s.strip()]
        long = [s for s in sentences if len(s.split()) > 22]
        if len(sentences) >= 3 and len(long) == len(sentences):
            findings.append(
                Finding(
                    rule="rhythm",
                    severity=Severity.WARN,
                    line=lineno,
                    excerpt=line.strip()[:60],
                    message="Every sentence in this bullet is long. Mix in a short one.",
                )
            )
    return findings


def lint_resume(
    text: str,
    spine: Spine,
    units: list[EvidenceUnit],
    jd: ParsedJD | None = None,
) -> list[Finding]:
    lines = text.splitlines()
    allowed = _source_numbers(units, spine)
    spans = _spine_spans(spine)
    sourced_tenures = _sourced_tenures(units)
    protected = _protected_phrases(units)
    findings: list[Finding] = []
    for lineno, line in enumerate(lines, 1):
        findings += _check_line_phrases(line, lineno)
        findings += _check_numbers(line, lineno, allowed)
        findings += _check_tenure(line, lineno, spans, sourced_tenures)
        findings += _check_do_not_print(line, lineno, protected)
    findings += _check_education(lines, spine)
    findings += _check_rhythm(lines)
    findings += _check_jd_mirroring(lines, jd)
    return findings


def has_blockers(findings: list[Finding]) -> bool:
    return any(f.severity is Severity.BLOCK for f in findings)
