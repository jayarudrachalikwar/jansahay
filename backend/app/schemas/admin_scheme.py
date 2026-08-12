"""
Admin-facing scheme request/response schemas.

The farmer-facing read schemas (SchemeResponse, SchemeDetailResponse, etc.)
are in schemas/scheme.py and are reused here for response shapes.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Eligibility criterion — shared between create and update
# ---------------------------------------------------------------------------

class EligibilityCriterionInput(BaseModel):
    """A single eligibility rule submitted in a create/update request."""

    criterion_type: str = Field(default="profile", max_length=100)
    field_name: str = Field(min_length=1, max_length=100)
    operator: str = Field(min_length=1, max_length=50)
    expected_value: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)


# ---------------------------------------------------------------------------
# Create request
# ---------------------------------------------------------------------------

class AdminSchemeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    short_description: str = Field(min_length=1, max_length=500)
    detailed_description: str = Field(min_length=1)
    department: str = Field(min_length=1, max_length=255)
    state: str = Field(min_length=1, max_length=100)
    scheme_type: str = Field(min_length=1, max_length=100)
    benefits: str = Field(min_length=1)
    application_process: str = Field(min_length=1)
    official_website: str | None = Field(default=None, max_length=500)
    is_active: bool = Field(default=True)
    eligibility_criteria: list[EligibilityCriterionInput] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Update request (same shape as create — all fields required on full update)
# ---------------------------------------------------------------------------

class AdminSchemeUpdate(AdminSchemeCreate):
    pass


# ---------------------------------------------------------------------------
# Response — admin list item (same as create, plus id and timestamps)
# ---------------------------------------------------------------------------

class AdminSchemeResponse(BaseModel):
    """Full scheme representation returned by admin endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    short_description: str
    detailed_description: str
    department: str
    state: str
    scheme_type: str
    benefits: str
    application_process: str
    official_website: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    eligibility_criteria: list["AdminEligibilityCriterionResponse"] = Field(
        default_factory=list
    )


class AdminEligibilityCriterionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    criterion_type: str
    field_name: str
    operator: str
    expected_value: str
    description: str | None


AdminSchemeResponse.model_rebuild()


class AdminSchemeListResponse(BaseModel):
    schemes: list[AdminSchemeResponse]
    total: int
