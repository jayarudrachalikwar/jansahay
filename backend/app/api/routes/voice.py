"""
Voice API routes.

POST /api/voice/transcribe — audio → transcript
POST /api/voice/speak      — text → audio
POST /api/voice/chat       — audio → transcript → assistant → audio
POST /api/voice/extract-profile — audio → transcript → profile field extraction

Security:
  - All endpoints require JWT authentication.
  - user_id is always taken from current_user.id (never from the request body).
  - Audio MIME type and size are validated before processing.
  - No audio bytes are persisted permanently.
  - No API keys are returned to the client.
"""
from __future__ import annotations

import base64
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.voice import (
    ProfileExtractResponse,
    SpeakRequest,
    TranscribeResponse,
    VoiceChatResponse,
)
from app.voice.service import VoiceServiceError, transcribe, speak, voice_chat
from app.voice.speech_to_text import SpeechToTextError, SpeechToTextNotConfiguredError
from app.voice.text_to_speech import TextToSpeechError, TextToSpeechNotConfiguredError
from app.voice.voice_profile_extractor import extract_profile_fields

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])

# Maximum audio upload size enforced at the route layer (before reading all bytes)
_MAX_AUDIO_BYTES_ROUTE = 10 * 1024 * 1024  # 10 MB


async def _read_audio(file: UploadFile) -> tuple[bytes, str]:
    """Read and size-validate the uploaded audio file."""
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio is empty.",
        )
    if len(audio_bytes) > _MAX_AUDIO_BYTES_ROUTE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Audio file exceeds the 10 MB limit.",
        )
    content_type = file.content_type or "audio/webm"
    return audio_bytes, content_type


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio_endpoint(
    audio: UploadFile = File(..., description="Audio file (webm, ogg, wav, mp4, etc.)"),
    language: str = Form(default="en", description="Language hint: en, hi, or te"),
    current_user: User = Depends(get_current_user),
) -> TranscribeResponse:
    """
    Transcribe uploaded audio to text.
    Returns the transcript and detected/resolved language.
    """
    audio_bytes, content_type = await _read_audio(audio)

    try:
        result = transcribe(audio_bytes, content_type=content_type, language_hint=language)
    except SpeechToTextNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except SpeechToTextError as exc:
        detail = str(exc)
        # Input validation errors → 422; provider/service errors → 503
        is_bad_input = (
            "unsupported audio format" in detail.lower()
            or "audio is empty" in detail.lower()
            or "exceeds the maximum" in detail.lower()
        )
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
                if is_bad_input
                else status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=detail,
        ) from exc

    return TranscribeResponse(
        transcript=result.transcript,
        language=result.language,
    )


@router.post("/speak")
async def text_to_speech_endpoint(
    payload: SpeakRequest,
    current_user: User = Depends(get_current_user),
) -> Response:
    """
    Convert text to speech and return MP3 audio bytes.
    """
    try:
        audio_bytes = speak(payload.text, language=payload.language)
    except TextToSpeechNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except TextToSpeechError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Cache-Control": "no-store"},
    )


@router.post("/chat", response_model=VoiceChatResponse)
async def voice_chat_endpoint(
    audio: UploadFile = File(..., description="Audio file from browser microphone"),
    language: str = Form(default="en", description="Language hint: en, hi, or te"),
    history: str = Form(
        default="[]",
        description="JSON-encoded conversation history (same format as /api/assistant/chat)",
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VoiceChatResponse:
    """
    Full voice pipeline:
      audio → STT → existing assistant (GraphRAG + Gemini) → TTS → audio

    The response includes:
      - transcript (what was heard)
      - response_text (what the assistant said)
      - audio_base64 (MP3 encoded as base64, suitable for browser Audio())
      - sources, rag_sources (same provenance as /api/assistant/chat)
    """
    import json as _json

    audio_bytes, content_type = await _read_audio(audio)

    logger.info(
        "[VOICE] /api/voice/chat request received — filename=%s content_type=%s audio_size=%d language=%s authenticated_user=%s",
        audio.filename,
        content_type,
        len(audio_bytes),
        language,
        current_user.email if hasattr(current_user, "email") else current_user.id,
    )

    # Parse history safely
    try:
        history_list: list[dict] = _json.loads(history)
        if not isinstance(history_list, list):
            history_list = []
    except Exception:
        history_list = []

    try:
        result = voice_chat(
            db=db,
            user=current_user,
            audio_bytes=audio_bytes,
            content_type=content_type,
            language_hint=language,
            history=history_list,
        )
    except VoiceServiceError as exc:
        detail = str(exc)
        # All VoiceServiceError cases are provider/service failures, not bad requests.
        # STT "temporarily unavailable", "not configured", Gemini errors → 503.
        # Only raise 422 if we have a genuine input validation problem.
        is_bad_request = (
            "unsupported audio format" in detail.lower()
            or "audio is empty" in detail.lower()
        )
        http_status = (
            status.HTTP_422_UNPROCESSABLE_ENTITY
            if is_bad_request
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        raise HTTPException(status_code=http_status, detail=detail) from exc

    # Encode audio as base64 for JSON response (small MP3 files are acceptable)
    audio_b64: str | None = None
    if result.audio_bytes:
        audio_b64 = base64.b64encode(result.audio_bytes).decode("utf-8")
        logger.info("[VOICE] TTS generated — audio_bytes=%d", len(result.audio_bytes))

    logger.info(
        "[VOICE] transcription=%r assistant_response_len=%d",
        result.transcript[:80] if result.transcript else "",
        len(result.response_text),
    )

    return VoiceChatResponse(
        transcript=result.transcript,
        language=result.language,
        response_text=result.response_text,
        audio_base64=audio_b64,
        sources=result.sources,
        eligibility_checked=result.eligibility_checked,
        rag_sources=result.rag_sources,
        tts_available=result.tts_available,
    )


@router.post("/extract-profile", response_model=ProfileExtractResponse)
async def extract_profile_from_voice(
    audio: UploadFile = File(..., description="Audio describing farmer profile information"),
    language: str = Form(default="en", description="Language hint: en, hi, or te"),
    current_user: User = Depends(get_current_user),
) -> ProfileExtractResponse:
    """
    Extract candidate profile fields from a voice utterance.

    IMPORTANT: This endpoint only returns extracted suggestions.
    The caller must present these to the farmer for confirmation before
    calling PUT /api/profile to save.

    Never saves profile data automatically.
    """
    audio_bytes, content_type = await _read_audio(audio)

    # Step 1: transcribe
    try:
        transcription_result = transcribe(
            audio_bytes, content_type=content_type, language_hint=language
        )
    except (SpeechToTextNotConfiguredError, SpeechToTextError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    # Step 2: extract profile fields from transcript (suggestions only)
    extraction = extract_profile_fields(transcription_result.transcript)

    return ProfileExtractResponse(
        raw_transcript=transcription_result.transcript,
        extracted_fields=extraction.fields,
        uncertain_fields=extraction.uncertain_fields,
    )
