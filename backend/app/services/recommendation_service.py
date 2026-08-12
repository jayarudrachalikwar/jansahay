from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session, joinedload

from app.models.farmer_profile import FarmerProfile
from app.models.scheme import GovernmentScheme
from app.services.eligibility_service import EligibilityResult, evaluate_eligibility


@dataclass
class SchemeRecommendation:
    scheme: GovernmentScheme
    relevance_score: int
    eligible: bool
    summary: str
    factors: list[str] = field(default_factory=list)
    match_status: str = "no_match"  # "eligible" | "partial" | "no_match"


RANKING_WEIGHTS = {
    "eligibility": 40,
    "state": 15,
    "occupation": 10,
    "income": 10,
    "land_holding": 10,
    "category": 5,
    "farming_type": 5,
    "crop_type": 5,
}


def _score_state_match(profile: FarmerProfile, scheme: GovernmentScheme) -> tuple[int, str | None]:
    if not profile.state or not scheme.state:
        return 0, None
    if profile.state.strip().lower() == scheme.state.strip().lower():
        return RANKING_WEIGHTS["state"], "State matches the scheme coverage area."
    if scheme.state.strip().lower() in {"all india", "pan india", "national"}:
        return RANKING_WEIGHTS["state"], "Scheme is available nationwide."
    return 0, None


def _score_field_match(
    profile_value: str | None,
    expected_values: list[str],
    weight_key: str,
    label: str,
) -> tuple[int, str | None]:
    if not profile_value:
        return 0, None
    normalized_profile = profile_value.strip().lower()
    normalized_expected = {value.strip().lower() for value in expected_values if value.strip()}
    if normalized_profile in normalized_expected:
        return RANKING_WEIGHTS[weight_key], f"{label} aligns with scheme focus."
    return 0, None


def _build_summary(eligible: bool, factors: list[str]) -> str:
    if eligible:
        prefix = "Profile-based recommendation: you appear eligible"
    else:
        prefix = "Profile-based recommendation: partial profile match"
    if factors:
        return f"{prefix}. {' '.join(factors[:2])}"
    return prefix + "."


def _compute_match_status(
    eligible: bool,
    criteria_count: int,
    eligibility: EligibilityResult,
) -> str:
    """
    Deterministic match-status classification:
      eligible  — all criteria passed (or scheme has no criteria)
      partial   — at least one criterion passed but not all
      no_match  — no criteria passed
    """
    if eligible:
        return "eligible"
    if criteria_count == 0:
        # No criteria → scheme_service treats as eligible; this path is
        # reached only if eligible==False, which can't happen with 0 criteria.
        return "eligible"

    # Count passing criteria by inspecting reason text produced by eligibility_service.
    # Passing reasons contain "satisfied", "matches", "within", "is among", or "includes".
    PASSING_MARKERS = ("satisfied", "matches", "within", "is among", "includes")
    passed_count = sum(
        1 for reason in eligibility.reasons
        if any(marker in reason.lower() for marker in PASSING_MARKERS)
    )
    return "partial" if passed_count > 0 else "no_match"


def calculate_relevance_score(
    profile: FarmerProfile,
    scheme: GovernmentScheme,
    eligibility: EligibilityResult,
) -> tuple[int, str, list[str]]:
    """Return (score, summary, factors).  The factors list is preserved in full."""
    score = 0
    factors: list[str] = []

    if eligibility.eligible:
        score += RANKING_WEIGHTS["eligibility"]
        factors.append("You meet the eligibility criteria.")

    state_score, state_reason = _score_state_match(profile, scheme)
    score += state_score
    if state_reason:
        factors.append(state_reason)

    for criterion in scheme.eligibility_criteria:
        field_name = criterion.field_name
        if field_name in {"farming_type", "occupation"}:
            pts, reason = _score_field_match(
                profile.farming_type,
                [criterion.expected_value],
                "occupation",
                "Farming type",
            )
        elif field_name == "annual_income":
            if eligibility.eligible:
                pts, reason = RANKING_WEIGHTS["income"], "Income profile fits scheme limits."
            else:
                pts, reason = 0, None
        elif field_name in {"land_holding", "land_size"}:
            if eligibility.eligible:
                pts, reason = RANKING_WEIGHTS["land_holding"], "Land holding matches scheme range."
            else:
                pts, reason = 0, None
        elif field_name in {"category", "farmer_category", "land_ownership"}:
            pts, reason = _score_field_match(
                profile.land_ownership,
                criterion.expected_value.split(","),
                "category",
                "Farmer category",
            )
        elif field_name in {"crop_type", "primary_crop"}:
            pts, reason = _score_field_match(
                profile.primary_crop,
                criterion.expected_value.split(","),
                "crop_type",
                "Crop type",
            )
        else:
            pts, reason = 0, None

        if pts > 0 and reason and reason not in factors:
            score += pts
            factors.append(reason)

    score = min(score, 100)
    return score, _build_summary(eligibility.eligible, factors), factors


def generate_recommendations(
    db: Session,
    profile: FarmerProfile,
    limit: int = 10,
    *,
    eligible_only: bool = False,
    sort_by: str = "score",
    scheme_type: str | None = None,
    state: str | None = None,
) -> list[SchemeRecommendation]:
    """
    Generate personalised scheme recommendations.

    Parameters
    ----------
    limit         Maximum results to return.
    eligible_only When True, return only schemes where eligible is True.
    sort_by       "score"       — highest relevance score first (default)
                  "name"        — alphabetical by scheme name
                  "eligibility" — eligible schemes first, then by score
    scheme_type   Case-insensitive exact match on scheme.scheme_type.
    state         Case-insensitive match on scheme.state; also includes nationwide schemes.
    """
    schemes = (
        db.query(GovernmentScheme)
        .options(joinedload(GovernmentScheme.eligibility_criteria))
        .filter(GovernmentScheme.is_active.is_(True))
        .all()
    )

    # Python-level filters (no extra DB round-trip required)
    if scheme_type:
        st_lower = scheme_type.strip().lower()
        schemes = [s for s in schemes if s.scheme_type.strip().lower() == st_lower]
    if state:
        state_lower = state.strip().lower()
        nationwide = {"all india", "pan india", "national"}
        schemes = [
            s for s in schemes
            if s.state.strip().lower() == state_lower
            or s.state.strip().lower() in nationwide
        ]

    recommendations: list[SchemeRecommendation] = []
    for scheme in schemes:
        eligibility = evaluate_eligibility(profile, scheme.eligibility_criteria)
        score, summary, factors = calculate_relevance_score(profile, scheme, eligibility)
        match_status = _compute_match_status(
            eligibility.eligible,
            len(scheme.eligibility_criteria),
            eligibility,
        )
        recommendations.append(
            SchemeRecommendation(
                scheme=scheme,
                relevance_score=score,
                eligible=eligibility.eligible,
                summary=summary,
                factors=factors,
                match_status=match_status,
            )
        )

    if eligible_only:
        recommendations = [r for r in recommendations if r.eligible]

    if sort_by == "name":
        recommendations.sort(key=lambda r: r.scheme.name.lower())
    else:
        # "score" and "eligibility" both use the same key; "eligibility" is
        # effectively the default behaviour (eligible first, then by score).
        recommendations.sort(
            key=lambda r: (r.eligible, r.relevance_score, r.scheme.name),
            reverse=True,
        )

    return recommendations[:limit]
