from __future__ import annotations

import asyncio
import logging
import random
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Literal

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

from llm.deepseek import get_chat_client

from . import content
from .curriculum import build_curriculum_outline as curriculum_outline_from_pdf
from .deepseek_generation import DeepSeekQuestionGenerator
from .models import DiagnosticResult, DiagnosticSubmission, Question, TopicScore

logger = logging.getLogger(__name__)


@dataclass
class DiagnosticConfig:
    length: int = 8  # ✅ Minska från 10 till 8 för snabbare generering
    difficulty_mix: dict[str, float] = field(
        default_factory=lambda: {"easy": 0.4, "medium": 0.4, "hard": 0.2}
    )
    prefer_dynamic: bool = True
    curriculum_hint: str | None = None
    temperature: float = 0.6
    max_tokens: int = 1200  # ✅ Minska från 1800 till 1200
    timeout: float = 45.0  # ✅ Lägg till timeout för API-anrop

    def __post_init__(self) -> None:
        total = sum(self.difficulty_mix.values())
        if total <= 0:
            raise ValueError("Difficulty mix must sum to > 0")
        self.difficulty_mix = {
            difficulty: weight / total for difficulty, weight in self.difficulty_mix.items()
        }


@dataclass(slots=True)
class DiagnosticGenerationOutcome:
    questions: list[Question]
    source: Literal["dynamic", "store"]
    dynamic_error: str | None = None


@retry(
    stop=stop_after_attempt(2),  # ✅ Retry logik för API-anrop
    wait=wait_exponential(multiplier=1.5, min=3, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError))
)
async def _generate_with_retry(
        generator: DeepSeekQuestionGenerator,
        grade: int,
        topics: Sequence[str],
        config: DiagnosticConfig,
        outline: str,
) -> list[Question]:
    """Helper function with retry logic for DeepSeek generation"""
    return await generator.generate(
        grade,
        topics,
        config.length,
        config.difficulty_mix,
        outline,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )


def generate_diagnostic(
        grade: int,
        topics: Sequence[str],
        config: DiagnosticConfig | None = None,
        skill_profile: Mapping[str, int] | None = None,
) -> DiagnosticGenerationOutcome:
    if config is None:
        config = DiagnosticConfig()

    adjusted_config = _adjust_config_for_skill(config, topics, skill_profile)
    dynamic_error: str | None = None
    dynamic_questions: list[Question] | None = None

    try:
        dynamic_questions = _maybe_generate_dynamic(grade, topics, adjusted_config)
    except DynamicGenerationError as exc:
        dynamic_error = str(exc)
        logger.warning("Dynamic generation failed: %s", dynamic_error)

    # ✅ Fallback till lokala frågor om dynamic failar
    if dynamic_questions:
        return DiagnosticGenerationOutcome(
            dynamic_questions[:adjusted_config.length],
            source="dynamic",
            dynamic_error=dynamic_error,
        )

    # Använd alltid fallback från store
    fallback_questions = _generate_from_store(grade, topics, adjusted_config)
    return DiagnosticGenerationOutcome(
        fallback_questions,
        source="store",
        dynamic_error=dynamic_error,  # ✅ Fortfarande info om varför dynamic failade
    )


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


def _generate_from_store(
        grade: int,
        topics: Sequence[str],
        config: DiagnosticConfig
) -> list[Question]:
    """Fallback: generera frågor från lokalt bibliotek"""
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
        logger.info(
            "Fyller på med extra frågor för %s (Åk %s). Behövde %s extra.",
            ", ".join(topics),
            grade,
            remaining,
        )
        extras = [q for q in candidates if q not in selected]
        if not extras:
            extras = candidates
        if extras:
            selected.extend(random.choices(extras, k=remaining))

    random.shuffle(selected)
    return selected[:config.length]


class DynamicGenerationError(RuntimeError):
    pass


def _maybe_generate_dynamic(
        grade: int,
        topics: Sequence[str],
        config: DiagnosticConfig,
) -> list[Question] | None:
    """Försök generera frågor via DeepSeek API med timeout och retry"""

    if not config.prefer_dynamic:
        return None

    client = get_chat_client()
    if client is None:
        raise DynamicGenerationError(
            "DeepSeek är inte konfigurerat. Sätt DEEPSEEK_API_KEY för att skapa nya frågor."
        )

    # ✅ Optimera curriculum outline för att minska token-användning
    outline = _build_optimized_outline(grade, topics, config.curriculum_hint)

    generator = DeepSeekQuestionGenerator(client)

    try:
        # ✅ Kör med total timeout för hela operationen
        questions = asyncio.run(
            _generate_with_retry(generator, grade, topics, config, outline)
        )

        if not questions:
            debug_details = generator.describe_last_attempt()
            hint = f" Senaste svar: {debug_details}" if debug_details else ""
            message = "DeepSeek genererade inga frågor. Använder lokala frågor istället."
            logger.info("%s%s", message, hint)
            raise DynamicGenerationError(message + hint)

        logger.info("DeepSeek genererade %s frågor för årskurs %s", len(questions), grade)
        return questions

    except asyncio.TimeoutError:
        error_msg = f"DeepSeek API timeout efter {config.timeout} sekunder"
        logger.warning(error_msg)
        raise DynamicGenerationError(error_msg) from None

    except httpx.TimeoutException:
        error_msg = f"DeepSeek API timeout vid anslutning"
        logger.warning(error_msg)
        raise DynamicGenerationError(error_msg) from None

    except RuntimeError as exc:
        error_msg = f"DeepSeek API fel: {exc}"
        logger.warning(error_msg)
        raise DynamicGenerationError(error_msg) from exc

    except Exception as exc:
        error_msg = f"Oväntat fel vid frågegenerering: {exc}"
        logger.exception("Dynamic diagnostic generation failed")
        raise DynamicGenerationError("Kunde inte generera frågor just nu. Använder lokala frågor.") from exc


def _build_optimized_outline(grade: int, topics: Sequence[str], curriculum_hint: str | None) -> str:
    """Bygg en optimerad curriculum outline för att minska token-användning"""

    if curriculum_hint:
        # ✅ Begränsa längden på manuella hints
        if len(curriculum_hint) > 800:
            return curriculum_hint[:800] + "..."
        return curriculum_hint

    # ✅ Begränsa outline från PDF
    outline = curriculum_outline_from_pdf(grade, topics)
    if outline and len(outline) > 1000:
        outline = outline[:1000] + "..."

    if outline:
        return outline

    # ✅ Fallback: använd korta exempel från store
    store = content.get_store()
    sections: list[str] = []

    for topic in topics:
        samples = [
                      question
                      for question in store.questions_by_grade.get(grade, [])
                      if question.topic == topic
                  ][:2]  # ✅ Endast 2 exempel per ämne

        if not samples:
            continue

        sections.append(f"Ämne: {topic}")
        for question in samples:
            # ✅ Mycket kortare format
            sections.append(f"- {question.stem[:60]}... | Svar: {question.answer}")

    return "\n".join(sections) if sections else "Ingen läroplansinformation tillgänglig."