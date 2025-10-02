from __future__ import annotations

from . import content
from .models import DiagnosticResult, Question

LEVEL_TO_DIFFICULTY = {
    1: "easy",
    2: "easy",
    3: "medium",
    4: "medium",
    5: "hard",
}


def _questions_for_topic(topic: str) -> list[Question]:
    store = content.get_store()
    return [question for question in store.questions.values() if question.topic == topic]


def recommend_exercises(result: DiagnosticResult, per_topic: int = 3) -> list[Question]:
    store = content.get_store()
    recommendations: list[Question] = []
    used_ids: set[str] = set()

    for topic_score in sorted(result.topics, key=lambda t: t.level):
        desired_difficulty = LEVEL_TO_DIFFICULTY.get(topic_score.level, "medium")
        topic_questions = _questions_for_topic(topic_score.topic)
        preferred = [q for q in topic_questions if q.difficulty == desired_difficulty]
        pool = preferred if len(preferred) >= per_topic else topic_questions
        for question in pool:
            if question.id in used_ids:
                continue
            recommendations.append(question)
            used_ids.add(question.id)
            if sum(1 for q in recommendations if q.topic == topic_score.topic) >= per_topic:
                break

    if not recommendations:
        # fallback: select first N questions regardless of topic
        for question in store.questions.values():
            if question.id in used_ids:
                continue
            recommendations.append(question)
            used_ids.add(question.id)
            if len(recommendations) >= per_topic * max(1, len(result.topics)):
                break

    return recommendations
