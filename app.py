"""Run this file to see the three screens with mock data:

    streamlit run app.py

(run the command from the project's main folder, so .streamlit/config.toml is found)
"""
import streamlit as st

from frontend import components, screens, styles

st.set_page_config(page_title="StormSignal", page_icon="🌩️", layout="wide",
                   initial_sidebar_state="expanded")
styles.inject_css()
st.session_state.setdefault("step", "intake")

step = st.session_state["step"]
components.render_sidebar(step)

if step == "intake":
    screens.screen_intake()
elif step == "followups":
    screens.screen_followups()
else:
    screens.screen_results()
