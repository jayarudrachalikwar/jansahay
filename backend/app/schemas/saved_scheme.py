from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.scheme import SchemeResponse


class SavedSchemeResponse(BaseModel):
    """A saved-scheme record returned to the farmer."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    scheme_id: int
    saved_at: datetime
    scheme: SchemeResponse


class SavedSchemeListResponse(BaseModel):
    saved_schemes: list[SavedSchemeResponse]
    total: int


class IsSavedResponse(BaseModel):
    scheme_id: int
    is_saved: bool
