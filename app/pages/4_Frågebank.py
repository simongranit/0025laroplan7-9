from __future__ import annotations

import asyncio
from pathlib import Path

import streamlit as st

from llm.deepseek import get_chat_client
from services import content
from services.question_bank import (
    GENERATED_DIR,
    CurriculumQuestionBankBuilder,
    QuestionBankRequest,
)

st.title("Frågebank (DeepSeek)")
st.write(
    "Skapa och återanvänd större frågebanker med hjälp av DeepSeek. "
    "Frågorna sparas lokalt och kan återanvändas vid framtida körningar."
)

client_available = get_chat_client() is not None
if not client_available:
    st.warning(
        "DeepSeek är inte konfigurerat ännu. Sätt `DEEPSEEK_API_KEY` för att kunna "
        "generera nya frågor."
    )

if st.button("Testa DeepSeek-anslutning", disabled=not client_available):
    client = get_chat_client()
    if client is None:
        st.error("DeepSeek-klienten kunde inte initieras.")
    else:
        with st.spinner("Kontrollerar anslutningen..."):
            try:
                asyncio.run(client.health_check())
            except Exception as exc:  # noqa: BLE001
                st.error(f"Anslutningstestet misslyckades: {exc}")
            else:
                st.success("Anslutningen fungerar!")

grade = st.selectbox("Årskurs", [7, 8, 9], index=[7, 8, 9].index(st.session_state.get("grade", 7)))
all_topics = content.list_topics(grade)
selected_topics = st.multiselect("Ämnen", options=all_topics, default=all_topics[:1])

col_config = st.columns(2)
with col_config[0]:
    total_questions = st.slider("Antal frågor totalt", min_value=10, max_value=120, step=10, value=60)
    temperature = st.slider("Temperature", min_value=0.0, max_value=1.2, value=0.6, step=0.1)
with col_config[1]:
    max_tokens = st.slider("Max tokens per svar", min_value=900, max_value=3200, value=2200, step=100)
    refresh = st.checkbox("Skapa om även om fil finns", value=False)

builder = CurriculumQuestionBankBuilder()

if st.button("Generera frågebank", disabled=not client_available):
    request = QuestionBankRequest(
        grade=grade,
        topics=selected_topics,
        total_questions=total_questions,
        temperature=temperature,
        max_tokens=max_tokens,
        refresh=refresh,
    )
    try:
        output_path = builder.build(request)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Kunde inte generera frågebank: {exc}")
    else:
        try:
            display_path = output_path.relative_to(Path.cwd())
        except ValueError:
            display_path = output_path
        st.success(
            "Frågebanken genererades! Filen finns på: "
            f"`{display_path}`"
        )

st.markdown("---")
st.subheader("Tillgängliga frågebanker")
existing_files = sorted(GENERATED_DIR.glob("*.json"))
if not existing_files:
    st.info("Inga genererade frågebanker hittades ännu.")
else:
    for file_path in existing_files:
        try:
            display_path = file_path.relative_to(Path.cwd())
        except ValueError:
            display_path = file_path
        st.write(f"• `{display_path}`")
