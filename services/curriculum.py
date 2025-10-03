from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Sequence

from pypdf import PdfReader

logger = logging.getLogger(__name__)

CURRICULUM_PDFS: dict[int, Path] = {
    7: Path("Matematik_Åk7.pdf"),
    8: Path("Matematik_Åk8.pdf"),
    9: Path("Matematik_Åk9.pdf"),
}

_DEFAULT_WINDOW = 800
_FALLBACK_CHARS = 1200


def available_grades() -> set[int]:
    """Return the set of grades that have an associated curriculum PDF."""

    return set(CURRICULUM_PDFS)


@lru_cache(maxsize=None)
def get_curriculum_text(grade: int) -> str:
    """Return the full, flattened curriculum text for the given grade."""

    if grade not in CURRICULUM_PDFS:
        msg = f"Okänd årskurs: {grade}"
        raise ValueError(msg)
    path = CURRICULUM_PDFS[grade]
    if not path.exists():
        logger.warning("Kunde inte hitta läroplansfil för Åk %s (%s)", grade, path)
        return ""
    reader = PdfReader(str(path))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text)
    combined = "\n".join(pages)
    return _squash_whitespace(combined)


def build_curriculum_outline(
    grade: int,
    topics: Sequence[str],
    *,
    window: int = _DEFAULT_WINDOW,
    fallback_chars: int = _FALLBACK_CHARS,
) -> str:
    """Return contextual snippets from the curriculum for the requested topics."""

    base_text = get_curriculum_text(grade)
    if not base_text:
        return ""
    lowered = base_text.lower()
    sections: list[str] = []
    for topic in topics:
        if not topic:
            continue
        marker = topic.lower()
        start = lowered.find(marker)
        if start == -1:
            snippet = base_text[:fallback_chars]
        else:
            snippet = base_text[max(0, start - window) : start + window]
        cleaned = _squash_whitespace(snippet)
        sections.append(f"Ämne: {topic}\n{cleaned}")
    return "\n\n".join(sections)


def _squash_whitespace(value: str) -> str:
    import re

    return re.sub(r"\s+", " ", value).strip()
