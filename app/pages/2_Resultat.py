from __future__ import annotations

import streamlit as st

from services import profiles
from services.diagnostics import score_submission
from services.models import DiagnosticResult, DiagnosticSubmission
from services.recommendations import recommend_exercises

st.set_page_config(page_title="Resultat", page_icon="📊")

submissions: list[DiagnosticSubmission] | None = st.session_state.get("submissions")
if not submissions:
    st.warning("Genomför en diagnostik innan du visar resultat.")
    st.stop()

if st.session_state.result is None:
    st.session_state.result = score_submission(submissions)

result: DiagnosticResult = st.session_state.result

active_profile = profiles.get_profile(st.session_state.get("profile_id"))
if active_profile:
    st.caption(f"Aktiv profil: {active_profile.label}")

st.header("Resultat")
st.metric("Totalt antal frågor", result.total_questions)
st.metric("Antal rätt", result.total_correct)
st.metric("Träffsäkerhet", f"{result.overall_accuracy * 100:.0f}%")

st.subheader("Detaljer per område")
for topic in result.topics:
    st.write(
        f"**{topic.topic}** – {topic.correct_answers}/{topic.total_questions} rätt (nivå {topic.level})"
    )

if st.button("Beräkna rekommendationer", type="primary"):
    st.session_state.recommendations = recommend_exercises(result)
    st.success("Rekommendationer uppdaterade! Gå vidare till sidan '3_Ovningar'.")
