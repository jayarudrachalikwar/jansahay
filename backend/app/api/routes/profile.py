from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_farmer
from app.database.session import get_db
from app.models.user import User
from app.schemas.farmer_profile import (
    FarmerProfileCreate,
    FarmerProfileResponse,
    FarmerProfileUpdate,
    ProfileCompletionDetailResponse,
    ProfileCompletionField,
    ProfileCompletionResponse,
)
from app.services.farmer_profile_service import (
    ProfileAlreadyExistsError,
    ProfileNotFoundError,
    calculate_profile_completion,
    create_profile,
    get_profile_by_user_id,
    get_profile_completion_detail,
    update_profile,
)

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=FarmerProfileResponse)
def get_my_profile(
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
) -> FarmerProfileResponse:
    profile = get_profile_by_user_id(db, current_user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farmer profile not found",
        )
    return profile


@router.post("", response_model=FarmerProfileResponse, status_code=status.HTTP_201_CREATED)
def create_my_profile(
    data: FarmerProfileCreate,
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
) -> FarmerProfileResponse:
    try:
        profile = create_profile(db, current_user.id, data)
    except ProfileAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return profile


@router.put("", response_model=FarmerProfileResponse)
def update_my_profile(
    data: FarmerProfileUpdate,
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
) -> FarmerProfileResponse:
    try:
        profile = update_profile(db, current_user.id, data)
    except ProfileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return profile


@router.get("/completion", response_model=ProfileCompletionResponse)
def get_my_profile_completion(
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
) -> ProfileCompletionResponse:
    profile = get_profile_by_user_id(db, current_user.id)
    return ProfileCompletionResponse(
        completion_percentage=calculate_profile_completion(profile),
    )


@router.get("/completion/detail", response_model=ProfileCompletionDetailResponse)
def get_my_profile_completion_detail(
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
) -> ProfileCompletionDetailResponse:
    """
    Return the profile completion percentage AND a list of which specific
    fields are still empty.  Useful for showing the farmer exactly what to fill in.

    Does NOT modify the existing GET /api/profile/completion endpoint.
    """
    profile = get_profile_by_user_id(db, current_user.id)
    percentage, missing = get_profile_completion_detail(profile)
    return ProfileCompletionDetailResponse(
        completion_percentage=percentage,
        missing_fields=[
            ProfileCompletionField(field=m["field"], label=m["label"])
            for m in missing
        ],
    )
