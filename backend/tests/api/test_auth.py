from datetime import timedelta

from jose import jwt

from app.auth.security import create_access_token
from app.core.config import settings


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


def test_farmer_registration_succeeds(client):
    response = register_farmer(client, email="farmer1@example.com")

    assert response.status_code == 201
    payload = response.json()
    assert "access_token" in payload
    assert payload["token_type"] == "bearer"


def test_duplicate_registration_fails(client):
    register_farmer(client, email="duplicate@example.com")
    response = register_farmer(client, email="duplicate@example.com")

    assert response.status_code == 400
    assert response.json()["detail"] == "Email is already registered"


def test_login_succeeds(client):
    register_farmer(client, email="login@example.com", password="password123")
    response = login_user(client, "login@example.com", "password123")

    assert response.status_code == 200
    assert "access_token" in response.json()


def test_wrong_password_fails(client):
    register_farmer(client, email="wrongpass@example.com", password="password123")
    response = login_user(client, "wrongpass@example.com", "wrongpassword")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_auth_me_requires_authentication(client):
    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_farmer_can_access_farmer_test_endpoint(client):
    register_response = register_farmer(client, email="rbac-farmer@example.com")
    token = register_response.json()["access_token"]

    response = client.get("/api/auth/test/farmer", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json()["message"] == "Farmer access granted"


def test_farmer_cannot_access_admin_endpoint(client):
    register_response = register_farmer(client, email="rbac-farmer2@example.com")
    token = register_response.json()["access_token"]

    response = client.get("/api/auth/test/admin", headers=auth_headers(token))

    assert response.status_code == 403
    assert response.json()["detail"] == "admin access required"


def test_admin_can_access_admin_test_endpoint(client, db_session):
    from app.services.auth_service import create_admin_user

    admin = create_admin_user(
        db_session,
        full_name="Test Admin",
        email="admin-test@example.com",
        password="adminpassword123",
    )
    db_session.commit()

    login_response = login_user(client, admin.email, "adminpassword123")
    token = login_response.json()["access_token"]

    response = client.get("/api/auth/test/admin", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json()["message"] == "Admin access granted"


def test_invalid_jwt_is_rejected(client):
    response = client.get(
        "/api/auth/me",
        headers=auth_headers("invalid.token.value"),
    )

    assert response.status_code == 401


def test_expired_jwt_is_rejected(client):
    expired_token = create_access_token(
        {"sub": "999"},
        expires_delta=timedelta(seconds=-1),
    )

    response = client.get("/api/auth/me", headers=auth_headers(expired_token))

    assert response.status_code == 401


def test_auth_me_returns_current_user(client):
    register_response = register_farmer(client, email="me@example.com")
    token = register_response.json()["access_token"]

    response = client.get("/api/auth/me", headers=auth_headers(token))

    assert response.status_code == 200
    payload = response.json()
    assert payload["email"] == "me@example.com"
    assert payload["role"] == "farmer"
    assert "password_hash" not in payload
