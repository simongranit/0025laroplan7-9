from __future__ import annotations

import asyncio
import importlib
import sys
import types
from contextlib import AbstractContextManager
from typing import Any, Iterable, Protocol, cast

import httpx
import pytest
from httpx import Request, Response

# The pdf module is optional in the test environment. Provide a lightweight stub
# to satisfy the import used by the production code without bringing in heavy
# dependencies.
try:  # pragma: no cover - exercised implicitly during import
    import pypdf  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - executed in CI without pypdf
    fake_pypdf = types.ModuleType("pypdf")
    setattr(fake_pypdf, "PdfReader", object)
    sys.modules.setdefault("pypdf", fake_pypdf)

from llm.deepseek import DeepSeekChatClient, DeepSeekDiagnosticRun, DeepSeekProvider
from services.content import get_store
from services.models import LLMFeedbackRequest
from services.question_bank import CurriculumQuestionBankBuilder


class _RespxModule(Protocol):
    def mock(self, *, base_url: str) -> AbstractContextManager[Any]: ...


respx_module: _RespxModule | None
try:  # pragma: no cover - respx is optional in the runtime environment
    respx_module = cast(_RespxModule, importlib.import_module("respx"))
except ModuleNotFoundError:  # pragma: no cover - executed in CI without respx
    respx_module = None

respx = respx_module


@pytest.mark.skipif(respx is None, reason="respx is required for HTTP mocking")
def test_deepseek_provider_success() -> None:
    store = get_store()
    question = store.questions["g7_aritmetik_001"]
    provider = DeepSeekProvider(api_key="test-key", base_url="https://mocked")

    async def _run() -> None:
        assert respx is not None
        with respx.mock(base_url="https://mocked") as router:
            router.post("/").mock(
                return_value=Response(
                    200,
                    json={
                        "choices": [
                            {"message": {"content": "Förklara på svenska"}},
                        ]
                    },
                )
            )
            response = await provider.feedback(
                LLMFeedbackRequest(question=question, student_answer="11")
            )
        assert "Förklara" in response

    asyncio.run(_run())


@pytest.mark.skipif(respx is None, reason="respx is required for HTTP mocking")
def test_deepseek_provider_error_includes_status_and_body() -> None:
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


@pytest.mark.skipif(respx is None, reason="respx is required for HTTP mocking")
def test_deepseek_provider_timeout_includes_exception_name() -> None:
    store = get_store()
    question = store.questions["g7_aritmetik_001"]
    provider = DeepSeekProvider(api_key="test-key", base_url="https://mocked")
    timeout_exc = httpx.TimeoutException("", request=Request("POST", "https://mocked/"))

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

    class DummyCauseError(Exception):
        pass

    class DummyClient:
        async def health_check(self) -> None:
            raise RuntimeError("Yttre fel") from DummyCauseError("Inre fel")

    class DummyGenerator:
        def __init__(self) -> None:
            self.client = DummyClient()

    with caplog.at_level("ERROR"):
        with pytest.raises(RuntimeError) as exc_info:
            builder._ensure_health_check(cast(Any, DummyGenerator()))

    assert "DeepSeek-hälsokontrollen misslyckades" in str(exc_info.value)
    assert any("DummyCauseError" in message for message in caplog.messages)
    assert not builder._health_check_completed


def test_deepseek_diagnostic_runs_stop_after_failure() -> None:
    class DummyDiagnosticClient(DeepSeekChatClient):
        def __init__(self) -> None:
            super().__init__(api_key="test-key", base_url="https://mocked")
            self._outcomes: list[str | Exception] = [
                "Första svaret",
                RuntimeError("misslyckades"),
                "Ej använd",  # säkerställ att vi skulle ha fler värden vid behov
            ]

        async def complete(
            self,
            messages: Iterable[dict[str, str]],
            *,
            max_tokens: int = 350,
            temperature: float = 0.7,
        ) -> str:
            assert messages, "diagnostik skickar alltid meddelanden"
            outcome = self._outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

    async def _run() -> None:
        client = DummyDiagnosticClient()
        results = await client.diagnostic_runs([1, 2, 3], max_tokens=128)
        assert [result.prompt_repeats for result in results] == [1, 2]
        assert all(isinstance(result, DeepSeekDiagnosticRun) for result in results)
        assert results[0].success
        assert not results[1].success
        assert "misslyckades" in (results[1].error or "")

    asyncio.run(_run())
