"""
Farmer saved-schemes read endpoint.

GET /api/saved-schemes  — list all schemes saved by the authenticated farmer.

Save/unsave mutations live on POST/DELETE /api/schemes/{id}/save to
keep scheme-related operations co-located with schemes.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_farmer
from app.database.session import get_db
from app.models.user import User
from app.schemas.saved_scheme import SavedSchemeListResponse, SavedSchemeResponse
from app.schemas.scheme import SchemeResponse
from app.services.saved_scheme_service import list_saved_schemes

router = APIRouter(prefix="/saved-schemes", tags=["saved-schemes"])


@router.get("", response_model=SavedSchemeListResponse)
def list_my_saved_schemes(
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
) -> SavedSchemeListResponse:
    """Return all schemes saved by the authenticated farmer, newest first."""
    records = list_saved_schemes(db, user_id=current_user.id)

    items = [
        SavedSchemeResponse(
            id=record.id,
            scheme_id=record.scheme_id,
            saved_at=record.saved_at,
            scheme=SchemeResponse.model_validate(record.scheme),
        )
        for record in records
    ]
    return SavedSchemeListResponse(saved_schemes=items, total=len(items))
