"""
Admin-only scheme management service.

Provides create / update / delete / admin-list operations for GovernmentScheme.
Farmer-facing read operations (list_active_schemes, get_scheme_detail, etc.)
remain in scheme_service.py — this module only handles admin mutations.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session, joinedload

from app.models.scheme import GovernmentScheme
from app.models.scheme_eligibility import SchemeEligibilityCriterion
from app.schemas.admin_scheme import (
    AdminSchemeCreate,
    AdminSchemeUpdate,
    EligibilityCriterionInput,
)

logger = logging.getLogger(__name__)


class SchemeDuplicateNameError(Exception):
    pass


class SchemeNotFoundError(Exception):
    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_scheme_by_id_for_admin(db: Session, scheme_id: int) -> GovernmentScheme | None:
    """Load a scheme (active or inactive) with its criteria eager-loaded."""
    return (
        db.query(GovernmentScheme)
        .options(joinedload(GovernmentScheme.eligibility_criteria))
        .filter(GovernmentScheme.id == scheme_id)
        .first()
    )


def _apply_criteria(
    db: Session,
    scheme: GovernmentScheme,
    criteria_data: list[EligibilityCriterionInput],
) -> None:
    """Replace all eligibility criteria on *scheme* with the provided list."""
    # Delete existing criteria — cascade="all, delete-orphan" would handle DB side
    # but we do it explicitly so the session stays consistent.
    for c in list(scheme.eligibility_criteria):
        db.delete(c)
    db.flush()

    for item in criteria_data:
        criterion = SchemeEligibilityCriterion(
            scheme_id=scheme.id,
            criterion_type=item.criterion_type,
            field_name=item.field_name,
            operator=item.operator,
            expected_value=item.expected_value,
            description=item.description,
        )
        db.add(criterion)


# ---------------------------------------------------------------------------
# List (all, including inactive — admin view)
# ---------------------------------------------------------------------------

def list_all_schemes_admin(db: Session) -> list[GovernmentScheme]:
    """Return all schemes ordered by name — admins can see inactive schemes."""
    return (
        db.query(GovernmentScheme)
        .options(joinedload(GovernmentScheme.eligibility_criteria))
        .order_by(GovernmentScheme.name.asc())
        .all()
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

def create_scheme(db: Session, data: AdminSchemeCreate) -> GovernmentScheme:
    scheme = GovernmentScheme(
        name=data.name.strip(),
        short_description=data.short_description.strip(),
        detailed_description=data.detailed_description.strip(),
        department=data.department.strip(),
        state=data.state.strip(),
        scheme_type=data.scheme_type.strip(),
        benefits=data.benefits.strip(),
        application_process=data.application_process.strip(),
        official_website=data.official_website.strip() if data.official_website else None,
        is_active=data.is_active,
    )
    db.add(scheme)
    db.flush()  # get scheme.id before inserting criteria

    _apply_criteria(db, scheme, data.eligibility_criteria)
    db.commit()
    db.refresh(scheme)
    return scheme


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

def update_scheme(db: Session, scheme_id: int, data: AdminSchemeUpdate) -> GovernmentScheme:
    scheme = _get_scheme_by_id_for_admin(db, scheme_id)
    if scheme is None:
        raise SchemeNotFoundError(f"Scheme {scheme_id} not found")

    scheme.name = data.name.strip()
    scheme.short_description = data.short_description.strip()
    scheme.detailed_description = data.detailed_description.strip()
    scheme.department = data.department.strip()
    scheme.state = data.state.strip()
    scheme.scheme_type = data.scheme_type.strip()
    scheme.benefits = data.benefits.strip()
    scheme.application_process = data.application_process.strip()
    scheme.official_website = data.official_website.strip() if data.official_website else None
    scheme.is_active = data.is_active

    _apply_criteria(db, scheme, data.eligibility_criteria)
    db.commit()
    db.refresh(scheme)
    return scheme


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

def delete_scheme(db: Session, scheme_id: int) -> None:
    scheme = _get_scheme_by_id_for_admin(db, scheme_id)
    if scheme is None:
        raise SchemeNotFoundError(f"Scheme {scheme_id} not found")
    db.delete(scheme)
    db.commit()


# ---------------------------------------------------------------------------
# Admin detail
# ---------------------------------------------------------------------------

def get_scheme_detail_admin(db: Session, scheme_id: int) -> GovernmentScheme:
    scheme = _get_scheme_by_id_for_admin(db, scheme_id)
    if scheme is None:
        raise SchemeNotFoundError(f"Scheme {scheme_id} not found")
    return scheme
