from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _strip_optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


class FarmerProfileBase(BaseModel):
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=50)
    state: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    village: str | None = Field(default=None, max_length=150)
    land_size: Decimal | None = Field(default=None, ge=0)
    land_unit: str | None = Field(default=None, max_length=30)
    land_ownership: str | None = Field(default=None, max_length=50)
    primary_crop: str | None = Field(default=None, max_length=100)
    secondary_crop: str | None = Field(default=None, max_length=100)
    soil_type: str | None = Field(default=None, max_length=100)
    irrigation_type: str | None = Field(default=None, max_length=100)
    farming_type: str | None = Field(default=None, max_length=100)
    annual_income: Decimal | None = Field(default=None, ge=0)

    @field_validator(
        "gender",
        "state",
        "district",
        "village",
        "land_unit",
        "land_ownership",
        "primary_crop",
        "secondary_crop",
        "soil_type",
        "irrigation_type",
        "farming_type",
        mode="before",
    )
    @classmethod
    def strip_strings(cls, value: object) -> object:
        if isinstance(value, str):
            return _strip_optional_str(value)
        return value


class FarmerProfileCreate(FarmerProfileBase):
    pass


class FarmerProfileUpdate(FarmerProfileBase):
    pass


class FarmerProfileResponse(FarmerProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


class ProfileCompletionResponse(BaseModel):
    completion_percentage: int


class ProfileCompletionField(BaseModel):
    field: str
    label: str


class ProfileCompletionDetailResponse(BaseModel):
    completion_percentage: int
    missing_fields: list[ProfileCompletionField]
