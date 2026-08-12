"""
Scheme record deduplicator.

Determines for each NormalizedScheme whether it is:
  NEW       — no existing row with this (source, external_id)
  UPDATED   — row exists but at least one field differs
  UNCHANGED — row exists and all fields are identical
  DUPLICATE — the same external_id appeared twice in this import batch

Rules enforced here:
  - Never hard-deletes records during synchronisation.
  - Does not overwrite is_active=True records with is_active=False
    unless the source explicitly signals deactivation.
  - Manual records (source IS NULL or source='manual') are never
    touched by the deduplicator.
"""
from __future__ import annotations

import logging
from enum import Enum

from sqlalchemy.orm import Session

from app.importers.models import NormalizedScheme, RecordOutcome
from app.models.scheme import GovernmentScheme

logger = logging.getLogger(__name__)

# Fields that are compared to decide whether an UPDATE is needed.
# We deliberately exclude: id, is_active, created_at, updated_at.
_COMPARABLE_FIELDS = [
    "name",
    "short_description",
    "detailed_description",
    "department",
    "state",
    "scheme_type",
    "benefits",
    "application_process",
    "official_website",
    "ministry",
    "beneficiary_type",
    "coverage_type",
    "geo_scope",
    "tags",
    "eligibility_notes",
    "documents_required",
    "source_url",
]


class DedupResult(str, Enum):
    NEW = RecordOutcome.NEW.value
    UPDATED = RecordOutcome.UPDATED.value
    UNCHANGED = RecordOutcome.UNCHANGED.value
    DUPLICATE = RecordOutcome.DUPLICATE.value


def check(
    normalized: NormalizedScheme,
    db: Session,
    seen_ids: set[str],
) -> tuple[DedupResult, GovernmentScheme | None]:
    """
    Compare a NormalizedScheme against the database and the current-batch
    seen_ids set.

    Parameters
    ----------
    normalized : the record to check
    db         : SQLAlchemy session (read-only in this function)
    seen_ids   : external_ids already processed in this import batch
                 (prevents processing duplicates within a single run)

    Returns
    -------
    (DedupResult, existing_row_or_None)
    """
    batch_key = f"{normalized.source}:{normalized.external_id}"

    if batch_key in seen_ids:
        return DedupResult.DUPLICATE, None

    existing: GovernmentScheme | None = (
        db.query(GovernmentScheme)
        .filter(
            GovernmentScheme.source == normalized.source,
            GovernmentScheme.external_id == normalized.external_id,
        )
        .first()
    )

    if existing is None:
        return DedupResult.NEW, None

    # Check whether any comparable field has changed
    for field_name in _COMPARABLE_FIELDS:
        old_val = getattr(existing, field_name, None)
        new_val = getattr(normalized, field_name, None)
        # Normalise empty string → None for comparison
        if old_val == "":
            old_val = None
        if new_val == "":
            new_val = None
        if old_val != new_val:
            logger.debug(
                "[DEDUP] source=%s external_id=%s field '%s' changed: %r → %r",
                normalized.source,
                normalized.external_id,
                field_name,
                old_val,
                new_val,
            )
            return DedupResult.UPDATED, existing

    return DedupResult.UNCHANGED, existing
