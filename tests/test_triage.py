"""careerkit triage: the inbox, ranked, with the parse validated."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from careerkit.paths import SAMPLE_CORPUS
from careerkit.triage import build_triage, render

DATA = SAMPLE_CORPUS / "data"
JD_MD = SAMPLE_CORPUS / "jd" / "halcyon-solutions-engineer.md"
JD_JSON = SAMPLE_CORPUS / "jd" / "halcyon-solutions-engineer-parsed.json"


def _inbox(tmp_path: Path) -> Path:
    inbox = tmp_path / "jd-inbox"
    inbox.mkdir()
    # 1. parsed and valid
    shutil.copy(JD_MD, inbox / "2026-09-01-halcyon-se.md")
    shutil.copy(JD_JSON, inbox / "2026-09-01-halcyon-se-parsed.json")
    # 2. parsed with an invented tag
    shutil.copy(JD_MD, inbox / "2026-09-02-bogus-se.md")
    parsed = json.loads(JD_JSON.read_text(encoding="utf-8"))
    parsed["requirements"][1]["skills"] = ["sso", "quantum-sso"]
    (inbox / "2026-09-02-bogus-se-parsed.json").write_text(json.dumps(parsed), encoding="utf-8")
    # 3. not parsed yet
    shutil.copy(JD_MD, inbox / "2026-09-03-unparsed-se.md")
    # 4. not pending any more: ignored entirely
    text = JD_MD.read_text(encoding="utf-8").replace("status: pending", "status: run")
    (inbox / "2026-09-04-done-se.md").write_text(text, encoding="utf-8")
    return inbox


def test_triage_ranks_verdicts_first_then_invalid_then_unparsed(tmp_path: Path) -> None:
    t = build_triage(_inbox(tmp_path), DATA)
    assert [r.state for r in t.rows] == ["apply", "parse-invalid", "unparsed"]
    assert t.rows[1].bad_tags == ["quantum-sso"]
    assert t.rows[0].verdict is not None and t.rows[0].verdict.required_counts["HIT"] == 3


def test_render_names_the_parse_queue(tmp_path: Path) -> None:
    md = render(build_triage(_inbox(tmp_path), DATA))
    assert "| 1 | Halcyon Robotics | Solutions Engineer | **apply** | 3/1/0/0 | 0 |" in md
    assert "tags not in skills.yaml: quantum-sso" in md
    assert "Parse next" in md and "2026-09-03-unparsed-se.md" in md
    assert "1 apply, 1 parse-invalid, 1 unparsed." in md
    assert "—" not in md


def test_empty_inbox(tmp_path: Path) -> None:
    (tmp_path / "jd-inbox").mkdir()
    assert render(build_triage(tmp_path / "jd-inbox", DATA)) == "Nothing pending.\n"
