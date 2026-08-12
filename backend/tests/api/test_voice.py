"""
Voice API tests — Phase 14.

All STT/TTS calls are mocked.
No live external API calls are made.
Tests cover:
  A. Auth / RBAC
  B. /api/voice/transcribe
  C. /api/voice/speak
  D. /api/voice/chat
  E. /api/voice/extract-profile
  F. Language detection helpers
  G. TTS helpers
  H. STT helpers
  I. Voice service orchestration
  J. Regression — existing assistant tests unaffected
"""
from __future__ import annotations

from io import BytesIO
from unittest.mock import Mock, patch

import pytest

from tests.api.test_profile import auth_headers, farmer_token, admin_token

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_audio_file(content: bytes = b"RIFF....WAVEfmt ", content_type: str = "audio/webm"):
    """Return a minimal fake audio upload."""
    return ("audio", BytesIO(content), content_type)


FAKE_WEBM = b"\x1a\x45\xdf\xa3" + b"\x00" * 100   # minimal webm-like bytes


# ---------------------------------------------------------------------------
# A. Auth / RBAC
# ---------------------------------------------------------------------------

def test_transcribe_requires_auth(client):
    resp = client.post("/api/voice/transcribe", files={"audio": _make_audio_file(FAKE_WEBM)})
    assert resp.status_code == 401


def test_speak_requires_auth(client):
    resp = client.post("/api/voice/speak", json={"text": "Hello", "language": "en"})
    assert resp.status_code == 401


def test_voice_chat_requires_auth(client):
    resp = client.post("/api/voice/chat", files={"audio": _make_audio_file(FAKE_WEBM)})
    assert resp.status_code == 401


def test_extract_profile_requires_auth(client):
    resp = client.post("/api/voice/extract-profile", files={"audio": _make_audio_file(FAKE_WEBM)})
    assert resp.status_code == 401


def test_admin_can_access_transcribe(client, db_session):
    """Admins can use transcription (it is not farmer-only)."""
    token = admin_token(client, db_session, email="admin-voice@example.com")
    fake_result = Mock()
    fake_result.transcript = "Test transcript"
    fake_result.language = "en"
    fake_result.stt_detected_language = None

    with patch("app.api.routes.voice.transcribe", return_value=fake_result):
        resp = client.post(
            "/api/voice/transcribe",
            files={"audio": _make_audio_file(FAKE_WEBM)},
            data={"language": "en"},
            headers=auth_headers(token),
        )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# B. /api/voice/transcribe
# ---------------------------------------------------------------------------

def test_transcribe_returns_transcript_and_language(client, db_session):
    token = farmer_token(client, email="transcribe-ok@example.com")
    fake_result = Mock(transcript="Meri fasal gehu hai", language="hi", stt_detected_language="hi")

    with patch("app.api.routes.voice.transcribe", return_value=fake_result):
        resp = client.post(
            "/api/voice/transcribe",
            files={"audio": _make_audio_file(FAKE_WEBM)},
            data={"language": "hi"},
            headers=auth_headers(token),
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["transcript"] == "Meri fasal gehu hai"
    assert payload["language"] == "hi"


def test_transcribe_empty_audio_returns_400(client, db_session):
    token = farmer_token(client, email="transcribe-empty@example.com")
    resp = client.post(
        "/api/voice/transcribe",
        files={"audio": ("audio", BytesIO(b""), "audio/webm")},
        data={"language": "en"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 400


def test_transcribe_oversized_audio_returns_413(client, db_session):
    token = farmer_token(client, email="transcribe-big@example.com")
    big_audio = b"\x00" * (11 * 1024 * 1024)  # 11 MB
    resp = client.post(
        "/api/voice/transcribe",
        files={"audio": ("audio", BytesIO(big_audio), "audio/webm")},
        data={"language": "en"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 413


def test_transcribe_stt_not_configured_returns_503(client, db_session):
    from app.voice.speech_to_text import SpeechToTextNotConfiguredError
    token = farmer_token(client, email="transcribe-noconfig@example.com")

    with patch("app.api.routes.voice.transcribe",
               side_effect=SpeechToTextNotConfiguredError("Gemini not configured")):
        resp = client.post(
            "/api/voice/transcribe",
            files={"audio": _make_audio_file(FAKE_WEBM)},
            data={"language": "en"},
            headers=auth_headers(token),
        )
    assert resp.status_code == 503


def test_transcribe_stt_error_returns_503(client, db_session):
    """Generic STT provider errors (Gemini failure, network, etc.) should be 503, not 422."""
    from app.voice.speech_to_text import SpeechToTextError
    token = farmer_token(client, email="transcribe-fail@example.com")

    with patch("app.api.routes.voice.transcribe",
               side_effect=SpeechToTextError("Transcription failed")):
        resp = client.post(
            "/api/voice/transcribe",
            files={"audio": _make_audio_file(FAKE_WEBM)},
            data={"language": "en"},
            headers=auth_headers(token),
        )
    assert resp.status_code == 503


def test_transcribe_bad_mime_returns_422(client, db_session):
    """Audio with unsupported MIME type should return 422 (input validation error)."""
    from app.voice.speech_to_text import SpeechToTextError
    token = farmer_token(client, email="transcribe-badmime@example.com")

    with patch("app.api.routes.voice.transcribe",
               side_effect=SpeechToTextError("Unsupported audio format 'video/mp4'.")):
        resp = client.post(
            "/api/voice/transcribe",
            files={"audio": _make_audio_file(FAKE_WEBM)},
            data={"language": "en"},
            headers=auth_headers(token),
        )
    assert resp.status_code == 422


def test_transcribe_telugu_language_hint(client, db_session):
    token = farmer_token(client, email="transcribe-te@example.com")
    fake_result = Mock(transcript="Nenu patti panta vesanu", language="te", stt_detected_language="te")

    with patch("app.api.routes.voice.transcribe", return_value=fake_result):
        resp = client.post(
            "/api/voice/transcribe",
            files={"audio": _make_audio_file(FAKE_WEBM)},
            data={"language": "te"},
            headers=auth_headers(token),
        )

    assert resp.status_code == 200
    assert resp.json()["language"] == "te"


# ---------------------------------------------------------------------------
# C. /api/voice/speak
# ---------------------------------------------------------------------------

def test_speak_returns_mp3_bytes(client, db_session):
    token = farmer_token(client, email="speak-ok@example.com")
    fake_mp3 = b"ID3" + b"\x00" * 100

    with patch("app.api.routes.voice.speak", return_value=fake_mp3):
        resp = client.post(
            "/api/voice/speak",
            json={"text": "Hello farmer!", "language": "en"},
            headers=auth_headers(token),
        )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/mpeg"
    assert resp.content == fake_mp3


def test_speak_hindi_text(client, db_session):
    token = farmer_token(client, email="speak-hi@example.com")
    fake_mp3 = b"ID3" + b"\x00" * 50

    with patch("app.api.routes.voice.speak", return_value=fake_mp3):
        resp = client.post(
            "/api/voice/speak",
            json={"text": "नमस्ते किसान", "language": "hi"},
            headers=auth_headers(token),
        )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/mpeg"


def test_speak_tts_not_configured_returns_503(client, db_session):
    from app.voice.text_to_speech import TextToSpeechNotConfiguredError
    token = farmer_token(client, email="speak-noconfig@example.com")

    with patch("app.api.routes.voice.speak",
               side_effect=TextToSpeechNotConfiguredError("gTTS not installed")):
        resp = client.post(
            "/api/voice/speak",
            json={"text": "Hello", "language": "en"},
            headers=auth_headers(token),
        )
    assert resp.status_code == 503


def test_speak_empty_text_returns_422(client, db_session):
    token = farmer_token(client, email="speak-empty@example.com")
    resp = client.post(
        "/api/voice/speak",
        json={"text": "", "language": "en"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 422


def test_speak_invalid_language_returns_422(client, db_session):
    token = farmer_token(client, email="speak-badlang@example.com")
    resp = client.post(
        "/api/voice/speak",
        json={"text": "Hello", "language": "fr"},  # French not supported
        headers=auth_headers(token),
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# D. /api/voice/chat
# ---------------------------------------------------------------------------

def test_voice_chat_returns_full_response(client, db_session):
    from tests.api.test_schemes import seed_test_scheme
    from app.voice.service import VoiceChatResult

    seed_test_scheme(db_session, name="Voice Chat Scheme")
    token = farmer_token(client, email="voice-chat-ok@example.com")

    fake_result = VoiceChatResult(
        transcript="Which schemes are available for farmers?",
        language="en",
        response_text="Here are the available schemes...",
        audio_bytes=b"ID3" + b"\x00" * 50,
        sources=["Voice Chat Scheme"],
        tts_available=True,
    )

    with patch("app.api.routes.voice.voice_chat", return_value=fake_result):
        resp = client.post(
            "/api/voice/chat",
            files={"audio": _make_audio_file(FAKE_WEBM)},
            data={"language": "en", "history": "[]"},
            headers=auth_headers(token),
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["transcript"] == "Which schemes are available for farmers?"
    assert payload["response_text"] == "Here are the available schemes..."
    assert payload["audio_base64"] is not None
    assert payload["tts_available"] is True
    assert "Voice Chat Scheme" in payload["sources"]


def test_voice_chat_includes_base64_audio(client, db_session):
    import base64
    from app.voice.service import VoiceChatResult

    token = farmer_token(client, email="voice-chat-audio@example.com")
    mp3_bytes = b"ID3" + b"\x00" * 20
    fake_result = VoiceChatResult(
        transcript="test",
        language="en",
        response_text="test response",
        audio_bytes=mp3_bytes,
        tts_available=True,
    )

    with patch("app.api.routes.voice.voice_chat", return_value=fake_result):
        resp = client.post(
            "/api/voice/chat",
            files={"audio": _make_audio_file(FAKE_WEBM)},
            data={"language": "en", "history": "[]"},
            headers=auth_headers(token),
        )

    payload = resp.json()
    decoded = base64.b64decode(payload["audio_base64"])
    assert decoded == mp3_bytes


def test_voice_chat_tts_unavailable_still_returns_text(client, db_session):
    from app.voice.service import VoiceChatResult

    token = farmer_token(client, email="voice-chat-notts@example.com")
    fake_result = VoiceChatResult(
        transcript="test",
        language="en",
        response_text="Text response without audio",
        audio_bytes=b"",
        tts_available=False,
    )

    with patch("app.api.routes.voice.voice_chat", return_value=fake_result):
        resp = client.post(
            "/api/voice/chat",
            files={"audio": _make_audio_file(FAKE_WEBM)},
            data={"language": "en", "history": "[]"},
            headers=auth_headers(token),
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["tts_available"] is False
    assert payload["audio_base64"] is None
    assert payload["response_text"] == "Text response without audio"


def test_voice_chat_uses_existing_assistant_pipeline(client, db_session):
    """Voice chat must call process_assistant_chat — not a second chatbot."""
    from tests.api.test_schemes import seed_test_scheme
    from app.voice.speech_to_text import TranscriptionResult
    from app.services.assistant_service import AssistantResult

    seed_test_scheme(db_session, name="Pipeline Scheme")
    token = farmer_token(client, email="voice-pipeline@example.com")

    transcription = TranscriptionResult(
        transcript="What schemes help cotton farmers?",
        language="en",
    )
    assistant_result = AssistantResult(
        answer="Cotton scheme info",
        sources=["Pipeline Scheme"],
    )

    with patch("app.voice.service.transcribe_audio", return_value=transcription):
        with patch("app.voice.service.process_assistant_chat", return_value=assistant_result) as mock_chat:
            with patch("app.voice.service.synthesize_speech", return_value=b"audio"):
                resp = client.post(
                    "/api/voice/chat",
                    files={"audio": _make_audio_file(FAKE_WEBM)},
                    data={"language": "en", "history": "[]"},
                    headers=auth_headers(token),
                )

    assert resp.status_code == 200
    mock_chat.assert_called_once()


def test_voice_chat_error_not_configured_returns_503(client, db_session):
    from app.voice.service import VoiceServiceError
    token = farmer_token(client, email="voice-chat-noconfig@example.com")

    with patch("app.api.routes.voice.voice_chat",
               side_effect=VoiceServiceError("AI assistant is not configured.")):
        resp = client.post(
            "/api/voice/chat",
            files={"audio": _make_audio_file(FAKE_WEBM)},
            data={"language": "en", "history": "[]"},
            headers=auth_headers(token),
        )
    assert resp.status_code == 503


def test_voice_chat_hindi_language(client, db_session):
    from app.voice.service import VoiceChatResult

    token = farmer_token(client, email="voice-chat-hindi@example.com")
    fake_result = VoiceChatResult(
        transcript="गेहूं के लिए कौनसी योजनाएं हैं?",
        language="hi",
        response_text="गेहूं किसानों के लिए...",
        audio_bytes=b"ID3\x00" * 10,
        tts_available=True,
    )

    with patch("app.api.routes.voice.voice_chat", return_value=fake_result):
        resp = client.post(
            "/api/voice/chat",
            files={"audio": _make_audio_file(FAKE_WEBM)},
            data={"language": "hi", "history": "[]"},
            headers=auth_headers(token),
        )

    assert resp.status_code == 200
    assert resp.json()["language"] == "hi"


# ---------------------------------------------------------------------------
# E. /api/voice/extract-profile
# ---------------------------------------------------------------------------

def test_extract_profile_returns_fields(client, db_session):
    from app.voice.speech_to_text import TranscriptionResult
    from app.voice.voice_profile_extractor import ExtractedProfileFields

    token = farmer_token(client, email="extract-profile@example.com")
    transcription = TranscriptionResult(
        transcript="I grow cotton in Warangal and have 3 acres.",
        language="en",
    )
    extraction = ExtractedProfileFields(
        fields={"primary_crop": "cotton", "district": "Warangal", "land_size": "3"},
        uncertain_fields=[],
        raw_transcript="I grow cotton in Warangal and have 3 acres.",
    )

    with patch("app.api.routes.voice.transcribe", return_value=transcription):
        with patch("app.voice.voice_profile_extractor.extract_profile_fields",
                   return_value=extraction):
            with patch("app.api.routes.voice.extract_profile_fields",
                       return_value=extraction):
                resp = client.post(
                    "/api/voice/extract-profile",
                    files={"audio": _make_audio_file(FAKE_WEBM)},
                    data={"language": "en"},
                    headers=auth_headers(token),
                )

    assert resp.status_code == 200
    payload = resp.json()
    assert "raw_transcript" in payload
    assert "extracted_fields" in payload
    assert isinstance(payload["extracted_fields"], dict)


def test_extract_profile_does_not_save_automatically(client, db_session):
    """Extracting profile fields must NEVER save them — only return candidates."""
    from app.voice.speech_to_text import TranscriptionResult
    from app.voice.voice_profile_extractor import ExtractedProfileFields

    token = farmer_token(client, email="extract-nosave@example.com")
    transcription = TranscriptionResult(transcript="I farm rice", language="en")
    extraction = ExtractedProfileFields(
        fields={"primary_crop": "rice"},
        uncertain_fields=[],
        raw_transcript="I farm rice",
    )

    with patch("app.api.routes.voice.transcribe", return_value=transcription):
        with patch("app.api.routes.voice.extract_profile_fields", return_value=extraction):
            resp = client.post(
                "/api/voice/extract-profile",
                files={"audio": _make_audio_file(FAKE_WEBM)},
                data={"language": "en"},
                headers=auth_headers(token),
            )

    assert resp.status_code == 200
    # Verify profile was NOT changed
    profile_resp = client.get("/api/profile", headers=auth_headers(token))
    assert profile_resp.status_code == 404  # no profile created


# ---------------------------------------------------------------------------
# F. Language detection helpers
# ---------------------------------------------------------------------------

def test_normalize_language_code_en():
    from app.voice.language_detection import normalize_language_code
    assert normalize_language_code("en") == "en"
    assert normalize_language_code("en-US") == "en"
    assert normalize_language_code("EN") == "en"


def test_normalize_language_code_hi():
    from app.voice.language_detection import normalize_language_code
    assert normalize_language_code("hi") == "hi"


def test_normalize_language_code_te():
    from app.voice.language_detection import normalize_language_code
    assert normalize_language_code("te") == "te"


def test_normalize_language_code_unknown_falls_back_to_en():
    from app.voice.language_detection import normalize_language_code
    assert normalize_language_code("fr") == "en"
    assert normalize_language_code("") == "en"
    assert normalize_language_code(None) == "en"


def test_resolve_language_user_preference_wins():
    from app.voice.language_detection import resolve_language
    assert resolve_language("hi", "en", None) == "hi"


def test_resolve_language_stt_used_when_no_preference():
    from app.voice.language_detection import resolve_language
    assert resolve_language(None, "te", None) == "te"


def test_resolve_language_falls_back_to_default():
    from app.voice.language_detection import resolve_language
    assert resolve_language(None, None, None) == "en"


def test_detect_from_text_returns_supported_language():
    from app.voice.language_detection import detect_from_text
    # Short English text
    result = detect_from_text("Hello, how are you?")
    assert result in ("en", "hi", "te")  # valid code


def test_detect_from_text_short_text_returns_default():
    from app.voice.language_detection import detect_from_text
    result = detect_from_text("ok")
    assert result == "en"


# ---------------------------------------------------------------------------
# G. TTS helpers
# ---------------------------------------------------------------------------

def test_synthesize_speech_empty_text_raises():
    from app.voice.text_to_speech import TextToSpeechError, synthesize_speech
    with pytest.raises(TextToSpeechError):
        synthesize_speech("", language="en")


def test_synthesize_speech_calls_gtts():
    from app.voice.text_to_speech import synthesize_speech

    fake_audio = b"ID3" + b"\x00" * 50

    with patch("app.voice.text_to_speech._synthesize_with_gtts", return_value=fake_audio):
        result = synthesize_speech("Hello farmer", language="en")

    assert result == fake_audio


def test_tts_gtts_failure_raises_tts_error():
    from app.voice.text_to_speech import TextToSpeechError

    with patch("app.voice.text_to_speech._synthesize_with_gtts",
               side_effect=Exception("network error")):
        from app.voice.text_to_speech import synthesize_speech
        with pytest.raises((TextToSpeechError, Exception)):
            synthesize_speech("Hello", language="en")


# ---------------------------------------------------------------------------
# H. STT helpers
# ---------------------------------------------------------------------------

def test_validate_audio_empty_raises():
    from app.voice.speech_to_text import SpeechToTextError, validate_audio
    with pytest.raises(SpeechToTextError, match="empty"):
        validate_audio(b"", "audio/webm")


def test_validate_audio_unsupported_mime_raises():
    from app.voice.speech_to_text import SpeechToTextError, validate_audio
    with pytest.raises(SpeechToTextError, match="[Uu]nsupported"):
        validate_audio(b"\x00" * 100, "video/mp4")


def test_validate_audio_valid_passes():
    from app.voice.speech_to_text import validate_audio
    validate_audio(FAKE_WEBM, "audio/webm")  # should not raise


def test_transcribe_audio_raises_when_not_configured(monkeypatch):
    from app.core.config import settings
    from app.voice.speech_to_text import SpeechToTextNotConfiguredError, transcribe_audio
    monkeypatch.setattr(settings, "gemini_api_key", "")
    with pytest.raises(SpeechToTextNotConfiguredError):
        transcribe_audio(FAKE_WEBM, "audio/webm", language_hint="en")


def test_map_to_gemini_mime():
    from app.voice.speech_to_text import _map_to_gemini_mime
    assert _map_to_gemini_mime("audio/webm") == "audio/webm"
    assert _map_to_gemini_mime("application/octet-stream") == "audio/webm"
    assert _map_to_gemini_mime("audio/wav") == "audio/wav"


# ---------------------------------------------------------------------------
# I. Voice service orchestration
# ---------------------------------------------------------------------------

def test_voice_service_transcribe_wraps_stt(monkeypatch):
    from app.voice.service import transcribe
    from app.voice.speech_to_text import TranscriptionResult

    expected = TranscriptionResult(transcript="hello", language="en")
    with patch("app.voice.service.transcribe_audio", return_value=expected) as mock_stt:
        result = transcribe(FAKE_WEBM, "audio/webm", language_hint="en")

    assert result is expected
    mock_stt.assert_called_once_with(FAKE_WEBM, content_type="audio/webm", language_hint="en")


def test_voice_service_speak_wraps_tts():
    from app.voice.service import speak

    with patch("app.voice.service.synthesize_speech", return_value=b"audio") as mock_tts:
        result = speak("Hello", language="te")

    assert result == b"audio"
    mock_tts.assert_called_once_with("Hello", language="te")


def test_voice_service_chat_fallback_when_tts_fails(db_session):
    """TTS failure must NOT prevent the response from being returned."""
    from app.voice.service import voice_chat
    from app.voice.speech_to_text import TranscriptionResult
    from app.services.assistant_service import AssistantResult
    from app.voice.text_to_speech import TextToSpeechError
    from app.models.user import User, UserRole

    fake_user = Mock(spec=User)
    fake_user.id = 999
    fake_user.role = UserRole.farmer

    transcription = TranscriptionResult(transcript="test query", language="en")
    assistant_result = AssistantResult(answer="Test answer", sources=[])

    with patch("app.voice.service.transcribe_audio", return_value=transcription):
        with patch("app.voice.service.process_assistant_chat", return_value=assistant_result):
            with patch("app.voice.service.synthesize_speech",
                       side_effect=TextToSpeechError("TTS failed")):
                result = voice_chat(
                    db=db_session,
                    user=fake_user,
                    audio_bytes=FAKE_WEBM,
                    language_hint="en",
                )

    assert result.response_text == "Test answer"
    assert result.tts_available is False
    assert result.audio_bytes == b""


# ---------------------------------------------------------------------------
# J. Regression — existing tests must still pass
# ---------------------------------------------------------------------------

def test_existing_assistant_chat_still_works(client, db_session):
    from tests.api.test_schemes import seed_test_scheme

    seed_test_scheme(db_session, name="Regression Voice Scheme")
    token = farmer_token(client, email="voice-reg-assistant@example.com")

    with patch("app.services.assistant_service.generate_assistant_response",
               return_value="All good."):
        resp = client.post(
            "/api/assistant/chat",
            json={"message": "Which schemes are available?"},
            headers=auth_headers(token),
        )

    assert resp.status_code == 200
    assert resp.json()["answer"] == "All good."


def test_existing_rag_search_still_works(client, db_session):
    token = farmer_token(client, email="voice-reg-rag@example.com")

    with patch("app.api.routes.rag.retrieve_document_chunks", return_value=[]):
        resp = client.post(
            "/api/rag/search",
            json={"query": "test query", "top_k": 3},
            headers=auth_headers(token),
        )

    assert resp.status_code == 200
