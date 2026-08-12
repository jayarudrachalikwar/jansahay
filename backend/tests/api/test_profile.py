from app.services.auth_service import create_admin_user


def register_farmer(client, email: str = "farmer@example.com", password: str = "password123"):
    return client.post(
        "/api/auth/register",
        json={
            "full_name": "Test Farmer",
            "email": email,
            "phone_number": "9999999999",
            "password": password,
        },
    )


def login_user(client, email: str, password: str):
    return client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def farmer_token(client, email: str = "profile-farmer@example.com") -> str:
    response = register_farmer(client, email=email)
    return response.json()["access_token"]


def admin_token(client, db_session, email: str = "profile-admin@example.com") -> str:
    create_admin_user(
        db_session,
        full_name="Profile Admin",
        email=email,
        password="adminpassword123",
    )
    db_session.commit()
    response = login_user(client, email, "adminpassword123")
    return response.json()["access_token"]


SAMPLE_PROFILE = {
    "date_of_birth": "1990-05-15",
    "gender": "male",
    "state": "Telangana",
    "district": "Nalgonda",
    "village": "Sample Village",
    "land_size": 3.5,
    "land_unit": "acres",
    "land_ownership": "owned",
    "primary_crop": "cotton",
    "secondary_crop": "pulses",
    "soil_type": "black",
    "irrigation_type": "canal",
    "farming_type": "subsistence",
    "annual_income": 120000,
}


def test_unauthenticated_get_profile_returns_401(client):
    response = client.get("/api/profile")
    assert response.status_code == 401


def test_unauthenticated_post_profile_returns_401(client):
    response = client.post("/api/profile", json=SAMPLE_PROFILE)
    assert response.status_code == 401


def test_farmer_can_create_profile(client):
    token = farmer_token(client, email="create-profile@example.com")
    response = client.post("/api/profile", json=SAMPLE_PROFILE, headers=auth_headers(token))

    assert response.status_code == 201
    payload = response.json()
    assert payload["state"] == "Telangana"
    assert payload["primary_crop"] == "cotton"


def test_farmer_can_retrieve_own_profile(client):
    token = farmer_token(client, email="get-profile@example.com")
    client.post("/api/profile", json=SAMPLE_PROFILE, headers=auth_headers(token))

    response = client.get("/api/profile", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json()["district"] == "Nalgonda"


def test_farmer_can_update_own_profile(client):
    token = farmer_token(client, email="update-profile@example.com")
    client.post("/api/profile", json=SAMPLE_PROFILE, headers=auth_headers(token))

    updated = {**SAMPLE_PROFILE, "village": "Updated Village"}
    response = client.put("/api/profile", json=updated, headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json()["village"] == "Updated Village"


def test_farmer_can_retrieve_completion_percentage(client):
    token = farmer_token(client, email="completion-profile@example.com")
    client.post("/api/profile", json=SAMPLE_PROFILE, headers=auth_headers(token))

    response = client.get("/api/profile/completion", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json()["completion_percentage"] == 100


def test_duplicate_profile_creation_returns_409(client):
    token = farmer_token(client, email="duplicate-profile@example.com")
    client.post("/api/profile", json=SAMPLE_PROFILE, headers=auth_headers(token))

    response = client.post("/api/profile", json=SAMPLE_PROFILE, headers=auth_headers(token))

    assert response.status_code == 409


def test_admin_get_profile_returns_403(client, db_session):
    token = admin_token(client, db_session, email="admin-get-profile@example.com")
    response = client.get("/api/profile", headers=auth_headers(token))
    assert response.status_code == 403


def test_admin_post_profile_returns_403(client, db_session):
    token = admin_token(client, db_session, email="admin-post-profile@example.com")
    response = client.post("/api/profile", json=SAMPLE_PROFILE, headers=auth_headers(token))
    assert response.status_code == 403


def test_admin_put_profile_returns_403(client, db_session):
    token = admin_token(client, db_session, email="admin-put-profile@example.com")
    response = client.put("/api/profile", json=SAMPLE_PROFILE, headers=auth_headers(token))
    assert response.status_code == 403


def test_invalid_negative_land_size_returns_422(client):
    token = farmer_token(client, email="invalid-land@example.com")
    invalid = {**SAMPLE_PROFILE, "land_size": -1}
    response = client.post("/api/profile", json=invalid, headers=auth_headers(token))
    assert response.status_code == 422


def test_invalid_negative_annual_income_returns_422(client):
    token = farmer_token(client, email="invalid-income@example.com")
    invalid = {**SAMPLE_PROFILE, "annual_income": -100}
    response = client.post("/api/profile", json=invalid, headers=auth_headers(token))
    assert response.status_code == 422


def test_farmer_profile_belongs_to_correct_user(client):
    token = farmer_token(client, email="owner-profile@example.com")
    me = client.get("/api/auth/me", headers=auth_headers(token)).json()
    created = client.post("/api/profile", json=SAMPLE_PROFILE, headers=auth_headers(token)).json()

    assert created["user_id"] == me["id"]


def test_farmer_cannot_access_another_farmers_profile_data(client):
    token_one = farmer_token(client, email="farmer-one@example.com")
    token_two = farmer_token(client, email="farmer-two@example.com")

    created = client.post(
        "/api/profile",
        json={**SAMPLE_PROFILE, "state": "Farmer One State"},
        headers=auth_headers(token_one),
    ).json()

    response = client.get("/api/profile", headers=auth_headers(token_two))

    assert response.status_code == 404
    assert response.json()["detail"] == "Farmer profile not found"

    own_profile = client.get("/api/profile", headers=auth_headers(token_one)).json()
    assert own_profile["id"] == created["id"]
    assert own_profile["state"] == "Farmer One State"
