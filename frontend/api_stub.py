"""Bridge between the Streamlit screens and the real modules.

Module 1 (stormsignal.risk)     -> real, live (needs internet, no key)
Module 2 (stormsignal.intake)   -> real if GROQ_API_KEY is set, otherwise the mock intake
Module 3 (stormsignal.rules)    -> real; also picks the follow-up questions
Module 4 (stormsignal.plan)     -> real; AI-written if GROQ_API_KEY is set, else rules-based
Module 5 (stormsignal.verifier) -> real; unsafe AI plans are rewritten once, then replaced
If anything in 3-5 fails, the mock plan (samples/ui/plan_example.json) is shown instead.

The screens only call analyze_household() and build_plan(); their return
shapes do not change.
"""
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MOCK_DIR = ROOT / "samples" / "ui"

# ---- Module 1: risk lookup -------------------------------------------------
try:
    from stormsignal.risk import get_top_risks, LocationNotFound
except Exception as e:  # missing file, missing package, ...
    get_top_risks = None

    class LocationNotFound(Exception):
        pass

    print(f"[api_stub] Module 1 not available, using mock risks: {e}")

# ---- Module 2: AI intake ---------------------------------------------------
try:
    from stormsignal.intake import analyze_household as _module2_intake
except Exception as e:  # no GROQ_API_KEY, broken import, ...
    _module2_intake = None
    print(f"[api_stub] Module 2 not available, using mock intake: {e}")

# ---- Modules 3, 4, 5: rules, plan writer, verifier (plain Python, always importable)
from stormsignal.plan import build_plan as _module4_plan
from stormsignal.rules import apply_answers, evaluate, open_questions
from stormsignal.verifier import finalize


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _load(name: str) -> dict:
    with open(MOCK_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _summary(profile: dict) -> str:
    """One-line summary shown on the screens, e.g. 'Miami, FL · Living alone · 3rd floor'."""
    home = profile.get("home") or {}
    mobility = profile.get("mobility") or {}
    parts = [profile.get("location") or ""]
    if profile.get("lives_alone") is True:
        parts.append("Living alone")
    if home.get("floor") is not None:
        parts.append(f"{_ordinal(home['floor'])} floor")
    if mobility.get("uses_wheelchair") is True:
        parts.append("Wheelchair user")
    if home.get("lift_needs_electricity") is True:
        parts.append("Lift needs electricity")
    return " · ".join(p for p in parts if p)


def _clean_followups(followups) -> list:
    """Make Module 2's follow-ups look like the mock ones."""
    cleaned = []
    for f in followups or []:
        helper = (f.get("helper") or "").strip()
        if " " not in helper:  # Module 2 sometimes returns an id like "lift_presence"
            helper = ""
        options = [o[:1].upper() + o[1:] for o in (f.get("options") or [])]
        if len(options) < 2:  # an open question ("Which floor?") can't be shown as radio buttons
            continue
        cleaned.append(
            {
                "id": f.get("id", ""),
                "question": f.get("question", ""),
                "helper": helper,
                "options": options,
            }
        )
    return cleaned

_COUNTRY_WORDS = {"united states", "united states of america", "usa", "us", "u.s.", "u.s.a.", "america"}


def _clean_location(location: str) -> str:
       """'Miami, FL, United States' -> 'Miami, FL' (Module 1 wants 'City, ST' or a ZIP)."""
       parts = [p.strip() for p in (location or "").split(",") if p.strip()]
       parts = [p for p in parts if p.lower() not in _COUNTRY_WORDS]
       return ", ".join(parts)


@lru_cache(maxsize=32)
def _risks(location: str) -> dict:
    """Module 1 call, cached so intake and plan do not hit the network twice."""
    return get_top_risks(location)


# hazard -> (card title, short explanation, icon).
# TODO: check components.py for the icon names it supports and update the icons.
HAZARDS = {
    "hurricane": ("Hurricanes", "Strong winds and storm surge can cut power and block roads.", "activity"),
    "flood": ("Flooding", "Flooding may block building access and roads.", "waves"),
    "heat": ("Extreme heat", "Heat and power cuts can make staying home unsafe.", "thermometer"),
    "earthquake": ("Earthquakes", "Shaking may stop your lift and damage buildings.", "activity"),
    "landslide": ("Landslides", "Slides can block roads and damage homes.", "activity"),
    "wildfire": ("Wildfires", "Smoke and fire can force a fast evacuation.", "activity"),
}


def _risk_cards(risks: list, county: str) -> list:
    cards = []
    for r in risks:
        name, blurb, icon = HAZARDS.get(
            r["hazard"], (r["hazard"].title(), "A hazard FEMA rates for your county.", "activity")
        )
        cards.append(
            {
                "name": name,
                "icon": icon,
                "why": f"{blurb} FEMA rates this {r['rating'].lower()} for {county}.",
            }
        )
    return cards


# ---------------------------------------------------------------------------
# Public functions (the screens call only these two)
# ---------------------------------------------------------------------------
def analyze_household(location: str, description: str) -> dict:
    """AI 1 (Intake): words -> profile + 1-2 follow-up questions.

    Returns: {"profile": {...}, "followups": [{"id","question","helper","options"}]}
    Raises ValueError with a friendly message if the place is not found.
    """
    location = _clean_location(location)

    # Module 1 checks the place first, so the user sees its error text.
    risks = []
    if get_top_risks is not None and location:
        try:
            risks = _risks(location)["risks"]
        except LocationNotFound as e:
            raise ValueError(str(e)) from e
        except Exception as e:  # network down etc.: keep going with the demo
            print(f"[api_stub] Module 1 failed, continuing: {e}")

    result = None
    if _module2_intake is not None:
        try:
            result = _module2_intake(description)
        except Exception as e:
            print(f"[api_stub] Module 2 failed, using mock intake: {e}")

    if result is None:
        result = _load("intake_example.json")

    profile = dict(result["profile"])
    profile["location"] = location or profile.get("location", "")
    profile["summary"] = _summary(profile)

    # The rules engine picks the questions whose answers would change this plan the most,
    # each with fixed options. The AI's own questions are only a fallback.
    try:
        followups = open_questions(risks, profile)
    except Exception as e:
        print(f"[api_stub] Module 3 could not pick questions, using the AI's: {e}")
        followups = _clean_followups(result.get("followups"))
    return {"profile": profile, "followups": followups}


def build_plan(profile: dict, answers: dict) -> dict:
    """Rules engine + AI 3 (Plan writer) + Verifier: build the personal plan.

    Returns the plan JSON the results screen expects (see samples/ui/plan_example.json),
    plus "plan_markdown" (the checked plan) and "verifier" {"status": "pass"|"fallback"}.
    """
    profile = apply_answers(profile, answers)  # follow-up answers fill in the unknowns
    location = (profile or {}).get("location")
    data = None
    if get_top_risks is not None and location:
        try:
            data = _risks(location)
        except Exception as e:
            print(f"[api_stub] Module 1 failed in build_plan: {e}")

    try:
        plan = _real_plan(profile, data)
    except Exception as e:  # never let a bug in 3-5 break the demo
        print(f"[api_stub] Modules 3-5 failed, using the mock plan: {e}")
        plan = _load("plan_example.json")
        if data:
            place = data["location"]
            plan["location"] = f"{place['name']}, {place['state']}"
            plan["top_risks"] = _risk_cards(data["risks"], place["county"])
    return plan


WHEN_ORDER = ["This week", "When a warning is issued", "During the event"]


def _whom(names) -> str:
    names = ["you" if n == "you" else n for n in names or []]
    return ", ".join(names)


def _real_plan(profile: dict, data: dict | None) -> dict:
    risks = data["risks"] if data else []
    rules = evaluate(risks, profile)  # Module 3

    # Module 4 sees needs, not the raw description (privacy), plus the rules output.
    plan_input = {
        "profile": {"household_needs": rules["household_needs"],
                    "uncovered_needs": rules["uncovered_needs"],
                    "summary": profile.get("summary", "")},
        "top_risks": risks,
        "module3_output": rules,
    }
    draft = _module4_plan(plan_input, use_groq=True)

    def rewrite(_plan_markdown, feedback):
        return _module4_plan(plan_input, use_groq=True, feedback=feedback)["markdown"]

    checked = finalize(draft["markdown"], rules, rewrite_fn=rewrite)  # Module 5

    by_rank = sorted(rules["gaps"], key=lambda g: g["rank"])[:3]
    gaps = [{
        "rank": n,
        "title": g["message"],
        "why": f"For {_whom(g['for_whom'])}." if g["for_whom"] else "This affects your whole household.",
        "fix": g["fix"],
        "source_ids": [g["source_id"]],
    } for n, g in enumerate(by_rank, start=1)]

    steps = sorted(rules["must_do"], key=lambda m: (WHEN_ORDER.index(m["when"]) if m["when"] in WHEN_ORDER
                                                     else len(WHEN_ORDER), m["priority"]))
    checklist = [{
        "id": m["rule_id"],
        "when": m["when"],
        "step": m["action"] + (f" (for {_whom(m['for_whom'])})" if m["for_whom"] and m["for_whom"] != ["you"] else ""),
        "source_ids": [m["source_id"]],
    } for m in steps]

    top = gaps[0]["title"].lower() if gaps else "the steps below"
    summary = (f"{len(checklist)} steps for your household, based on {len(rules['sources'])} official "
               f"sources. Start with: {top}.")

    plan = {
        "is_demo": False,
        "location": profile.get("location", ""),
        "top_risks": [],
        "summary": summary,
        "gaps": gaps,
        "checklist": checklist,
        "comparison": [],
        "sources": rules["sources"],
        "plan_markdown": checked["final_plan"],
        "verifier": {"status": "pass" if checked["passed"] else "fallback",
                     "note": "" if checked["passed"] else
                     f"missing: {checked['missing_rules']}, forbidden: {checked['forbidden_found']}"},
        "generation_method": draft.get("generation_method", "rules"),
    }
    if data:
        place = data["location"]
        plan["location"] = f"{place['name']}, {place['state']}"
        plan["top_risks"] = _risk_cards(data["risks"], place["county"])
    return plan
