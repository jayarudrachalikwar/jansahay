from __future__ import annotations

import logging

from google import genai
from google.genai import errors as genai_errors

from app.core.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_OUTPUT_DIMENSIONALITY = 768


class EmbeddingNotConfiguredError(Exception):
    pass


class EmbeddingAPIError(Exception):
    pass


def is_embedding_configured() -> bool:
    return bool(settings.gemini_api_key and settings.gemini_api_key.strip())


def generate_embedding(text: str) -> list[float]:
    embeddings = generate_embeddings_batch([text])
    return embeddings[0]


def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    if not is_embedding_configured():
        raise EmbeddingNotConfiguredError("Embedding service is not configured.")

    client = genai.Client(api_key=settings.gemini_api_key)

    try:
        response = client.models.embed_content(
            model=settings.embedding_model,
            contents=texts,
            config={"output_dimensionality": EMBEDDING_OUTPUT_DIMENSIONALITY},
        )
    except genai_errors.APIError as exc:
        logger.warning("Gemini embedding request failed")
        raise EmbeddingAPIError("Embedding service is temporarily unavailable.") from exc
    except Exception as exc:
        logger.warning("Unexpected embedding integration error")
        raise EmbeddingAPIError("Embedding service is temporarily unavailable.") from exc

    embeddings = _extract_embeddings(response, expected=len(texts))
    if len(embeddings) != len(texts):
        raise EmbeddingAPIError("Embedding service returned an unexpected response.")

    return embeddings


def _extract_embeddings(response: object, expected: int) -> list[list[float]]:
    embeddings: list[list[float]] = []

    data = getattr(response, "embeddings", None)
    if data:
        for item in data:
            values = getattr(item, "values", None)
            if values is not None:
                embeddings.append(list(values))

    if embeddings:
        return embeddings

    embedding = getattr(response, "embedding", None)
    if embedding is not None:
        values = getattr(embedding, "values", None)
        if values is not None:
            return [list(values)]

    if expected == 1:
        return []

    return embeddings
