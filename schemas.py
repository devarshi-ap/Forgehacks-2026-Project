from typing import List, Optional

from pydantic import BaseModel, Field


class HomeProfile(BaseModel):
    type: Optional[str] = None
    floor: Optional[int] = None
    has_lift: Optional[bool] = None
    lift_needs_electricity: Optional[bool] = None


class MobilityProfile(BaseModel):
    uses_wheelchair: Optional[bool] = None
    wheelchair_type: Optional[str] = None


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


class FollowupQuestion(BaseModel):
    id: str
    question: str
    helper: str
    options: List[str]


class IntakeAIResult(BaseModel):
    profile: HouseholdProfile
    followups: List[FollowupQuestion]