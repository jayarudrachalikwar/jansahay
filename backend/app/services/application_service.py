"""
Application-preparation business logic for Phase 12.

Responsibilities:
  - create / get / update FarmerSchemeApplication records
  - ownership enforcement (a farmer can only touch their own applications)
  - checklist generation — reuses existing eligibility_service and
    farmer_profile_service; no new eligibility logic introduced here
"""
from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.farmer_profile import FarmerProfile
from app.models.farmer_scheme_application import ApplicationStatus, FarmerSchemeApplication
from app.models.scheme import GovernmentScheme
from app.schemas.application import (
    ApplicationChecklistItem,
    ApplicationChecklistResponse,
    ApplicationSummaryResponse,
    FarmerSchemeApplicationCreate,
    FarmerSchemeApplicationUpdate,
)
from app.services.eligibility_service import evaluate_eligibility
from app.services.farmer_profile_service import (
    COMPLETION_FIELDS,
    COMPLETION_FIELD_LABELS,
    get_profile_by_user_id,
)
from app.services.scheme_service import get_scheme_by_id


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class ApplicationNotFoundError(Exception):
    pass


class ApplicationAlreadyExistsError(Exception):
    pass


class SchemeNotFoundError(Exception):
    pass


class ProfileRequiredError(Exception):
    pass


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_scheme(db: Session, scheme_id: int) -> GovernmentScheme:
    scheme = get_scheme_by_id(db, scheme_id)
    if scheme is None:
        raise SchemeNotFoundError(f"Scheme {scheme_id} not found or is not active.")
    return scheme


def _get_application(
    db: Session,
    *,
    user_id: int,
    scheme_id: int,
) -> FarmerSchemeApplication | None:
    return (
        db.query(FarmerSchemeApplication)
        .filter(
            FarmerSchemeApplication.user_id == user_id,
            FarmerSchemeApplication.scheme_id == scheme_id,
        )
        .options(joinedload(FarmerSchemeApplication.scheme))
        .first()
    )


def _attach_scheme(
    db: Session,
    application: FarmerSchemeApplication,
) -> FarmerSchemeApplication:
    """Ensure the scheme relationship is populated."""
    if application.scheme is None:
        db.refresh(application)
    return application


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------


def create_or_get_application(
    db: Session,
    *,
    user_id: int,
    scheme_id: int,
    data: FarmerSchemeApplicationCreate,
) -> FarmerSchemeApplication:
    """
    Return existing application or create a new one with status 'preparing'.
    Idempotent — calling this twice returns the same record.
    """
    _load_scheme(db, scheme_id)

    existing = _get_application(db, user_id=user_id, scheme_id=scheme_id)
    if existing is not None:
        return _attach_scheme(db, existing)

    application = FarmerSchemeApplication(
        user_id=user_id,
        scheme_id=scheme_id,
        status=ApplicationStatus.preparing,
        notes=data.notes,
    )
    db.add(application)
    try:
        db.commit()
        db.refresh(application)
    except IntegrityError:
        db.rollback()
        existing = _get_application(db, user_id=user_id, scheme_id=scheme_id)
        if existing is None:
            raise
        return _attach_scheme(db, existing)

    return _attach_scheme(db, application)


def get_application(
    db: Session,
    *,
    user_id: int,
    scheme_id: int,
) -> FarmerSchemeApplication:
    """
    Return the farmer's application for a scheme.
    Raises ApplicationNotFoundError if none exists.
    """
    _load_scheme(db, scheme_id)
    application = _get_application(db, user_id=user_id, scheme_id=scheme_id)
    if application is None:
        raise ApplicationNotFoundError(
            "No application found for this scheme. Use POST to create one."
        )
    return _attach_scheme(db, application)


def update_application(
    db: Session,
    *,
    user_id: int,
    scheme_id: int,
    data: FarmerSchemeApplicationUpdate,
) -> FarmerSchemeApplication:
    """
    Update status and/or notes on an existing application.
    Only the owning farmer can update their own application.
    """
    application = get_application(db, user_id=user_id, scheme_id=scheme_id)

    if data.status is not None:
        application.status = data.status
    if data.notes is not None:
        application.notes = data.notes

    db.commit()
    db.refresh(application)
    return _attach_scheme(db, application)


def list_applications(
    db: Session,
    *,
    user_id: int,
) -> list[FarmerSchemeApplication]:
    """Return all applications for the authenticated farmer, newest first."""
    return (
        db.query(FarmerSchemeApplication)
        .filter(FarmerSchemeApplication.user_id == user_id)
        .options(joinedload(FarmerSchemeApplication.scheme))
        .order_by(FarmerSchemeApplication.updated_at.desc())
        .all()
    )


def get_application_summary(
    db: Session,
    *,
    user_id: int,
) -> ApplicationSummaryResponse:
    """Return counts by status — used for the dashboard pill."""
    applications = list_applications(db, user_id=user_id)
    return ApplicationSummaryResponse(
        total=len(applications),
        preparing=sum(1 for a in applications if a.status == ApplicationStatus.preparing),
        ready_to_apply=sum(
            1 for a in applications if a.status == ApplicationStatus.ready_to_apply
        ),
        submitted=sum(1 for a in applications if a.status == ApplicationStatus.submitted),
    )


# ---------------------------------------------------------------------------
# Checklist generation
# ---------------------------------------------------------------------------

# Profile fields included in the checklist — ordered for display.
# Reuses COMPLETION_FIELDS + COMPLETION_FIELD_LABELS from farmer_profile_service.
# No new completion logic introduced.

_CHECKLIST_PROFILE_GROUPS: list[tuple[str, list[str]]] = [
    (
        "Identity",
        ["date_of_birth", "gender"],
    ),
    (
        "Location",
        ["state", "district", "village"],
    ),
    (
        "Land",
        ["land_size", "land_unit", "land_ownership"],
    ),
    (
        "Farming",
        ["primary_crop", "farming_type", "irrigation_type", "soil_type"],
    ),
    (
        "Finance",
        ["annual_income"],
    ),
]


def _profile_checklist_items(profile: FarmerProfile | None) -> list[ApplicationChecklistItem]:
    """
    Return one checklist item per profile field that appears in COMPLETION_FIELDS.
    Marks each field complete or missing based on the actual profile value.
    """
    items: list[ApplicationChecklistItem] = []

    for _group, fields in _CHECKLIST_PROFILE_GROUPS:
        for field_name in fields:
            if field_name not in COMPLETION_FIELDS:
                continue

            label = COMPLETION_FIELD_LABELS.get(
                field_name, field_name.replace("_", " ").title()
            )

            if profile is None:
                items.append(
                    ApplicationChecklistItem(
                        key=f"profile_{field_name}",
                        label=label,
                        status="missing",
                        message=f"Add your {label.lower()} to your farmer profile.",
                    )
                )
                continue

            value = getattr(profile, field_name, None)
            is_empty = value is None or (isinstance(value, str) and not value.strip())

            if is_empty:
                items.append(
                    ApplicationChecklistItem(
                        key=f"profile_{field_name}",
                        label=label,
                        status="missing",
                        message=f"Add your {label.lower()} to your farmer profile.",
                    )
                )
            else:
                items.append(
                    ApplicationChecklistItem(
                        key=f"profile_{field_name}",
                        label=label,
                        status="complete",
                        message=f"{label} is available in your profile.",
                    )
                )

    return items


def _eligibility_checklist_items(
    profile: FarmerProfile | None,
    scheme: GovernmentScheme,
) -> list[ApplicationChecklistItem]:
    """
    Return one checklist item per scheme eligibility criterion.
    Reuses evaluate_eligibility — no new eligibility logic.
    """
    if not scheme.eligibility_criteria:
        return [
            ApplicationChecklistItem(
                key="eligibility_no_criteria",
                label="Eligibility",
                status="complete",
                message="No specific eligibility criteria are defined for this scheme.",
            )
        ]

    if profile is None:
        return [
            ApplicationChecklistItem(
                key="eligibility_no_profile",
                label="Eligibility",
                status="missing",
                message="Complete your farmer profile to check scheme eligibility.",
            )
        ]

    # Reuse the existing service — evaluate each criterion individually so we
    # can surface per-criterion status.
    from app.services.eligibility_service import evaluate_criterion

    items: list[ApplicationChecklistItem] = []
    for idx, criterion in enumerate(scheme.eligibility_criteria):
        passed, reason = evaluate_criterion(profile, criterion)
        label = (
            criterion.description.rstrip(".")
            if criterion.description
            else f"{criterion.field_name.replace('_', ' ').title()} {criterion.operator} {criterion.expected_value}"
        )
        items.append(
            ApplicationChecklistItem(
                key=f"eligibility_{idx}_{criterion.field_name}",
                label=label,
                status="complete" if passed else "missing",
                message=reason,
            )
        )

    return items


def generate_checklist(
    db: Session,
    *,
    user_id: int,
    scheme_id: int,
) -> ApplicationChecklistResponse:
    """
    Generate a structured application checklist for a specific scheme.

    Combines:
      1. Profile completeness (reuses COMPLETION_FIELDS)
      2. Scheme eligibility criteria (reuses evaluate_criterion)
    """
    scheme = _load_scheme(db, scheme_id)
    profile = get_profile_by_user_id(db, user_id)

    profile_items = _profile_checklist_items(profile)
    eligibility_items = _eligibility_checklist_items(profile, scheme)
    all_items = profile_items + eligibility_items

    completed = sum(1 for item in all_items if item.status == "complete")
    missing = sum(1 for item in all_items if item.status in ("missing", "attention"))

    # Readiness: eligible + all profile completion items are complete
    eligibility_result = (
        evaluate_eligibility(profile, scheme.eligibility_criteria)
        if profile is not None
        else None
    )
    is_eligible = eligibility_result.eligible if eligibility_result is not None else False
    profile_complete = all(
        item.status == "complete" for item in profile_items
    )
    ready = is_eligible and profile_complete

    return ApplicationChecklistResponse(
        items=all_items,
        total=len(all_items),
        completed=completed,
        missing=missing,
        ready=ready,
    )
