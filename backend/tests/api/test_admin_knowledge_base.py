"""
Phase 8 — Admin Knowledge Base Management tests.

Groups:
  A. Authentication / RBAC
  B. Search / filter on GET /admin/documents
  C. Chunk count endpoint GET /admin/documents/{id}/chunks
  D. Knowledge Base stats GET /admin/knowledge-base/stats
  E. Hard delete DELETE /admin/documents/{id}
  F. Regression — Phase 7 upload/ingest/status still works
"""
from __future__ import annotations

import io
from unittest.mock import MagicMock, call, patch

import pytest

from tests.api.test_profile import admin_token, auth_headers, farmer_token

MINIMAL_PDF = (
    b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
    b"xref\n0 1\n0000000000 65535 f \n"
    b"trailer\n<< /Size 1 /Root 1 0 R >>\nstartxref\n9\n%%EOF"
)
UPLOAD_ENDPOINT = "/api/admin/documents"
KB_STATS_ENDPOINT = "/api/admin/knowledge-base/stats"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _upload(client, token, content=MINIMAL_PDF, filename="kb_test.pdf"):
    return client.post(
        UPLOAD_ENDPOINT,
        files={"file": (filename, io.BytesIO(content), "application/pdf")},
        headers=auth_headers(token),
    )


def _seed(client, token, *, filename="seed.pdf", tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.document_service.settings.document_upload_dir",
        str(tmp_path),
    )
    resp = _upload(client, token, filename=filename)
    assert resp.status_code == 201, resp.json()
    return resp.json()


# ===========================================================================
# A. Authentication / RBAC
# ===========================================================================

def test_unauthenticated_kb_stats_returns_401(client):
    assert client.get(KB_STATS_ENDPOINT).status_code == 401


def test_farmer_kb_stats_returns_403(client):
    token = farmer_token(client, email="farmer-kb-stats@example.com")
    assert client.get(KB_STATS_ENDPOINT, headers=auth_headers(token)).status_code == 403


def test_unauthenticated_chunks_returns_401(client):
    assert client.get(f"{UPLOAD_ENDPOINT}/1/chunks").status_code == 401


def test_farmer_chunks_returns_403(client):
    token = farmer_token(client, email="farmer-chunks@example.com")
    assert (
        client.get(f"{UPLOAD_ENDPOINT}/1/chunks", headers=auth_headers(token)).status_code
        == 403
    )


def test_unauthenticated_delete_returns_401(client):
    assert client.delete(f"{UPLOAD_ENDPOINT}/1").status_code == 401


def test_farmer_delete_returns_403(client):
    token = farmer_token(client, email="farmer-delete@example.com")
    assert (
        client.delete(f"{UPLOAD_ENDPOINT}/1", headers=auth_headers(token)).status_code
        == 403
    )


def test_admin_can_access_kb_stats(client, db_session):
    token = admin_token(client, db_session, email="admin-kb-access@example.com")
    resp = client.get(KB_STATS_ENDPOINT, headers=auth_headers(token))
    assert resp.status_code == 200


# ===========================================================================
# B. Search / filter on GET /admin/documents
# ===========================================================================

def test_list_without_filters_returns_all(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.document_service.settings.document_upload_dir", str(tmp_path)
    )
    token = admin_token(client, db_session, email="admin-list-all@example.com")
    _upload(client, token, filename="filter_a.pdf")
    _upload(client, token, filename="filter_b.pdf")
    resp = client.get(UPLOAD_ENDPOINT, headers=auth_headers(token))
    assert resp.status_code == 200
    names = [d["original_filename"] for d in resp.json()["documents"]]
    assert "filter_a.pdf" in names
    assert "filter_b.pdf" in names


def test_filter_by_status_uploaded(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.document_service.settings.document_upload_dir", str(tmp_path)
    )
    token = admin_token(client, db_session, email="admin-filter-status@example.com")
    _upload(client, token, filename="status_filter.pdf")
    resp = client.get(
        UPLOAD_ENDPOINT, params={"status": "uploaded"}, headers=auth_headers(token)
    )
    assert resp.status_code == 200
    docs = resp.json()["documents"]
    assert all(d["status"] == "uploaded" for d in docs)
    assert any(d["original_filename"] == "status_filter.pdf" for d in docs)


def test_filter_by_invalid_status_returns_empty(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.document_service.settings.document_upload_dir", str(tmp_path)
    )
    token = admin_token(client, db_session, email="admin-invalid-status@example.com")
    _upload(client, token, filename="invalid_status.pdf")
    resp = client.get(
        UPLOAD_ENDPOINT, params={"status": "nonexistent_status"}, headers=auth_headers(token)
    )
    assert resp.status_code == 200
    assert resp.json()["documents"] == []


def test_search_by_filename_substring(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.document_service.settings.document_upload_dir", str(tmp_path)
    )
    token = admin_token(client, db_session, email="admin-search-name@example.com")
    _upload(client, token, filename="unique_xyzabc_scheme.pdf")
    _upload(client, token, filename="other_document.pdf")
    resp = client.get(
        UPLOAD_ENDPOINT, params={"search": "xyzabc"}, headers=auth_headers(token)
    )
    assert resp.status_code == 200
    docs = resp.json()["documents"]
    assert len(docs) >= 1
    assert all("xyzabc" in d["original_filename"] for d in docs)


def test_search_is_case_insensitive(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.document_service.settings.document_upload_dir", str(tmp_path)
    )
    token = admin_token(client, db_session, email="admin-search-case@example.com")
    _upload(client, token, filename="CaseTest_Doc.pdf")
    resp = client.get(
        UPLOAD_ENDPOINT, params={"search": "casetest"}, headers=auth_headers(token)
    )
    assert resp.status_code == 200
    assert any("CaseTest_Doc.pdf" in d["original_filename"] for d in resp.json()["documents"])


def test_combined_status_and_search_filter(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.document_service.settings.document_upload_dir", str(tmp_path)
    )
    token = admin_token(client, db_session, email="admin-combined-filter@example.com")
    _upload(client, token, filename="combined_target.pdf")
    resp = client.get(
        UPLOAD_ENDPOINT,
        params={"status": "uploaded", "search": "combined_target"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    docs = resp.json()["documents"]
    assert any(d["original_filename"] == "combined_target.pdf" for d in docs)
    assert all(d["status"] == "uploaded" for d in docs)


# ===========================================================================
# C. Chunk count endpoint  GET /admin/documents/{id}/chunks
# ===========================================================================

def test_chunks_invalid_document_returns_404(client, db_session):
    token = admin_token(client, db_session, email="admin-chunks-404@example.com")
    resp = client.get(f"{UPLOAD_ENDPOINT}/999999/chunks", headers=auth_headers(token))
    assert resp.status_code == 404


def test_chunks_returns_required_fields(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.document_service.settings.document_upload_dir", str(tmp_path)
    )
    token = admin_token(client, db_session, email="admin-chunks-fields@example.com")
    doc = _upload(client, token, filename="chunks_fields.pdf").json()

    with (
        patch("app.api.routes.admin.get_qdrant_client") as mock_client,
        patch("app.api.routes.admin.count_document_vectors", return_value=7),
        patch("app.api.routes.admin.collection_point_count", return_value=42),
    ):
        mock_client.return_value = MagicMock()
        resp = client.get(
            f"{UPLOAD_ENDPOINT}/{doc['id']}/chunks", headers=auth_headers(token)
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert set(payload.keys()) == {"document_id", "chunk_count", "collection_total"}
    assert payload["document_id"] == doc["document_id"]
    assert payload["chunk_count"] == 7
    assert payload["collection_total"] == 42


def test_chunks_scoped_to_document(client, db_session, tmp_path, monkeypatch):
    """count_document_vectors must be called with the document's document_id, not another's."""
    monkeypatch.setattr(
        "app.services.document_service.settings.document_upload_dir", str(tmp_path)
    )
    token = admin_token(client, db_session, email="admin-chunks-scope@example.com")
    doc = _upload(client, token, filename="scope_doc.pdf").json()

    captured = []

    def capture_count(client_obj, doc_id):
        captured.append(doc_id)
        return 3

    with (
        patch("app.api.routes.admin.get_qdrant_client", return_value=MagicMock()),
        patch("app.api.routes.admin.count_document_vectors", side_effect=capture_count),
        patch("app.api.routes.admin.collection_point_count", return_value=10),
    ):
        client.get(f"{UPLOAD_ENDPOINT}/{doc['id']}/chunks", headers=auth_headers(token))

    assert len(captured) == 1
    assert captured[0] == doc["document_id"]


def test_chunks_returns_zero_when_qdrant_unavailable(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.document_service.settings.document_upload_dir", str(tmp_path)
    )
    token = admin_token(client, db_session, email="admin-chunks-unavail@example.com")
    doc = _upload(client, token, filename="unavail_chunks.pdf").json()

    from app.rag.vector_store import VectorStoreUnavailableError

    with patch(
        "app.api.routes.admin.get_qdrant_client",
        side_effect=VectorStoreUnavailableError("down"),
    ):
        resp = client.get(
            f"{UPLOAD_ENDPOINT}/{doc['id']}/chunks", headers=auth_headers(token)
        )

    assert resp.status_code == 200
    assert resp.json()["chunk_count"] == 0
    assert resp.json()["collection_total"] == 0


# ===========================================================================
# D. Knowledge Base stats  GET /admin/knowledge-base/stats
# ===========================================================================

def test_kb_stats_response_has_required_fields(client, db_session):
    token = admin_token(client, db_session, email="admin-stats-fields@example.com")
    with (
        patch("app.api.routes.admin.get_qdrant_client", return_value=MagicMock()),
        patch("app.api.routes.admin.collection_point_count", return_value=0),
    ):
        resp = client.get(KB_STATS_ENDPOINT, headers=auth_headers(token))
    assert resp.status_code == 200
    payload = resp.json()
    assert "total_documents" in payload
    assert "by_status" in payload
    assert "total_indexed_chunks" in payload
    assert "qdrant_reachable" in payload


def test_kb_stats_counts_documents(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.document_service.settings.document_upload_dir", str(tmp_path)
    )
    token = admin_token(client, db_session, email="admin-stats-count@example.com")
    _upload(client, token, filename="stats_count_a.pdf")
    _upload(client, token, filename="stats_count_b.pdf")

    with (
        patch("app.api.routes.admin.get_qdrant_client", return_value=MagicMock()),
        patch("app.api.routes.admin.collection_point_count", return_value=0),
    ):
        resp = client.get(KB_STATS_ENDPOINT, headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["total_documents"] >= 2


def test_kb_stats_by_status_grouping(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.document_service.settings.document_upload_dir", str(tmp_path)
    )
    token = admin_token(client, db_session, email="admin-stats-group@example.com")
    _upload(client, token, filename="group_doc.pdf")

    with (
        patch("app.api.routes.admin.get_qdrant_client", return_value=MagicMock()),
        patch("app.api.routes.admin.collection_point_count", return_value=0),
    ):
        resp = client.get(KB_STATS_ENDPOINT, headers=auth_headers(token))
    by_status = resp.json()["by_status"]
    # All known statuses must be present in the grouping dict
    for s in ("uploaded", "processing", "indexed", "failed", "inactive"):
        assert s in by_status
    assert by_status["uploaded"] >= 1


def test_kb_stats_includes_chunk_count(client, db_session):
    token = admin_token(client, db_session, email="admin-stats-chunks@example.com")
    with (
        patch("app.api.routes.admin.get_qdrant_client", return_value=MagicMock()),
        patch("app.api.routes.admin.collection_point_count", return_value=99),
    ):
        resp = client.get(KB_STATS_ENDPOINT, headers=auth_headers(token))
    assert resp.json()["total_indexed_chunks"] == 99
    assert resp.json()["qdrant_reachable"] is True


def test_kb_stats_qdrant_unreachable_degrades_gracefully(client, db_session):
    token = admin_token(client, db_session, email="admin-stats-unreach@example.com")
    from app.rag.vector_store import VectorStoreUnavailableError

    with patch(
        "app.api.routes.admin.get_qdrant_client",
        side_effect=VectorStoreUnavailableError("down"),
    ):
        resp = client.get(KB_STATS_ENDPOINT, headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["qdrant_reachable"] is False
    assert resp.json()["total_indexed_chunks"] == 0


# ===========================================================================
# E. Hard delete  DELETE /admin/documents/{id}
# ===========================================================================

def test_delete_invalid_document_returns_404(client, db_session):
    token = admin_token(client, db_session, email="admin-delete-404@example.com")
    resp = client.delete(f"{UPLOAD_ENDPOINT}/999999", headers=auth_headers(token))
    assert resp.status_code == 404


def test_delete_success_returns_204(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.document_service.settings.document_upload_dir", str(tmp_path)
    )
    token = admin_token(client, db_session, email="admin-delete-204@example.com")
    doc = _upload(client, token, filename="delete_me.pdf").json()

    with (
        patch("app.services.document_service.get_qdrant_client", return_value=MagicMock()),
        patch("app.services.document_service.delete_document_vectors"),
    ):
        resp = client.delete(f"{UPLOAD_ENDPOINT}/{doc['id']}", headers=auth_headers(token))

    assert resp.status_code == 204


def test_delete_removes_db_record(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.document_service.settings.document_upload_dir", str(tmp_path)
    )
    token = admin_token(client, db_session, email="admin-delete-db@example.com")
    doc = _upload(client, token, filename="delete_db.pdf").json()

    with (
        patch("app.services.document_service.get_qdrant_client", return_value=MagicMock()),
        patch("app.services.document_service.delete_document_vectors"),
    ):
        client.delete(f"{UPLOAD_ENDPOINT}/{doc['id']}", headers=auth_headers(token))

    # DB record must be gone
    detail = client.get(f"{UPLOAD_ENDPOINT}/{doc['id']}", headers=auth_headers(token))
    assert detail.status_code == 404


def test_delete_removes_physical_file(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.document_service.settings.document_upload_dir", str(tmp_path)
    )
    token = admin_token(client, db_session, email="admin-delete-file@example.com")
    doc = _upload(client, token, filename="delete_file.pdf").json()

    # Confirm the file was written
    from pathlib import Path
    file_path = tmp_path / doc["filename"]
    assert file_path.exists()

    with (
        patch("app.services.document_service.get_qdrant_client", return_value=MagicMock()),
        patch("app.services.document_service.delete_document_vectors"),
    ):
        client.delete(f"{UPLOAD_ENDPOINT}/{doc['id']}", headers=auth_headers(token))

    # Physical file must be gone
    assert not file_path.exists()


def test_delete_invokes_qdrant_vector_cleanup(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.document_service.settings.document_upload_dir", str(tmp_path)
    )
    token = admin_token(client, db_session, email="admin-delete-qdrant@example.com")
    doc = _upload(client, token, filename="delete_qdrant.pdf").json()

    with (
        patch("app.services.document_service.get_qdrant_client", return_value=MagicMock()),
        patch("app.services.document_service.delete_document_vectors") as mock_del,
    ):
        client.delete(f"{UPLOAD_ENDPOINT}/{doc['id']}", headers=auth_headers(token))

    mock_del.assert_called_once()
    # The call must use the document's own document_id
    _, call_args = mock_del.call_args[0], mock_del.call_args
    assert doc["document_id"] in str(mock_del.call_args)


def test_delete_qdrant_failure_preserves_db_record(client, db_session, tmp_path, monkeypatch):
    """If Qdrant cleanup fails, the DB record must NOT be deleted."""
    monkeypatch.setattr(
        "app.services.document_service.settings.document_upload_dir", str(tmp_path)
    )
    token = admin_token(client, db_session, email="admin-delete-preserve@example.com")
    doc = _upload(client, token, filename="preserve_on_fail.pdf").json()

    from app.rag.vector_store import VectorStoreOperationError

    with (
        patch("app.services.document_service.get_qdrant_client", return_value=MagicMock()),
        patch(
            "app.services.document_service.delete_document_vectors",
            side_effect=VectorStoreOperationError("Qdrant delete failed"),
        ),
    ):
        resp = client.delete(f"{UPLOAD_ENDPOINT}/{doc['id']}", headers=auth_headers(token))

    # Route returns 503 when deletion service raises DocumentDeletionError
    assert resp.status_code == 503

    # DB record must still exist
    detail = client.get(f"{UPLOAD_ENDPOINT}/{doc['id']}", headers=auth_headers(token))
    assert detail.status_code == 200


def test_delete_does_not_affect_other_documents(client, db_session, tmp_path, monkeypatch):
    """Deleting document A must not touch document B's record."""
    monkeypatch.setattr(
        "app.services.document_service.settings.document_upload_dir", str(tmp_path)
    )
    token = admin_token(client, db_session, email="admin-delete-isolate@example.com")
    doc_a = _upload(client, token, filename="isolate_a.pdf").json()
    doc_b = _upload(client, token, filename="isolate_b.pdf").json()

    with (
        patch("app.services.document_service.get_qdrant_client", return_value=MagicMock()),
        patch("app.services.document_service.delete_document_vectors") as mock_del,
    ):
        client.delete(f"{UPLOAD_ENDPOINT}/{doc_a['id']}", headers=auth_headers(token))

    # Only doc_a's document_id should have been passed to delete_document_vectors
    assert mock_del.call_count == 1
    passed_doc_id = mock_del.call_args[0][1]
    assert passed_doc_id == doc_a["document_id"]
    assert passed_doc_id != doc_b["document_id"]

    # doc_b still exists in the DB
    assert (
        client.get(f"{UPLOAD_ENDPOINT}/{doc_b['id']}", headers=auth_headers(token)).status_code
        == 200
    )


def test_delete_missing_file_is_non_fatal(client, db_session, tmp_path, monkeypatch):
    """If the physical file is already gone, delete should still succeed."""
    monkeypatch.setattr(
        "app.services.document_service.settings.document_upload_dir", str(tmp_path)
    )
    token = admin_token(client, db_session, email="admin-delete-nofile@example.com")
    doc = _upload(client, token, filename="missing_file.pdf").json()

    # Remove the file manually before calling delete
    from pathlib import Path
    file_path = tmp_path / doc["filename"]
    if file_path.exists():
        file_path.unlink()

    with (
        patch("app.services.document_service.get_qdrant_client", return_value=MagicMock()),
        patch("app.services.document_service.delete_document_vectors"),
    ):
        resp = client.delete(f"{UPLOAD_ENDPOINT}/{doc['id']}", headers=auth_headers(token))

    assert resp.status_code == 204
    assert (
        client.get(f"{UPLOAD_ENDPOINT}/{doc['id']}", headers=auth_headers(token)).status_code
        == 404
    )


# ===========================================================================
# F. Regression — Phase 7 upload / ingest / status still works
# ===========================================================================

def test_phase7_upload_still_works(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.document_service.settings.document_upload_dir", str(tmp_path)
    )
    token = admin_token(client, db_session, email="admin-p7-upload@example.com")
    resp = _upload(client, token, filename="regression_upload.pdf")
    assert resp.status_code == 201
    assert resp.json()["status"] == "uploaded"


def test_phase7_ingest_still_works(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.document_service.settings.document_upload_dir", str(tmp_path)
    )
    token = admin_token(client, db_session, email="admin-p7-ingest@example.com")
    doc = _upload(client, token, filename="regression_ingest.pdf").json()

    mock_chunks = [
        MagicMock(
            document_id=doc["document_id"],
            filename="regression_ingest.pdf",
            page_number=1,
            chunk_index=0,
            text="Regression chunk.",
        )
    ]
    with (
        patch("app.services.document_service.load_pdf_document") as mock_load,
        patch("app.services.document_service.chunk_pages", return_value=mock_chunks),
        patch("app.services.document_service.generate_embeddings_batch", return_value=[[0.1] * 768]),
        patch("app.services.document_service.get_qdrant_client", return_value=MagicMock()),
        patch("app.services.document_service.upsert_chunks", return_value=1),
    ):
        mock_load.return_value = MagicMock(
            pages=[MagicMock(filename="regression_ingest.pdf", page_number=1, text="chunk.")],
            document_id=doc["document_id"],
        )
        resp = client.post(
            f"{UPLOAD_ENDPOINT}/{doc['id']}/ingest", headers=auth_headers(token)
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "indexed"


def test_phase7_status_update_still_works(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.document_service.settings.document_upload_dir", str(tmp_path)
    )
    token = admin_token(client, db_session, email="admin-p7-status@example.com")
    doc = _upload(client, token, filename="regression_status.pdf").json()
    resp = client.patch(
        f"{UPLOAD_ENDPOINT}/{doc['id']}/status",
        json={"is_active": False},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
    assert resp.json()["status"] == "inactive"
