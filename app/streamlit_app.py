from __future__ import annotations

import streamlit as st
from dotenv import load_dotenv

from services import content, diagnostics

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


st.title("Matte Diagnostik för årskurs 7–9")
st.markdown(
    "Välj årskurs och ämne för att starta en kort diagnostik."
)

cols = st.columns(2)
with cols[0]:
    grade = st.selectbox("Årskurs", [7, 8, 9], index=[7, 8, 9].index(st.session_state.grade))
with cols[1]:
    topics = content.list_topics(grade)
    topic = st.selectbox("Ämne", topics or ["Ingen data"])

if st.button("Starta diagnostik"):
    st.session_state.grade = grade
    st.session_state.topic = topic
    try:
        questions = diagnostics.generate_diagnostic(grade, [topic])
    except ValueError as exc:
        st.error(str(exc))
    else:
        st.session_state.diagnostic_questions = questions
        st.session_state.submissions = []
        st.session_state.result = None
        st.session_state.recommendations = []
        st.success("Diagnostik startad! Gå till sidan '1_Diagnostik' för att börja.")

st.markdown("---")
st.write("Använd sidomenyn för att navigera mellan diagnos, resultat och övningar.")
