from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EligibilityCriterionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    criterion_type: str
    field_name: str
    operator: str
    expected_value: str
    description: str | None = None


class SchemeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    short_description: str
    department: str
    state: str
    scheme_type: str
    benefits: str


class SchemeDetailResponse(SchemeResponse):
    detailed_description: str
    application_process: str
    official_website: str | None = None
    eligibility_criteria: list[EligibilityCriterionResponse] = Field(default_factory=list)


class SchemeSearchResponse(BaseModel):
    schemes: list[SchemeResponse]
    total: int


class SchemeEligibilityResponse(BaseModel):
    scheme: SchemeDetailResponse
    eligible: bool
    reasons: list[str]


class SchemeRecommendationResponse(BaseModel):
    scheme: SchemeResponse
    relevance_score: int = Field(ge=0, le=100)
    eligible: bool
    summary: str
    factors: list[str] = Field(default_factory=list)
    match_status: Literal["eligible", "partial", "no_match"] = "no_match"


class SchemeRecommendationsListResponse(BaseModel):
    recommendations: list[SchemeRecommendationResponse]
    total: int
