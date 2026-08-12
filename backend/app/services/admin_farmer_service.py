"""
Admin-only farmer management service.

Provides read-only access to farmer accounts and their profiles.
Never exposes password hashes or authentication credentials.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session, joinedload

from app.models.user import User, UserRole

logger = logging.getLogger(__name__)


class FarmerNotFoundError(Exception):
    pass


def list_farmers(db: Session) -> list[User]:
    """Return all farmer accounts with their profiles eager-loaded, ordered by name."""
    return (
        db.query(User)
        .options(joinedload(User.farmer_profile))
        .filter(User.role == UserRole.farmer)
        .order_by(User.full_name.asc())
        .all()
    )


def get_farmer(db: Session, farmer_id: int) -> User:
    """Return a single farmer account with profile. Raises FarmerNotFoundError if not found."""
    user = (
        db.query(User)
        .options(joinedload(User.farmer_profile))
        .filter(User.id == farmer_id, User.role == UserRole.farmer)
        .first()
    )
    if user is None:
        raise FarmerNotFoundError(f"Farmer {farmer_id} not found")
    return user
