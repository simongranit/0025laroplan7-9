from __future__ import annotations

import random
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from . import content
from .models import DiagnosticResult, DiagnosticSubmission, Question, TopicScore


@dataclass
class DiagnosticConfig:
    length: int = 10
    difficulty_mix: dict[str, float] = field(
        default_factory=lambda: {"easy": 0.4, "medium": 0.4, "hard": 0.2}
    )

    def __post_init__(self) -> None:
        total = sum(self.difficulty_mix.values())
        if total <= 0:
            raise ValueError("Difficulty mix must sum to > 0")
        self.difficulty_mix = {
            difficulty: weight / total for difficulty, weight in self.difficulty_mix.items()
        }


def generate_diagnostic(grade: int, topics: Sequence[str], config: DiagnosticConfig | None = None) -> list[Question]:
    if config is None:
        config = DiagnosticConfig()
    store = content.get_store()
    candidates: list[Question] = []
    for topic in topics:
        candidates.extend(
            q
            for q in store.questions_by_grade.get(grade, [])
            if q.topic == topic
        )
    if len(candidates) < config.length:
        # fall back to any topic if insufficient pool
        candidates = store.questions_by_grade.get(grade, [])
    if not candidates:
        raise ValueError(f"No questions found for grade {grade} and topics {topics}.")

    by_difficulty: dict[str, list[Question]] = defaultdict(list)
    for question in candidates:
        by_difficulty[question.difficulty].append(question)

    selected: list[Question] = []
    remaining = config.length
    for difficulty, weight in config.difficulty_mix.items():
        target = max(1, int(round(weight * config.length)))
        pool = by_difficulty.get(difficulty, [])
        if pool:
            k = min(len(pool), target, remaining)
            selected.extend(random.sample(pool, k=k))
            remaining -= k

    if remaining > 0:
        leftovers = [q for q in candidates if q not in selected]
        if leftovers:
            selected.extend(random.sample(leftovers, k=min(len(leftovers), remaining)))

    random.shuffle(selected)
    return selected[: config.length]


def score_submission(submissions: Iterable[DiagnosticSubmission]) -> DiagnosticResult:
    submissions_list = list(submissions)
    total_questions = len(submissions_list)
    correct_total = 0
    per_topic: dict[str, Counter[str]] = defaultdict(Counter)

    for submission in submissions_list:
        is_correct = submission.is_correct
        if is_correct:
            correct_total += 1
        topic = submission.question.topic
        per_topic[topic]["total"] += 1
        if is_correct:
            per_topic[topic]["correct"] += 1

    topic_scores = [
        TopicScore(
            topic=topic,
            total_questions=counts["total"],
            correct_answers=counts.get("correct", 0),
        )
        for topic, counts in sorted(per_topic.items())
    ]

    return DiagnosticResult(
        total_questions=total_questions,
        total_correct=correct_total,
        topics=topic_scores,
    )
