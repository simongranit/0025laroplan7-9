from __future__ import annotations

import streamlit as st

from app import _bootstrap  # noqa: F401
from services import profiles
from services.models import DiagnosticSubmission

st.set_page_config(page_title="Diagnostik", page_icon="📝")

if "diagnostic_questions" not in st.session_state or not st.session_state.diagnostic_questions:
    st.warning("Starta en diagnostik från startsidan först.")
    st.stop()

if "current_index" not in st.session_state:
    st.session_state.current_index = 0

active_profile = profiles.get_profile(st.session_state.get("profile_id"))
if active_profile:
    st.caption(f"Aktiv profil: {active_profile.label}")

questions = st.session_state.diagnostic_questions
index = st.session_state.current_index
question = questions[index]

st.header(f"Fråga {index + 1} av {len(questions)}")
st.write(question.stem)

answer_key = f"answer_{question.id}"
default_value = st.session_state.get(answer_key, "")

if question.choices:
    answer = st.radio("Välj svar", question.choices, index=question.choices.index(default_value) if default_value in question.choices else 0)
else:
    answer = st.text_input("Ditt svar", value=default_value)

st.session_state[answer_key] = answer

cols = st.columns(3)
with cols[0]:
    if st.button("⬅️ Föregående", disabled=index == 0):
        st.session_state.current_index = max(0, index - 1)
        st.rerun()
with cols[1]:
    if st.button("Spara svar"):
        st.success("Svar sparat!")
with cols[2]:
    if st.button("Nästa ➡️", disabled=index >= len(questions) - 1):
        st.session_state.current_index = min(len(questions) - 1, index + 1)
        st.rerun()

st.markdown("---")

if st.button("Lämna in diagnostik", type="primary"):
    submissions = []
    for q in questions:
        submission = DiagnosticSubmission(question=q, submitted_answer=st.session_state.get(f"answer_{q.id}", ""))
        submissions.append(submission)
    st.session_state.submissions = submissions
    st.session_state.result = None
    st.success("Diagnostik inlämnad! Gå till sidan '2_Resultat'.")
