"""careerkit terms: unmapped posting language, decided once, applied everywhere."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from careerkit.dataload import load_aliases, load_declined, load_parsed_jd, load_spine, load_units
from careerkit.jd import ParsedJD, Requirement
from careerkit.paths import SAMPLE_CORPUS
from careerkit.terms import (
    TermDecision,
    alias_additions,
    apply_decisions,
    build_queue,
    load_terms,
    record,
    render_queue,
    suggest_tag,
)
from careerkit.verdict import build_verdict

DATA = SAMPLE_CORPUS / "data"
JD_JSON = SAMPLE_CORPUS / "jd" / "halcyon-solutions-engineer-parsed.json"


def _jd(*reqs: Requirement, unknown: list[str] | None = None) -> ParsedJD:
    return ParsedJD(source="x", title_to_mirror="T", role_family="f", seniority="s",
                    company="Halcyon", requirements=list(reqs), unknown_terms=unknown or [])


def test_record_appends_and_refuses_a_second_decision_on_the_same_term(tmp_path: Path) -> None:
    path = tmp_path / "terms.yaml"
    record(path, TermDecision(term="observability", decision="alias", tag="telemetry",
                              note="same thing"))
    record(path, TermDecision(term="OpenTelemetry", decision="gap", note="never used it"))
    record(path, TermDecision(term="ROS 2", decision="ignore"))
    loaded = load_terms(path)
    assert [t.decision for t in loaded] == ["alias", "gap", "ignore"]
    assert loaded[0].tag == "telemetry" and loaded[0].date
    with pytest.raises(ValueError):
        record(path, TermDecision(term="opentelemetry", decision="ignore"))
    with pytest.raises(ValueError):
        record(path, TermDecision(term="Go", decision="alias"))  # no tag
    assert alias_additions(loaded) == {"telemetry": ["observability"]}


def test_alias_decisions_join_the_alias_table_without_touching_skills_yaml(tmp_path: Path) -> None:
    data = tmp_path / "data"
    shutil.copytree(DATA, data)
    before = (data / "skills.yaml").read_text(encoding="utf-8")
    record(data / "terms.yaml",
           TermDecision(term="observability", decision="alias", tag="telemetry"))
    aliases = load_aliases(data / "skills.yaml")
    assert aliases.resolve("observability") == "telemetry"
    assert (data / "skills.yaml").read_text(encoding="utf-8") == before


def test_queue_dedupes_across_postings_skips_decided_and_suggests(tmp_path: Path) -> None:
    aliases = load_aliases(DATA / "skills.yaml")
    a = tmp_path / "a-parsed.json"
    b = tmp_path / "b-parsed.json"
    a.write_text(_jd(Requirement(id="r", text="Deep OpenTelemetry experience", skills=[],
                                 weight="required"),
                     unknown=["OpenTelemetry", "Observability", "Go"]
                     ).model_dump_json(by_alias=True), encoding="utf-8")
    jd_b = _jd(unknown=["opentelemetry", "user provisioning", "SCIM provisioning"])
    jd_b = jd_b.model_copy(update={"company": "Beta"})
    b.write_text(jd_b.model_dump_json(by_alias=True), encoding="utf-8")
    terms = [TermDecision(term="Go", decision="gap")]
    queue = build_queue([a, b], terms, aliases)
    names = [q.term for q in queue]
    assert names[0] == "OpenTelemetry" and queue[0].postings == ["Halcyon", "Beta"]
    assert queue[0].in_required_want is True
    assert "Go" not in names  # decided
    assert "user provisioning" not in names  # an exact alias resolves; nothing to decide
    assert "SCIM provisioning" in names  # not exact, so it is asked, with a suggestion
    assert suggest_tag("SCIM provisioning", aliases) == "scim"
    assert suggest_tag("data migration", aliases) == "migration"
    md = render_queue(queue)
    assert "| OpenTelemetry | 2: Halcyon, Beta | yes |" in md and "--gap" in md


def test_decisions_change_the_verdict() -> None:
    units, spine, declined = (load_units(DATA / "evidence"), load_spine(DATA / "spine.yaml"),
                              load_declined(DATA / "declined.yaml"))
    jd = _jd(Requirement(id="a", text="Hands-on SSO", skills=["sso"], weight="required"),
             Requirement(id="b", text="Owns the identity provider setup", skills=[],
                         weight="required"),
             Requirement(id="c", text="Deep OpenTelemetry experience", skills=[],
                         weight="required"),
             Requirement(id="d", text="Familiarity with ROS 2", skills=[], weight="preferred"))
    before = build_verdict(jd, units, spine, declined)
    assert before.recommendation == "unmapped" and len(before.unmapped_required) == 2
    terms = [TermDecision(term="identity provider", decision="alias", tag="idp-configuration"),
             TermDecision(term="OpenTelemetry", decision="gap", note="never used it"),
             TermDecision(term="ROS 2", decision="gap")]
    after = build_verdict(jd, units, spine, declined, terms)
    assert after.unmapped_required == []
    assert after.required_counts["MISS"] == 1
    assert after.recommendation == "name-the-gap"
    assert any("OpenTelemetry: a gap you recorded" in g for g in after.name_in_the_letter)
    assert any("ROS 2: a gap you recorded" in g for g in after.say_no_plainly)
    remapped = apply_decisions(jd, terms)
    assert remapped.requirements[1].skills == ["idp-configuration"]
    assert jd.requirements[1].skills == []  # the parse on disk is untouched


def test_sample_corpus_terms_file_loads_and_is_applied() -> None:
    terms = load_terms(DATA / "terms.yaml")
    assert {t.decision for t in terms} == {"alias", "gap", "ignore"}
    jd = load_parsed_jd(JD_JSON)
    units, spine, declined = (load_units(DATA / "evidence"), load_spine(DATA / "spine.yaml"),
                              load_declined(DATA / "declined.yaml"))
    v = build_verdict(jd, units, spine, declined, terms)
    assert any("ROS 2: a gap you recorded" in g for g in v.say_no_plainly)
    on_disk = json.loads(JD_JSON.read_text(encoding="utf-8"))["unknown_terms"]
    assert on_disk == ["Halcyon Fleet API", "ROS 2"]  # decisions never edit the parse
