"""
Graph ingestion service for JanSahay.

Converts PostgreSQL domain objects into graph nodes and relationships.
All operations are idempotent (MERGE-based).

Rules:
- Never fabricate data. Every field written to Neo4j maps to a real
  PostgreSQL column on the corresponding SQLAlchemy model.
- Only create crop/category relationships when eligibility criteria
  explicitly reference them.
- Only create DESCRIBES relationships when we have evidence linking
  a document to a specific scheme (currently: not yet implemented —
  document→scheme linking requires explicit admin tagging or
  a post-ingestion linking step).
- Gracefully handles Neo4j unavailability — callers get a
  GraphDatabaseUnavailableError, never a driver crash.
"""
from __future__ import annotations

import logging

from app.ai.neo4j.client import GraphDatabaseError, GraphDatabaseUnavailableError
from app.ai.neo4j.models import DocumentNode, FarmerNode, SchemeNode
from app.ai.neo4j.repository import (
    delete_document_node,
    upsert_document,
    upsert_farmer,
    upsert_scheme,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Field names in SchemeEligibilityCriterion that map to crops / categories
# ---------------------------------------------------------------------------
_CROP_FIELDS = frozenset({"crop_type", "primary_crop", "crop"})
_CATEGORY_FIELDS = frozenset({"category", "farmer_category", "land_ownership", "occupation", "farming_type"})


def _extract_crop_values(criteria: list) -> list[str]:
    """
    Return normalised crop values found in eligibility criteria.
    Handles comma-separated expected_value strings (e.g. "rice,wheat").
    """
    crops: list[str] = []
    for criterion in criteria:
        if criterion.field_name.lower() in _CROP_FIELDS:
            for part in criterion.expected_value.split(","):
                val = part.strip()
                if val:
                    crops.append(val)
    return list(dict.fromkeys(crops))   # deduplicate, preserve order


def _extract_category_values(criteria: list) -> list[str]:
    """Return normalised category/type values from eligibility criteria."""
    cats: list[str] = []
    for criterion in criteria:
        if criterion.field_name.lower() in _CATEGORY_FIELDS:
            for part in criterion.expected_value.split(","):
                val = part.strip()
                if val:
                    cats.append(val)
    return list(dict.fromkeys(cats))


# ---------------------------------------------------------------------------
# Domain-level ingestion functions
# ---------------------------------------------------------------------------

def ingest_scheme(scheme) -> None:
    """
    Ingest a GovernmentScheme SQLAlchemy object into Neo4j.
    Includes state, scheme_type, and any crop/category relationships
    derivable from the scheme's eligibility criteria.

    Parameters
    ----------
    scheme : GovernmentScheme
        Must have .eligibility_criteria loaded (eager or lazy-loaded).
    """
    criteria = list(scheme.eligibility_criteria or [])
    target_crops = _extract_crop_values(criteria)
    target_categories = _extract_category_values(criteria)

    node = SchemeNode(
        scheme_id=scheme.id,
        name=scheme.name,
        department=scheme.department,
        state=scheme.state,
        scheme_type=scheme.scheme_type,
        is_active=scheme.is_active,
        target_crops=target_crops,
        target_categories=target_categories,
    )
    try:
        upsert_scheme(node)
        logger.debug("Graph: upserted Scheme(%d) %s", scheme.id, scheme.name)
    except GraphDatabaseUnavailableError:
        logger.warning("Graph: Neo4j unavailable — skipping scheme ingestion for %s", scheme.name)
        raise
    except GraphDatabaseError as exc:
        logger.error("Graph: failed to upsert scheme %s: %s", scheme.name, exc)
        raise


def ingest_farmer_profile(profile) -> None:
    """
    Ingest a FarmerProfile SQLAlchemy object into Neo4j.

    Parameters
    ----------
    profile : FarmerProfile
        Must have .user_id, .state, .district, .primary_crop, etc.
    """
    node = FarmerNode(
        user_id=profile.user_id,
        state=profile.state,
        district=profile.district,
        primary_crop=profile.primary_crop,
        secondary_crop=profile.secondary_crop,
        land_ownership=profile.land_ownership,
        farming_type=profile.farming_type,
    )
    try:
        upsert_farmer(node)
        logger.debug("Graph: upserted Farmer(user_id=%d)", profile.user_id)
    except GraphDatabaseUnavailableError:
        logger.warning(
            "Graph: Neo4j unavailable — skipping farmer ingestion for user_id=%d",
            profile.user_id,
        )
        raise
    except GraphDatabaseError as exc:
        logger.error("Graph: failed to upsert farmer user_id=%d: %s", profile.user_id, exc)
        raise


def ingest_document_metadata(document, scheme_ids: list[int] | None = None) -> None:
    """
    Ingest a GovernmentDocument SQLAlchemy object into Neo4j.

    Parameters
    ----------
    document : GovernmentDocument
        Must have .document_id, .filename, .original_filename.
    scheme_ids : list[int] | None
        PostgreSQL scheme IDs that this document is explicitly linked to.
        Pass an empty list or None when no scheme linkage is known.
        Never infer or hallucinate links.
    """
    node = DocumentNode(
        document_id=document.document_id,
        filename=document.filename,
        original_filename=document.original_filename,
        scheme_ids=scheme_ids or [],
    )
    try:
        upsert_document(node)
        logger.debug(
            "Graph: upserted Document(%s) with %d scheme links",
            document.document_id[:8],
            len(node.scheme_ids),
        )
    except GraphDatabaseUnavailableError:
        logger.warning(
            "Graph: Neo4j unavailable — skipping document ingestion for %s",
            document.original_filename,
        )
        raise
    except GraphDatabaseError as exc:
        logger.error(
            "Graph: failed to upsert document %s: %s",
            document.original_filename,
            exc,
        )
        raise


def remove_document_from_graph(document_id: str) -> None:
    """
    Remove a Document node (and all its relationships) from Neo4j.
    Called when a document is hard-deleted from the admin portal.
    Swallows unavailability errors gracefully — PostgreSQL deletion still proceeds.
    """
    try:
        delete_document_node(document_id)
        logger.debug("Graph: deleted Document(%s)", document_id[:8])
    except GraphDatabaseUnavailableError:
        logger.warning(
            "Graph: Neo4j unavailable — document %s was not removed from graph.",
            document_id[:8],
        )
    except GraphDatabaseError as exc:
        logger.error("Graph: failed to remove document %s: %s", document_id[:8], exc)


def bulk_ingest_schemes(schemes: list) -> tuple[int, int]:
    """
    Ingest a list of GovernmentScheme objects.
    Returns (success_count, failure_count).
    """
    success = 0
    failure = 0
    for scheme in schemes:
        try:
            ingest_scheme(scheme)
            success += 1
        except (GraphDatabaseError, GraphDatabaseUnavailableError):
            failure += 1
    logger.info("Graph bulk ingest: %d schemes OK, %d failed", success, failure)
    return success, failure
