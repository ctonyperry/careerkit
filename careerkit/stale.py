"""Which units to re-ask about.

A MEMORY-tier fact is a recollection, and recollections drift. The corpus can
only show that if every unit carries when it was last stood behind. This lists
units oldest-first, MEMORY tier first within the same age, and treats a unit
with no `confirmed_on` at all as the oldest thing in the file, because it is:
nobody has ever dated it.

    careerkit stale                 # everything, oldest first
    careerkit stale --older-than 365 # only units not confirmed in a year

The output is a question list, not a verdict. A unit being old does not make
it wrong; it makes it worth a read.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

from careerkit.models import EvidenceUnit, Tier

_TIER_ORDER = {Tier.MEMORY: 0, Tier.DOC: 1, Tier.PRIMARY: 2}


@dataclass
class StaleEntry:
    unit: EvidenceUnit
    age_days: int | None  # None: never dated

    @property
    def label(self) -> str:
        if self.age_days is None:
            return "never dated"
        return f"{self.age_days}d"


def _parse(date: str | None) -> _dt.date | None:
    if not date:
        return None
    try:
        return _dt.date.fromisoformat(str(date)[:10])
    except ValueError:
        return None


def stale_units(
    units: list[EvidenceUnit],
    *,
    older_than_days: int | None = None,
    today: _dt.date | None = None,
) -> list[StaleEntry]:
    today = today or _dt.date.today()
    out: list[StaleEntry] = []
    for u in units:
        d = _parse(u.confirmed_on)
        age = (today - d).days if d else None
        if older_than_days is not None and age is not None and age < older_than_days:
            continue
        out.append(StaleEntry(unit=u, age_days=age))
    # Undated first, then oldest, then weakest tier.
    out.sort(key=lambda e: (e.age_days is not None, -(e.age_days or 0),
                            _TIER_ORDER[e.unit.tier]))
    return out


def render(entries: list[StaleEntry]) -> str:
    if not entries:
        return "nothing stale."
    width = max(len(e.unit.id) for e in entries)
    lines = [f"{'UNIT':<{width}}  {'AGE':>11}  TIER     STATUS"]
    for e in entries:
        lines.append(
            f"{e.unit.id:<{width}}  {e.label:>11}  {e.unit.tier.value:<8} {e.unit.status.value}"
        )
    return "\n".join(lines)
