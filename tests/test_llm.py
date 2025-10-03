from __future__ import annotations

import asyncio
from contextlib import AbstractContextManager
import sys
import types
from typing import Any, Protocol, cast

import httpx
import pytest
from httpx import Request, Response

try:
    import pypdf  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    fake_pypdf = types.ModuleType("pypdf")
    fake_pypdf.PdfReader = object  # type: ignore[attr-defined]
    sys.modules.setdefault("pypdf", fake_pypdf)

from llm.deepseek import DeepSeekProvider
from services.content import get_store
from services.question_bank import CurriculumQuestionBankBuilder
from services.models import LLMFeedbackRequest


class _RespxModule(Protocol):
    def mock(self, *, base_url: str) -> AbstractContextManager[Any]: ...


try:
    import respx as _respx_mod  # type: ignore
except ModuleNotFoundError:
    _respx_mod = None

respx = cast(_RespxModule | None, _respx_mod)


def test_deepseek_provider_success() -> None:
    if respx is None:
        pytest.skip("respx is required for HTTP mocking")
    store = get_store()
    question = store.questions["g7_aritmetik_001"]
    provider = DeepSeekProvider(api_key="test-key", base_url="https://mocked")
    async def _run() -> None:
        assert respx is not None
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

    asyncio.run(_run())


def test_deepseek_provider_error() -> None:
    if respx is None:
        pytest.skip("respx is required for HTTP mocking")
    store = get_store()
    question = store.questions["g7_aritmetik_001"]
    provider = DeepSeekProvider(api_key="test-key", base_url="https://mocked")
    async def _run() -> None:
        assert respx is not None
        with respx.mock(base_url="https://mocked") as router:
            router.post("/").mock(return_value=Response(500, json={"error": "fail"}))
            with pytest.raises(RuntimeError) as exc_info:
                await provider.feedback(
                    LLMFeedbackRequest(question=question, student_answer="11")
                )
        message = str(exc_info.value)
        assert "status code 500" in message
        assert "fail" in message
        assert exc_info.value.__cause__ is not None

    asyncio.run(_run())


def test_deepseek_provider_timeout_includes_exception_name() -> None:
    if respx is None:
        pytest.skip("respx is required for HTTP mocking")
    store = get_store()
    question = store.questions["g7_aritmetik_001"]
    provider = DeepSeekProvider(api_key="test-key", base_url="https://mocked")
    timeout_exc = httpx.TimeoutException(
        "", request=Request("POST", "https://mocked/")
    )
    async def _run() -> None:
        assert respx is not None
        with respx.mock(base_url="https://mocked") as router:
            router.post("/").mock(side_effect=timeout_exc)
            with pytest.raises(RuntimeError) as exc_info:
                await provider.feedback(
                    LLMFeedbackRequest(question=question, student_answer="11")
                )
        message = str(exc_info.value)
        assert "request timed out" in message
        assert "TimeoutException" in message
        assert exc_info.value.__cause__ is timeout_exc

    asyncio.run(_run())


def test_question_bank_health_check_logs_cause(tmp_path, caplog) -> None:
    builder = CurriculumQuestionBankBuilder(output_dir=tmp_path)

    class DummyCause(Exception):
        pass

    class DummyClient:
        async def health_check(self) -> None:
            raise RuntimeError("Yttre fel") from DummyCause()

    class DummyGenerator:
        def __init__(self) -> None:
            self.client = DummyClient()

    with caplog.at_level("ERROR"):
        with pytest.raises(RuntimeError) as exc_info:
            builder._ensure_health_check(DummyGenerator())
    assert "DeepSeek-hälsokontrollen misslyckades" in str(exc_info.value)
    assert any("DummyCause" in message for message in caplog.messages)
    assert not builder._health_check_completed
    with respx.mock(base_url="https://mocked") as router:
        router.post("/").mock(return_value=Response(500, json={"error": "fail"}))
        with pytest.raises(RuntimeError) as exc_info:
            await provider.feedback(
                LLMFeedbackRequest(question=question, student_answer="11")
            )
    message = str(exc_info.value)
    assert "status code 500" in message
    assert "fail" in message
    assert exc_info.value.__cause__ is not None
