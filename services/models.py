from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

DifficultyLevel = Literal["easy", "medium", "hard"]


class Question(BaseModel):
    id: str
    grade: int
    topic: str
    difficulty: DifficultyLevel
    stem: str
    choices: list[str] | None = None
    answer: str
    solution_explainer: str
    tags: list[str] = Field(default_factory=list)


class Quiz(BaseModel):
    id: str
    title: str
    grade: int
    topic: str
    question_ids: list[str]


class AttemptMetadata(BaseModel):
    diagnostic_id: str | None = None
    source: str | None = None


class Attempt(BaseModel):
    user_id: str
    question_id: str
    submitted: str
    correct: bool
    timestamp: datetime
    metadata: AttemptMetadata = Field(default_factory=AttemptMetadata)


class DiagnosticSubmission(BaseModel):
    question: Question
    submitted_answer: str

    @property
    def is_correct(self) -> bool:
        return self.question.answer.strip().lower() == self.submitted_answer.strip().lower()


class TopicScore(BaseModel):
    topic: str
    total_questions: int
    correct_answers: int

    @property
    def accuracy(self) -> float:
        if self.total_questions == 0:
            return 0.0
        return self.correct_answers / self.total_questions

    @property
    def level(self) -> int:
        percentage = self.accuracy * 100
        if percentage < 40:
            return 1
        if percentage < 55:
            return 2
        if percentage < 70:
            return 3
        if percentage < 85:
            return 4
        return 5


class DiagnosticResult(BaseModel):
    total_questions: int
    total_correct: int
    topics: list[TopicScore]

    @property
    def overall_accuracy(self) -> float:
        if self.total_questions == 0:
            return 0.0
        return self.total_correct / self.total_questions

    @property
    def skill_profile(self) -> dict[str, int]:
        return {topic.topic: topic.level for topic in self.topics}


class PDFRequest(BaseModel):
    title: str
    include_solutions: bool = False
    questions: list[Question]


class LLMFeedbackRequest(BaseModel):
    question: Question
    student_answer: str


class LLMFeedbackResponse(BaseModel):
    feedback: str
    fallback_used: bool = False
    error_message: str | None = None
    external_url: HttpUrl | None = None
