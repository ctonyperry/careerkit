"""Test wiring.

Two kinds of test live here, and the difference is the corpus they read.

- Contract tests run against whatever corpus CAREERKIT_CORPUS names, and
  against the fictional sample corpus in examples/sample-corpus when it is
  unset. These are the public contract, and CI runs them on the sample.
- Historical tests are marked `private_corpus`. They were written against the
  original author's record and assert on its specific units and roles (the
  go/no-go regression that reproduced the first manual run, for instance).
  They are true, they are worth keeping, and they can only pass on that one
  corpus, so they skip anywhere else.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from careerkit.dataload import AliasTable, load_aliases, load_spine, load_units
from careerkit.models import EvidenceUnit, Spine

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"

_env = os.environ.get("CAREERKIT_CORPUS")
CORPUS = Path(_env).expanduser() if _env else REPO_ROOT / "examples" / "sample-corpus"
DATA_DIR = CORPUS / "data"

# The historical tests were written against one particular corpus. Detect it
# by a unit that only it has, rather than by whether the env var is set: a
# second person pointing CAREERKIT_CORPUS at their own record should get the
# contract tests and a clean skip, not twelve failures about someone else's
# career.
HISTORICAL_CORPUS = (DATA_DIR / "evidence" / "linkedin-mcdonalds.yaml").exists()

# The pre-excavation (cold-start) baseline for the go/no-go regression.
#
# This is an ALLOWLIST on purpose. It was a blocklist of excavated units, but
# that inverts the maintenance burden: the corpus is the byproduct and grows
# with every dogfood run, so each new unit touching a baseline skill silently
# eroded the regression until someone remembered to exclude it. The baseline is
# a fixed historical fact instead: the units migrated from career-data.md at
# commit c02f6a8, minus the three the original manual run recovered
# (session-learnings.md step 4). Corpus growth can no longer weaken it.
#
# Only ever edit this if the historical record itself was wrong.
EXCAVATED_UNIT_IDS = frozenset(
    {"linkedin-mcdonalds", "linkedin-ceu-rescue", "linkedin-iqvia"}
)

MIGRATED_UNIT_IDS = frozenset(
    {
        "apple-ux-research",
        "apple-xapi-library",
        "athenaonline-content-production",
        "athenaonline-technical-owner",
        "ims-operations",
        "linkedin-book-of-business",
        "linkedin-ceu-rescue",
        "linkedin-integration-library",
        "linkedin-iqvia",
        "linkedin-mcdonalds",
        "linkedin-microsoft-datalake",
        "microsoft-acpi-qa",
        "project-dice-game",
        "project-rc-lighting",
        "project-squadventure",
        "project-ux-telemetry-kit",
        "symantec-support",
    }
)

BASELINE_UNIT_IDS = MIGRATED_UNIT_IDS - EXCAVATED_UNIT_IDS


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "private_corpus: asserts on the original author's record; skipped on any other corpus",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if HISTORICAL_CORPUS:
        return
    skip = pytest.mark.skip(
        reason="written against the original author's corpus; set CAREERKIT_CORPUS to it"
    )
    for item in items:
        if "private_corpus" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def spine() -> Spine:
    return load_spine(DATA_DIR / "spine.yaml")


@pytest.fixture(scope="session")
def units() -> list[EvidenceUnit]:
    return load_units(DATA_DIR / "evidence")


@pytest.fixture(scope="session")
def aliases() -> AliasTable:
    return load_aliases(DATA_DIR / "skills.yaml")


@pytest.fixture(scope="session")
def thinned_units(units: list[EvidenceUnit]) -> list[EvidenceUnit]:
    """The cold-start career file the go/no-go regression reproduces."""
    baseline = [u for u in units if u.id in BASELINE_UNIT_IDS]
    missing = BASELINE_UNIT_IDS - {u.id for u in baseline}
    assert not missing, f"baseline units deleted from the corpus: {sorted(missing)}"
    return baseline
