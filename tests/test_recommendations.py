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
    recs = recommend_exercises(
        result,
        per_topic=2,
        grade=7,
        skill_profile={"Taluppfattning": 4},
    )
    assert len(recs) >= 2
    assert all(rec.topic in result.skill_profile for rec in recs)
    assert all(rec.grade == 7 for rec in recs)


def test_recommendations_use_skill_profile_levels() -> None:
    store = get_store()
    submissions = [
        DiagnosticSubmission(
            question=store.questions["g7_aritmetik_001"], submitted_answer="10"
        )
    ]
    result = score_submission(submissions)
    advanced = recommend_exercises(
        result,
        per_topic=2,
        grade=7,
        skill_profile={"Taluppfattning": 5},
    )
    beginner = recommend_exercises(
        result,
        per_topic=2,
        grade=7,
        skill_profile={"Taluppfattning": 1},
    )
    assert any(question.difficulty == "hard" for question in advanced)
    assert any(question.difficulty == "easy" for question in beginner)
