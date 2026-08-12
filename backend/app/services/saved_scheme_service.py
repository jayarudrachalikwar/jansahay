"""
Saved-scheme business logic.

Business rules:
- Only the owning farmer can save/unsave their schemes.
- Saving is idempotent: saving an already-saved scheme returns the existing record.
- The scheme must be active to be saved.
- Cascade deletes on user or scheme removal are handled at the database level.
"""
from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, joinedload

from app.models.saved_scheme import SavedScheme
from app.models.scheme import GovernmentScheme

logger = logging.getLogger(__name__)


class SchemeNotFoundError(Exception):
    pass


class SavedSchemeNotFoundError(Exception):
    pass


def _get_active_scheme(db: Session, scheme_id: int) -> GovernmentScheme:
    scheme = (
        db.query(GovernmentScheme)
        .filter(GovernmentScheme.id == scheme_id, GovernmentScheme.is_active.is_(True))
        .first()
    )
    if scheme is None:
        raise SchemeNotFoundError(f"Scheme {scheme_id} not found or is not active.")
    return scheme


def save_scheme(db: Session, *, user_id: int, scheme_id: int) -> SavedScheme:
    """
    Save a scheme for the given farmer.
    Idempotent: returns the existing record if already saved.
    Raises SchemeNotFoundError if the scheme does not exist or is inactive.
    """
    _get_active_scheme(db, scheme_id)

    existing = (
        db.query(SavedScheme)
        .filter(SavedScheme.user_id == user_id, SavedScheme.scheme_id == scheme_id)
        .first()
    )
    if existing is not None:
        return existing

    record = SavedScheme(user_id=user_id, scheme_id=scheme_id)
    db.add(record)
    try:
        db.commit()
        db.refresh(record)
    except IntegrityError:
        db.rollback()
        # Race-condition: another request saved it first — return existing
        record = (
            db.query(SavedScheme)
            .filter(SavedScheme.user_id == user_id, SavedScheme.scheme_id == scheme_id)
            .first()
        )
    return record


def unsave_scheme(db: Session, *, user_id: int, scheme_id: int) -> None:
    """
    Remove a saved-scheme record for the given farmer.
    Raises SavedSchemeNotFoundError if the record does not exist.
    """
    record = (
        db.query(SavedScheme)
        .filter(SavedScheme.user_id == user_id, SavedScheme.scheme_id == scheme_id)
        .first()
    )
    if record is None:
        raise SavedSchemeNotFoundError(
            f"Scheme {scheme_id} is not in your saved list."
        )
    db.delete(record)
    db.commit()


def list_saved_schemes(db: Session, *, user_id: int) -> list[SavedScheme]:
    """
    Return all saved-scheme records for the given farmer, newest first.
    Eagerly loads the associated GovernmentScheme to avoid N+1 queries.
    """
    return (
        db.query(SavedScheme)
        .join(GovernmentScheme, SavedScheme.scheme_id == GovernmentScheme.id)
        .filter(
            SavedScheme.user_id == user_id,
            GovernmentScheme.is_active.is_(True),
        )
        .options(joinedload(SavedScheme.scheme))
        .order_by(SavedScheme.saved_at.desc())
        .all()
    )


def is_saved(db: Session, *, user_id: int, scheme_id: int) -> bool:
    """Return True if the farmer has saved the given scheme."""
    return (
        db.query(SavedScheme)
        .filter(SavedScheme.user_id == user_id, SavedScheme.scheme_id == scheme_id)
        .first()
    ) is not None
