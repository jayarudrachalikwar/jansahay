"""
Phase 11 — Recommendation improvements tests.

Tests:
  - factors field is returned
  - match_status values (eligible / partial / no_match)
  - eligible_only filter
  - sort_by (score / name / eligibility)
  - scheme_type filter
  - state filter
  - profile completion detail endpoint
  - existing /api/profile/completion unchanged
  - regression: existing recommendation + saved-scheme tests unaffected
"""
from __future__ import annotations

import pytest
from unittest.mock import patch

from tests.api.test_profile import SAMPLE_PROFILE, admin_token, auth_headers, farmer_token
from tests.api.test_schemes import seed_test_scheme

RECS = "/api/recommendations"
PROFILE_DETAIL = "/api/profile/completion/detail"
PROFILE_COMPLETION = "/api/profile/completion"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _setup_farmer_with_profile(client, email: str) -> str:
    token = farmer_token(client, email=email)
    client.post("/api/profile", json=SAMPLE_PROFILE, headers=auth_headers(token))
    return token


def _seed_with_state_criteria(db_session, *, name: str, state: str = "Telangana") -> object:
    """Seed a scheme with one state-equals criterion."""
    from tests.api.test_schemes import seed_test_scheme
    from app.models.scheme_eligibility import SchemeEligibilityCriterion

    scheme = seed_test_scheme(db_session, name=name, state=state)
    crit = SchemeEligibilityCriterion(
        scheme_id=scheme.id,
        criterion_type="profile",
        field_name="state",
        operator="equals",
        expected_value=state,
        description=None,
    )
    db_session.add(crit)
    db_session.commit()
    return scheme


# ---------------------------------------------------------------------------
# A. factors field
# ---------------------------------------------------------------------------

def test_recommendation_response_contains_factors_field(client, db_session):
    seed_test_scheme(db_session, name="Factors Scheme")
    token = _setup_farmer_with_profile(client, "p11-factors@example.com")
    resp = client.get(RECS, headers=auth_headers(token))
    assert resp.status_code == 200
    recs = resp.json()["recommendations"]
    assert len(recs) >= 1
    for rec in recs:
        assert "factors" in rec
        assert isinstance(rec["factors"], list)


def test_recommendation_factors_is_list_of_strings(client, db_session):
    seed_test_scheme(db_session, name="Factor Types Scheme")
    token = _setup_farmer_with_profile(client, "p11-factor-types@example.com")
    resp = client.get(RECS, headers=auth_headers(token))
    assert resp.status_code == 200
    for rec in resp.json()["recommendations"]:
        for factor in rec["factors"]:
            assert isinstance(factor, str)
            assert len(factor) > 0


# ---------------------------------------------------------------------------
# B. match_status
# ---------------------------------------------------------------------------

def test_eligible_scheme_returns_match_status_eligible(client, db_session):
    """Scheme with a state criterion that the farmer satisfies → eligible."""
    _seed_with_state_criteria(db_session, name="Eligible Status Scheme", state="Telangana")
    token = _setup_farmer_with_profile(client, "p11-eligible@example.com")
    resp = client.get(RECS, headers=auth_headers(token))
    assert resp.status_code == 200
    # SAMPLE_PROFILE has state=Telangana, so this scheme should be eligible
    eligible_recs = [r for r in resp.json()["recommendations"] if r["scheme"]["name"] == "Eligible Status Scheme"]
    assert len(eligible_recs) == 1
    assert eligible_recs[0]["match_status"] == "eligible"
    assert eligible_recs[0]["eligible"] is True


def test_scheme_no_criteria_returns_eligible_status(client, db_session):
    """Scheme with no eligibility criteria is always eligible."""
    seed_test_scheme(db_session, name="No Criteria Status Scheme", criteria=[])
    token = _setup_farmer_with_profile(client, "p11-no-criteria@example.com")
    resp = client.get(RECS, headers=auth_headers(token))
    assert resp.status_code == 200
    no_crit_recs = [r for r in resp.json()["recommendations"] if r["scheme"]["name"] == "No Criteria Status Scheme"]
    assert len(no_crit_recs) == 1
    assert no_crit_recs[0]["match_status"] == "eligible"


def test_non_eligible_scheme_returns_partial_or_no_match(client, db_session):
    """Scheme with a criterion the farmer does NOT satisfy."""
    from app.models.scheme_eligibility import SchemeEligibilityCriterion
    scheme = seed_test_scheme(db_session, name="Fail Status Scheme", state="Andhra Pradesh")
    crit = SchemeEligibilityCriterion(
        scheme_id=scheme.id,
        criterion_type="profile",
        field_name="state",
        operator="equals",
        expected_value="Andhra Pradesh",
        description=None,
    )
    db_session.add(crit)
    db_session.commit()
    # SAMPLE_PROFILE state = Telangana → does NOT match Andhra Pradesh
    token = _setup_farmer_with_profile(client, "p11-fail-status@example.com")
    resp = client.get(RECS, headers=auth_headers(token))
    assert resp.status_code == 200
    fail_recs = [r for r in resp.json()["recommendations"] if r["scheme"]["name"] == "Fail Status Scheme"]
    assert len(fail_recs) == 1
    assert fail_recs[0]["match_status"] in ("partial", "no_match")
    assert fail_recs[0]["eligible"] is False


def test_match_status_field_present_on_all_recommendations(client, db_session):
    seed_test_scheme(db_session, name="Match Status Present Scheme")
    token = _setup_farmer_with_profile(client, "p11-status-all@example.com")
    resp = client.get(RECS, headers=auth_headers(token))
    assert resp.status_code == 200
    for rec in resp.json()["recommendations"]:
        assert "match_status" in rec
        assert rec["match_status"] in ("eligible", "partial", "no_match")


# ---------------------------------------------------------------------------
# C. eligible_only filter
# ---------------------------------------------------------------------------

def test_eligible_only_filter_returns_only_eligible(client, db_session):
    seed_test_scheme(db_session, name="EligOnly Scheme 1")
    seed_test_scheme(db_session, name="EligOnly Scheme 2")
    token = _setup_farmer_with_profile(client, "p11-elig-only@example.com")
    resp = client.get(RECS + "?eligible_only=true", headers=auth_headers(token))
    assert resp.status_code == 200
    for rec in resp.json()["recommendations"]:
        assert rec["eligible"] is True


def test_eligible_only_false_returns_all(client, db_session):
    seed_test_scheme(db_session, name="EligFalse Scheme")
    token = _setup_farmer_with_profile(client, "p11-elig-false@example.com")
    resp_all = client.get(RECS, headers=auth_headers(token))
    resp_false = client.get(RECS + "?eligible_only=false", headers=auth_headers(token))
    assert resp_all.status_code == 200
    assert resp_false.status_code == 200
    assert resp_all.json()["total"] == resp_false.json()["total"]


# ---------------------------------------------------------------------------
# D. sort_by
# ---------------------------------------------------------------------------

def test_sort_by_score_is_default(client, db_session):
    for i in range(3):
        seed_test_scheme(db_session, name=f"ScoreSort {i}")
    token = _setup_farmer_with_profile(client, "p11-sort-score@example.com")
    resp = client.get(RECS + "?sort_by=score", headers=auth_headers(token))
    assert resp.status_code == 200
    recs = resp.json()["recommendations"]
    if len(recs) >= 2:
        scores = [r["relevance_score"] for r in recs]
        # Eligible first (True > False), then by score descending
        for i in range(len(recs) - 1):
            if recs[i]["eligible"] == recs[i + 1]["eligible"]:
                assert recs[i]["relevance_score"] >= recs[i + 1]["relevance_score"]


def test_sort_by_name_returns_alphabetical(client, db_session):
    for name in ["Zebra Scheme", "Apple Scheme", "Mango Scheme"]:
        seed_test_scheme(db_session, name=name)
    token = _setup_farmer_with_profile(client, "p11-sort-name@example.com")
    resp = client.get(RECS + "?sort_by=name&limit=50", headers=auth_headers(token))
    assert resp.status_code == 200
    names = [r["scheme"]["name"] for r in resp.json()["recommendations"]]
    assert names == sorted(names, key=str.lower)


def test_sort_by_eligibility_eligible_first(client, db_session):
    seed_test_scheme(db_session, name="EligSort Scheme A")
    seed_test_scheme(db_session, name="EligSort Scheme B")
    token = _setup_farmer_with_profile(client, "p11-sort-elig@example.com")
    resp = client.get(RECS + "?sort_by=eligibility&limit=50", headers=auth_headers(token))
    assert resp.status_code == 200
    recs = resp.json()["recommendations"]
    if len(recs) >= 2:
        # Once eligible=False appears, no eligible=True should follow it
        found_ineligible = False
        for rec in recs:
            if not rec["eligible"]:
                found_ineligible = True
            if found_ineligible:
                assert not rec["eligible"], "Eligible rec found after ineligible"


def test_invalid_sort_by_returns_422(client, db_session):
    token = farmer_token(client, email="p11-sort-invalid@example.com")
    resp = client.get(RECS + "?sort_by=invalid_value", headers=auth_headers(token))
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# E. scheme_type filter
# ---------------------------------------------------------------------------

def test_scheme_type_filter(client, db_session):
    seed_test_scheme(db_session, name="TypeFilter A", scheme_type="Financial Assistance")
    seed_test_scheme(db_session, name="TypeFilter B", scheme_type="Insurance")
    token = _setup_farmer_with_profile(client, "p11-type-filter@example.com")
    resp = client.get(RECS + "?scheme_type=Financial+Assistance&limit=50", headers=auth_headers(token))
    assert resp.status_code == 200
    for rec in resp.json()["recommendations"]:
        assert rec["scheme"]["scheme_type"].lower() == "financial assistance"


def test_scheme_type_filter_case_insensitive(client, db_session):
    seed_test_scheme(db_session, name="TypeCase Scheme", scheme_type="Crop Insurance")
    token = _setup_farmer_with_profile(client, "p11-type-case@example.com")
    resp = client.get(RECS + "?scheme_type=crop+insurance&limit=50", headers=auth_headers(token))
    assert resp.status_code == 200
    for rec in resp.json()["recommendations"]:
        assert rec["scheme"]["scheme_type"].lower() == "crop insurance"


# ---------------------------------------------------------------------------
# F. state filter
# ---------------------------------------------------------------------------

def test_state_filter(client, db_session):
    seed_test_scheme(db_session, name="StateFilter Telangana", state="Telangana")
    seed_test_scheme(db_session, name="StateFilter Karnataka", state="Karnataka")
    token = _setup_farmer_with_profile(client, "p11-state-filter@example.com")
    resp = client.get(RECS + "?state=Telangana&limit=50", headers=auth_headers(token))
    assert resp.status_code == 200
    for rec in resp.json()["recommendations"]:
        state_lower = rec["scheme"]["state"].lower()
        assert state_lower in ("telangana", "all india", "pan india", "national")


# ---------------------------------------------------------------------------
# G. Profile completion detail endpoint
# ---------------------------------------------------------------------------

def test_profile_completion_detail_requires_auth(client):
    resp = client.get(PROFILE_DETAIL)
    assert resp.status_code == 401


def test_profile_completion_detail_requires_farmer(client, db_session):
    token = admin_token(client, db_session, email="p11-detail-admin@example.com")
    resp = client.get(PROFILE_DETAIL, headers=auth_headers(token))
    assert resp.status_code == 403


def test_profile_completion_detail_returns_percentage(client, db_session):
    token = farmer_token(client, email="p11-detail-pct@example.com")
    client.post("/api/profile", json=SAMPLE_PROFILE, headers=auth_headers(token))
    resp = client.get(PROFILE_DETAIL, headers=auth_headers(token))
    assert resp.status_code == 200
    payload = resp.json()
    assert "completion_percentage" in payload
    assert 0 <= payload["completion_percentage"] <= 100


def test_profile_completion_detail_returns_missing_fields(client, db_session):
    token = farmer_token(client, email="p11-detail-missing@example.com")
    # Create a minimal profile — some fields will be missing
    partial = {
        "state": "Telangana",
        "primary_crop": "cotton",
        "land_size": "3.0",
        "land_unit": "acres",
    }
    client.post("/api/profile", json=partial, headers=auth_headers(token))
    resp = client.get(PROFILE_DETAIL, headers=auth_headers(token))
    assert resp.status_code == 200
    payload = resp.json()
    assert "missing_fields" in payload
    assert isinstance(payload["missing_fields"], list)
    # Partial profile should have some missing fields
    assert len(payload["missing_fields"]) > 0
    for item in payload["missing_fields"]:
        assert "field" in item
        assert "label" in item
        assert isinstance(item["field"], str)
        assert isinstance(item["label"], str)


def test_profile_completion_detail_full_profile_has_few_missing(client, db_session):
    token = farmer_token(client, email="p11-detail-full@example.com")
    client.post("/api/profile", json=SAMPLE_PROFILE, headers=auth_headers(token))
    resp = client.get(PROFILE_DETAIL, headers=auth_headers(token))
    assert resp.status_code == 200
    payload = resp.json()
    # SAMPLE_PROFILE fills most fields — completion should be high
    assert payload["completion_percentage"] >= 60


def test_profile_completion_detail_no_profile_returns_all_missing(client):
    token = farmer_token(client, email="p11-detail-none@example.com")
    resp = client.get(PROFILE_DETAIL, headers=auth_headers(token))
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["completion_percentage"] == 0
    assert len(payload["missing_fields"]) > 0


# ---------------------------------------------------------------------------
# H. Existing /api/profile/completion unchanged
# ---------------------------------------------------------------------------

def test_existing_completion_endpoint_unchanged(client):
    token = farmer_token(client, email="p11-completion-old@example.com")
    resp = client.get(PROFILE_COMPLETION, headers=auth_headers(token))
    assert resp.status_code == 200
    payload = resp.json()
    # Must still return exactly this structure
    assert set(payload.keys()) == {"completion_percentage"}
    assert isinstance(payload["completion_percentage"], int)


# ---------------------------------------------------------------------------
# I. Both recommendation paths return factors + match_status
# ---------------------------------------------------------------------------

def test_schemes_recommendations_path_also_returns_factors(client, db_session):
    seed_test_scheme(db_session, name="SchemePath Factors Scheme")
    token = _setup_farmer_with_profile(client, "p11-schemepath@example.com")
    resp = client.get("/api/schemes/recommendations", headers=auth_headers(token))
    assert resp.status_code == 200
    for rec in resp.json()["recommendations"]:
        assert "factors" in rec
        assert "match_status" in rec


def test_recommendations_summary_returns_factors(client, db_session):
    seed_test_scheme(db_session, name="Summary Factors Scheme")
    token = _setup_farmer_with_profile(client, "p11-summary-factors@example.com")
    resp = client.get(RECS + "/summary", headers=auth_headers(token))
    assert resp.status_code == 200
    for rec in resp.json()["recommendations"]:
        assert "factors" in rec
        assert "match_status" in rec


# ---------------------------------------------------------------------------
# J. Regression — existing recommendation + saved-scheme behavior
# ---------------------------------------------------------------------------

def test_existing_recommendations_still_work(client, db_session):
    seed_test_scheme(db_session, name="Regression Recs Scheme")
    token = _setup_farmer_with_profile(client, "p11-regression-recs@example.com")
    resp = client.get(RECS, headers=auth_headers(token))
    assert resp.status_code == 200
    payload = resp.json()
    assert "recommendations" in payload
    assert "total" in payload
    # New fields present, old fields still present
    for rec in payload["recommendations"]:
        assert "scheme" in rec
        assert "relevance_score" in rec
        assert "eligible" in rec
        assert "summary" in rec
        assert "factors" in rec
        assert "match_status" in rec


def test_existing_saved_schemes_unaffected(client, db_session, tmp_path, monkeypatch):
    scheme = seed_test_scheme(db_session, name="Regression Save Scheme")
    token = farmer_token(client, email="p11-regression-save@example.com")
    r = client.post(f"/api/schemes/{scheme.id}/save", headers=auth_headers(token))
    assert r.status_code == 201
    r2 = client.get("/api/saved-schemes", headers=auth_headers(token))
    assert r2.status_code == 200
    assert r2.json()["total"] >= 1
