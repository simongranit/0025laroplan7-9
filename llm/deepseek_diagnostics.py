from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Protocol


class CompletionCallable(Protocol):
    async def __call__(
        self,
        messages: Iterable[dict[str, str]],
        *,
        max_tokens: int = 512,
        temperature: float = 0.0,
    ) -> str:
        ...


@dataclass(slots=True)
class DeepSeekDiagnosticRun:
    """Result information from a diagnostic DeepSeek invocation."""

    prompt_repeats: int
    max_tokens: int
    duration: float
    success: bool
    error: str | None = None
    response_preview: str | None = None


async def run_diagnostic_sequence(
    complete: CompletionCallable,
    prompt_repeats: Iterable[int],
    *,
    max_tokens: int = 512,
    temperature: float = 0.0,
) -> list[DeepSeekDiagnosticRun]:
    """Run progressively heavier prompts with the provided completion callable."""

    base_instruction = (
        "Du är en hjälpsam mattelärare. Förklara resonemangen för varje uppgift nedan.\n\n"
    )
    sample_problem = (
        "Problem: Beräkna 12 * 18 och redovisa alla steg.\n"
        "Problem: Lös ekvationen 3x + 5 = 23 och motivera lösningen.\n"
    )
    results: list[DeepSeekDiagnosticRun] = []
    for repeats in prompt_repeats:
        prompt_body = sample_problem * max(repeats, 1)
        messages = [
            {"role": "system", "content": "Du är en hjälpsam mattelärare."},
            {"role": "user", "content": base_instruction + prompt_body},
        ]
        start = perf_counter()
        try:
            response = await complete(
                messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as exc:  # noqa: BLE001 - propagate diagnostic info
            duration = perf_counter() - start
            results.append(
                DeepSeekDiagnosticRun(
                    prompt_repeats=repeats,
                    max_tokens=max_tokens,
                    duration=duration,
                    success=False,
                    error=str(exc),
                )
            )
            break
        duration = perf_counter() - start
        preview = response.strip()
        results.append(
            DeepSeekDiagnosticRun(
                prompt_repeats=repeats,
                max_tokens=max_tokens,
                duration=duration,
                success=True,
                response_preview=preview[:200] if preview else None,
            )
        )
    return results


async def run_diagnostic_load_test(
    client: Any,
    prompt_repeats: Iterable[int],
    *,
    max_tokens: int = 512,
    temperature: float = 0.0,
) -> list[DeepSeekDiagnosticRun]:
    """Run the diagnostic sequence against any DeepSeek-like client.

    Falls back to the client's ``complete`` coroutine when ``diagnostic_runs`` is
    not available (e.g. on legacy instances).
    """

    if hasattr(client, "diagnostic_runs"):
        diagnostic = getattr(client, "diagnostic_runs")
        if callable(diagnostic):
            return await diagnostic(  # type: ignore[misc]
                prompt_repeats,
                max_tokens=max_tokens,
                temperature=temperature,
            )

    if not hasattr(client, "complete"):
        raise AttributeError("DeepSeek-klienten saknar stöd för anslutningsdiagnos.")

    complete = getattr(client, "complete")
    if not callable(complete):  # pragma: no cover - defensive guard
        raise TypeError("DeepSeek-klientens 'complete'-attribut är inte anropbart.")

    return await run_diagnostic_sequence(
        complete,  # type: ignore[arg-type]
        prompt_repeats,
        max_tokens=max_tokens,
        temperature=temperature,
    )


__all__ = [
    "CompletionCallable",
    "DeepSeekDiagnosticRun",
    "run_diagnostic_load_test",
    "run_diagnostic_sequence",
]
