"""Module 2: household description -> profile + follow-up questions. See intake.py."""
from .schemas import CMIST, NEED_TAGS, HouseholdProfile, IntakeAIResult


def analyze_household(description: str) -> dict:
    """Runs the AI intake. Imported on first use, because intake.py needs GROQ_API_KEY
    as soon as it loads, and the schemas above must be usable without a key."""
    from .intake import analyze_household as run

    return run(description)


__all__ = ["CMIST", "NEED_TAGS", "HouseholdProfile", "IntakeAIResult", "analyze_household"]
