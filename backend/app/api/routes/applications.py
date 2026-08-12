"""
Phase 12 — Application Assistance routes.

All endpoints require farmer authentication.
user_id is ALWAYS derived from the JWT token — never from the request body.

Endpoints:
  GET    /api/applications                          — list own applications
  GET    /api/applications/summary                  — count summary for dashboard
  POST   /api/schemes/{scheme_id}/application       — create or get application
  GET    /api/schemes/{scheme_id}/application       — get application detail
  PATCH  /api/schemes/{scheme_id}/application       — update status / notes
  GET    /api/schemes/{scheme_id}/application/checklist — generate checklist
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_farmer
from app.database.session import get_db
from app.models.user import User
from app.schemas.application import (
    ApplicationChecklistResponse,
    ApplicationListResponse,
    ApplicationSummaryResponse,
    FarmerSchemeApplicationCreate,
    FarmerSchemeApplicationResponse,
    FarmerSchemeApplicationUpdate,
)
from app.schemas.scheme import SchemeResponse
from app.services.application_service import (
    ApplicationNotFoundError,
    SchemeNotFoundError,
    create_or_get_application,
    generate_checklist,
    get_application,
    get_application_summary,
    list_applications,
    update_application,
)

# ---------------------------------------------------------------------------
# Two routers:
#   applications_router — /api/applications prefix
#   scheme_application_router — /api/schemes prefix (appended to existing
#                               schemes router via separate include)
# ---------------------------------------------------------------------------

applications_router = APIRouter(prefix="/applications", tags=["applications"])
scheme_application_router = APIRouter(prefix="/schemes", tags=["applications"])


# ---------------------------------------------------------------------------
# /api/applications
# ---------------------------------------------------------------------------


@applications_router.get("", response_model=ApplicationListResponse)
def list_my_applications(
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
) -> ApplicationListResponse:
    """Return all application-preparation records for the authenticated farmer."""
    records = list_applications(db, user_id=current_user.id)
    return ApplicationListResponse(
        applications=[
            FarmerSchemeApplicationResponse(
                id=r.id,
                user_id=r.user_id,
                scheme_id=r.scheme_id,
                status=r.status,
                notes=r.notes,
                created_at=r.created_at,
                updated_at=r.updated_at,
                scheme=SchemeResponse.model_validate(r.scheme),
            )
            for r in records
        ],
        total=len(records),
    )


@applications_router.get("/summary", response_model=ApplicationSummaryResponse)
def get_my_application_summary(
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
) -> ApplicationSummaryResponse:
    """Return application count by status — for the dashboard pill."""
    return get_application_summary(db, user_id=current_user.id)


# ---------------------------------------------------------------------------
# /api/schemes/{scheme_id}/application
# ---------------------------------------------------------------------------


def _to_response(record: object) -> FarmerSchemeApplicationResponse:
    return FarmerSchemeApplicationResponse(
        id=record.id,
        user_id=record.user_id,
        scheme_id=record.scheme_id,
        status=record.status,
        notes=record.notes,
        created_at=record.created_at,
        updated_at=record.updated_at,
        scheme=SchemeResponse.model_validate(record.scheme),
    )


@scheme_application_router.post(
    "/{scheme_id}/application",
    response_model=FarmerSchemeApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_application(
    scheme_id: int,
    data: FarmerSchemeApplicationCreate = FarmerSchemeApplicationCreate(),
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
) -> FarmerSchemeApplicationResponse:
    """
    Create an application-preparation record for a scheme.
    Idempotent — returns the existing record if one already exists.
    """
    try:
        record = create_or_get_application(
            db, user_id=current_user.id, scheme_id=scheme_id, data=data
        )
    except SchemeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_response(record)


@scheme_application_router.get(
    "/{scheme_id}/application",
    response_model=FarmerSchemeApplicationResponse,
)
def get_my_application(
    scheme_id: int,
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
) -> FarmerSchemeApplicationResponse:
    """Return the farmer's application-preparation record for a scheme."""
    try:
        record = get_application(db, user_id=current_user.id, scheme_id=scheme_id)
    except SchemeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ApplicationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_response(record)


@scheme_application_router.patch(
    "/{scheme_id}/application",
    response_model=FarmerSchemeApplicationResponse,
)
def update_my_application(
    scheme_id: int,
    data: FarmerSchemeApplicationUpdate,
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
) -> FarmerSchemeApplicationResponse:
    """Update application status or notes."""
    try:
        record = update_application(
            db, user_id=current_user.id, scheme_id=scheme_id, data=data
        )
    except SchemeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ApplicationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_response(record)


@scheme_application_router.get(
    "/{scheme_id}/application/checklist",
    response_model=ApplicationChecklistResponse,
)
def get_application_checklist(
    scheme_id: int,
    current_user: User = Depends(require_farmer),
    db: Session = Depends(get_db),
) -> ApplicationChecklistResponse:
    """
    Return the structured application checklist for a scheme.

    Combines profile completeness + scheme eligibility criteria.
    Does NOT require an existing application record.
    """
    try:
        return generate_checklist(db, user_id=current_user.id, scheme_id=scheme_id)
    except SchemeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
