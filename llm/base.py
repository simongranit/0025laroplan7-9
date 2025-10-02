from __future__ import annotations

from typing import Protocol

from services.models import LLMFeedbackRequest


class LLMProvider(Protocol):
    async def feedback(self, request: LLMFeedbackRequest) -> str:
        """Generate formative feedback for a student's answer."""


class NullLLMProvider:
    async def feedback(self, request: LLMFeedbackRequest) -> str:  # noqa: D401
        return request.question.solution_explainer
