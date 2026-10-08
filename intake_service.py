import json
import os

from dotenv import load_dotenv
from groq import Groq

from app.models.schemas import IntakeAIResult


# ---------------------------------------------------------
# StormSignal
# Module 2 - AI Intake Service
# ---------------------------------------------------------

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


client = Groq(
    api_key=GROQ_API_KEY
)


SYSTEM_PROMPT = """
You are the StormSignal AI Intake assistant.

Your ONLY job is to convert a person's natural-language
household description into structured information.

You must NOT:
- provide disaster safety advice
- recommend emergency actions
- diagnose medical conditions
- invent facts
- assume missing information

You MUST:
1. Extract only facts explicitly stated by the user.
2. Use null for unknown information.
3. Identify important missing household information.
4. Ask at most 2 useful follow-up questions.
5. Return JSON matching the supplied schema.

The profile contains:

- age
- lives_alone
- home type
- home floor
- whether the home has a lift
- whether the lift needs electricity
- whether the person uses a wheelchair
- wheelchair type
- medical/assistive equipment
- whether the person has a car
- whether someone nearby can help

For wheelchair_type use:
- "powered"
- "manual"
- "prefer_not_to_say"
- null

For helper_nearby:
- true
- false
- null

Important:
Do not infer facts that the user did not state.

Example:

User:
"I live alone on the third floor and use a wheelchair."

Correct interpretation:

lives_alone = true
floor = 3
uses_wheelchair = true

But:

has_lift = null
wheelchair_type = null
helper_nearby = null

because the user did not provide those facts.

Follow-up questions should only ask about important
missing information that could affect later safety rules.

Do not ask unnecessary personal questions.
"""


# ---------------------------------------------------------
# JSON Schema used by Groq Structured Outputs
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


def analyze_household(description: str) -> dict:
    """
    Convert natural-language household information
    into a structured profile and follow-up questions.
    """

    if not description or not description.strip():
        raise ValueError(
            "Household description cannot be empty."
        )

    user_prompt = f"""
Analyze this household description:

{description}

Extract only explicitly stated information.

Use null for information that is not provided.

Ask no more than 2 follow-up questions.

Do not provide safety advice.

Return the structured result according to the
provided JSON schema.
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

    # -----------------------------------------------------
    # Validate returned data using Pydantic
    # -----------------------------------------------------

    validated = IntakeAIResult.model_validate(
        data
    )

    return validated.model_dump()