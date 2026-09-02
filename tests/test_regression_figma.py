"""The go/no-go regression test from implementation-design.md.

session-learnings.md, step 4: against the Figma JD, the pre-excavation career
file was thin on security-conversation and discovery experience. Asking
"did you do this?" recovered the McDonald's IT+L&D guidance work, the CEU
rescue, and the IQVIA escalation. This test reconstructs that pre-excavation
state (real data minus the excavated units) and asserts the gap component
reproduces the manual run: those gaps surface as MISS/THIN with recovery
questions, and the excavated units are exactly what close them.
"""

import pytest
from conftest import FIXTURES

from careerkit.coverage import CoverageStatus, assess_jd
from careerkit.dataload import load_parsed_jd
from careerkit.models import EvidenceUnit, Spine
from careerkit.questions import generate_questions

pytestmark = pytest.mark.private_corpus


def skill_status(coverages: list, skill: str) -> CoverageStatus:
    statuses = {
        s.skill: s.status for cov in coverages for s in cov.skills
    }
    return statuses[skill]


def test_pre_excavation_gaps_surface(
    thinned_units: list[EvidenceUnit], spine: Spine
) -> None:
    jd = load_parsed_jd(FIXTURES / "figma-jd-parsed.json")
    coverages = assess_jd(jd, thinned_units, spine)

    # The gaps the manual run found (session-learnings step 4):
    assert skill_status(coverages, "scim") is CoverageStatus.MISS
    assert skill_status(coverages, "escalation-management") is CoverageStatus.MISS
    assert skill_status(coverages, "stakeholder-guidance") is CoverageStatus.THIN
    assert skill_status(coverages, "sso") is CoverageStatus.THIN

    # And recovery questions exist for the requirements those gaps sit in:
    questions = generate_questions(coverages)
    asked_reqs = {q.requirement_id for q in questions}
    assert "security-it-ownership" in asked_reqs
    assert "cross-functional" in asked_reqs

    # What was NOT a gap in the manual run must not generate noise:
    assert skill_status(coverages, "front-end") is CoverageStatus.HIT
    assert skill_status(coverages, "customer-facing") is CoverageStatus.HIT


def test_excavated_units_close_the_gaps(
    units: list[EvidenceUnit], spine: Spine
) -> None:
    """With the full (post-excavation) data, the same skills improve.

    This proves the recovered units are what close the gaps, i.e. the questions
    the component asks are the ones that produced the strong resume.
    """
    jd = load_parsed_jd(FIXTURES / "figma-jd-parsed.json")
    coverages = assess_jd(jd, units, spine)

    # scim MISS -> HIT: the McDonald's deep-debug unit plus the enterprise
    # SCIM-familiarity unit excavated in the dogfood interview. (In the original
    # manual run, with only McDonald's, this was THIN.)
    assert skill_status(coverages, "scim") is CoverageStatus.HIT
    assert skill_status(coverages, "escalation-management") is CoverageStatus.HIT
    assert skill_status(coverages, "stakeholder-guidance") is CoverageStatus.HIT
    assert skill_status(coverages, "sso") is CoverageStatus.HIT
