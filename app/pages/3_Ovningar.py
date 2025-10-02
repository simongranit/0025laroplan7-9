from __future__ import annotations

import asyncio

import streamlit as st

try:  # pragma: no cover - executed during startup
    from app import _bootstrap  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover
    import importlib.util
    import sys
    from pathlib import Path
    from types import ModuleType

    _app_dir = Path(__file__).resolve().parents[1]
    _package = ModuleType("app")
    _package.__path__ = [str(_app_dir)]
    sys.modules.setdefault("app", _package)

    _spec = importlib.util.spec_from_file_location("app._bootstrap", _app_dir / "_bootstrap.py")
    if _spec and _spec.loader:
        _module = importlib.util.module_from_spec(_spec)
        sys.modules["app._bootstrap"] = _module
        _spec.loader.exec_module(_module)
    else:  # pragma: no cover
        raise
    from app import _bootstrap  # noqa: F401

from llm.base import NullLLMProvider
from llm.deepseek import get_llm_provider
from services import profiles
from services.models import LLMFeedbackRequest, Question
from services.pdf import render_questions_to_pdf

st.set_page_config(page_title="Övningar", page_icon="📚")

recommendations: list[Question] = st.session_state.get("recommendations", [])
if not recommendations:
    st.warning("Beräkna rekommendationer från resultat-sidan först.")
    st.stop()

provider = get_llm_provider()

st.header("Rekommenderade övningar")
active_profile = profiles.get_profile(st.session_state.get("profile_id"))
if active_profile:
    st.caption(f"Aktiv profil: {active_profile.label}")

for question in recommendations:
    with st.expander(f"{question.topic}: {question.stem[:60]}..."):
        st.write(question.stem)
        if question.choices:
            for choice in question.choices:
                st.write(f"- {choice}")
        if st.button("Visa facit", key=f"solution_{question.id}"):
            st.info(f"**Svar:** {question.answer}\n\n**Förklaring:** {question.solution_explainer}")
        if not isinstance(provider, NullLLMProvider):
            if st.button("AI-förklaring", key=f"ai_{question.id}"):
                with st.spinner("Hämtar AI-förklaring..."):
                    request = LLMFeedbackRequest(
                        question=question,
                        student_answer=st.session_state.get(f"answer_{question.id}", ""),
                    )
                    feedback_text = asyncio.run(provider.feedback(request))
                    st.write(feedback_text)
        else:
            st.caption("AI-förklaringar kräver en konfigurerad DEEPSEEK_API_KEY.")

st.markdown("---")
include_solutions = st.checkbox("Inkludera lösningar i PDF", value=False)
pdf_bytes = render_questions_to_pdf(
    recommendations,
    title="Rekommenderade övningar",
    include_solutions=include_solutions,
)
st.download_button(
    label="Ladda ner som PDF",
    data=pdf_bytes,
    file_name="ovningar.pdf",
    mime="application/pdf",
)
