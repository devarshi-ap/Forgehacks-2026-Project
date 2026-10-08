"""Tests for Module 3 (rules engine).

Every profile here is hand-written, so these run alone: no AI, no network, no other module.
Run with `python -m pytest tests/test_rules.py`.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import rules  # noqa: E402

MIAMI = ["hurricane", "flood", "heat"]


def profile(**fields) -> dict:
    """A flat profile where everything not given is unknown."""
    return {**rules.PROFILE_DEFAULTS, **fields}


def ids(result, key="must_do") -> list[str]:
    return [item["rule_id"] for item in result[key]]


def gap_messages(result) -> list[str]:
    return [g["message"] for g in result["gaps"]]


# ---- the rule table itself ---------------------------------------------------

def test_rule_count_matches_the_plan():
    assert 15 <= len(rules.RULES) <= 25


def test_rule_ids_are_unique_and_tag_safe():
    all_ids = [r.id for r in rules.RULES]
    assert len(all_ids) == len(set(all_ids))
    for rid in all_ids:
        assert re.fullmatch(r"[A-Z]+(-[A-Z]+)+", rid), rid  # e.g. PWR-WHEELCHAIR, fits in [RULE-ID]


def test_every_rule_cites_a_known_source():
    for r in rules.RULES:
        assert r.source_id in rules.SOURCES, r.id


def test_every_source_is_used_and_complete():
    used = {r.source_id for r in rules.RULES}
    assert used == set(rules.SOURCES)
    for s in rules.SOURCES.values():
        assert s["url"].startswith("https://") and s["publisher"] and s["title"]


def test_rules_only_name_supported_hazards():
    for r in rules.RULES:
        assert set(r.hazards) <= set(rules.SUPPORTED_HAZARDS), r.id


def test_every_supported_hazard_has_rules():
    covered = {h for r in rules.RULES for h in r.hazards}
    assert covered == set(rules.SUPPORTED_HAZARDS)


def test_no_rule_text_contains_a_forbidden_phrase():
    """If an action said "drive through flood water", Module 4 would copy it and the verifier would reject the plan."""
    phrases = {p for r in rules.RULES for p in r.never_do}
    for r in rules.RULES:
        texts = [r.action] + ([r.gap.message, r.gap.fix] if r.gap else [])
        for text in texts:
            for phrase in phrases:
                assert phrase not in text.lower(), f"{r.id} contains forbidden phrase {phrase!r}"


def test_checklist_phases_are_the_ones_the_ui_shows():
    assert {r.when for r in rules.RULES} <= {rules.WHEN_NOW, rules.WHEN_WARNING, rules.WHEN_DURING}


# ---- the spec's example -------------------------------------------------------

def test_spec_example_powered_wheelchair_without_backup_power():
    """hurricane + powered wheelchair + no backup power -> must-do PWR-WHEELCHAIR + gap."""
    result = rules.evaluate(["hurricane"], profile(mobility="powered_wheelchair", has_backup_power=False))
    assert "PWR-WHEELCHAIR" in ids(result)
    assert "No backup charging for your wheelchair" in gap_messages(result)


def test_readme_persona_gets_the_three_readme_gaps():
    """23, lives alone, 3rd floor, powered wheelchair, doesn't drive, Miami."""
    data = json.loads((ROOT / "samples" / "rules" / "miami_wheelchair.json").read_text(encoding="utf-8"))
    result = rules.evaluate(data["risks"], data["profile"])
    messages = gap_messages(result)
    for expected in ("No way to evacuate without a car", "No backup charging for your wheelchair",
                     "No one checks on you"):
        assert expected in messages
    assert result["gaps"][0]["priority"] == 1


# ---- personas from docs/test_personas.md --------------------------------------

def test_mobile_home_family_must_leave_before_a_hurricane():
    result = rules.evaluate(MIAMI, profile(housing="mobile home", lives_alone=False, drives=True))
    assert "HUR-MOBILE-HOME" in ids(result)
    assert "shelter in a mobile home" in result["never_do"]
    assert result["gaps"][0]["rule_id"] == "HUR-MOBILE-HOME"


def test_oxygen_user_needs_backup_power_and_no_indoor_generator():
    result = rules.evaluate(["heat"], profile(power_medical=["oxygen concentrator"]))
    assert "PWR-MEDICAL" in ids(result)
    assert "PWR-GENERATOR" in ids(result)
    assert "run a generator indoors" in result["never_do"]
    assert "Your medical equipment has no backup power" in gap_messages(result)


def test_no_car_household_needs_evacuation_transport():
    result = rules.evaluate(["hurricane"], profile(drives=False, helper_nearby=False))
    assert "EVAC-TRANSPORT" in ids(result)
    assert "No way to evacuate without a car" in gap_messages(result)


# ---- how known / unknown facts change the result ------------------------------

def test_unknown_counts_as_missing_for_gaps():
    result = rules.evaluate(["heat"], profile(has_ac=None))
    assert "No air conditioning at home" in gap_messages(result)


def test_known_yes_removes_the_gap_but_keeps_the_step():
    result = rules.evaluate(["heat"], profile(has_ac=True))
    assert "HEAT-COOL-PLACE" in ids(result)
    assert "No air conditioning at home" not in gap_messages(result)


def test_driver_gets_no_transport_rule():
    result = rules.evaluate(["hurricane"], profile(drives=True))
    assert "EVAC-TRANSPORT" not in ids(result)


def test_having_a_helper_closes_the_transport_gap():
    result = rules.evaluate(["hurricane"], profile(drives=False, helper_nearby=True))
    assert "EVAC-TRANSPORT" in ids(result)
    assert "No way to evacuate without a car" not in gap_messages(result)


def test_elevator_help_only_above_the_ground_floor():
    upstairs = rules.evaluate(["flood"], profile(mobility="manual_wheelchair", floor=3))
    ground = rules.evaluate(["flood"], profile(mobility="manual_wheelchair", floor=1))
    assert "EVAC-HELP" in ids(upstairs)
    assert "EVAC-HELP" not in ids(ground)


def test_checkin_only_for_people_living_alone():
    assert "HEAT-CHECKIN" in ids(rules.evaluate(["heat"], profile(lives_alone=True)))
    assert "HEAT-CHECKIN" not in ids(rules.evaluate(["heat"], profile(lives_alone=False)))


def test_wheelchair_users_get_lock_cover_hold_on():
    chair = rules.evaluate(["earthquake"], profile(mobility="powered_wheelchair"))
    walker = rules.evaluate(["earthquake"], profile(mobility="none"))
    assert "EQ-LOCK-COVER" in ids(chair) and "EQ-DROP-COVER" not in ids(chair)
    assert "EQ-DROP-COVER" in ids(walker) and "EQ-LOCK-COVER" not in ids(walker)


def test_earthquake_upstairs_forbids_the_elevator():
    result = rules.evaluate(["earthquake"], profile(floor=5, has_elevator=True))
    assert "use the elevator" in result["never_do"]


def test_pets_are_included():
    result = rules.evaluate(["flood"], profile(pets=["dog"]))
    assert "PETS-PLAN" in ids(result)


# ---- hazards ------------------------------------------------------------------

def test_flood_forbids_the_basement_and_flood_water():
    result = rules.evaluate(["flood"], profile())
    assert {"go to the basement", "drive through flood water"} <= set(result["never_do"])


def test_rules_for_absent_hazards_do_not_fire():
    result = rules.evaluate(["earthquake", "wildfire"], profile(lives_alone=True))
    fired_hazards = {h for m in result["must_do"] for h in m["hazards"]}
    assert fired_hazards <= {"earthquake", "wildfire"}
    assert not any(rid.startswith(("HEAT-", "FLOOD-", "HUR-")) for rid in ids(result))


def test_unsupported_hazards_are_reported_not_dropped_silently():
    result = rules.evaluate(["earthquake", "landslide"], profile())
    assert result["hazards"] == ["earthquake"]
    assert result["uncovered_hazards"] == ["landslide"]


def test_accepts_module1_output_list_of_dicts_or_names():
    as_dict = {"location": {}, "risks": [{"hazard": "flood", "score": 90.0, "rating": "Very High"}]}
    as_list = as_dict["risks"]
    as_names = ["Flood"]
    results = [rules.evaluate(r, profile()) for r in (as_dict, as_list, as_names)]
    assert results[0] == results[1] == results[2]


# ---- ordering and output shape --------------------------------------------------

def test_must_do_is_sorted_most_urgent_first():
    result = rules.evaluate(MIAMI, profile(mobility="powered_wheelchair", floor=3, lives_alone=True, drives=False))
    priorities = [m["priority"] for m in result["must_do"]]
    assert priorities == sorted(priorities)


def test_ties_follow_module1_hazard_rank():
    # FLOOD-HIGH-GROUND and HEAT-COOL-PLACE are both priority 2; order follows the risk ranking.
    heat_first = ids(rules.evaluate(["heat", "flood"], profile()))
    flood_first = ids(rules.evaluate(["flood", "heat"], profile()))
    assert heat_first.index("HEAT-COOL-PLACE") < heat_first.index("FLOOD-HIGH-GROUND")
    assert flood_first.index("FLOOD-HIGH-GROUND") < flood_first.index("HEAT-COOL-PLACE")


def test_gaps_are_ranked_from_one():
    result = rules.evaluate(MIAMI, profile(mobility="powered_wheelchair", drives=False, lives_alone=True))
    assert [g["rank"] for g in result["gaps"]] == list(range(1, len(result["gaps"]) + 1))


def test_never_do_has_no_duplicates():
    result = rules.evaluate(MIAMI, profile())  # hurricane and flood share the flood-water phrases
    assert len(result["never_do"]) == len(set(result["never_do"]))


def test_only_cited_sources_are_returned():
    result = rules.evaluate(["flood"], profile())
    assert {s["id"] for s in result["sources"]} == {m["source_id"] for m in result["must_do"]}


def test_output_is_json_serialisable():
    json.dumps(rules.evaluate(MIAMI, profile(power_medical=["cpap"], pets=["cat"])))


def test_empty_profile_and_no_risks_do_not_crash():
    result = rules.evaluate([], None)
    assert ids(result) == ["GEN-ALERTS", "GEN-KIT"]
    assert result["gaps"] == []


# ---- profile shapes ------------------------------------------------------------

# Module 2's current output (module2_output.json on the module-2-ai-intake branch).
MODULE2_NESTED = {
    "age": 23, "lives_alone": True,
    "home": {"type": "apartment", "floor": 3, "has_lift": None, "lift_needs_electricity": None},
    "mobility": {"uses_wheelchair": True, "wheelchair_type": "powered"},
    "medical_equipment": ["oxygen concentrator", "insulin"],
    "has_car": False, "helper_nearby": None,
}


def test_module2_nested_profile_is_understood():
    p = rules.normalize_profile(MODULE2_NESTED)
    assert p["housing"] == "apartment" and p["floor"] == 3
    assert p["mobility"] == "powered_wheelchair"
    assert p["drives"] is False
    assert p["power_medical"] == ["oxygen concentrator"]
    assert p["fridge_meds"] == ["insulin"]


def test_module2_nested_profile_fires_the_right_rules():
    result = rules.evaluate(MIAMI, MODULE2_NESTED)
    for rid in ("PWR-WHEELCHAIR", "PWR-MEDICAL", "MEDS-FRIDGE", "EVAC-TRANSPORT", "EVAC-HELP"):
        assert rid in ids(result)


def test_wheelchair_of_unknown_type_is_not_assumed_powered():
    nested = {**MODULE2_NESTED, "mobility": {"uses_wheelchair": True, "wheelchair_type": None}}
    p = rules.normalize_profile(nested)
    assert p["mobility"] == "wheelchair"
    assert "PWR-WHEELCHAIR" not in ids(rules.evaluate(MIAMI, nested))


@pytest.mark.parametrize("text,expected", [
    ("Powered wheelchair", "powered_wheelchair"), ("electric scooter", "powered_wheelchair"),
    ("manual_wheelchair", "manual_wheelchair"), ("wheelchair", "wheelchair"),
    ("cane", "walker_or_cane"), ("none", "none"), (None, None), ("", None),
])
def test_mobility_wording(text, expected):
    assert rules.normalize_profile({"mobility": text})["mobility"] == expected


@pytest.mark.parametrize("text,expected", [
    ("mobile home", "mobile_home"), ("Trailer", "mobile_home"), ("apartment", "apartment"),
    ("3rd floor apt", "apartment"), ("house", "house"), ("house with service road", "house"), (None, None),
])
def test_housing_wording(text, expected):
    assert rules.normalize_profile({"housing": text})["housing"] == expected


def test_bad_floor_value_becomes_unknown():
    assert rules.normalize_profile({"floor": "third"})["floor"] is None
    assert rules.normalize_profile({"floor": "3"})["floor"] == 3


def test_uncovered_needs_pass_through_for_module4():
    result = rules.evaluate(["heat"], profile(uncovered_needs=["service dog", "deaf"]))
    assert result["uncovered_needs"] == ["service dog", "deaf"]


# ---- contract with Module 5 (verifier) -------------------------------------------

def test_output_works_with_the_verifier():
    """Runs only once verifier.py is merged in (branch module5-verifier)."""
    verifier = pytest.importorskip("verifier")
    result = rules.evaluate(MIAMI, profile(mobility="powered_wheelchair", floor=3, drives=False))
    good = "\n".join(f"- {m['action']} [{m['rule_id']}]" for m in result["must_do"])
    assert verifier.verify_plan(good, result)["passed"] is True
    bad = good + "\n- When the warning comes, go to the basement."
    assert verifier.verify_plan(bad, result)["forbidden_found"] == ["go to the basement"]
    checklist = verifier.rules_to_checklist(result)
    assert all(f"[{m['rule_id']}]" in checklist for m in result["must_do"])
