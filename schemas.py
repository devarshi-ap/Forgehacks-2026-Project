from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# Needs the AI may tag a person with, grouped by CMIST: the "access and
# functional needs" framework U.S. emergency planners use. A closed list, so
# every tag has a rule behind it (rules.py) and the AI can't invent field names.
# Anything that fits none of these goes in `uncovered_needs` instead.
# A wheelchair, having a car and living alone have their own fields.
CMIST = {
    "Communication": (
        "deaf_or_hard_of_hearing",
        "blind_or_low_vision",
        "speech_difficulty",
        "limited_english",
    ),
    "Maintaining health": (
        "daily_medication",
        "refrigerated_medication",
        "power_dependent_device",
        "dialysis_or_regular_treatment",
        "breathing_condition",
        "special_diet_or_allergy",
        "pregnant",
    ),
    "Independence": (
        "walker_cane_or_crutches",
        "everyday_aids",
        "service_animal",
    ),
    "Support and safety": (
        "memory_loss_or_dementia",
        "autism_or_developmental",
        "mental_health_condition",
        "needs_personal_care",
        "infant_or_young_child",
        "older_adult",
    ),
    "Transportation": (
        "needs_accessible_transport",
    ),
}

NEED_TAGS = tuple(tag for tags in CMIST.values() for tag in tags)

Need = Literal[NEED_TAGS]


class HomeProfile(BaseModel):
    type: Optional[str] = None
    floor: Optional[int] = None
    has_lift: Optional[bool] = None
    lift_needs_electricity: Optional[bool] = None
    below_ground: Optional[bool] = None


class MobilityProfile(BaseModel):
    uses_wheelchair: Optional[bool] = None
    wheelchair_type: Optional[str] = None


class HouseholdMember(BaseModel):
    """Someone else who lives with the user, e.g. {"who": "mom", "age": 78, "needs": ["memory_loss_or_dementia"]}."""
    who: str
    age: Optional[int] = None
    needs: List[Need] = Field(default_factory=list)


class HouseholdProfile(BaseModel):
    age: Optional[int] = None
    lives_alone: Optional[bool] = None

    home: HomeProfile = Field(
        default_factory=HomeProfile
    )

    mobility: MobilityProfile = Field(
        default_factory=MobilityProfile
    )

    medical_equipment: List[str] = Field(
        default_factory=list
    )

    has_car: Optional[bool] = None

    helper_nearby: Optional[bool] = None

    # The user's own needs, beyond wheelchair use and medical equipment above.
    needs: List[Need] = Field(default_factory=list)

    # Everyone else in the home, with their own needs.
    others: List[HouseholdMember] = Field(default_factory=list)

    pets: List[str] = Field(default_factory=list)

    has_backup_power: Optional[bool] = None

    has_ac: Optional[bool] = None

    # Needs that fit none of the tags, in the user's words (e.g. "son runs off when scared").
    uncovered_needs: List[str] = Field(default_factory=list)


class FollowupQuestion(BaseModel):
    id: str
    question: str
    helper: str
    options: List[str]


class IntakeAIResult(BaseModel):
    profile: HouseholdProfile
    followups: List[FollowupQuestion]
