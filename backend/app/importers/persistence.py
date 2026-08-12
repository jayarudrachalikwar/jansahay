"""
Scheme persistence layer.

Writes NormalizedScheme records to PostgreSQL.

Safety rules:
  - Never deletes records.
  - Never touches records with source=None or source='manual'.
  - Only updates fields listed in _UPDATE_FIELDS; never changes
    is_active, id, created_at, or the eligibility_criteria relationship.
  - Commits are controlled by the caller, not by these functions.
  - In dry-run mode the caller must not call these functions;
    the pipeline skips them entirely.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.importers.models import NormalizedScheme
from app.models.scheme import GovernmentScheme

logger = logging.getLogger(__name__)

_UPDATE_FIELDS = [
    "name",
    "short_description",
    "detailed_description",
    "department",
    "state",
    "scheme_type",
    "benefits",
    "application_process",
    "official_website",
    "source_url",
    "ministry",
    "beneficiary_type",
    "coverage_type",
    "geo_scope",
    "tags",
    "eligibility_notes",
    "documents_required",
    "last_verified_at",
]


def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def insert(normalized: NormalizedScheme, db: Session) -> GovernmentScheme:
    """
    Insert a new GovernmentScheme row.
    Does NOT commit — the caller controls the transaction.
    """
    row = GovernmentScheme(
        name=normalized.name,
        short_description=normalized.short_description,
        detailed_description=normalized.detailed_description,
        department=normalized.department,
        state=normalized.state,
        scheme_type=normalized.scheme_type,
        benefits=normalized.benefits,
        application_process=normalized.application_process,
        official_website=normalized.official_website,
        is_active=True,
        external_id=normalized.external_id,
        source=normalized.source,
        source_url=normalized.source_url,
        ministry=normalized.ministry,
        beneficiary_type=normalized.beneficiary_type,
        coverage_type=normalized.coverage_type,
        geo_scope=normalized.geo_scope,
        tags=normalized.tags,
        eligibility_notes=normalized.eligibility_notes,
        documents_required=normalized.documents_required,
        last_verified_at=_now_utc(),
    )
    db.add(row)
    logger.debug(
        "[PERSIST] INSERT source=%s external_id=%s name=%r",
        normalized.source, normalized.external_id, normalized.name,
    )
    return row


def update(
    existing: GovernmentScheme,
    normalized: NormalizedScheme,
    db: Session,
) -> GovernmentScheme:
    """
    Update mutable fields on an existing GovernmentScheme row.
    Does NOT commit — the caller controls the transaction.
    """
    setattr(existing, "last_verified_at", _now_utc())

    for field_name in _UPDATE_FIELDS:
        if field_name == "last_verified_at":
            continue  # already handled above
        new_val = getattr(normalized, field_name, None)
        setattr(existing, field_name, new_val)

    logger.debug(
        "[PERSIST] UPDATE source=%s external_id=%s name=%r",
        normalized.source, normalized.external_id, normalized.name,
    )
    return existing
