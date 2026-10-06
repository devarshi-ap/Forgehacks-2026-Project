"""Run this file to see the three screens with mock data:

    streamlit run frontend/demo_app.py

(run the command from the project's MAIN folder, so .streamlit/config.toml is found)
"""
import streamlit as st

import components
import screens
import styles

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
