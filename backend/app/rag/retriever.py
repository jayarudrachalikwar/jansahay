from __future__ import annotations

from typing import Any

from app.rag.embeddings import EmbeddingAPIError, EmbeddingNotConfiguredError, generate_embedding
from app.rag.vector_store import VectorStoreUnavailableError, get_qdrant_client, search_vectors


class RetrievalError(Exception):
    pass


def retrieve_document_chunks(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    if not query.strip():
        return []

    try:
        query_vector = generate_embedding(query.strip())
        client = get_qdrant_client()
        return search_vectors(client, query_vector, top_k=top_k)
    except (EmbeddingNotConfiguredError, EmbeddingAPIError) as exc:
        raise RetrievalError(str(exc)) from exc
    except VectorStoreUnavailableError as exc:
        raise RetrievalError(str(exc)) from exc
