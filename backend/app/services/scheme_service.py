from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.farmer_profile import FarmerProfile
from app.models.scheme import GovernmentScheme
from app.services.eligibility_service import EligibilityResult, evaluate_eligibility
from app.services.farmer_profile_service import get_profile_by_user_id
from app.services.recommendation_service import SchemeRecommendation, generate_recommendations


class SchemeNotFoundError(Exception):
    pass


class FarmerProfileRequiredError(Exception):
    pass


def list_active_schemes(
    db: Session,
    *,
    search: str | None = None,
    state: str | None = None,
    scheme_type: str | None = None,
) -> list[GovernmentScheme]:
    query = db.query(GovernmentScheme).filter(GovernmentScheme.is_active.is_(True))

    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                GovernmentScheme.name.ilike(term),
                GovernmentScheme.short_description.ilike(term),
                GovernmentScheme.benefits.ilike(term),
                GovernmentScheme.department.ilike(term),
            )
        )

    if state:
        query = query.filter(GovernmentScheme.state.ilike(state.strip()))

    if scheme_type:
        query = query.filter(GovernmentScheme.scheme_type.ilike(scheme_type.strip()))

    return query.order_by(GovernmentScheme.name.asc()).all()


def get_scheme_by_id(db: Session, scheme_id: int) -> GovernmentScheme | None:
    return (
        db.query(GovernmentScheme)
        .options(joinedload(GovernmentScheme.eligibility_criteria))
        .filter(GovernmentScheme.id == scheme_id, GovernmentScheme.is_active.is_(True))
        .first()
    )


def get_scheme_detail(db: Session, scheme_id: int) -> GovernmentScheme:
    scheme = get_scheme_by_id(db, scheme_id)
    if scheme is None:
        raise SchemeNotFoundError("Scheme not found")
    return scheme


def check_scheme_eligibility(
    db: Session,
    user_id: int,
    scheme_id: int,
) -> tuple[GovernmentScheme, EligibilityResult]:
    profile = get_profile_by_user_id(db, user_id)
    if profile is None:
        raise FarmerProfileRequiredError(
            "Farmer profile not found. Complete your profile to check scheme eligibility."
        )

    scheme = get_scheme_detail(db, scheme_id)
    eligibility = evaluate_eligibility(profile, scheme.eligibility_criteria)
    return scheme, eligibility


def get_scheme_recommendations(
    db: Session,
    user_id: int,
    limit: int = 10,
    *,
    eligible_only: bool = False,
    sort_by: str = "score",
    scheme_type: str | None = None,
    state: str | None = None,
) -> list[SchemeRecommendation]:
    profile = get_profile_by_user_id(db, user_id)
    if profile is None:
        raise FarmerProfileRequiredError(
            "Farmer profile not found. Complete your profile to receive recommendations."
        )
    return generate_recommendations(
        db,
        profile,
        limit=limit,
        eligible_only=eligible_only,
        sort_by=sort_by,
        scheme_type=scheme_type,
        state=state,
    )
