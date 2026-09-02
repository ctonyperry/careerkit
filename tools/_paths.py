"""Shim so every gate under tools/ finds the engine and the corpus the same way.

The gates are scripts, run as `python tools/<gate>.py <run-dir>`, so they put
the repo root on sys.path themselves and then defer to careerkit.paths, which
is the one place that knows where the corpus is.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from careerkit.paths import corpus_dir  # noqa: E402

CORPUS = corpus_dir()
EVIDENCE = CORPUS / "data" / "evidence"
SPINE = CORPUS / "data" / "spine.yaml"
