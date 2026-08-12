"""
Phase 9 — Admin Scheme Management tests.

Groups:
  A. Authentication / RBAC
  B. List schemes (admin view includes inactive)
  C. Create scheme
  D. Get scheme detail
  E. Update scheme
  F. Delete scheme
  G. Eligibility criteria management
  H. Farmer-facing routes unaffected (regression)
"""
from __future__ import annotations

from tests.api.test_profile import admin_token, auth_headers, farmer_token
from tests.api.test_schemes import seed_test_scheme

ADMIN_SCHEMES_ENDPOINT = "/api/admin/schemes"

MINIMAL_SCHEME = {
    "name": "Test Admin Scheme",
    "short_description": "Short desc for testing.",
    "detailed_description": "Detailed desc for testing.",
    "department": "Test Department",
    "state": "Telangana",
    "scheme_type": "Financial Assistance",
    "benefits": "Test benefits.",
    "application_process": "Apply at local office.",
    "official_website": None,
    "is_active": True,
    "eligibility_criteria": [],
}

SCHEME_WITH_CRITERIA = {
    **MINIMAL_SCHEME,
    "name": "Criteria Scheme",
    "eligibility_criteria": [
        {
            "criterion_type": "profile",
            "field_name": "state",
            "operator": "equals",
            "expected_value": "Telangana",
            "description": "Must be from Telangana.",
        }
    ],
}


# ---------------------------------------------------------------------------
# A. Authentication / RBAC
# ---------------------------------------------------------------------------

def test_unauthenticated_list_returns_401(client):
    assert client.get(ADMIN_SCHEMES_ENDPOINT).status_code == 401


def test_farmer_list_returns_403(client):
    token = farmer_token(client, email="farmer-scheme-list@example.com")
    assert client.get(ADMIN_SCHEMES_ENDPOINT, headers=auth_headers(token)).status_code == 403


def test_unauthenticated_create_returns_401(client):
    assert client.post(ADMIN_SCHEMES_ENDPOINT, json=MINIMAL_SCHEME).status_code == 401


def test_farmer_create_returns_403(client):
    token = farmer_token(client, email="farmer-scheme-create@example.com")
    assert (
        client.post(ADMIN_SCHEMES_ENDPOINT, json=MINIMAL_SCHEME, headers=auth_headers(token)).status_code
        == 403
    )


def test_farmer_delete_returns_403(client):
    token = farmer_token(client, email="farmer-scheme-delete@example.com")
    assert (
        client.delete(f"{ADMIN_SCHEMES_ENDPOINT}/1", headers=auth_headers(token)).status_code
        == 403
    )


def test_farmer_update_returns_403(client):
    token = farmer_token(client, email="farmer-scheme-update@example.com")
    assert (
        client.put(
            f"{ADMIN_SCHEMES_ENDPOINT}/1",
            json=MINIMAL_SCHEME,
            headers=auth_headers(token),
        ).status_code
        == 403
    )


# ---------------------------------------------------------------------------
# B. List
# ---------------------------------------------------------------------------

def test_admin_can_list_schemes(client, db_session):
    token = admin_token(client, db_session, email="admin-list-schemes@example.com")
    resp = client.get(ADMIN_SCHEMES_ENDPOINT, headers=auth_headers(token))
    assert resp.status_code == 200
    payload = resp.json()
    assert "schemes" in payload
    assert "total" in payload


def test_admin_list_includes_seeded_scheme(client, db_session):
    seed_test_scheme(db_session, name="Admin List Visible Scheme")
    token = admin_token(client, db_session, email="admin-list-visible@example.com")
    resp = client.get(ADMIN_SCHEMES_ENDPOINT, headers=auth_headers(token))
    assert resp.status_code == 200
    names = [s["name"] for s in resp.json()["schemes"]]
    assert "Admin List Visible Scheme" in names


def test_admin_list_includes_inactive_schemes(client, db_session):
    """Admin list must show inactive schemes that farmer list hides."""
    token = admin_token(client, db_session, email="admin-inactive-list@example.com")
    # Create an inactive scheme via admin
    inactive = {**MINIMAL_SCHEME, "name": "Inactive Admin Scheme", "is_active": False}
    create_resp = client.post(ADMIN_SCHEMES_ENDPOINT, json=inactive, headers=auth_headers(token))
    assert create_resp.status_code == 201

    list_resp = client.get(ADMIN_SCHEMES_ENDPOINT, headers=auth_headers(token))
    names = [s["name"] for s in list_resp.json()["schemes"]]
    assert "Inactive Admin Scheme" in names

    # Farmer list must NOT see it
    farmer_tok = farmer_token(client, email="farmer-no-inactive@example.com")
    farmer_resp = client.get("/api/schemes", headers=auth_headers(farmer_tok))
    farmer_names = [s["name"] for s in farmer_resp.json()["schemes"]]
    assert "Inactive Admin Scheme" not in farmer_names


# ---------------------------------------------------------------------------
# C. Create
# ---------------------------------------------------------------------------

def test_admin_can_create_scheme(client, db_session):
    token = admin_token(client, db_session, email="admin-create-scheme@example.com")
    resp = client.post(ADMIN_SCHEMES_ENDPOINT, json=MINIMAL_SCHEME, headers=auth_headers(token))
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["name"] == MINIMAL_SCHEME["name"]
    assert payload["is_active"] is True
    assert "id" in payload


def test_created_scheme_has_all_response_fields(client, db_session):
    token = admin_token(client, db_session, email="admin-create-fields@example.com")
    resp = client.post(
        ADMIN_SCHEMES_ENDPOINT,
        json={**MINIMAL_SCHEME, "name": "Fields Check Scheme"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 201
    payload = resp.json()
    required = {
        "id", "name", "short_description", "detailed_description", "department",
        "state", "scheme_type", "benefits", "application_process", "official_website",
        "is_active", "created_at", "updated_at", "eligibility_criteria",
    }
    assert required.issubset(set(payload.keys()))


def test_create_scheme_with_eligibility_criteria(client, db_session):
    token = admin_token(client, db_session, email="admin-create-criteria@example.com")
    resp = client.post(
        ADMIN_SCHEMES_ENDPOINT,
        json=SCHEME_WITH_CRITERIA,
        headers=auth_headers(token),
    )
    assert resp.status_code == 201
    criteria = resp.json()["eligibility_criteria"]
    assert len(criteria) == 1
    assert criteria[0]["field_name"] == "state"
    assert criteria[0]["operator"] == "equals"
    assert criteria[0]["expected_value"] == "Telangana"


def test_create_scheme_missing_required_field_returns_422(client, db_session):
    token = admin_token(client, db_session, email="admin-create-invalid@example.com")
    invalid = {k: v for k, v in MINIMAL_SCHEME.items() if k != "name"}
    resp = client.post(ADMIN_SCHEMES_ENDPOINT, json=invalid, headers=auth_headers(token))
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# D. Get detail
# ---------------------------------------------------------------------------

def test_admin_can_get_scheme_detail(client, db_session):
    token = admin_token(client, db_session, email="admin-get-detail@example.com")
    created = client.post(
        ADMIN_SCHEMES_ENDPOINT,
        json={**MINIMAL_SCHEME, "name": "Detail Get Scheme"},
        headers=auth_headers(token),
    ).json()

    resp = client.get(f"{ADMIN_SCHEMES_ENDPOINT}/{created['id']}", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_unknown_scheme_detail_returns_404(client, db_session):
    token = admin_token(client, db_session, email="admin-detail-404@example.com")
    resp = client.get(f"{ADMIN_SCHEMES_ENDPOINT}/999999", headers=auth_headers(token))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# E. Update
# ---------------------------------------------------------------------------

def test_admin_can_update_scheme(client, db_session):
    token = admin_token(client, db_session, email="admin-update-scheme@example.com")
    created = client.post(
        ADMIN_SCHEMES_ENDPOINT,
        json={**MINIMAL_SCHEME, "name": "Before Update"},
        headers=auth_headers(token),
    ).json()

    updated_body = {**MINIMAL_SCHEME, "name": "After Update"}
    resp = client.put(
        f"{ADMIN_SCHEMES_ENDPOINT}/{created['id']}",
        json=updated_body,
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "After Update"


def test_update_replaces_eligibility_criteria(client, db_session):
    token = admin_token(client, db_session, email="admin-update-criteria@example.com")
    created = client.post(
        ADMIN_SCHEMES_ENDPOINT,
        json=SCHEME_WITH_CRITERIA,
        headers=auth_headers(token),
    ).json()
    assert len(created["eligibility_criteria"]) == 1

    # Update with 2 criteria
    updated_body = {
        **MINIMAL_SCHEME,
        "name": SCHEME_WITH_CRITERIA["name"],
        "eligibility_criteria": [
            {
                "criterion_type": "profile",
                "field_name": "state",
                "operator": "equals",
                "expected_value": "Telangana",
                "description": "Must be Telangana.",
            },
            {
                "criterion_type": "profile",
                "field_name": "annual_income",
                "operator": "less_than_or_equal",
                "expected_value": "100000",
                "description": None,
            },
        ],
    }
    resp = client.put(
        f"{ADMIN_SCHEMES_ENDPOINT}/{created['id']}",
        json=updated_body,
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert len(resp.json()["eligibility_criteria"]) == 2


def test_update_unknown_scheme_returns_404(client, db_session):
    token = admin_token(client, db_session, email="admin-update-404@example.com")
    resp = client.put(
        f"{ADMIN_SCHEMES_ENDPOINT}/999999",
        json=MINIMAL_SCHEME,
        headers=auth_headers(token),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# F. Delete
# ---------------------------------------------------------------------------

def test_admin_can_delete_scheme(client, db_session):
    token = admin_token(client, db_session, email="admin-delete-scheme@example.com")
    created = client.post(
        ADMIN_SCHEMES_ENDPOINT,
        json={**MINIMAL_SCHEME, "name": "Delete Target Scheme"},
        headers=auth_headers(token),
    ).json()

    resp = client.delete(
        f"{ADMIN_SCHEMES_ENDPOINT}/{created['id']}", headers=auth_headers(token)
    )
    assert resp.status_code == 204


def test_deleted_scheme_returns_404(client, db_session):
    token = admin_token(client, db_session, email="admin-delete-gone@example.com")
    created = client.post(
        ADMIN_SCHEMES_ENDPOINT,
        json={**MINIMAL_SCHEME, "name": "Gone After Delete"},
        headers=auth_headers(token),
    ).json()
    client.delete(f"{ADMIN_SCHEMES_ENDPOINT}/{created['id']}", headers=auth_headers(token))

    resp = client.get(f"{ADMIN_SCHEMES_ENDPOINT}/{created['id']}", headers=auth_headers(token))
    assert resp.status_code == 404


def test_deleted_scheme_absent_from_list(client, db_session):
    token = admin_token(client, db_session, email="admin-delete-list@example.com")
    created = client.post(
        ADMIN_SCHEMES_ENDPOINT,
        json={**MINIMAL_SCHEME, "name": "List Gone After Delete"},
        headers=auth_headers(token),
    ).json()
    client.delete(f"{ADMIN_SCHEMES_ENDPOINT}/{created['id']}", headers=auth_headers(token))

    list_resp = client.get(ADMIN_SCHEMES_ENDPOINT, headers=auth_headers(token))
    ids = [s["id"] for s in list_resp.json()["schemes"]]
    assert created["id"] not in ids


def test_delete_unknown_scheme_returns_404(client, db_session):
    token = admin_token(client, db_session, email="admin-delete-unknown@example.com")
    resp = client.delete(f"{ADMIN_SCHEMES_ENDPOINT}/999999", headers=auth_headers(token))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# G. Eligibility criteria
# ---------------------------------------------------------------------------

def test_eligibility_criterion_fields_are_present(client, db_session):
    token = admin_token(client, db_session, email="admin-criteria-fields@example.com")
    resp = client.post(
        ADMIN_SCHEMES_ENDPOINT,
        json=SCHEME_WITH_CRITERIA,
        headers=auth_headers(token),
    )
    assert resp.status_code == 201
    criterion = resp.json()["eligibility_criteria"][0]
    assert "id" in criterion
    assert criterion["criterion_type"] == "profile"
    assert criterion["field_name"] == "state"
    assert criterion["operator"] == "equals"
    assert criterion["expected_value"] == "Telangana"
    assert criterion["description"] == "Must be from Telangana."


def test_scheme_created_with_no_criteria_has_empty_list(client, db_session):
    token = admin_token(client, db_session, email="admin-no-criteria@example.com")
    resp = client.post(
        ADMIN_SCHEMES_ENDPOINT,
        json={**MINIMAL_SCHEME, "name": "No Criteria Scheme"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 201
    assert resp.json()["eligibility_criteria"] == []


# ---------------------------------------------------------------------------
# H. Farmer-facing routes unaffected (regression)
# ---------------------------------------------------------------------------

def test_farmer_can_still_list_schemes_after_admin_create(client, db_session):
    """Farmer-facing route must still work after admin creates a scheme."""
    admin_tok = admin_token(client, db_session, email="admin-regression-create@example.com")
    client.post(
        ADMIN_SCHEMES_ENDPOINT,
        json={**MINIMAL_SCHEME, "name": "Regression Visible Scheme", "is_active": True},
        headers=auth_headers(admin_tok),
    )

    farmer_tok = farmer_token(client, email="farmer-regression@example.com")
    resp = client.get("/api/schemes", headers=auth_headers(farmer_tok))
    assert resp.status_code == 200
    names = [s["name"] for s in resp.json()["schemes"]]
    assert "Regression Visible Scheme" in names


def test_farmer_scheme_delete_does_not_affect_farmer_browse(client, db_session):
    """Deleting one scheme must not remove others from farmer view."""
    admin_tok = admin_token(client, db_session, email="admin-regression-delete@example.com")
    keep = client.post(
        ADMIN_SCHEMES_ENDPOINT,
        json={**MINIMAL_SCHEME, "name": "Keep This Scheme"},
        headers=auth_headers(admin_tok),
    ).json()
    remove = client.post(
        ADMIN_SCHEMES_ENDPOINT,
        json={**MINIMAL_SCHEME, "name": "Remove This Scheme"},
        headers=auth_headers(admin_tok),
    ).json()

    client.delete(f"{ADMIN_SCHEMES_ENDPOINT}/{remove['id']}", headers=auth_headers(admin_tok))

    farmer_tok = farmer_token(client, email="farmer-keep-check@example.com")
    resp = client.get("/api/schemes", headers=auth_headers(farmer_tok))
    names = [s["name"] for s in resp.json()["schemes"]]
    assert "Keep This Scheme" in names
    assert "Remove This Scheme" not in names
