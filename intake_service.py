import json
import os

from dotenv import load_dotenv
from groq import Groq

from schemas import NEED_TAGS, IntakeAIResult


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
- whether the home is below ground (basement)
- whether the home has a lift
- whether the lift needs electricity
- whether the person uses a wheelchair
- wheelchair type
- medical/assistive equipment
- whether the person has a car
- whether someone nearby can help
- the user's own needs (tags, see below)
- other people in the home and their needs
- pets
- whether they have backup power (generator, spare batteries)
- whether they have air conditioning
- needs that fit no tag (uncovered_needs)

Needs are tags from this list ONLY, grouped by CMIST
(Communication, Maintaining health, Independence, Support and safety,
Transportation). A person can have tags from several groups.

Communication (getting and understanding warnings):
- deaf_or_hard_of_hearing: deaf, hard of hearing, uses hearing aids
- blind_or_low_vision: blind, low vision, cannot read small text
- speech_difficulty: hard to speak or be understood, non-verbal,
  uses sign language or a communication device
- limited_english: limited English or prefers another language

Maintaining health (what keeps them well):
- daily_medication: takes medicine every day
- refrigerated_medication: medicine that must stay cold (e.g. insulin)
- power_dependent_device: oxygen, CPAP, ventilator, home dialysis or
  any medical device that needs electricity
- dialysis_or_regular_treatment: dialysis, chemotherapy or other
  treatment they must travel to on a schedule
- breathing_condition: asthma, COPD or other lung condition
- special_diet_or_allergy: severe food allergy, feeding tube or a
  diet they cannot go without (e.g. diabetic, celiac)
- pregnant

Independence (aids they rely on):
- walker_cane_or_crutches: uses a walker, cane, crutches or rollator
- everyday_aids: glasses, hearing aids, prosthetics or other aids that
  need spares or batteries
- service_animal: has a service animal (pets go in pets instead)

Support and safety (needs another person):
- memory_loss_or_dementia: dementia, Alzheimer's, gets confused or lost
- autism_or_developmental: autism, intellectual or developmental disability
- mental_health_condition: anxiety, PTSD, depression, bipolar disorder,
  schizophrenia or similar
- needs_personal_care: needs help to bathe, dress, eat, use the toilet
  or move between bed and chair, or has a home aide or caregiver
- infant_or_young_child: a baby or a child under about 5
- older_adult: about 65 or older

Transportation:
- needs_accessible_transport: cannot ride in an ordinary car, e.g.
  must stay in their wheelchair or needs a stretcher

Put a tag on the person it belongs to: the user's own needs go in
"needs", everyone else goes in "others" as
{"who": "mom", "age": 78, "needs": [...]}.
A wheelchair still goes in mobility, not in needs.

If something matters for safety but fits no tag, add a short phrase
in the user's words to uncovered_needs (e.g. "son runs away when
frightened"). Never drop a stated need.

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

Example 2:

User:
"I live with my mom, who has dementia and takes insulin, and my
6-year-old son. We have a dog. I'm hard of hearing."

Correct interpretation:

lives_alone = false
needs = ["deaf_or_hard_of_hearing"]
others = [
  {"who": "mom", "age": null, "needs": ["memory_loss_or_dementia",
   "refrigerated_medication"]},
  {"who": "son", "age": 6, "needs": []}
]
pets = ["dog"]

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
                        },

                        "below_ground": {
                            "type": ["boolean", "null"]
                        }
                    },

                    "required": [
                        "type",
                        "floor",
                        "has_lift",
                        "lift_needs_electricity",
                        "below_ground"
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
                },

                "needs": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": list(NEED_TAGS)
                    }
                },

                "others": {
                    "type": "array",

                    "items": {
                        "type": "object",

                        "properties": {

                            "who": {
                                "type": "string"
                            },

                            "age": {
                                "type": ["integer", "null"]
                            },

                            "needs": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": list(NEED_TAGS)
                                }
                            }
                        },

                        "required": [
                            "who",
                            "age",
                            "needs"
                        ],

                        "additionalProperties": False
                    }
                },

                "pets": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },

                "has_backup_power": {
                    "type": ["boolean", "null"]
                },

                "has_ac": {
                    "type": ["boolean", "null"]
                },

                "uncovered_needs": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },

            "required": [
                "age",
                "lives_alone",
                "home",
                "mobility",
                "medical_equipment",
                "has_car",
                "helper_nearby",
                "needs",
                "others",
                "pets",
                "has_backup_power",
                "has_ac",
                "uncovered_needs"
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