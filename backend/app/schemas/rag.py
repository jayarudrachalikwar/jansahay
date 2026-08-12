from typing import Any

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Existing Qdrant-only search schemas (unchanged)
# ---------------------------------------------------------------------------

class RagSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Query cannot be empty")
        return stripped


class RagSearchResultItem(BaseModel):
    text: str
    filename: str
    page_number: int
    chunk_index: int
    score: float


class RagSearchResponse(BaseModel):
    results: list[RagSearchResultItem]
    total: int


# ---------------------------------------------------------------------------
# Phase 13 — Neo4j graph search
# ---------------------------------------------------------------------------

class GraphSearchRequest(BaseModel):
    """
    Request body for POST /api/rag/graph-search.
    Filters are applied to the graph database only — no LLM inference.
    """

    state: str | None = Field(
        default=None,
        max_length=100,
        description="Filter schemes by this state name (e.g. 'Telangana').",
    )
    crop: str | None = Field(
        default=None,
        max_length=100,
        description="Filter schemes targeting this crop (e.g. 'cotton').",
    )
    scheme_ids: list[int] | None = Field(
        default=None,
        description="Optional list of specific scheme IDs to fetch graph context for.",
    )


class GraphSearchResponse(BaseModel):
    results: list[dict[str, Any]]
    total: int


# ---------------------------------------------------------------------------
# Phase 13 — GraphRAG (Qdrant + Neo4j fused)
# ---------------------------------------------------------------------------

class GraphRagRequest(BaseModel):
    """
    Request body for POST /api/rag/graph-rag.
    Performs fused Qdrant vector + Neo4j graph retrieval.
    """

    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)
    state: str | None = Field(
        default=None,
        max_length=100,
        description="Optional state context for graph retrieval.",
    )
    crop: str | None = Field(
        default=None,
        max_length=100,
        description="Optional crop context for graph retrieval.",
    )
    scheme_ids: list[int] | None = Field(
        default=None,
        description="Optional specific scheme IDs to include graph context for.",
    )

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Query cannot be empty")
        return stripped


class GraphRagResponse(BaseModel):
    context: str
    sources: list[str]
    raw_sources: list[dict[str, Any]]
    graph_used: bool
    vector_used: bool
