"""Module 5: Verifier (non-AI).

Question it answers: is the AI's plan safe to show?

Input : the plan Markdown (Module 4 output) + the rules (Module 3 output)
Output: {"passed": bool, "missing_rules": [...], "forbidden_found": [...]} + the final plan to display

How it works (plain Python, no AI):
  1. Every must-do rule ID must appear in the plan as a tag, like [PWR-WHEELCHAIR].
  2. No never-do phrase (like "go to the basement") may appear in the plan.
  3. If a check fails: ask Module 4 to rewrite ONCE. If it fails again, show the rules
     as a plain checklist instead. The AI text is never shown unless it passed.

Expected rules shape (Module 3). Extra keys are ignored; strings are also accepted:
  {
    "must_do":  [{"rule_id": "PWR-WHEELCHAIR", "action": "...", "source": "..."}],
    "never_do": ["go to the basement", ...],
    "gaps":     [{"message": "...", "fix": "...", "priority": 1}]
  }

Try it from the command line:
  python verifier.py samples/verifier/good_plan.md samples/verifier/rules_example.json
"""
from __future__ import annotations

import json
import re
import sys
from typing import Callable, Optional

# "do not go to the basement", "never go to ...", "avoid go to ..." right before the phrase = a warning, not advice
_NEGATION_BEFORE = re.compile(
    r"(?:do not|don't|never|should not|shouldn't|must not|mustn't|avoid)\s+(?:ever\s+)?$"
)


# ---------------------------------------------------------------- helpers
def _norm(text: str) -> str:
    """Lowercase, straighten quotes, drop Markdown emphasis, collapse spaces."""
    text = (text or "").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = text.replace("\u00a0", " ").replace("*", "").replace("`", "")
    return re.sub(r"\s+", " ", text).strip().lower()


def _rule_id(item) -> str:
    if isinstance(item, str):
        return item.strip()
    for key in ("rule_id", "id", "rule"):
        if item.get(key):
            return str(item[key]).strip()
    raise ValueError(f"must_do item has no rule id: {item!r}")


def _phrase(item) -> str:
    if isinstance(item, str):
        return item
    for key in ("phrase", "text"):
        if item.get(key):
            return str(item[key])
    raise ValueError(f"never_do item has no phrase: {item!r}")


def _has_tag(plan: str, rule_id: str) -> bool:
    return re.search(r"\[\s*" + re.escape(rule_id) + r"\s*\]", plan, flags=re.IGNORECASE) is not None


def _has_forbidden(plan_norm: str, phrase: str, allow_negated: bool) -> bool:
    needle = _norm(phrase)
    if not needle:
        return False
    for match in re.finditer(r"(?<!\w)" + re.escape(needle) + r"(?!\w)", plan_norm):
        before = plan_norm[max(0, match.start() - 30):match.start()]
        if allow_negated and _NEGATION_BEFORE.search(before):
            continue  # e.g. "Do not go to the basement" is a warning, not bad advice
        return True
    return False


# ---------------------------------------------------------------- the check
def verify_plan(plan_markdown: str, rules: dict, allow_negated: bool = True) -> dict:
    """Run both checks once. Returns {"passed", "missing_rules", "forbidden_found"}."""
    plan_markdown = plan_markdown or ""
    plan_norm = _norm(plan_markdown)

    required, seen = [], set()
    for item in rules.get("must_do", []):
        rid = _rule_id(item)
        if rid not in seen:
            seen.add(rid)
            required.append(rid)

    missing = [rid for rid in required if not _has_tag(plan_markdown, rid)]
    forbidden = [
        _phrase(item) for item in rules.get("never_do", [])
        if _has_forbidden(plan_norm, _phrase(item), allow_negated)
    ]
    return {"passed": not missing and not forbidden,
            "missing_rules": missing, "forbidden_found": forbidden}


# ---------------------------------------------------------------- fallback + rewrite loop
def rules_to_checklist(rules: dict) -> str:
    """The plain, rules-only checklist shown when the AI plan cannot be confirmed."""
    lines = ["## Your checklist (rules-based)",
             "",
             "_The AI-written plan could not be confirmed, so this is the checked list of required steps._",
             ""]
    gaps = sorted(rules.get("gaps", []), key=lambda g: g.get("priority", 99) if isinstance(g, dict) else 99)
    if gaps:
        lines += ["### Biggest gaps"]
        for n, gap in enumerate(gaps, start=1):
            if isinstance(gap, dict):
                fix = f" — {gap['fix']}" if gap.get("fix") else ""
                lines.append(f"{n}. {gap.get('message', '')}{fix}")
            else:
                lines.append(f"{n}. {gap}")
        lines.append("")
    lines += ["### Required steps"]
    for item in rules.get("must_do", []):
        rid = _rule_id(item)
        action = item.get("action", "") if isinstance(item, dict) else ""
        source = f" (Source: {item['source']})" if isinstance(item, dict) and item.get("source") else ""
        lines.append(f"- [ ] [{rid}] {action}{source}".rstrip())
    never = [_phrase(i) for i in rules.get("never_do", [])]
    if never:
        lines += ["", "### Avoid"] + [f"- {p}" for p in never]
    return "\n".join(lines)


def _feedback(result: dict) -> str:
    parts = []
    if result["missing_rules"]:
        parts.append("Your plan is missing these required rules: " + ", ".join(result["missing_rules"])
                     + ". Add each one as a step tagged like [RULE-ID].")
    if result["forbidden_found"]:
        parts.append("Your plan contains advice that is not allowed: "
                     + "; ".join(f'"{p}"' for p in result["forbidden_found"]) + ". Remove it.")
    return " ".join(parts)


def finalize(plan_markdown: str, rules: dict,
             rewrite_fn: Optional[Callable[[str, str], str]] = None,
             allow_negated: bool = True) -> dict:
    """Check the plan; on failure rewrite once; if it still fails, fall back to the rules checklist.

    rewrite_fn(plan_markdown, feedback_text) -> new_plan_markdown   (Module 4 provides this)

    Returns {"passed", "missing_rules", "forbidden_found", "used_rewrite", "used_fallback", "final_plan"}
    where passed/missing/forbidden describe the FIRST plan-check of the plan that was finally judged.
    """
    result = verify_plan(plan_markdown, rules, allow_negated)
    out = dict(result, used_rewrite=False, used_fallback=False, final_plan=plan_markdown)
    if result["passed"]:
        return out

    if rewrite_fn is not None:
        out["used_rewrite"] = True
        try:
            rewritten = rewrite_fn(plan_markdown, _feedback(result))
            second = verify_plan(rewritten, rules, allow_negated)
        except Exception:  # an AI call can fail; never let that break the page
            second = None
        if second is not None and second["passed"]:
            out.update(second, final_plan=rewritten)
            return out
        if second is not None:
            out.update({k: second[k] for k in ("missing_rules", "forbidden_found")})

    out.update(passed=False, used_fallback=True, final_plan=rules_to_checklist(rules))
    return out


# ---------------------------------------------------------------- command line demo
def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: python verifier.py PLAN.md RULES.json")
        return 2
    plan = open(argv[1], encoding="utf-8").read()
    rules = json.load(open(argv[2], encoding="utf-8"))
    result = verify_plan(plan, rules)
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
