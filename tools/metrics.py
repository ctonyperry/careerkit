"""Deterministic scorecard for a run. No LLM, no judgment, no narrative.

Every measure here was computed by hand at least once during the 2026-08-25
review and changed a decision: bullets without a result, foreign-domain jargon
density, skills-line terms no bullet supports, sentence-length uniformity. This
file exists so those checks stop being ad hoc, and so a pipeline change either
moves a number or it does not.

    python tools/metrics.py runs/<run-dir> [--json] [--baseline]

Page count comes from the rendered .docx when one is present and Word is
available; otherwise it is reported as unknown rather than guessed. Guessing
page counts is what put two spilled resumes into Drive.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

# What counts as a bullet stating an outcome. Two corrections on 2026-08-25,
# after the count was quoted at Tony as though it were a census:
#   - \b\d{2,}\b matched bare four-digit YEARS, so the compressed "Earlier"
#     line scored as a result on the strength of "1998". False positive.
#   - Spelled-out figures were invisible, so "the contract went from six months
#     to nine" and "roughly two million front-line workers" scored zero. False
#     negative on two of the strongest outcomes in the document.
# It stays a keyword proxy either way. A bullet describing scope of practice
# rather than an achievement is legitimate resume content, and forcing a result
# onto one is exactly how invented outcomes get written.
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
_RESULT_RE = re.compile(
    r"\$\d|\d+%|~?\d[\d,]*[KM+]|\b\d{2,}\b|5/5|landed|closed|unblocked|shipped"
    r"|extended|caught|resolved|without escalating|adopted"
    r"|\b(two|three|four|five|six|seven|eight|nine|ten|dozen|hundred|thousand"
    r"|million)\b",
    re.I,
)


def _states_result(bullet: str) -> bool:
    """True if the bullet claims an outcome, ignoring dates."""
    return bool(_RESULT_RE.search(_YEAR_RE.sub(" ", bullet)))


_ARTICLE_OPENER_RE = re.compile(r"^(the|a|an)\b", re.I)
_TRICOLON_RE = re.compile(r",[^,]+,\s*and\s", re.I)
_STOP = frozenset(
    ["a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "had", "has", "have", "in", "into", "is", "it", "its", "of", "on", "or", "that", "the", "their", "them", "then", "there", "these", "they", "this", "to", "was", "were", "with", "which", "who", "our", "we", "you", "your", "i"]
)


@dataclass
class Doc:
    name: str
    words: int
    pages: int | None
    bullets: int
    bullets_with_result: int
    bullets_verb_first: int
    bullet_length_spread: int
    bullet_opener_variety: int
    sentence_mean: float
    sentence_stdev: float
    tricolons: int
    em_dashes: int
    type_token_ratio: float


@dataclass
class RunMetrics:
    run: str
    company: str
    documents: list[Doc] = field(default_factory=list)
    jargon_absent_from_jd: dict[str, int] = field(default_factory=dict)
    skills_terms_unsupported: list[str] = field(default_factory=list)


def _page_count(docx: Path) -> int | None:
    """Ask Word. Return None rather than guessing when it is unavailable."""
    docx = docx.resolve()
    if not docx.exists():
        return None
    script = (
        "$w=New-Object -ComObject Word.Application;$w.Visible=$false;"
        f"$d=$w.Documents.Open('{docx}',$false,$true);"
        "$d.ComputeStatistics(2);$d.Close($false);$w.Quit()"
    )
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=120,
        )
        return int(out.stdout.strip().splitlines()[-1])
    except Exception:
        return None


def _sentences(text: str) -> list[str]:
    prose = "\n".join(
        line for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith(("#", "|", ">"))
    )
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", prose) if len(s.split()) > 2]


def _bullets(text: str) -> list[str]:
    return [
        line.strip()[2:].strip()
        for line in text.splitlines()
        if line.strip().startswith(("- ", "* "))
    ]


def _content_words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z][a-z'-]+", text.lower()) if w not in _STOP]


def bullet_length_spread(bullets: list[str]) -> int:
    """Longest bullet minus shortest, in words.

    Sentence-level uniformity is already measured; this is the same tell one
    level up. On 2026-08-25 a resume passed lint, crosscheck, citecheck and
    finalize with twelve bullets between 27 and 50 words, all but two of them
    inside a ten-word band, and it still read as machine output. Every bullet
    was doing the same amount of work. Below roughly 20 the set is suspiciously
    even; a person writes some bullets short.
    """
    lengths = [len(b.split()) for b in bullets]
    return max(lengths) - min(lengths) if lengths else 0


def bullet_opener_variety(bullets: list[str]) -> int:
    """Distinct first words across the bullets.

    Approaching one-per-bullet is synonym cycling: a thesaurus reached for so
    no verb repeats. Humans repeat the clearest word, so some repetition is the
    healthy signal, and it also pulls type-token ratio back toward human range.
    """
    openers = [b.split()[0].strip("*").lower() for b in bullets if b.split()]
    return len(set(openers))


def measure_doc(name: str, text: str, docx: Path | None) -> Doc:
    bullets = _bullets(text)
    sentences = _sentences(text)
    lengths = [len(s.split()) for s in sentences] or [0]
    words = _content_words(text)
    return Doc(
        name=name,
        words=len(text.split()),
        pages=_page_count(docx) if docx else None,
        bullets=len(bullets),
        bullets_with_result=sum(1 for b in bullets if _states_result(b)),
        bullets_verb_first=sum(1 for b in bullets if not _ARTICLE_OPENER_RE.match(b)),
        bullet_length_spread=bullet_length_spread(bullets),
        bullet_opener_variety=bullet_opener_variety(bullets),
        sentence_mean=round(statistics.mean(lengths), 1),
        sentence_stdev=round(statistics.pstdev(lengths), 1),
        tricolons=sum(
            1 for line in text.splitlines()
            if not line.lstrip().startswith(("- ", "* "))
            and _TRICOLON_RE.search(line)
        ),
        em_dashes=text.count("—"),
        type_token_ratio=round(len(set(words)) / len(words), 2) if words else 0.0,
    )


def jargon_absent_from_jd(text: str, jd_text: str, floor: int = 2) -> dict[str, int]:
    """Terms the document leans on that the JD never uses.

    Not automatically wrong: "SAML" may be absent from a JD that says "identity
    federation". It is a prompt to check whether a term is doing work for this
    reader, which is how xAPI x4 and SCORM x2 were found in an identity-company
    application.
    """
    jd_words = set(_content_words(jd_text))
    counts: dict[str, int] = {}
    # Domain terms, not common English: acronyms, camelCase, and mid-sentence
    # capitals. Counting ordinary words surfaced "across x5" and "owned x4",
    # which tell you nothing; the signal wanted is xAPI, SCORM, sendBeacon.
    # A word that also appears lowercase in the same document is ordinary
    # English capitalised at a sentence start ("Ran", "Built"), not a term.
    lowercase_forms = {w for w in re.findall(r"\b[a-z][a-z0-9'-]{2,}\b", text)}
    months = {
        "jan", "feb", "mar", "apr", "may", "jun", "jul",
        "aug", "sep", "oct", "nov", "dec",
    }
    for token in re.findall(r"\b[A-Za-z][A-Za-z0-9.+#/-]{2,}\b", text):
        stripped = token.strip(".-/")
        if stripped.lower() in lowercase_forms or stripped.lower() in months:
            continue
        is_acronym = stripped.isupper() and len(stripped) > 2
        is_camel = re.search(r"[a-z][A-Z]", stripped) is not None
        is_proper = stripped[:1].isupper() and not stripped.isupper()
        if not (is_acronym or is_camel or is_proper):
            continue
        if stripped.lower() in jd_words or stripped.lower() in _STOP:
            continue
        counts[stripped] = counts.get(stripped, 0) + 1
    return dict(
        sorted(
            ((w, n) for w, n in counts.items() if n >= floor),
            key=lambda kv: -kv[1],
        )[:12]
    )


def skills_terms_unsupported(text: str) -> list[str]:
    """Skills-line terms that appear nowhere else in the document.

    The house rule is that the skills line may only restate what a bullet
    proves. On 2026-08-25 a JD-required keyword was found sitting there alone.
    """
    line = next(
        (
            ln
            for ln in text.splitlines()
            if ln.count("·") >= 3
            and not ln.startswith("#")
            and "@" not in ln  # the contact line is middot-separated too
        ),
        None,
    )
    if not line:
        return []
    body = text.replace(line, "")
    unsupported = []
    for term in (t.strip() for t in line.split("·")):
        keys = [k for k in re.findall(r"[A-Za-z][A-Za-z0-9.+#/]+", term) if len(k) > 2]
        if not keys:
            continue
        # Distinctive keys carry the claim: a proper noun or an acronym is the
        # part a reader checks. Requiring only ONE key to appear let "identity
        # lifecycle with HRIS sources (Workday, ADP)" pass on the strength of
        # "identity" while Workday and ADP appeared nowhere in the document.
        distinctive = [
            k for k in keys
            if (k[:1].isupper() and not k.islower()) or k.isupper()
        ]
        missing = [
            k for k in (distinctive or keys)
            if not re.search(rf"\b{re.escape(k)}", body, re.I)
        ]
        if missing and len(missing) == len(distinctive or keys):
            unsupported.append(term)
        elif missing:
            unsupported.append(f"{term}  (unsupported: {', '.join(missing)})")
    return unsupported


def collect(run_dir: Path) -> RunMetrics:
    manifest = yaml.safe_load((run_dir / "manifest.yaml").read_text(encoding="utf-8"))
    metrics = RunMetrics(run=run_dir.name, company=str(manifest.get("company", "")))

    jd_text = ""
    jd_rel = manifest.get("jd")
    if jd_rel:
        for candidate in (Path(jd_rel), run_dir / jd_rel, run_dir.parent.parent / jd_rel):
            if candidate.exists():
                jd_text = candidate.read_text(encoding="utf-8")
                break

    for name in manifest.get("documents", []):
        path = run_dir / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        docx = path.with_suffix(".docx")
        metrics.documents.append(measure_doc(name, text, docx if docx.exists() else None))
        if name == manifest.get("resume"):
            if jd_text:
                metrics.jargon_absent_from_jd = jargon_absent_from_jd(text, jd_text)
            metrics.skills_terms_unsupported = skills_terms_unsupported(text)
    return metrics


def render(m: RunMetrics) -> str:
    out = [f"{m.company}  ({m.run})", ""]
    for d in m.documents:
        pages = d.pages if d.pages is not None else "?"
        out.append(f"  {d.name}")
        out.append(f"    {d.words} words, {pages} page(s)")
        if d.bullets:
            out.append(
                f"    bullets {d.bullets}: {d.bullets_with_result} state a result, "
                f"{d.bullets_verb_first} open with a verb"
            )
            out.append(
                f"    bullet length spread {d.bullet_length_spread}w, "
                f"{d.bullet_opener_variety} distinct openers of {d.bullets}  "
                f"(a narrow spread, or one opener per bullet, reads machine-shaped)"
            )
        out.append(
            f"    sentences mean {d.sentence_mean}w, stdev {d.sentence_stdev}  "
            f"(low stdev reads metronomic)"
        )
        out.append(
            f"    tricolons {d.tricolons}, em dashes {d.em_dashes}, "
            f"type-token {d.type_token_ratio} (human prose 0.50-0.65+)"
        )
        out.append("")
    if m.skills_terms_unsupported:
        out.append("  skills-line terms no bullet supports:")
        out += [f"    - {t}" for t in m.skills_terms_unsupported]
        out.append("")
    if m.jargon_absent_from_jd:
        pairs = ", ".join(f"{w} x{n}" for w, n in m.jargon_absent_from_jd.items())
        out.append(f"  leaned on but absent from the JD: {pairs}")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deterministic scorecard for a run.")
    parser.add_argument("run_dir")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--baseline", action="store_true", help="write metrics.json into the run"
    )
    args = parser.parse_args(argv)

    run_dir = Path(args.run_dir)
    metrics = collect(run_dir)
    blob = json.dumps(asdict(metrics), indent=2)
    if args.baseline:
        (run_dir / "metrics.json").write_text(blob + "\n", encoding="utf-8")
        print(f"Wrote {run_dir / 'metrics.json'}")
    print(blob if args.json else render(metrics))
    return 0


if __name__ == "__main__":
    sys.exit(main())
