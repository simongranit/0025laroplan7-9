from __future__ import annotations

import os
from typing import Any

import httpx
from jinja2 import Environment

from services.models import LLMFeedbackRequest

from .base import LLMProvider, NullLLMProvider

PROMPT_TEMPLATE = """Du är en hjälpsam mattelärare. Eleven har svarat på en fråga.
Fråga: {{ question.stem }}
Givet svar: {{ student_answer }}
Korrekt svar: {{ question.answer }}
Förklara steg för steg på svenska (max 120 ord) och uppmuntra eleven.
"""

_env = Environment(autoescape=False)


class DeepSeekProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str | None = None, timeout: float = 8.0) -> None:
        if not api_key:
            raise ValueError("DeepSeek API key is required")
        self.api_key = api_key
        self.base_url = base_url or "https://api.deepseek.com/v1/chat/completions"
        self.timeout = timeout

    async def feedback(self, request: LLMFeedbackRequest) -> str:
        prompt = _env.from_string(PROMPT_TEMPLATE).render(
            question=request.question,
            student_answer=request.student_answer,
        )
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    self.base_url,
                    json={
                        "model": "deepseek-chat",
                        "messages": [
                            {"role": "system", "content": "Du är en vänlig mattelärare."},
                            {"role": "user", "content": prompt},
                        ],
                        "max_tokens": 350,
                        "temperature": 0.7,
                    },
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                response.raise_for_status()
            except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.RequestError) as exc:
                raise RuntimeError("DeepSeek API request failed") from exc

        data: dict[str, Any] = response.json()
        try:
            choices = data["choices"]
            message = choices[0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Unexpected DeepSeek response structure") from exc
        return str(message)


def get_llm_provider() -> LLMProvider:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        return NullLLMProvider()
    return DeepSeekProvider(api_key)
