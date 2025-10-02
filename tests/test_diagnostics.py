from __future__ import annotations

from services import diagnostics
from services.content import get_store
from services.models import DiagnosticSubmission


def test_generate_diagnostic_returns_requested_length() -> None:
    questions = diagnostics.generate_diagnostic(7, ["Taluppfattning"], diagnostics.DiagnosticConfig(length=5))
    assert len(questions) == 5


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
