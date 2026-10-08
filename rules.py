"""
Module 3: Rules engine
======================
Mini-problem: given the location's top risks and the household, what must they do,
what must they never do, and what are they missing?

    >>> result = evaluate(["hurricane", "flood", "heat"], profile)
    {
      "hazards": ["hurricane", "flood", "heat"],
      "uncovered_hazards": [],
      "uncovered_needs": [],
      "must_do":  [{"rule_id": "PWR-WHEELCHAIR", "action": "...", "when": "This week",
                    "priority": 1, "hazards": [], "source_id": "READY-DISABILITY",
                    "source": "Ready.gov · People with Disabilities"}, ...],
      "never_do": ["go to the basement", "drive through flood water", ...],
      "gaps":     [{"rule_id": "PWR-WHEELCHAIR", "message": "No backup charging for your wheelchair",
                    "fix": "...", "priority": 1, "rank": 1, "source_id": "READY-DISABILITY"}, ...],
      "sources":  [{"id": "READY-DISABILITY", "publisher": "Ready.gov", "title": "...", "url": "..."}, ...]
    }

How it works (no AI here; this is plain code on purpose, so it can be tested):
  1. Clean up the profile (accepts the flat spec shape or Module 2's nested shape).
  2. Every rule below has a condition on the hazards and the profile. Keep the ones that fire.
  3. A rule can also name a gap: something the household is missing. Unknown (None) counts
     as missing, because it's safer to point out a gap that isn't there than to hide one.
  4. Sort everything most urgent first (priority, then the hazard's rank from Module 1).

Who uses the output:
  - Module 4 (plan writer) must tag every must_do step with its [RULE-ID] and must never
    write a never_do phrase.
  - Module 5 (verifier) checks exactly that.
  - The UI shows `sources` and the gaps.

Writing never_do phrases: start them with the verb ("go to the basement", not "basement").
The verifier lets a phrase through only when a negation sits right before it, so
"Do not go to the basement" passes but "Never, ever, go to the basement" does not.

Run it from the terminal:
    python rules.py samples/rules/miami_wheelchair.json
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from typing import Callable, Iterable, Optional

# Hazards we have rules for. Module 1 can also return "landslide"; those come back in
# "uncovered_hazards" so Module 4 can label any advice about them as AI-suggested.
SUPPORTED_HAZARDS = ("hurricane", "flood", "heat", "earthquake", "wildfire")

# Checklist phases, in the order the UI shows them.
WHEN_NOW = "This week"
WHEN_WARNING = "When a warning is issued"
WHEN_DURING = "During the event"

# --------------------------------------------------------------------------
# Sources: official guidance every rule cites. The UI looks these up by id.
# TODO before the demo: open every link and check the advice still matches.
# --------------------------------------------------------------------------

SOURCES: dict[str, dict] = {
    s["id"]: s
    for s in [
        {"id": "READY-ALERTS", "publisher": "Ready.gov", "title": "Emergency Alerts",
         "url": "https://www.ready.gov/alerts"},
        {"id": "READY-KIT", "publisher": "Ready.gov", "title": "Build a Kit",
         "url": "https://www.ready.gov/kit"},
        {"id": "READY-DISABILITY", "publisher": "Ready.gov", "title": "People with Disabilities",
         "url": "https://www.ready.gov/disability"},
        {"id": "READY-POWER", "publisher": "Ready.gov", "title": "Power Outages",
         "url": "https://www.ready.gov/power-outages"},
        {"id": "READY-EVACUATION", "publisher": "Ready.gov", "title": "Evacuation",
         "url": "https://www.ready.gov/evacuation"},
        {"id": "READY-PETS", "publisher": "Ready.gov", "title": "Pets and Animals",
         "url": "https://www.ready.gov/pets"},
        {"id": "READY-HURRICANE", "publisher": "Ready.gov", "title": "Hurricanes",
         "url": "https://www.ready.gov/hurricanes"},
        {"id": "READY-FLOOD", "publisher": "Ready.gov", "title": "Floods",
         "url": "https://www.ready.gov/floods"},
        {"id": "NWS-TADD", "publisher": "National Weather Service", "title": "Turn Around Don't Drown",
         "url": "https://www.weather.gov/safety/flood-turn-around-dont-drown"},
        {"id": "READY-HEAT", "publisher": "Ready.gov", "title": "Extreme Heat",
         "url": "https://www.ready.gov/heat"},
        {"id": "READY-EARTHQUAKE", "publisher": "Ready.gov", "title": "Earthquakes",
         "url": "https://www.ready.gov/earthquakes"},
        {"id": "READY-WILDFIRE", "publisher": "Ready.gov", "title": "Wildfires",
         "url": "https://www.ready.gov/wildfires"},
    ]
}

# --------------------------------------------------------------------------
# Profile: the household facts the rules read. None always means "unknown".
# --------------------------------------------------------------------------

PROFILE_DEFAULTS: dict = {
    "housing": None,           # "apartment" | "house" | "mobile_home" | other text
    "floor": None,             # int; 1 = ground floor (U.S. numbering)
    "has_elevator": None,
    "lives_alone": None,
    "mobility": None,          # "none" | "walker_or_cane" | "wheelchair" (type unknown)
                               # | "manual_wheelchair" | "powered_wheelchair"
    "has_backup_power": None,
    "drives": None,
    "has_ac": None,
    "helper_nearby": None,     # someone nearby who can help them leave / check on them
    "power_medical": [],       # e.g. ["oxygen concentrator"]
    "fridge_meds": [],         # e.g. ["insulin"]
    "pets": [],                # e.g. ["dog"]
    "uncovered_needs": [],     # needs no rule covers; passed through to Module 4
}

# Words in Module 2's free-text medical_equipment list that mean "needs electricity".
_POWER_WORDS = ("oxygen", "concentrator", "cpap", "bipap", "ventilator", "dialysis", "nebulizer",
                "suction", "feeding pump", "infusion pump", "hospital bed", "patient lift", "powered",
                "electric")
_FRIDGE_WORDS = ("insulin", "refrigerat", "fridge")


def _norm_housing(value) -> Optional[str]:
    if not value:
        return None
    text = str(value).strip().lower().replace("-", " ").replace("_", " ")
    words = set(re.findall(r"[a-z]+", text))
    if words & {"mobile", "trailer", "manufactured", "caravan", "rv"}:
        return "mobile_home"
    if words & {"apartment", "apt", "flat", "condo", "unit"}:
        return "apartment"
    if "house" in text or "home" in words:
        return "house"
    return text.replace(" ", "_")


def _norm_mobility(value) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip().lower().replace("-", " ").replace("_", " ")
    if not text:
        return None
    if any(w in text for w in ("power", "electric", "motor", "scooter")):
        return "powered_wheelchair"
    if "manual" in text:
        return "manual_wheelchair"
    if "wheelchair" in text or "chair" in text:
        return "wheelchair"
    if any(w in text for w in ("walker", "cane", "crutch", "rollator")):
        return "walker_or_cane"
    if text in ("none", "no", "independent", "walks"):
        return "none"
    return text.replace(" ", "_")


def _as_list(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    return [str(v) for v in value if v]


def _from_nested(raw: dict) -> dict:
    """Module 2's current shape: {"home": {...}, "mobility": {...}, "medical_equipment": [...], "has_car": ...}."""
    home = raw.get("home") or {}
    mob = raw.get("mobility") or {}
    out = dict(raw)
    out["housing"] = home.get("type")
    out["floor"] = home.get("floor")
    out["has_elevator"] = home.get("has_lift")
    if mob.get("uses_wheelchair") is True:
        wtype = (mob.get("wheelchair_type") or "").lower()
        out["mobility"] = {"powered": "powered_wheelchair", "manual": "manual_wheelchair"}.get(wtype, "wheelchair")
    elif mob.get("uses_wheelchair") is False:
        out["mobility"] = "none"
    else:
        out["mobility"] = None
    if raw.get("has_car") is not None and raw.get("drives") is None:
        out["drives"] = raw["has_car"]
    equipment = _as_list(raw.get("medical_equipment"))
    out["power_medical"] = _as_list(raw.get("power_medical")) + [
        e for e in equipment if any(w in e.lower() for w in _POWER_WORDS)]
    out["fridge_meds"] = _as_list(raw.get("fridge_meds")) + [
        e for e in equipment if any(w in e.lower() for w in _FRIDGE_WORDS)]
    return out


def normalize_profile(profile) -> dict:
    """Any profile (dict, Pydantic model, flat or nested) -> the flat dict the rules read."""
    if profile is None:
        raw = {}
    elif hasattr(profile, "model_dump"):
        raw = profile.model_dump()
    else:
        raw = dict(profile)

    if isinstance(raw.get("home"), dict) or isinstance(raw.get("mobility"), dict):
        raw = _from_nested(raw)

    p = {key: raw.get(key, default) for key, default in PROFILE_DEFAULTS.items()}
    p["housing"] = _norm_housing(p["housing"])
    p["mobility"] = _norm_mobility(p["mobility"])
    try:
        p["floor"] = int(p["floor"]) if p["floor"] is not None else None
    except (TypeError, ValueError):
        p["floor"] = None
    for key in ("power_medical", "fridge_meds", "pets", "uncovered_needs"):
        p[key] = _as_list(p[key])
    return p


# Small, readable conditions the rules are built from.
def uses_wheelchair(p) -> bool:
    return p["mobility"] in ("wheelchair", "manual_wheelchair", "powered_wheelchair")


def limited_mobility(p) -> bool:
    return uses_wheelchair(p) or p["mobility"] == "walker_or_cane"


def needs_power(p) -> bool:
    return p["mobility"] == "powered_wheelchair" or bool(p["power_medical"])


def above_ground(p) -> bool:
    return p["floor"] is not None and p["floor"] >= 2


def not_yes(value) -> bool:
    """False or unknown. Used for gaps: an unknown counts as missing."""
    return value is not True


def always(p, hazards) -> bool:
    return True


# --------------------------------------------------------------------------
# Rules
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Gap:
    missing: Callable[[dict], bool]   # profile -> is this thing missing?
    message: str
    fix: str


@dataclass(frozen=True)
class Rule:
    id: str
    hazards: tuple[str, ...]          # empty = applies whatever the hazards are
    applies: Callable[[dict, list[str]], bool]
    action: str
    source_id: str
    when: str
    priority: int                     # 1 = most urgent
    never_do: tuple[str, ...] = ()
    gap: Optional[Gap] = None

    def fires(self, p: dict, hazards: list[str]) -> bool:
        if self.hazards and not set(self.hazards) & set(hazards):
            return False
        return self.applies(p, hazards)


FLOOD_WATER = ("drive through flood water", "walk through flood water", "drive through a flooded road")
ELEVATOR = ("use the elevator", "take the elevator", "use the lift", "take the lift")

RULES: list[Rule] = [
    # ---- everyone ---------------------------------------------------------
    Rule("GEN-ALERTS", (), always,
         "Sign up for your local emergency alerts, and keep a battery or hand-crank radio and a "
         "charged phone so you still get them if the power is out.",
         "READY-ALERTS", WHEN_NOW, 4),
    Rule("GEN-KIT", (), always,
         "Build an emergency kit with water, food, a flashlight, spare batteries, a first aid kit and "
         "at least several days of any medicines you take.",
         "READY-KIT", WHEN_NOW, 4),

    # ---- power-dependent ----------------------------------------------------
    Rule("PWR-WHEELCHAIR", (), lambda p, h: p["mobility"] == "powered_wheelchair",
         "Plan backup charging for your powered wheelchair: a spare battery or charger, and a place "
         "with power you can get to if the electricity goes out.",
         "READY-DISABILITY", WHEN_NOW, 1,
         gap=Gap(lambda p: not_yes(p["has_backup_power"]),
                 "No backup charging for your wheelchair",
                 "Get a backup battery, or find a nearby place with power where you can recharge.")),
    Rule("PWR-MEDICAL", (), lambda p, h: bool(p["power_medical"]),
         "Make a backup power plan for your medical equipment: extra batteries, ask your power company "
         "about its medical-needs list, and know where you can go early to get power.",
         "READY-POWER", WHEN_NOW, 1,
         gap=Gap(lambda p: not_yes(p["has_backup_power"]),
                 "Your medical equipment has no backup power",
                 "Get backup batteries, register with your power company's medical-needs program, and "
                 "pick a place with power you can go to before an outage.")),
    Rule("PWR-GENERATOR", (), lambda p, h: needs_power(p) or "hurricane" in h,
         "If you use a generator, keep it outdoors and well away from windows and doors, because its "
         "exhaust contains deadly carbon monoxide.",
         "READY-POWER", WHEN_DURING, 3,
         never_do=("run a generator indoors", "use a generator indoors", "run a generator inside",
                   "run a generator in the garage")),
    Rule("MEDS-FRIDGE", (), lambda p, h: bool(p["fridge_meds"]),
         "Plan how to keep your refrigerated medicine cold during a power outage, such as a cooler "
         "with ice packs, and ask your pharmacist how long it stays safe without a fridge.",
         "READY-POWER", WHEN_NOW, 2,
         gap=Gap(lambda p: not_yes(p["has_backup_power"]),
                 "No way to keep your medicine cold in an outage",
                 "Keep a cooler and ice packs ready, and ask your pharmacist how long your medicine "
                 "stays safe unrefrigerated.")),

    # ---- getting out --------------------------------------------------------
    Rule("EVAC-HELP", (), lambda p, h: limited_mobility(p) and above_ground(p),
         "Agree in advance who will help you leave your building if the elevator stops, and practise "
         "the route with them.",
         "READY-DISABILITY", WHEN_NOW, 2,
         gap=Gap(lambda p: not_yes(p["helper_nearby"]),
                 "No agreed way to leave without the elevator",
                 "Ask a neighbour, friend or building manager to be your evacuation helper, and agree a "
                 "backup contact.")),
    Rule("EVAC-TRANSPORT", ("hurricane", "flood", "wildfire"), lambda p, h: not_yes(p["drives"]),
         "Plan how you will leave without driving: register with your local evacuation-assistance "
         "program or arrange a ride, and leave as soon as officials advise.",
         "READY-EVACUATION", WHEN_NOW, 1,
         gap=Gap(lambda p: not_yes(p["drives"]) and not_yes(p["helper_nearby"]),
                 "No way to evacuate without a car",
                 "Register with your county's evacuation-assistance program, or arrange a ride with "
                 "someone who drives before a warning is issued.")),
    Rule("PETS-PLAN", (), lambda p, h: bool(p["pets"]),
         "Include your pets in your plan: pet food, water and medicines in your kit, and a "
         "pet-friendly shelter or hotel you can go to.",
         "READY-PETS", WHEN_NOW, 4,
         never_do=("leave your pets behind", "leave pets behind")),

    # ---- hurricane ----------------------------------------------------------
    Rule("HUR-EVAC-ZONE", ("hurricane",), always,
         "Find out whether you live in a hurricane evacuation zone, and leave right away if officials "
         "tell you to evacuate.",
         "READY-HURRICANE", WHEN_WARNING, 2,
         never_do=("ignore an evacuation order", "ignore evacuation orders") + FLOOD_WATER),
    Rule("HUR-MOBILE-HOME", ("hurricane",), lambda p, h: p["housing"] == "mobile_home",
         "Plan to leave your mobile home for a sturdy building before the hurricane arrives; mobile "
         "homes are not safe in hurricane winds.",
         "READY-HURRICANE", WHEN_WARNING, 1,
         never_do=("shelter in a mobile home", "shelter in your mobile home", "stay in your mobile home",
                   "ride out the storm"),
         gap=Gap(lambda p: True,
                 "Your home is not safe shelter in a hurricane",
                 "Choose a sturdy shelter now, and plan how you will get there before the storm.")),

    # ---- flood --------------------------------------------------------------
    Rule("FLOOD-HIGH-GROUND", ("flood",), always,
         "Know how to reach higher ground or a higher floor, and move there as soon as flooding "
         "threatens.",
         "READY-FLOOD", WHEN_WARNING, 2,
         never_do=("go to the basement", "shelter in the basement", "climb into a closed attic")),
    Rule("FLOOD-TADD", ("flood",), always,
         "Turn around, don't drown: stay out of flood water on foot or in a car. Just six inches of "
         "moving water can knock you off your feet.",
         "NWS-TADD", WHEN_DURING, 2,
         never_do=FLOOD_WATER),

    # ---- heat ---------------------------------------------------------------
    Rule("HEAT-COOL-PLACE", ("heat",), always,
         "Know where you can stay cool during a heat wave, such as an air-conditioned room or a nearby "
         "cooling center, and how you will get there.",
         "READY-HEAT", WHEN_NOW, 2,
         never_do=("rely on a fan", "leave pets in a parked car", "leave children in a parked car"),
         gap=Gap(lambda p: not_yes(p["has_ac"]),
                 "No air conditioning at home",
                 "Find your nearest cooling center or an air-conditioned place you can reach, and plan "
                 "how to get there.")),
    Rule("HEAT-CHECKIN", ("heat",), lambda p, h: p["lives_alone"] is True,
         "Set up a daily check-in with a neighbour, friend or family member during heat alerts.",
         "READY-HEAT", WHEN_NOW, 3,
         gap=Gap(lambda p: not_yes(p["helper_nearby"]),
                 "No one checks on you",
                 "Ask a neighbour or friend to check on you every day during heat alerts.")),
    Rule("HEAT-HYDRATE", ("heat",), always,
         "During a heat warning, drink plenty of fluids, stay out of the sun in the hottest part of "
         "the day, and learn the signs of heat stroke.",
         "READY-HEAT", WHEN_WARNING, 4),

    # ---- earthquake ---------------------------------------------------------
    Rule("EQ-DROP-COVER", ("earthquake",), lambda p, h: not uses_wheelchair(p),
         "When shaking starts: Drop, Cover, and Hold On until it stops.",
         "READY-EARTHQUAKE", WHEN_DURING, 3,
         never_do=("stand in a doorway", "run outside")),
    Rule("EQ-LOCK-COVER", ("earthquake",), lambda p, h: uses_wheelchair(p),
         "When shaking starts: Lock your wheels, Cover your head and neck with your arms, and Hold On "
         "until it stops.",
         "READY-EARTHQUAKE", WHEN_DURING, 2,
         never_do=("stand in a doorway", "run outside")),
    Rule("EQ-SECURE", ("earthquake",), always,
         "Secure heavy furniture, shelves and TVs to the wall so they cannot fall on you.",
         "READY-EARTHQUAKE", WHEN_NOW, 4),
    Rule("EQ-AFTER-ELEVATOR", ("earthquake",), lambda p, h: above_ground(p) or p["has_elevator"] is True,
         "After the shaking stops, leave by the stairs or with your evacuation helper; elevators may be "
         "damaged or stop working.",
         "READY-EARTHQUAKE", WHEN_DURING, 3,
         never_do=ELEVATOR),

    # ---- wildfire -----------------------------------------------------------
    Rule("WF-LEAVE-EARLY", ("wildfire",), always,
         "Leave as soon as officials advise, or earlier if you need extra time to evacuate, and know "
         "more than one way out of your area.",
         "READY-WILDFIRE", WHEN_WARNING, 2,
         never_do=("wait until you see flames",)),
    Rule("WF-SMOKE", ("wildfire",), always,
         "Prepare for wildfire smoke: keep N95 masks at home and choose a room you can keep closed "
         "up with clean air.",
         "READY-WILDFIRE", WHEN_NOW, 4),
]

# --------------------------------------------------------------------------
# Public function: this is what the rest of StormSignal calls
# --------------------------------------------------------------------------


def hazard_names(risks) -> list[str]:
    """Module 1's output (dict), its "risks" list, or plain hazard names -> ["flood", ...]."""
    if isinstance(risks, dict):
        risks = risks.get("risks", [])
    names = []
    for r in risks or []:
        name = r.get("hazard") if isinstance(r, dict) else r
        name = str(name or "").strip().lower()
        if name and name not in names:
            names.append(name)
    return names


def _unique(items: Iterable) -> list:
    seen, out = set(), []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def evaluate(risks, profile) -> dict:
    """Top risks + household profile -> must_do, never_do, gaps and sources, most urgent first."""
    hazards = hazard_names(risks)
    supported = [h for h in hazards if h in SUPPORTED_HAZARDS]
    p = normalize_profile(profile)

    def hazard_rank(rule: Rule) -> int:
        ranks = [supported.index(h) for h in rule.hazards if h in supported]
        return min(ranks) if ranks else -1  # general rules sort first within a priority

    fired = [r for r in RULES if r.fires(p, supported)]
    fired.sort(key=lambda r: (r.priority, hazard_rank(r)))  # stable: ties keep RULES order

    must_do = [{
        "rule_id": r.id,
        "action": r.action,
        "when": r.when,
        "priority": r.priority,
        "hazards": [h for h in supported if h in r.hazards],
        "source_id": r.source_id,
        "source": f'{SOURCES[r.source_id]["publisher"]} · {SOURCES[r.source_id]["title"]}',
    } for r in fired]

    gaps = [{
        "rule_id": r.id,
        "message": r.gap.message,
        "fix": r.gap.fix,
        "priority": r.priority,
        "source_id": r.source_id,
    } for r in fired if r.gap and r.gap.missing(p)]
    for rank, gap in enumerate(gaps, start=1):
        gap["rank"] = rank

    return {
        "hazards": supported,
        "uncovered_hazards": [h for h in hazards if h not in SUPPORTED_HAZARDS],
        "uncovered_needs": p["uncovered_needs"],
        "must_do": must_do,
        "never_do": _unique(phrase for r in fired for phrase in r.never_do),
        "gaps": gaps,
        "sources": [SOURCES[sid] for sid in _unique(r.source_id for r in fired)],
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python rules.py INPUT.json   (INPUT has \"risks\" and \"profile\")")
        sys.exit(2)
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)
    print(json.dumps(evaluate(data["risks"], data["profile"]), indent=2, ensure_ascii=False))
