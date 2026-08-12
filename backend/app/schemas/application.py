from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.farmer_scheme_application import ApplicationStatus
from app.schemas.scheme import SchemeResponse

# ---------------------------------------------------------------------------
# Application CRUD schemas
# ---------------------------------------------------------------------------


class FarmerSchemeApplicationCreate(BaseModel):
    """Body is empty — status defaults to 'preparing', notes are optional."""

    notes: str | None = Field(default=None, max_length=2000)


class FarmerSchemeApplicationUpdate(BaseModel):
    status: ApplicationStatus | None = None
    notes: str | None = Field(default=None, max_length=2000)


class FarmerSchemeApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    scheme_id: int
    status: ApplicationStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime
    scheme: SchemeResponse


class ApplicationListResponse(BaseModel):
    applications: list[FarmerSchemeApplicationResponse]
    total: int


# ---------------------------------------------------------------------------
# Checklist schemas
# ---------------------------------------------------------------------------

ChecklistItemStatus = Literal["complete", "missing", "attention"]


class ApplicationChecklistItem(BaseModel):
    key: str
    label: str
    status: ChecklistItemStatus
    message: str


class ApplicationChecklistResponse(BaseModel):
    items: list[ApplicationChecklistItem]
    total: int
    completed: int
    missing: int
    ready: bool


# ---------------------------------------------------------------------------
# Summary (for dashboard)
# ---------------------------------------------------------------------------


class ApplicationSummaryResponse(BaseModel):
    total: int
    preparing: int
    ready_to_apply: int
    submitted: int
