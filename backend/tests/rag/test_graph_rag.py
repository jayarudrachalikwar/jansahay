"""
Phase 13 — Neo4j + GraphRAG tests.

All Neo4j calls are mocked so no real Neo4j server is required.
Tests cover:
  A. Neo4j configuration (settings)
  B. Client — driver creation, unavailability handling
  C. Schema initialisation
  D. Repository — upsert operations (idempotent MERGE)
  E. Repository — retrieval queries
  F. Ingestion — domain-level helpers
  G. GraphRAG service — fusion, fallback, provenance
  H. GraphRAG API endpoints (/api/rag/graph-search, /api/rag/graph-rag)
  I. Assistant integration — GraphRAG is used for RAG queries
  J. Regression — existing Qdrant RAG tests unaffected
"""
from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import pytest

# ---------------------------------------------------------------------------
# A. Configuration
# ---------------------------------------------------------------------------

def test_neo4j_uri_in_settings():
    from app.core.config import settings
    assert hasattr(settings, "neo4j_uri")
    assert "bolt" in settings.neo4j_uri or "neo4j" in settings.neo4j_uri


def test_neo4j_username_in_settings():
    from app.core.config import settings
    assert hasattr(settings, "neo4j_username")
    assert settings.neo4j_username  # non-empty


def test_neo4j_password_in_settings():
    from app.core.config import settings
    assert hasattr(settings, "neo4j_password")
    assert settings.neo4j_password  # non-empty


def test_neo4j_database_in_settings():
    from app.core.config import settings
    assert hasattr(settings, "neo4j_database")
    assert settings.neo4j_database  # non-empty


def test_neo4j_configured_property_true_when_all_set():
    from app.core.config import settings
    # All three fields are non-empty in default config
    assert settings.neo4j_configured is True


def test_neo4j_configured_property_false_when_uri_empty(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "neo4j_uri", "")
    assert settings.neo4j_configured is False


# ---------------------------------------------------------------------------
# B. Client — driver creation and unavailability
# ---------------------------------------------------------------------------

def test_get_driver_raises_unavailable_when_not_configured(monkeypatch):
    from app.core.config import settings
    from app.ai.neo4j.client import GraphDatabaseUnavailableError, get_driver
    import app.ai.neo4j.client as client_module

    monkeypatch.setattr(settings, "neo4j_uri", "")
    client_module._driver = None  # reset singleton
    with pytest.raises(GraphDatabaseUnavailableError):
        get_driver()
    client_module._driver = None  # cleanup


def test_get_driver_raises_unavailable_on_connection_failure(monkeypatch):
    from app.ai.neo4j.client import GraphDatabaseUnavailableError, get_driver
    import app.ai.neo4j.client as client_module

    client_module._driver = None
    with patch("app.ai.neo4j.client._create_driver", side_effect=Exception("connection refused")):
        with pytest.raises(GraphDatabaseUnavailableError):
            get_driver()
    client_module._driver = None


def test_verify_connectivity_returns_false_when_neo4j_down(monkeypatch):
    from app.ai.neo4j.client import verify_connectivity
    import app.ai.neo4j.client as client_module

    client_module._driver = None
    with patch("app.ai.neo4j.client.get_driver", side_effect=Exception("down")):
        assert verify_connectivity() is False


def test_verify_connectivity_returns_true_when_up():
    from app.ai.neo4j.client import verify_connectivity
    mock_driver = Mock()
    mock_driver.verify_connectivity.return_value = None
    with patch("app.ai.neo4j.client.get_driver", return_value=mock_driver):
        assert verify_connectivity() is True


def test_get_session_context_manager_yields_and_closes():
    from app.ai.neo4j.client import get_session
    mock_session = MagicMock()
    mock_driver = Mock()
    mock_driver.session.return_value = mock_session

    with patch("app.ai.neo4j.client.get_driver", return_value=mock_driver):
        with get_session() as session:
            assert session is mock_session
    mock_session.close.assert_called_once()


def test_close_driver_does_not_raise_when_none():
    from app.ai.neo4j.client import close_driver
    import app.ai.neo4j.client as client_module
    client_module._driver = None
    close_driver()  # must not raise


# ---------------------------------------------------------------------------
# C. Schema initialisation
# ---------------------------------------------------------------------------

def _mock_session():
    """Return a MagicMock that behaves like a Neo4j session."""
    session = MagicMock()
    session.__enter__ = Mock(return_value=session)
    session.__exit__ = Mock(return_value=False)
    return session


def test_initialize_schema_runs_all_statements():
    from app.ai.neo4j.schema import _CONSTRAINTS, _INDEXES, initialize_schema

    mock_session = _mock_session()
    with patch("app.ai.neo4j.schema.get_session", return_value=mock_session):
        initialize_schema()

    expected_calls = len(_CONSTRAINTS) + len(_INDEXES)
    assert mock_session.run.call_count == expected_calls


def test_initialize_schema_continues_on_partial_failure():
    """If one statement fails, schema init should keep going (log + continue)."""
    from app.ai.neo4j.schema import initialize_schema

    mock_session = _mock_session()
    # Make every other statement fail
    call_count = [0]

    def side_effect(stmt, *args, **kwargs):
        call_count[0] += 1
        if call_count[0] % 2 == 0:
            raise Exception("statement failed")

    mock_session.run.side_effect = side_effect
    with patch("app.ai.neo4j.schema.get_session", return_value=mock_session):
        initialize_schema()  # must not raise

    assert mock_session.run.call_count > 0


def test_initialize_schema_is_idempotent():
    """Calling initialize_schema twice must not raise."""
    from app.ai.neo4j.schema import initialize_schema

    mock_session = _mock_session()
    with patch("app.ai.neo4j.schema.get_session", return_value=mock_session):
        initialize_schema()
        initialize_schema()

    assert mock_session.run.call_count > 0


# ---------------------------------------------------------------------------
# D. Repository — upsert operations
# ---------------------------------------------------------------------------

def test_upsert_scheme_runs_merge_cypher():
    from app.ai.neo4j.models import SchemeNode
    from app.ai.neo4j.repository import upsert_scheme

    node = SchemeNode(
        scheme_id=1,
        name="Test Scheme",
        department="Test Dept",
        state="Telangana",
        scheme_type="Financial Assistance",
        is_active=True,
        target_crops=["cotton"],
        target_categories=["owned"],
    )

    mock_session = _mock_session()
    with patch("app.ai.neo4j.repository.get_session", return_value=mock_session):
        upsert_scheme(node)

    assert mock_session.run.call_count >= 1
    # Main MERGE call must include scheme_id
    first_call_params = mock_session.run.call_args_list[0][0][1]
    assert first_call_params["scheme_id"] == 1


def test_upsert_scheme_with_no_crops_skips_crop_cypher():
    from app.ai.neo4j.models import SchemeNode
    from app.ai.neo4j.repository import upsert_scheme

    node = SchemeNode(
        scheme_id=2,
        name="No Crop Scheme",
        department="Dept",
        state="All India",
        scheme_type="Insurance",
        is_active=True,
        target_crops=[],
        target_categories=[],
    )

    mock_session = _mock_session()
    with patch("app.ai.neo4j.repository.get_session", return_value=mock_session):
        upsert_scheme(node)

    # Should only have the main MERGE call (no crop/category loops)
    assert mock_session.run.call_count == 1


def test_upsert_farmer_creates_nodes_and_relationships():
    from app.ai.neo4j.models import FarmerNode
    from app.ai.neo4j.repository import upsert_farmer

    node = FarmerNode(
        user_id=42,
        state="Telangana",
        district="Hyderabad",
        primary_crop="cotton",
        secondary_crop=None,
        land_ownership="owned",
        farming_type="organic",
    )

    mock_session = _mock_session()
    with patch("app.ai.neo4j.repository.get_session", return_value=mock_session):
        upsert_farmer(node)

    # Main MERGE + state + district + crop = 4 calls minimum
    assert mock_session.run.call_count >= 4


def test_upsert_document_with_no_scheme_ids():
    from app.ai.neo4j.models import DocumentNode
    from app.ai.neo4j.repository import upsert_document

    node = DocumentNode(
        document_id="abc123",
        filename="server_safe.pdf",
        original_filename="Official Document.pdf",
        scheme_ids=[],
    )

    mock_session = _mock_session()
    with patch("app.ai.neo4j.repository.get_session", return_value=mock_session):
        upsert_document(node)

    # Only the main MERGE — no DESCRIBES relationship
    assert mock_session.run.call_count == 1


def test_upsert_document_with_scheme_ids_creates_describes_relationship():
    from app.ai.neo4j.models import DocumentNode
    from app.ai.neo4j.repository import upsert_document

    node = DocumentNode(
        document_id="abc456",
        filename="another.pdf",
        original_filename="Scheme Doc.pdf",
        scheme_ids=[1, 2],
    )

    mock_session = _mock_session()
    with patch("app.ai.neo4j.repository.get_session", return_value=mock_session):
        upsert_document(node)

    # MERGE + DESCRIBES = 2 calls
    assert mock_session.run.call_count == 2


def test_delete_document_node_calls_detach_delete():
    from app.ai.neo4j.repository import delete_document_node

    mock_session = _mock_session()
    with patch("app.ai.neo4j.repository.get_session", return_value=mock_session):
        delete_document_node("abc123")

    call_cypher = mock_session.run.call_args_list[0][0][0]
    assert "DETACH DELETE" in call_cypher


# ---------------------------------------------------------------------------
# E. Repository — retrieval queries
# ---------------------------------------------------------------------------

def _make_mock_record(**kwargs):
    """Return a dict-like object that behaves like a Neo4j Record."""
    return kwargs


def test_find_schemes_in_state_returns_list():
    from app.ai.neo4j.repository import find_schemes_in_state

    mock_records = [
        _make_mock_record(scheme_id=1, scheme_name="Test Scheme", department="Dept",
                          scheme_type="Financial Assistance", state="Telangana"),
    ]
    mock_session = _mock_session()
    mock_session.run.return_value = iter(mock_records)

    with patch("app.ai.neo4j.repository.get_session", return_value=mock_session):
        results = find_schemes_in_state("Telangana")

    assert len(results) == 1
    assert results[0]["scheme_id"] == 1


def test_find_schemes_in_state_uses_parameterized_query():
    from app.ai.neo4j.repository import find_schemes_in_state

    mock_session = _mock_session()
    mock_session.run.return_value = iter([])

    with patch("app.ai.neo4j.repository.get_session", return_value=mock_session):
        find_schemes_in_state("Telangana")

    call_args = mock_session.run.call_args_list[0]
    params = call_args[0][1]  # positional params dict
    assert params == {"state": "Telangana"}


def test_find_schemes_for_crop_uses_parameterized_query():
    from app.ai.neo4j.repository import find_schemes_for_crop

    mock_session = _mock_session()
    mock_session.run.return_value = iter([])

    with patch("app.ai.neo4j.repository.get_session", return_value=mock_session):
        find_schemes_for_crop("cotton")

    params = mock_session.run.call_args_list[0][0][1]
    assert params["crop"] == "cotton"


def test_get_scheme_graph_context_returns_empty_dict_when_not_found():
    from app.ai.neo4j.repository import get_scheme_graph_context

    mock_session = _mock_session()
    mock_result = Mock()
    mock_result.single.return_value = None
    mock_session.run.return_value = mock_result

    with patch("app.ai.neo4j.repository.get_session", return_value=mock_session):
        result = get_scheme_graph_context(999)

    assert result == {}


def test_find_schemes_for_farmer_combines_state_and_crop():
    from app.ai.neo4j.repository import find_schemes_for_farmer

    state_record = _make_mock_record(scheme_id=1, scheme_name="State Scheme",
                                     department="D", scheme_type="T", state="Telangana")
    crop_record = _make_mock_record(scheme_id=2, scheme_name="Crop Scheme",
                                    department="D", scheme_type="T", crop="cotton")
    overlap_record = _make_mock_record(scheme_id=1, scheme_name="State Scheme",
                                       department="D", scheme_type="T", crop="cotton")

    def run_side_effect(cypher, params):
        if "State" in cypher:
            return iter([state_record])
        return iter([crop_record, overlap_record])

    mock_session = _mock_session()
    mock_session.run.side_effect = run_side_effect

    with patch("app.ai.neo4j.repository.get_session", return_value=mock_session):
        results = find_schemes_for_farmer(state="Telangana", crop="cotton")

    scheme_ids = {r["scheme_id"] for r in results}
    assert 1 in scheme_ids
    assert 2 in scheme_ids


def test_find_schemes_for_farmer_returns_empty_when_neither_given():
    from app.ai.neo4j.repository import find_schemes_for_farmer

    results = find_schemes_for_farmer(state=None, crop=None)
    assert results == []


# ---------------------------------------------------------------------------
# F. Ingestion — domain-level helpers
# ---------------------------------------------------------------------------

def _make_scheme_obj(scheme_id=1, name="Test", department="Dept",
                     state="Telangana", scheme_type="Financial Assistance",
                     is_active=True, criteria=None):
    scheme = Mock()
    scheme.id = scheme_id
    scheme.name = name
    scheme.department = department
    scheme.state = state
    scheme.scheme_type = scheme_type
    scheme.is_active = is_active
    scheme.eligibility_criteria = criteria or []
    return scheme


def _make_profile_obj(user_id=1, state="Telangana", district="Hyd",
                      primary_crop="cotton", secondary_crop=None,
                      land_ownership="owned", farming_type="organic"):
    profile = Mock()
    profile.user_id = user_id
    profile.state = state
    profile.district = district
    profile.primary_crop = primary_crop
    profile.secondary_crop = secondary_crop
    profile.land_ownership = land_ownership
    profile.farming_type = farming_type
    return profile


def _make_document_obj(document_id="abc123", filename="f.pdf",
                       original_filename="Original.pdf"):
    doc = Mock()
    doc.document_id = document_id
    doc.filename = filename
    doc.original_filename = original_filename
    return doc


def test_ingest_scheme_calls_upsert_scheme():
    from app.ai.neo4j.ingestion import ingest_scheme

    scheme = _make_scheme_obj()
    mock_session = _mock_session()
    with patch("app.ai.neo4j.repository.get_session", return_value=mock_session):
        ingest_scheme(scheme)

    assert mock_session.run.call_count >= 1


def test_ingest_scheme_extracts_crop_from_eligibility_criteria():
    from app.ai.neo4j.ingestion import ingest_scheme, _extract_crop_values

    crit = Mock()
    crit.field_name = "primary_crop"
    crit.expected_value = "cotton,wheat"
    scheme = _make_scheme_obj(criteria=[crit])

    crops = _extract_crop_values([crit])
    assert "cotton" in crops
    assert "wheat" in crops


def test_ingest_scheme_skips_when_neo4j_unavailable():
    from app.ai.neo4j.ingestion import ingest_scheme
    from app.ai.neo4j.client import GraphDatabaseUnavailableError

    scheme = _make_scheme_obj()
    with patch("app.ai.neo4j.ingestion.upsert_scheme",
               side_effect=GraphDatabaseUnavailableError("down")):
        with pytest.raises(GraphDatabaseUnavailableError):
            ingest_scheme(scheme)


def test_ingest_farmer_profile_calls_upsert_farmer():
    from app.ai.neo4j.ingestion import ingest_farmer_profile

    profile = _make_profile_obj()
    mock_session = _mock_session()
    with patch("app.ai.neo4j.repository.get_session", return_value=mock_session):
        ingest_farmer_profile(profile)

    assert mock_session.run.call_count >= 1


def test_ingest_document_metadata_creates_document_node():
    from app.ai.neo4j.ingestion import ingest_document_metadata

    doc = _make_document_obj()
    mock_session = _mock_session()
    with patch("app.ai.neo4j.repository.get_session", return_value=mock_session):
        ingest_document_metadata(doc, scheme_ids=[])

    assert mock_session.run.call_count >= 1


def test_remove_document_from_graph_swallows_unavailability():
    from app.ai.neo4j.ingestion import remove_document_from_graph
    from app.ai.neo4j.client import GraphDatabaseUnavailableError

    with patch("app.ai.neo4j.ingestion.delete_document_node",
               side_effect=GraphDatabaseUnavailableError("down")):
        remove_document_from_graph("abc123")  # must NOT raise


def test_bulk_ingest_schemes_returns_counts():
    from app.ai.neo4j.ingestion import bulk_ingest_schemes
    from app.ai.neo4j.client import GraphDatabaseError

    schemes = [_make_scheme_obj(scheme_id=i) for i in range(3)]
    call_count = [0]

    def side_effect(scheme):
        call_count[0] += 1
        if call_count[0] == 2:
            raise GraphDatabaseError("transient")

    with patch("app.ai.neo4j.ingestion.ingest_scheme", side_effect=side_effect):
        success, failure = bulk_ingest_schemes(schemes)

    assert success == 2
    assert failure == 1


# ---------------------------------------------------------------------------
# G. GraphRAG service
# ---------------------------------------------------------------------------

def test_graph_rag_search_returns_qdrant_result_when_neo4j_unavailable():
    """If Neo4j is unavailable, the result still contains Qdrant context."""
    from app.rag.graph_rag_service import graph_rag_search
    from app.ai.neo4j.client import GraphDatabaseUnavailableError
    from app.rag.rag_service import RagResult

    qdrant_result = RagResult(
        context="DOCUMENT KNOWLEDGE:\n[Source: test.pdf, page 1]\nSome text.",
        sources=["test.pdf"],
        raw_sources=[{"filename": "test.pdf", "page_number": 1, "chunk_index": 0}],
    )

    with patch("app.rag.graph_rag_service.try_search_knowledge_base", return_value=qdrant_result):
        with patch("app.rag.graph_rag_service.get_graph_context_for_query",
                   side_effect=GraphDatabaseUnavailableError("down")):
            result = graph_rag_search("how to apply", state="Telangana", crop="cotton")

    assert result.vector_used is True
    assert result.graph_used is False
    assert "DOCUMENT KNOWLEDGE" in result.context
    assert len(result.raw_sources) == 1


def test_graph_rag_search_includes_graph_context_when_available():
    """When Neo4j returns results, they appear in the fused context."""
    from app.rag.graph_rag_service import graph_rag_search
    from app.rag.rag_service import RagResult

    qdrant_result = RagResult(context="DOCUMENT KNOWLEDGE:\nSome doc.", sources=[], raw_sources=[])
    graph_results = [
        {
            "scheme_id": 1, "scheme_name": "PM-KISAN", "department": "Agri",
            "scheme_type": "Financial Assistance", "match_reason": "state",
            "states": ["All India"], "crops": [], "categories": [], "documents": [],
        }
    ]

    with patch("app.rag.graph_rag_service.try_search_knowledge_base", return_value=qdrant_result):
        with patch("app.rag.graph_rag_service.get_graph_context_for_query", return_value=graph_results):
            result = graph_rag_search("benefits for farmers", state="Telangana")

    assert result.graph_used is True
    assert result.vector_used is True
    assert "GRAPH KNOWLEDGE" in result.context
    assert "DOCUMENT KNOWLEDGE" in result.context


def test_graph_rag_search_graph_context_appears_before_document_context():
    """Graph knowledge must be listed before document knowledge in the fused context."""
    from app.rag.graph_rag_service import graph_rag_search
    from app.rag.rag_service import RagResult

    qdrant_result = RagResult(context="DOCUMENT KNOWLEDGE:\nDoc.", sources=[], raw_sources=[])
    graph_results = [{"scheme_id": 1, "scheme_name": "S", "department": "D",
                      "scheme_type": "T", "match_reason": "state",
                      "states": ["Telangana"], "crops": [], "categories": [], "documents": []}]

    with patch("app.rag.graph_rag_service.try_search_knowledge_base", return_value=qdrant_result):
        with patch("app.rag.graph_rag_service.get_graph_context_for_query", return_value=graph_results):
            result = graph_rag_search("query", state="Telangana")

    graph_pos = result.context.find("GRAPH KNOWLEDGE")
    doc_pos = result.context.find("DOCUMENT KNOWLEDGE")
    assert graph_pos < doc_pos


def test_try_graph_rag_search_returns_none_when_no_context():
    """try_graph_rag_search must return None (not empty GraphRagResult) when nothing found."""
    from app.rag.graph_rag_service import try_graph_rag_search

    with patch("app.rag.graph_rag_service.try_search_knowledge_base", return_value=None):
        with patch("app.rag.graph_rag_service.get_graph_context_for_query", return_value=[]):
            result = try_graph_rag_search("unrelated query")

    assert result is None


def test_graph_rag_sources_contain_provenance():
    """Sources returned from graph search must be labelled with [graph] tag."""
    from app.rag.graph_rag_service import graph_rag_search
    from app.rag.rag_service import RagResult

    qdrant_result = RagResult(context="DOCUMENT KNOWLEDGE:\nDoc.", sources=[], raw_sources=[])
    graph_results = [{"scheme_id": 1, "scheme_name": "PM-KISAN", "department": "D",
                      "scheme_type": "T", "match_reason": "state",
                      "states": [], "crops": [], "categories": [], "documents": []}]

    with patch("app.rag.graph_rag_service.try_search_knowledge_base", return_value=qdrant_result):
        with patch("app.rag.graph_rag_service.get_graph_context_for_query", return_value=graph_results):
            result = graph_rag_search("query")

    graph_sources = [s for s in result.sources if "[graph]" in s]
    assert len(graph_sources) >= 1


def test_graph_rag_fallback_completely_when_both_fail():
    """Even if both Qdrant and Neo4j fail, graph_rag_search must not raise."""
    from app.rag.graph_rag_service import graph_rag_search
    from app.ai.neo4j.client import GraphDatabaseUnavailableError

    with patch("app.rag.graph_rag_service.try_search_knowledge_base", return_value=None):
        with patch("app.rag.graph_rag_service.get_graph_context_for_query",
                   side_effect=GraphDatabaseUnavailableError("down")):
            result = graph_rag_search("query")

    assert result.context == ""
    assert result.graph_used is False
    assert result.vector_used is False


# ---------------------------------------------------------------------------
# H. GraphRAG API endpoints
# ---------------------------------------------------------------------------

def test_graph_search_endpoint_requires_authentication(client):
    resp = client.post("/api/rag/graph-search", json={"state": "Telangana"})
    assert resp.status_code == 401


def test_graph_rag_endpoint_requires_authentication(client):
    resp = client.post("/api/rag/graph-rag", json={"query": "schemes for farmers"})
    assert resp.status_code == 401


def test_graph_search_endpoint_returns_results(client, db_session):
    from tests.api.test_profile import farmer_token, auth_headers

    token = farmer_token(client, email="graph-search-test@example.com")
    graph_results = [
        {"scheme_id": 1, "scheme_name": "Test", "department": "D",
         "scheme_type": "T", "match_reason": "state",
         "states": ["Telangana"], "crops": [], "categories": [], "documents": []}
    ]

    with patch("app.api.routes.rag.get_graph_context_for_query", return_value=graph_results):
        resp = client.post(
            "/api/rag/graph-search",
            json={"state": "Telangana"},
            headers=auth_headers(token),
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert "results" in payload
    assert "total" in payload
    assert payload["total"] == 1


def test_graph_search_endpoint_handles_neo4j_unavailable(client, db_session):
    from tests.api.test_profile import farmer_token, auth_headers
    from app.ai.neo4j.client import GraphDatabaseUnavailableError

    token = farmer_token(client, email="graph-search-unavail@example.com")

    with patch("app.api.routes.rag.get_graph_context_for_query",
               side_effect=GraphDatabaseUnavailableError("down")):
        resp = client.post(
            "/api/rag/graph-search",
            json={"state": "Telangana"},
            headers=auth_headers(token),
        )

    assert resp.status_code == 503


def test_graph_rag_endpoint_returns_context(client, db_session):
    from tests.api.test_profile import farmer_token, auth_headers
    from app.rag.graph_rag_service import GraphRagResult

    token = farmer_token(client, email="graph-rag-test@example.com")
    fake_result = GraphRagResult(
        context="GRAPH KNOWLEDGE:\nSome graph.\n\nDOCUMENT KNOWLEDGE:\nSome doc.",
        sources=["Test Scheme [graph]", "doc.pdf"],
        raw_sources=[{"filename": "doc.pdf", "page_number": 1, "chunk_index": 0}],
        graph_used=True,
        vector_used=True,
    )

    with patch("app.api.routes.rag.graph_rag_search", return_value=fake_result):
        resp = client.post(
            "/api/rag/graph-rag",
            json={"query": "how to apply for PM-KISAN"},
            headers=auth_headers(token),
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert "context" in payload
    assert payload["graph_used"] is True
    assert payload["vector_used"] is True
    assert len(payload["sources"]) == 2


def test_graph_rag_endpoint_empty_query_returns_422(client, db_session):
    from tests.api.test_profile import farmer_token, auth_headers

    token = farmer_token(client, email="graph-rag-empty@example.com")
    resp = client.post(
        "/api/rag/graph-rag",
        json={"query": "   "},
        headers=auth_headers(token),
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# I. Assistant integration — GraphRAG used for document queries
# ---------------------------------------------------------------------------

@patch("app.services.assistant_service.generate_assistant_response", return_value="GraphRAG answer.")
def test_assistant_uses_graph_rag_for_document_queries(mock_generate, client, db_session):
    """When a message contains RAG keywords, the assistant should call try_graph_rag_search."""
    from tests.api.test_profile import farmer_token, auth_headers
    from tests.api.test_schemes import seed_test_scheme
    from app.rag.graph_rag_service import GraphRagResult

    seed_test_scheme(db_session, name="GraphRAG Integration Scheme")
    token = farmer_token(client, email="graphrag-assistant@example.com")
    fake_graph_result = GraphRagResult(
        context="GRAPH KNOWLEDGE:\nScheme info.",
        sources=["GraphRAG Integration Scheme [graph]"],
        raw_sources=[],
        graph_used=True,
        vector_used=False,
    )

    with patch("app.services.assistant_service.try_graph_rag_search", return_value=fake_graph_result):
        resp = client.post(
            "/api/assistant/chat",
            json={"message": "What documents do I need to apply?"},
            headers=auth_headers(token),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"] == "GraphRAG answer."


@patch("app.services.assistant_service.generate_assistant_response", return_value="Fallback answer.")
def test_assistant_falls_back_to_qdrant_when_graph_rag_returns_none(mock_generate, client, db_session):
    """When graph_rag returns None, assistant should fall back to try_search_knowledge_base."""
    from tests.api.test_profile import farmer_token, auth_headers
    from tests.api.test_schemes import seed_test_scheme
    from app.rag.rag_service import RagResult

    seed_test_scheme(db_session, name="Fallback Qdrant Scheme")
    token = farmer_token(client, email="qdrant-fallback@example.com")

    qdrant_result = RagResult(
        context="DOCUMENT KNOWLEDGE:\nQdrant doc.",
        sources=["fallback.pdf"],
        raw_sources=[{"filename": "fallback.pdf", "page_number": 1, "chunk_index": 0}],
    )

    with patch("app.services.assistant_service.try_graph_rag_search", return_value=None):
        with patch("app.services.assistant_service.try_search_knowledge_base",
                   return_value=qdrant_result):
            resp = client.post(
                "/api/assistant/chat",
                json={"message": "How to apply for schemes?"},
                headers=auth_headers(token),
            )

    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# J. Regression — existing Qdrant RAG tests unaffected
# ---------------------------------------------------------------------------

def test_existing_qdrant_search_endpoint_still_works(client, db_session):
    """POST /api/rag/search must still work after GraphRAG addition."""
    from tests.api.test_profile import farmer_token, auth_headers

    token = farmer_token(client, email="qdrant-reg-test@example.com")

    with patch("app.api.routes.rag.retrieve_document_chunks",
               return_value=[]):
        resp = client.post(
            "/api/rag/search",
            json={"query": "any query", "top_k": 3},
            headers=auth_headers(token),
        )

    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_try_search_knowledge_base_unchanged():
    """Existing Qdrant-only function must remain callable and return correct type."""
    from app.rag.rag_service import try_search_knowledge_base

    with patch("app.rag.embeddings.settings.gemini_api_key", ""):
        result = try_search_knowledge_base("query")

    assert result is None  # no key configured → RetrievalError → None
