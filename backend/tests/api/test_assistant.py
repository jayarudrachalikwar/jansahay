from unittest.mock import patch

from app.core.config import settings
from app.services.assistant_service import GeminiAPIError, GeminiNotConfiguredError
from tests.api.test_profile import admin_token, auth_headers, farmer_token
from tests.api.test_schemes import create_farmer_with_profile, seed_test_scheme


def assistant_payload(message: str, history: list[dict] | None = None) -> dict:
    payload = {"message": message}
    if history is not None:
        payload["history"] = history
    return payload


@patch("app.services.assistant_service.generate_assistant_response")
def test_unauthenticated_assistant_request_returns_401(mock_generate, client):
    response = client.post(
        "/api/assistant/chat",
        json=assistant_payload("Which schemes are suitable for me?"),
    )
    assert response.status_code == 401
    mock_generate.assert_not_called()


@patch("app.services.assistant_service.generate_assistant_response", return_value="Sample answer.")
def test_authenticated_farmer_can_access_assistant(mock_generate, client, db_session):
    seed_test_scheme(db_session, name="Assistant Farmer Scheme")
    token = farmer_token(client, email="assistant-farmer@example.com")

    response = client.post(
        "/api/assistant/chat",
        json=assistant_payload("Which schemes are suitable for me?"),
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Sample answer."
    assert "rag_sources" in data
    assert isinstance(data["rag_sources"], list)
    mock_generate.assert_called_once()


def test_empty_message_returns_422(client):
    token = farmer_token(client, email="assistant-empty@example.com")
    response = client.post(
        "/api/assistant/chat",
        json={"message": "   "},
        headers=auth_headers(token),
    )
    assert response.status_code == 422


def test_missing_gemini_configuration_handled_gracefully(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    seed_test_scheme(db_session, name="Assistant Config Scheme")
    token = farmer_token(client, email="assistant-config@example.com")

    response = client.post(
        "/api/assistant/chat",
        json=assistant_payload("Tell me about schemes"),
        headers=auth_headers(token),
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "AI assistant is not configured."


@patch("app.services.assistant_service.generate_assistant_response")
def test_gemini_api_failure_handled_gracefully(mock_generate, client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    mock_generate.side_effect = GeminiAPIError("AI assistant is temporarily unavailable. Please try again.")
    seed_test_scheme(db_session, name="Assistant Failure Scheme")
    token = farmer_token(client, email="assistant-failure@example.com")

    response = client.post(
        "/api/assistant/chat",
        json=assistant_payload("Tell me about schemes"),
        headers=auth_headers(token),
    )

    assert response.status_code == 503
    assert "temporarily unavailable" in response.json()["detail"]


@patch("app.services.assistant_service.generate_assistant_response")
def test_scheme_context_is_retrieved_from_database(mock_generate, client, db_session):
    scheme = seed_test_scheme(db_session, name="Unique Assistant Scheme Name")
    token = farmer_token(client, email="assistant-scheme-context@example.com")

    def capture_context(**kwargs):
        assert "Unique Assistant Scheme Name" in kwargs["system_instruction"]
        return "Scheme context loaded."

    mock_generate.side_effect = capture_context

    response = client.post(
        "/api/assistant/chat",
        json=assistant_payload("Tell me about Unique Assistant Scheme Name"),
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert "Unique Assistant Scheme Name" in response.json()["sources"]
    assert scheme.name in response.json()["sources"]


@patch("app.services.assistant_service.check_scheme_eligibility")
@patch("app.services.assistant_service.generate_assistant_response", return_value="Eligibility explained.")
def test_eligibility_question_uses_deterministic_service(
    mock_generate,
    mock_check_eligibility,
    client,
    db_session,
):
    from app.services.eligibility_service import EligibilityResult

    scheme = seed_test_scheme(db_session, name="Assistant Eligibility Scheme")
    mock_check_eligibility.return_value = (
        scheme,
        EligibilityResult(eligible=True, reasons=["State matches the scheme requirement."]),
    )
    token = create_farmer_with_profile(client, "assistant-eligibility@example.com")

    response = client.post(
        "/api/assistant/chat",
        json=assistant_payload(f"Am I eligible for {scheme.name}?"),
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["eligibility_checked"] is True
    mock_check_eligibility.assert_called_once()


@patch("app.services.assistant_service.get_scheme_recommendations")
@patch("app.services.assistant_service.generate_assistant_response", return_value="Recommendations explained.")
def test_recommendation_question_uses_existing_recommendation_service(
    mock_generate,
    mock_get_recommendations,
    client,
    db_session,
):
    from app.services.recommendation_service import SchemeRecommendation

    scheme = seed_test_scheme(db_session, name="Assistant Recommendation Scheme")
    mock_get_recommendations.return_value = [
        SchemeRecommendation(
            scheme=scheme,
            relevance_score=85,
            eligible=True,
            summary="Profile-based recommendation.",
        )
    ]
    token = create_farmer_with_profile(client, "assistant-recommendations@example.com")

    response = client.post(
        "/api/assistant/chat",
        json=assistant_payload("Which schemes are suitable for me?"),
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    mock_get_recommendations.assert_called_once()


@patch("app.services.assistant_service.generate_assistant_response")
def test_admin_does_not_receive_farmer_private_profile_context(
    mock_generate,
    client,
    db_session,
):
    seed_test_scheme(db_session, name="Assistant Admin Scheme")
    token = admin_token(client, db_session, email="assistant-admin@example.com")

    def capture_context(**kwargs):
        assert "farmer_profile" not in kwargs["system_instruction"]
        assert '"user_role": "admin"' in kwargs["system_instruction"]
        return "Admin-safe answer."

    mock_generate.side_effect = capture_context

    response = client.post(
        "/api/assistant/chat",
        json=assistant_payload("What information is in my farmer profile?"),
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "Admin-safe answer."


@patch("app.services.assistant_service.generate_assistant_response", return_value="Safe answer.")
def test_no_secrets_exposed_in_response(mock_generate, client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "super-secret-test-key")
    seed_test_scheme(db_session, name="Assistant Secret Scheme")
    token = farmer_token(client, email="assistant-secrets@example.com")

    response = client.post(
        "/api/assistant/chat",
        json=assistant_payload("Tell me about schemes"),
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    payload = response.json()
    serialized = str(payload).lower()
    assert "super-secret-test-key" not in serialized
    assert "system_instruction" not in serialized
    assert "prompt" not in payload


@patch("app.services.assistant_service.generate_assistant_response", return_value="Non-RAG answer.")
def test_rag_sources_defaults_to_empty_list_for_non_rag_query(mock_generate, client, db_session):
    """rag_sources must be [] when the message contains no DOCUMENT_RAG_KEYWORDS."""
    seed_test_scheme(db_session, name="Non RAG Query Scheme")
    token = farmer_token(client, email="assistant-rag-default@example.com")

    response = client.post(
        "/api/assistant/chat",
        json=assistant_payload("Which schemes are available?"),
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    data = response.json()
    assert "rag_sources" in data
    assert data["rag_sources"] == []
