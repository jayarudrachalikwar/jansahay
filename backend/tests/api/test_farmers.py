"""
Phase 9 — Admin Farmer Management tests.

Groups:
  A. Authentication / RBAC on GET /api/admin/farmers
  B. Authentication / RBAC on GET /api/admin/farmers/{id}
  C. List response structure and content
  D. Detail response structure and content
  E. Sensitive field exclusion
  F. Edge cases (unknown farmer, farmer without profile)
"""
from __future__ import annotations

from tests.api.test_profile import (
    SAMPLE_PROFILE,
    admin_token,
    auth_headers,
    farmer_token,
)

FARMERS_ENDPOINT = "/api/admin/farmers"


# ---------------------------------------------------------------------------
# A. Authentication / RBAC — list
# ---------------------------------------------------------------------------

def test_unauthenticated_farmer_list_returns_401(client):
    assert client.get(FARMERS_ENDPOINT).status_code == 401


def test_farmer_cannot_list_farmers(client):
    token = farmer_token(client, email="farmer-list-rbac@farmers.example.com")
    assert client.get(FARMERS_ENDPOINT, headers=auth_headers(token)).status_code == 403


def test_admin_can_list_farmers(client, db_session):
    token = admin_token(client, db_session, email="admin-list-farmers@example.com")
    resp = client.get(FARMERS_ENDPOINT, headers=auth_headers(token))
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# B. Authentication / RBAC — detail
# ---------------------------------------------------------------------------

def test_unauthenticated_farmer_detail_returns_401(client):
    assert client.get(f"{FARMERS_ENDPOINT}/1").status_code == 401


def test_farmer_cannot_access_farmer_detail(client):
    token = farmer_token(client, email="farmer-detail-rbac@farmers.example.com")
    assert client.get(f"{FARMERS_ENDPOINT}/1", headers=auth_headers(token)).status_code == 403


def test_unknown_farmer_returns_404(client, db_session):
    token = admin_token(client, db_session, email="admin-404-farmer@example.com")
    resp = client.get(f"{FARMERS_ENDPOINT}/999999", headers=auth_headers(token))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# C. List response structure and content
# ---------------------------------------------------------------------------

def test_farmer_list_returns_expected_structure(client, db_session):
    token = admin_token(client, db_session, email="admin-list-struct@example.com")
    resp = client.get(FARMERS_ENDPOINT, headers=auth_headers(token))
    assert resp.status_code == 200
    payload = resp.json()
    assert "farmers" in payload
    assert "total" in payload
    assert isinstance(payload["farmers"], list)
    assert isinstance(payload["total"], int)


def test_registered_farmer_appears_in_list(client, db_session):
    # Register a farmer then check admin can see them
    farmer_tok = farmer_token(client, email="visible-farmer@farmers.example.com")
    admin_tok = admin_token(client, db_session, email="admin-sees-farmer@example.com")

    resp = client.get(FARMERS_ENDPOINT, headers=auth_headers(admin_tok))
    assert resp.status_code == 200
    emails = [f["email"] for f in resp.json()["farmers"]]
    assert "visible-farmer@farmers.example.com" in emails


def test_list_item_has_required_fields(client, db_session):
    farmer_token(client, email="list-fields-farmer@farmers.example.com")
    admin_tok = admin_token(client, db_session, email="admin-list-fields@example.com")

    resp = client.get(FARMERS_ENDPOINT, headers=auth_headers(admin_tok))
    assert resp.status_code == 200
    farmers = resp.json()["farmers"]
    assert len(farmers) >= 1
    item = farmers[0]
    required_fields = {"id", "full_name", "email", "is_active", "created_at", "has_profile"}
    assert required_fields.issubset(set(item.keys()))


def test_admin_is_not_included_in_farmer_list(client, db_session):
    """Admins must not appear in the farmer list even if seeded in the same DB."""
    admin_tok = admin_token(client, db_session, email="admin-not-listed@example.com")

    resp = client.get(FARMERS_ENDPOINT, headers=auth_headers(admin_tok))
    assert resp.status_code == 200
    roles_returned = [f.get("role") for f in resp.json()["farmers"]]
    # role is not exposed but we can check the admin email is absent
    emails = [f["email"] for f in resp.json()["farmers"]]
    assert "admin-not-listed@example.com" not in emails


# ---------------------------------------------------------------------------
# D. Detail response structure and content
# ---------------------------------------------------------------------------

def test_admin_can_get_farmer_detail(client, db_session):
    farmer_tok = farmer_token(client, email="detail-farmer@farmers.example.com")
    # Get the farmer's ID from the list
    admin_tok = admin_token(client, db_session, email="admin-detail-get@example.com")
    list_resp = client.get(FARMERS_ENDPOINT, headers=auth_headers(admin_tok))
    farmer_id = next(
        f["id"] for f in list_resp.json()["farmers"]
        if f["email"] == "detail-farmer@farmers.example.com"
    )

    resp = client.get(f"{FARMERS_ENDPOINT}/{farmer_id}", headers=auth_headers(admin_tok))
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["id"] == farmer_id
    assert payload["email"] == "detail-farmer@farmers.example.com"


def test_detail_has_required_fields(client, db_session):
    farmer_token(client, email="detail-fields-farmer@farmers.example.com")
    admin_tok = admin_token(client, db_session, email="admin-detail-fields@example.com")
    list_resp = client.get(FARMERS_ENDPOINT, headers=auth_headers(admin_tok))
    farmer_id = next(
        f["id"] for f in list_resp.json()["farmers"]
        if f["email"] == "detail-fields-farmer@farmers.example.com"
    )

    resp = client.get(f"{FARMERS_ENDPOINT}/{farmer_id}", headers=auth_headers(admin_tok))
    assert resp.status_code == 200
    payload = resp.json()
    required = {"id", "full_name", "email", "phone_number", "is_active", "created_at", "updated_at", "farmer_profile"}
    assert required.issubset(set(payload.keys()))


def test_farmer_detail_includes_profile_when_present(client, db_session):
    farmer_tok = farmer_token(client, email="profile-detail-farmer@farmers.example.com")
    # Create the farmer profile
    client.post("/api/profile", json=SAMPLE_PROFILE, headers=auth_headers(farmer_tok))

    admin_tok = admin_token(client, db_session, email="admin-profile-check@example.com")
    list_resp = client.get(FARMERS_ENDPOINT, headers=auth_headers(admin_tok))
    farmer_id = next(
        f["id"] for f in list_resp.json()["farmers"]
        if f["email"] == "profile-detail-farmer@farmers.example.com"
    )

    resp = client.get(f"{FARMERS_ENDPOINT}/{farmer_id}", headers=auth_headers(admin_tok))
    assert resp.status_code == 200
    profile = resp.json()["farmer_profile"]
    assert profile is not None
    assert profile["state"] == SAMPLE_PROFILE["state"]
    assert profile["primary_crop"] == SAMPLE_PROFILE["primary_crop"]


def test_farmer_detail_profile_is_null_without_profile(client, db_session):
    farmer_token(client, email="no-profile-detail@farmers.example.com")
    admin_tok = admin_token(client, db_session, email="admin-no-profile@example.com")
    list_resp = client.get(FARMERS_ENDPOINT, headers=auth_headers(admin_tok))
    farmer_id = next(
        f["id"] for f in list_resp.json()["farmers"]
        if f["email"] == "no-profile-detail@farmers.example.com"
    )

    resp = client.get(f"{FARMERS_ENDPOINT}/{farmer_id}", headers=auth_headers(admin_tok))
    assert resp.status_code == 200
    assert resp.json()["farmer_profile"] is None


def test_has_profile_flag_true_when_profile_exists(client, db_session):
    farmer_tok = farmer_token(client, email="has-profile-flag@farmers.example.com")
    client.post("/api/profile", json=SAMPLE_PROFILE, headers=auth_headers(farmer_tok))

    admin_tok = admin_token(client, db_session, email="admin-has-profile-flag@example.com")
    list_resp = client.get(FARMERS_ENDPOINT, headers=auth_headers(admin_tok))
    item = next(
        f for f in list_resp.json()["farmers"]
        if f["email"] == "has-profile-flag@farmers.example.com"
    )
    assert item["has_profile"] is True


def test_has_profile_flag_false_without_profile(client, db_session):
    farmer_token(client, email="no-profile-flag@farmers.example.com")
    admin_tok = admin_token(client, db_session, email="admin-no-profile-flag@example.com")
    list_resp = client.get(FARMERS_ENDPOINT, headers=auth_headers(admin_tok))
    item = next(
        f for f in list_resp.json()["farmers"]
        if f["email"] == "no-profile-flag@farmers.example.com"
    )
    assert item["has_profile"] is False


# ---------------------------------------------------------------------------
# E. Sensitive field exclusion
# ---------------------------------------------------------------------------

def test_password_hash_not_exposed_in_list(client, db_session):
    farmer_token(client, email="pw-list-check@farmers.example.com")
    admin_tok = admin_token(client, db_session, email="admin-pw-list@example.com")
    resp = client.get(FARMERS_ENDPOINT, headers=auth_headers(admin_tok))
    serialized = str(resp.json()).lower()
    assert "password" not in serialized
    assert "password_hash" not in serialized


def test_password_hash_not_exposed_in_detail(client, db_session):
    farmer_token(client, email="pw-detail-check@farmers.example.com")
    admin_tok = admin_token(client, db_session, email="admin-pw-detail@example.com")
    list_resp = client.get(FARMERS_ENDPOINT, headers=auth_headers(admin_tok))
    farmer_id = next(
        f["id"] for f in list_resp.json()["farmers"]
        if f["email"] == "pw-detail-check@farmers.example.com"
    )
    resp = client.get(f"{FARMERS_ENDPOINT}/{farmer_id}", headers=auth_headers(admin_tok))
    serialized = str(resp.json()).lower()
    assert "password" not in serialized
    assert "password_hash" not in serialized
