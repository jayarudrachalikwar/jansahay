from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_farmer
from app.database.session import get_db
from app.models.user import User
from app.schemas.scheme import (
    SchemeDetailResponse,
    SchemeEligibilityResponse,
    SchemeRecommendationResponse,
    SchemeRecommendationsListResponse,
    SchemeResponse,
    SchemeSearchResponse,
)
from app.schemas.saved_scheme import IsSavedResponse, SavedSchemeListResponse, SavedSchemeResponse
from app.services.scheme_service import (
    FarmerProfileRequiredError,
    SchemeNotFoundError,
    check_scheme_eligibility,
    get_scheme_detail,
    get_scheme_recommendations,
    list_active_schemes,
)
from app.services.saved_scheme_service import (
    SavedSchemeNotFoundError,
    SchemeNotFoundError as SavedSchemeSchemeNotFoundError,
    is_saved,
    list_saved_schemes,
    save_scheme,
    unsave_scheme,
)

router = APIRouter(prefix="/schemes", tags=["schemes"])


@router.get("", response_model=SchemeSearchResponse)
def list_schemes(
    search: str | None = Query(default=None),
    state: str | None = Query(default=None),
    scheme_type: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SchemeSearchResponse:
    schemes = list_active_schemes(
        db,
        search=search,
        state=state,
        scheme_type=scheme_type,
    )
    return SchemeSearchResponse(
        schemes=[SchemeResponse.model_validate(scheme) for scheme in schemes],
        total=len(schemes),
    )


@router.get("/recommendations", response_model=SchemeRecommendationsListResponse)
def get_recommendations(
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
) -> SchemeRecommendationsListResponse:
    try:
        recommendations = get_scheme_recommendations(db, current_user.id)
    except FarmerProfileRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return SchemeRecommendationsListResponse(
        recommendations=[
            SchemeRecommendationResponse(
                scheme=SchemeResponse.model_validate(item.scheme),
                relevance_score=item.relevance_score,
                eligible=item.eligible,
                summary=item.summary,
                factors=item.factors,
                match_status=item.match_status,
            )
            for item in recommendations
        ],
        total=len(recommendations),
    )


@router.get("/{scheme_id}", response_model=SchemeDetailResponse)
def get_scheme(
    scheme_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SchemeDetailResponse:
    try:
        scheme = get_scheme_detail(db, scheme_id)
    except SchemeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return SchemeDetailResponse.model_validate(scheme)


@router.get("/{scheme_id}/eligibility", response_model=SchemeEligibilityResponse)
def get_scheme_eligibility(
    scheme_id: int,
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
) -> SchemeEligibilityResponse:
    try:
        scheme, eligibility = check_scheme_eligibility(db, current_user.id, scheme_id)
    except FarmerProfileRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except SchemeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return SchemeEligibilityResponse(
        scheme=SchemeDetailResponse.model_validate(scheme),
        eligible=eligibility.eligible,
        reasons=eligibility.reasons,
    )


# ---------------------------------------------------------------------------
# POST /schemes/{scheme_id}/save  — save a scheme
# ---------------------------------------------------------------------------

@router.post(
    "/{scheme_id}/save",
    response_model=SavedSchemeResponse,
    status_code=status.HTTP_201_CREATED,
)
def save_scheme_endpoint(
    scheme_id: int,
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
) -> SavedSchemeResponse:
    """Save a scheme for the authenticated farmer. Idempotent — returns existing record if already saved."""
    try:
        record = save_scheme(db, user_id=current_user.id, scheme_id=scheme_id)
    except SavedSchemeSchemeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    # Eagerly load the scheme for the response
    scheme = get_scheme_detail(db, scheme_id)
    return SavedSchemeResponse(
        id=record.id,
        scheme_id=record.scheme_id,
        saved_at=record.saved_at,
        scheme=SchemeResponse.model_validate(scheme),
    )


# ---------------------------------------------------------------------------
# DELETE /schemes/{scheme_id}/save  — unsave a scheme
# ---------------------------------------------------------------------------

@router.delete(
    "/{scheme_id}/save",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def unsave_scheme_endpoint(
    scheme_id: int,
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
) -> Response:
    """Remove a saved scheme for the authenticated farmer."""
    try:
        unsave_scheme(db, user_id=current_user.id, scheme_id=scheme_id)
    except SavedSchemeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
