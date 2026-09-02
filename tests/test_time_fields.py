"""The fields that let the corpus show its age. See SPINE-SPEC.md."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from careerkit.dataload import load_units
from careerkit.models import Correction, EvidenceUnit, Status, Tier
from careerkit.stale import stale_units


def _unit(uid: str, **kw) -> EvidenceUnit:
    base = dict(id=uid, role=None, narrative="x", skills=["python"],
                tier=Tier.MEMORY, status=Status.CONFIRMED)
    base.update(kw)
    return EvidenceUnit(**base)


def _write(dirpath: Path, uid: str, extra: str = "") -> None:
    (dirpath / f"{uid}.yaml").write_text(
        f"id: {uid}\nrole: null\nnarrative: x\nskills: [python]\n"
        f"tier: MEMORY\nstatus: confirmed\n{extra}",
        encoding="utf-8",
    )


def test_all_new_fields_are_optional_so_every_existing_unit_still_loads(tmp_path):
    _write(tmp_path, "old-style")
    (u,) = load_units(tmp_path)
    assert u.confirmed_on is None and u.confirmed_by is None
    assert u.supersedes is None and u.history == []


def test_history_is_typed_and_kept_apart_from_render_notes(tmp_path):
    _write(tmp_path, "u", "render_notes: [\"never claim X\"]\n"
                          "history:\n  - {date: '2026-08-26', text: 'title corrected'}\n")
    (u,) = load_units(tmp_path)
    assert u.render_notes == ["never claim X"]
    assert u.history == [Correction(date="2026-08-26", text="title corrected")]


def test_superseded_unit_is_dropped_by_the_loader_but_the_file_stays(tmp_path):
    _write(tmp_path, "old")
    _write(tmp_path, "new", "supersedes: old\n")
    ids = {u.id for u in load_units(tmp_path)}
    assert ids == {"new"}
    assert (tmp_path / "old.yaml").exists()


def test_supersedes_pointing_at_a_unit_already_gone_is_harmless(tmp_path):
    _write(tmp_path, "new", "supersedes: long-gone\n")
    assert [u.id for u in load_units(tmp_path)] == ["new"]


def test_stale_orders_undated_first_then_oldest_then_weakest_tier():
    today = dt.date(2026, 8, 26)
    units = [
        _unit("fresh", confirmed_on="2026-08-20", tier=Tier.PRIMARY),
        _unit("old-primary", confirmed_on="2025-01-01", tier=Tier.PRIMARY),
        _unit("old-memory", confirmed_on="2025-01-01", tier=Tier.MEMORY),
        _unit("undated"),
    ]
    order = [e.unit.id for e in stale_units(units, today=today)]
    assert order == ["undated", "old-memory", "old-primary", "fresh"]


def test_stale_older_than_filters_but_never_hides_undated():
    today = dt.date(2026, 8, 26)
    units = [_unit("fresh", confirmed_on="2026-08-20"),
             _unit("old", confirmed_on="2025-01-01"),
             _unit("undated")]
    ids = [e.unit.id for e in stale_units(units, older_than_days=365, today=today)]
    assert ids == ["undated", "old"]


def test_stale_reports_an_unparseable_date_as_undated():
    (e,) = stale_units([_unit("bad", confirmed_on="sometime in August")],
                       today=dt.date(2026, 8, 26))
    assert e.age_days is None and e.label == "never dated"


@pytest.mark.parametrize("date", ["2026-08-26", "2026-08-26T10:00:00"])
def test_stale_accepts_dates_with_or_without_time(date):
    (e,) = stale_units([_unit("u", confirmed_on=date)], today=dt.date(2026, 8, 27))
    assert e.age_days == 1
