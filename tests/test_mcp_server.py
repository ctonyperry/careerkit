"""The MCP surface: the same functions, reachable from a conversation."""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

import pytest

from careerkit import mcp_server as srv
from careerkit.paths import SAMPLE_CORPUS


@pytest.fixture
def runs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A runs directory with the sample posting and its parse, on a copied corpus."""
    corpus = tmp_path / "corpus"
    shutil.copytree(SAMPLE_CORPUS, corpus)
    root = tmp_path / "runs-root"
    inbox = root / "jd-inbox"
    inbox.mkdir(parents=True)
    shutil.copy(SAMPLE_CORPUS / "jd" / "halcyon-solutions-engineer.md",
                inbox / "2026-09-01-halcyon-se.md")
    shutil.copy(SAMPLE_CORPUS / "jd" / "halcyon-solutions-engineer-parsed.json",
                inbox / "2026-09-01-halcyon-se-parsed.json")
    shutil.copytree(SAMPLE_CORPUS.parent / "sample-run", root / "runs" / "halcyon")
    monkeypatch.setenv("CAREERKIT_CORPUS", str(corpus))
    monkeypatch.setenv("CAREERKIT_RUNS", str(root))
    return root


def test_tools_register_with_their_docstrings() -> None:
    pytest.importorskip("mcp")
    server = srv.build_server()
    tools = asyncio.run(server.list_tools())
    names = {t.name for t in tools}
    assert names == {fn.__name__ for fn in srv.TOOLS}
    assert all(t.description for t in tools)


def test_read_tools_render_from_the_env(runs: Path) -> None:
    assert "halcyon-se" in srv.inbox_pending()
    assert "| 1 | Halcyon Robotics |" in srv.triage_table()
    assert srv.verdict_for("jd-inbox/2026-09-01-halcyon-se-parsed.json").startswith("# Verdict:")
    assert "Prep: Solutions Engineer" in srv.prep_sheet("halcyon")
    assert "1 runs" in srv.outcomes_table()
    assert "brightline-enablement" in srv.stale_units()


def test_decide_records_only_what_the_person_said(runs: Path) -> None:
    queue_before = srv.terms_queue()
    assert "Nothing to decide" in queue_before  # the sample decided its two terms already
    bad = srv.terms_decide("Fleet telemetry", "alias", tag="not-a-tag")
    assert bad.startswith("'not-a-tag' is not")
    assert srv.terms_decide("Fleet telemetry", "alias") == "an alias needs the tag it maps to"
    assert srv.terms_decide("Fleet telemetry", "maybe") == "decision must be alias, gap or ignore"
    ok = srv.terms_decide("Fleet telemetry", "alias", tag="telemetry",
                          note="same idea as the xAPI work")
    assert ok == "recorded: 'Fleet telemetry' -> alias telemetry"
    again = srv.terms_decide("fleet telemetry", "gap")
    assert "already has a decision" in again


def test_missing_runs_env_is_a_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CAREERKIT_RUNS", raising=False)
    with pytest.raises(RuntimeError, match="CAREERKIT_RUNS"):
        srv.inbox_pending()


def test_server_relays_a_missing_env_as_text(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("mcp")
    monkeypatch.delenv("CAREERKIT_RUNS", raising=False)
    server = srv.build_server()
    result = asyncio.run(server.call_tool("inbox_pending", {}))
    text = result[0].text if isinstance(result, list) else str(result)
    assert "CAREERKIT_RUNS" in text


def test_tags_list_is_the_closed_vocabulary_and_bad_tags_point_back_at_it(runs: Path) -> None:
    """The chat once offered invented tags, then unit ids. It had no way to see
    the vocabulary, and the refusal did not say where to look."""
    listing = srv.tags_list()
    assert listing.startswith("5") or listing[0].isdigit()  # "<n> tags ..."
    assert "telemetry" in listing and "sso  (" in listing
    narrowed = srv.tags_list("provision")
    assert "scim" in narrowed and "\ntelemetry" not in narrowed
    refusal = srv.terms_decide("leading projects", "alias", tag="technical-leadership")
    assert "Not recorded" in refusal and "tags_list" in refusal
    assert "Nearest by name" in refusal and "technical-writing" in refusal
    unit_as_tag = srv.terms_decide("leading projects", "alias", tag="lantern-sso-rollouts")
    assert "Not recorded" in unit_as_tag
