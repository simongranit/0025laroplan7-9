from __future__ import annotations

from services.content import get_store
from services.diagnostics import score_submission
from services.models import DiagnosticSubmission
from services.recommendations import recommend_exercises


def test_recommendations_return_questions() -> None:
    store = get_store()
    submissions = [
        DiagnosticSubmission(question=store.questions["g7_aritmetik_001"], submitted_answer="0"),
        DiagnosticSubmission(question=store.questions["g7_proc_001"], submitted_answer="20"),
    ]
    result = score_submission(submissions)
    recs = recommend_exercises(result, per_topic=2)
    assert len(recs) >= 2
    assert all(rec.topic in result.skill_profile for rec in recs)
