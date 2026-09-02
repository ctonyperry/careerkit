"""Parsed-JD model.

The parse itself is an LLM step performed in Claude Code chat using
prompts/jd-parse.md, which writes this JSON shape. Requirement skills must be
CANONICAL tags from data/skills.yaml; JD language the parser cannot map goes
into unknown_terms for the user to confirm as new aliases.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Requirement(BaseModel):
    id: str
    text: str
    skills: list[str]
    weight: Literal["required", "preferred"]
    # capability: excavatable, drives the recovery-question flow (the default,
    #   so pre-pivot fixtures stay valid).
    # credential: NOT excavatable (a degree cannot be recovered from memory) —
    #   a strategy note instead (see careerkit.strategy).
    # tenure: computed deterministically from the spine, never asked.
    kind: Literal["capability", "credential", "tenure"] = "capability"


class ParsedJD(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source: str
    title_to_mirror: str
    role_family: str
    seniority: str
    # The target company, used only for the ranker's target-affinity signal.
    # Optional so pre-existing parsed JDs stay valid.
    company: str | None = None
    # User-picked from a menu, never auto-classified. Aliased because
    # "register" shadows a BaseModel attribute.
    register_choice: str | None = Field(default=None, alias="register")
    requirements: list[Requirement]
    unknown_terms: list[str] = Field(default_factory=list)
