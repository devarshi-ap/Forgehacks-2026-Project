import json
from pathlib import Path
import pytest
from plan_service import build_plan

FIXTURE = Path(__file__).with_name("module4_input_example.json")

@pytest.fixture
def sample_input():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))

def test_required_sections(sample_input):
    markdown = build_plan(sample_input)["markdown"]
    assert "# Your biggest gaps" in markdown
    assert "# Your plan" in markdown
    assert "# Other things to consider" in markdown

def test_rule_ids_and_sources(sample_input):
    markdown = build_plan(sample_input)["markdown"]
    for rule in sample_input["module3_output"]["rules"]:
        assert f'[{rule["rule_id"]}]' in markdown
        assert rule["source"]["url"] in markdown

def test_uncovered_needs(sample_input):
    markdown = build_plan(sample_input)["markdown"]
    assert "AI-suggested" in markdown
    assert "Accessible emergency transport" in markdown

@pytest.mark.parametrize("persona", [
    {"home_type": "Apartment", "wheelchair_user": True},
    {"home_type": "Mobile home", "no_car": True},
    {"home_type": "House", "powered_medical_equipment": True},
    {"home_type": "Apartment", "no_car": False},
    {"home_type": "House", "pets": ["dog"]},
])
def test_five_personas(sample_input, persona):
    sample_input["profile"].update(persona)
    result = build_plan(sample_input)
    assert result["markdown"].strip()
    assert "# Your plan" in result["markdown"]

def test_missing_rules(sample_input):
    sample_input["module3_output"]["rules"] = []
    markdown = build_plan(sample_input)["markdown"]
    assert "Flooding" in markdown
    assert "Extreme Heat" in markdown

def test_missing_rule_id(sample_input):
    sample_input["module3_output"]["rules"][0].pop("rule_id")
    markdown = build_plan(sample_input)["markdown"]
    assert "[UNKNOWN]" in markdown
