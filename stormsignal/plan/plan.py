
import os
import json
from pathlib import Path
from typing import cast

from dotenv import load_dotenv
from groq import Groq
from groq.types.chat import ChatCompletionMessageParam
from .schemas import PlanInput, PlanOutput


PROJECT_DIR = Path(__file__).resolve().parents[2]  # project root, where .env lives
load_dotenv(PROJECT_DIR / ".env", override=False)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv(
    "GROQ_MODEL", "openai/gpt-oss-120b"
).strip()


HAZARD_LABELS = {
    "hurricane": "Hurricane", "flood": "Flooding", "heat": "Extreme heat",
    "earthquake": "Earthquake", "wildfire": "Wildfire", "landslide": "Landslide",
}
GENERAL_SECTION = "Everyone at home"


def _label(hazard) -> str:
    return HAZARD_LABELS.get(str(hazard).lower(), str(hazard))


def _from_rules_engine(module3: dict) -> list[dict]:
    """Module 3's must_do items -> the rule shape below (one hazard each, for_whom in the text)."""
    rules = []
    for item in module3.get("must_do", []):
        hazards = item.get("hazards") or []
        action = item.get("action", "")
        whom = [w for w in item.get("for_whom") or [] if w != "you"]
        if whom:
            action = f"{action} (for {', '.join(whom)})"
        rules.append(dict(item, action=action,
                          hazard=_label(hazards[0]) if hazards else GENERAL_SECTION))
    return rules


def _gap_text(gap) -> str:
    if isinstance(gap, dict):
        fix = f" → {gap['fix']}" if gap.get("fix") else ""
        return f"{gap.get('message', '')}{fix}"
    return str(gap)


def _build_rules_plan(raw_input: dict) -> dict:
    data = PlanInput.model_validate(raw_input)
    profile = data.profile
    risks = data.top_risks
    module3 = data.module3_output

    rules = module3.get("rules", module3.get("matched_rules", [])) or _from_rules_engine(module3)

    if isinstance(rules, dict):
        rules = [
            dict(rule, hazard=rule.get("hazard", hazard))
            for hazard, items in rules.items()
            if isinstance(items, list)
            for rule in items
            if isinstance(rule, dict)
        ]

    gaps = module3.get("gaps", [])
    uncovered = module3.get(
        "uncovered_needs", profile.get("uncovered_needs", [])
    )

    if isinstance(uncovered, str):
        uncovered = [uncovered]
    if isinstance(gaps, str):
        gaps = [gaps]
    gaps = [_gap_text(gap) for gap in gaps]

    if not gaps:
        gaps = list(uncovered) or [
            "Confirm emergency contacts and safe evacuation arrangements."
        ]

    sections = {}

    for rule in rules:
        hazard = _label(
            rule.get("hazard") or rule.get("risk") or "General safety"
        )
        rule_id = (
            rule.get("rule_id")
            or rule.get("ruleId")
            or rule.get("id")
            or rule.get("rule_code")
            or "UNKNOWN"
        )
        action = (
            rule.get("action")
            or rule.get("recommendation")
            or rule.get("instruction")
            or rule.get("description")
            or "Follow applicable safety guidance."
        )

        source = rule.get("source", "Source not provided by Module 3")

        if isinstance(source, dict):
            url = source.get("url") or source.get("link", "")
            name = source.get("name") or source.get("title") or "Source"
            source = f"{name} ({url})" if url else name

        sections.setdefault(hazard, []).append(
            f"- {action} [{rule_id}] — Source: {source}"
        )

    for risk in risks:
        hazard = (
            risk if isinstance(risk, str)
            else risk.get(
                "name", risk.get("hazard", risk.get("risk", "Unknown hazard"))
            )
        )
        sections.setdefault(
            _label(hazard),
            ["- No matching rule supplied; check official local guidance."]
        )

    lines = ["# Your biggest gaps", ""]
    lines.extend(f"- {gap}" for gap in gaps)
    lines += ["", "# Your plan", ""]

    for hazard, steps in sections.items():
        lines += [f"## {hazard}", "", *steps, ""]

    lines += ["# Other things to consider", ""]

    lines.extend(
        f"- **AI-suggested:** For '{need}', identify a suitable local "
        "service or trusted contact and verify arrangements."
        for need in uncovered
    )

    if not uncovered:
        lines.append(
            "- **AI-suggested:** Review emergency contacts and evacuation "
            "arrangements with your household."
        )

    markdown = "\n".join(lines)

    plan_by_hazard = {
        hazard: [step.removeprefix("- ") for step in steps]
        for hazard, steps in sections.items()
    }

    suggestions = [
        f"AI-suggested: Address uncovered need: {need}"
        for need in uncovered
    ]

    result = PlanOutput(
        biggest_gaps=[str(gap) for gap in gaps],
        plan_by_hazard=plan_by_hazard,
        other_things_to_consider=suggestions,
        markdown=markdown,
    )

    return result.model_dump()


def build_plan(raw_input: dict, use_groq: bool = False, feedback: str | None = None) -> dict:
    """Rules output -> plan. With use_groq the AI rewrites it in plain language; otherwise
    (or if the AI fails) the rules-based plan is returned. `feedback` is the verifier's
    note when it asks for a rewrite (Module 5)."""
    fallback = _build_rules_plan(raw_input)

    if not use_groq:
        return fallback

    if not GROQ_API_KEY:
        fallback["generation_method"] = "rule_based_fallback"
        fallback["generation_error"] = (
            "GROQ_API_KEY is missing. Check the project .env file."
        )
        return fallback

    try:
        client = Groq(api_key=GROQ_API_KEY)

        module3 = raw_input.get("module3_output", {})
        prompt_data = {
            "profile": raw_input.get("profile", {}),
            "top_risks": raw_input.get("top_risks", []),
            "module3_output": module3,
            "rules_based_plan": fallback["markdown"],
        }
        required_ids = [m.get("rule_id") for m in module3.get("must_do", []) if m.get("rule_id")]
        forbidden = module3.get("never_do", [])
        checks = ""
        if required_ids:
            checks += ("\n\nEvery one of these rule IDs MUST appear in the plan as a tag in square "
                       "brackets on its step, e.g. [PWR-WHEELCHAIR]: " + ", ".join(required_ids))
        if forbidden:
            checks += ("\n\nNEVER write any of these phrases anywhere in the plan, not even as a "
                       "warning: " + "; ".join(f'"{p}"' for p in forbidden))
        if feedback:
            checks += "\n\nA safety check rejected your previous plan: " + feedback

        messages = cast(
            list[ChatCompletionMessageParam],
            [
                {
                    "role": "system",
                    "content": (
                        "You are StormSignal's emergency preparedness plan writer. "
                        "Generate a personalized Markdown plan with these exact "
                        "headings: '# Your biggest gaps', '# Your plan', and "
                        "'# Other things to consider'. Preserve supplied rule IDs "
                        "and source citations. Never invent official sources, URLs, "
                        "or rule IDs. Use the rules-based plan as your factual "
                        "foundation. Clearly label additional advice as "
                        "'**AI-suggested:**'. If a hazard has no matching rule, "
                        "direct the user to verified local official guidance. "
                        "Return only the complete Markdown plan."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Create a personalized safety plan from this data:\n"
                        + json.dumps(
                            prompt_data,
                            ensure_ascii=False,
                            indent=2,
                        )
                        + checks
                    ),
                },
            ],
        )

        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.2,
            max_tokens=2500,
        )

        markdown = (
            response.choices[0].message.content or ""
        ).strip()

        required_headings = [
            "# Your biggest gaps",
            "# Your plan",
            "# Other things to consider",
        ]

        if not markdown or not all(
            heading in markdown for heading in required_headings
        ):
            raise ValueError(
                "Groq returned an empty plan or omitted a required heading."
            )

        fallback["markdown"] = markdown
        fallback["generation_method"] = "groq"
        fallback["generation_error"] = None
        return fallback

    except Exception as exc:
        fallback["generation_method"] = "rule_based_fallback"
        fallback["generation_error"] = f"{type(exc).__name__}: {exc}"
        return fallback