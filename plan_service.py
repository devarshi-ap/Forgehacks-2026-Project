
import os
import json
from pathlib import Path
from typing import cast

from dotenv import load_dotenv
from groq import Groq
from groq.types.chat import ChatCompletionMessageParam
from module4_schemas import PlanInput, PlanOutput


PROJECT_DIR = Path(__file__).resolve().parent
load_dotenv(PROJECT_DIR / ".env", override=False)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv(
    "GROQ_MODEL", "openai/gpt-oss-120b"
).strip()


def _build_rules_plan(raw_input: dict) -> dict:
    data = PlanInput.model_validate(raw_input)
    profile = data.profile
    risks = data.top_risks
    module3 = data.module3_output

    rules = module3.get("rules", module3.get("matched_rules", []))

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

    if not gaps:
        gaps = list(uncovered) or [
            "Confirm emergency contacts and safe evacuation arrangements."
        ]

    sections = {}

    for rule in rules:
        hazard = str(
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
            str(hazard),
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


def build_plan(raw_input: dict, use_groq: bool = False) -> dict:
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

        prompt_data = {
            "profile": raw_input.get("profile", {}),
            "top_risks": raw_input.get("top_risks", []),
            "module3_output": raw_input.get("module3_output", {}),
            "rules_based_plan": fallback["markdown"],
        }

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