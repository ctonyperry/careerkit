"""Persist a web-UI excavation session into the corpus.

The web UI never writes career data directly (a red-team rule: writes go through
validated Python, and the author reviews what lands). A session is the UI's output:
cards the user placed (four-beat answers) and wants they declined. This module
turns them into provisional evidence units and declined records on disk.

Everything written is `status: provisional, tier: MEMORY` and carries a
[VERIFY] that it is a raw interview ramble needing structure before finalize.
Nothing is ever confirmed here; ingest only stages, exactly like the chat loop.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from careerkit.dataload import load_declined, load_units
from careerkit.models import DeclinedRecord, EvidenceUnit, Status, Tier

_RAMBLE_VERIFY = (
    "Raw from a UI interview ramble. Structure into narrative/metrics and apply "
    "the smaller-reading before any resume uses it."
)


class SessionPlacement(BaseModel):
    want_id: str
    role_id: str  # the spine role the user tapped (an interview OUTPUT)
    text: str
    skills: list[str] = Field(default_factory=list)


class SessionDecline(BaseModel):
    want_id: str
    text: str
    skills: list[str] = Field(default_factory=list)


class IngestSession(BaseModel):
    jd_source: str
    placements: list[SessionPlacement] = Field(default_factory=list)
    declines: list[SessionDecline] = Field(default_factory=list)


class IngestResult(BaseModel):
    created_units: list[str] = Field(default_factory=list)
    added_declines: list[str] = Field(default_factory=list)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "want"


def _unique_id(base: str, existing: set[str]) -> str:
    if base not in existing:
        existing.add(base)
        return base
    n = 2
    while f"{base}-{n}" in existing:
        n += 1
    uid = f"{base}-{n}"
    existing.add(uid)
    return uid


def placement_to_unit(
    placement: SessionPlacement, existing_ids: set[str]
) -> EvidenceUnit:
    """Build a provisional MEMORY unit from a placed card. Pure; mutates the id set."""
    uid = _unique_id(f"session-{_slug(placement.want_id)}", existing_ids)
    return EvidenceUnit(
        id=uid,
        role=placement.role_id,
        narrative=placement.text,
        skills=placement.skills,
        tier=Tier.MEMORY,
        status=Status.PROVISIONAL,
        verify=[_RAMBLE_VERIFY],
    )


def decline_to_record(decline: SessionDecline, date: str) -> DeclinedRecord:
    return DeclinedRecord(
        text=decline.text,
        skills=decline.skills,
        date=date,
        note="declined via web UI session",
    )


def _unit_yaml(unit: EvidenceUnit) -> str:
    doc = {
        "id": unit.id,
        "role": unit.role,
        "narrative": unit.narrative,
        "skills": unit.skills,
        "tier": unit.tier.value,
        "status": unit.status.value,
        "link": unit.link,
        "verify": unit.verify,
    }
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=88)


def write_session(session: IngestSession, data_dir: Path, date: str) -> IngestResult:
    evidence_dir = data_dir / "evidence"
    existing_ids = {u.id for u in load_units(evidence_dir)}

    created: list[str] = []
    for placement in session.placements:
        unit = placement_to_unit(placement, existing_ids)
        (evidence_dir / f"{unit.id}.yaml").write_text(_unit_yaml(unit), encoding="utf-8")
        created.append(unit.id)

    declined_path = data_dir / "declined.yaml"
    records = load_declined(declined_path)
    new_records = [decline_to_record(d, date) for d in session.declines]
    if new_records:
        combined = [r.model_dump() for r in records + new_records]
        declined_path.write_text(
            yaml.safe_dump({"declined": combined}, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

    return IngestResult(
        created_units=created,
        added_declines=[d.want_id for d in session.declines],
    )
