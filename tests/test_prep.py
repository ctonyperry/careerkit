"""careerkit prep: the corpus re-sorted around the questions a run invites."""

from __future__ import annotations

from careerkit.paths import SAMPLE_CORPUS
from careerkit.prep import build_prep, claim_rows, render

RUN = SAMPLE_CORPUS.parent / "sample-run"
DATA = SAMPLE_CORPUS / "data"


def test_claim_rows_read_the_evidence_table_in_page_order() -> None:
    rows = claim_rows((RUN / "claim-sheet.md").read_text(encoding="utf-8"))
    assert rows[0].section == "Lantern"
    assert rows[0].unit_ids == ["lantern-sso-rollouts"]
    assert rows[-1].unit_ids == ["helpdesk-early"]  # a spine role id, not a unit


def test_prep_lists_only_cited_units_and_keeps_their_bounds_verbatim() -> None:
    sheet = build_prep(RUN, DATA)
    ids = [u.unit_id for u in sheet.units]
    assert "lantern-scim-rate-limit" in ids
    assert "brightline-enablement" not in ids  # excluded on purpose, so not prepped
    rate = next(u for u in sheet.units if u.unit_id == "lantern-scim-rate-limit")
    # The note also says "interview-defensible", so it files under on_record;
    # the point is that the bound reaches the sheet verbatim, wherever it files.
    assert any("Never render as" in b for b in rate.bounds + rate.on_record)
    assert rate.doubted_figures == ["$4M contract"]
    assert rate.safe_figures == ["roughly 300,000 users"]
    assert "$4M" in rate.never_say


def test_prep_separates_interview_answers_already_on_record() -> None:
    sheet = build_prep(RUN, DATA)
    sso = next(u for u in sheet.units if u.unit_id == "lantern-sso-rollouts")
    assert len(sso.on_record) == 1
    assert "attribute" in sso.on_record[0]
    assert not any("interview" in b.lower() for b in sso.bounds)


def test_prep_surfaces_open_verifies_and_the_declined_probe() -> None:
    sheet = build_prep(RUN, DATA)
    sec = next(u for u in sheet.units if u.unit_id == "lantern-security-questionnaires")
    assert sec.verify and "bridge letter" in sec.verify[0]
    statuses = {p.status for p in sheet.probes}
    assert "DECLINED" in statuses
    infra = next(p for p in sheet.probes if p.status == "DECLINED")
    assert "Kubernetes" in infra.detail  # the person's own words, from declined.yaml
    assert sheet.unknown_terms == ["Halcyon Fleet API", "ROS 2"]


def test_render_is_readable_and_names_the_safe_figure() -> None:
    md = render(build_prep(RUN, DATA))
    assert md.startswith("# Prep: Solutions Engineer at Halcyon Robotics")
    assert "## Settle before the room" in md
    assert 'you doubt "$4M contract". Say roughly 300,000 users instead.' in md
    assert "## Where the questions will land" in md
    assert "—" not in md
