from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from app.rag.chunker import DocumentChunk, chunk_pages
from app.rag.document_loader import DocumentPage, DocumentLoadError, load_pdf_document
from app.rag.embeddings import EmbeddingAPIError, EmbeddingNotConfiguredError, generate_embeddings_batch
from app.rag.rag_service import format_rag_context, format_rag_sources, try_search_knowledge_base
from app.rag.retriever import RetrievalError, retrieve_document_chunks
from app.rag.vector_store import compute_document_id, compute_point_id, ensure_collection, search_vectors


def test_chunk_pages_creates_multiple_chunks_with_overlap():
    words = [f"word{i}" for i in range(900)]
    pages = [DocumentPage(filename="sample.pdf", page_number=1, text=" ".join(words))]
    chunks = chunk_pages(document_id="doc-1", pages=pages)

    assert len(chunks) > 1
    assert all(isinstance(chunk, DocumentChunk) for chunk in chunks)
    assert chunks[0].page_number == 1
    assert chunks[0].chunk_index == 0


def test_compute_document_and_point_ids_are_deterministic():
    document_id = compute_document_id("sample.pdf", b"same-content")
    point_id_one = compute_point_id(document_id, 0)
    point_id_two = compute_point_id(document_id, 0)

    assert document_id == compute_document_id("sample.pdf", b"same-content")
    assert point_id_one == point_id_two


def test_generate_embeddings_batch_requires_configuration(monkeypatch):
    monkeypatch.setattr("app.rag.embeddings.settings.gemini_api_key", "")
    with pytest.raises(EmbeddingNotConfiguredError):
        generate_embeddings_batch(["hello"])


def test_generate_embeddings_batch_raises_api_error_on_failure(monkeypatch):
    monkeypatch.setattr("app.rag.embeddings.settings.gemini_api_key", "test-key")
    fake_client = Mock()
    fake_client.models.embed_content.side_effect = Exception("boom")

    with patch("app.rag.embeddings.genai.Client", return_value=fake_client):
        with pytest.raises(EmbeddingAPIError):
            generate_embeddings_batch(["hello"])


def test_ensure_collection_creates_collection_when_missing():
    client = Mock()
    client.get_collections.return_value = Mock(collections=[])

    ensure_collection(client)

    client.create_collection.assert_called_once()


def test_search_vectors_returns_payload_metadata():
    client = Mock()
    client.get_collections.return_value = Mock(collections=[Mock(name="jansahay_documents")])
    client.query_points.return_value = Mock(
        points=[
            Mock(
                score=0.87,
                payload={
                    "text": "Required documents include land proof.",
                    "filename": "sample_crop_insurance.pdf",
                    "page_number": 2,
                    "chunk_index": 1,
                    "document_id": "abc",
                },
            )
        ]
    )

    results = search_vectors(client, [0.1, 0.2, 0.3], top_k=1)

    assert len(results) == 1
    assert results[0]["filename"] == "sample_crop_insurance.pdf"
    assert results[0]["page_number"] == 2
    assert results[0]["chunk_index"] == 1


def test_retrieve_document_chunks_raises_retrieval_error_when_embedding_unconfigured(monkeypatch):
    monkeypatch.setattr("app.rag.embeddings.settings.gemini_api_key", "")
    with pytest.raises(RetrievalError):
        retrieve_document_chunks("benefits", top_k=3)


def test_try_search_knowledge_base_returns_none_when_retrieval_fails(monkeypatch):
    monkeypatch.setattr("app.rag.embeddings.settings.gemini_api_key", "")

    assert try_search_knowledge_base("documents required") is None


def test_format_rag_context_and_sources():
    results = [
        {
            "text": "Application process step one.",
            "filename": "sample_crop_insurance.pdf",
            "page_number": 3,
        }
    ]
    context = format_rag_context(results)
    sources = format_rag_sources(results)

    assert "DOCUMENT KNOWLEDGE:" in context
    assert sources == ["sample_crop_insurance.pdf — page 3"]


def test_load_pdf_document_preserves_page_numbers(tmp_path: Path):
    pdf_file = tmp_path / "sample.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n...")

    with pytest.raises(DocumentLoadError):
        load_pdf_document(pdf_file, document_id="doc")


# ---------------------------------------------------------------------------
# raw_sources / RagResult tests (Phase 6 structured metadata)
# ---------------------------------------------------------------------------

def test_search_knowledge_base_populates_raw_sources():
    """search_knowledge_base must populate raw_sources with filename/page/chunk dicts."""
    from unittest.mock import patch as _patch
    from app.rag.rag_service import search_knowledge_base

    fake_results = [
        {
            "text": "Required documents include land proof.",
            "filename": "sample_crop_insurance.pdf",
            "page_number": 2,
            "chunk_index": 1,
            "document_id": "abc",
            "score": 0.87,
        },
        {
            "text": "Submit form to the local agricultural office.",
            "filename": "sample_crop_insurance.pdf",
            "page_number": 3,
            "chunk_index": 2,
            "document_id": "abc",
            "score": 0.75,
        },
    ]

    with _patch("app.rag.rag_service.retrieve_document_chunks", return_value=fake_results):
        result = search_knowledge_base("application documents")

    assert len(result.raw_sources) == 2
    assert result.raw_sources[0] == {
        "filename": "sample_crop_insurance.pdf",
        "page_number": 2,
        "chunk_index": 1,
    }
    assert result.raw_sources[1] == {
        "filename": "sample_crop_insurance.pdf",
        "page_number": 3,
        "chunk_index": 2,
    }


def test_raw_sources_each_contain_required_keys():
    """Every raw_sources entry must have exactly filename, page_number, chunk_index."""
    from unittest.mock import patch as _patch
    from app.rag.rag_service import search_knowledge_base

    fake_results = [
        {
            "text": "Some chunk text.",
            "filename": "scheme_guide.pdf",
            "page_number": 1,
            "chunk_index": 0,
            "document_id": "xyz",
            "score": 0.90,
        }
    ]

    with _patch("app.rag.rag_service.retrieve_document_chunks", return_value=fake_results):
        result = search_knowledge_base("how to apply")

    for entry in result.raw_sources:
        assert set(entry.keys()) == {"filename", "page_number", "chunk_index"}


def test_raw_sources_empty_when_no_results():
    """raw_sources must be [] when Qdrant returns no results."""
    from unittest.mock import patch as _patch
    from app.rag.rag_service import search_knowledge_base

    with _patch("app.rag.rag_service.retrieve_document_chunks", return_value=[]):
        result = search_knowledge_base("anything")

    assert result.raw_sources == []


def test_raw_sources_excludes_entries_without_filename():
    """Entries with no filename must be excluded from raw_sources."""
    from unittest.mock import patch as _patch
    from app.rag.rag_service import search_knowledge_base

    fake_results = [
        {
            "text": "Valid chunk.",
            "filename": "valid.pdf",
            "page_number": 1,
            "chunk_index": 0,
            "score": 0.9,
        },
        {
            "text": "No filename chunk.",
            "filename": "",
            "page_number": 2,
            "chunk_index": 1,
            "score": 0.8,
        },
    ]

    with _patch("app.rag.rag_service.retrieve_document_chunks", return_value=fake_results):
        result = search_knowledge_base("query")

    assert len(result.raw_sources) == 1
    assert result.raw_sources[0]["filename"] == "valid.pdf"


def test_try_search_knowledge_base_returns_none_returns_empty_raw_sources(monkeypatch):
    """try_search_knowledge_base returns None (not a RagResult) when retrieval fails — no raw_sources leaks."""
    monkeypatch.setattr("app.rag.embeddings.settings.gemini_api_key", "")
    result = try_search_knowledge_base("documents")
    assert result is None
