from unittest.mock import patch

from app.rag.rag_service import format_rag_context, format_rag_sources
from tests.api.test_profile import auth_headers, farmer_token


def rag_payload(query: str, top_k: int = 5) -> dict:
    return {"query": query, "top_k": top_k}


def test_unauthenticated_rag_search_returns_401(client):
    response = client.post(
        "/api/rag/search",
        json=rag_payload("What documents mention crop insurance?"),
    )
    assert response.status_code == 401


@patch("app.api.routes.rag.retrieve_document_chunks")
def test_authenticated_farmer_can_search(mock_retrieve, client):
    mock_retrieve.return_value = [
        {
            "text": "Application documents required.",
            "filename": "sample_crop_insurance.pdf",
            "page_number": 2,
            "chunk_index": 1,
            "score": 0.87,
        }
    ]
    token = farmer_token(client, email="rag-search-farmer@example.com")

    response = client.post(
        "/api/rag/search",
        json=rag_payload("What documents are required to apply?"),
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["results"][0]["filename"] == "sample_crop_insurance.pdf"


def test_empty_query_returns_422(client):
    token = farmer_token(client, email="rag-empty-query@example.com")
    response = client.post(
        "/api/rag/search",
        json={"query": "   ", "top_k": 5},
        headers=auth_headers(token),
    )
    assert response.status_code == 422


def test_top_k_validation(client):
    token = farmer_token(client, email="rag-topk@example.com")
    response = client.post(
        "/api/rag/search",
        json={"query": "benefits", "top_k": 0},
        headers=auth_headers(token),
    )
    assert response.status_code == 422

    response = client.post(
        "/api/rag/search",
        json={"query": "benefits", "top_k": 11},
        headers=auth_headers(token),
    )
    assert response.status_code == 422


@patch("app.api.routes.rag.retrieve_document_chunks", return_value=[])
def test_empty_qdrant_collection_handled_gracefully(mock_retrieve, client):
    token = farmer_token(client, email="rag-empty-collection@example.com")
    response = client.post(
        "/api/rag/search",
        json=rag_payload("What documents are required?"),
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json() == {"results": [], "total": 0}


@patch("app.api.routes.rag.retrieve_document_chunks")
def test_retrieval_result_structure(mock_retrieve, client):
    mock_retrieve.return_value = [
        {
            "text": "Bank account details for claim settlement.",
            "filename": "sample_crop_insurance.pdf",
            "page_number": 2,
            "chunk_index": 0,
            "score": 0.91,
        }
    ]
    token = farmer_token(client, email="rag-structure@example.com")

    response = client.post(
        "/api/rag/search",
        json=rag_payload("application documents"),
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    item = response.json()["results"][0]
    assert set(item.keys()) == {"text", "filename", "page_number", "chunk_index", "score"}
    assert item["text"]
    assert item["filename"]
    assert item["page_number"] == 2
    assert item["chunk_index"] == 0
    assert isinstance(item["score"], float)


def test_rag_context_formatting():
    results = [
        {
            "text": "Required documents include land proof.",
            "filename": "sample_crop_insurance.pdf",
            "page_number": 2,
        }
    ]
    context = format_rag_context(results)
    sources = format_rag_sources(results)

    assert "DOCUMENT KNOWLEDGE:" in context
    assert "[Source: sample_crop_insurance.pdf, page 2]" in context
    assert "Do not override deterministic eligibility results." in context
    assert sources == ["sample_crop_insurance.pdf — page 2"]


@patch("app.services.assistant_service.generate_assistant_response", return_value="Answer without RAG.")
@patch("app.services.assistant_service.try_search_knowledge_base", return_value=None)
def test_assistant_still_works_when_rag_returns_no_results(
    mock_rag,
    mock_generate,
    client,
    db_session,
):
    from tests.api.test_schemes import seed_test_scheme

    seed_test_scheme(db_session, name="Assistant No RAG Scheme")
    token = farmer_token(client, email="assistant-no-rag@example.com")

    response = client.post(
        "/api/assistant/chat",
        json={"message": "Which schemes are suitable for me?"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "Answer without RAG."


@patch("app.services.assistant_service.generate_assistant_response", return_value="Eligibility explained.")
@patch("app.services.assistant_service.check_scheme_eligibility")
@patch("app.services.assistant_service.try_search_knowledge_base")
def test_existing_eligibility_behavior_remains_authoritative(
    mock_rag,
    mock_check_eligibility,
    mock_generate,
    client,
    db_session,
):
    from app.services.eligibility_service import EligibilityResult
    from tests.api.test_schemes import create_farmer_with_profile, seed_test_scheme

    scheme = seed_test_scheme(db_session, name="RAG Eligibility Scheme")
    mock_check_eligibility.return_value = (
        scheme,
        EligibilityResult(eligible=False, reasons=["Annual income exceeds the maximum allowed income."]),
    )
    token = create_farmer_with_profile(client, "rag-eligibility-authority@example.com")

    response = client.post(
        "/api/assistant/chat",
        json={"message": f"Am I eligible for {scheme.name}?"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["eligibility_checked"] is True
    mock_check_eligibility.assert_called_once()


@patch("app.services.assistant_service.generate_assistant_response")
@patch("app.services.assistant_service.try_search_knowledge_base")
def test_gemini_receives_rag_context_for_document_related_question(
    mock_rag,
    mock_generate,
    client,
    db_session,
):
    from app.rag.rag_service import RagResult
    from tests.api.test_schemes import seed_test_scheme

    seed_test_scheme(db_session, name="RAG Document Scheme")
    mock_rag.return_value = RagResult(
        context="DOCUMENT KNOWLEDGE:\n[Source: sample_crop_insurance.pdf, page 2]\nRequired documents.",
        sources=["sample_crop_insurance.pdf — page 2"],
    )

    def capture_context(**kwargs):
        assert "DOCUMENT KNOWLEDGE" in kwargs["system_instruction"]
        assert "sample_crop_insurance.pdf" in kwargs["system_instruction"]
        return "Grounded document answer."

    mock_generate.side_effect = capture_context
    token = farmer_token(client, email="rag-assistant-context@example.com")

    response = client.post(
        "/api/assistant/chat",
        json={"message": "What documents are required to apply?"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "Grounded document answer."
    assert any("sample_crop_insurance.pdf" in source for source in response.json()["sources"])


@patch("app.api.routes.rag.retrieve_document_chunks")
def test_metadata_contains_filename_page_and_chunk(mock_retrieve, client):
    mock_retrieve.return_value = [
        {
            "text": "Chunk text",
            "filename": "sample_crop_insurance.pdf",
            "page_number": 4,
            "chunk_index": 3,
            "score": 0.75,
        }
    ]
    token = farmer_token(client, email="rag-metadata@example.com")

    response = client.post(
        "/api/rag/search",
        json=rag_payload("benefits"),
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    mock_retrieve.assert_called_once()
    assert mock_retrieve.call_args.kwargs["top_k"] == 5
    payload = response.json()
    assert payload["results"][0]["chunk_index"] == 3
    item = response.json()["results"][0]
    assert item["filename"] == "sample_crop_insurance.pdf"
    assert item["page_number"] == 4


# ---------------------------------------------------------------------------
# rag_sources field on /api/assistant/chat (Phase 6 structured metadata)
# ---------------------------------------------------------------------------

@patch("app.services.assistant_service.generate_assistant_response", return_value="Document answer.")
@patch("app.services.assistant_service.try_graph_rag_search", return_value=None)
@patch("app.services.assistant_service.try_search_knowledge_base")
def test_assistant_response_contains_rag_sources_field(
    mock_rag,
    mock_graph_rag,
    mock_generate,
    client,
    db_session,
):
    """When RAG fires, rag_sources in the response must contain structured metadata."""
    from app.rag.rag_service import RagResult
    from tests.api.test_schemes import seed_test_scheme

    seed_test_scheme(db_session, name="RAG Sources Scheme")
    mock_rag.return_value = RagResult(
        context="DOCUMENT KNOWLEDGE:\n[Source: sample_crop_insurance.pdf, page 2, chunk 1]\nRequired docs.",
        sources=["sample_crop_insurance.pdf — page 2 — chunk 1"],
        raw_sources=[
            {"filename": "sample_crop_insurance.pdf", "page_number": 2, "chunk_index": 1}
        ],
    )
    token = farmer_token(client, email="rag-sources-field@example.com")

    response = client.post(
        "/api/assistant/chat",
        json={"message": "What documents are required to apply?"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert "rag_sources" in payload
    assert len(payload["rag_sources"]) == 1
    source = payload["rag_sources"][0]
    assert source["filename"] == "sample_crop_insurance.pdf"
    assert source["page_number"] == 2
    assert source["chunk_index"] == 1


@patch("app.services.assistant_service.generate_assistant_response", return_value="Generic answer.")
@patch("app.services.assistant_service.try_search_knowledge_base")
def test_rag_sources_empty_when_rag_not_triggered(
    mock_rag,
    mock_generate,
    client,
    db_session,
):
    """For a non-RAG-keyword message, rag_sources must be [] and try_search_knowledge_base not called."""
    from tests.api.test_schemes import seed_test_scheme

    seed_test_scheme(db_session, name="No RAG Trigger Scheme")
    token = farmer_token(client, email="rag-not-triggered@example.com")

    response = client.post(
        "/api/assistant/chat",
        # No DOCUMENT_RAG_KEYWORDS — RAG must not fire
        json={"message": "Am I eligible for No RAG Trigger Scheme?"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["rag_sources"] == []
    mock_rag.assert_not_called()


@patch("app.services.assistant_service.generate_assistant_response", return_value="Multi-chunk answer.")
@patch("app.services.assistant_service.try_graph_rag_search", return_value=None)
@patch("app.services.assistant_service.try_search_knowledge_base")
def test_rag_sources_contain_all_chunks_returned(
    mock_rag,
    mock_graph_rag,
    mock_generate,
    client,
    db_session,
):
    """Multiple retrieved chunks must each appear as a separate rag_sources entry."""
    from app.rag.rag_service import RagResult
    from tests.api.test_schemes import seed_test_scheme

    seed_test_scheme(db_session, name="Multi Chunk Scheme")
    mock_rag.return_value = RagResult(
        context="DOCUMENT KNOWLEDGE:\n[Source: guide.pdf, page 1, chunk 0]\nChunk A.\n\n[Source: guide.pdf, page 2, chunk 1]\nChunk B.",
        sources=["guide.pdf — page 1 — chunk 0", "guide.pdf — page 2 — chunk 1"],
        raw_sources=[
            {"filename": "guide.pdf", "page_number": 1, "chunk_index": 0},
            {"filename": "guide.pdf", "page_number": 2, "chunk_index": 1},
        ],
    )
    token = farmer_token(client, email="rag-multi-chunk@example.com")

    response = client.post(
        "/api/assistant/chat",
        json={"message": "What are the application documents required?"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["rag_sources"]) == 2
    assert payload["rag_sources"][0] == {"filename": "guide.pdf", "page_number": 1, "chunk_index": 0}
    assert payload["rag_sources"][1] == {"filename": "guide.pdf", "page_number": 2, "chunk_index": 1}


@patch("app.services.assistant_service.generate_assistant_response", return_value="No RAG answer.")
@patch("app.services.assistant_service.try_graph_rag_search", return_value=None)
@patch("app.services.assistant_service.try_search_knowledge_base", return_value=None)
def test_rag_sources_empty_when_qdrant_returns_no_results(
    mock_rag,
    mock_graph_rag,
    mock_generate,
    client,
    db_session,
):
    """When try_search_knowledge_base returns None (e.g. Qdrant empty), rag_sources must be []."""
    from tests.api.test_schemes import seed_test_scheme

    seed_test_scheme(db_session, name="Empty Qdrant Scheme")
    token = farmer_token(client, email="rag-empty-qdrant@example.com")

    response = client.post(
        "/api/assistant/chat",
        json={"message": "What documents are required to apply?"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["rag_sources"] == []


@patch("app.services.assistant_service.generate_assistant_response", return_value="Structured answer.")
@patch("app.services.assistant_service.try_search_knowledge_base")
def test_rag_sources_item_structure_matches_schema(
    mock_rag,
    mock_generate,
    client,
    db_session,
):
    """Each rag_sources item must have exactly the three fields: filename, page_number, chunk_index."""
    from app.rag.rag_service import RagResult
    from tests.api.test_schemes import seed_test_scheme

    seed_test_scheme(db_session, name="Schema Check Scheme")
    mock_rag.return_value = RagResult(
        context="DOCUMENT KNOWLEDGE:\n[Source: info.pdf, page 5, chunk 3]\nSome info.",
        sources=["info.pdf — page 5 — chunk 3"],
        raw_sources=[{"filename": "info.pdf", "page_number": 5, "chunk_index": 3}],
    )
    token = farmer_token(client, email="rag-schema-check@example.com")

    response = client.post(
        "/api/assistant/chat",
        json={"message": "How to apply for this scheme?"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    item = response.json()["rag_sources"][0]
    assert set(item.keys()) == {"filename", "page_number", "chunk_index"}
    assert isinstance(item["filename"], str)
    assert isinstance(item["page_number"], int)
    assert isinstance(item["chunk_index"], int)
