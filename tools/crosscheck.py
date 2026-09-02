"""Cross-document checks for a targeted-resume run.

careerkit owns the single-document gates (house-style lint, coverage,
finalize). This tool owns what only exists across a RUN: several documents
written for one JD, which must agree with each other, with the spine, and with
the JD text on disk.

Every check here exists because the 2026-08-24 session shipped the bug it
catches (see coalesce-report.md section 6).

    python tools/crosscheck.py runs/<run-dir> [--spine <path>] [--json]

Exit 1 if any BLOCK finding fires.

LIMITATION, deliberate: jd-trace is word-overlap, not comprehension. A
sentence can share vocabulary with the JD while asserting something the JD
never says. Catching that is the adversarial eval pass's job (a skeptic agent
reading both texts); this tool exists to make the mechanical failures
impossible, not to replace the reader.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from _paths import SPINE as DEFAULT_SPINE  # noqa: E402

BLOCK = "BLOCK"
WARN = "WARN"

ROOT = Path(__file__).resolve().parent.parent

# Words carrying no evidentiary weight when matching a sentence against JD text.
STOPWORDS = frozenset(
    ["a", "an", "and", "are", "as", "at", "be", "been", "being", "but", "by", "can", "could", "did", "do", "does", "for", "from", "had", "has", "have", "how", "i", "if", "in", "into", "is", "it", "its", "me", "my", "not", "of", "on", "or", "our", "so", "than", "that", "the", "their", "them", "then", "there", "these", "they", "this", "to", "too", "us", "was", "we", "were", "what", "when", "where", "which", "who", "why", "will", "with", "would", "you", "your", "yours", "am", "here", "just", "really", "very", "much", "more", "most", "also", "one", "two", "three", "about", "over", "under", "after", "before", "while", "because", "way", "ways", "lot", "part", "big", "real", "thing", "things", "kind", "sort", "posting", "listing", "job", "role", "says", "said", "mention", "mentions", "opens", "open", "apply", "applying", "exactly", "itself", "same", "only", "just", "want", "wants", "looking", "look"]
)

TENSE_PRESENT = re.compile(
    r"\b(present|currently|i am on|i'm on|ongoing|to date|now at)\b", re.I
)

DATE_RANGE = re.compile(
    r"((?:[A-Z][a-z]{2,8}\.?\s+)?\d{4})\s*(?:-|--|to)\s*"
    r"((?:[A-Z][a-z]{2,8}\.?\s+)?\d{4}|Present)",
    re.I,
)

GENERIC_COMPANY_TOKENS = frozenset(
    ["app", "inc", "corp", "corporation", "labs", "group", "company", "holdings", "technologies", "systems", "solutions", "software", "services", "the", "and", "via"]
)

COMPANY_CLAIM_HINT = re.compile(
    r"\b(your (?:posting|job|listing|team|company|mission)|the (?:posting|listing) says"
    r"|you(?:'re| are) building|all[- ]in on|as your)\b",
    re.I,
)


@dataclass
class Finding:
    severity: str
    rule: str
    doc: str
    line: int
    message: str
    excerpt: str


def _sentences(text: str) -> list[tuple[int, str]]:
    """(line_number, sentence) pairs, sentence-split within each line."""
    out: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("---", "```", "<!--", "|")):
            continue
        # Headings are scanned, not skipped: on a resume the role dates live in
        # the heading, which is exactly where tense and drift bugs hide.
        stripped = re.sub(r"^[#>*\-\s]+", "", stripped)
        if not stripped:
            continue
        for part in re.split(r"(?<=[.!?])\s+", stripped):
            cleaned = part.strip("-*. \t")
            if cleaned:
                out.append((lineno, cleaned))
    return out


def _stem(word: str) -> str:
    """Crude suffix stripping so 'securing' matches the JD's 'secures'. Not
    linguistics; just enough that a real quote of the JD is not flagged as
    unsupported."""
    word = word.rstrip("'").removesuffix("'s")
    for suffix, keep in (("ing", 5), ("ers", 5), ("ed", 4), ("es", 4), ("s", 4)):
        if len(word) >= keep and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def _content_words(sentence: str) -> set[str]:
    words = re.findall(r"[a-z0-9']+", sentence.lower())
    return {_stem(w) for w in words if w not in STOPWORDS and len(w) > 2}


def _org_key(org: str) -> str:
    """First distinctive token of an org name: 'Apple (via TEKsystems)' -> 'apple'."""
    return re.split(r"[ (/,]", str(org).strip())[0].lower()


def _load_manifest(run_dir: Path) -> dict:
    path = run_dir / "manifest.yaml"
    if not path.exists():
        raise SystemExit("no manifest.yaml in " + str(run_dir))
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _documents(run_dir: Path, manifest: dict) -> dict[str, str]:
    docs: dict[str, str] = {}
    for name in manifest.get("documents", []):
        path = run_dir / name
        if path.exists():
            docs[name] = path.read_text(encoding="utf-8")
    return docs


def check_spine_agreement(docs: dict[str, str], spine: dict) -> list[Finding]:
    """A role the spine says ended must never read as ongoing."""
    findings: list[Finding] = []
    for role in spine.get("roles", []):
        org = str(role.get("org", ""))
        end = str(role.get("end", ""))
        key = _org_key(org)
        if len(key) < 3 or not end or "present" in end.lower():
            continue
        for doc, text in docs.items():
            for lineno, sentence in _sentences(text):
                if key in sentence.lower() and TENSE_PRESENT.search(sentence):
                    findings.append(
                        Finding(
                            BLOCK,
                            "spine-tense",
                            doc,
                            lineno,
                            f"{org} ended {end} per the spine, but this reads as ongoing.",
                            sentence[:160],
                        )
                    )
    return findings


def check_cross_document(docs: dict[str, str], spine: dict) -> list[Finding]:
    """The same org must not carry different date ranges across a run's documents."""
    findings: list[Finding] = []
    seen: dict[str, list[tuple[str, int, str]]] = {}
    orgs = [k for k in (_org_key(r.get("org", "")) for r in spine.get("roles", [])) if len(k) >= 3]

    for doc, text in docs.items():
        for lineno, sentence in _sentences(text):
            low = sentence.lower()
            for org in orgs:
                if org not in low:
                    continue
                match = DATE_RANGE.search(sentence)
                if match:
                    seen.setdefault(org, []).append((doc, lineno, match.group(0).lower()))
                elif TENSE_PRESENT.search(sentence):
                    seen.setdefault(org, []).append((doc, lineno, "reads-as-ongoing"))

    for org, mentions in seen.items():
        variants = {v for _, _, v in mentions}
        if len(variants) > 1:
            where = "; ".join(f"{d}:{ln} '{v}'" for d, ln, v in mentions)
            findings.append(
                Finding(
                    BLOCK,
                    "cross-doc-drift",
                    mentions[0][0],
                    mentions[0][1],
                    f"'{org}' is described inconsistently across this run: {where}",
                    ", ".join(sorted(variants))[:160],
                )
            )
    return findings


def check_jd_trace(
    docs: dict[str, str], jd_text: str, company: str, min_overlap: float = 0.34
) -> list[Finding]:
    """Sentences asserting something ABOUT the target company must be supported
    by the JD file on disk. This catches cross-JD contamination: the Okta phrase
    'all in on' landing in a Cash App cover letter."""
    findings: list[Finding] = []
    jd_words = _content_words(jd_text)
    company_words = _content_words(company)
    # Word-boundary match on distinctive tokens only. Without boundaries "App"
    # matches "Apple"/"applied" and "Block" matches "renewal-blocking".
    tokens = [
        t
        for t in re.findall(r"[A-Za-z][A-Za-z0-9']+", company)
        if len(t) >= 4 and t.lower() not in GENERIC_COMPANY_TOKENS
    ]
    if not tokens:
        return findings
    company_re = re.compile(
        r"\b(?:" + "|".join(re.escape(t) for t in tokens) + r")\b", re.I
    )

    for doc, text in docs.items():
        for lineno, sentence in _sentences(text):
            mentions_company = bool(company_re.search(sentence))
            hinted = bool(COMPANY_CLAIM_HINT.search(sentence))
            if not (mentions_company or hinted):
                continue
            words = _content_words(sentence) - company_words
            if not words:
                continue
            ratio = len(words & jd_words) / len(words)
            if ratio >= min_overlap:
                continue
            unsupported = sorted(words - jd_words)[:8]
            findings.append(
                Finding(
                    BLOCK if hinted else WARN,
                    "jd-trace",
                    doc,
                    lineno,
                    (
                        "claim about the target company is not supported by the JD text "
                        f"({int(ratio * 100)}% overlap); unsupported: "
                        f"{', '.join(unsupported)}. Quote the JD or cite a source."
                    ),
                    sentence[:160],
                )
            )
    return findings


# Referring expressions that need an antecedent OUTSIDE their own bullet. A
# bullet is read alone, in any order, and is routinely deleted or reordered, so
# a back-reference to a neighbour is a dependency the format does not support.
_DANGLING = re.compile(
    r"\b(that|those|the same|this)\s+"
    r"(rollout|engagement|project|customer|account|integration|effort|work|"
    r"library|migration|program|deployment|team|firm|platform)\b",
    re.I,
)


def check_dangling_reference(docs: dict[str, str]) -> list[Finding]:
    """A bullet pointing at something only a neighbouring bullet establishes.

    Found on 2026-08-26, and by Tony rather than by a gate. A layout experiment
    removed the McDonald's bullet, and the bullet after it still opened
    "Diagnosed a provisioning sync failing partway through that rollout".
    Which rollout? The one that had just been deleted.

    This is a cost of the format itself. Bullets get cut, reordered and
    re-selected per target, so any bullet that leans on its neighbour is one
    edit away from nonsense, and the nonsense reads as carelessness at exactly
    the moment a reader is deciding whether to keep going.
    """
    findings: list[Finding] = []
    for name, text in docs.items():
        if not name.endswith(".md") or "resume" not in name:
            continue
        section: list[str] = []
        for i, line in enumerate(text.splitlines(), 1):
            if line.startswith("#"):
                section = []
                continue
            if not line.strip().startswith(("- ", "* ")):
                continue
            bullet = line.strip()[2:]
            for m in _DANGLING.finditer(bullet):
                phrase, noun = m.group(0), m.group(2).lower()
                before = bullet[: m.start()].lower()
                # Satisfied outright if the bullet names the thing itself first,
                # e.g. "the library ... its runbook".
                if noun in before or noun.rstrip("s") in before:
                    continue
                # An earlier bullet in the same role can supply it. That reads
                # correctly TODAY and breaks the moment that bullet is cut,
                # which is exactly what happened on 2026-08-26, so it is a
                # warning rather than a pass.
                earlier = any(noun in b.lower() or noun.rstrip("s") in b.lower()
                              for b in section)
                findings.append(Finding(
                    severity="WARN" if earlier else "BLOCK",
                    rule="dangling-reference", doc=name, line=i,
                    message=(
                        f"{phrase!r} is answered by an earlier bullet in the same role, "
                        f"not by this one. It reads correctly now and breaks the moment "
                        f"that bullet is cut or reordered, which is how it broke once."
                        if earlier else
                        f"{phrase!r} has no antecedent in this bullet or any earlier one "
                        f"in the same role. Name the thing."),
                    excerpt=bullet[:90],
                ))
            section.append(bullet)
    return findings


def check_claim_coverage(
    run_dir: Path, manifest: dict, evidence_dir: Path
) -> list[Finding]:
    """A resume with bullets must ship a claim sheet citing REAL evidence unit
    ids. Matching against the corpus (not a hyphenated-word regex) also catches
    a cited id that does not exist."""
    sheet_name = manifest.get("claim_sheet")
    resume_name = manifest.get("resume")
    if not sheet_name or not resume_name:
        return []
    sheet_path, resume_path = run_dir / sheet_name, run_dir / resume_name
    if not (sheet_path.exists() and resume_path.exists()):
        return []

    known = {p.stem for p in evidence_dir.glob("*.yaml")} if evidence_dir.exists() else set()
    sheet_text = sheet_path.read_text(encoding="utf-8")
    cited = {uid for uid in known if re.search(r"\b" + re.escape(uid) + r"\b", sheet_text)}
    has_bullets = any(
        line.strip().startswith(("- ", "* "))
        for line in resume_path.read_text(encoding="utf-8").splitlines()
    )

    findings: list[Finding] = []
    if has_bullets and not cited:
        findings.append(
            Finding(
                BLOCK,
                "claim-sheet-empty",
                sheet_name,
                1,
                "resume has bullets but the claim sheet cites no known evidence unit id.",
                "",
            )
        )
    # An id-shaped token in the sheet that matches no unit on disk is a
    # fabricated citation, which is worse than no citation.
    for token in set(re.findall(r"\b([a-z][a-z0-9]+(?:-[a-z0-9]+){2,4})\b", sheet_text)):
        if known and token not in known and token.split("-")[0] in {
            p.stem.split("-")[0] for p in evidence_dir.glob("*.yaml")
        }:
            findings.append(
                Finding(
                    WARN,
                    "claim-sheet-unknown-id",
                    sheet_name,
                    1,
                    f"'{token}' looks like an evidence id but no such unit exists.",
                    token,
                )
            )
    return findings


def _resolve_jd(run_dir: Path, jd_rel: str) -> Path | None:
    """A manifest's `jd:` is written relative to wherever the runs live, and
    that is a private directory this repo knows nothing about. So: the path
    as given, then the run directory and each of its ancestors, then
    $CAREERKIT_RUNS if set, then this repo. The first hit wins."""
    run_dir = run_dir.resolve()
    candidates = [Path(jd_rel), run_dir / jd_rel]
    candidates += [parent / jd_rel for parent in run_dir.parents]
    runs_root = os.environ.get("CAREERKIT_RUNS")
    if runs_root:
        candidates.append(Path(runs_root).expanduser() / jd_rel)
    candidates.append(ROOT / jd_rel)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def run_checks(
    run_dir: Path,
    spine_path: Path = DEFAULT_SPINE,
    evidence_dir: Path | None = None,
) -> list[Finding]:
    manifest = _load_manifest(run_dir)
    docs = _documents(run_dir, manifest)
    if not docs:
        raise SystemExit("manifest lists no readable documents in " + str(run_dir))
    spine = yaml.safe_load(spine_path.read_text(encoding="utf-8")) or {}

    findings = check_spine_agreement(docs, spine)
    findings += check_cross_document(docs, spine)
    findings += check_dangling_reference(docs)

    # An untargeted document (the LinkedIn profile, a bio) has no posting to
    # trace against. Everything else still applies, and the spine checks matter
    # MORE there: a public page carrying a stale tense is worse than a resume
    # doing it, because nobody re-reads it before sending.
    if str(manifest.get("target", "")).lower() in {"none", "untargeted"}:
        findings += check_claim_coverage(
            run_dir, manifest, evidence_dir or (spine_path.parent / "evidence")
        )
        return findings

    jd_rel = manifest.get("jd")
    jd_path = _resolve_jd(run_dir, str(jd_rel)) if jd_rel else None
    if jd_path is not None:
        findings += check_jd_trace(
            docs, jd_path.read_text(encoding="utf-8"), str(manifest.get("company", ""))
        )
    else:
        findings.append(
            Finding(
                BLOCK,
                "jd-missing",
                "manifest.yaml",
                1,
                "no JD text on disk: the jd-trace check cannot run.",
                str(jd_rel),
            )
        )

    findings += check_claim_coverage(
        run_dir, manifest, evidence_dir or (spine_path.parent / "evidence")
    )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cross-document checks for a run.")
    parser.add_argument("run_dir")
    parser.add_argument("--spine", default=str(DEFAULT_SPINE))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    findings = run_checks(Path(args.run_dir), Path(args.spine))
    if args.json:
        print(json.dumps([asdict(f) for f in findings], indent=2))
    else:
        for finding in findings:
            print(
                f"{finding.severity:5} {finding.doc}:{finding.line} "
                f"[{finding.rule}] {finding.message}"
            )
            if finding.excerpt:
                print("      :: " + finding.excerpt)
    blocks = sum(1 for f in findings if f.severity == BLOCK)
    print(f"{blocks} blocking, {len(findings) - blocks} advisory")
    return 1 if blocks else 0


if __name__ == "__main__":
    sys.exit(main())
