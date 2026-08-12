"""
Phase 10 — Saved Schemes tests.

POST   /api/schemes/{id}/save
DELETE /api/schemes/{id}/save
"""
from __future__ import annotations

import pytest

from tests.api.test_profile import auth_headers, farmer_token, admin_token
from tests.api.test_schemes import seed_test_scheme

SCHEMES_BASE = "/api/schemes"


def _save(client, token, scheme_id):
    return client.post(f"{SCHEMES_BASE}/{scheme_id}/save", headers=auth_headers(token))


def _unsave(client, token, scheme_id):
    return client.delete(f"{SCHEMES_BASE}/{scheme_id}/save", headers=auth_headers(token))


# ---------------------------------------------------------------------------
# A. Auth / RBAC
# ---------------------------------------------------------------------------

def test_unauthenticated_save_returns_401(client, db_session):
    scheme = seed_test_scheme(db_session, name="Save Auth Scheme")
    resp = client.post(f"{SCHEMES_BASE}/{scheme.id}/save")
    assert resp.status_code == 401


def test_unauthenticated_unsave_returns_401(client, db_session):
    scheme = seed_test_scheme(db_session, name="Unsave Auth Scheme")
    resp = client.delete(f"{SCHEMES_BASE}/{scheme.id}/save")
    assert resp.status_code == 401


def test_admin_cannot_save_scheme(client, db_session):
    scheme = seed_test_scheme(db_session, name="Admin Save Scheme")
    token = admin_token(client, db_session, email="admin-save@example.com")
    resp = _save(client, token, scheme.id)
    assert resp.status_code == 403


def test_admin_cannot_unsave_scheme(client, db_session):
    scheme = seed_test_scheme(db_session, name="Admin Unsave Scheme")
    token = admin_token(client, db_session, email="admin-unsave@example.com")
    resp = _unsave(client, token, scheme.id)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# B. Save
# ---------------------------------------------------------------------------

def test_farmer_can_save_scheme(client, db_session):
    scheme = seed_test_scheme(db_session, name="Farmer Save Scheme")
    token = farmer_token(client, email="farmer-save@example.com")
    resp = _save(client, token, scheme.id)
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["scheme_id"] == scheme.id
    assert "id" in payload
    assert "saved_at" in payload
    assert payload["scheme"]["id"] == scheme.id


def test_save_response_has_required_fields(client, db_session):
    scheme = seed_test_scheme(db_session, name="Save Fields Scheme")
    token = farmer_token(client, email="farmer-save-fields@example.com")
    resp = _save(client, token, scheme.id)
    assert resp.status_code == 201
    payload = resp.json()
    required = {"id", "scheme_id", "saved_at", "scheme"}
    assert required.issubset(set(payload.keys()))
    assert {"id", "name", "short_description"}.issubset(set(payload["scheme"].keys()))


def test_save_nonexistent_scheme_returns_404(client):
    token = farmer_token(client, email="farmer-save-404@example.com")
    resp = _save(client, token, 999999)
    assert resp.status_code == 404


def test_duplicate_save_is_idempotent(client, db_session):
    scheme = seed_test_scheme(db_session, name="Duplicate Save Scheme")
    token = farmer_token(client, email="farmer-dup-save@example.com")
    r1 = _save(client, token, scheme.id)
    r2 = _save(client, token, scheme.id)
    # Both should succeed — second returns existing record
    assert r1.status_code == 201
    assert r2.status_code in (200, 201)
    # Same saved-scheme id
    assert r1.json()["id"] == r2.json()["id"]


# ---------------------------------------------------------------------------
# C. Unsave
# ---------------------------------------------------------------------------

def test_farmer_can_unsave_scheme(client, db_session):
    scheme = seed_test_scheme(db_session, name="Farmer Unsave Scheme")
    token = farmer_token(client, email="farmer-unsave@example.com")
    _save(client, token, scheme.id)
    resp = _unsave(client, token, scheme.id)
    assert resp.status_code == 204


def test_unsave_scheme_not_in_saved_list_returns_404(client, db_session):
    scheme = seed_test_scheme(db_session, name="Not Saved Scheme")
    token = farmer_token(client, email="farmer-unsave-404@example.com")
    resp = _unsave(client, token, scheme.id)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# D. Ownership — one farmer cannot see/modify another's saved records
# ---------------------------------------------------------------------------

def test_farmer_cannot_unsave_another_farmers_record(client, db_session):
    scheme = seed_test_scheme(db_session, name="Ownership Scheme")
    token_a = farmer_token(client, email="farmer-owner-a@example.com")
    token_b = farmer_token(client, email="farmer-owner-b@example.com")

    _save(client, token_a, scheme.id)
    # Farmer B tries to unsave Farmer A's record
    resp = _unsave(client, token_b, scheme.id)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# E. Save response includes scheme data
# ---------------------------------------------------------------------------

def test_save_response_scheme_name_matches(client, db_session):
    scheme = seed_test_scheme(db_session, name="Named Save Scheme")
    token = farmer_token(client, email="farmer-named-save@example.com")
    resp = _save(client, token, scheme.id)
    assert resp.status_code == 201
    assert resp.json()["scheme"]["name"] == "Named Save Scheme"


# ---------------------------------------------------------------------------
# F. List saved schemes
# ---------------------------------------------------------------------------

def test_farmer_can_list_saved_schemes(client, db_session):
    scheme = seed_test_scheme(db_session, name="List Save Scheme")
    token = farmer_token(client, email="farmer-list-saved@example.com")
    _save(client, token, scheme.id)

    resp = client.get("/api/saved-schemes", headers=auth_headers(token))
    assert resp.status_code == 200
    payload = resp.json()
    assert "saved_schemes" in payload
    assert "total" in payload
    assert payload["total"] >= 1
    saved_ids = [s["scheme_id"] for s in payload["saved_schemes"]]
    assert scheme.id in saved_ids


def test_unsaved_scheme_not_in_list(client, db_session):
    scheme = seed_test_scheme(db_session, name="Not Listed Saved Scheme")
    token = farmer_token(client, email="farmer-not-listed@example.com")

    resp = client.get("/api/saved-schemes", headers=auth_headers(token))
    assert resp.status_code == 200
    saved_ids = [s["scheme_id"] for s in resp.json()["saved_schemes"]]
    assert scheme.id not in saved_ids


def test_unauthenticated_list_saved_returns_401(client):
    resp = client.get("/api/saved-schemes")
    assert resp.status_code == 401


def test_admin_cannot_list_saved_schemes(client, db_session):
    token = admin_token(client, db_session, email="admin-list-saved@example.com")
    resp = client.get("/api/saved-schemes", headers=auth_headers(token))
    assert resp.status_code == 403


def test_farmer_only_sees_own_saved_schemes(client, db_session):
    scheme_a = seed_test_scheme(db_session, name="Own Saved A Scheme")
    scheme_b = seed_test_scheme(db_session, name="Own Saved B Scheme")
    token_a = farmer_token(client, email="own-saved-a@example.com")
    token_b = farmer_token(client, email="own-saved-b@example.com")

    _save(client, token_a, scheme_a.id)
    _save(client, token_b, scheme_b.id)

    resp_a = client.get("/api/saved-schemes", headers=auth_headers(token_a))
    saved_ids_a = [s["scheme_id"] for s in resp_a.json()["saved_schemes"]]
    assert scheme_a.id in saved_ids_a
    assert scheme_b.id not in saved_ids_a
