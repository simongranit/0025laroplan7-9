from __future__ import annotations

from dataclasses import MISSING, dataclass, field, fields
from datetime import datetime
from typing import Any, Literal, TypeVar, cast, get_args, get_origin
import types

NONE_TYPE = type(None)
UNION_TYPES = {types.UnionType}
try:  # pragma: no cover - typing.Union may not exist in older versions
    from typing import Union as TypingUnion

    UNION_TYPES.add(cast(type[Any], TypingUnion))
except ImportError:  # pragma: no cover
    pass

T = TypeVar("T", bound="ModelMixin")


class ModelMixin:
    """Lightweight replacement for the Pydantic helpers used in the project."""

    @classmethod
    def from_dict(cls: type[T], data: dict[str, Any]) -> T:
        if not isinstance(data, dict):  # pragma: no cover - defensive
            raise TypeError(f"Expected a mapping to create {cls.__name__}")
        kwargs: dict[str, Any] = {}
        for field_info in fields(cast(type[Any], cls)):
            name = field_info.name
            if name not in data:
                has_default = field_info.default is not MISSING or getattr(
                    field_info, "default_factory", MISSING
                ) is not MISSING
                if has_default:
                    continue
                raise ValueError(f"Missing required field {name} for {cls.__name__}")
            value = data[name]
            kwargs[name] = cls._convert_value(value, field_info.type)
        return cls(**kwargs)

    @classmethod
    def model_validate(cls: type[T], data: dict[str, Any]) -> T:
        return cls.from_dict(data)

    @staticmethod
    def _convert_value(value: Any, annotation: Any) -> Any:
        if annotation in {Any, None}:
            return value
        origin = get_origin(annotation)
        if origin is Literal:
            allowed = set(get_args(annotation))
            if value not in allowed:
                raise ValueError(f"Value {value!r} not in {allowed}")
            return value
        if origin in {list, tuple, set, frozenset}:
            (item_type,) = get_args(annotation) or (Any,)
            iterable = [] if value is None else value
            return [ModelMixin._convert_value(item, item_type) for item in iterable]
        if origin in {dict}:
            key_type, item_type = get_args(annotation) or (Any, Any)
            mapping = {} if value is None else value
            return {
                ModelMixin._convert_value(key, key_type): ModelMixin._convert_value(item, item_type)
                for key, item in mapping.items()
            }
        if origin in UNION_TYPES:
            for candidate in get_args(annotation):
                if candidate is NONE_TYPE and value is None:
                    return None
                try:
                    return ModelMixin._convert_value(value, candidate)
                except Exception:
                    continue
            return value
        if isinstance(annotation, type):
            if issubclass(annotation, ModelMixin):
                if isinstance(value, annotation):
                    return value
                if isinstance(value, dict):
                    return annotation.model_validate(value)
            if annotation is datetime:
                if isinstance(value, datetime):
                    return value
                if isinstance(value, str):
                    return datetime.fromisoformat(value)
            if annotation in {str, int, float, bool}:
                return annotation(value)
            if annotation is NONE_TYPE:
                return None
        return value

    def model_dump(self, mode: str | None = None) -> dict[str, Any]:
        def serialize(value: Any) -> Any:
            if isinstance(value, datetime):
                return value.isoformat()
            if isinstance(value, ModelMixin):
                return value.model_dump(mode=mode)
            if isinstance(value, list):
                return [serialize(item) for item in value]
            if isinstance(value, dict):
                return {key: serialize(item) for key, item in value.items()}
            return value

        result: dict[str, Any] = {}
        for field_info in fields(self):  # type: ignore[arg-type]
            value = getattr(self, field_info.name)
            if mode == "json":
                result[field_info.name] = serialize(value)
            else:
                result[field_info.name] = value
        return result

    def model_copy(self: T, *, update: dict[str, Any] | None = None) -> T:
        values = self.model_dump()
        if update:
            values.update(update)
        cls: type[T] = type(self)
        return cls.from_dict(values)

DifficultyLevel = Literal["easy", "medium", "hard"]


@dataclass
class Question(ModelMixin):
    id: str
    grade: int
    topic: str
    difficulty: DifficultyLevel
    stem: str
    choices: list[str] | None = None
    answer: str = ""
    solution_explainer: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class Quiz(ModelMixin):
    id: str
    title: str
    grade: int
    topic: str
    question_ids: list[str]


@dataclass
class AttemptMetadata(ModelMixin):
    diagnostic_id: str | None = None
    source: str | None = None


@dataclass
class Attempt(ModelMixin):
    user_id: str
    question_id: str
    submitted: str
    correct: bool
    timestamp: datetime
    metadata: AttemptMetadata = field(default_factory=AttemptMetadata)


@dataclass
class DiagnosticSubmission(ModelMixin):
    question: Question
    submitted_answer: str

    @property
    def is_correct(self) -> bool:
        return self.question.answer.strip().lower() == self.submitted_answer.strip().lower()


@dataclass
class TopicScore(ModelMixin):
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


@dataclass
class DiagnosticResult(ModelMixin):
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


@dataclass
class PDFRequest(ModelMixin):
    title: str
    include_solutions: bool = False
    questions: list[Question] = field(default_factory=list)


@dataclass
class LLMFeedbackRequest(ModelMixin):
    question: Question
    student_answer: str


@dataclass
class LLMFeedbackResponse(ModelMixin):
    feedback: str
    fallback_used: bool = False
    error_message: str | None = None
    external_url: str | None = None


@dataclass
class Profile(ModelMixin):
    id: str
    name: str
    last_grade: int
    last_topic: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    skill_profile: dict[str, int] = field(default_factory=dict)

    @property
    def label(self) -> str:
        return f"{self.name} (Åk {self.last_grade})"
