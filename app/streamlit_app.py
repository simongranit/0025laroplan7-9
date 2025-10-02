from __future__ import annotations

import streamlit as st
from dotenv import load_dotenv

from services import content, diagnostics, profiles

load_dotenv()

st.set_page_config(page_title="Matte Diagnostik Åk 7–9", page_icon="🧮", layout="wide")

if "grade" not in st.session_state:
    st.session_state.grade = 7
if "topic" not in st.session_state:
    st.session_state.topic = None
if "diagnostic_questions" not in st.session_state:
    st.session_state.diagnostic_questions = []
if "submissions" not in st.session_state:
    st.session_state.submissions = []
if "result" not in st.session_state:
    st.session_state.result = None
if "recommendations" not in st.session_state:
    st.session_state.recommendations = []
if "profile_id" not in st.session_state:
    st.session_state.profile_id = None

st.title("Matte Diagnostik för årskurs 7–9")
st.markdown(
    "Välj årskurs och ämne för att starta en kort diagnostik."
)

existing_profiles = profiles.list_profiles()
selected_profile = None
if existing_profiles:
    options = {profile.id: profile for profile in existing_profiles}
    option_ids = list(options.keys())
    default_id = st.session_state.profile_id or option_ids[0]
    if default_id not in options:
        default_id = option_ids[0]
    selected_profile_id = st.selectbox(
        "Välj profil",
        option_ids,
        index=option_ids.index(default_id),
        format_func=lambda pid: options[pid].label,
    )
    selected_profile = options[selected_profile_id]
    if selected_profile_id != st.session_state.profile_id:
        st.session_state.profile_id = selected_profile_id
        st.session_state.grade = selected_profile.last_grade
        st.session_state.topic = selected_profile.last_topic
else:
    st.info("Skapa en profil för att spara dina preferenser mellan sessioner.")

with st.expander("Skapa ny profil"):
    with st.form("create_profile_form", clear_on_submit=True):
        name = st.text_input("Namn", placeholder="Till exempel: Alex")
        default_grade = (
            st.session_state.grade if st.session_state.grade in {7, 8, 9} else 7
        )
        profile_grade = st.selectbox(
            "Startårskurs",
            [7, 8, 9],
            index=[7, 8, 9].index(default_grade),
        )
        create_submitted = st.form_submit_button("Skapa profil")
        if create_submitted:
            profile = profiles.create_profile(name, profile_grade)
            st.session_state.profile_id = profile.id
            st.session_state.grade = profile.last_grade
            st.session_state.topic = profile.last_topic
            st.success(f"Profilen '{profile.name}' skapades.")
            st.rerun()

if selected_profile:
    st.caption(f"Aktiv profil: {selected_profile.label}")

cols = st.columns(2)
with cols[0]:
    current_grade = st.session_state.grade if st.session_state.grade in {7, 8, 9} else 7
    grade = st.selectbox(
        "Årskurs",
        [7, 8, 9],
        index=[7, 8, 9].index(current_grade),
    )
    if grade != st.session_state.grade:
        st.session_state.grade = grade
        if st.session_state.profile_id:
            try:
                profiles.update_profile(st.session_state.profile_id, last_grade=grade)
            except ValueError:
                st.session_state.profile_id = None
with cols[1]:
    topics = content.list_topics(grade)
    topic = st.selectbox("Ämne", topics or ["Ingen data"])
    if topic != st.session_state.topic:
        st.session_state.topic = topic
        if st.session_state.profile_id and topic != "Ingen data":
            try:
                profiles.update_profile(st.session_state.profile_id, last_topic=topic)
            except ValueError:
                st.session_state.profile_id = None

if st.button("Starta diagnostik"):
    st.session_state.grade = grade
    st.session_state.topic = topic
    skill_profile = selected_profile.skill_profile if selected_profile else None
    try:
        questions = diagnostics.generate_diagnostic(
            grade,
            [topic],
            skill_profile=skill_profile,
        )
    except ValueError as exc:
        st.error(str(exc))
    else:
        st.session_state.diagnostic_questions = questions
        st.session_state.submissions = []
        st.session_state.result = None
        st.session_state.recommendations = []
        if st.session_state.profile_id and topic != "Ingen data":
            try:
                profiles.update_profile(
                    st.session_state.profile_id,
                    last_grade=grade,
                    last_topic=topic,
                )
            except ValueError:
                st.session_state.profile_id = None
        st.success("Diagnostik startad! Gå till sidan '1_Diagnostik' för att börja.")

st.markdown("---")
st.write("Använd sidomenyn för att navigera mellan diagnos, resultat och övningar.")
