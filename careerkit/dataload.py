"""Loaders for the flat-file career data. Deterministic; no LLM anywhere."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from careerkit.jd import ParsedJD
from careerkit.models import DeclinedRecord, EvidenceUnit, Spine


class AliasTable:
    """Maps JD language to canonical skill tags. Grows only by confirmation."""

    def __init__(self, aliases: dict[str, list[str]]) -> None:
        self._canonical: frozenset[str] = frozenset(aliases)
        self._lookup: dict[str, str] = {tag.lower(): tag for tag in aliases}
        for tag, terms in aliases.items():
            for term in terms:
                self._lookup[term.lower()] = tag

    @property
    def canonical_tags(self) -> frozenset[str]:
        return self._canonical

    @property
    def phrases(self) -> dict[str, str]:
        """Every known phrase (tags included), lowercased, to its tag."""
        return dict(self._lookup)

    def resolve(self, term: str) -> str | None:
        return self._lookup.get(term.lower())


def _read_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_spine(path: Path) -> Spine:
    return Spine.model_validate(_read_yaml(path))


def load_units(evidence_dir: Path) -> list[EvidenceUnit]:
    units = [
        EvidenceUnit.model_validate(_read_yaml(p))
        for p in sorted(evidence_dir.glob("*.yaml"))
    ]
    seen: set[str] = set()
    for unit in units:
        if unit.id in seen:
            raise ValueError(f"duplicate evidence unit id: {unit.id}")
        seen.add(unit.id)
    # A superseded unit stays on disk as history and stops being evidence.
    # Before this, two units recorded their replacement in a prose note and the
    # gap engine kept scoring both, which double-counted the same fact.
    replaced = {u.supersedes for u in units if u.supersedes}
    return [u for u in units if u.id not in replaced]


def load_aliases(path: Path) -> AliasTable:
    """The alias table, plus every alias the person confirmed in the sibling
    terms.yaml. skills.yaml stays hand-owned; confirmations accrete beside it."""
    raw = _read_yaml(path)
    aliases: dict[str, list[str]] = {
        tag: list(terms or []) for tag, terms in raw["aliases"].items()
    }
    terms_path = path.with_name("terms.yaml")
    if terms_path.exists():
        for t in (_read_yaml(terms_path) or {}).get("terms") or []:
            if t.get("decision") == "alias" and t.get("tag") in aliases:
                aliases[t["tag"]].append(str(t["term"]))
    return AliasTable(aliases)


def load_declined(path: Path) -> list[DeclinedRecord]:
    """Load negative-evidence records. Missing/empty file -> no declines."""
    if not path.exists():
        return []
    raw = _read_yaml(path)
    records = (raw or {}).get("declined") or []
    return [DeclinedRecord.model_validate(r) for r in records]


def load_parsed_jd(path: Path) -> ParsedJD:
    with path.open(encoding="utf-8") as f:
        return ParsedJD.model_validate(json.load(f))
