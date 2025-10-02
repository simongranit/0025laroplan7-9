from __future__ import annotations

import asyncio
import json
import logging
import random
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from llm.deepseek import DeepSeekChatClient, get_chat_client

from . import content
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


def generate_diagnostic(grade: int, topics: Sequence[str], config: DiagnosticConfig | None = None) -> list[Question]:
    if config is None:
        config = DiagnosticConfig()
    dynamic_questions = _maybe_generate_dynamic(grade, topics, config)
    if dynamic_questions:
        return dynamic_questions[: config.length]
    return _generate_from_store(grade, topics, config)


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
    if len(candidates) < config.length:
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
    generator = _DeepSeekDiagnosticGenerator(client)
    try:
        return asyncio.run(
            generator.generate(grade, topics, config.length, config.difficulty_mix, outline)
        )
    except RuntimeError as exc:
        logger.warning("Dynamic diagnostic generation avbruten: %s", exc)
        return None
    except Exception as exc:  # noqa: BLE001
        logger.exception("Dynamic diagnostic generation failed: %s", exc)
        return None


def _build_curriculum_outline(grade: int, topics: Sequence[str]) -> str:
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


class _DeepSeekDiagnosticGenerator:
    def __init__(self, client: DeepSeekChatClient) -> None:
        self.client = client

    async def generate(
        self,
        grade: int,
        topics: Sequence[str],
        length: int,
        difficulty_mix: dict[str, float],
        curriculum_outline: str | None,
    ) -> list[Question]:
        prompt = self._build_prompt(grade, topics, length, difficulty_mix, curriculum_outline)
        response = await self.client.complete(
            [
                {
                    "role": "system",
                    "content": "Du är en erfaren matematiklärare som skriver diagnostiska prov för svenska läroplanen.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=1800,
            temperature=0.6,
        )
        return self._parse_questions(response, grade, topics, length)

    def _build_prompt(
        self,
        grade: int,
        topics: Sequence[str],
        length: int,
        difficulty_mix: dict[str, float],
        curriculum_outline: str | None,
    ) -> str:
        distribution = ", ".join(
            f"{int(weight * 100)}% {level}" for level, weight in difficulty_mix.items()
        )
        outline_section = (
            f"\nFölj dessa exempel från undervisningen:\n{curriculum_outline}"
            if curriculum_outline
            else ""
        )
        topics_text = ", ".join(topics)
        return (
            "Skapa ett diagnostiskt prov för matematik enligt den svenska läroplanen.\n"
            f"Årskurs: {grade}.\n"
            f"Områden: {topics_text}.\n"
            f"Provets längd: {length} frågor.\n"
            f"Svårighetsfördelning: {distribution}.\n"
            "Varje fråga ska vara tydlig och skriven på svenska."
            " Använd rätt matematiskt språk och inkludera vardagsnära sammanhang när det passar."
            f"{outline_section}\n"
            "Returnera ENBART JSON med nyckeln \"questions\". Varje fråga ska vara ett objekt"
            " med fälten id, grade, topic, difficulty (easy|medium|hard), stem, answer,"
            " solution_explainer och choices (lista med svarsalternativ eller tom lista)."
            " Lösningsförklaringen ska vara kort och vägledande."
            " Om frågan är öppen ska choices vara en tom lista."
            " Id ska vara unikt och kan börja med 'dyn'."
        )

    def _parse_questions(
        self,
        response: str,
        grade: int,
        topics: Sequence[str],
        length: int,
    ) -> list[Question]:
        try:
            payload = self._extract_json(response)
        except (ValueError, TypeError) as exc:
            logger.warning("Kunde inte tolka JSON från DeepSeek: %s", exc)
            return []
        raw_questions = payload.get("questions", []) if isinstance(payload, dict) else []
        questions: list[Question] = []
        for index, item in enumerate(raw_questions):
            normalized = self._normalize_question(item, grade, topics, index)
            if not normalized:
                continue
            try:
                question = Question.model_validate(normalized)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Ogiltig fråga från DeepSeek hoppar över: %s", exc)
                continue
            questions.append(question)
            if len(questions) >= length:
                break
        random.shuffle(questions)
        return questions

    def _normalize_question(
        self,
        item: Any,
        grade: int,
        topics: Sequence[str],
        index: int,
    ) -> dict[str, Any] | None:
        if not isinstance(item, dict):
            return None
        topic = item.get("topic") or (topics[0] if topics else "Allmänt")
        difficulty = self._normalize_difficulty(item.get("difficulty"))
        stem = str(item.get("stem", "")).strip()
        answer = str(item.get("answer", "")).strip()
        solution = str(
            item.get("solution_explainer")
            or item.get("solution")
            or item.get("explanation", "")
        ).strip()
        if not stem or not answer:
            return None
        choices_raw = item.get("choices")
        if isinstance(choices_raw, list):
            choices = [str(choice).strip() for choice in choices_raw if str(choice).strip()]
        else:
            choices = []
        tags_raw = item.get("tags")
        if isinstance(tags_raw, list):
            tags = [str(tag).strip() for tag in tags_raw if str(tag).strip()]
        else:
            tags = []
        if not solution:
            solution = f"Rätt svar är {answer}."
        normalized: dict[str, Any] = {
            "id": item.get("id") or f"dyn_{grade}_{index}_{uuid4().hex[:6]}",
            "grade": grade,
            "topic": topic,
            "difficulty": difficulty,
            "stem": stem,
            "answer": answer,
            "solution_explainer": solution,
            "choices": choices or None,
            "tags": sorted({*tags, "dynamic"}),
        }
        return normalized

    def _normalize_difficulty(self, value: Any) -> str:
        if not value:
            return "medium"
        normalized = str(value).strip().lower()
        mapping = {
            "lätt": "easy",
            "enkel": "easy",
            "easy": "easy",
            "medel": "medium",
            "mellan": "medium",
            "medium": "medium",
            "svår": "hard",
            "hard": "hard",
        }
        return mapping.get(normalized, "medium")

    def _extract_json(self, text: str) -> dict[str, Any]:
        first = text.find("{")
        last = text.rfind("}")
        if first == -1 or last == -1 or last <= first:
            raise ValueError("No JSON object found")
        fragment = text[first : last + 1]
        return json.loads(fragment)
