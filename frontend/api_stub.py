"""Temporary stand-ins for the real backend (Kesava's AI/ML part).

Right now both functions just return example JSON from the mock_data folder,
so the screens can be built and tested before the backend exists.
When the real backend is ready, only THIS file changes: replace the bodies
with calls to the real functions. The screens do not need to change.
"""
import json
from pathlib import Path

MOCK_DIR = Path(__file__).resolve().parent.parent / "mock_data"


def _load(name: str) -> dict:
    with open(MOCK_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def analyze_household(location: str, description: str) -> dict:
    """AI 1 (Intake): turn the user's words into a profile plus 1-2 follow-up questions.

    Returns: {"profile": {...}, "followups": [{"id", "question", "options"}, ...]}
    """
    return _load("intake_example.json")


def build_plan(profile: dict, answers: dict) -> dict:
    """Rules engine + AI 3 (Plan writer) + Verifier: build the personal plan.

    answers is a dict like {"wheelchair_type": "Powered", "elevator_backup": "I don't know"}.
    Returns the plan JSON (see mock_data/plan_example.json for the exact shape).
    """
    return _load("plan_example.json")
