from __future__ import annotations

import json
import random
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError

from .models import Question, Quiz

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"
QUESTIONS_DIR = CONTENT_DIR / "questions"
GENERATED_QUESTIONS_DIR = CONTENT_DIR / "generated"
QUIZZES_DIR = CONTENT_DIR / "quizzes"
SCHEMA_VERSION = "1.0"


class QuestionSet(BaseModel):
    schema_version: str
    questions: list[Question]


class QuizSet(BaseModel):
    schema_version: str
    quizzes: list[Quiz]


@dataclass
class ContentStore:
    questions: dict[str, Question]
    questions_by_grade: dict[int, list[Question]]
    quizzes: dict[str, Quiz]

    def list_topics(self, grade: int) -> list[str]:
        return sorted({q.topic for q in self.questions_by_grade.get(grade, [])})

    def get_random_questions(self, grade: int, topic: str, n: int) -> list[Question]:
        available = [q for q in self.questions_by_grade.get(grade, []) if q.topic == topic]
        if not available:
            raise ValueError(f"No questions found for grade {grade} and topic {topic}.")
        k = min(len(available), n)
        return random.sample(available, k=k)

    def get_quiz(self, quiz_id: str) -> Quiz:
        try:
            return self.quizzes[quiz_id]
        except KeyError as exc:
            raise ValueError(f"Quiz {quiz_id} not found") from exc


def _load_question_file(path: Path) -> Iterable[Question]:
    with path.open("r", encoding="utf-8") as handle:
        if path.suffix in {".yaml", ".yml"}:
            raw = yaml.safe_load(handle)
        else:
            raw = json.load(handle)
    try:
        question_set = QuestionSet.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(f"Invalid question file {path}: {exc}") from exc
    if question_set.schema_version != SCHEMA_VERSION:
        raise ValueError(
            f"Schema version mismatch in {path}: {question_set.schema_version} != {SCHEMA_VERSION}"
        )
    return question_set.questions


def _load_quiz_file(path: Path) -> Iterable[Quiz]:
    with path.open("r", encoding="utf-8") as handle:
        if path.suffix in {".yaml", ".yml"}:
            raw = yaml.safe_load(handle)
        else:
            raw = json.load(handle)
    try:
        quiz_set = QuizSet.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(f"Invalid quiz file {path}: {exc}") from exc
    if quiz_set.schema_version != SCHEMA_VERSION:
        raise ValueError(
            f"Schema version mismatch in {path}: {quiz_set.schema_version} != {SCHEMA_VERSION}"
        )
    return quiz_set.quizzes


def load_content() -> ContentStore:
    question_map: dict[str, Question] = {}
    questions_by_grade: dict[int, list[Question]] = {}

    question_dirs = [QUESTIONS_DIR, GENERATED_QUESTIONS_DIR]
    for directory in question_dirs:
        if not directory.exists():
            continue
        for pattern in ("*.y*ml", "*.json"):
            for path in directory.glob(pattern):
                for question in _load_question_file(path):
                    question_map[question.id] = question
                    questions_by_grade.setdefault(question.grade, []).append(question)

    quizzes: dict[str, Quiz] = {}
    for path in QUIZZES_DIR.glob("*.y*ml"):
        for quiz in _load_quiz_file(path):
            quizzes[quiz.id] = quiz

    return ContentStore(question_map, questions_by_grade, quizzes)


_store: ContentStore | None = None


def get_store() -> ContentStore:
    global _store
    if _store is None:
        _store = load_content()
    return _store


def list_topics(grade: int) -> list[str]:
    return get_store().list_topics(grade)


def get_random_questions(grade: int, topic: str, n: int) -> list[Question]:
    return get_store().get_random_questions(grade, topic, n)


def get_quiz(quiz_id: str) -> Quiz:
    return get_store().get_quiz(quiz_id)


def iter_questions(ids: Sequence[str]) -> Iterable[Question]:
    store = get_store()
    for qid in ids:
        if qid not in store.questions:
            raise ValueError(f"Question {qid} not found")
        yield store.questions[qid]
