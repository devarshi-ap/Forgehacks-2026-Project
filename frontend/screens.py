"""The three StormSignal screens (Streamlit): intake, follow-ups, results.

Layout and wording follow the Figma designs. All data comes from api_stub.py,
so the screens do not care whether the data is mock or real.
"""
import streamlit as st

from frontend import api_stub
from frontend import components as C
from frontend.components import esc, icon, md

EXAMPLE = {
    "city": "New York City",
    "country": "United States",
    "description": (
        "I live alone on the 3rd floor of an apartment building in New York City. I use a "
        "wheelchair. There is a lift, but it needs electricity. I want to know how to prepare "
        "if I need to leave or the power goes out."
    ),
}


def go_to(step: str):
    st.session_state["step"] = step
    st.rerun()


def _fill_example():
    for key, value in EXAMPLE.items():
        st.session_state[key] = value


# ================================================================ Screen 1
def screen_intake():
    C.page_top("intake", "Step 1 of 3 · About you", "StormSignal",
               "Turn official disaster guidance into a plan that fits your home and your everyday needs.")

    # Widget values are cleared when we leave this screen, so restore them.
    for key in ("city", "country", "description"):
        st.session_state.setdefault(key, st.session_state.get("saved_" + key, ""))

    with st.container(key="card_intake"):
        C.h2("Let’s start with you")
        C.support("You know your situation best. Share only what you’re comfortable sharing.")
        col_city, col_country = st.columns(2)
        col_city.text_input("City", key="city", placeholder="e.g. New York City")
        col_country.text_input("Country", key="country", placeholder="e.g. United States")
        md('<div class="ss-label">Describe your home and your situation in your own words</div>'
           '<div class="ss-help">For example: how you get around, who lives with you, and anything you depend on.</div>')
        st.text_area("Describe your home and your situation in your own words", key="description",
                     height=180, label_visibility="collapsed")
        if st.session_state["description"] == EXAMPLE["description"]:
            C.caption("Example filled in for this demo. No name or exact address needed.")
        else:
            C.caption("No name or exact address needed.")
        left, _, right = st.columns([2, 5, 2])
        left.button("Use an example", on_click=_fill_example)
        go = right.button("Continue", type="primary")

    if go:
        city = st.session_state["city"].strip()
        country = st.session_state["country"].strip()
        description = st.session_state["description"].strip()
        if not (city and country and description):
            st.error("Please fill in your city, your country and a short description.")
        else:
            st.session_state.update(saved_city=city, saved_country=country, saved_description=description)
        with st.spinner("Reading your description..."):
                try:
                    st.session_state["intake"] = api_stub.analyze_household(
                        f"{city}, {country}", description
                    )
                except ValueError as err:
                    st.session_state.pop("intake", None)
                    st.error(str(err))
                    st.stop()
        go_to("followups")

    C.privacy_line()
    C.h3("What happens next?")
    C.support("Answer two quick questions. Then review a cited, illustrative preparedness plan.")
    C.footer()


# ================================================================ Screen 2
def screen_followups():
    intake = st.session_state["intake"]
    questions = intake["followups"]
    C.page_top("followups", "Step 2 of 3 · Quick questions", "A little more detail",
               "Two quick questions help us make the example plan more useful. "
               "You can choose “not sure” or skip personal details.")
    C.profile_strip(intake["profile"].get("summary", intake["profile"].get("location", "")))

    with st.container(key="card_questions"):
        for n, q in enumerate(questions, start=1):
            md(f'<div class="ss-qlabel">Question {n} of {len(questions)}</div>'
               f'<h3 class="ss-h3">{esc(q["question"])}</h3>'
               f'<div class="ss-help">{esc(q.get("helper", ""))}</div>')
            st.radio(q["question"], q["options"], index=None, key=f"fu_{q['id']}",
                     label_visibility="collapsed")

    back, _, build = st.columns([2, 5, 2])
    with back:
        with st.container(key="back_btn"):
            if st.button("← Back"):
                go_to("intake")
    if build.button("Build my plan", type="primary"):
        # Unanswered questions are allowed ("skip personal details"); the backend gets "Not answered".
        answers = {q["id"]: st.session_state.get(f"fu_{q['id']}") or "Not answered" for q in questions}
        st.session_state["answers"] = answers
        with st.spinner("Building your plan..."):
            st.session_state["plan"] = api_stub.build_plan(intake["profile"], answers)
        go_to("results")

    C.caption("Your answers are used only for this session’s illustrative plan.")
    C.footer()


# ================================================================ Screen 3
def _tab_gaps(plan, by_id):
    C.h2("Start with these three gaps")
    if plan.get("is_demo"):
        C.support("Suggested order for this demo — not an official risk ranking.")
    cards = ""
    for gap in sorted(plan["gaps"], key=lambda g: g["rank"]):
        cards += (
            f'<div class="ss-gap"><div class="ss-gap-head"><span class="ss-num">{esc(gap["rank"])}</span>'
            f'<h3 class="ss-h3">{esc(gap["title"])}</h3></div>'
            f'<div class="ss-body">{esc(gap["why"])}</div>'
            f'<div class="ss-todo-label">WHAT TO DO</div>'
            f'<div class="ss-body">{esc(gap["fix"])}</div>'
            f'{C.source_block(gap["source_ids"], by_id)}</div>'
        )
    md(cards)


def _tab_checklist(plan, by_id):
    items = plan["checklist"]
    total = len(items)
    done = sum(1 for i in items if st.session_state.get(f"chk_{i['id']}", False))
    pct = round(100 * done / total) if total else 0
    C.h2("Small steps, at the right time")
    with st.container(key="card_progress"):
        md(f'<div class="ss-progress-text">{done} of {total} tasks complete · {pct}%</div>')
        st.progress(done / total if total else 0)
        C.caption("Demo checklist. Your ticks stay in this session.")
    phases = {}
    for item in items:
        phases.setdefault(item["when"], []).append(item)
    for n, (when, group) in enumerate(phases.items()):
        with st.container(key=f"card_phase_{n}"):
            md(f'<div class="ss-phase">{esc(when)}</div>')
            for item in group:
                st.checkbox(item["step"], key=f"chk_{item['id']}")
    all_ids = [sid for item in items for sid in item["source_ids"]]
    C.source_footer(all_ids, by_id)
    md('<div class="ss-warn-text">Illustrative planning only. Official instructions take priority.</div>')


def _tab_compare(plan, by_id):
    C.h2("Same guidance. Your circumstances.")
    C.support("Your details make the next steps more specific. This example has not been verified for your building.")
    rows = plan["comparison"]
    html = '<div class="ss-cmp-grid">'
    html += '<div class="ss-cmp-head" style="--o:0">Generic advice</div>'
    html += '<div class="ss-cmp-head" style="--o:50">Personalised for you</div>'
    for n, row in enumerate(rows, start=1):
        html += (f'<div class="ss-cmp" style="--o:{n}"><div class="ss-cmp-topic">{esc(row["topic"])}</div>'
                 f'{esc(row["generic"])}</div>')
        html += (f'<div class="ss-cmp is-personal" style="--o:{50 + n}"><div class="ss-cmp-topic">{esc(row["topic"])}</div>'
                 f'{esc(row["personalised"])}</div>')
    html += '</div>'
    md(html)
    all_ids = [sid for row in rows for sid in row["source_ids"]]
    C.source_footer(all_ids, by_id)


def screen_results():
    plan = st.session_state["plan"]
    by_id = {s["id"]: s for s in plan["sources"]}

    C.page_top("results", "Step 3 of 3 · Your plan", "A plan for your situation", plan["location"])

    if plan.get("is_demo"):
        md('<div class="ss-notice"><div class="ss-notice-label">Illustrative demo output</div>'
           '<div class="ss-notice-text">These are planning topics, not live alerts or a verified risk assessment. '
           'Confirm the plan with local authorities and people who support you.</div></div>')
    if plan["verifier"]["status"] != "pass":
        md('<div class="ss-notice"><div class="ss-notice-label">Safety check</div>'
           '<div class="ss-notice-text">We could not confirm the AI-written plan, so you are seeing the '
           'rules-based version instead.</div></div>')

    C.h3("Risks to plan for")
    risks = "".join(
        f'<div class="ss-risk">{icon(r.get("icon", "shield"), 24)}'
        f'<div class="ss-risk-name">{esc(r["name"])}</div><div class="ss-risk-why">{esc(r["why"])}</div></div>'
        for r in plan["top_risks"]
    )
    md(f'<div class="ss-risks">{risks}</div>')

    C.h3("What matters most for you")
    C.body(plan["summary"])

    tab_gaps, tab_check, tab_compare = st.tabs(["Biggest gaps", "Checklist", "Generic vs. yours"])
    with tab_gaps:
        _tab_gaps(plan, by_id)
    with tab_check:
        _tab_checklist(plan, by_id)
    with tab_compare:
        _tab_compare(plan, by_id)

    with st.expander("All sources", expanded=True):
        if plan.get("is_demo"):
            C.support("Official general guidance used for this example. Sources do not verify this personalised plan. "
                      "Open official sites for current alerts.")
        md("".join(
            f'<div class="ss-srcitem"><strong>{esc(s["publisher"])} · {esc(s["title"])}</strong><br>'
            f'{C.source_link(s, full=True)}</div>' for s in plan["sources"]
        ))

    if st.button("Start over"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    C.footer()
