from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_farmer
from app.database.session import get_db
from app.models.user import User
from app.schemas.scheme import (
    SchemeRecommendationResponse,
    SchemeRecommendationsListResponse,
    SchemeResponse,
)
from app.services.scheme_service import FarmerProfileRequiredError, get_scheme_recommendations

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _build_recommendation_response(item: object) -> SchemeRecommendationResponse:
    """Single source of truth for building a recommendation response item."""
    return SchemeRecommendationResponse(
        scheme=SchemeResponse.model_validate(item.scheme),
        relevance_score=item.relevance_score,
        eligible=item.eligible,
        summary=item.summary,
        factors=item.factors,
        match_status=item.match_status,
    )


def _build_response(
    recommendations: list,
    total_override: int | None = None,
) -> SchemeRecommendationsListResponse:
    items = [_build_recommendation_response(r) for r in recommendations]
    return SchemeRecommendationsListResponse(
        recommendations=items,
        total=total_override if total_override is not None else len(items),
    )


@router.get("", response_model=SchemeRecommendationsListResponse)
def list_recommendations(
    limit: int = Query(default=10, ge=1, le=50),
    sort_by: Literal["score", "name", "eligibility"] = Query(default="score"),
    eligible_only: bool = Query(default=False),
    scheme_type: str | None = Query(default=None),
    state: str | None = Query(default=None),
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
) -> SchemeRecommendationsListResponse:
    """
    Return personalized scheme recommendations for the authenticated farmer.

    Query parameters:
      limit         1–50 (default 10)
      sort_by       score | name | eligibility  (default: score)
      eligible_only true/false — only return schemes where eligible=true
      scheme_type   filter by scheme type (case-insensitive exact match)
      state         filter by state (case-insensitive; also includes nationwide schemes)
    """
    try:
        recommendations = get_scheme_recommendations(
            db,
            current_user.id,
            limit=limit,
            eligible_only=eligible_only,
            sort_by=sort_by,
            scheme_type=scheme_type,
            state=state,
        )
    except FarmerProfileRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _build_response(recommendations)


@router.get("/summary", response_model=SchemeRecommendationsListResponse)
def recommendations_summary(
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
) -> SchemeRecommendationsListResponse:
    """
    Return the top 5 recommendations — suitable for dashboard widgets.
    Requires a completed farmer profile.
    """
    try:
        recommendations = get_scheme_recommendations(db, current_user.id, limit=5)
    except FarmerProfileRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _build_response(recommendations)
