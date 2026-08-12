from __future__ import annotations

import hashlib
import logging
import uuid
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import settings
from app.rag.chunker import DocumentChunk
from app.rag.embeddings import EMBEDDING_OUTPUT_DIMENSIONALITY

logger = logging.getLogger(__name__)


class VectorStoreUnavailableError(Exception):
    pass


class VectorStoreOperationError(Exception):
    pass


def compute_document_id(filename: str, file_bytes: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(filename.encode("utf-8"))
    digest.update(file_bytes)
    return digest.hexdigest()


def compute_point_id(document_id: str, chunk_index: int) -> str:
    digest = hashlib.sha256(f"{document_id}:{chunk_index}".encode("utf-8")).hexdigest()
    return str(uuid.UUID(digest[:32]))


def get_qdrant_client() -> QdrantClient:
    try:
        return QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
            timeout=30,
        )
    except Exception as exc:
        logger.warning("Unable to connect to Qdrant")
        raise VectorStoreUnavailableError("Vector store is unavailable.") from exc


def ensure_collection(client: QdrantClient) -> None:
    collection_name = settings.qdrant_collection_name
    try:
        existing = {collection.name for collection in client.get_collections().collections}
    except Exception as exc:
        raise VectorStoreUnavailableError("Vector store is unavailable.") from exc

    if collection_name in existing:
        return

    try:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=qmodels.VectorParams(
                size=EMBEDDING_OUTPUT_DIMENSIONALITY,
                distance=qmodels.Distance.COSINE,
            ),
        )
    except Exception as exc:
        raise VectorStoreOperationError("Unable to create vector collection.") from exc


def upsert_chunks(
    client: QdrantClient,
    chunks: list[DocumentChunk],
    embeddings: list[list[float]],
) -> int:
    if len(chunks) != len(embeddings):
        raise VectorStoreOperationError("Chunk and embedding counts do not match.")

    ensure_collection(client)

    points = []
    for chunk, vector in zip(chunks, embeddings, strict=True):
        points.append(
            qmodels.PointStruct(
                id=compute_point_id(chunk.document_id, chunk.chunk_index),
                vector=vector,
                payload={
                    "document_id": chunk.document_id,
                    "filename": chunk.filename,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                },
            )
        )

    try:
        client.upsert(
            collection_name=settings.qdrant_collection_name,
            points=points,
            wait=True,
        )
    except Exception as exc:
        raise VectorStoreOperationError("Unable to index document chunks.") from exc

    return len(points)


def search_vectors(
    client: QdrantClient,
    query_vector: list[float],
    top_k: int,
) -> list[dict[str, Any]]:
    ensure_collection(client)

    try:
        response = client.query_points(
            collection_name=settings.qdrant_collection_name,
            query=query_vector,
            limit=top_k,
            with_payload=True,
        )
    except Exception as exc:
        raise VectorStoreUnavailableError("Vector store is unavailable.") from exc

    results: list[dict[str, Any]] = []
    for point in response.points:
        payload = point.payload or {}
        results.append(
            {
                "text": payload.get("text", ""),
                "filename": payload.get("filename", ""),
                "page_number": payload.get("page_number"),
                "chunk_index": payload.get("chunk_index"),
                "document_id": payload.get("document_id"),
                "score": float(point.score) if point.score is not None else 0.0,
            }
        )
    return results


def collection_point_count(client: QdrantClient) -> int:
    ensure_collection(client)
    try:
        info = client.get_collection(settings.qdrant_collection_name)
        return int(info.points_count or 0)
    except Exception as exc:
        raise VectorStoreUnavailableError("Vector store is unavailable.") from exc


def delete_document_vectors(client: QdrantClient, document_id: str) -> None:
    """
    Delete all Qdrant vectors whose payload.document_id matches the given value.
    Scoped strictly to this document — never touches other documents' vectors.
    Raises VectorStoreOperationError on failure; VectorStoreUnavailableError on
    connection failure (surfaced from ensure_collection).
    """
    ensure_collection(client)

    try:
        client.delete(
            collection_name=settings.qdrant_collection_name,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="document_id",
                            match=qmodels.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
            wait=True,
        )
        logger.info("Deleted Qdrant vectors for document_id=%s", document_id)
    except Exception as exc:
        logger.warning("Failed to delete Qdrant vectors for document_id=%s", document_id)
        raise VectorStoreOperationError(
            "Unable to delete vectors from the vector store."
        ) from exc


def count_document_vectors(client: QdrantClient, document_id: str) -> int:
    """
    Count how many Qdrant vectors have payload.document_id equal to the given value.
    Returns 0 when the document has no indexed vectors.
    Raises VectorStoreUnavailableError on connection/collection failure.
    """
    ensure_collection(client)

    try:
        result = client.count(
            collection_name=settings.qdrant_collection_name,
            count_filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="document_id",
                        match=qmodels.MatchValue(value=document_id),
                    )
                ]
            ),
            exact=True,
        )
        return int(result.count)
    except Exception as exc:
        logger.warning("Failed to count Qdrant vectors for document_id=%s", document_id)
        raise VectorStoreUnavailableError("Vector store is unavailable.") from exc
