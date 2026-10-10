"""Small reusable pieces: icons, safety banner, step indicators, headings, source lines.

Everything here only prints HTML/CSS classes defined in styles.py.
User/AI text is always passed through esc() so it can never inject HTML.
"""
import html as _html

import streamlit as st

STEPS = [("intake", "About you"), ("followups", "Quick questions"), ("results", "Your plan")]

BANNER_TEXT = (
    "StormSignal is not an emergency service. Check official alerts and follow local "
    "authorities. In immediate danger, contact local emergency services (911 in the U.S.)."
)
FOOTER_TEXT = "A starting point for planning, not a substitute for official guidance."
DEMO_PLACE = "New York City, U.S."   # shown in the sidebar demo card; change or remove after the demo


def esc(value) -> str:
    return _html.escape(str(value), quote=True)


def md(markup: str):
    """Render an HTML snippet. Lines are stripped and joined so Markdown never treats them as code."""
    st.markdown("".join(line.strip() for line in markup.strip().splitlines()), unsafe_allow_html=True)


# ------------------------------------------------------------------ icons
_SVG = {
    "shield": '<path d="M12 3l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6z"/><path d="M12 8v4M12 16h.01"/>',
    "lock": '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 018 0v3"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-6 8-6s8 2 8 6"/>',
    "check": '<path d="M5 12l5 5 9-9"/>',
    "radar": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5"/><path d="M12 12l6-6"/>',
    "waves": '<path d="M2 8c2.5 0 2.5-2 5-2s2.5 2 5 2 2.5-2 5-2 2.5 2 5 2M2 14c2.5 0 2.5-2 5-2s2.5 2 5 2 2.5-2 5-2 2.5 2 5 2M2 20c2.5 0 2.5-2 5-2s2.5 2 5 2 2.5-2 5-2 2.5 2 5 2"/>',
    "activity": '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
    "thermometer": '<path d="M14 14.8V5a2 2 0 10-4 0v9.8a4 4 0 104 0z"/>',
}


def icon(name: str, size: int = 20) -> str:
    path = _SVG.get(name, _SVG["shield"])
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{path}</svg>'
    )


# ------------------------------------------------------------------ steps
def _state(index: int, current_index: int) -> str:
    return "done" if index < current_index else ("current" if index == current_index else "todo")


def _step_html(index: int, label: str, state: str, css_class: str) -> str:
    badge = icon("check", 14) if state == "done" else str(index + 1)
    return (
        f'<div class="{css_class} is-{state}"><span class="ss-badge">{badge}</span>'
        f'<span>{esc(label)}</span></div>'
    )


def _current_index(current: str) -> int:
    return [key for key, _ in STEPS].index(current)


def render_sidebar(current: str):
    """Desktop sidebar: brand, 3 steps, demo card, privacy note."""
    idx = _current_index(current)
    steps = "".join(_step_html(i, label, _state(i, idx), "ss-side-step") for i, (_, label) in enumerate(STEPS))
    with st.sidebar:
        md(
            f'<div class="ss-brand">{icon("radar", 28)}<span>StormSignal</span></div>'
            f'<div class="ss-tagline">Personal preparedness, one step at a time.</div>'
            f'{steps}'
            f'<div class="ss-demo-card"><div class="ss-demo-label">HACKATHON DEMO</div>'
            f'<div class="ss-demo-place">{esc(DEMO_PLACE)}</div>'
            f'<div class="ss-demo-note">Illustrative plans. No live alerts.</div></div>'
            f'<div class="ss-side-privacy">{icon("lock", 20)}<span>No account needed. Your session, your details.</span></div>'
        )


def safety_banner():
    md(f'<div class="ss-banner" role="note">{icon("shield", 24)}<div>{esc(BANNER_TEXT)}</div></div>')


def mobile_header(current: str):
    idx = _current_index(current)
    chips = "".join(_step_html(i, label, _state(i, idx), "ss-chip") for i, (_, label) in enumerate(STEPS))
    md(
        f'<div class="ss-mobile-only"><div class="ss-brand">{icon("radar", 28)}<span>StormSignal</span></div>'
        f'<div class="ss-chips">{chips}</div></div>'
    )


def page_top(current: str, eyebrow_text: str, title: str, lead_text: str = ""):
    """Banner + mobile header + desktop top line + eyebrow + page title (+ lead). Every screen starts with this."""
    safety_banner()
    mobile_header(current)
    md('<div class="ss-topline"><span>PERSONAL PREPAREDNESS</span><span class="ss-act">Illustrative demo · No live alerts</span></div>')
    md(f'<div class="ss-eyebrow">{esc(eyebrow_text)}</div><h1 class="ss-h1">{esc(title)}</h1>')
    if lead_text:
        md(f'<p class="ss-lead">{esc(lead_text)}</p>')


# ------------------------------------------------------------------ text helpers
def h2(text):      md(f'<h2 class="ss-h2">{esc(text)}</h2>')
def h3(text):      md(f'<h3 class="ss-h3">{esc(text)}</h3>')
def body(text):    md(f'<p class="ss-body">{esc(text)}</p>')
def support(text): md(f'<p class="ss-support">{esc(text)}</p>')
def caption(text): md(f'<div class="ss-caption">{esc(text)}</div>')


def privacy_line(text="Your details stay in this browser session only"):
    md(f'<div class="ss-privacy">{icon("lock", 22)}<span>{esc(text)}</span></div>')


def footer():
    md(f'<div class="ss-rule"></div><div class="ss-footnote">{esc(FOOTER_TEXT)}</div>')


def profile_strip(text):
    md(f'<div class="ss-strip">{icon("user", 22)}<span>{esc(text)}</span></div>')


# ------------------------------------------------------------------ sources
def _short(url: str) -> str:
    return url.replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")


def _is_web(url: str) -> bool:
    return str(url).startswith(("https://", "http://"))


def source_link(src: dict, full: bool = False) -> str:
    label = src["url"] if full else _short(src["url"])
    if not _is_web(src["url"]):
        return esc(label)
    return f'<a href="{esc(src["url"])}" target="_blank" rel="noopener noreferrer">{esc(label)}</a>'


def source_block(source_ids, by_id) -> str:
    """'Source: Publisher · Title' + short links, as a small footer inside a card."""
    srcs = [by_id[i] for i in source_ids if i in by_id]
    if not srcs:
        return ""
    names = " + ".join(f'{s["publisher"]} · {s["title"]}' for s in srcs)
    links = " · ".join(source_link(s) for s in srcs)
    return f'<div class="ss-src">Source: {esc(names)}<br>{links}</div>'


def source_footer(source_ids, by_id):
    """One 'Sources: ...' line under a tab."""
    srcs = []
    for i in source_ids:
        if i in by_id and by_id[i] not in srcs:
            srcs.append(by_id[i])
    if srcs:
        md(f'<div class="ss-foot-src">Sources: {" · ".join(source_link(s) for s in srcs)}</div>')
