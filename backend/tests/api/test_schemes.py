from app.models.scheme import GovernmentScheme
from app.models.scheme_eligibility import SchemeEligibilityCriterion
from app.services.auth_service import create_admin_user
from tests.api.test_profile import (
    SAMPLE_PROFILE,
    admin_token,
    auth_headers,
    farmer_token,
    login_user,
    register_farmer,
)


def seed_test_scheme(
    db_session,
    *,
    name: str = "Test Scheme Alpha",
    state: str = "Telangana",
    scheme_type: str = "Financial Assistance",
    criteria: list[dict] | None = None,
) -> GovernmentScheme:
    scheme = GovernmentScheme(
        name=name,
        short_description="Sample short description for testing.",
        detailed_description="Sample detailed description for testing eligibility.",
        department="Test Department",
        state=state,
        scheme_type=scheme_type,
        benefits="Sample benefits for eligible farmers.",
        application_process="Apply through the local agriculture office.",
        official_website="https://example.dev/test-scheme",
        is_active=True,
    )
    db_session.add(scheme)
    db_session.flush()

    default_criteria = criteria or [
        {
            "criterion_type": "profile",
            "field_name": "state",
            "operator": "equals",
            "expected_value": "Telangana",
            "description": "Farmer's state matches the scheme eligibility.",
        },
        {
            "criterion_type": "profile",
            "field_name": "annual_income",
            "operator": "less_than_or_equal",
            "expected_value": "200000",
            "description": "Annual income satisfies the scheme requirement.",
        },
    ]
    for item in default_criteria:
        db_session.add(SchemeEligibilityCriterion(scheme_id=scheme.id, **item))

    db_session.commit()
    db_session.refresh(scheme)
    return scheme


def create_farmer_with_profile(client, email: str, profile: dict | None = None) -> str:
    token = farmer_token(client, email=email)
    payload = profile or SAMPLE_PROFILE
    client.post("/api/profile", json=payload, headers=auth_headers(token))
    return token


def test_unauthenticated_list_schemes_returns_401(client):
    response = client.get("/api/schemes")
    assert response.status_code == 401


def test_farmer_can_list_schemes(client, db_session):
    seed_test_scheme(db_session, name="Farmer Visible Scheme")
    token = farmer_token(client, email="schemes-farmer@example.com")

    response = client.get("/api/schemes", headers=auth_headers(token))

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert any(item["name"] == "Farmer Visible Scheme" for item in payload["schemes"])


def test_admin_cannot_access_farmer_only_eligibility(client, db_session):
    scheme = seed_test_scheme(db_session, name="Admin Blocked Eligibility Scheme")
    token = admin_token(client, db_session, email="schemes-admin-elig@example.com")

    response = client.get(
        f"/api/schemes/{scheme.id}/eligibility",
        headers=auth_headers(token),
    )
    assert response.status_code == 403


def test_scheme_detail_works(client, db_session):
    scheme = seed_test_scheme(db_session, name="Detail Scheme")
    token = farmer_token(client, email="scheme-detail@example.com")

    response = client.get(f"/api/schemes/{scheme.id}", headers=auth_headers(token))

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Detail Scheme"
    assert payload["detailed_description"]
    assert len(payload["eligibility_criteria"]) >= 1


def test_unknown_scheme_returns_404(client):
    token = farmer_token(client, email="unknown-scheme@example.com")
    response = client.get("/api/schemes/999999", headers=auth_headers(token))
    assert response.status_code == 404


def test_search_works(client, db_session):
    seed_test_scheme(db_session, name="Unique Search Crop Insurance")
    token = farmer_token(client, email="search-schemes@example.com")

    response = client.get(
        "/api/schemes",
        params={"search": "Unique Search"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    names = [item["name"] for item in response.json()["schemes"]]
    assert "Unique Search Crop Insurance" in names


def test_state_filter_works(client, db_session):
    seed_test_scheme(db_session, name="Telangana Only Scheme", state="Telangana")
    seed_test_scheme(db_session, name="Karnataka Only Scheme", state="Karnataka")
    token = farmer_token(client, email="state-filter@example.com")

    response = client.get(
        "/api/schemes",
        params={"state": "Telangana"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    states = {item["state"] for item in response.json()["schemes"]}
    assert states == {"Telangana"}


def test_farmer_without_profile_cannot_check_eligibility(client, db_session):
    scheme = seed_test_scheme(db_session, name="No Profile Eligibility Scheme")
    token = farmer_token(client, email="no-profile-elig@example.com")

    response = client.get(
        f"/api/schemes/{scheme.id}/eligibility",
        headers=auth_headers(token),
    )

    assert response.status_code == 404
    assert "profile" in response.json()["detail"].lower()


def test_eligible_farmer_receives_eligible_true(client, db_session):
    scheme = seed_test_scheme(
        db_session,
        name="Eligible Farmer Scheme",
        criteria=[
            {
                "criterion_type": "profile",
                "field_name": "state",
                "operator": "equals",
                "expected_value": "Telangana",
                "description": "Farmer's state matches the scheme eligibility.",
            }
        ],
    )
    token = create_farmer_with_profile(client, "eligible-farmer@example.com")

    response = client.get(
        f"/api/schemes/{scheme.id}/eligibility",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["eligible"] is True


def test_ineligible_farmer_receives_eligible_false(client, db_session):
    scheme = seed_test_scheme(
        db_session,
        name="Ineligible Farmer Scheme",
        criteria=[
            {
                "criterion_type": "profile",
                "field_name": "annual_income",
                "operator": "less_than_or_equal",
                "expected_value": "50000",
                "description": "Annual income must be within subsidy limits.",
            }
        ],
    )
    token = create_farmer_with_profile(
        client,
        "ineligible-farmer@example.com",
        profile={**SAMPLE_PROFILE, "annual_income": 120000},
    )

    response = client.get(
        f"/api/schemes/{scheme.id}/eligibility",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["eligible"] is False


def test_eligibility_reasons_are_returned(client, db_session):
    scheme = seed_test_scheme(db_session, name="Reasons Scheme")
    token = create_farmer_with_profile(client, "reasons-farmer@example.com")

    response = client.get(
        f"/api/schemes/{scheme.id}/eligibility",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["reasons"], list)
    assert len(payload["reasons"]) >= 1


def test_recommendations_require_farmer_authentication(client):
    response = client.get("/api/schemes/recommendations")
    assert response.status_code == 401


def test_recommendations_return_ranked_schemes(client, db_session):
    seed_test_scheme(
        db_session,
        name="Recommendation High Match",
        criteria=[
            {
                "criterion_type": "profile",
                "field_name": "state",
                "operator": "equals",
                "expected_value": "Telangana",
                "description": "State match",
            }
        ],
    )
    seed_test_scheme(
        db_session,
        name="Recommendation Low Match",
        state="Karnataka",
        criteria=[
            {
                "criterion_type": "profile",
                "field_name": "state",
                "operator": "equals",
                "expected_value": "Karnataka",
                "description": "State match",
            }
        ],
    )
    token = create_farmer_with_profile(client, "recommendations-farmer@example.com")

    response = client.get("/api/schemes/recommendations", headers=auth_headers(token))

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 2
    assert payload["recommendations"][0]["relevance_score"] >= payload["recommendations"][1]["relevance_score"]


def test_admin_cannot_access_recommendations(client, db_session):
    seed_test_scheme(db_session, name="Admin Blocked Recommendations")
    token = admin_token(client, db_session, email="schemes-admin-rec@example.com")

    response = client.get("/api/schemes/recommendations", headers=auth_headers(token))
    assert response.status_code == 403


def test_seeded_schemes_are_returned(client, db_session):
    for index in range(5):
        seed_test_scheme(db_session, name=f"Seeded Scheme {index + 1}")

    token = farmer_token(client, email="seeded-schemes@example.com")
    response = client.get("/api/schemes", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json()["total"] >= 5
