from pathlib import Path

import yaml

from careerkit.dataload import load_declined, load_units
from careerkit.models import Status, Tier
from careerkit.session import (
    IngestSession,
    SessionDecline,
    SessionPlacement,
    decline_to_record,
    placement_to_unit,
    write_session,
)


def test_placement_becomes_provisional_memory_unit() -> None:
    existing: set[str] = set()
    unit = placement_to_unit(
        SessionPlacement(
            want_id="networking",
            role_id="athenaonline",
            text="Ran the colo network: firewalls, NAT, load balancing.",
            skills=["networking", "infrastructure"],
        ),
        existing,
    )
    assert unit.role == "athenaonline"
    assert unit.tier is Tier.MEMORY
    assert unit.status is Status.PROVISIONAL
    assert unit.skills == ["networking", "infrastructure"]
    assert unit.verify  # carries the ramble [VERIFY]
    assert unit.id == "session-networking"


def test_placement_ids_are_unique() -> None:
    existing = {"session-networking"}
    unit = placement_to_unit(
        SessionPlacement(want_id="networking", role_id="ims", text="x"), existing
    )
    assert unit.id == "session-networking-2"


def test_decline_to_record_is_dated_negative_evidence() -> None:
    rec = decline_to_record(
        SessionDecline(want_id="crypto", text="crypto custody", skills=["scim"]),
        date="2026-07-02",
    )
    assert rec.skills == ["scim"]
    assert rec.date == "2026-07-02"
    assert "web UI" in (rec.note or "")


def test_write_session_persists_units_and_declines(tmp_path: Path) -> None:
    data = tmp_path / "data"
    (data / "evidence").mkdir(parents=True)
    (data / "declined.yaml").write_text("declined: []\n", encoding="utf-8")

    session = IngestSession(
        jd_source="examples/ripple-jd.md",
        placements=[
            SessionPlacement(
                want_id="networking",
                role_id="athenaonline",
                text="Ran the colo network end to end.",
                skills=["networking"],
            )
        ],
        declines=[SessionDecline(want_id="crypto", text="crypto custody", skills=[])],
    )
    result = write_session(session, data, date="2026-07-02")

    assert result.created_units == ["session-networking"]
    units = load_units(data / "evidence")
    assert len(units) == 1
    assert units[0].status is Status.PROVISIONAL

    declines = load_declined(data / "declined.yaml")
    assert len(declines) == 1
    assert declines[0].text == "crypto custody"

    # Written YAML is round-trippable and clean.
    raw = yaml.safe_load((data / "evidence" / "session-networking.yaml").read_text())
    assert raw["role"] == "athenaonline"
    assert raw["tier"] == "MEMORY"
