"""
Admin document management service.

Reuses the existing Phase 6 RAG pipeline:
  document_loader → chunker → embeddings → vector_store
No duplicate implementations.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import DocumentStatus, GovernmentDocument
from app.rag.chunker import chunk_pages
from app.rag.document_loader import DocumentLoadError, load_pdf_document
from app.rag.embeddings import EmbeddingAPIError, EmbeddingNotConfiguredError, generate_embeddings_batch
from app.rag.vector_store import (
    VectorStoreOperationError,
    VectorStoreUnavailableError,
    compute_document_id,
    get_qdrant_client,
    upsert_chunks,
)

logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {"application/pdf", "application/x-pdf"}


class DocumentNotFoundError(Exception):
    pass


class DocumentValidationError(Exception):
    pass


class DocumentIngestionError(Exception):
    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _upload_dir() -> Path:
    """Return (and create if needed) the document storage directory."""
    path = settings.document_upload_path
    path.mkdir(parents=True, exist_ok=True)
    return path


def _try_write_to_disk(file_path: Path, file_bytes: bytes) -> bool:
    """Attempt to write file to disk; returns False if filesystem is read-only (e.g. Vercel)."""
    try:
        file_path.write_bytes(file_bytes)
        return True
    except (OSError, PermissionError):
        return False


def _safe_server_filename(original_filename: str) -> str:
    """Generate a UUID-based server filename preserving only the .pdf extension."""
    return f"{uuid.uuid4().hex}.pdf"


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def get_document(db: Session, document_id: int) -> GovernmentDocument | None:
    return db.query(GovernmentDocument).filter(GovernmentDocument.id == document_id).first()


def get_document_or_404(db: Session, document_id: int) -> GovernmentDocument:
    doc = get_document(db, document_id)
    if doc is None:
        raise DocumentNotFoundError(f"Document {document_id} not found")
    return doc


def list_documents(db: Session) -> list[GovernmentDocument]:
    return (
        db.query(GovernmentDocument)
        .order_by(GovernmentDocument.created_at.desc())
        .all()
    )


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

def save_uploaded_document(
    db: Session,
    *,
    original_filename: str,
    content_type: str,
    file_bytes: bytes,
) -> GovernmentDocument:
    """
    Validate, persist to disk, and register metadata in PostgreSQL.
    Does NOT run ingestion — that is a separate step.
    """
    # Content-type check (browsers may send application/octet-stream for PDFs;
    # we also check the magic bytes below)
    if content_type not in ALLOWED_CONTENT_TYPES and not original_filename.lower().endswith(".pdf"):
        raise DocumentValidationError("Only PDF files are accepted.")

    # Magic-byte check: PDF files start with %PDF
    if not file_bytes[:4] == b"%PDF":
        raise DocumentValidationError("Uploaded file is not a valid PDF.")

    if len(file_bytes) == 0:
        raise DocumentValidationError("Uploaded file is empty.")

    if len(file_bytes) > settings.max_upload_size_bytes:
        raise DocumentValidationError(
            f"File exceeds the maximum allowed size of {settings.max_upload_size_mb} MB."
        )

    # Deterministic document_id for Qdrant dedup
    doc_id_hash = compute_document_id(original_filename, file_bytes)

    # Server-safe filename — never use the original name on the filesystem
    server_filename = _safe_server_filename(original_filename)

    # Write to disk if possible (local Docker dev); always store in DB (Vercel prod)
    file_path = _upload_dir() / server_filename
    _try_write_to_disk(file_path, file_bytes)

    record = GovernmentDocument(
        filename=server_filename,
        original_filename=original_filename,
        content_type="application/pdf",
        file_size=len(file_bytes),
        file_data=file_bytes,  # stored in DB for Vercel ephemeral-filesystem compatibility
        document_id=doc_id_hash,
        status=DocumentStatus.uploaded,
        is_active=True,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

def ingest_document(db: Session, document_id: int) -> GovernmentDocument:
    """
    Run the full Phase 6 RAG pipeline for a stored document.
    Updates status to processing → indexed (or failed).
    """
    doc = get_document_or_404(db, document_id)
    file_path = _upload_dir() / doc.filename

    # Mark as processing
    doc.status = DocumentStatus.processing
    doc.error_message = None
    db.commit()
    db.refresh(doc)

    try:
        # 1. Load PDF pages using existing document_loader
        # On Vercel the local file may not exist (ephemeral fs); fall back to DB bytes.
        if not file_path.exists() and doc.file_data:
            _try_write_to_disk(file_path, doc.file_data)
        loaded = load_pdf_document(file_path, doc.document_id)

        # 2. Chunk pages using existing chunker
        chunks = chunk_pages(document_id=doc.document_id, pages=loaded.pages)
        if not chunks:
            raise DocumentIngestionError("No text chunks could be extracted from the document.")

        # 3. Generate embeddings using existing Gemini embeddings
        texts = [chunk.text for chunk in chunks]
        try:
            embeddings = generate_embeddings_batch(texts)
        except EmbeddingNotConfiguredError as exc:
            raise DocumentIngestionError("Embedding service is not configured.") from exc
        except EmbeddingAPIError as exc:
            raise DocumentIngestionError("Embedding service is temporarily unavailable.") from exc

        # 4. Upsert into Qdrant using existing vector_store
        # Deterministic point IDs mean re-ingestion replaces existing vectors
        try:
            client = get_qdrant_client()
            upsert_chunks(client, chunks, embeddings)
        except VectorStoreUnavailableError as exc:
            raise DocumentIngestionError("Vector store is unavailable.") from exc
        except VectorStoreOperationError as exc:
            raise DocumentIngestionError("Vector store operation failed.") from exc

        # 5. Write document metadata to Neo4j graph (non-blocking)
        # Neo4j failure is logged but NEVER causes the Qdrant ingestion to fail.
        try:
            from app.ai.neo4j.ingestion import ingest_document_metadata
            ingest_document_metadata(doc, scheme_ids=[])
        except Exception as neo4j_exc:
            logger.warning(
                "Graph ingestion skipped for %s: %s",
                doc.original_filename,
                neo4j_exc,
            )

        # 6. Update metadata
        doc.status = DocumentStatus.indexed
        doc.page_count = len(loaded.pages)
        doc.ingested_at = datetime.now(tz=timezone.utc)
        doc.error_message = None
        db.commit()
        db.refresh(doc)
        logger.info("Document %s ingested: %d chunks", doc.filename, len(chunks))

    except (DocumentLoadError, DocumentIngestionError) as exc:
        safe_message = str(exc)
        doc.status = DocumentStatus.failed
        doc.error_message = safe_message
        db.commit()
        db.refresh(doc)
        logger.warning("Document ingestion failed for %s: %s", doc.filename, safe_message)
        raise DocumentIngestionError(safe_message) from exc
    except Exception as exc:
        doc.status = DocumentStatus.failed
        doc.error_message = "An unexpected error occurred during ingestion."
        db.commit()
        db.refresh(doc)
        logger.exception("Unexpected error during ingestion of %s", doc.filename)
        raise DocumentIngestionError("An unexpected error occurred during ingestion.") from exc

    return doc


# ---------------------------------------------------------------------------
# Status management
# ---------------------------------------------------------------------------

def deactivate_document(db: Session, document_id: int) -> GovernmentDocument:
    """Mark document as inactive. Does not delete physical file or Qdrant vectors."""
    doc = get_document_or_404(db, document_id)
    doc.status = DocumentStatus.inactive
    doc.is_active = False
    db.commit()
    db.refresh(doc)
    return doc


def activate_document(db: Session, document_id: int) -> GovernmentDocument:
    """Re-activate a previously deactivated document (metadata only, no re-ingestion)."""
    doc = get_document_or_404(db, document_id)
    doc.is_active = True
    # Restore to indexed if it was previously indexed, else uploaded
    if doc.status == DocumentStatus.inactive:
        doc.status = DocumentStatus.indexed if doc.ingested_at else DocumentStatus.uploaded
    db.commit()
    db.refresh(doc)
    return doc


# ---------------------------------------------------------------------------
# Phase 8: search, delete
# ---------------------------------------------------------------------------

from app.rag.vector_store import delete_document_vectors, count_document_vectors  # noqa: E402


class DocumentDeletionError(Exception):
    pass


def search_documents(
    db: Session,
    *,
    status_filter: str | None = None,
    search: str | None = None,
) -> list[GovernmentDocument]:
    """
    Return documents with optional filtering.

    status_filter: match documents whose status equals this value (case-insensitive).
    search: case-insensitive substring match on original_filename.
    Both filters are ANDed when supplied together.
    Ordering: newest first (created_at DESC) — same as list_documents.
    """
    query = db.query(GovernmentDocument)

    if status_filter:
        # Normalise to lowercase to match the enum values
        try:
            status_enum = DocumentStatus(status_filter.lower())
            query = query.filter(GovernmentDocument.status == status_enum)
        except ValueError:
            # Unknown status value — return empty result rather than error
            return []

    if search:
        query = query.filter(
            GovernmentDocument.original_filename.ilike(f"%{search}%")
        )

    return query.order_by(GovernmentDocument.created_at.desc()).all()


def delete_document(db: Session, document_id: int) -> None:
    """
    Hard-delete a document with a safe transaction-like workflow:

      1. Find the document (404 if missing).
      2. Delete its Qdrant vectors (document_id-scoped, never global).
         → On failure: raise DocumentDeletionError; DB record untouched.
      3. Remove the physical file (missing file handled gracefully).
      4. Delete the PostgreSQL record and commit.

    If Qdrant cleanup fails the DB record is NOT removed and no success is
    reported — the caller receives DocumentDeletionError.
    """
    doc = get_document_or_404(db, document_id)

    # Step 1 — Qdrant vector cleanup (must succeed before touching disk or DB)
    try:
        client = get_qdrant_client()
        delete_document_vectors(client, doc.document_id)
    except (VectorStoreOperationError, VectorStoreUnavailableError) as exc:
        # Qdrant is down or the delete failed — do NOT touch DB or file
        raise DocumentDeletionError(
            "Vector store cleanup failed; document was not deleted."
        ) from exc

    # Step 2 — Physical file removal (missing file is not an error)
    try:
        file_path = _upload_dir() / doc.filename
        if file_path.exists():
            file_path.unlink()
    except Exception as exc:
        logger.warning(
            "Could not remove physical file %s during delete: %s",
            doc.filename,
            exc,
        )
        # Non-fatal — continue to DB delete so we don't leave an orphaned record

    # Step 2a — Clear DB-stored bytes to free PostgreSQL space
    doc.file_data = None

    # Step 2b — Remove document node from Neo4j graph (non-blocking)
    try:
        from app.ai.neo4j.ingestion import remove_document_from_graph
        remove_document_from_graph(doc.document_id)
    except Exception as neo4j_exc:
        logger.warning(
            "Graph node removal skipped for %s: %s",
            doc.document_id[:8],
            neo4j_exc,
        )

    # Step 3 — DB delete + commit
    db.delete(doc)
    db.commit()
