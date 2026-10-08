from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.risk_service import get_top_risks
from app.services.intake_service import analyze_household


router = APIRouter(
    prefix="/api",
    tags=["StormSignal"]
)


# ---------------------------------------------------------
# Request models
# ---------------------------------------------------------

class IntakeRequest(BaseModel):
    location: str
    description: str


class PlanRequest(BaseModel):
    profile: dict
    answers: dict


# ---------------------------------------------------------
# MODULE 1 + MODULE 2
# ---------------------------------------------------------

@router.post("/intake")
def analyze_intake(request: IntakeRequest):

    # -----------------------------
    # Validate input
    # -----------------------------

    if not request.location.strip():

        raise HTTPException(
            status_code=400,
            detail="Location is required."
        )

    if not request.description.strip():

        raise HTTPException(
            status_code=400,
            detail="Household description is required."
        )

    # -----------------------------
    # MODULE 1
    # FEMA risk lookup
    # -----------------------------

    risk_result = get_top_risks(
        request.location
    )

    if not risk_result.get("found"):

        raise HTTPException(
            status_code=400,
            detail=risk_result.get(
                "message",
                "Location could not be found."
            )
        )

    # -----------------------------
    # MODULE 2
    # Groq AI Intake
    # -----------------------------

    try:

        ai_result = analyze_household(
            request.description
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    # -----------------------------
    # Combined response
    # -----------------------------

    return {

        "location": request.location,

        "profile": ai_result["profile"],

        "followups": ai_result["followups"],

        "risks": risk_result["risks"],

        "county": risk_result.get(
            "county"
        ),

        "state": risk_result.get(
            "state"
        ),

        "nri_rating": risk_result.get(
            "nri_rating"
        ),

        "nri_score": risk_result.get(
            "nri_score"
        )
    }


# ---------------------------------------------------------
# MODULE 4 placeholder
# ---------------------------------------------------------

@router.post("/plan")
def build_plan(request: PlanRequest):

    if not request.profile:

        raise HTTPException(
            status_code=400,
            detail="Profile is required."
        )

    return {

        "profile": request.profile,

        "answers": request.answers,

        "message":
            "Plan generation will be connected "
            "in Module 4."
    }