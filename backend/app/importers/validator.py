"""
Scheme record validator.

Validates a NormalizedScheme before persistence.
Returns a list of validation errors (empty = valid).
"""
from __future__ import annotations

from app.importers.models import NormalizedScheme

_MAX_LENGTHS = {
    "name": 255,
    "short_description": 500,
    "department": 255,
    "state": 100,
    "scheme_type": 100,
    "external_id": 200,
    "source": 50,
    "ministry": 255,
    "beneficiary_type": 500,
    "coverage_type": 50,
    "geo_scope": 50,
    "official_website": 500,
    "source_url": 1000,
}

_REQUIRED_FIELDS = [
    "name",
    "short_description",
    "detailed_description",
    "department",
    "state",
    "scheme_type",
    "benefits",
    "application_process",
    "external_id",
    "source",
]

_ALLOWED_COVERAGE_TYPES = {"central", "state", "centrally_sponsored", "ut", "unknown", None}
_ALLOWED_GEO_SCOPES = {"national", "state", "district", "block", "unknown", None}


def validate(scheme: NormalizedScheme) -> list[str]:
    """
    Return a list of validation error strings.
    Empty list means the record is valid.
    """
    errors: list[str] = []

    # Required fields
    for field in _REQUIRED_FIELDS:
        value = getattr(scheme, field, None)
        if not value or (isinstance(value, str) and not value.strip()):
            errors.append(f"Required field '{field}' is missing or empty.")

    # Length checks
    for field, limit in _MAX_LENGTHS.items():
        value = getattr(scheme, field, None)
        if isinstance(value, str) and len(value) > limit:
            errors.append(
                f"Field '{field}' exceeds maximum length ({len(value)} > {limit})."
            )

    # Controlled vocabulary
    if scheme.coverage_type not in _ALLOWED_COVERAGE_TYPES:
        errors.append(
            f"Invalid coverage_type '{scheme.coverage_type}'. "
            f"Allowed: {sorted(v for v in _ALLOWED_COVERAGE_TYPES if v)}."
        )

    if scheme.geo_scope not in _ALLOWED_GEO_SCOPES:
        errors.append(
            f"Invalid geo_scope '{scheme.geo_scope}'. "
            f"Allowed: {sorted(v for v in _ALLOWED_GEO_SCOPES if v)}."
        )

    # URL sanity check (non-empty must start with http)
    for url_field in ("official_website", "source_url"):
        url = getattr(scheme, url_field, None)
        if url and not url.startswith(("http://", "https://")):
            errors.append(f"Field '{url_field}' does not look like a URL: '{url[:80]}'.")

    return errors
