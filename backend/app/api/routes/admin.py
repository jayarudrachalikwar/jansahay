"""
Admin document management routes.

All endpoints require JWT authentication + admin role.
Farmers receive 403 via the require_admin dependency.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.database.session import get_db
from app.models.document import DocumentStatus
from app.models.user import User
from app.rag.vector_store import (
    VectorStoreUnavailableError,
    collection_point_count,
    count_document_vectors,
    get_qdrant_client,
)
from app.schemas.document import (
    DocumentChunkStats,
    DocumentListResponse,
    DocumentResponse,
    DocumentStatusUpdateRequest,
    KnowledgeBaseStats,
)
from app.services.document_service import (
    DocumentDeletionError,
    DocumentIngestionError,
    DocumentNotFoundError,
    DocumentValidationError,
    activate_document,
    deactivate_document,
    delete_document,
    get_document_or_404,
    ingest_document,
    list_documents,
    save_uploaded_document,
    search_documents,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# POST /admin/documents  — upload a PDF
# ---------------------------------------------------------------------------

@router.post(
    "/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    """
    Upload a PDF document.
    - Rejects non-PDF files (content-type + magic bytes)
    - Rejects oversized files (configurable via MAX_UPLOAD_SIZE_MB)
    - Stores document with a server-generated safe filename
    - Does NOT ingest immediately — call POST /admin/documents/{id}/ingest
    """
    file_bytes = await file.read()
    original_filename = file.filename or "upload.pdf"
    content_type = file.content_type or "application/octet-stream"

    try:
        doc = save_uploaded_document(
            db,
            original_filename=original_filename,
            content_type=content_type,
            file_bytes=file_bytes,
        )
    except DocumentValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return DocumentResponse.model_validate(doc)


# ---------------------------------------------------------------------------
# GET /admin/documents  — list / search / filter documents
# ---------------------------------------------------------------------------

@router.get("/documents", response_model=DocumentListResponse)
def list_all_documents(
    status: str | None = Query(default=None, description="Filter by document status"),
    search: str | None = Query(default=None, description="Search by original filename"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> DocumentListResponse:
    """
    Return managed documents (metadata only, no content).

    Optional query parameters:
    - status: one of uploaded | processing | indexed | failed | inactive
    - search: case-insensitive substring match on original_filename

    When neither parameter is supplied the behaviour is identical to Phase 7
    (returns all documents, newest first).
    """
    docs = search_documents(db, status_filter=status, search=search)
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(doc) for doc in docs],
        total=len(docs),
    )


# ---------------------------------------------------------------------------
# GET /admin/knowledge-base/stats  — KB health overview
# NOTE: must be declared BEFORE /documents/{document_id} to avoid FastAPI
#       treating "knowledge-base" as a path parameter value.
# ---------------------------------------------------------------------------

@router.get("/knowledge-base/stats", response_model=KnowledgeBaseStats)
def knowledge_base_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> KnowledgeBaseStats:
    """
    Return aggregate knowledge-base statistics:
    - total document count
    - documents grouped by status
    - total indexed chunks (Qdrant collection total)
    - whether Qdrant is reachable
    """
    # Document counts from PostgreSQL
    all_docs = list_documents(db)
    total_documents = len(all_docs)

    by_status: dict[str, int] = {s.value: 0 for s in DocumentStatus}
    for doc in all_docs:
        by_status[doc.status.value] = by_status.get(doc.status.value, 0) + 1

    # Qdrant stats — graceful degradation when unavailable
    total_indexed_chunks = 0
    qdrant_reachable = False
    try:
        client = get_qdrant_client()
        total_indexed_chunks = collection_point_count(client)
        qdrant_reachable = True
    except VectorStoreUnavailableError:
        pass

    return KnowledgeBaseStats(
        total_documents=total_documents,
        by_status=by_status,
        total_indexed_chunks=total_indexed_chunks,
        qdrant_reachable=qdrant_reachable,
    )


# ---------------------------------------------------------------------------
# GET /admin/documents/{id}  — document detail
# ---------------------------------------------------------------------------

@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document_detail(
    document_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    """Return metadata for a single document."""
    try:
        doc = get_document_or_404(db, document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return DocumentResponse.model_validate(doc)


# ---------------------------------------------------------------------------
# GET /admin/documents/{id}/chunks  — per-document Qdrant chunk count
# ---------------------------------------------------------------------------

@router.get("/documents/{document_id}/chunks", response_model=DocumentChunkStats)
def get_document_chunks(
    document_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> DocumentChunkStats:
    """
    Return the number of Qdrant vectors indexed for this document and the
    total collection size.  Returns chunk_count=0 when Qdrant is unavailable
    rather than raising, so the UI can degrade gracefully.
    """
    try:
        doc = get_document_or_404(db, document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    chunk_count = 0
    collection_total = 0
    try:
        client = get_qdrant_client()
        chunk_count = count_document_vectors(client, doc.document_id)
        collection_total = collection_point_count(client)
    except VectorStoreUnavailableError:
        pass

    return DocumentChunkStats(
        document_id=doc.document_id,
        chunk_count=chunk_count,
        collection_total=collection_total,
    )


# ---------------------------------------------------------------------------
# PATCH /admin/documents/{id}/status  — activate / deactivate
# ---------------------------------------------------------------------------

@router.patch("/documents/{document_id}/status", response_model=DocumentResponse)
def update_document_status(
    document_id: int,
    body: DocumentStatusUpdateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    """
    Activate or deactivate a document.
    Deactivation marks the record inactive — does not delete the file
    or remove Qdrant vectors.
    """
    try:
        if body.is_active:
            doc = activate_document(db, document_id)
        else:
            doc = deactivate_document(db, document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return DocumentResponse.model_validate(doc)


# ---------------------------------------------------------------------------
# POST /admin/documents/{id}/ingest  — run / re-run ingestion
# ---------------------------------------------------------------------------

@router.post("/documents/{document_id}/ingest", response_model=DocumentResponse)
def ingest_document_endpoint(
    document_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    """
    Run (or re-run) ingestion for a document through the Phase 6 RAG pipeline:
    PDF → pypdf → chunking → Gemini embeddings → Qdrant

    Re-ingestion is safe: deterministic point IDs mean existing Qdrant vectors
    for this document are replaced, not duplicated.

    Returns the updated document metadata (status will be 'indexed' on success
    or 'failed' with error_message on failure).
    """
    try:
        doc = ingest_document(db, document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except DocumentIngestionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return DocumentResponse.model_validate(doc)


# ---------------------------------------------------------------------------
# DELETE /admin/documents/{id}  — hard delete with Qdrant + file cleanup
# ---------------------------------------------------------------------------

@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_document_endpoint(
    document_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    """
    Permanently delete a document.

    Deletion order (safe transaction-like):
      1. Remove Qdrant vectors scoped to this document's document_id.
      2. Remove the physical uploaded file (missing file is non-fatal).
      3. Delete the PostgreSQL record and commit.

    If Qdrant cleanup fails the DB record is NOT removed and HTTP 503 is
    returned so the caller can retry.
    """
    try:
        delete_document(db, document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except DocumentDeletionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
