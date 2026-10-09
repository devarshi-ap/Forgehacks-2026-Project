
import json
import os

from dotenv import load_dotenv
from groq import Groq

# Correct import for the StormSignal backend package
from app.models.schemas import IntakeAIResult


# ---------------------------------------------------------
# StormSignal - Module 2: AI Intake Service
# ---------------------------------------------------------

# Load environment variables from backend/.env
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b"
)

if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY is missing. "
        "Add it to backend/.env"
    )

client = Groq(api_key=GROQ_API_KEY)


# ---------------------------------------------------------
# System Prompt
# ---------------------------------------------------------

SYSTEM_PROMPT = """
You are the StormSignal AI Intake assistant.

Your only task is to convert a household description
into structured information.

Rules:
1. Extract only facts explicitly stated by the user.
2. Use null for unknown information.
3. Do not invent or assume facts.
4. Do not provide disaster safety advice.
5. Do not recommend emergency actions.
6. Do not diagnose medical conditions.
7. Ask at most 2 useful follow-up questions.
8. Ask only questions relevant to later safety rules.
9. Return data matching the provided JSON schema.

Extract these fields:
- age
- lives_alone
- home type
- home floor
- has_lift
- lift_needs_electricity
- uses_wheelchair
- wheelchair_type
- medical_equipment
- has_car
- helper_nearby

Allowed wheelchair_type values:
- powered
- manual
- prefer_not_to_say
- null

Use true, false, or null for boolean fields.

Example:
"I live alone on the third floor and use a wheelchair."

Extract:
- lives_alone = true
- floor = 3
- uses_wheelchair = true

Do not assume whether the home has a lift,
whether the wheelchair is powered, or whether
a helper is nearby.

Use null for those unknown values.
"""


# ---------------------------------------------------------
# Strict JSON Schema for Groq Structured Outputs
# ---------------------------------------------------------

INTAKE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "profile": {
            "type": "object",
            "properties": {
                "age": {
                    "type": ["integer", "null"]
                },
                "lives_alone": {
                    "type": ["boolean", "null"]
                },
                "home": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": ["string", "null"]
                        },
                        "floor": {
                            "type": ["integer", "null"]
                        },
                        "has_lift": {
                            "type": ["boolean", "null"]
                        },
                        "lift_needs_electricity": {
                            "type": ["boolean", "null"]
                        }
                    },
                    "required": [
                        "type",
                        "floor",
                        "has_lift",
                        "lift_needs_electricity"
                    ],
                    "additionalProperties": False
                },
                "mobility": {
                    "type": "object",
                    "properties": {
                        "uses_wheelchair": {
                            "type": ["boolean", "null"]
                        },
                        "wheelchair_type": {
                            "type": ["string", "null"]
                        }
                    },
                    "required": [
                        "uses_wheelchair",
                        "wheelchair_type"
                    ],
                    "additionalProperties": False
                },
                "medical_equipment": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "has_car": {
                    "type": ["boolean", "null"]
                },
                "helper_nearby": {
                    "type": ["boolean", "null"]
                }
            },
            "required": [
                "age",
                "lives_alone",
                "home",
                "mobility",
                "medical_equipment",
                "has_car",
                "helper_nearby"
            ],
            "additionalProperties": False
        },
        "followups": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string"
                    },
                    "question": {
                        "type": "string"
                    },
                    "helper": {
                        "type": "string"
                    },
                    "options": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": [
                    "id",
                    "question",
                    "helper",
                    "options"
                ],
                "additionalProperties": False
            }
        }
    },
    "required": [
        "profile",
        "followups"
    ],
    "additionalProperties": False
}


# ---------------------------------------------------------
# Analyze Household
# ---------------------------------------------------------

def analyze_household(description: str) -> dict:
    """
    Convert a household description into a structured
    profile and up to two follow-up questions.
    """

    if not isinstance(description, str) or not description.strip():
        raise ValueError(
            "Household description cannot be empty."
        )

    user_prompt = f"""
Analyze the following household description:

{description}

Extract only explicitly stated facts.
Use null for unknown information.
Ask no more than 2 useful follow-up questions.
Do not provide disaster safety advice.
Return only data matching the supplied JSON schema.
"""

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "stormsignal_intake",
                    "strict": True,
                    "schema": INTAKE_JSON_SCHEMA
                }
            },
            temperature=0.1
        )

    except Exception as error:
        raise RuntimeError(
            f"Groq API request failed: {error}"
        ) from error

    content = response.choices[0].message.content

    if not content:
        raise RuntimeError(
            "Groq returned an empty response."
        )

    try:
        data = json.loads(content)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "Groq returned invalid JSON."
        ) from error

    # Validate the response against the Pydantic model.
    validated = IntakeAIResult.model_validate(data)

    result = validated.model_dump()

    # Enforce the maximum follow-up count in application code.
    result["followups"] = result["followups"][:2]

    return result
