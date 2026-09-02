"""Test wiring.

Tests run against whatever corpus CAREERKIT_CORPUS names, and against the
fictional sample corpus in examples/sample-corpus when it is unset. Nothing
in this suite asserts on a particular person's record; a second person's
corpus is expected to keep it green.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from careerkit.dataload import AliasTable, load_aliases, load_spine, load_units
from careerkit.models import EvidenceUnit, Spine

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_CORPUS = REPO_ROOT / "examples" / "sample-corpus"
SAMPLE_JD = SAMPLE_CORPUS / "jd" / "halcyon-solutions-engineer-parsed.json"

_env = os.environ.get("CAREERKIT_CORPUS")
CORPUS = Path(_env).expanduser() if _env else SAMPLE_CORPUS
DATA_DIR = CORPUS / "data"


@pytest.fixture(scope="session")
def spine() -> Spine:
    return load_spine(DATA_DIR / "spine.yaml")


@pytest.fixture(scope="session")
def units() -> list[EvidenceUnit]:
    return load_units(DATA_DIR / "evidence")


@pytest.fixture(scope="session")
def aliases() -> AliasTable:
    return load_aliases(DATA_DIR / "skills.yaml")
