"""
Phase 12 — Application Assistance tests.

Covers:
  A. Auth / RBAC
  B. Create application (POST /api/schemes/{id}/application)
  C. Get application (GET  /api/schemes/{id}/application)
  D. Update application (PATCH /api/schemes/{id}/application)
  E. List applications (GET /api/applications)
  F. Application summary (GET /api/applications/summary)
  G. Checklist (GET /api/schemes/{id}/application/checklist)
  H. Ownership isolation
  I. Regression — saved schemes, recommendations, eligibility unaffected
"""
from __future__ import annotations

import pytest

from tests.api.test_profile import SAMPLE_PROFILE, admin_token, auth_headers, farmer_token
from tests.api.test_schemes import seed_test_scheme

SCHEMES = "/api/schemes"
APPS = "/api/applications"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _app_url(scheme_id: int) -> str:
    return f"{SCHEMES}/{scheme_id}/application"


def _checklist_url(scheme_id: int) -> str:
    return f"{SCHEMES}/{scheme_id}/application/checklist"


def _setup_farmer(client, email: str, with_profile: bool = True) -> str:
    token = farmer_token(client, email=email)
    if with_profile:
        client.post("/api/profile", json=SAMPLE_PROFILE, headers=auth_headers(token))
    return token


def _create_app(client, token, scheme_id, *, notes=None):
    body = {}
    if notes is not None:
        body["notes"] = notes
    return client.post(_app_url(scheme_id), json=body, headers=auth_headers(token))


# ---------------------------------------------------------------------------
# A. Auth / RBAC
# ---------------------------------------------------------------------------

def test_unauthenticated_create_returns_401(client, db_session):
    scheme = seed_test_scheme(db_session, name="Auth Create Scheme")
    resp = client.post(_app_url(scheme.id), json={})
    assert resp.status_code == 401


def test_unauthenticated_get_returns_401(client, db_session):
    scheme = seed_test_scheme(db_session, name="Auth Get Scheme")
    resp = client.get(_app_url(scheme.id))
    assert resp.status_code == 401


def test_unauthenticated_patch_returns_401(client, db_session):
    scheme = seed_test_scheme(db_session, name="Auth Patch Scheme")
    resp = client.patch(_app_url(scheme.id), json={"status": "preparing"})
    assert resp.status_code == 401


def test_unauthenticated_checklist_returns_401(client, db_session):
    scheme = seed_test_scheme(db_session, name="Auth Checklist Scheme")
    resp = client.get(_checklist_url(scheme.id))
    assert resp.status_code == 401


def test_unauthenticated_list_returns_401(client):
    resp = client.get(APPS)
    assert resp.status_code == 401


def test_admin_cannot_create_application(client, db_session):
    scheme = seed_test_scheme(db_session, name="Admin Create App Scheme")
    token = admin_token(client, db_session, email="admin-app-create@example.com")
    resp = _create_app(client, token, scheme.id)
    assert resp.status_code == 403


def test_admin_cannot_list_applications(client, db_session):
    token = admin_token(client, db_session, email="admin-app-list@example.com")
    resp = client.get(APPS, headers=auth_headers(token))
    assert resp.status_code == 403


def test_admin_cannot_get_checklist(client, db_session):
    scheme = seed_test_scheme(db_session, name="Admin Checklist Scheme")
    token = admin_token(client, db_session, email="admin-app-checklist@example.com")
    resp = client.get(_checklist_url(scheme.id), headers=auth_headers(token))
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# B. Create application
# ---------------------------------------------------------------------------

def test_farmer_can_create_application(client, db_session):
    scheme = seed_test_scheme(db_session, name="Create App Scheme")
    token = _setup_farmer(client, "create-app@example.com")
    resp = _create_app(client, token, scheme.id)
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["scheme_id"] == scheme.id
    assert payload["status"] == "preparing"
    assert "id" in payload
    assert "created_at" in payload
    assert "updated_at" in payload
    assert payload["scheme"]["id"] == scheme.id


def test_create_application_default_status_is_preparing(client, db_session):
    scheme = seed_test_scheme(db_session, name="Default Status App Scheme")
    token = _setup_farmer(client, "default-status-app@example.com")
    resp = _create_app(client, token, scheme.id)
    assert resp.status_code == 201
    assert resp.json()["status"] == "preparing"


def test_create_application_with_notes(client, db_session):
    scheme = seed_test_scheme(db_session, name="Notes App Scheme")
    token = _setup_farmer(client, "notes-app@example.com")
    resp = _create_app(client, token, scheme.id, notes="Remember to attach land documents.")
    assert resp.status_code == 201
    assert resp.json()["notes"] == "Remember to attach land documents."


def test_create_application_nonexistent_scheme_returns_404(client):
    token = farmer_token(client, email="app-404-scheme@example.com")
    resp = _create_app(client, token, 999999)
    assert resp.status_code == 404


def test_create_application_is_idempotent(client, db_session):
    scheme = seed_test_scheme(db_session, name="Idempotent App Scheme")
    token = _setup_farmer(client, "idempotent-app@example.com")
    r1 = _create_app(client, token, scheme.id)
    r2 = _create_app(client, token, scheme.id)
    assert r1.status_code == 201
    assert r2.status_code in (200, 201)
    assert r1.json()["id"] == r2.json()["id"]


def test_create_application_response_has_scheme_name(client, db_session):
    scheme = seed_test_scheme(db_session, name="Named App Scheme")
    token = _setup_farmer(client, "named-app@example.com")
    resp = _create_app(client, token, scheme.id)
    assert resp.status_code == 201
    assert resp.json()["scheme"]["name"] == "Named App Scheme"


# ---------------------------------------------------------------------------
# C. Get application
# ---------------------------------------------------------------------------

def test_farmer_can_get_own_application(client, db_session):
    scheme = seed_test_scheme(db_session, name="Get App Scheme")
    token = _setup_farmer(client, "get-app@example.com")
    _create_app(client, token, scheme.id)
    resp = client.get(_app_url(scheme.id), headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["scheme_id"] == scheme.id


def test_get_nonexistent_application_returns_404(client, db_session):
    scheme = seed_test_scheme(db_session, name="Get No App Scheme")
    token = _setup_farmer(client, "get-no-app@example.com")
    resp = client.get(_app_url(scheme.id), headers=auth_headers(token))
    assert resp.status_code == 404


def test_get_application_nonexistent_scheme_returns_404(client):
    token = farmer_token(client, email="get-app-no-scheme@example.com")
    resp = client.get(_app_url(999999), headers=auth_headers(token))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# D. Update application
# ---------------------------------------------------------------------------

def test_farmer_can_update_application_status(client, db_session):
    scheme = seed_test_scheme(db_session, name="Update Status Scheme")
    token = _setup_farmer(client, "update-status@example.com")
    _create_app(client, token, scheme.id)
    resp = client.patch(
        _app_url(scheme.id),
        json={"status": "ready_to_apply"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready_to_apply"


def test_farmer_can_update_notes(client, db_session):
    scheme = seed_test_scheme(db_session, name="Update Notes Scheme")
    token = _setup_farmer(client, "update-notes@example.com")
    _create_app(client, token, scheme.id)
    resp = client.patch(
        _app_url(scheme.id),
        json={"notes": "Updated notes here."},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["notes"] == "Updated notes here."


def test_all_valid_statuses_accepted(client, db_session):
    for status_val in ("not_started", "preparing", "ready_to_apply", "submitted"):
        scheme = seed_test_scheme(db_session, name=f"Status Scheme {status_val}")
        token = _setup_farmer(client, f"status-{status_val}@example.com")
        _create_app(client, token, scheme.id)
        resp = client.patch(
            _app_url(scheme.id),
            json={"status": status_val},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200, f"Failed for status={status_val}"
        assert resp.json()["status"] == status_val


def test_invalid_status_returns_422(client, db_session):
    scheme = seed_test_scheme(db_session, name="Invalid Status Scheme")
    token = _setup_farmer(client, "invalid-status@example.com")
    _create_app(client, token, scheme.id)
    resp = client.patch(
        _app_url(scheme.id),
        json={"status": "not_a_real_status"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 422


def test_update_nonexistent_application_returns_404(client, db_session):
    scheme = seed_test_scheme(db_session, name="Update No App Scheme")
    token = _setup_farmer(client, "update-no-app@example.com")
    resp = client.patch(
        _app_url(scheme.id),
        json={"status": "preparing"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# E. List applications
# ---------------------------------------------------------------------------

def test_farmer_can_list_own_applications(client, db_session):
    s1 = seed_test_scheme(db_session, name="List App Scheme 1")
    s2 = seed_test_scheme(db_session, name="List App Scheme 2")
    token = _setup_farmer(client, "list-apps@example.com")
    _create_app(client, token, s1.id)
    _create_app(client, token, s2.id)
    resp = client.get(APPS, headers=auth_headers(token))
    assert resp.status_code == 200
    payload = resp.json()
    assert "applications" in payload
    assert "total" in payload
    assert payload["total"] == 2
    scheme_ids = {a["scheme_id"] for a in payload["applications"]}
    assert s1.id in scheme_ids
    assert s2.id in scheme_ids


def test_list_applications_empty_for_new_farmer(client):
    token = farmer_token(client, email="empty-apps@example.com")
    resp = client.get(APPS, headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
    assert resp.json()["applications"] == []


def test_list_applications_response_has_required_fields(client, db_session):
    scheme = seed_test_scheme(db_session, name="Fields App Scheme")
    token = _setup_farmer(client, "fields-app@example.com")
    _create_app(client, token, scheme.id)
    resp = client.get(APPS, headers=auth_headers(token))
    assert resp.status_code == 200
    app = resp.json()["applications"][0]
    required = {"id", "user_id", "scheme_id", "status", "notes", "created_at", "updated_at", "scheme"}
    assert required.issubset(set(app.keys()))
    assert {"id", "name", "short_description"}.issubset(set(app["scheme"].keys()))


# ---------------------------------------------------------------------------
# F. Application summary
# ---------------------------------------------------------------------------

def test_summary_returns_zero_counts_for_new_farmer(client):
    token = farmer_token(client, email="summary-zero@example.com")
    resp = client.get(f"{APPS}/summary", headers=auth_headers(token))
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total"] == 0
    assert payload["preparing"] == 0
    assert payload["ready_to_apply"] == 0
    assert payload["submitted"] == 0


def test_summary_counts_by_status(client, db_session):
    schemes = [seed_test_scheme(db_session, name=f"Summary Scheme {i}") for i in range(3)]
    token = _setup_farmer(client, "summary-counts@example.com")
    # Create 3 apps; update 2 to different statuses
    for s in schemes:
        _create_app(client, token, s.id)
    client.patch(_app_url(schemes[1].id), json={"status": "ready_to_apply"}, headers=auth_headers(token))
    client.patch(_app_url(schemes[2].id), json={"status": "submitted"}, headers=auth_headers(token))
    resp = client.get(f"{APPS}/summary", headers=auth_headers(token))
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total"] == 3
    assert payload["preparing"] == 1
    assert payload["ready_to_apply"] == 1
    assert payload["submitted"] == 1


# ---------------------------------------------------------------------------
# G. Checklist
# ---------------------------------------------------------------------------

def test_checklist_returns_structured_response(client, db_session):
    scheme = seed_test_scheme(db_session, name="Checklist Struct Scheme")
    token = _setup_farmer(client, "checklist-struct@example.com")
    resp = client.get(_checklist_url(scheme.id), headers=auth_headers(token))
    assert resp.status_code == 200
    payload = resp.json()
    assert "items" in payload
    assert "total" in payload
    assert "completed" in payload
    assert "missing" in payload
    assert "ready" in payload
    assert isinstance(payload["items"], list)
    assert payload["total"] == len(payload["items"])
    assert payload["completed"] + payload["missing"] <= payload["total"]


def test_checklist_items_have_required_fields(client, db_session):
    scheme = seed_test_scheme(db_session, name="Checklist Fields Scheme")
    token = _setup_farmer(client, "checklist-fields@example.com")
    resp = client.get(_checklist_url(scheme.id), headers=auth_headers(token))
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert "key" in item
        assert "label" in item
        assert "status" in item
        assert "message" in item
        assert item["status"] in ("complete", "missing", "attention")


def test_checklist_shows_missing_profile_fields(client, db_session):
    scheme = seed_test_scheme(db_session, name="Checklist Missing Profile Scheme")
    # Create farmer with partial profile — several fields missing
    token = farmer_token(client, email="checklist-missing@example.com")
    client.post("/api/profile", json={"state": "Telangana"}, headers=auth_headers(token))
    resp = client.get(_checklist_url(scheme.id), headers=auth_headers(token))
    assert resp.status_code == 200
    payload = resp.json()
    missing_items = [i for i in payload["items"] if i["status"] == "missing"]
    assert len(missing_items) > 0


def test_checklist_full_profile_has_complete_profile_items(client, db_session):
    scheme = seed_test_scheme(db_session, name="Checklist Full Profile Scheme")
    token = _setup_farmer(client, "checklist-full@example.com")
    resp = client.get(_checklist_url(scheme.id), headers=auth_headers(token))
    assert resp.status_code == 200
    # SAMPLE_PROFILE fills all COMPLETION_FIELDS — all profile items should be complete
    profile_items = [i for i in resp.json()["items"] if i["key"].startswith("profile_")]
    complete_profile_items = [i for i in profile_items if i["status"] == "complete"]
    assert len(complete_profile_items) == len(profile_items)


def test_checklist_eligible_scheme_with_complete_profile_is_ready(client, db_session):
    # Scheme that SAMPLE_PROFILE satisfies (state=Telangana, income<=200000)
    scheme = seed_test_scheme(db_session, name="Checklist Ready Scheme")
    token = _setup_farmer(client, "checklist-ready@example.com")
    resp = client.get(_checklist_url(scheme.id), headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["ready"] is True


def test_checklist_ineligible_scheme_is_not_ready(client, db_session):
    from app.models.scheme_eligibility import SchemeEligibilityCriterion
    scheme = seed_test_scheme(
        db_session,
        name="Checklist Not Ready Scheme",
        criteria=[{
            "criterion_type": "profile",
            "field_name": "state",
            "operator": "equals",
            "expected_value": "Karnataka",
            "description": "Must be from Karnataka.",
        }],
    )
    # SAMPLE_PROFILE has state=Telangana — fails Karnataka criterion
    token = _setup_farmer(client, "checklist-not-ready@example.com")
    resp = client.get(_checklist_url(scheme.id), headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["ready"] is False


def test_checklist_no_profile_shows_missing(client, db_session):
    scheme = seed_test_scheme(db_session, name="Checklist No Profile Scheme")
    token = farmer_token(client, email="checklist-no-profile@example.com")
    resp = client.get(_checklist_url(scheme.id), headers=auth_headers(token))
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["missing"] > 0
    assert payload["ready"] is False


def test_checklist_nonexistent_scheme_returns_404(client):
    token = farmer_token(client, email="checklist-404@example.com")
    resp = client.get(_checklist_url(999999), headers=auth_headers(token))
    assert resp.status_code == 404


def test_checklist_does_not_require_existing_application(client, db_session):
    """Checklist works even if no application record has been created yet."""
    scheme = seed_test_scheme(db_session, name="Checklist No App Scheme")
    token = _setup_farmer(client, "checklist-no-app@example.com")
    # No call to _create_app
    resp = client.get(_checklist_url(scheme.id), headers=auth_headers(token))
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# H. Ownership isolation — a farmer cannot see/modify another's application
# ---------------------------------------------------------------------------

def test_farmer_cannot_get_another_farmers_application(client, db_session):
    scheme = seed_test_scheme(db_session, name="Ownership Get Scheme")
    token_a = _setup_farmer(client, "owner-a-get@example.com")
    token_b = farmer_token(client, email="owner-b-get@example.com")
    _create_app(client, token_a, scheme.id)
    # Farmer B has no application for this scheme
    resp = client.get(_app_url(scheme.id), headers=auth_headers(token_b))
    assert resp.status_code == 404


def test_farmer_cannot_patch_another_farmers_application(client, db_session):
    scheme = seed_test_scheme(db_session, name="Ownership Patch Scheme")
    token_a = _setup_farmer(client, "owner-a-patch@example.com")
    token_b = farmer_token(client, email="owner-b-patch@example.com")
    _create_app(client, token_a, scheme.id)
    resp = client.patch(
        _app_url(scheme.id),
        json={"status": "submitted"},
        headers=auth_headers(token_b),
    )
    assert resp.status_code == 404


def test_farmers_applications_are_isolated(client, db_session):
    """Farmer B's list should not contain Farmer A's applications."""
    s1 = seed_test_scheme(db_session, name="Isolated Scheme A")
    s2 = seed_test_scheme(db_session, name="Isolated Scheme B")
    token_a = _setup_farmer(client, "isolated-a@example.com")
    token_b = _setup_farmer(client, "isolated-b@example.com")
    _create_app(client, token_a, s1.id)
    _create_app(client, token_b, s2.id)
    resp_a = client.get(APPS, headers=auth_headers(token_a))
    resp_b = client.get(APPS, headers=auth_headers(token_b))
    ids_a = {a["scheme_id"] for a in resp_a.json()["applications"]}
    ids_b = {a["scheme_id"] for a in resp_b.json()["applications"]}
    assert s1.id in ids_a
    assert s2.id not in ids_a
    assert s2.id in ids_b
    assert s1.id not in ids_b


# ---------------------------------------------------------------------------
# I. Regression — existing functionality unaffected
# ---------------------------------------------------------------------------

def test_existing_saved_schemes_unaffected(client, db_session):
    scheme = seed_test_scheme(db_session, name="Regression Save Scheme P12")
    token = farmer_token(client, email="p12-reg-save@example.com")
    r = client.post(f"/api/schemes/{scheme.id}/save", headers=auth_headers(token))
    assert r.status_code == 201
    r2 = client.get("/api/saved-schemes", headers=auth_headers(token))
    assert r2.status_code == 200
    assert r2.json()["total"] >= 1


def test_existing_recommendations_unaffected(client, db_session):
    seed_test_scheme(db_session, name="Regression Rec Scheme P12")
    token = _setup_farmer(client, "p12-reg-rec@example.com")
    resp = client.get("/api/recommendations", headers=auth_headers(token))
    assert resp.status_code == 200
    payload = resp.json()
    assert "recommendations" in payload
    for rec in payload["recommendations"]:
        assert "match_status" in rec
        assert "factors" in rec


def test_existing_eligibility_unaffected(client, db_session):
    scheme = seed_test_scheme(
        db_session,
        name="Regression Elig Scheme P12",
        criteria=[{
            "criterion_type": "profile",
            "field_name": "state",
            "operator": "equals",
            "expected_value": "Telangana",
            "description": "State match.",
        }],
    )
    token = _setup_farmer(client, "p12-reg-elig@example.com")
    resp = client.get(f"/api/schemes/{scheme.id}/eligibility", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["eligible"] is True


def test_application_and_save_independent(client, db_session):
    """Creating an application must not affect saved-scheme state."""
    scheme = seed_test_scheme(db_session, name="App Save Independent Scheme")
    token = _setup_farmer(client, "app-save-independent@example.com")
    # Save the scheme, then create application
    client.post(f"/api/schemes/{scheme.id}/save", headers=auth_headers(token))
    _create_app(client, token, scheme.id)
    # Both operations should coexist independently
    saved = client.get("/api/saved-schemes", headers=auth_headers(token))
    apps = client.get(APPS, headers=auth_headers(token))
    assert saved.json()["total"] >= 1
    assert apps.json()["total"] >= 1
