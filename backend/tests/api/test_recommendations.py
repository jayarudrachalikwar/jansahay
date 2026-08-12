"""
Phase 10 — Recommendations endpoint tests.

GET /api/recommendations
GET /api/recommendations/summary

The recommendation logic itself is tested indirectly through test_schemes.py.
These tests focus on the route layer: auth, RBAC, response shape, and profile
requirement handling.
"""
from __future__ import annotations

from unittest.mock import patch

from tests.api.test_profile import SAMPLE_PROFILE, admin_token, auth_headers, farmer_token
from tests.api.test_schemes import seed_test_scheme

RECS_ENDPOINT = "/api/recommendations"
SUMMARY_ENDPOINT = "/api/recommendations/summary"


# ---------------------------------------------------------------------------
# A. Auth / RBAC
# ---------------------------------------------------------------------------

def test_unauthenticated_recommendations_returns_401(client):
    assert client.get(RECS_ENDPOINT).status_code == 401


def test_unauthenticated_summary_returns_401(client):
    assert client.get(SUMMARY_ENDPOINT).status_code == 401


def test_admin_recommendations_returns_403(client, db_session):
    token = admin_token(client, db_session, email="admin-recs-403@example.com")
    assert client.get(RECS_ENDPOINT, headers=auth_headers(token)).status_code == 403


def test_admin_summary_returns_403(client, db_session):
    token = admin_token(client, db_session, email="admin-summary-403@example.com")
    assert client.get(SUMMARY_ENDPOINT, headers=auth_headers(token)).status_code == 403


# ---------------------------------------------------------------------------
# B. Profile requirement
# ---------------------------------------------------------------------------

def test_recommendations_without_profile_returns_404(client):
    token = farmer_token(client, email="recs-no-profile@example.com")
    resp = client.get(RECS_ENDPOINT, headers=auth_headers(token))
    assert resp.status_code == 404
    assert "profile" in resp.json()["detail"].lower()


def test_summary_without_profile_returns_404(client):
    token = farmer_token(client, email="summary-no-profile@example.com")
    resp = client.get(SUMMARY_ENDPOINT, headers=auth_headers(token))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# C. Successful responses
# ---------------------------------------------------------------------------

def test_farmer_with_profile_gets_recommendations(client, db_session):
    seed_test_scheme(db_session, name="Rec Route Scheme")
    token = farmer_token(client, email="recs-with-profile@example.com")
    client.post("/api/profile", json=SAMPLE_PROFILE, headers=auth_headers(token))

    resp = client.get(RECS_ENDPOINT, headers=auth_headers(token))
    assert resp.status_code == 200
    payload = resp.json()
    assert "recommendations" in payload
    assert "total" in payload
    assert isinstance(payload["recommendations"], list)


def test_recommendations_response_structure(client, db_session):
    seed_test_scheme(db_session, name="Rec Structure Scheme")
    token = farmer_token(client, email="recs-structure@example.com")
    client.post("/api/profile", json=SAMPLE_PROFILE, headers=auth_headers(token))

    resp = client.get(RECS_ENDPOINT, headers=auth_headers(token))
    assert resp.status_code == 200
    recs = resp.json()["recommendations"]
    assert len(recs) >= 1
    item = recs[0]
    assert "scheme" in item
    assert "relevance_score" in item
    assert "eligible" in item
    assert "summary" in item
    assert "id" in item["scheme"]
    assert "name" in item["scheme"]
    assert 0 <= item["relevance_score"] <= 100


def test_summary_returns_at_most_5_recommendations(client, db_session):
    for i in range(6):
        seed_test_scheme(db_session, name=f"Summary Scheme {i}")
    token = farmer_token(client, email="summary-limit@example.com")
    client.post("/api/profile", json=SAMPLE_PROFILE, headers=auth_headers(token))

    resp = client.get(SUMMARY_ENDPOINT, headers=auth_headers(token))
    assert resp.status_code == 200
    assert len(resp.json()["recommendations"]) <= 5


def test_recommendations_limit_param_respected(client, db_session):
    for i in range(4):
        seed_test_scheme(db_session, name=f"Limit Scheme {i}")
    token = farmer_token(client, email="recs-limit@example.com")
    client.post("/api/profile", json=SAMPLE_PROFILE, headers=auth_headers(token))

    resp = client.get(RECS_ENDPOINT + "?limit=2", headers=auth_headers(token))
    assert resp.status_code == 200
    assert len(resp.json()["recommendations"]) <= 2


def test_recommendations_delegates_to_existing_service(client, db_session):
    """
    Verify the route delegates to get_scheme_recommendations without
    duplicating logic — done by checking both /api/schemes/recommendations
    and /api/recommendations return the same data.
    """
    seed_test_scheme(db_session, name="Delegation Check Scheme")
    token = farmer_token(client, email="recs-delegation@example.com")
    client.post("/api/profile", json=SAMPLE_PROFILE, headers=auth_headers(token))

    r1 = client.get("/api/schemes/recommendations", headers=auth_headers(token)).json()
    r2 = client.get(RECS_ENDPOINT, headers=auth_headers(token)).json()

    # Both should return same number of recommendations for same data
    assert r1["total"] == r2["total"]
