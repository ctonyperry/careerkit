"""Prepare reviewer packets for an expert panel.

The design constraint: reviewers must differ in WHAT THEY ARE GIVEN, not in an
adjective. A "recruiter persona" that reads the whole document carefully is not
a recruiter; a reviewer handed only what fits above the fold is. career-graph's
own architecture review predicted persona prompting would make "no measurable
difference on groundedness", and it was right, because the persona was the only
thing that changed.

So this script does the deterministic half: it slices, strips, and packages, and
each packet states the one task that reviewer can perform with what it holds.

    python tools/panel.py runs/<run-dir>

Writes evals/panels/<run>/*.md. Spawn one agent per packet; each returns
findings only.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

RECRUITER_TASK = """\
You are screening a stack of applications. You will spend about seven seconds
here before deciding to keep reading or move on.

Below is EVERYTHING you would see in that time: the top of the page, nothing
more. You do not have the job description and you will not get one. You are
screening for a {role}.

Answer three questions, briefly:
1. Keep or pass?
2. What made you decide, quoting the words that did it?
3. What did you expect to see in this space and did not?

Do not speculate about what might appear further down. Judge what is here.
"""

MANAGER_TASK = """\
You are the hiring manager for this role. A recruiter passed this along, and
you will spend about two minutes on it before deciding whether to interview.

You have the full application and the job description. The question you are
actually answering is: could this person be dropped into a customer engagement
alone without embarrassing us?

Report:
1. Interview or decline, and the single strongest reason either way.
2. The three things you would probe in a screen, and what you suspect is
   thinner than it reads.
3. Anything the posting asks for that you cannot find evidence of here.
4. Any claim you would want substantiated before an offer.

Findings only. Do not rewrite anything.
"""

CRITIC_TASK = """\
You are a writing editor. You have the document and nothing else: no job
description, no company name, no idea what role this targets.

Company and product names have been replaced with [redacted by the review
harness]. That substitution is ours, not the writer's, and the sentences around
it will read oddly as a result. Do not report it as a defect.

That is deliberate. Without the posting you cannot rationalise a weak sentence
as "relevant", so judge only whether this reads as though a person wrote it.

Report:
1. Any sentence that reads as machine-generated, quoted, with the tell named.
2. Where the rhythm goes uniform, or where every construction has the same
   shape.
3. Any clause that could be deleted with no loss of information.
4. Anything that is trying to sound impressive rather than being specific.
5. The two strongest sentences, so the voice worth keeping is identified.

Findings only. Do not rewrite anything.
"""


def _strip_identifiers(text: str, company: str) -> str:
    """Remove the target company so the critic cannot infer the posting.

    The replacement reads as ordinary prose on purpose. An earlier version used
    a bracketed placeholder, and the 2026-08-25 critic reported it as an
    unfilled merge field left in the output: a real defect to report, and not
    one that was in the document. A redaction that looks like a bug spends a
    reviewer on the harness instead of the writing.
    """
    tokens = [t for t in re.findall(r"[A-Za-z][A-Za-z0-9']+", company) if len(t) >= 4]
    for token in tokens:
        text = re.sub(rf"\b{re.escape(token)}\b", "[redacted by the review harness]", text, flags=re.I)
    return text


def above_the_fold(resume: str) -> str:
    """What a seven-second scan actually reaches.

    Eye-tracking (Ladders 2018) puts attention on the name, the current title,
    the most recent company, and the first two or three bullets. That is a
    principled slice, unlike an arbitrary percentage of the file.
    """
    lines = resume.splitlines()
    out: list[str] = []
    role_headings = 0
    bullets_after_first_role = 0
    for line in lines:
        if line.startswith("### "):
            role_headings += 1
            if role_headings > 1:
                break
        if role_headings == 1 and line.strip().startswith(("- ", "* ")):
            bullets_after_first_role += 1
            if bullets_after_first_role > 3:
                break
        out.append(line)
    return "\n".join(out).rstrip()


def build(run_dir: Path) -> list[Path]:
    manifest = yaml.safe_load((run_dir / "manifest.yaml").read_text(encoding="utf-8"))
    company = str(manifest.get("company", ""))
    role = str(manifest.get("role", ""))

    resume_name = manifest.get("resume")
    resume = (run_dir / resume_name).read_text(encoding="utf-8") if resume_name else ""
    documents = "\n\n---\n\n".join(
        (run_dir / n).read_text(encoding="utf-8")
        for n in manifest.get("documents", [])
        if (run_dir / n).exists()
    )

    jd_text = ""
    jd_rel = manifest.get("jd")
    if jd_rel:
        for candidate in (Path(jd_rel), run_dir / jd_rel, run_dir.parent.parent / jd_rel):
            if candidate.exists():
                jd_text = candidate.read_text(encoding="utf-8")
                break

    # Packets belong beside the runs, not in the engine repo.
    runs_root = Path(os.environ.get("CAREERKIT_RUNS") or ROOT)
    out_dir = runs_root / "evals" / "panels" / run_dir.name
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    packets = {
        "recruiter.md": (
            RECRUITER_TASK.format(role=role)
            + "\n\n## What you can see\n\n"
            + above_the_fold(resume)
        ),
        "hiring-manager.md": (
            MANAGER_TASK
            + "\n\n## The posting\n\n"
            + jd_text
            + "\n\n## The application\n\n"
            + documents
        ),
        "writing-critic.md": (
            CRITIC_TASK
            + "\n\n## The document\n\n"
            + _strip_identifiers(documents, company)
        ),
    }
    for name, body in packets.items():
        path = out_dir / name
        path.write_text(body, encoding="utf-8")
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare expert-panel packets.")
    parser.add_argument("run_dir")
    args = parser.parse_args(argv)
    for path in build(Path(args.run_dir)):
        words = len(path.read_text(encoding="utf-8").split())
        print(f"Wrote {path}  ({words} words)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
