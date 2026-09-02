from test_coverage import make_spine

from careerkit.jd import ParsedJD, Requirement
from careerkit.linter import Severity, has_blockers, lint_resume
from careerkit.models import (
    Education,
    EvidenceUnit,
    Metric,
    Spine,
    Status,
    Tier,
)


def _spine_with_education() -> Spine:
    spine = make_spine()
    spine.education = Education(
        items=[
            "Certificate, Portland Community College, 2012",
            "CS and business coursework at Lane Community College",
        ]
    )
    return spine


def _units() -> list[EvidenceUnit]:
    return [
        EvidenceUnit(
            id="m",
            role="new-role",
            narrative="Delivered a $10M program reaching ~2M users.",
            skills=["x"],
            tier=Tier.PRIMARY,
            status=Status.CONFIRMED,
            metrics=[Metric(value="$10M", tier=Tier.PRIMARY)],
        )
    ]


def _rules(findings: list) -> set[str]:
    return {f.rule for f in findings}


def test_em_dash_blocks() -> None:
    findings = lint_resume("- Owned delivery — end to end.", make_spine(), [])
    assert "em-dash" in _rules(findings)
    assert has_blockers(findings)


def test_banned_and_self_rating_phrases_block() -> None:
    text = "- A results-driven, seasoned engineer with a proven track record."
    findings = lint_resume(text, make_spine(), [])
    assert "banned-phrase" in _rules(findings)
    assert "self-rating" in _rules(findings)


def test_tricolon_warns_in_prose_but_not_in_bullets() -> None:
    prose = "Collaborative, driven, and thorough across every engagement."
    findings = lint_resume(prose, make_spine(), [])
    tricolon = [f for f in findings if f.rule == "tricolon"]
    assert tricolon and all(f.severity is Severity.WARN for f in tricolon)
    assert not has_blockers(findings)  # heuristic, never blocks

    bullet = "- Migrated billing, built the email system, and modernized reporting."
    assert "tricolon" not in _rules(lint_resume(bullet, make_spine(), []))


def test_number_without_source_blocks_unless_verified() -> None:
    spine, units = make_spine(), _units()
    assert "number-without-source" in _rules(
        lint_resume("- Cut costs by 40%.", spine, units)
    )
    # Same number, marked [VERIFY], is allowed through.
    assert "number-without-source" not in _rules(
        lint_resume("- Cut costs by 40%. [VERIFY]", spine, units)
    )
    # A sourced figure passes.
    assert "number-without-source" not in _rules(
        lint_resume("- Delivered a $10M program.", spine, units)
    )


def test_education_hallucinated_credential_blocks() -> None:
    spine = _spine_with_education()
    text = "## EDUCATION\nB.S. in Computer Science, Stanford University, 2015"
    findings = lint_resume(text, spine, [])
    assert "education-not-in-spine" in _rules(findings)
    assert has_blockers(findings)


def test_education_verbatim_from_spine_passes() -> None:
    spine = _spine_with_education()
    text = "## EDUCATION\nCertificate, Portland Community College, 2012"
    assert "education-not-in-spine" not in _rules(lint_resume(text, spine, []))


def test_rhythm_only_warns() -> None:
    long_sentence = " ".join(["word"] * 25) + "."
    bullet = "- " + long_sentence + " " + long_sentence + " " + long_sentence
    findings = lint_resume(bullet, make_spine(), [])
    rhythm = [f for f in findings if f.rule == "rhythm"]
    assert rhythm and all(f.severity is Severity.WARN for f in rhythm)


def test_clean_resume_has_no_blockers() -> None:
    spine, units = _spine_with_education(), _units()
    text = (
        "# Morgan Vale\n"
        "## EXPERIENCE\n"
        "- Delivered a $10M program reaching ~2M users.\n"
        "## EDUCATION\n"
        "Certificate, Portland Community College, 2012\n"
    )
    assert not has_blockers(lint_resume(text, spine, units))


def _mirror_jd() -> ParsedJD:
    return ParsedJD(
        source="x",
        title_to_mirror="T",
        role_family="f",
        seniority="s",
        requirements=[
            Requirement(
                id="r1",
                text=(
                    "Lead technical discovery for customer deployments, guiding "
                    "engineering teams from integration design through production "
                    "rollout at enterprise scale"
                ),
                skills=["sso"],
                weight="required",
            ),
            Requirement(
                id="r2",
                text="Debug customer infrastructure and trace failures to root cause",
                skills=["sso"],
                weight="required",
            ),
        ],
    )


_MIRROR_SUMMARY = (
    "Consultant who guides customer engineering teams from integration design "
    "through production rollout, then traces failures at enterprise scale to "
    "root cause."
)


def _summary_doc(summary: str) -> str:
    header = "# Morgan Vale\n\nt@example.com\n\n**Title**\n\n"
    return header + summary + "\n\n## Experience\n"


def test_summary_that_paraphrases_the_jd_is_flagged() -> None:
    findings = lint_resume(_summary_doc(_MIRROR_SUMMARY), make_spine(), [], _mirror_jd())
    mirror = [f for f in findings if f.rule == "jd-mirroring"]
    assert mirror, "a summary echoing the JD should be flagged"
    assert mirror[0].severity is Severity.WARN  # judgment call, never blocks


def test_trajectory_summary_is_not_flagged() -> None:
    doc = _summary_doc(
        "Thirty-one years in software, starting at a tier-2 support desk in 1995. "
        "Ran technical operations for a management-education network, then spent "
        "six years at LinkedIn."
    )
    assert "jd-mirroring" not in _rules(lint_resume(doc, make_spine(), [], _mirror_jd()))


def test_jd_mirroring_is_skipped_without_a_jd() -> None:
    doc = _summary_doc(_MIRROR_SUMMARY)
    assert "jd-mirroring" not in _rules(lint_resume(doc, make_spine(), []))


def test_bullets_may_echo_the_jd_freely() -> None:
    # Only the summary is checked. Bullets SHOULD share the JD's domain
    # vocabulary; they were selected against it.
    doc = (
        "# Morgan Vale\n\n**Title**\n\n## Experience\n\n"
        "- Led technical discovery for customer deployments, guiding engineering "
        "teams from integration design through production rollout at enterprise "
        "scale, tracing failures to root cause.\n"
    )
    assert "jd-mirroring" not in _rules(lint_resume(doc, make_spine(), [], _mirror_jd()))


def test_tenure_must_be_computable_from_the_spine() -> None:
    """The characteristic hallucination: a summary aggregate that feels like
    arithmetic. Two shipped on 2026-08-24 and every other gate passed them.

    Fixture spine: OldCo 1999-2005, NewCo 2019-Jun 2026. Computable spans are
    the whole career (27) and each role (6, 7), plus a one-year rounding
    ceiling on each. Spans crossing role boundaries are deliberately NOT
    computable: allowing them is what let "fifteen years" through against the
    real spine (defect corpus, 2026-08-25).
    """
    spine, units = make_spine(), _units()

    # The whole career is computable, spelled out or in digits.
    assert "tenure-not-computed" not in _rules(
        lint_resume("Twenty-seven years in software.", spine, units)
    )
    assert "tenure-not-computed" not in _rules(
        lint_resume("27 years in software.", spine, units)
    )
    # A single role's span is computable.
    assert "tenure-not-computed" not in _rules(
        lint_resume("Seven years at NewCo.", spine, units)
    )
    # A span crossing roles is not: 2026 minus OldCo's 1999 start is 27, which
    # the whole-career span already covers, but 2026 minus NewCo's 2019 start
    # (7) must not license an unrelated 20.
    assert "tenure-not-computed" in _rules(
        lint_resume("Twenty years of customer-facing work.", spine, units)
    )
    # An aggregate nobody can derive is a fabrication.
    findings = lint_resume("Fifteen years of customer-facing consulting.", spine, units)
    assert "tenure-not-computed" in _rules(findings)
    assert has_blockers(findings)
    # The "N+ years" form is the one older resumes used most.
    assert "tenure-not-computed" in _rules(
        lint_resume("25+ years in enterprise integration.", spine, units)
    )


def test_tenure_carried_by_a_unit_is_allowed() -> None:
    """Not every tenure claim is about a spine role. '~4 years as Microsoft's
    go-to API contact' describes a relationship and is carried by the unit."""
    spine = make_spine()
    units = [
        EvidenceUnit(
            id="rel",
            role="new-role",
            narrative="Was the go-to API contact for roughly four years.",
            skills=["x"],
            tier=Tier.PRIMARY,
            status=Status.CONFIRMED,
        )
    ]
    assert "tenure-not-computed" not in _rules(
        lint_resume("- Four years as their go-to API contact.", spine, units)
    )
    # A different figure, from no unit and no span, still blocks.
    assert "tenure-not-computed" in _rules(
        lint_resume("- Eleven years as their go-to API contact.", spine, units)
    )


def test_tenure_ignores_ordinary_year_mentions() -> None:
    spine, units = make_spine(), _units()
    clean = "- Shipped the 2019 migration and the 2026 rebuild."
    assert "tenure-not-computed" not in _rules(lint_resume(clean, spine, units))


def test_doubted_metric_no_longer_legitimises_a_number() -> None:
    """Confirmation and doubt are symmetric. When the author stops standing behind a
    figure it must stop sourcing that number, not merely fail to be promoted.
    The $10M franchise-rollout figure went this way on 2026-08-25."""
    spine = make_spine()
    unit = EvidenceUnit(
        id="m",
        role="new-role",
        narrative="Ran a large program.",
        skills=["x"],
        tier=Tier.PRIMARY,
        status=Status.CONFIRMED,
        metrics=[Metric(value="program exceeding $10M", tier=Tier.MEMORY, doubted=True)],
    )
    findings = lint_resume("- Led a $10M program.", spine, [unit])
    assert "number-without-source" in _rules(findings)
    assert has_blockers(findings)

    # The same metric, still trusted, sources the figure.
    unit.metrics = [Metric(value="program exceeding $10M", tier=Tier.PRIMARY)]
    assert "number-without-source" not in _rules(
        lint_resume("- Led a $10M program.", spine, [unit])
    )


def test_do_not_print_blocks_regardless_of_coverage() -> None:
    """Some things are true, sourced, relevant, and still must not be sent: a
    figure the author no longer trusts, an artifact he is not ready to share."""
    spine = make_spine()
    unit = EvidenceUnit(
        id="kit",
        role=None,
        narrative="Published the UX Telemetry Kit to npm.",
        skills=["x"],
        tier=Tier.PRIMARY,
        status=Status.CONFIRMED,
        do_not_print=["UX Telemetry Kit"],
    )
    findings = lint_resume("- Published the UX Telemetry Kit, an npm module.", spine, [unit])
    assert "do-not-print" in _rules(findings)
    assert has_blockers(findings)
    # Case-insensitive, and silent when the phrase is absent.
    assert "do-not-print" in _rules(lint_resume("- shipped a ux telemetry kit", spine, [unit]))
    clean = lint_resume("- Shipped a telemetry library.", spine, [unit])
    assert "do-not-print" not in _rules(clean)


def test_bullet_opening_with_an_article_warns() -> None:
    """Every institutional guide gives the same first rule: bullets open with a
    verb. Noun-phrase openers are where clumsy compression breeds."""
    spine, units = make_spine(), _units()
    clumsy = "- The API subject-matter expert customer engineering teams built against."
    findings = lint_resume(clumsy, spine, units)
    assert "bullet-opener" in _rules(findings)
    assert not has_blockers(findings)  # heuristic: a front-loaded number can earn it

    assert "bullet-opener" not in _rules(
        lint_resume("- Advised customer engineering teams building against the API.", spine, units)
    )
    # Prose is unaffected; the rule is about bullets.
    assert "bullet-opener" not in _rules(
        lint_resume("The path runs from support into consulting.", spine, units)
    )
