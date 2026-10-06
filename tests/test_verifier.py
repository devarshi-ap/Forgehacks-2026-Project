"""Tests for Module 5 (verifier). Works with pytest (`pytest tests/test_verifier.py`)
and with plain Python (`python tests/test_verifier.py`)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import verifier  # noqa: E402

SAMPLES = ROOT / "samples" / "verifier"
RULES = json.loads((SAMPLES / "rules_example.json").read_text(encoding="utf-8"))
GOOD = (SAMPLES / "good_plan.md").read_text(encoding="utf-8")
BAD_MISSING = (SAMPLES / "bad_missing_rule.md").read_text(encoding="utf-8")
BAD_FORBIDDEN = (SAMPLES / "bad_forbidden.md").read_text(encoding="utf-8")


def test_good_plan_passes():
    result = verifier.verify_plan(GOOD, RULES)
    assert result == {"passed": True, "missing_rules": [], "forbidden_found": []}


def test_plan_with_a_rule_removed_is_caught():
    result = verifier.verify_plan(BAD_MISSING, RULES)
    assert result["passed"] is False
    assert result["missing_rules"] == ["EVAC-HELP"]
    assert result["forbidden_found"] == []


def test_go_to_the_basement_in_a_flood_is_caught():
    result = verifier.verify_plan(BAD_FORBIDDEN, RULES)
    assert result["passed"] is False
    assert result["forbidden_found"] == ["go to the basement"]
    assert result["missing_rules"] == []


def test_warning_against_a_forbidden_phrase_is_not_flagged():
    for sentence in ("Do not go to the basement.", "Never go to the basement.",
                     "You must not go to the basement.", "Please don’t go to the basement."):
        plan = GOOD.replace("Do not go to the basement during a flood.", sentence)
        assert verifier.verify_plan(plan, RULES)["passed"] is True, sentence


def test_case_spacing_and_markdown_do_not_hide_a_forbidden_phrase():
    plan = GOOD + "\n- Then GO   TO THE **basement** quickly.\n"
    assert verifier.verify_plan(plan, RULES)["forbidden_found"] == ["go to the basement"]


def test_rule_tag_must_be_in_square_brackets():
    plan = GOOD.replace("[EVAC-HELP]", "EVAC-HELP")
    assert verifier.verify_plan(plan, RULES)["missing_rules"] == ["EVAC-HELP"]


def test_rule_tag_tolerates_case_and_spaces():
    plan = GOOD.replace("[EVAC-HELP]", "[ evac-help ]")
    assert verifier.verify_plan(plan, RULES)["passed"] is True


def test_empty_plan_is_missing_everything():
    result = verifier.verify_plan("", RULES)
    assert result["passed"] is False
    assert result["missing_rules"] == ["PWR-WHEELCHAIR", "EVAC-HELP", "FLOOD-HIGH-GROUND"]


def test_accepts_plain_strings_and_phrase_dicts():
    rules = {"must_do": ["A-1", {"id": "B-2"}], "never_do": [{"phrase": "use the lift"}]}
    assert verifier.verify_plan("[A-1] [B-2] ok", rules)["passed"] is True
    assert verifier.verify_plan("[A-1] [B-2] use the lift", rules)["forbidden_found"] == ["use the lift"]


def test_finalize_passes_through_a_good_plan_without_calling_rewrite():
    def boom(plan, feedback):
        raise AssertionError("rewrite must not be called")
    out = verifier.finalize(GOOD, RULES, rewrite_fn=boom)
    assert out["passed"] and not out["used_rewrite"] and not out["used_fallback"]
    assert out["final_plan"] == GOOD


def test_finalize_rewrites_once_and_accepts_a_fixed_plan():
    calls = []

    def rewrite(plan, feedback):
        calls.append(feedback)
        return GOOD

    out = verifier.finalize(BAD_MISSING, RULES, rewrite_fn=rewrite)
    assert len(calls) == 1 and "EVAC-HELP" in calls[0]
    assert out["passed"] and out["used_rewrite"] and not out["used_fallback"]
    assert out["final_plan"] == GOOD


def test_finalize_falls_back_to_rules_when_rewrite_still_fails():
    calls = []

    def rewrite(plan, feedback):
        calls.append(1)
        return BAD_FORBIDDEN

    out = verifier.finalize(BAD_MISSING, RULES, rewrite_fn=rewrite)
    assert len(calls) == 1  # rewrite is tried only once
    assert out["passed"] is False and out["used_fallback"] is True
    for rule in RULES["must_do"]:
        assert f"[{rule['rule_id']}]" in out["final_plan"]
    assert "go to the basement" in out["final_plan"]  # listed under "Avoid"
    assert "go to the basement" not in verifier._norm(out["final_plan"].split("### Avoid")[0])


def test_finalize_falls_back_when_the_ai_call_crashes():
    def rewrite(plan, feedback):
        raise TimeoutError("AI service down")

    out = verifier.finalize(BAD_FORBIDDEN, RULES, rewrite_fn=rewrite)
    assert out["used_fallback"] is True and out["passed"] is False


def test_finalize_without_a_rewrite_function_goes_straight_to_fallback():
    out = verifier.finalize(BAD_MISSING, RULES)
    assert out["used_fallback"] is True and not out["used_rewrite"]
    assert out["final_plan"].startswith("## Your checklist (rules-based)")


def test_fallback_checklist_lists_gaps_in_priority_order():
    text = verifier.rules_to_checklist(RULES)
    assert text.index("No backup charging") < text.index("No agreed way to leave")


def test_command_line_demo_exit_codes():
    good = verifier.main(["verifier.py", str(SAMPLES / "good_plan.md"), str(SAMPLES / "rules_example.json")])
    bad = verifier.main(["verifier.py", str(SAMPLES / "bad_forbidden.md"), str(SAMPLES / "rules_example.json")])
    assert good == 0 and bad == 1


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print("PASS", name)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print("FAIL", name, "->", repr(exc))
    print(f"\n{len(tests) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
