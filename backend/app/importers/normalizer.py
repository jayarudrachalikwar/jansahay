"""
Scheme record normalizer.

Converts a RawSchemeRecord into a NormalizedScheme by:
  - mapping source-specific field names to GovernmentScheme columns
  - enforcing column length limits (with safe truncation + logging)
  - normalizing state/UT names to the canonical JanSahay form
  - extracting beneficiary/coverage metadata
  - preserving unstructured eligibility text (never inventing structure)
  - validating required fields

The normalizer is source-aware: it dispatches to a source-specific
mapping function, then applies shared post-processing.
"""
from __future__ import annotations

import logging
from typing import Any

from app.importers.models import NormalizedScheme, RawSchemeRecord

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Column length limits (must match the migration/model)
# ---------------------------------------------------------------------------

_LIMITS = {
    "name": 255,
    "short_description": 500,
    "department": 255,
    "state": 100,
    "scheme_type": 100,
    "official_website": 500,
    "source_url": 1000,
    "external_id": 200,
    "source": 50,
    "ministry": 255,
    "beneficiary_type": 500,
    "coverage_type": 50,
    "geo_scope": 50,
}

# ---------------------------------------------------------------------------
# State/UT canonicalization map
# ---------------------------------------------------------------------------

_STATE_ALIASES: dict[str, str] = {
    # Canonical "All India" aliases
    "all states": "All India",
    "all states/uts": "All India",
    "pan india": "All India",
    "national": "All India",
    "central": "All India",
    "india": "All India",
    "all": "All India",
    # Common abbreviations / alternate spellings
    "andhra pradesh": "Andhra Pradesh",
    "ap": "Andhra Pradesh",
    "arunachal pradesh": "Arunachal Pradesh",
    "assam": "Assam",
    "bihar": "Bihar",
    "chhattisgarh": "Chhattisgarh",
    "goa": "Goa",
    "gujarat": "Gujarat",
    "haryana": "Haryana",
    "himachal pradesh": "Himachal Pradesh",
    "hp": "Himachal Pradesh",
    "jharkhand": "Jharkhand",
    "karnataka": "Karnataka",
    "kerala": "Kerala",
    "madhya pradesh": "Madhya Pradesh",
    "mp": "Madhya Pradesh",
    "maharashtra": "Maharashtra",
    "manipur": "Manipur",
    "meghalaya": "Meghalaya",
    "mizoram": "Mizoram",
    "nagaland": "Nagaland",
    "odisha": "Odisha",
    "orissa": "Odisha",
    "punjab": "Punjab",
    "rajasthan": "Rajasthan",
    "sikkim": "Sikkim",
    "tamil nadu": "Tamil Nadu",
    "tn": "Tamil Nadu",
    "telangana": "Telangana",
    "tripura": "Tripura",
    "uttar pradesh": "Uttar Pradesh",
    "up": "Uttar Pradesh",
    "uttarakhand": "Uttarakhand",
    "west bengal": "West Bengal",
    "wb": "West Bengal",
    # Union Territories
    "andaman and nicobar islands": "Andaman and Nicobar Islands",
    "chandigarh": "Chandigarh",
    "dadra and nagar haveli and daman and diu": "Dadra and Nagar Haveli and Daman and Diu",
    "delhi": "Delhi",
    "nct of delhi": "Delhi",
    "jammu and kashmir": "Jammu and Kashmir",
    "j&k": "Jammu and Kashmir",
    "ladakh": "Ladakh",
    "lakshadweep": "Lakshadweep",
    "puducherry": "Puducherry",
    "pondicherry": "Puducherry",
}


def normalize_state(raw: str | None) -> str:
    """Return the canonical state name, defaulting to 'All India' if unknown."""
    if not raw or not raw.strip():
        return "All India"
    normalized = _STATE_ALIASES.get(raw.strip().lower())
    if normalized:
        return normalized
    # Return title-cased original if not in the alias map (new UTs, etc.)
    return raw.strip().title()


# ---------------------------------------------------------------------------
# Field truncation
# ---------------------------------------------------------------------------

def _truncate(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    limit = _LIMITS.get(field)
    if limit and len(value) > limit:
        logger.debug(
            "[NORMALIZER] Field '%s' truncated from %d to %d chars", field, len(value), limit
        )
        return value[:limit]
    return value


def _str(raw: Any, default: str = "") -> str:
    if raw is None:
        return default
    return str(raw).strip()


def _join_list(raw: Any, sep: str = ", ") -> str | None:
    """Convert a list of strings to a comma-separated string, or return None."""
    if isinstance(raw, list):
        parts = [str(item).strip() for item in raw if item]
        return sep.join(parts) if parts else None
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


# ---------------------------------------------------------------------------
# Source-specific extractors
# ---------------------------------------------------------------------------

def _extract_fixture(data: dict[str, Any]) -> dict[str, Any]:
    """
    Extract fields from the fixture/myScheme JSON schema.

    Expected keys (based on myScheme portal structure):
      schemeId, schemeName, schemeShortTitle, schemeDescription,
      state, ministry, department, schemeType, beneficiaryType,
      eligibilityCriteria, benefits, applicationProcess,
      documents, tags, schemeUrl
    """
    return {
        "name": _str(data.get("schemeName") or data.get("name")),
        "short_description": _str(
            data.get("schemeShortTitle")
            or data.get("short_description")
            or data.get("schemeName")
            or data.get("name")
        ),
        "detailed_description": _str(
            data.get("schemeDescription")
            or data.get("detailed_description")
            or data.get("description")
        ),
        "department": _str(data.get("department") or data.get("nodal_department")),
        "state": normalize_state(
            _str(data.get("state") or data.get("stateCode") or data.get("stateName"))
        ),
        "scheme_type": _str(
            data.get("schemeType")
            or data.get("scheme_type")
            or data.get("category")
            or "Welfare"
        ),
        "benefits": _str(
            _join_list(data.get("benefits")) or data.get("benefits") or data.get("benefit")
        ),
        "application_process": _str(
            _join_list(data.get("applicationProcess"))
            or data.get("applicationProcess")
            or data.get("application_process")
            or "Apply through official channel."
        ),
        "official_website": _str(data.get("schemeUrl") or data.get("official_website")) or None,
        "ministry": _str(data.get("ministry") or data.get("ministry_name")) or None,
        "beneficiary_type": _join_list(
            data.get("beneficiaryType") or data.get("beneficiary_type")
        ),
        "coverage_type": _infer_coverage_type(data),
        "geo_scope": _infer_geo_scope(data),
        "tags": _join_list(data.get("tags")),
        # Eligibility text preserved as-is — never structurally parsed here
        "eligibility_notes": _str(
            _join_list(data.get("eligibilityCriteria"))
            or data.get("eligibilityCriteria")
            or data.get("eligibility_notes")
        ) or None,
        "documents_required": _join_list(
            data.get("documents") or data.get("requiredDocuments")
        ),
        "source_url": _str(data.get("schemeUrl") or data.get("source_url")) or None,
    }


def _infer_coverage_type(data: dict[str, Any]) -> str | None:
    """Infer coverage_type from available fields."""
    raw = str(data.get("schemeLevel") or data.get("coverage_type") or "").lower()
    if "central" in raw:
        return "central"
    if "state" in raw:
        return "state"
    if "sponsored" in raw:
        return "centrally_sponsored"
    if "ut" in raw:
        return "ut"
    state = str(data.get("state") or "").strip().lower()
    if state in ("all states", "all states/uts", "pan india", "all india", ""):
        return "central"
    return "state"


def _infer_geo_scope(data: dict[str, Any]) -> str | None:
    state = str(data.get("state") or "").strip().lower()
    if state in ("all states", "all states/uts", "pan india", "all india", ""):
        return "national"
    return "state"


# ---------------------------------------------------------------------------
# Main normalizer entry point
# ---------------------------------------------------------------------------

_SOURCE_EXTRACTORS = {
    "fixture": _extract_fixture,
    "myscheme": _extract_fixture,   # myScheme uses the same schema as fixture
    "data_gov_in": _extract_fixture,  # placeholder — map when real API is available
}


def normalize(record: RawSchemeRecord) -> NormalizedScheme | None:
    """
    Normalize a RawSchemeRecord into a NormalizedScheme.

    Returns None if normalization fails for this record.
    Logs the failure reason; caller adds it to the import report.
    """
    extractor = _SOURCE_EXTRACTORS.get(record.source, _extract_fixture)
    try:
        fields = extractor(record.raw_data)
    except Exception as exc:
        logger.warning(
            "[NORMALIZER] source=%s external_id=%s extraction failed: %s",
            record.source, record.external_id, exc,
        )
        return None

    # Apply column length limits
    for field_name in list(_LIMITS.keys()):
        if field_name in fields and isinstance(fields[field_name], str):
            fields[field_name] = _truncate(fields[field_name], field_name)

    # Ensure required text fields are non-empty
    for req in ("name", "department", "benefits", "application_process"):
        if not fields.get(req):
            logger.warning(
                "[NORMALIZER] source=%s external_id=%s missing required field '%s'",
                record.source, record.external_id, req,
            )
            return None

    # Apply limits to Text columns (no hard database limit, but guard anyway)
    for text_field in ("detailed_description", "benefits", "application_process"):
        val = fields.get(text_field, "")
        if val and len(val) > 10_000:
            fields[text_field] = val[:10_000]
            logger.debug("[NORMALIZER] Text field '%s' truncated to 10000 chars", text_field)

    return NormalizedScheme(
        name=fields["name"],
        short_description=fields.get("short_description") or fields["name"][:500],
        detailed_description=fields.get("detailed_description") or fields["name"],
        department=fields["department"],
        state=fields["state"],
        scheme_type=fields.get("scheme_type") or "Welfare",
        benefits=fields["benefits"],
        application_process=fields["application_process"],
        official_website=fields.get("official_website"),
        external_id=record.external_id,
        source=record.source,
        source_url=fields.get("source_url"),
        ministry=fields.get("ministry"),
        beneficiary_type=fields.get("beneficiary_type"),
        coverage_type=fields.get("coverage_type"),
        geo_scope=fields.get("geo_scope"),
        tags=fields.get("tags"),
        eligibility_notes=fields.get("eligibility_notes"),
        documents_required=fields.get("documents_required"),
    )
