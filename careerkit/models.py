"""Data model for the career file. See implementation-design.md."""

from __future__ import annotations

import datetime
import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


class Tier(StrEnum):
    """Provenance reliability. PRIMARY/DOC are grounded; MEMORY needs ownership."""

    PRIMARY = "PRIMARY"
    DOC = "DOC"
    MEMORY = "MEMORY"


class Status(StrEnum):
    CONFIRMED = "confirmed"
    PROVISIONAL = "provisional"


class Metric(BaseModel):
    value: str
    tier: Tier
    # Confirmation and doubt are symmetric. When the author stops standing behind a
    # figure, it must stop legitimising that number in a draft, not merely fail
    # to be promoted. A doubted metric is excluded from the linter's allowed set,
    # so printing it blocks as number-without-source.
    doubted: bool = False


class Car(BaseModel):
    challenge: str | None = None
    action: str | None = None
    result: str | None = None


def _iso(value: Any) -> Any:
    """YAML hands back a real date for an unquoted 2026-08-25. Keep the field a
    string so hand-typed values like 'Aug 2026' survive too, and so the file
    can be edited without knowing which spellings the parser turns into
    objects. The first migration wrote 23 unquoted dates and every test that
    loaded the corpus failed on the first one."""
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()[:10]
    return value


class Correction(BaseModel):
    """A dated change to what a unit says. History, kept off the rules."""

    date: str
    text: str

    _norm_date = field_validator("date", mode="before")(_iso)


class EvidenceUnit(BaseModel):
    id: str
    role: str | None
    kind: str = "role-evidence"
    narrative: str
    car: Car | None = None
    metrics: list[Metric] = Field(default_factory=list)
    skills: list[str]
    tier: Tier
    status: Status
    # Optional public artifact URL (repo, npm, published work). Verifiable
    # artifacts are the non-traditional candidate's substitute for credentials.
    link: str | None = None
    # When and by whom this unit was last stood behind. Prose notes carried
    # "author-confirmed 2026-08-25" on thirty-two units and nothing could ask
    # "what has not been re-confirmed in a year?". A MEMORY-tier fact decays;
    # this is how the corpus shows its age. See SPINE-SPEC.md.
    confirmed_on: str | None = None
    confirmed_by: str | None = None
    # The unit this one replaces. The loader drops the superseded unit so the
    # gap engine stops counting it; the file stays as history. Two units did
    # this by a prose note and the old unit kept scoring.
    supersedes: str | None = None
    # Standing bounds only: what a rendering may and may not do, in the
    # person's own words, dated. Corrections go in `history`, so a reader gets
    # the rule without the changelog it accreted from.
    render_notes: list[str] = Field(default_factory=list)
    history: list[Correction] = Field(default_factory=list)
    verify: list[str] = Field(default_factory=list)

    _norm_confirmed_on = field_validator("confirmed_on", mode="before")(_iso)
    # Literal strings that must never reach a sent document, whatever the
    # coverage maths says: a figure the author no longer trusts, an artifact he is not
    # ready to share, a customer name that stays generic. Render notes carry the
    # reasoning; this carries the enforcement.
    do_not_print: list[str] = Field(default_factory=list)


class DeclinedRecord(BaseModel):
    """Negative evidence: something the author confirmed he has NOT done.

    Feeds DECLINED coverage — the skill is never re-asked and drives a
    poor-fit strategy note instead of a recovery question.
    """

    text: str
    skills: list[str]
    date: str | None = None
    note: str | None = None


class Identity(BaseModel):
    legal_name: str
    goes_by: str
    resume_header: str
    email: str
    phone: str
    linkedin: str
    location: str
    notes: list[str] = Field(default_factory=list)


class SpineRole(BaseModel):
    id: str
    org: str
    title: str
    start: str
    end: str
    titles: list[str] = Field(default_factory=list)
    type: str | None = None
    notes: list[str] = Field(default_factory=list)
    corrections: list[str] = Field(default_factory=list)
    render_notes: list[str] = Field(default_factory=list)

    def end_year(self) -> int | None:
        """Extract a sortable year from the display string ('Jun 2026', 'Early 1999')."""
        match = _YEAR_RE.search(self.end)
        return int(match.group(0)) if match else None

    def start_year(self) -> int | None:
        """Extract a sortable year from the start display string ('Summer 1998', '~2018')."""
        match = _YEAR_RE.search(self.start)
        return int(match.group(0)) if match else None


class Education(BaseModel):
    items: list[str] = Field(default_factory=list)
    framing: str | None = None


class Spine(BaseModel):
    identity: Identity
    roles: list[SpineRole]
    education: Education | None = None

    def role_by_id(self, role_id: str) -> SpineRole | None:
        return next((r for r in self.roles if r.id == role_id), None)
