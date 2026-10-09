"""Offline tests for Module 2 (intake). No API key or network needed: the Groq
client is replaced with a fake that returns a canned reply.

Run with `python -m pytest tests/test_intake.py`.
"""
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("GROQ_API_KEY", "test-key-not-used")  # module refuses to import without one

import intake_service  # noqa: E402
from schemas import NEED_TAGS, HouseholdProfile, IntakeAIResult  # noqa: E402

PROFILE_SCHEMA = intake_service.INTAKE_JSON_SCHEMA["properties"]["profile"]

# What the AI should return for:
# "I live with my mom, who has dementia and takes insulin, and my 6-year-old son.
#  We have a dog and no car. I'm hard of hearing. My son runs off when he's scared."
RICH_REPLY = {
    "profile": {
        "age": None, "lives_alone": False,
        "home": {"type": None, "floor": None, "has_lift": None,
                 "lift_needs_electricity": None, "below_ground": None},
        "mobility": {"uses_wheelchair": None, "wheelchair_type": None},
        "medical_equipment": [], "has_car": False, "helper_nearby": None,
        "needs": ["deaf_or_hard_of_hearing"],
        "others": [
            {"who": "mom", "age": None, "needs": ["memory_loss_or_dementia", "refrigerated_medication"]},
            {"who": "son", "age": 6, "needs": []},
        ],
        "pets": ["dog"], "has_backup_power": None, "has_ac": None,
        "uncovered_needs": ["son runs off when scared"],
    },
    "followups": [
        {"id": "has_backup_power", "question": "Do you have a way to keep insulin cold if the power goes out?",
         "helper": "This helps plan for your mom's medicine.", "options": ["Yes", "No", "Not sure"]},
    ],
}


def _walk(schema, path="profile"):
    """Yield every object node in the JSON schema."""
    if schema.get("type") == "object":
        yield path, schema
        for name, child in schema["properties"].items():
            yield from _walk(child, f"{path}.{name}")
    elif schema.get("type") == "array":
        yield from _walk(schema["items"], f"{path}[]")


# ---- the JSON schema the AI must follow --------------------------------------

def test_strict_mode_rules_hold_everywhere():
    """Groq's strict mode needs every property required and no extra properties, at every level."""
    for path, node in _walk(PROFILE_SCHEMA):
        assert set(node["required"]) == set(node["properties"]), path
        assert node["additionalProperties"] is False, path


def test_json_schema_and_pydantic_model_have_the_same_fields():
    assert set(PROFILE_SCHEMA["properties"]) == set(HouseholdProfile.model_fields)


def test_need_tags_are_the_same_list_everywhere():
    props = PROFILE_SCHEMA["properties"]
    assert props["needs"]["items"]["enum"] == list(NEED_TAGS)
    assert props["others"]["items"]["properties"]["needs"]["items"]["enum"] == list(NEED_TAGS)


def test_prompt_explains_every_tag():
    for tag in NEED_TAGS:
        assert tag in intake_service.SYSTEM_PROMPT, tag


def test_rich_reply_matches_the_json_schema():
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(RICH_REPLY, intake_service.INTAKE_JSON_SCHEMA)


def test_made_up_tag_is_rejected():
    jsonschema = pytest.importorskip("jsonschema")
    bad = json.loads(json.dumps(RICH_REPLY))
    bad["profile"]["needs"] = ["superpowers"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, intake_service.INTAKE_JSON_SCHEMA)
    with pytest.raises(Exception):
        IntakeAIResult.model_validate(bad)


# ---- the Pydantic model -------------------------------------------------------

def test_rich_reply_validates():
    result = IntakeAIResult.model_validate(RICH_REPLY)
    assert result.profile.others[0].needs == ["memory_loss_or_dementia", "refrigerated_medication"]
    assert result.profile.uncovered_needs == ["son runs off when scared"]


def test_old_output_without_new_fields_still_loads():
    """Kesava's original module2_output.json predates the new fields; they default to empty/unknown."""
    old = json.loads((ROOT / " module2_output.json").read_text(encoding="utf-8"))
    profile = IntakeAIResult.model_validate(old).profile
    assert profile.mobility.uses_wheelchair is True
    assert profile.needs == [] and profile.others == [] and profile.pets == []
    assert profile.has_backup_power is None and profile.home.below_ground is None


# ---- analyze_household with a fake AI -----------------------------------------

class _FakeCompletions:
    def __init__(self, reply):
        self.reply, self.calls = reply, []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        message = type("Message", (), {"content": json.dumps(self.reply)})()
        choice = type("Choice", (), {"message": message})()
        return type("Response", (), {"choices": [choice]})()


@pytest.fixture
def fake_ai(monkeypatch):
    fake = _FakeCompletions(RICH_REPLY)
    monkeypatch.setattr(intake_service.client.chat, "completions", fake)
    return fake


def test_analyze_household_returns_new_fields(fake_ai):
    out = intake_service.analyze_household("I live with my mom, who has dementia...")
    assert out["profile"]["needs"] == ["deaf_or_hard_of_hearing"]
    assert [o["who"] for o in out["profile"]["others"]] == ["mom", "son"]
    assert out["profile"]["pets"] == ["dog"]


def test_analyze_household_sends_the_tag_list_to_the_ai(fake_ai):
    intake_service.analyze_household("anything")
    sent = fake_ai.calls[0]["response_format"]["json_schema"]["schema"]
    assert sent["properties"]["profile"]["properties"]["needs"]["items"]["enum"] == list(NEED_TAGS)


def test_empty_description_is_rejected(fake_ai):
    with pytest.raises(ValueError):
        intake_service.analyze_household("   ")
    assert fake_ai.calls == []


# ---- CMIST grouping ----------------------------------------------------------

def test_cmist_has_the_five_groups():
    from schemas import CMIST
    assert list(CMIST) == ["Communication", "Maintaining health", "Independence",
                           "Support and safety", "Transportation"]


def test_each_tag_is_in_exactly_one_group():
    from schemas import CMIST
    flat = [tag for tags in CMIST.values() for tag in tags]
    assert len(flat) == len(set(flat)) == len(NEED_TAGS)


def test_prompt_names_every_group():
    from schemas import CMIST
    for group in CMIST:
        assert group in intake_service.SYSTEM_PROMPT, group
