"""
GraphRAG service — fuses Qdrant vector retrieval with Neo4j graph retrieval.

Architecture:
    User query
        │
        ├─── Qdrant vector search  →  document chunks (semantic similarity)
        │
        └─── Neo4j graph search    →  structured entity relationships
                                        (scheme→state, scheme→crop, document→scheme)
        │
        └─── Context fusion → combined context string for Gemini

Design rules:
- Qdrant pipeline is NEVER replaced. If Neo4j is unavailable, the system
  transparently falls back to Qdrant-only RAG (same as before this phase).
- Graph context never overrides deterministic eligibility results.
- Source provenance is preserved for every piece of context.
- No graph relationships are fabricated. Retrieval is purely query-driven.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.ai.neo4j.client import GraphDatabaseError, GraphDatabaseUnavailableError
from app.ai.neo4j.repository import get_graph_context_for_query
from app.rag.rag_service import RagResult, try_search_knowledge_base

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class GraphRagResult:
    """Combined result from Qdrant + Neo4j retrieval."""

    # Fused context string ready to inject into Gemini system instruction
    context: str

    # Human-readable source labels
    sources: list[str] = field(default_factory=list)

    # Structured raw sources for API responses
    raw_sources: list[dict] = field(default_factory=list)

    # Whether graph retrieval contributed anything
    graph_used: bool = False

    # Whether vector retrieval contributed anything
    vector_used: bool = False


# ---------------------------------------------------------------------------
# Context formatters
# ---------------------------------------------------------------------------

def _format_graph_context(graph_results: list[dict]) -> str:
    """
    Format Neo4j results into a clearly labelled context block.
    Only includes fields that are actually present — no invented data.
    """
    if not graph_results:
        return ""

    sections: list[str] = ["GRAPH KNOWLEDGE:"]

    for item in graph_results:
        name = item.get("scheme_name") or item.get("name", "Unknown Scheme")
        scheme_id = item.get("scheme_id")
        department = item.get("department", "")
        scheme_type = item.get("scheme_type", "")
        match_reason = item.get("match_reason", "")

        header_parts = [f"[Scheme] {name}"]
        if scheme_id:
            header_parts.append(f"ID: {scheme_id}")
        if department:
            header_parts.append(f"Department: {department}")
        if scheme_type:
            header_parts.append(f"Type: {scheme_type}")
        if match_reason:
            header_parts.append(f"Matched by: {match_reason}")

        sections.append("\n".join(header_parts))

        # Relationships — only emit when non-empty
        relationships: list[str] = []

        states = [s for s in (item.get("states") or []) if s]
        if states:
            for st in states:
                relationships.append(f"  {name} → AVAILABLE_IN → {st}")

        crops = [c for c in (item.get("crops") or []) if c]
        if crops:
            for cr in crops:
                relationships.append(f"  {name} → TARGETS_CROP → {cr}")

        categories = [c for c in (item.get("categories") or []) if c]
        if categories:
            for cat in categories:
                relationships.append(f"  {name} → BELONGS_TO → {cat}")

        documents = [d for d in (item.get("documents") or []) if d]
        if documents:
            for doc in documents:
                relationships.append(f"  {name} → DESCRIBED_BY → {doc}")

        if relationships:
            sections.append("[Relationships]")
            sections.extend(relationships)

        sections.append("[Source] Neo4j\n")

    sections.extend([
        "STRICT RULES (Graph context):",
        "- Graph relationships describe what JanSahay has indexed — not official government records.",
        "- Do not invent relationships not shown above.",
        "- Do not override deterministic eligibility results.",
    ])

    return "\n".join(sections)


def _merge_contexts(
    vector_context: str,
    graph_context: str,
) -> str:
    """
    Combine vector and graph context into a single string.
    Each section is clearly labelled.
    """
    parts: list[str] = []
    if graph_context:
        parts.append(graph_context)
    if vector_context:
        parts.append(vector_context)
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Main retrieval functions
# ---------------------------------------------------------------------------

def graph_rag_search(
    query: str,
    *,
    state: str | None = None,
    crop: str | None = None,
    scheme_ids: list[int] | None = None,
    top_k: int = 5,
) -> GraphRagResult:
    """
    Perform fused Qdrant + Neo4j retrieval for a query.

    Parameters
    ----------
    query     : The user's natural-language query.
    state     : Optional farmer state (extracted from profile or message).
    crop      : Optional primary crop (extracted from profile or message).
    scheme_ids: Optional list of specific scheme IDs to include graph context for.
    top_k     : Number of Qdrant results.

    Returns
    -------
    GraphRagResult with combined context and provenance.
    Falls back to Qdrant-only on Neo4j unavailability.
    """
    vector_context = ""
    graph_context = ""
    sources: list[str] = []
    raw_sources: list[dict] = []
    graph_used = False
    vector_used = False

    # ── 1. Qdrant vector search ─────────────────────────────────────────────
    try:
        qdrant_result: RagResult | None = try_search_knowledge_base(query, top_k=top_k)
        if qdrant_result is not None:
            vector_context = qdrant_result.context
            sources.extend(qdrant_result.sources)
            raw_sources.extend(qdrant_result.raw_sources)
            vector_used = True
    except Exception as exc:
        logger.warning("GraphRAG: Qdrant search failed: %s", exc)

    # ── 2. Neo4j graph search ────────────────────────────────────────────────
    try:
        graph_results = get_graph_context_for_query(
            state=state,
            crop=crop,
            scheme_ids=scheme_ids or [],
        )
        if graph_results:
            graph_context = _format_graph_context(graph_results)
            for item in graph_results:
                label = item.get("scheme_name") or item.get("name")
                if label and label not in sources:
                    sources.append(f"{label} [graph]")
            graph_used = True
            logger.debug("GraphRAG: Neo4j returned %d graph results", len(graph_results))
    except GraphDatabaseUnavailableError as exc:
        logger.warning("GraphRAG: Neo4j unavailable — falling back to Qdrant only: %s", exc)
    except GraphDatabaseError as exc:
        logger.warning("GraphRAG: Neo4j query failed — falling back to Qdrant only: %s", exc)
    except Exception as exc:
        logger.warning("GraphRAG: unexpected graph error: %s", exc)

    # ── 3. Fuse contexts ─────────────────────────────────────────────────────
    combined_context = _merge_contexts(vector_context, graph_context)

    return GraphRagResult(
        context=combined_context,
        sources=list(dict.fromkeys(sources)),  # deduplicate, preserve order
        raw_sources=raw_sources,
        graph_used=graph_used,
        vector_used=vector_used,
    )


def try_graph_rag_search(
    query: str,
    *,
    state: str | None = None,
    crop: str | None = None,
    scheme_ids: list[int] | None = None,
    top_k: int = 5,
) -> GraphRagResult | None:
    """
    Like graph_rag_search but returns None if both retrieval paths return nothing.
    Safe to use as a direct drop-in for try_search_knowledge_base in contexts
    that accept an optional result.
    """
    try:
        result = graph_rag_search(
            query,
            state=state,
            crop=crop,
            scheme_ids=scheme_ids,
            top_k=top_k,
        )
    except Exception as exc:
        logger.warning("GraphRAG: search failed entirely: %s", exc)
        return None

    if not result.context:
        return None
    return result
