"""Where the corpus lives. The one place that knows.

The engine is public and the person is private. They meet through one
environment variable:

    CAREERKIT_CORPUS   directory holding data/spine.yaml, data/evidence/,
                       data/declined.yaml, data/skills.yaml and career-data.md

Unset, everything runs against the fictional sample corpus shipped in
examples/sample-corpus, so a fresh clone works before anyone has typed a word
about themselves. Set, the same code runs on a real record it has never seen.

Until 2026-08-26 four gates carried an absolute path to one machine's copy of
one person's corpus. That was the single largest reason nobody else could run
this, and it is the reason this module exists.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_CORPUS = REPO_ROOT / "examples" / "sample-corpus"
ENV_VAR = "CAREERKIT_CORPUS"


def corpus_dir(*, quiet: bool = False) -> Path:
    """The corpus directory, or exit with a message that says how to fix it."""
    raw = os.environ.get(ENV_VAR)
    if raw:
        path = Path(raw).expanduser()
        if not (path / "data" / "spine.yaml").exists():
            raise SystemExit(
                f"{ENV_VAR}={raw}: no data/spine.yaml there. Point it at the "
                "directory holding your spine and evidence."
            )
        return path
    if not quiet:
        print(
            f"[careerkit] {ENV_VAR} is not set; using the sample corpus at "
            f"{SAMPLE_CORPUS}",
            file=sys.stderr,
        )
    return SAMPLE_CORPUS


def using_sample_corpus() -> bool:
    return not os.environ.get(ENV_VAR)
