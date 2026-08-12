"""
Admin farmer management routes.

Provides read-only access to farmer accounts.
Never exposes passwords, password hashes, or authentication tokens.
All endpoints require admin role.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.database.session import get_db
from app.models.user import User
from app.schemas.farmer import (
    AdminFarmerDetail,
    AdminFarmerListItem,
    AdminFarmerListResponse,
)
from app.services.admin_farmer_service import FarmerNotFoundError, get_farmer, list_farmers

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/farmers", tags=["admin-farmers"])


@router.get("", response_model=AdminFarmerListResponse)
def list_farmers_endpoint(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminFarmerListResponse:
    """Return all farmer accounts with summary profile info. Admin only."""
    farmers = list_farmers(db)

    items: list[AdminFarmerListItem] = []
    for farmer in farmers:
        profile = farmer.farmer_profile
        items.append(
            AdminFarmerListItem(
                id=farmer.id,
                full_name=farmer.full_name,
                email=farmer.email,
                phone_number=farmer.phone_number,
                is_active=farmer.is_active,
                created_at=farmer.created_at,
                state=profile.state if profile else None,
                primary_crop=profile.primary_crop if profile else None,
                has_profile=profile is not None,
            )
        )

    return AdminFarmerListResponse(farmers=items, total=len(items))


@router.get("/{farmer_id}", response_model=AdminFarmerDetail)
def get_farmer_endpoint(
    farmer_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminFarmerDetail:
    """Return full farmer account + profile. Admin only."""
    try:
        farmer = get_farmer(db, farmer_id)
    except FarmerNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return AdminFarmerDetail.model_validate(farmer)
