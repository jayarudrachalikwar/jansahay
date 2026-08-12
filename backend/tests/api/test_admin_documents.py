"""
Phase 7 — Admin Document Management tests.

Coverage:
  - Authentication: unauthenticated → 401, farmer → 403, admin → success
  - Upload validation: non-PDF, empty file, oversized, valid PDF
  - Document list / detail
  - Status update (activate / deactivate)
  - Re-ingestion (success and failure paths)
  - Invalid document ID → 404
  - RAG metadata: indexed chunks contain document_id, filename, page_number, chunk_index
  - Phase 1–6 regression: existing tests are not duplicated here but the
    conftest wires all models, so the full suite remains intact
"""
from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import pytest

from tests.api.test_profile import admin_token, auth_headers, farmer_token

# ---------------------------------------------------------------------------
# Minimal valid PDF bytes (magic header only — enough for the magic-byte check)
# ---------------------------------------------------------------------------
MINIMAL_PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n0 1\n0000000000 65535 f \ntrailer\n<< /Size 1 /Root 1 0 R >>\nstartxref\n9\n%%EOF"

UPLOAD_ENDPOINT = "/api/admin/documents"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _upload(client, token: str, content: bytes, filename: str = "test.pdf", content_type: str = "application/pdf"):
    return client.post(
        UPLOAD_ENDPOINT,
        files={"file": (filename, io.BytesIO(content), content_type)},
        headers=auth_headers(token),
    )


def _seed_document(client, token: str, *, content: bytes = MINIMAL_PDF, filename: str = "test_doc.pdf") -> dict:
    resp = _upload(client, token, content, filename=filename)
    assert resp.status_code == 201, resp.json()
    return resp.json()


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def test_unauthenticated_upload_returns_401(client):
    resp = client.post(
        UPLOAD_ENDPOINT,
        files={"file": ("test.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")},
    )
    assert resp.status_code == 401


def test_unauthenticated_list_returns_401(client):
    resp = client.get(UPLOAD_ENDPOINT)
    assert resp.status_code == 401


def test_unauthenticated_detail_returns_401(client):
    resp = client.get(f"{UPLOAD_ENDPOINT}/1")
    assert resp.status_code == 401


def test_farmer_upload_returns_403(client):
    token = farmer_token(client, email="farmer-upload-rbac@example.com")
    resp = _upload(client, token, MINIMAL_PDF)
    assert resp.status_code == 403


def test_farmer_list_returns_403(client):
    token = farmer_token(client, email="farmer-list-rbac@example.com")
    resp = client.get(UPLOAD_ENDPOINT, headers=auth_headers(token))
    assert resp.status_code == 403


def test_farmer_detail_returns_403(client):
    token = farmer_token(client, email="farmer-detail-rbac@example.com")
    resp = client.get(f"{UPLOAD_ENDPOINT}/1", headers=auth_headers(token))
    assert resp.status_code == 403


def test_farmer_status_update_returns_403(client):
    token = farmer_token(client, email="farmer-status-rbac@example.com")
    resp = client.patch(
        f"{UPLOAD_ENDPOINT}/1/status",
        json={"is_active": False},
        headers=auth_headers(token),
    )
    assert resp.status_code == 403


def test_farmer_ingest_returns_403(client):
    token = farmer_token(client, email="farmer-ingest-rbac@example.com")
    resp = client.post(f"{UPLOAD_ENDPOINT}/1/ingest", headers=auth_headers(token))
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Upload validation
# ---------------------------------------------------------------------------

def test_non_pdf_content_type_rejected(client, db_session):
    token = admin_token(client, db_session, email="admin-non-pdf@example.com")
    resp = _upload(client, token, b"not a pdf at all", filename="file.txt", content_type="text/plain")
    assert resp.status_code == 400
    assert "PDF" in resp.json()["detail"]


def test_non_pdf_magic_bytes_rejected(client, db_session):
    """Correct content-type but wrong magic bytes — must be rejected."""
    token = admin_token(client, db_session, email="admin-magic-bytes@example.com")
    resp = _upload(client, token, b"Not a PDF but pretending", filename="fake.pdf", content_type="application/pdf")
    assert resp.status_code == 400
    assert "PDF" in resp.json()["detail"]


def test_empty_file_rejected(client, db_session):
    token = admin_token(client, db_session, email="admin-empty@example.com")
    resp = _upload(client, token, b"", filename="empty.pdf", content_type="application/pdf")
    assert resp.status_code == 400


def test_oversized_file_rejected(client, db_session, monkeypatch):
    monkeypatch.setattr("app.services.document_service.settings.max_upload_size_mb", 0)
    # 0 MB limit → any non-empty file should be rejected
    token = admin_token(client, db_session, email="admin-oversized@example.com")
    resp = _upload(client, token, MINIMAL_PDF)
    assert resp.status_code == 400
    assert "size" in resp.json()["detail"].lower()


def test_valid_pdf_upload_returns_201(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.document_service.settings.document_upload_dir",
        str(tmp_path),
    )
    token = admin_token(client, db_session, email="admin-valid-upload@example.com")
    resp = _upload(client, token, MINIMAL_PDF, filename="valid.pdf")
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["original_filename"] == "valid.pdf"
    assert payload["status"] == "uploaded"
    assert payload["is_active"] is True
    assert payload["file_size"] == len(MINIMAL_PDF)


def test_upload_response_has_all_required_fields(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.document_service.settings.document_upload_dir", str(tmp_path))
    token = admin_token(client, db_session, email="admin-fields@example.com")
    resp = _upload(client, token, MINIMAL_PDF, filename="fields.pdf")
    assert resp.status_code == 201
    payload = resp.json()
    required = {"id", "filename", "original_filename", "content_type", "file_size",
                "page_count", "document_id", "status", "error_message", "is_active",
                "created_at", "updated_at", "ingested_at"}
    assert required.issubset(set(payload.keys()))


def test_server_filename_differs_from_original(client, db_session, tmp_path, monkeypatch):
    """The stored filename must be server-generated (UUID), not the user-supplied name."""
    monkeypatch.setattr("app.services.document_service.settings.document_upload_dir", str(tmp_path))
    token = admin_token(client, db_session, email="admin-safe-filename@example.com")
    resp = _upload(client, token, MINIMAL_PDF, filename="original_name.pdf")
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["filename"] != "original_name.pdf"
    assert payload["original_filename"] == "original_name.pdf"


# ---------------------------------------------------------------------------
# List documents
# ---------------------------------------------------------------------------

def test_admin_can_list_empty_documents(client, db_session):
    token = admin_token(client, db_session, email="admin-list-empty@example.com")
    resp = client.get(UPLOAD_ENDPOINT, headers=auth_headers(token))
    assert resp.status_code == 200
    payload = resp.json()
    assert "documents" in payload
    assert "total" in payload
    assert isinstance(payload["documents"], list)


def test_admin_list_includes_uploaded_document(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.document_service.settings.document_upload_dir", str(tmp_path))
    token = admin_token(client, db_session, email="admin-list-includes@example.com")
    _seed_document(client, token, filename="list_test.pdf")
    resp = client.get(UPLOAD_ENDPOINT, headers=auth_headers(token))
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total"] >= 1
    assert any(d["original_filename"] == "list_test.pdf" for d in payload["documents"])


# ---------------------------------------------------------------------------
# Document detail
# ---------------------------------------------------------------------------

def test_admin_can_get_document_detail(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.document_service.settings.document_upload_dir", str(tmp_path))
    token = admin_token(client, db_session, email="admin-detail@example.com")
    doc = _seed_document(client, token, filename="detail_test.pdf")
    resp = client.get(f"{UPLOAD_ENDPOINT}/{doc['id']}", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["id"] == doc["id"]
    assert resp.json()["original_filename"] == "detail_test.pdf"


def test_invalid_document_id_returns_404(client, db_session):
    token = admin_token(client, db_session, email="admin-404@example.com")
    resp = client.get(f"{UPLOAD_ENDPOINT}/999999", headers=auth_headers(token))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Status update (activate / deactivate)
# ---------------------------------------------------------------------------

def test_admin_can_deactivate_document(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.document_service.settings.document_upload_dir", str(tmp_path))
    token = admin_token(client, db_session, email="admin-deactivate@example.com")
    doc = _seed_document(client, token, filename="deactivate_test.pdf")

    resp = client.patch(
        f"{UPLOAD_ENDPOINT}/{doc['id']}/status",
        json={"is_active": False},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["is_active"] is False
    assert payload["status"] == "inactive"


def test_admin_can_reactivate_document(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.document_service.settings.document_upload_dir", str(tmp_path))
    token = admin_token(client, db_session, email="admin-reactivate@example.com")
    doc = _seed_document(client, token, filename="reactivate_test.pdf")

    # deactivate first
    client.patch(
        f"{UPLOAD_ENDPOINT}/{doc['id']}/status",
        json={"is_active": False},
        headers=auth_headers(token),
    )
    # now reactivate
    resp = client.patch(
        f"{UPLOAD_ENDPOINT}/{doc['id']}/status",
        json={"is_active": True},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True


def test_status_update_invalid_document_returns_404(client, db_session):
    token = admin_token(client, db_session, email="admin-status-404@example.com")
    resp = client.patch(
        f"{UPLOAD_ENDPOINT}/999999/status",
        json={"is_active": False},
        headers=auth_headers(token),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Re-ingestion
# ---------------------------------------------------------------------------

def test_successful_ingestion_sets_status_to_indexed(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.document_service.settings.document_upload_dir", str(tmp_path))
    token = admin_token(client, db_session, email="admin-ingest-success@example.com")
    doc = _seed_document(client, token, filename="ingest_success.pdf")

    mock_chunks = [
        MagicMock(
            document_id=doc["document_id"],
            filename="ingest_success.pdf",
            page_number=1,
            chunk_index=0,
            text="Sample text chunk.",
        )
    ]

    with (
        patch("app.services.document_service.load_pdf_document") as mock_load,
        patch("app.services.document_service.chunk_pages", return_value=mock_chunks),
        patch("app.services.document_service.generate_embeddings_batch", return_value=[[0.1] * 768]),
        patch("app.services.document_service.get_qdrant_client") as mock_client,
        patch("app.services.document_service.upsert_chunks", return_value=1),
    ):
        mock_load.return_value = MagicMock(
            pages=[MagicMock(filename="ingest_success.pdf", page_number=1, text="Sample.")],
            document_id=doc["document_id"],
        )
        mock_client.return_value = MagicMock()

        resp = client.post(
            f"{UPLOAD_ENDPOINT}/{doc['id']}/ingest",
            headers=auth_headers(token),
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "indexed"
    assert payload["page_count"] == 1
    assert payload["ingested_at"] is not None
    assert payload["error_message"] is None


def test_failed_ingestion_sets_status_to_failed(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.document_service.settings.document_upload_dir", str(tmp_path))
    token = admin_token(client, db_session, email="admin-ingest-fail@example.com")
    doc = _seed_document(client, token, filename="ingest_fail.pdf")

    with patch("app.services.document_service.load_pdf_document") as mock_load:
        from app.rag.document_loader import DocumentLoadError
        mock_load.side_effect = DocumentLoadError("No extractable text found in PDF: ingest_fail.pdf")

        resp = client.post(
            f"{UPLOAD_ENDPOINT}/{doc['id']}/ingest",
            headers=auth_headers(token),
        )

    assert resp.status_code == 422
    assert "text" in resp.json()["detail"].lower() or "extractable" in resp.json()["detail"].lower()

    # confirm DB record is marked failed
    detail_resp = client.get(f"{UPLOAD_ENDPOINT}/{doc['id']}", headers=auth_headers(token))
    assert detail_resp.json()["status"] == "failed"
    assert detail_resp.json()["error_message"] is not None


def test_reingest_replaces_existing_vectors_without_duplicating(client, db_session, tmp_path, monkeypatch):
    """Re-ingestion should call upsert_chunks (which uses deterministic point IDs)."""
    monkeypatch.setattr("app.services.document_service.settings.document_upload_dir", str(tmp_path))
    token = admin_token(client, db_session, email="admin-reingest-dedup@example.com")
    doc = _seed_document(client, token, filename="reingest_dedup.pdf")

    mock_chunks = [
        MagicMock(
            document_id=doc["document_id"],
            filename="reingest_dedup.pdf",
            page_number=1,
            chunk_index=0,
            text="Dedup chunk.",
        )
    ]

    with (
        patch("app.services.document_service.load_pdf_document") as mock_load,
        patch("app.services.document_service.chunk_pages", return_value=mock_chunks),
        patch("app.services.document_service.generate_embeddings_batch", return_value=[[0.1] * 768]),
        patch("app.services.document_service.get_qdrant_client") as mock_client,
        patch("app.services.document_service.upsert_chunks", return_value=1) as mock_upsert,
    ):
        mock_load.return_value = MagicMock(
            pages=[MagicMock(filename="reingest_dedup.pdf", page_number=1, text="Dedup.")],
            document_id=doc["document_id"],
        )
        mock_client.return_value = MagicMock()

        # First ingest
        resp1 = client.post(f"{UPLOAD_ENDPOINT}/{doc['id']}/ingest", headers=auth_headers(token))
        assert resp1.status_code == 200

        # Re-ingest
        resp2 = client.post(f"{UPLOAD_ENDPOINT}/{doc['id']}/ingest", headers=auth_headers(token))
        assert resp2.status_code == 200

    # upsert_chunks called twice — both times with the same deterministic point IDs
    assert mock_upsert.call_count == 2


def test_ingest_invalid_document_id_returns_404(client, db_session):
    token = admin_token(client, db_session, email="admin-ingest-404@example.com")
    resp = client.post(f"{UPLOAD_ENDPOINT}/999999/ingest", headers=auth_headers(token))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# RAG metadata on indexed chunks
# ---------------------------------------------------------------------------

def test_indexed_chunk_payload_contains_required_rag_metadata(client, db_session, tmp_path, monkeypatch):
    """
    Verify that chunks sent to upsert_chunks carry the four metadata fields
    required for RAG retrieval: document_id, filename, page_number, chunk_index.
    """
    monkeypatch.setattr("app.services.document_service.settings.document_upload_dir", str(tmp_path))
    token = admin_token(client, db_session, email="admin-rag-metadata@example.com")
    doc = _seed_document(client, token, filename="rag_metadata.pdf")

    captured_chunks = []

    def capture_upsert(client_obj, chunks, embeddings):
        captured_chunks.extend(chunks)
        return len(chunks)

    mock_chunks = [
        MagicMock(
            document_id=doc["document_id"],
            filename="rag_metadata.pdf",
            page_number=2,
            chunk_index=1,
            text="RAG metadata test.",
        )
    ]

    with (
        patch("app.services.document_service.load_pdf_document") as mock_load,
        patch("app.services.document_service.chunk_pages", return_value=mock_chunks),
        patch("app.services.document_service.generate_embeddings_batch", return_value=[[0.1] * 768]),
        patch("app.services.document_service.get_qdrant_client") as mock_client,
        patch("app.services.document_service.upsert_chunks", side_effect=capture_upsert),
    ):
        mock_load.return_value = MagicMock(
            pages=[MagicMock(filename="rag_metadata.pdf", page_number=2, text="RAG.")],
            document_id=doc["document_id"],
        )
        mock_client.return_value = MagicMock()
        client.post(f"{UPLOAD_ENDPOINT}/{doc['id']}/ingest", headers=auth_headers(token))

    assert len(captured_chunks) == 1
    chunk = captured_chunks[0]
    assert chunk.document_id == doc["document_id"]
    assert chunk.filename == "rag_metadata.pdf"
    assert chunk.page_number == 2
    assert chunk.chunk_index == 1


# ---------------------------------------------------------------------------
# Embedding / Qdrant unavailability
# ---------------------------------------------------------------------------

def test_ingestion_fails_gracefully_when_embedding_unavailable(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.document_service.settings.document_upload_dir", str(tmp_path))
    token = admin_token(client, db_session, email="admin-embed-fail@example.com")
    doc = _seed_document(client, token, filename="embed_fail.pdf")

    mock_chunks = [MagicMock(text="chunk")]

    with (
        patch("app.services.document_service.load_pdf_document") as mock_load,
        patch("app.services.document_service.chunk_pages", return_value=mock_chunks),
        patch(
            "app.services.document_service.generate_embeddings_batch",
            side_effect=Exception("Embedding service down"),
        ),
    ):
        mock_load.return_value = MagicMock(
            pages=[MagicMock(filename="embed_fail.pdf", page_number=1, text="text.")],
            document_id=doc["document_id"],
        )
        resp = client.post(f"{UPLOAD_ENDPOINT}/{doc['id']}/ingest", headers=auth_headers(token))

    assert resp.status_code == 422
    detail_resp = client.get(f"{UPLOAD_ENDPOINT}/{doc['id']}", headers=auth_headers(token))
    assert detail_resp.json()["status"] == "failed"


def test_ingestion_fails_gracefully_when_qdrant_unavailable(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.document_service.settings.document_upload_dir", str(tmp_path))
    token = admin_token(client, db_session, email="admin-qdrant-fail@example.com")
    doc = _seed_document(client, token, filename="qdrant_fail.pdf")

    mock_chunks = [MagicMock(text="chunk")]

    with (
        patch("app.services.document_service.load_pdf_document") as mock_load,
        patch("app.services.document_service.chunk_pages", return_value=mock_chunks),
        patch("app.services.document_service.generate_embeddings_batch", return_value=[[0.1] * 768]),
        patch(
            "app.services.document_service.get_qdrant_client",
            side_effect=Exception("Qdrant down"),
        ),
    ):
        mock_load.return_value = MagicMock(
            pages=[MagicMock(filename="qdrant_fail.pdf", page_number=1, text="text.")],
            document_id=doc["document_id"],
        )
        resp = client.post(f"{UPLOAD_ENDPOINT}/{doc['id']}/ingest", headers=auth_headers(token))

    assert resp.status_code == 422
    detail_resp = client.get(f"{UPLOAD_ENDPOINT}/{doc['id']}", headers=auth_headers(token))
    assert detail_resp.json()["status"] == "failed"


# ---------------------------------------------------------------------------
# Ownership / isolation
# ---------------------------------------------------------------------------

def test_document_list_does_not_expose_filesystem_paths(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.document_service.settings.document_upload_dir", str(tmp_path))
    token = admin_token(client, db_session, email="admin-no-paths@example.com")
    _seed_document(client, token, filename="no_path.pdf")
    resp = client.get(UPLOAD_ENDPOINT, headers=auth_headers(token))
    assert resp.status_code == 200
    serialized = str(resp.json()).lower()
    # tmp_path is a Windows/Linux absolute path — should not appear in response
    assert str(tmp_path).lower().replace("\\", "/") not in serialized
