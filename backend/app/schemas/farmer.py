"""
Admin-facing farmer response schemas.

Never exposes password_hash or any other authentication credential.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class AdminFarmerProfileResponse(BaseModel):
    """Farmer profile fields safe for admin viewing."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    date_of_birth: date | None
    gender: str | None
    state: str | None
    district: str | None
    village: str | None
    land_size: Decimal | None
    land_unit: str | None
    land_ownership: str | None
    primary_crop: str | None
    secondary_crop: str | None
    soil_type: str | None
    irrigation_type: str | None
    farming_type: str | None
    annual_income: Decimal | None
    created_at: datetime
    updated_at: datetime


class AdminFarmerListItem(BaseModel):
    """Compact farmer representation for the admin list view."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    phone_number: str | None
    is_active: bool
    created_at: datetime
    # Inline summary fields — convenient for the list without a second request
    state: str | None = None
    primary_crop: str | None = None
    has_profile: bool = False


class AdminFarmerDetail(BaseModel):
    """Full farmer account + profile for the admin detail view."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    phone_number: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    farmer_profile: AdminFarmerProfileResponse | None


class AdminFarmerListResponse(BaseModel):
    farmers: list[AdminFarmerListItem]
    total: int
