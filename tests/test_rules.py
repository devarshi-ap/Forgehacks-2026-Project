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

from stormsignal.rules import rules  # noqa: E402

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
    assert 30 <= len(rules.RULES) <= 45


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
    assert ids(result) == ["GEN-ALERTS", "GEN-KIT", "MEDS-LIST"]
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
    from stormsignal.verifier import verifier
    result = rules.evaluate(MIAMI, profile(mobility="powered_wheelchair", floor=3, drives=False))
    good = "\n".join(f"- {m['action']} [{m['rule_id']}]" for m in result["must_do"])
    assert verifier.verify_plan(good, result)["passed"] is True
    bad = good + "\n- When the warning comes, go to the basement."
    assert verifier.verify_plan(bad, result)["forbidden_found"] == ["go to the basement"]
    checklist = verifier.rules_to_checklist(result)
    assert all(f"[{m['rule_id']}]" in checklist for m in result["must_do"])


# ---- wider coverage: need tags and other people at home -------------------------

ALL_HAZARDS = list(rules.SUPPORTED_HAZARDS)


def for_whom(result, rule_id) -> list[str]:
    return next(m["for_whom"] for m in result["must_do"] if m["rule_id"] == rule_id)


def test_every_need_tag_has_a_rule():
    tagged = {tag for r in rules.RULES for tag in r.needs}
    assert tagged == set(rules.NEED_TAGS)


@pytest.mark.parametrize("tag", rules.NEED_TAGS)
def test_each_tag_changes_the_plan(tag):
    baseline = set(ids(rules.evaluate(ALL_HAZARDS, profile())))
    with_tag = set(ids(rules.evaluate(ALL_HAZARDS, profile(others=[{"who": "mom", "needs": [tag]}]))))
    assert with_tag - baseline, f"{tag} fires no extra rule"


def test_need_tags_match_module2_schema():
    """Module 2 (intake) and Module 3 (rules) must use the same tag list."""
    from stormsignal.intake import schemas
    assert tuple(schemas.NEED_TAGS) == rules.NEED_TAGS
    assert {g: tuple(v) for g, v in schemas.CMIST.items()} == rules.CMIST


def test_household_with_mom_dad_and_son():
    """Mom has dementia and takes insulin, dad uses crutches, son is 6."""
    household = {**MODULE2_NESTED, "mobility": {"uses_wheelchair": False, "wheelchair_type": None},
                 "medical_equipment": [], "lives_alone": False,
                 "others": [{"who": "mom", "age": 78, "needs": ["memory_loss_or_dementia", "refrigerated_medication"]},
                            {"who": "dad", "age": 80, "needs": ["walker_cane_or_crutches"]},
                            {"who": "son", "age": 6, "needs": []}]}
    result = rules.evaluate(MIAMI, household)
    assert for_whom(result, "CARE-SUPERVISION") == ["mom"]
    assert for_whom(result, "MEDS-FRIDGE") == ["mom"]
    assert for_whom(result, "MOB-AID") == ["dad"]
    assert for_whom(result, "HEAT-HIGH-RISK") == ["mom", "dad"]  # both over 65
    assert "son" not in for_whom(result, "HEAT-HIGH-RISK")      # 6 is not a young child
    assert "EVAC-HELP" in ids(result)                            # dad's crutches + 3rd floor


def test_deaf_pregnant_in_a_basement_with_a_dog():
    result = rules.evaluate(["flood"], profile(needs=["deaf_or_hard_of_hearing", "pregnant"],
                                               housing="basement apartment", pets=["dog"]))
    for rid in ("COMM-HEARING", "FAMILY-BABY", "FLOOD-BASEMENT", "PETS-PLAN"):
        assert rid in ids(result)
    basement_gap = next(g for g in result["gaps"] if g["rule_id"] == "FLOOD-BASEMENT")
    assert basement_gap["priority"] == 1
    assert "stay in the basement" in result["never_do"]
    assert for_whom(result, "COMM-HEARING") == ["you"]


def test_basement_detection():
    assert rules.normalize_profile({"housing": "basement apartment"})["below_ground"] is True
    assert rules.normalize_profile({"floor": -1})["below_ground"] is True
    assert rules.normalize_profile({"floor": 0})["below_ground"] is None   # ground floor in many countries
    nested = {**MODULE2_NESTED, "home": {**MODULE2_NESTED["home"], "below_ground": True}}
    assert rules.normalize_profile(nested)["below_ground"] is True


def test_age_adds_older_adult_and_young_child():
    needs = rules.normalize_profile({"age": 70, "others": [{"who": "baby", "age": 1}]})["needs"]
    assert needs == {"older_adult": ["you"], "infant_or_young_child": ["baby"]}


def test_old_fields_still_become_tags():
    needs = rules.normalize_profile({"power_medical": ["cpap"], "fridge_meds": ["insulin"],
                                     "mobility": "cane"})["needs"]
    assert set(needs) == {"power_dependent_device", "refrigerated_medication", "walker_cane_or_crutches"}


def test_unknown_tag_goes_to_uncovered_needs():
    result = rules.evaluate(["heat"], profile(needs=["needs a translator for ASL"]))
    assert "needs a translator for ASL" in result["uncovered_needs"]


def test_household_rules_have_no_one_named():
    result = rules.evaluate(["flood"], profile())
    assert for_whom(result, "FLOOD-HIGH-GROUND") == []


# ---- CMIST ---------------------------------------------------------------------

def test_cmist_groups_are_complete_and_disjoint():
    assert list(rules.CMIST) == ["Communication", "Maintaining health", "Independence",
                                 "Support and safety", "Transportation"]
    assert len(rules.NEED_TAGS) == len(set(rules.NEED_TAGS)) == len(rules.CMIST_GROUP)


def test_every_cmist_group_has_rules():
    groups = {rules.CMIST_GROUP[tag] for r in rules.RULES for tag in r.needs}
    assert groups == set(rules.CMIST)


def test_needs_are_reported_by_cmist_group():
    result = rules.evaluate(["flood"], profile(needs=["speech_difficulty"],
                                               others=[{"who": "grandma", "needs": ["needs_personal_care"]}]))
    by_group = result["needs_by_cmist"]
    assert by_group["Communication"] == {"speech_difficulty": ["you"]}
    assert by_group["Support and safety"] == {"needs_personal_care": ["grandma"]}
    assert by_group["Transportation"] == {}


def test_personal_care_without_backup_is_a_top_gap():
    result = rules.evaluate(["heat"], profile(others=[{"who": "dad", "needs": ["needs_personal_care"]}]))
    gap = next(g for g in result["gaps"] if g["rule_id"] == "SUPPORT-CARE")
    assert gap["priority"] == 1 and gap["for_whom"] == ["dad"]


def test_accessible_transport_only_matters_when_you_might_evacuate():
    stretcher = profile(needs=["needs_accessible_transport"])
    assert "TRANS-ACCESSIBLE" in ids(rules.evaluate(["hurricane"], stretcher))
    assert "TRANS-ACCESSIBLE" not in ids(rules.evaluate(["earthquake"], stretcher))
