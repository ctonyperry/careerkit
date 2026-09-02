from test_coverage import make_spine, make_unit

from careerkit.coverage import assess_requirement
from careerkit.jd import Requirement
from careerkit.questions import generate_questions


def test_miss_generates_grounded_recovery_question() -> None:
    req = Requirement(
        id="security",
        text="Owns the customer security relationship",
        skills=["scim"],
        weight="required",
    )
    cov = assess_requirement(req, [], make_spine())
    questions = generate_questions([cov])
    assert len(questions) == 1
    q = questions[0].text
    assert "This role wants" in q
    assert "Did you do this work, and when?" in q
    # The forbidden framing (invites inflation):
    assert "match better" not in q.lower()


def test_thin_question_names_the_existing_evidence() -> None:
    req = Requirement(
        id="sso", text="Identity integration experience", skills=["sso"], weight="required"
    )
    cov = assess_requirement(req, [make_unit("athena-sso", ["sso"])], make_spine())
    questions = generate_questions([cov])
    assert len(questions) == 1
    assert "athena-sso" in questions[0].text  # jogs memory with what exists


def test_hit_generates_no_question() -> None:
    req = Requirement(
        id="sso", text="Identity integration experience", skills=["sso"], weight="required"
    )
    units = [make_unit("u1", ["sso"]), make_unit("u2", ["sso"])]
    cov = assess_requirement(req, units, make_spine())
    assert generate_questions([cov]) == []


def test_credential_requirement_generates_no_recovery_question() -> None:
    # A degree is not excavatable; it gets a strategy note, never a question.
    req = Requirement(
        id="degree",
        text="BS in Computer Science",
        skills=["scim"],
        weight="required",
        kind="credential",
    )
    cov = assess_requirement(req, [], make_spine())
    assert generate_questions([cov]) == []


def test_tenure_requirement_generates_no_recovery_question() -> None:
    req = Requirement(
        id="tenure",
        text="8+ years of experience",
        skills=["scim"],
        weight="required",
        kind="tenure",
    )
    cov = assess_requirement(req, [], make_spine())
    assert generate_questions([cov]) == []


def test_declined_skill_never_generates_a_recovery_question() -> None:
    # "Never did that" is recorded once; the JD must not re-ask it.
    req = Requirement(
        id="infra", text="Runs the data center", skills=["infrastructure"], weight="required"
    )
    cov = assess_requirement(req, [], make_spine(), frozenset({"infrastructure"}))
    assert generate_questions([cov]) == []


def test_questions_ask_for_specific_instance() -> None:
    # Defensibility starts at the question: ask for instance + date.
    req = Requirement(id="x", text="Escalation ownership", skills=["scim"], weight="required")
    cov = assess_requirement(req, [], make_spine())
    q = generate_questions([cov])[0].text
    assert "specific" in q.lower()
