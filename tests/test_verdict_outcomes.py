"""careerkit verdict and careerkit outcomes: the honest call first, and the
record that outlives the search."""

from __future__ import annotations

from pathlib import Path

from careerkit.coverage import assess_jd
from careerkit.dataload import load_declined, load_parsed_jd, load_spine, load_units
from careerkit.jd import ParsedJD, Requirement
from careerkit.outcomes import build_ledger
from careerkit.outcomes import render as render_ledger
from careerkit.paths import SAMPLE_CORPUS
from careerkit.strategy import tenure_findings
from careerkit.terms import TermDecision
from careerkit.verdict import build_verdict, render

DATA = SAMPLE_CORPUS / "data"
JD = SAMPLE_CORPUS / "jd" / "halcyon-solutions-engineer-parsed.json"


def _corpus():
    return (load_units(DATA / "evidence"), load_spine(DATA / "spine.yaml"),
            load_declined(DATA / "declined.yaml"))


def test_sample_verdict_is_apply_with_probing_and_a_plain_no() -> None:
    units, spine, declined = _corpus()
    v = build_verdict(load_parsed_jd(JD), units, spine, declined)
    assert v.recommendation == "apply"
    assert v.required_counts["HIT"] == 3 and v.required_counts["THIN"] == 1
    assert v.name_in_the_letter == []
    assert any("security questionnaires" in p for p in v.expect_probing)
    assert any("Kubernetes" in s for s in v.say_no_plainly)  # the declined record's words
    assert v.tenure and "roles carrying customer-facing span 2012 to 2026 = 14 years" in v.tenure[0]
    assert v.credentials and "not a gate" in v.credentials[0]
    assert v.hard_gates == []


def test_tenure_is_computed_from_the_spine_not_typed() -> None:
    """A tagged tenure want scores the roles that carry the tag, not the
    whole timeline. The first verdict on a live posting said 31 years against
    a customer-facing want the page itself put at six."""
    units, spine, declined = _corpus()
    jd = load_parsed_jd(JD)
    (tagged,) = tenure_findings(assess_jd(jd, units, spine, declined), spine, units)
    assert tagged.required_years == 5 and tagged.actual_years == 14 and tagged.meets is True
    (whole,) = tenure_findings(assess_jd(jd, units, spine, declined), spine)
    assert whole.actual_years == 17  # 2009 to 2026: the arithmetic without units
    short = ParsedJD(source="x", title_to_mirror="T", role_family="f", seniority="s",
                     requirements=[Requirement(id="t", text="20+ years of SSO work",
                                               skills=["sso"], weight="required",
                                               kind="tenure")])
    v = build_verdict(short, units, spine, declined)
    assert v.recommendation == "hard-gate"
    assert any("roles carrying sso span" in g for g in v.hard_gates)


def test_a_required_miss_means_name_the_gap() -> None:
    units, spine, declined = _corpus()
    jd = ParsedJD(source="x", title_to_mirror="T", role_family="f", seniority="s",
                  requirements=[Requirement(id="r", text="Ships production Rust services",
                                            skills=["rust"], weight="required")])
    v = build_verdict(jd, units, spine, declined)
    assert v.recommendation == "name-the-gap"
    assert "Rust" in v.name_in_the_letter[0] and "nothing in the record" in v.name_in_the_letter[0]


def test_unmapped_required_wants_never_count_as_hits() -> None:
    """The coverage engine scores an empty skills list as HIT. On the first
    real inbox that made a posting with twenty unmapped terms read 10/0/0/0."""
    units, spine, declined = _corpus()
    reqs = [Requirement(id="a", text="Hands-on SSO", skills=["sso"], weight="required"),
            Requirement(id="b", text="Deep OpenTelemetry experience", skills=[], weight="required"),
            Requirement(id="c", text="Refinery sampling", skills=[], weight="required"),
            Requirement(id="d", text="Go", skills=[], weight="preferred")]
    jd = ParsedJD(source="x", title_to_mirror="T", role_family="f", seniority="s",
                  requirements=reqs)
    v = build_verdict(jd, units, spine, declined)
    assert v.required_counts["HIT"] == 1 and sum(v.required_counts.values()) == 1
    assert v.unmapped_required == ["Deep OpenTelemetry experience", "Refinery sampling"]
    assert v.unmapped_preferred == ["Go"]
    assert v.recommendation == "unmapped"  # two unmapped outnumber one hit
    md = render(v)
    assert "plus 2 the parse could not map" in md
    assert "## Required, and the record has no tag for it" in md


def test_a_stated_credential_without_equivalence_is_a_hard_gate() -> None:
    units, spine, declined = _corpus()
    jd = ParsedJD(source="x", title_to_mirror="T", role_family="f", seniority="s",
                  requirements=[Requirement(id="deg", text="Bachelor's degree in Computer Science",
                                            skills=["sso"], weight="required", kind="credential")])
    v = build_verdict(jd, units, spine, declined)
    assert v.recommendation == "hard-gate"
    assert "Bachelor" in v.hard_gates[0]
    md = render(v)
    assert md.startswith("# Verdict: T")
    assert "no document should argue it" in md
    assert "—" not in md


def _manifest(path: Path, **fields: str) -> None:
    path.mkdir(parents=True)
    body = "".join(f"{k}: {v}\n" for k, v in fields.items())
    (path / "manifest.yaml").write_text(body, encoding="utf-8")


def test_ledger_reads_every_manifest_and_counts_the_sent(tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    _manifest(runs / "2026-08-01-a", company="A", role="SE", captured="2026-08-01",
              status="sent", outcome="rejected", outcome_date="2026-08-20",
              outcome_notes="'we went with an internal candidate'")
    _manifest(runs / "2026-08-05-b", company="B", role="FDE", captured="2026-08-05", status="sent")
    _manifest(runs / "2026-08-09-c", company="C", role="TA", captured="2026-08-09",
              status="on-hold-at-cp2")
    ledger = build_ledger(tmp_path)  # the parent works as well as the runs dir
    assert [r.company for r in ledger.rows] == ["A", "B", "C"]
    assert ledger.by_outcome() == {"no response yet": 1, "rejected": 1}
    assert ledger.by_status() == {"on-hold-at-cp2": 1, "sent": 2}
    md = render_ledger(ledger)
    assert "3 runs, 2 sent." in md
    assert "internal candidate" in md


def test_an_export_block_is_exported_not_sent(tmp_path: Path) -> None:
    """Three packages sat exported and unsent for a week. Only the status
    says sent."""
    runs = tmp_path / "runs"
    (runs / "r").mkdir(parents=True)
    (runs / "r" / "manifest.yaml").write_text(
        "company: X\nrole: Y\ncaptured: 2026-08-01\nstatus: ready-to-send\nexport:\n  drive: http://x\n",
        encoding="utf-8")
    (row,) = build_ledger(runs).rows
    assert row.exported is True and row.sent is False
    assert "1 exported and not sent" in render_ledger(build_ledger(runs))


def test_sample_run_makes_a_one_row_ledger() -> None:
    ledger = build_ledger(SAMPLE_CORPUS.parent / "sample-run")
    assert len(ledger.rows) == 0 or ledger.rows[0].company == "Halcyon Robotics"


def test_a_decided_term_leaves_the_unmapped_list() -> None:
    units, spine, declined = _corpus()
    jd = ParsedJD(
        source="x", title_to_mirror="x", role_family="x", seniority="x",
        requirements=[Requirement(id="obj", text="Address technical objections",
                                  skills=[], weight="required")],
        unknown_terms=["technical objections", "data residency"],
    )
    decision = TermDecision(term="technical objections", decision="alias",
                            tag="stakeholder-guidance", note="handled them", date="2026-09-02")
    v = build_verdict(jd, units, spine, declined, [decision])
    assert v.unknown_terms == ["data residency"]
    assert "technical objections" not in render(v)
