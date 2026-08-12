from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.models.farmer_profile import FarmerProfile
from app.models.scheme_eligibility import SchemeEligibilityCriterion

SUPPORTED_OPERATORS = frozenset(
    {
        "equals",
        "not_equals",
        "greater_than",
        "greater_than_or_equal",
        "less_than",
        "less_than_or_equal",
        "contains",
        "in",
    }
)

PROFILE_FIELD_ALIASES = {
    "age": "age",
    "gender": "gender",
    "state": "state",
    "district": "district",
    "category": "land_ownership",
    "land_holding": "land_size",
    "annual_income": "annual_income",
    "occupation": "farming_type",
    "farming_type": "farming_type",
    "crop_type": "primary_crop",
    "irrigation_status": "irrigation_type",
    "farmer_category": "land_ownership",
    "land_size": "land_size",
    "primary_crop": "primary_crop",
    "irrigation_type": "irrigation_type",
    "land_ownership": "land_ownership",
}

FIELD_LABELS = {
    "age": "Age",
    "gender": "Gender",
    "state": "State",
    "district": "District",
    "category": "Category",
    "land_holding": "Land holding",
    "annual_income": "Annual income",
    "occupation": "Occupation",
    "farming_type": "Farming type",
    "crop_type": "Crop type",
    "irrigation_status": "Irrigation status",
    "farmer_category": "Farmer category",
}


@dataclass
class EligibilityResult:
    eligible: bool
    reasons: list[str]


def _calculate_age(date_of_birth: date | None) -> int | None:
    if date_of_birth is None:
        return None
    today = date.today()
    age = today.year - date_of_birth.year
    if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
        age -= 1
    return age


def _get_profile_value(profile: FarmerProfile, field_name: str) -> object | None:
    profile_field = PROFILE_FIELD_ALIASES.get(field_name, field_name)
    if profile_field == "age":
        return _calculate_age(profile.date_of_birth)
    return getattr(profile, profile_field, None)


def _normalize_string(value: object) -> str:
    return str(value).strip().lower()


def _parse_numeric(value: str) -> Decimal | None:
    try:
        return Decimal(value.strip())
    except Exception:
        return None


def _compare_values(
    actual: object | None,
    expected: str,
    operator: str,
) -> bool:
    if actual is None:
        return False

    if operator in {"equals", "not_equals"}:
        if isinstance(actual, (int, float, Decimal)):
            expected_num = _parse_numeric(expected)
            if expected_num is not None:
                result = Decimal(str(actual)) == expected_num
            else:
                result = _normalize_string(actual) == _normalize_string(expected)
        else:
            result = _normalize_string(actual) == _normalize_string(expected)
        return not result if operator == "not_equals" else result

    if operator in {
        "greater_than",
        "greater_than_or_equal",
        "less_than",
        "less_than_or_equal",
    }:
        actual_num = Decimal(str(actual)) if not isinstance(actual, Decimal) else actual
        expected_num = _parse_numeric(expected)
        if expected_num is None:
            return False
        if operator == "greater_than":
            return actual_num > expected_num
        if operator == "greater_than_or_equal":
            return actual_num >= expected_num
        if operator == "less_than":
            return actual_num < expected_num
        return actual_num <= expected_num

    if operator == "contains":
        return _normalize_string(expected) in _normalize_string(actual)

    if operator == "in":
        allowed = {_normalize_string(part) for part in expected.split(",")}
        return _normalize_string(actual) in allowed

    return False


def _build_reason(
    criterion: SchemeEligibilityCriterion,
    passed: bool,
    actual: object | None,
) -> str:
    label = FIELD_LABELS.get(criterion.field_name, criterion.field_name.replace("_", " ").title())
    if criterion.description:
        base = criterion.description.strip()
        if passed:
            return f"{base} (requirement satisfied)."
        return f"{base} (requirement not satisfied)."

    operator = criterion.operator
    expected = criterion.expected_value

    if passed:
        if operator == "equals":
            return f"{label} matches the scheme requirement ({expected})."
        if operator == "not_equals":
            return f"{label} satisfies the scheme exclusion rule."
        if operator in {"greater_than", "greater_than_or_equal"}:
            return f"{label} satisfies the minimum required value."
        if operator in {"less_than", "less_than_or_equal"}:
            return f"{label} is within the allowed limit."
        if operator == "contains":
            return f"{label} includes the required value."
        if operator == "in":
            return f"{label} is among the eligible values."
        return f"{label} satisfies the scheme requirement."

    if actual is None:
        return f"{label} is missing from your farmer profile."

    if operator == "equals":
        return f"{label} does not match the required value ({expected})."
    if operator == "not_equals":
        return f"{label} matches an excluded value ({expected})."
    if operator in {"greater_than", "greater_than_or_equal"}:
        return f"{label} is below the minimum required value ({expected})."
    if operator in {"less_than", "less_than_or_equal"}:
        return f"{label} exceeds the maximum allowed value ({expected})."
    if operator == "contains":
        return f"{label} does not include the required value ({expected})."
    if operator == "in":
        return f"{label} is not among the eligible values ({expected})."
    return f"{label} does not satisfy the scheme requirement."


def evaluate_criterion(
    profile: FarmerProfile,
    criterion: SchemeEligibilityCriterion,
) -> tuple[bool, str]:
    actual = _get_profile_value(profile, criterion.field_name)
    operator = criterion.operator.strip().lower()

    if operator not in SUPPORTED_OPERATORS:
        return False, f"Unsupported eligibility operator: {criterion.operator}"

    if actual is None:
        return False, _build_reason(criterion, False, actual)

    passed = _compare_values(actual, criterion.expected_value, operator)
    return passed, _build_reason(criterion, passed, actual)


def evaluate_eligibility(
    profile: FarmerProfile,
    criteria: list[SchemeEligibilityCriterion],
) -> EligibilityResult:
    if not criteria:
        return EligibilityResult(
            eligible=True,
            reasons=["No specific eligibility criteria are defined for this scheme."],
        )

    reasons: list[str] = []
    all_passed = True

    for criterion in criteria:
        passed, reason = evaluate_criterion(profile, criterion)
        reasons.append(reason)
        if not passed:
            all_passed = False

    return EligibilityResult(eligible=all_passed, reasons=reasons)
