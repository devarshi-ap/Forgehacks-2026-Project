"""All custom CSS for StormSignal, taken from the Figma 'Theme & visible states' guide.

Colours:  canvas #101722, sidebar #17152D, surface #192331, raised #202D3E,
          text #F3F6FC, secondary text #B8C5D6, action #8BB9FF, border #435269,
          selected #223A59, safety text #FFD18A, safety surface #352B20.
Rules:    blue for actions/selection/focus, amber ONLY for safety notices.
"""
import streamlit as st

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

:root {
  --canvas:#101722; --sidebar:#17152D; --surface:#192331; --raised:#202D3E;
  --text:#F3F6FC; --muted:#B8C5D6; --action:#8BB9FF; --action-text:#101722;
  --border:#435269; --selected:#223A59; --safety-text:#FFD18A; --safety-surface:#352B20;
}

html, body, .stApp, button, input, textarea { font-family:'Inter', system-ui, sans-serif; }
.stApp { background:var(--canvas); color:var(--text); }
header[data-testid="stHeader"] { background:transparent; }
footer { visibility:hidden; }
.block-container { max-width:1160px; padding:48px 32px 56px 32px; }

/* ---------- sidebar (desktop steps) ---------- */
section[data-testid="stSidebar"] { background:var(--sidebar); border-right:none; }
@media (min-width: 769px) {
  section[data-testid="stSidebar"] { min-width:260px !important; max-width:260px !important; }
}
[data-testid="stSidebarUserContent"] { padding-top:8px; }

.ss-brand { display:flex; align-items:center; gap:10px; font-size:22px; font-weight:700; color:var(--text); }
.ss-brand svg { color:var(--action); }
.ss-tagline { color:var(--muted); font-size:16px; line-height:24px; margin:16px 0 28px 0; }
.ss-side-step { display:flex; align-items:center; gap:12px; padding:12px 14px; margin-bottom:10px;
  border:1px solid transparent; border-radius:10px; color:var(--muted); font-size:18px; line-height:27px; }
.ss-side-step.is-current { background:var(--selected); border-color:var(--action); color:var(--text); font-weight:600; }
.ss-badge { display:inline-flex; align-items:center; justify-content:center; width:28px; height:28px;
  border-radius:50%; background:var(--raised); color:var(--muted); font-size:14px; font-weight:600; flex:none; }
.is-current .ss-badge { background:var(--action); color:var(--action-text); }
.is-done .ss-badge { background:var(--raised); color:var(--action); }
.ss-demo-card { background:var(--surface); border-radius:12px; padding:16px; margin-top:28px; }
.ss-demo-label { color:var(--action); font-size:14px; font-weight:600; letter-spacing:.04em; margin-bottom:6px; }
.ss-demo-place { color:var(--text); font-size:16px; line-height:24px; }
.ss-demo-note { color:var(--muted); font-size:14px; line-height:21px; margin-top:6px; }
.ss-side-privacy { display:flex; gap:10px; align-items:flex-start; color:var(--muted); font-size:14px;
  line-height:21px; margin-top:72px; }
.ss-side-privacy svg { color:var(--action); flex:none; }

/* ---------- mobile-only header (brand + step chips) ---------- */
.ss-mobile-only { display:none; }
.ss-chips { display:grid; grid-template-columns:repeat(3, 1fr); gap:8px; margin:16px 0 24px 0; }
.ss-chip { display:flex; flex-direction:column; gap:8px; padding:12px; border-radius:10px; background:var(--surface);
  border:1px solid transparent; color:var(--muted); font-size:14px; line-height:21px; }
.ss-chip.is-current { background:var(--selected); border-color:var(--action); color:var(--text); font-weight:600; }
@media (max-width: 768px) {
  .ss-mobile-only { display:block; }
  .ss-topline { display:none !important; }
}

/* ---------- safety banner (amber is ONLY for safety) ---------- */
.ss-banner { display:flex; gap:12px; align-items:flex-start; background:var(--safety-surface); color:var(--safety-text);
  border-left:3px solid var(--safety-text); border-radius:8px; padding:16px 20px; margin-bottom:24px;
  font-size:16px; line-height:24px; }
.ss-banner svg { flex:none; margin-top:2px; }
.ss-warn-text { color:var(--safety-text); font-size:16px; line-height:24px; margin-top:16px; }

/* ---------- typography ---------- */
.ss-topline { display:flex; justify-content:space-between; color:var(--muted); font-size:14px; letter-spacing:.04em; margin-bottom:20px; }
.ss-topline .ss-act { color:var(--action); letter-spacing:0; }
.ss-eyebrow { color:var(--action); font-size:14px; line-height:21px; font-weight:600; letter-spacing:.04em; text-transform:uppercase; margin-bottom:8px; }
.ss-h1 { font-size:40px; line-height:48px; font-weight:700; color:var(--text); margin:0 0 8px 0; }
.ss-lead { font-size:18px; line-height:27px; color:var(--muted); margin:0 0 24px 0; }
.ss-h2 { font-size:28px; line-height:36px; font-weight:600; color:var(--text); margin:8px 0 8px 0; }
.ss-h3 { font-size:22px; line-height:33px; font-weight:600; color:var(--text); margin:16px 0 8px 0; }
.ss-body { font-size:18px; line-height:27px; color:var(--text); margin:0 0 16px 0; }
.ss-support { font-size:16px; line-height:24px; color:var(--muted); margin:0 0 16px 0; }
.ss-label { font-size:18px; line-height:27px; font-weight:600; color:var(--text); margin-top:8px; }
.ss-help { font-size:16px; line-height:24px; color:var(--muted); margin-bottom:8px; }
.ss-caption { font-size:14px; line-height:21px; color:var(--muted); margin:4px 0 16px 0; }
.ss-privacy { display:flex; gap:10px; align-items:center; color:var(--muted); font-size:16px; line-height:24px; margin:20px 0 24px 0; }
.ss-rule { border-top:1px solid var(--border); margin:32px 0 16px 0; }
.ss-footnote { font-size:14px; line-height:21px; color:var(--muted); }
@media (max-width: 640px) {
  .block-container { padding:20px 20px 40px 20px; }
  .ss-h1 { font-size:32px; line-height:38px; }
  .ss-h2 { font-size:24px; line-height:32px; }
}

/* ---------- cards built from st.container(key="card_...") ---------- */
[class*="st-key-card_"] { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:28px 32px; }
@media (max-width: 640px) { [class*="st-key-card_"] { padding:20px; } }

/* ---------- inputs: at least 56px high, 8px radius ---------- */
div[data-baseweb="input"], div[data-baseweb="base-input"], div[data-baseweb="textarea"] {
  background:var(--canvas) !important; border-radius:8px !important; }
div[data-baseweb="input"], div[data-baseweb="textarea"] { border:1px solid var(--border) !important; }
div[data-baseweb="input"]:focus-within, div[data-baseweb="textarea"]:focus-within {
  border-color:var(--action) !important; box-shadow:0 0 0 2px var(--action); }
div[data-baseweb="input"] input { min-height:56px; font-size:18px; color:var(--text); }
div[data-baseweb="textarea"] textarea { font-size:18px; line-height:27px; color:var(--text); }
[data-testid="stWidgetLabel"] p { font-size:18px; font-weight:600; color:var(--text); }

/* ---------- radio buttons as selectable cards ---------- */
div[role="radiogroup"] { gap:12px; }
div[role="radiogroup"] > label { background:var(--canvas); border:1px solid var(--border); border-radius:8px;
  padding:14px 16px; min-height:56px; width:100%; align-items:center; margin:0; }
div[role="radiogroup"] > label:has(input:checked) { background:var(--selected); border-color:var(--action); }
div[role="radiogroup"] label p { font-size:18px; line-height:27px; color:var(--text); }

/* ---------- checkboxes: 48px+ rows ---------- */
[data-testid="stCheckbox"] label { min-height:48px; align-items:center; }
[data-testid="stCheckbox"] label p { font-size:18px; line-height:27px; color:var(--text); }

/* ---------- buttons ---------- */
[data-testid^="stBaseButton-"] { min-height:56px; border-radius:8px; font-size:18px; font-weight:600; padding:0 24px; width:100%; }
[data-testid^="stBaseButton-primary"] { background:var(--action); border:none; }
[data-testid^="stBaseButton-primary"] p { color:var(--action-text) !important; font-weight:600; }
[data-testid^="stBaseButton-secondary"] { background:var(--surface); border:1px solid var(--border); }
[data-testid^="stBaseButton-secondary"] p { color:var(--text) !important; font-weight:600; }
.st-key-back_btn [data-testid^="stBaseButton-"] { background:transparent; border:none; justify-content:flex-start; padding:0; }
.st-key-back_btn [data-testid^="stBaseButton-"] p { color:var(--action) !important; }
button:focus-visible, input:focus-visible, textarea:focus-visible, [role="tab"]:focus-visible {
  outline:2px solid var(--action) !important; outline-offset:2px; }

/* ---------- tabs: visible selected underline + label weight ---------- */
button[data-baseweb="tab"] { height:56px; padding:0 20px; background:transparent; }
button[data-baseweb="tab"] p { font-size:18px; color:var(--muted); }
button[data-baseweb="tab"][aria-selected="true"] { background:var(--selected); border-radius:8px 8px 0 0; }
button[data-baseweb="tab"][aria-selected="true"] p { color:var(--text); font-weight:600; }
div[data-baseweb="tab-highlight"] { background:var(--action); height:3px; }
div[data-baseweb="tab-border"] { background:var(--border); }
@media (max-width: 640px) { button[data-baseweb="tab"] { padding:0 10px; } button[data-baseweb="tab"] p { font-size:14px; } }

/* ---------- expander ("All sources") ---------- */
[data-testid="stExpander"] details { background:var(--surface); border:1px solid var(--border); border-radius:12px; }
[data-testid="stExpander"] summary p { font-size:22px; font-weight:600; color:var(--text); }

/* ---------- plan pieces ---------- */
.ss-strip { display:flex; gap:12px; align-items:center; background:var(--raised); border-radius:10px; padding:16px 20px;
  color:var(--muted); font-size:16px; line-height:24px; margin-bottom:24px; }
.ss-strip svg { color:var(--action); flex:none; }
.ss-qlabel { color:var(--action); font-size:14px; font-weight:600; letter-spacing:.04em; text-transform:uppercase; margin-top:8px; }
.ss-notice { background:var(--selected); border-radius:10px; padding:16px 20px; margin:0 0 28px 0; }
.ss-notice-label { color:var(--action); font-size:14px; font-weight:600; letter-spacing:.04em; text-transform:uppercase; margin-bottom:4px; }
.ss-notice-text { color:var(--text); font-size:16px; line-height:24px; }
.ss-risks { display:grid; grid-template-columns:repeat(3, 1fr); gap:16px; margin-bottom:8px; }
@media (max-width: 768px) { .ss-risks { grid-template-columns:1fr; } }
.ss-risk { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:20px; }
.ss-risk svg { color:var(--action); }
.ss-risk-name { font-size:22px; line-height:33px; font-weight:600; color:var(--text); margin-top:8px; }
.ss-risk-why { font-size:16px; line-height:24px; color:var(--muted); margin-top:4px; }
.ss-gap { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:24px 28px; margin-bottom:16px; }
.ss-gap-head { display:flex; gap:12px; align-items:center; margin-bottom:8px; }
.ss-gap-head .ss-h3 { margin:0; }
.ss-num { display:inline-flex; align-items:center; justify-content:center; min-width:32px; height:32px; border-radius:8px;
  background:var(--selected); color:var(--action); font-weight:600; font-size:16px; }
.ss-todo-label { color:var(--action); font-size:14px; font-weight:600; letter-spacing:.04em; margin-top:12px; }
.ss-src { border-top:1px solid var(--border); margin-top:16px; padding-top:12px; font-size:14px; line-height:21px; color:var(--muted); }
.ss-src a, .ss-srcitem a, .ss-foot-src a { color:var(--action); text-decoration:none; }
.ss-srcitem { margin-bottom:16px; font-size:16px; line-height:24px; color:var(--text); }
.ss-srcitem strong { font-weight:600; }
.ss-foot-src { font-size:14px; line-height:21px; color:var(--muted); margin:8px 0; }
.ss-progress-text { font-size:18px; font-weight:600; color:var(--text); margin-bottom:8px; }
.ss-phase { font-size:22px; line-height:33px; font-weight:600; color:var(--text); margin:0 0 8px 0; }

/* generic vs. yours: 2 columns on desktop, stacked (generic first) on mobile */
.ss-cmp-grid { display:grid; grid-template-columns:1fr 1fr; gap:16px 24px; }
.ss-cmp-head { color:var(--action); font-size:14px; font-weight:600; letter-spacing:.04em; text-transform:uppercase; }
.ss-cmp { background:var(--canvas); border:1px solid var(--border); border-radius:10px; padding:16px 20px;
  font-size:18px; line-height:27px; color:var(--text); }
.ss-cmp.is-personal { background:var(--selected); border-color:var(--action); }
.ss-cmp-topic { color:var(--action); font-size:14px; font-weight:600; margin-bottom:6px; }
@media (max-width: 768px) {
  .ss-cmp-grid { display:flex; flex-direction:column; }
  .ss-cmp-grid > * { order:var(--o, 0); }
}
"""


def inject_css():
    st.markdown("<style>" + CSS + "</style>", unsafe_allow_html=True)
