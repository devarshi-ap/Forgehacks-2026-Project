import json
from pathlib import Path
import pytest
from stormsignal.plan import build_plan

FIXTURE = Path(__file__).resolve().parent.parent / "samples" / "plan" / "module4_input_example.json"

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


def test_reads_the_rules_engine_output():
    """Module 3's real output (must_do / gaps dicts / for_whom) must come through with every rule tag."""
    from stormsignal.rules import evaluate
    from stormsignal.verifier import verify_plan
    household = {"floor": 3, "mobility": "powered_wheelchair", "drives": False,
                 "others": [{"who": "mom", "needs": ["memory_loss_or_dementia"]}]}
    rules = evaluate(["hurricane", "flood", "heat"], household)
    result = build_plan({"profile": {}, "top_risks": ["hurricane", "flood", "heat"], "module3_output": rules})
    markdown = result["markdown"]
    assert verify_plan(markdown, rules)["passed"]
    assert "## Flooding" in markdown and "## Everyone at home" in markdown
    assert "(for mom)" in markdown
    assert "No backup charging for your wheelchair → Get a backup battery" in markdown
    assert "{'rule_id'" not in markdown  # gaps are written as text, not raw dicts
