from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# Status values must match DocumentStatus enum exactly
DocumentStatusLiteral = Literal["uploaded", "processing", "indexed", "failed", "inactive"]


class DocumentResponse(BaseModel):
    """Full document metadata returned by all admin document endpoints."""

    model_config = {"from_attributes": True}

    id: int
    filename: str
    original_filename: str
    content_type: str
    file_size: int
    page_count: int | None
    document_id: str
    status: DocumentStatusLiteral
    error_message: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    ingested_at: datetime | None


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


class DocumentStatusUpdateRequest(BaseModel):
    """Request body for PATCH /admin/documents/{id}/status."""

    is_active: bool = Field(
        description="Set to false to deactivate, true to reactivate the document."
    )


class DocumentChunkStats(BaseModel):
    """Qdrant vector counts for a single document."""

    document_id: str
    chunk_count: int
    collection_total: int


class KnowledgeBaseStats(BaseModel):
    """Aggregate knowledge-base health stats for the admin dashboard."""

    total_documents: int
    by_status: dict[str, int]
    total_indexed_chunks: int
    qdrant_reachable: bool
