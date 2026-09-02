"""Recovery-question generation. Deterministic templates.

The framing is the load-bearing part (session-learnings.md, step 4):
  "This role wants X. Your file is thin on X. Did you do X, and when?"
NEVER "what would make you match better" (invites inflation). THIN questions
name the existing evidence to jog memory, which is how the manual run
recovered the franchise-rollout detail. Questions ask for a specific instance and a
rough date so defensibility starts at the question, not at review time.
"""

from __future__ import annotations

from pydantic import BaseModel

from careerkit.coverage import CoverageStatus, RequirementCoverage

_INSTANCE_ASK = (
    "If yes, name a specific instance: which customer or project, roughly when, "
    "and what you personally did. Memory-only answers are fine; they get marked "
    "for conscious ownership before any resume uses them."
)


class RecoveryQuestion(BaseModel):
    requirement_id: str
    skills: list[str]
    text: str


def _question_for(cov: RequirementCoverage) -> RecoveryQuestion | None:
    # Only capability requirements are excavatable. credential -> strategy note,
    # tenure -> spine math (both in careerkit.strategy); neither is ever asked.
    if cov.requirement.kind != "capability":
        return None

    missing = [s for s in cov.skills if s.status is CoverageStatus.MISS]
    thin = [s for s in cov.skills if s.status is CoverageStatus.THIN]
    if not missing and not thin:
        return None

    lines = [f"This role wants: {cov.requirement.text}"]
    if missing:
        tags = ", ".join(s.skill for s in missing)
        lines.append(f"I don't see anything in your file for: {tags}.")
    for s in thin:
        existing = ", ".join(s.unit_ids)
        lines.append(
            f"Your file is thin on {s.skill}; the only support is: {existing}."
        )
    lines.append("Did you do this work, and when?")
    lines.append(_INSTANCE_ASK)

    return RecoveryQuestion(
        requirement_id=cov.requirement.id,
        skills=[s.skill for s in missing + thin],
        text="\n".join(lines),
    )


def generate_questions(
    coverages: list[RequirementCoverage],
) -> list[RecoveryQuestion]:
    return [q for cov in coverages if (q := _question_for(cov)) is not None]
