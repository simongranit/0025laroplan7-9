from __future__ import annotations

from services import diagnostics
from services.content import get_store
from services.models import DiagnosticSubmission, Question


def test_generate_diagnostic_returns_requested_length() -> None:
    outcome = diagnostics.generate_diagnostic(
        7, ["Taluppfattning"], diagnostics.DiagnosticConfig(length=5)
    )
    assert len(outcome.questions) == 5
    assert outcome.source == "store"


def test_score_submission_creates_topic_scores() -> None:
    store = get_store()
    sample = [store.questions["g7_aritmetik_001"], store.questions["g7_proc_001"]]
    submissions = [
        DiagnosticSubmission(question=sample[0], submitted_answer="10"),
        DiagnosticSubmission(question=sample[1], submitted_answer="0"),
    ]
    result = diagnostics.score_submission(submissions)
    assert result.total_questions == 2
    assert result.total_correct == 1
    assert "Taluppfattning" in result.skill_profile


def test_generate_diagnostic_uses_dynamic(monkeypatch) -> None:
    dynamic_question = Question(
        id="dyn_q1",
        grade=7,
        topic="Taluppfattning",
        difficulty="easy",
        stem="Vad är 2 + 3?",
        answer="5",
        solution_explainer="Addera talen.",
    )

    monkeypatch.setattr(
        diagnostics,
        "_maybe_generate_dynamic",
        lambda grade, topics, config: [dynamic_question],
    )

    outcome = diagnostics.generate_diagnostic(
        7, ["Taluppfattning"], diagnostics.DiagnosticConfig(length=3)
    )
    assert outcome.source == "dynamic"
    assert outcome.questions == [dynamic_question]


def test_generate_diagnostic_fallback_when_dynamic_empty(monkeypatch) -> None:
    monkeypatch.setattr(
        diagnostics, "_maybe_generate_dynamic", lambda grade, topics, config: []
    )
    config = diagnostics.DiagnosticConfig(length=4)
    outcome = diagnostics.generate_diagnostic(7, ["Taluppfattning"], config)
    assert outcome.source == "store"
    assert len(outcome.questions) == 4


def test_generate_diagnostic_uses_skill_profile(monkeypatch) -> None:
    monkeypatch.setattr(
        diagnostics, "_maybe_generate_dynamic", lambda grade, topics, config: []
    )
    monkeypatch.setattr(diagnostics.random, "sample", lambda seq, k: list(seq)[:k])
    config = diagnostics.DiagnosticConfig(length=3, prefer_dynamic=False)
    outcome = diagnostics.generate_diagnostic(
        7,
        ["Taluppfattning"],
        config,
        skill_profile={"Taluppfattning": 5},
    )
    assert any(question.difficulty == "hard" for question in outcome.questions)
