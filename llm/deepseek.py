from __future__ import annotations

import asyncio
import os
from collections.abc import Iterable
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


class DeepSeekChatClient:
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

    async def complete(
        self,
        messages: Iterable[dict[str, str]],
        *,
        max_tokens: int = 350,
        temperature: float = 0.7,
    ) -> str:
        timeout = httpx.Timeout(self.timeout)
        payload = {
            "model": "deepseek-chat",
            "messages": list(messages),
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        for attempt in range(self.max_retries + 1):
            async with httpx.AsyncClient(timeout=timeout) as client:
                try:
                    response = await client.post(
                        self.base_url,
                        json=payload,
                        headers={"Authorization": f"Bearer {self.api_key}"},
                    )
                    response.raise_for_status()
                    break
                except (
                    httpx.TimeoutException,
                    httpx.HTTPStatusError,
                    httpx.RequestError,
                ) as exc:
                    if attempt >= self.max_retries:
                        details = ""
                        if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
                            response_text = exc.response.text
                            details = (
                                " (status code "
                                f"{exc.response.status_code}, response: {response_text})"
                            )
                        elif isinstance(exc, httpx.TimeoutException):
                            details = " (request timed out)"
                        elif isinstance(exc, httpx.RequestError) and exc.request is not None:
                            details = f" (request error for {exc.request.url!r})"
                        error_text = _describe_exception(exc)
                        cause = exc.__cause__ or exc.__context__
                        if cause is not None:
                            error_text = f"{error_text} (cause: {_describe_exception(cause)})"
                        raise RuntimeError(
                            f"DeepSeek API request failed{details}: {error_text}"
                        raise RuntimeError(
                            f"DeepSeek API request failed{details}: {exc}"
                        ) from exc
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

    async def health_check(self) -> None:
        """Perform a lightweight request to ensure the API is reachable."""
        response = await self.complete(
            [
                {"role": "system", "content": "Du är ett diagnostiskt övervakningsverktyg."},
                {"role": "user", "content": "Svara enbart med OK."},
            ],
            max_tokens=8,
            temperature=0.0,
        )
        if not response.strip():
            raise RuntimeError("DeepSeek API health check returned an empty response.")


class DeepSeekProvider(LLMProvider):
    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        timeout: float = 12.0,
        max_retries: int = 2,
        retry_backoff: float = 1.5,
    ) -> None:
        self.client = DeepSeekChatClient(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            retry_backoff=retry_backoff,
        )

    async def feedback(self, request: LLMFeedbackRequest) -> str:
        prompt = _env.from_string(PROMPT_TEMPLATE).render(
            question=request.question,
            student_answer=request.student_answer,
        )
        return await self.client.complete(
            [
                {"role": "system", "content": "Du är en vänlig mattelärare."},
                {"role": "user", "content": prompt},
            ]
        )


def get_llm_provider() -> LLMProvider:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        return NullLLMProvider()
    base_url = os.getenv("DEEPSEEK_API_BASE_URL", "").strip() or None
    return DeepSeekProvider(api_key, base_url=base_url)


def get_chat_client() -> DeepSeekChatClient | None:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        return None
    base_url = os.getenv("DEEPSEEK_API_BASE_URL", "").strip() or None
    return DeepSeekChatClient(api_key, base_url=base_url)


def _describe_exception(exc: BaseException) -> str:
    message = str(exc).strip()
    if message:
        return message
    return exc.__class__.__name__
