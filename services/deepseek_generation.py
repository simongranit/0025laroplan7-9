from __future__ import annotations

import json
import logging
import random
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from llm.deepseek import DeepSeekChatClient

from .models import Question

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class GenerationDebugInfo:
    """Metadata about the most recent DeepSeek generation attempt."""

    prompt: str
    raw_response: str | None = None
    parse_error: str | None = None
    discarded_questions: int = 0
    returned_questions: int = 0

    def summary(self) -> str:
        parts: list[str] = []
        if self.parse_error:
            parts.append(f"JSON-fel: {self.parse_error}")
        if self.discarded_questions:
            parts.append(f"Kasserade frågor: {self.discarded_questions}")
        parts.append(f"Giltiga frågor: {self.returned_questions}")
        if self.raw_response:
            snippet = _truncate_text(self.raw_response, max_length=240)
            parts.append(f"Svarssnutt: {snippet}")
        return "; ".join(parts)


class DeepSeekQuestionGenerator:
    """Helper that turns DeepSeek chat responses into :class:`Question` objects."""

    def __init__(self, client: DeepSeekChatClient) -> None:
        self.client = client
        self._debug_info: GenerationDebugInfo | None = None

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
        self._debug_info = GenerationDebugInfo(prompt=prompt)
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
        if self._debug_info is not None:
            self._debug_info.raw_response = response
        questions = self._parse_questions(response, grade, topics, length)
        if self._debug_info is not None:
            self._debug_info.returned_questions = len(questions)
        return questions

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
            if self._debug_info is not None:
                self._debug_info.parse_error = str(exc)
            return []
        raw_questions = payload.get("questions", []) if isinstance(payload, dict) else []
        questions: list[Question] = []
        for index, item in enumerate(raw_questions):
            normalized = self._normalize_question(item, grade, topics, index)
            if not normalized:
                if self._debug_info is not None:
                    self._debug_info.discarded_questions += 1
                continue
            try:
                question = Question.model_validate(normalized)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Ogiltig fråga från DeepSeek hoppar över: %s", exc)
                if self._debug_info is not None:
                    self._debug_info.discarded_questions += 1
                continue
            questions.append(question)
            if len(questions) >= length:
                break
        random.shuffle(questions)
        return questions

    def describe_last_attempt(self) -> str | None:
        if self._debug_info is None:
            return None
        summary = self._debug_info.summary()
        return summary or None

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
        """Try to recover JSON payloads even when wrapped in Markdown."""

        def _load_candidate(candidate: str) -> dict[str, Any] | None:
            try:
                data = json.loads(candidate)
            except json.JSONDecodeError:
                return None
            if isinstance(data, list):
                return {"questions": data}
            if isinstance(data, dict):
                return data
            return None

        candidates: list[str] = []
        trimmed = text.strip()
        if trimmed:
            candidates.append(trimmed)

        import re

        pattern = re.compile(r"```(?:json)?\s*([\[{].*?[\]}])\s*```", re.DOTALL)
        for match in pattern.finditer(text):
            snippet = match.group(1).strip()
            if snippet:
                candidates.append(snippet)

        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            candidates.append(text[first_brace : last_brace + 1])

        first_bracket = text.find("[")
        last_bracket = text.rfind("]")
        if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
            candidates.append(text[first_bracket : last_bracket + 1])

        seen: set[str] = set()
        for candidate in candidates:
            normalized = candidate.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            loaded = _load_candidate(normalized)
            if loaded is not None:
                return loaded

        raise ValueError("No JSON object found in DeepSeek response")


def merge_questions(*batches: Iterable[Question]) -> list[Question]:
    """Utility to flatten batches and keep order predictable for persistence."""

    merged: list[Question] = []
    for batch in batches:
        merged.extend(batch)
    return merged


def _truncate_text(value: str, *, max_length: int) -> str:
    snippet = " ".join(value.strip().split())
    if len(snippet) <= max_length:
        return snippet
    return snippet[: max_length - 1].rstrip() + "…"
