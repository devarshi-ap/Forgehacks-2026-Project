from typing import Any
from pydantic import BaseModel, Field


class PlanInput(BaseModel):
    profile: dict[str, Any] = Field(default_factory=dict)
    top_risks: list[Any] = Field(default_factory=list)
    module3_output: dict[str, Any] = Field(default_factory=dict)


class PlanOutput(BaseModel):
    biggest_gaps: list[str]
    plan_by_hazard: dict[str, list[str]]
    other_things_to_consider: list[str]
    markdown: str
