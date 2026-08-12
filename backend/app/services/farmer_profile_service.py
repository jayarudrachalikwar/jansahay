from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.farmer_profile import FarmerProfile
from app.schemas.farmer_profile import FarmerProfileCreate, FarmerProfileUpdate

COMPLETION_FIELDS = (
    "date_of_birth",
    "gender",
    "state",
    "district",
    "village",
    "land_size",
    "land_unit",
    "land_ownership",
    "primary_crop",
    "soil_type",
    "irrigation_type",
    "farming_type",
    "annual_income",
)


class ProfileAlreadyExistsError(Exception):
    pass


class ProfileNotFoundError(Exception):
    pass


def get_profile_by_user_id(db: Session, user_id: int) -> FarmerProfile | None:
    return db.query(FarmerProfile).filter(FarmerProfile.user_id == user_id).first()


def calculate_profile_completion(profile: FarmerProfile) -> int:
    if profile is None:
        return 0

    filled = 0
    for field_name in COMPLETION_FIELDS:
        value = getattr(profile, field_name)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        filled += 1

    total = len(COMPLETION_FIELDS)
    return round((filled / total) * 100)


def create_profile(db: Session, user_id: int, data: FarmerProfileCreate) -> FarmerProfile:
    if get_profile_by_user_id(db, user_id) is not None:
        raise ProfileAlreadyExistsError("Farmer profile already exists")

    profile = FarmerProfile(user_id=user_id, **data.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def update_profile(db: Session, user_id: int, data: FarmerProfileUpdate) -> FarmerProfile:
    profile = get_profile_by_user_id(db, user_id)
    if profile is None:
        raise ProfileNotFoundError("Farmer profile not found")

    for field_name, value in data.model_dump().items():
        setattr(profile, field_name, value)

    db.commit()
    db.refresh(profile)
    return profile


# Human-readable labels for every field tracked in COMPLETION_FIELDS
COMPLETION_FIELD_LABELS: dict[str, str] = {
    "date_of_birth": "Date of birth",
    "gender": "Gender",
    "state": "State",
    "district": "District",
    "village": "Village",
    "land_size": "Land size",
    "land_unit": "Land unit",
    "land_ownership": "Land ownership",
    "primary_crop": "Primary crop",
    "soil_type": "Soil type",
    "irrigation_type": "Irrigation type",
    "farming_type": "Farming type",
    "annual_income": "Annual income",
}


def get_profile_completion_detail(
    profile: FarmerProfile | None,
) -> tuple[int, list[dict[str, str]]]:
    """
    Return (completion_percentage, missing_fields).

    missing_fields is a list of {"field": <name>, "label": <human label>}
    for each COMPLETION_FIELD that is currently empty/None.

    Reuses calculate_profile_completion() — no logic duplication.
    """
    percentage = calculate_profile_completion(profile)

    if profile is None:
        missing = [
            {"field": f, "label": COMPLETION_FIELD_LABELS.get(f, f.replace("_", " ").title())}
            for f in COMPLETION_FIELDS
        ]
        return percentage, missing

    missing: list[dict[str, str]] = []
    for field_name in COMPLETION_FIELDS:
        value = getattr(profile, field_name)
        is_empty = value is None or (isinstance(value, str) and not value.strip())
        if is_empty:
            missing.append(
                {
                    "field": field_name,
                    "label": COMPLETION_FIELD_LABELS.get(
                        field_name, field_name.replace("_", " ").title()
                    ),
                }
            )

    return percentage, missing
