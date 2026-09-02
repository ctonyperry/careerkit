from pathlib import Path

from conftest import DATA_DIR

from careerkit.dataload import AliasTable, load_declined
from careerkit.models import EvidenceUnit


def test_unit_skills_exist_in_alias_table(
    units: list[EvidenceUnit], aliases: AliasTable
) -> None:
    # Every tag on a unit must be a canonical tag; otherwise coverage
    # silently misses it.
    for unit in units:
        for skill in unit.skills:
            assert skill in aliases.canonical_tags, f"{unit.id}: unknown tag {skill}"


def test_shipped_declined_file_loads() -> None:
    # Grows only by the author's confirmation (first records: 2026-08-24). Assert
    # the file parses and every record carries the required fields — never
    # pin the count (see CLAUDE.md: the corpus grows).
    records = load_declined(DATA_DIR / "declined.yaml")
    for rec in records:
        assert rec.text
        assert rec.date


def test_missing_declined_file_is_no_declines(tmp_path: Path) -> None:
    assert load_declined(tmp_path / "nope.yaml") == []


def test_declined_records_parse(tmp_path: Path) -> None:
    p = tmp_path / "declined.yaml"
    p.write_text(
        "declined:\n"
        "  - text: Never managed a Kubernetes cluster\n"
        "    skills: [infrastructure]\n"
        "    date: '2026'\n"
        "    note: asked in an early run\n",
        encoding="utf-8",
    )
    records = load_declined(p)
    assert len(records) == 1
    assert records[0].skills == ["infrastructure"]
    assert records[0].date == "2026"


def test_alias_resolution(aliases: AliasTable) -> None:
    assert aliases.resolve("single sign-on") == "sso"
    assert aliases.resolve("SAML") == "sso"  # case-insensitive
    assert aliases.resolve("scim") == "scim"  # canonical passes through
    assert aliases.resolve("blockchain") is None
