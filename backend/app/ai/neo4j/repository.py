"""
Neo4j graph repository.

All Cypher is parameterized — no string interpolation of user-controlled values.
Every public function catches Neo4j errors and re-raises as GraphDatabaseError.
Returns plain Python dicts, never neo4j Record objects.
"""
from __future__ import annotations

import logging
from typing import Any

from app.ai.neo4j.client import GraphDatabaseError, GraphDatabaseUnavailableError, get_session
from app.ai.neo4j.models import DocumentNode, FarmerNode, SchemeNode

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Upsert helpers (idempotent MERGE operations)
# ---------------------------------------------------------------------------

def upsert_scheme(scheme: SchemeNode) -> None:
    """
    MERGE a Scheme node and its relationships:
      (:Scheme)-[:AVAILABLE_IN]->(:State)
      (:Scheme)-[:BELONGS_TO]->(:Category)
      (:Scheme)-[:TARGETS_CROP]->(:Crop)
    """
    cypher = """
    MERGE (s:Scheme {scheme_id: $scheme_id})
    SET s.name       = $name,
        s.department = $department,
        s.state      = $state,
        s.scheme_type= $scheme_type,
        s.is_active  = $is_active

    WITH s
    MERGE (st:State {name: $state_name})
    MERGE (s)-[:AVAILABLE_IN]->(st)

    WITH s
    MERGE (cat:Category {name: $category})
    MERGE (s)-[:BELONGS_TO]->(cat)
    """
    params: dict[str, Any] = {
        "scheme_id": scheme.scheme_id,
        "name": scheme.name,
        "department": scheme.department,
        "state": scheme.state,
        "scheme_type": scheme.scheme_type,
        "is_active": scheme.is_active,
        "state_name": scheme.state.strip() or "All India",
        "category": scheme.scheme_type.strip(),
    }

    with get_session() as session:
        session.run(cypher, params)

        # Crop relationships — only if eligibility criteria specify crops
        if scheme.target_crops:
            crop_cypher = """
            MATCH (s:Scheme {scheme_id: $scheme_id})
            UNWIND $crops AS crop_name
            MERGE (c:Crop {name: crop_name})
            MERGE (s)-[:TARGETS_CROP]->(c)
            """
            session.run(crop_cypher, {"scheme_id": scheme.scheme_id, "crops": scheme.target_crops})

        # Category relationships from target_categories (eligibility field values)
        if scheme.target_categories:
            cat_cypher = """
            MATCH (s:Scheme {scheme_id: $scheme_id})
            UNWIND $categories AS cat_name
            MERGE (cat:Category {name: cat_name})
            MERGE (s)-[:BELONGS_TO]->(cat)
            """
            session.run(cat_cypher, {"scheme_id": scheme.scheme_id, "categories": scheme.target_categories})


def upsert_farmer(farmer: FarmerNode) -> None:
    """
    MERGE a Farmer node and its relationships:
      (:Farmer)-[:LOCATED_IN]->(:State)
      (:Farmer)-[:LOCATED_IN]->(:District)
      (:Farmer)-[:GROWS]->(:Crop)
    """
    cypher = """
    MERGE (f:Farmer {user_id: $user_id})
    SET f.land_ownership = $land_ownership,
        f.farming_type   = $farming_type
    """
    params: dict[str, Any] = {
        "user_id": farmer.user_id,
        "land_ownership": farmer.land_ownership,
        "farming_type": farmer.farming_type,
    }
    with get_session() as session:
        session.run(cypher, params)

        if farmer.state:
            session.run(
                """
                MATCH (f:Farmer {user_id: $user_id})
                MERGE (st:State {name: $state})
                MERGE (f)-[:LOCATED_IN]->(st)
                """,
                {"user_id": farmer.user_id, "state": farmer.state.strip()},
            )

        if farmer.district and farmer.state:
            session.run(
                """
                MATCH (f:Farmer {user_id: $user_id})
                MERGE (d:District {name: $district, state_name: $state})
                MERGE (f)-[:LOCATED_IN]->(d)
                """,
                {
                    "user_id": farmer.user_id,
                    "district": farmer.district.strip(),
                    "state": farmer.state.strip(),
                },
            )

        for crop_field in (farmer.primary_crop, farmer.secondary_crop):
            if crop_field:
                session.run(
                    """
                    MATCH (f:Farmer {user_id: $user_id})
                    MERGE (c:Crop {name: $crop})
                    MERGE (f)-[:GROWS]->(c)
                    """,
                    {"user_id": farmer.user_id, "crop": crop_field.strip()},
                )


def upsert_document(doc: DocumentNode) -> None:
    """
    MERGE a Document node and optional DESCRIBES relationships to Schemes.
    Only creates relationships for scheme_ids that are explicitly provided —
    never inferred or hallucinated.
    """
    cypher = """
    MERGE (d:Document {document_id: $document_id})
    SET d.filename          = $filename,
        d.original_filename = $original_filename
    """
    with get_session() as session:
        session.run(
            cypher,
            {
                "document_id": doc.document_id,
                "filename": doc.filename,
                "original_filename": doc.original_filename,
            },
        )

        if doc.scheme_ids:
            session.run(
                """
                MATCH (d:Document {document_id: $document_id})
                UNWIND $scheme_ids AS sid
                MATCH (s:Scheme {scheme_id: sid})
                MERGE (d)-[:DESCRIBES]->(s)
                """,
                {"document_id": doc.document_id, "scheme_ids": doc.scheme_ids},
            )


def delete_document_node(document_id: str) -> None:
    """Remove a Document node and all its relationships from the graph."""
    with get_session() as session:
        session.run(
            "MATCH (d:Document {document_id: $document_id}) DETACH DELETE d",
            {"document_id": document_id},
        )


# ---------------------------------------------------------------------------
# Graph retrieval queries
# ---------------------------------------------------------------------------

def find_schemes_in_state(state: str) -> list[dict[str, Any]]:
    """Return all active Scheme nodes available in the given state."""
    cypher = """
    MATCH (s:Scheme)-[:AVAILABLE_IN]->(st:State {name: $state})
    WHERE s.is_active = true
    RETURN s.scheme_id AS scheme_id,
           s.name      AS scheme_name,
           s.department AS department,
           s.scheme_type AS scheme_type,
           st.name     AS state
    ORDER BY s.name
    """
    with get_session() as session:
        result = session.run(cypher, {"state": state.strip()})
        return [_record_to_dict(r) for r in result]


def find_schemes_for_crop(crop: str) -> list[dict[str, Any]]:
    """Return active Scheme nodes that target the given crop."""
    cypher = """
    MATCH (s:Scheme)-[:TARGETS_CROP]->(c:Crop)
    WHERE toLower(c.name) = toLower($crop)
      AND s.is_active = true
    RETURN s.scheme_id AS scheme_id,
           s.name      AS scheme_name,
           s.department AS department,
           s.scheme_type AS scheme_type,
           c.name      AS crop
    ORDER BY s.name
    """
    with get_session() as session:
        result = session.run(cypher, {"crop": crop.strip()})
        return [_record_to_dict(r) for r in result]


def find_schemes_by_category(category: str) -> list[dict[str, Any]]:
    """Return active Scheme nodes belonging to the given category/type."""
    cypher = """
    MATCH (s:Scheme)-[:BELONGS_TO]->(cat:Category)
    WHERE toLower(cat.name) = toLower($category)
      AND s.is_active = true
    RETURN s.scheme_id AS scheme_id,
           s.name      AS scheme_name,
           s.department AS department,
           cat.name   AS category
    ORDER BY s.name
    """
    with get_session() as session:
        result = session.run(cypher, {"category": category.strip()})
        return [_record_to_dict(r) for r in result]


def get_scheme_graph_context(scheme_id: int) -> dict[str, Any]:
    """
    Return structured graph context for a single scheme:
    available states, target crops, categories, and linked documents.
    """
    cypher = """
    MATCH (s:Scheme {scheme_id: $scheme_id})
    OPTIONAL MATCH (s)-[:AVAILABLE_IN]->(st:State)
    OPTIONAL MATCH (s)-[:TARGETS_CROP]->(c:Crop)
    OPTIONAL MATCH (s)-[:BELONGS_TO]->(cat:Category)
    OPTIONAL MATCH (d:Document)-[:DESCRIBES]->(s)
    RETURN s.scheme_id AS scheme_id,
           s.name      AS scheme_name,
           s.department AS department,
           s.scheme_type AS scheme_type,
           collect(DISTINCT st.name) AS states,
           collect(DISTINCT c.name)  AS crops,
           collect(DISTINCT cat.name) AS categories,
           collect(DISTINCT d.original_filename) AS documents
    """
    with get_session() as session:
        result = session.run(cypher, {"scheme_id": scheme_id})
        record = result.single()
        if record is None:
            return {}
        return _record_to_dict(record)


def find_schemes_for_farmer(
    state: str | None,
    crop: str | None,
) -> list[dict[str, Any]]:
    """
    Find graph-matched schemes for a farmer based on state and/or crop.
    Combines state match + crop match — at least one must be provided.
    Returns deduplicated results.
    """
    if not state and not crop:
        return []

    results: dict[int, dict] = {}

    if state:
        for row in find_schemes_in_state(state):
            sid = row.get("scheme_id")
            if sid is not None:
                results[sid] = {**row, "match_reason": "state"}

    if crop:
        for row in find_schemes_for_crop(crop):
            sid = row.get("scheme_id")
            if sid is not None:
                if sid in results:
                    results[sid]["match_reason"] = "state+crop"
                else:
                    results[sid] = {**row, "match_reason": "crop"}

    return list(results.values())


def find_documents_for_scheme(scheme_id: int) -> list[dict[str, Any]]:
    """Return documents linked to a given scheme."""
    cypher = """
    MATCH (d:Document)-[:DESCRIBES]->(s:Scheme {scheme_id: $scheme_id})
    RETURN d.document_id      AS document_id,
           d.original_filename AS original_filename,
           d.filename          AS filename
    ORDER BY d.original_filename
    """
    with get_session() as session:
        result = session.run(cypher, {"scheme_id": scheme_id})
        return [_record_to_dict(r) for r in result]


def get_graph_context_for_query(
    state: str | None = None,
    crop: str | None = None,
    scheme_ids: list[int] | None = None,
) -> list[dict[str, Any]]:
    """
    Aggregate graph context relevant to a query.
    Combines schemes found by state/crop with their relationship data.
    Used by the GraphRAG fusion layer.
    """
    schemes: list[dict] = []

    # Direct state/crop lookup
    if state or crop:
        schemes = find_schemes_for_farmer(state=state, crop=crop)

    # Enrich with full graph context per matched scheme
    enriched: list[dict] = []
    for scheme in schemes[:8]:   # cap to avoid excessive graph traversal
        sid = scheme.get("scheme_id")
        if sid is not None:
            ctx = get_scheme_graph_context(sid)
            if ctx:
                enriched.append({**scheme, **ctx, "source": "neo4j"})

    # If specific scheme_ids requested, add those too
    if scheme_ids:
        existing_ids = {e.get("scheme_id") for e in enriched}
        for sid in scheme_ids:
            if sid not in existing_ids:
                ctx = get_scheme_graph_context(sid)
                if ctx:
                    enriched.append({**ctx, "source": "neo4j", "match_reason": "direct"})

    return enriched


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _record_to_dict(record: Any) -> dict[str, Any]:
    """Convert a neo4j Record to a plain Python dict."""
    return dict(record)
