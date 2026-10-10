"""Module 3: risks + profile -> must do, never do, gaps, sources. See rules.py.

Also picks the follow-up questions (open_questions) and applies the answers (apply_answers).
"""
from .rules import (CMIST, NEED_TAGS, QUESTIONS, RULES, SOURCES, apply_answers, evaluate,
                    normalize_profile, open_questions)

__all__ = ["CMIST", "NEED_TAGS", "QUESTIONS", "RULES", "SOURCES", "apply_answers", "evaluate",
           "normalize_profile", "open_questions"]
