from __future__ import annotations

import pytest
import respx
from httpx import Response

from llm.deepseek import DeepSeekProvider
from services.content import get_store
from services.models import LLMFeedbackRequest


@pytest.mark.asyncio
async def test_deepseek_provider_success() -> None:
    store = get_store()
    question = store.questions["g7_aritmetik_001"]
    provider = DeepSeekProvider(api_key="test-key", base_url="https://mocked")
    with respx.mock(base_url="https://mocked") as router:
        router.post("/").mock(return_value=Response(200, json={
            "choices": [
                {"message": {"content": "Förklara på svenska"}}
            ]
        }))
        response = await provider.feedback(
            LLMFeedbackRequest(question=question, student_answer="11")
        )
    assert "Förklara" in response


@pytest.mark.asyncio
async def test_deepseek_provider_error() -> None:
    store = get_store()
    question = store.questions["g7_aritmetik_001"]
    provider = DeepSeekProvider(api_key="test-key", base_url="https://mocked")
    with respx.mock(base_url="https://mocked") as router:
        router.post("/").mock(return_value=Response(500, json={"error": "fail"}))
        with pytest.raises(RuntimeError):
            await provider.feedback(
                LLMFeedbackRequest(question=question, student_answer="11")
            )
