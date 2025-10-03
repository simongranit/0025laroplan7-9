from __future__ import annotations

import asyncio
import logging
import random
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace

from llm.deepseek import get_chat_client

from . import content
from .curriculum import build_curriculum_outline as curriculum_outline_from_pdf
from .deepseek_generation import DeepSeekQuestionGenerator
from .models import DiagnosticResult, DiagnosticSubmission, Question, TopicScore

logger = logging.getLogger(__name__)


@dataclass
class DiagnosticConfig:
    length: int = 10
    difficulty_mix: dict[str, float] = field(
        default_factory=lambda: {"easy": 0.4, "medium": 0.4, "hard": 0.2}
    )
    prefer_dynamic: bool = True
    curriculum_hint: str | None = None

    def __post_init__(self) -> None:
        total = sum(self.difficulty_mix.values())
        if total <= 0:
            raise ValueError("Difficulty mix must sum to > 0")
        self.difficulty_mix = {
            difficulty: weight / total for difficulty, weight in self.difficulty_mix.items()
        }


def generate_diagnostic(
    grade: int,
    topics: Sequence[str],
    config: DiagnosticConfig | None = None,
    skill_profile: Mapping[str, int] | None = None,
) -> list[Question]:
    if config is None:
        config = DiagnosticConfig()
    adjusted_config = _adjust_config_for_skill(config, topics, skill_profile)
    dynamic_questions = _maybe_generate_dynamic(grade, topics, adjusted_config)
    if dynamic_questions:
        return dynamic_questions[: adjusted_config.length]
    return _generate_from_store(grade, topics, adjusted_config)


def _adjust_config_for_skill(
    config: DiagnosticConfig,
    topics: Sequence[str],
    skill_profile: Mapping[str, int] | None,
) -> DiagnosticConfig:
    if not skill_profile:
        return config
    levels = [skill_profile[topic] for topic in topics if topic in skill_profile]
    if not levels:
        return config
    avg_level = sum(levels) / len(levels)
    if avg_level < 2.5:
        mix = {"easy": 0.6, "medium": 0.3, "hard": 0.1}
    elif avg_level < 3.5:
        mix = {"easy": 0.3, "medium": 0.5, "hard": 0.2}
    else:
        mix = {"easy": 0.2, "medium": 0.3, "hard": 0.5}
    return replace(config, difficulty_mix=mix)


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


def _generate_from_store(grade: int, topics: Sequence[str], config: DiagnosticConfig) -> list[Question]:
    store = content.get_store()
    candidates: list[Question] = []
    for topic in topics:
        candidates.extend(
            q
            for q in store.questions_by_grade.get(grade, [])
            if q.topic == topic
        )
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
        logger.warning(
            "Not enough unika frågor för %s (Åk %s). Försöker fylla på med slumpmässiga val.",
            ", ".join(topics),
            grade,
        )
        extras = [q for q in candidates if q not in selected]
        if not extras:
            extras = candidates
        if extras:
            selected.extend(random.choices(extras, k=remaining))

    random.shuffle(selected)
    return selected[: config.length]


def _maybe_generate_dynamic(
    grade: int,
    topics: Sequence[str],
    config: DiagnosticConfig,
) -> list[Question] | None:
    if not config.prefer_dynamic:
        return None
    client = get_chat_client()
    if client is None:
        return None
    outline = config.curriculum_hint or _build_curriculum_outline(grade, topics)
    generator = DeepSeekQuestionGenerator(client)
    try:
        return asyncio.run(
            generator.generate(
                grade,
                topics,
                config.length,
                config.difficulty_mix,
                outline,
            )
        )
    except RuntimeError as exc:
        logger.warning("Dynamic diagnostic generation avbruten: %s", exc)
        return None
    except Exception as exc:  # noqa: BLE001
        logger.exception("Dynamic diagnostic generation failed: %s", exc)
        return None


def _build_curriculum_outline(grade: int, topics: Sequence[str]) -> str:
    outline = curriculum_outline_from_pdf(grade, topics)
    if outline:
        return outline

    store = content.get_store()
    sections: list[str] = []
    for topic in topics:
        samples = [
            question
            for question in store.questions_by_grade.get(grade, [])
            if question.topic == topic
        ][:3]
        if not samples:
            continue
        sections.append(f"Ämne: {topic}")
        for question in samples:
            sections.append(
                f"- ({question.difficulty}) {question.stem} | Facit: {question.answer}"
            )
    return "\n".join(sections)


