from __future__ import annotations

from typing import cast

import streamlit as st

from app import _bootstrap  # noqa: F401
from services import profiles
from services.diagnostics import score_submission
from services.models import DiagnosticResult, DiagnosticSubmission
from services.recommendations import recommend_exercises

st.set_page_config(page_title="Resultat", page_icon="📊")

raw_submissions = cast(list[DiagnosticSubmission] | None, st.session_state.get("submissions"))
if raw_submissions is None or not raw_submissions:
    st.warning("Genomför en diagnostik innan du visar resultat.")
    st.stop()

submissions = raw_submissions

if st.session_state.result is None:
    st.session_state.result = score_submission(submissions)

result: DiagnosticResult = st.session_state.result

active_profile = profiles.get_profile(st.session_state.get("profile_id"))
if active_profile:
    st.caption(f"Aktiv profil: {active_profile.label}")
    pending_levels = {
        topic: level
        for topic, level in result.skill_profile.items()
        if active_profile.skill_profile.get(topic) != level
    }
    if pending_levels:
        try:
            active_profile = profiles.update_profile(
                active_profile.id,
                skill_profile=pending_levels,
            )
        except ValueError:
            active_profile = None

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
    grade = active_profile.last_grade if active_profile else None
    skill_profile = active_profile.skill_profile if active_profile else None
    st.session_state.recommendations = recommend_exercises(
        result,
        grade=grade,
        skill_profile=skill_profile,
    )
    st.success("Rekommendationer uppdaterade! Gå vidare till sidan '3_Ovningar'.")
