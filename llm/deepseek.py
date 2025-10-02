from __future__ import annotations

import os
from typing import Any

import asyncio
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
    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        timeout: float = 12.0,
        max_retries: int = 2,
        retry_backoff: float = 1.5,
    ) -> None:
        if not api_key:
            raise ValueError("DeepSeek API key is required")
        self.api_key = api_key
        self.base_url = base_url or "https://api.deepseek.com/v1/chat/completions"
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

    async def feedback(self, request: LLMFeedbackRequest) -> str:
        prompt = _env.from_string(PROMPT_TEMPLATE).render(
            question=request.question,
            student_answer=request.student_answer,
        )
        timeout = httpx.Timeout(self.timeout)
        for attempt in range(self.max_retries + 1):
            async with httpx.AsyncClient(timeout=timeout) as client:
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
                    break
                except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.RequestError) as exc:
                    if attempt >= self.max_retries:
                        raise RuntimeError("DeepSeek API request failed") from exc
                    await asyncio.sleep(self.retry_backoff * (attempt + 1))

        try:
            data: dict[str, Any] = response.json()
        except ValueError as exc:
            raise RuntimeError("DeepSeek API response was not valid JSON") from exc
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
