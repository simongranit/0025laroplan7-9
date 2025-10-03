from __future__ import annotations

import asyncio
import json
import logging
import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from llm.deepseek import get_chat_client

from .curriculum import CURRICULUM_PDFS, build_curriculum_outline
from .deepseek_generation import DeepSeekQuestionGenerator
from .models import Question

logger = logging.getLogger(__name__)

GENERATED_DIR = Path(__file__).resolve().parent.parent / "content" / "generated"


@dataclass(slots=True)
class QuestionBankRequest:
    grade: int
    topics: Sequence[str]
    total_questions: int = 60
    difficulty_mix: dict[str, float] = field(
        default_factory=lambda: {"easy": 0.4, "medium": 0.4, "hard": 0.2}
    )
    refresh: bool = False
    temperature: float = 0.5
    max_tokens: int = 2600


class CurriculumQuestionBankBuilder:
    """Create and persist large questionbank batches using DeepSeek."""

    def __init__(self, output_dir: Path | None = None) -> None:
        self.output_dir = output_dir or GENERATED_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._health_check_completed = False

    def build(self, request: QuestionBankRequest) -> Path:
        if request.grade not in CURRICULUM_PDFS:
            raise ValueError(f"Okänd årskurs: {request.grade}")
        topics = [topic for topic in request.topics if topic]
        if not topics:
            raise ValueError("Minst ett ämne krävs för att skapa frågor.")
        slug = _slugify("_".join(topics))
        output_path = self.output_dir / f"grade{request.grade}_{slug}.json"
        if output_path.exists() and not request.refresh:
            logger.info("Återanvänder befintligt frågebank: %s", output_path)
            return output_path

        client = get_chat_client()
        if client is None:
            raise RuntimeError("DeepSeek är inte konfigurerat. Sätt DEEPSEEK_API_KEY först.")

        generator = DeepSeekQuestionGenerator(client)
        curriculum_outline = build_curriculum_outline(request.grade, topics)
        if not curriculum_outline:
            logger.warning(
                "Hittade ingen läroplanstext för Åk %s. Frågorna kan sakna kontext.",
                request.grade,
            )

        collected: list[Question] = []
        remaining_total = request.total_questions
        for index, topic in enumerate(topics):
            topic_remaining = math.ceil(remaining_total / (len(topics) - index))
            collected.extend(
                self._generate_for_topic(
                    generator,
                    grade=request.grade,
                    topic=topic,
                    target=topic_remaining,
                    difficulty_mix=request.difficulty_mix,
                    curriculum_outline=curriculum_outline,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                )
            )
            remaining_total = max(0, request.total_questions - len(collected))
            if remaining_total <= 0:
                break

        if not collected:
            raise RuntimeError("DeepSeek genererade inga frågor. Försök igen senare.")

        unique_questions = self._ensure_unique_ids(request.grade, slug, collected)

        payload = {
            "schema_version": "1.0",
            "questions": [question.model_dump() for question in unique_questions],
        }
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        logger.info(
            "Skapade %s frågor för Åk %s (%s) och sparade till %s",
            len(unique_questions),
            request.grade,
            ", ".join(topics),
            output_path,
        )
        return output_path

    def _generate_for_topic(
        self,
        generator: DeepSeekQuestionGenerator,
        *,
        grade: int,
        topic: str,
        target: int,
        difficulty_mix: dict[str, float],
        curriculum_outline: str,
        temperature: float,
        max_tokens: int,
    ) -> list[Question]:
        questions: list[Question] = []
        attempts = 0
        seen_stems: set[str] = {question.stem for question in questions}
        batch_size = max(5, min(15, target))
        self._ensure_health_check(generator)
        while len(questions) < target and attempts < 6:
            attempts += 1
            try:
                batch = asyncio.run(
                    generator.generate(
                        grade,
                        [topic],
                        batch_size,
                        difficulty_mix,
                        curriculum_outline,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                )
            except RuntimeError as exc:
                cause = exc.__cause__ or exc.__context__
                if cause is not None:
                    logger.warning(
                        "DeepSeek-förfrågan misslyckades (%s): %s (orsak: %s)",
                        topic,
                        exc,
                        _describe_exception(cause),
                        cause,
                    )
                else:
                    logger.warning("DeepSeek-förfrågan misslyckades (%s): %s", topic, exc)
                break
            if not batch:
                logger.info("Inga frågor genererades för %s i försök %s", topic, attempts)
                continue
            for question in batch:
                if question.topic.lower() != topic.lower():
                    question = question.model_copy(update={"topic": topic})
                if question.stem not in seen_stems:
                    questions.append(question)
                    seen_stems.add(question.stem)
            if len(questions) >= target:
                break
        if not questions:
            logger.warning("Hittade inga frågor för %s trots %s försök.", topic, attempts)
        return questions[:target]

    def _ensure_unique_ids(
        self, grade: int, slug: str, questions: Sequence[Question]
    ) -> list[Question]:
        updated: list[Question] = []
        for index, question in enumerate(questions, start=1):
            identifier = f"gen_{grade}_{slug}_{index:03d}"
            updated.append(question.model_copy(update={"id": identifier}))
        return updated

    def _ensure_health_check(self, generator: DeepSeekQuestionGenerator) -> None:
        if self._health_check_completed:
            return
        try:
            asyncio.run(generator.client.health_check())
        except Exception as exc:  # noqa: BLE001
            cause = exc.__cause__ or exc.__context__
            if cause is not None:
                logger.error(
                    "DeepSeek-hälsokontroll misslyckades: %s (orsak: %s)",
                    exc,
                    _describe_exception(cause),
                )
            else:
                logger.error("DeepSeek-hälsokontroll misslyckades: %s", exc)
            raise RuntimeError(
                "DeepSeek-hälsokontrollen misslyckades. Avbryter generering."
            ) from exc
        else:
            self._health_check_completed = True
            logger.debug("DeepSeek-hälsokontroll lyckades.")


def _describe_exception(exc: BaseException) -> str:
    message = str(exc).strip()
    if message:
        return message
    return exc.__class__.__name__


def _slugify(value: str) -> str:
    import re

    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "topics"

