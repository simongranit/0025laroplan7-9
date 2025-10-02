from __future__ import annotations

from collections.abc import Mapping

from . import content
from .models import DiagnosticResult, Question

LEVEL_TO_DIFFICULTY = {
    1: "easy",
    2: "easy",
    3: "medium",
    4: "medium",
    5: "hard",
}

LEVEL_TO_DIFFICULTY_ORDER = {
    1: ["easy", "medium", "hard"],
    2: ["easy", "medium", "hard"],
    3: ["medium", "easy", "hard"],
    4: ["medium", "hard", "easy"],
    5: ["hard", "medium", "easy"],
}


def _questions_for_topic(topic: str, *, grade: int | None = None) -> list[Question]:
    store = content.get_store()
    return [
        question
        for question in store.questions.values()
        if question.topic == topic and (grade is None or question.grade == grade)
    ]


def recommend_exercises(
    result: DiagnosticResult,
    *,
    per_topic: int = 3,
    grade: int | None = None,
    skill_profile: Mapping[str, int] | None = None,
) -> list[Question]:
    recommendations: list[Question] = []
    used_ids: set[str] = set()

    for topic_score in sorted(result.topics, key=lambda t: t.level):
        target_level = (
            skill_profile.get(topic_score.topic, topic_score.level)
            if skill_profile
            else topic_score.level
        )
        desired_difficulty = LEVEL_TO_DIFFICULTY.get(target_level, "medium")
        difficulties = LEVEL_TO_DIFFICULTY_ORDER.get(
            target_level, [desired_difficulty, "medium", "easy", "hard"]
        )
        topic_questions = _questions_for_topic(topic_score.topic, grade=grade)
        if not topic_questions:
            topic_questions = _questions_for_topic(topic_score.topic)

        collected = 0
        for difficulty in difficulties:
            for question in topic_questions:
                if question.id in used_ids or question.difficulty != difficulty:
                    continue
                recommendations.append(question)
                used_ids.add(question.id)
                collected += 1
                if collected >= per_topic:
                    break
            if collected >= per_topic:
                break
        if collected < per_topic:
            for question in topic_questions:
                if question.id in used_ids:
                    continue
                recommendations.append(question)
                used_ids.add(question.id)
                collected += 1
                if collected >= per_topic:
                    break

    return recommendations
