from __future__ import annotations

import json
import logging
import random
from typing import Any, Iterable, Sequence
from uuid import uuid4

from llm.deepseek import DeepSeekChatClient

from .models import Question

logger = logging.getLogger(__name__)


class DeepSeekQuestionGenerator:
    """Helper that turns DeepSeek chat responses into :class:`Question` objects."""

    def __init__(self, client: DeepSeekChatClient) -> None:
        self.client = client

    async def generate(
        self,
        grade: int,
        topics: Sequence[str],
        length: int,
        difficulty_mix: dict[str, float],
        curriculum_outline: str | None,
        *,
        temperature: float = 0.6,
        max_tokens: int = 1800,
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
            max_tokens=max_tokens,
            temperature=temperature,
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


def merge_questions(*batches: Iterable[Question]) -> list[Question]:
    """Utility to flatten batches and keep order predictable for persistence."""

    merged: list[Question] = []
    for batch in batches:
        merged.extend(batch)
    return merged
