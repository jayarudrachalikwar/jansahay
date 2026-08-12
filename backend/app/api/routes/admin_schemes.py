"""
Admin scheme management routes.

All endpoints require JWT authentication + admin role.
These are separate from the farmer-facing /api/schemes routes
and do NOT modify existing farmer-facing behaviour.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.database.session import get_db
from app.models.user import User
from app.schemas.admin_scheme import (
    AdminSchemeCreate,
    AdminSchemeListResponse,
    AdminSchemeResponse,
    AdminSchemeUpdate,
)
from app.services.admin_scheme_service import (
    SchemeNotFoundError,
    create_scheme,
    delete_scheme,
    get_scheme_detail_admin,
    list_all_schemes_admin,
    update_scheme,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/schemes", tags=["admin-schemes"])


@router.get("", response_model=AdminSchemeListResponse)
def list_schemes_admin(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminSchemeListResponse:
    """Return all schemes (active and inactive) for admin management."""
    schemes = list_all_schemes_admin(db)
    return AdminSchemeListResponse(
        schemes=[AdminSchemeResponse.model_validate(s) for s in schemes],
        total=len(schemes),
    )


@router.post("", response_model=AdminSchemeResponse, status_code=status.HTTP_201_CREATED)
def create_scheme_endpoint(
    body: AdminSchemeCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminSchemeResponse:
    """Create a new government scheme with optional eligibility criteria."""
    scheme = create_scheme(db, body)
    return AdminSchemeResponse.model_validate(scheme)


@router.get("/{scheme_id}", response_model=AdminSchemeResponse)
def get_scheme_admin(
    scheme_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminSchemeResponse:
    """Return a single scheme (active or inactive) for admin editing."""
    try:
        scheme = get_scheme_detail_admin(db, scheme_id)
    except SchemeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return AdminSchemeResponse.model_validate(scheme)


@router.put("/{scheme_id}", response_model=AdminSchemeResponse)
def update_scheme_endpoint(
    scheme_id: int,
    body: AdminSchemeUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminSchemeResponse:
    """Replace all scheme fields and eligibility criteria."""
    try:
        scheme = update_scheme(db, scheme_id, body)
    except SchemeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return AdminSchemeResponse.model_validate(scheme)


@router.delete(
    "/{scheme_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_scheme_endpoint(
    scheme_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    """Permanently delete a scheme and all its eligibility criteria (cascade)."""
    try:
        delete_scheme(db, scheme_id)
    except SchemeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
