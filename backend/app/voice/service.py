"""
Voice orchestration service.

Coordinates:
  audio → STT → language detection → existing assistant pipeline → TTS → audio

IMPORTANT:
  This service does NOT implement a second chatbot.
  It calls the existing process_assistant_chat() for all AI reasoning.
  Voice is purely an input/output interface for the existing assistant.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.user import User
from app.services.assistant_service import process_assistant_chat
from app.services.gemini_service import GeminiAPIError, GeminiNotConfiguredError
from app.voice.language_detection import resolve_language
from app.voice.speech_to_text import SpeechToTextError, TranscriptionResult, transcribe_audio
from app.voice.text_to_speech import TextToSpeechError, synthesize_speech

logger = logging.getLogger(__name__)


class VoiceServiceError(Exception):
    pass


@dataclass
class VoiceChatResult:
    transcript: str
    language: str
    response_text: str
    audio_bytes: bytes
    sources: list[str] = field(default_factory=list)
    eligibility_checked: bool = False
    rag_sources: list[dict] = field(default_factory=list)
    tts_available: bool = True


def transcribe(
    audio_bytes: bytes,
    content_type: str = "audio/webm",
    language_hint: str | None = None,
) -> TranscriptionResult:
    """
    Transcribe audio bytes to text.
    Thin wrapper around speech_to_text.transcribe_audio.
    """
    return transcribe_audio(audio_bytes, content_type=content_type, language_hint=language_hint)


def speak(text: str, language: str = "en") -> bytes:
    """
    Convert text to speech audio bytes (MP3).
    Thin wrapper around text_to_speech.synthesize_speech.
    """
    return synthesize_speech(text, language=language)


def voice_chat(
    db: Session,
    user: User,
    audio_bytes: bytes,
    content_type: str = "audio/webm",
    language_hint: str | None = None,
    history: list[dict[str, str]] | None = None,
) -> VoiceChatResult:
    """
    Full voice pipeline:
      audio → STT → language detection → existing assistant → TTS → audio

    Uses process_assistant_chat() — the single source of truth for AI reasoning.
    """
    # 1. Transcribe audio
    try:
        transcription = transcribe_audio(
            audio_bytes,
            content_type=content_type,
            language_hint=language_hint,
        )
        logger.info("[VOICE] transcription=%r", transcription.transcript[:80] if transcription.transcript else "")
    except SpeechToTextError as exc:
        raise VoiceServiceError(str(exc)) from exc

    # 2. Resolve language
    language = resolve_language(
        user_preference=language_hint,
        stt_detected=transcription.stt_detected_language,
        transcript=transcription.transcript,
    )

    # 3. Build language-aware system instruction addition
    language_instruction = _get_language_instruction(language)

    # 4. Process through existing assistant pipeline — no duplication
    try:
        result = process_assistant_chat(
            db=db,
            user=user,
            message=transcription.transcript,
            history=history,
            language_instruction=language_instruction,
        )
        logger.info("[VOICE] assistant response generated — answer_len=%d", len(result.answer))
    except GeminiNotConfiguredError as exc:
        raise VoiceServiceError("AI assistant is not configured.") from exc
    except GeminiAPIError as exc:
        raise VoiceServiceError(str(exc)) from exc

    # 5. TTS — non-blocking: if TTS fails, return text-only response
    audio_bytes_out = b""
    tts_available = True
    try:
        audio_bytes_out = synthesize_speech(result.answer, language=language)
    except (TextToSpeechError, Exception) as exc:
        logger.warning("TTS failed — returning text-only response: %s", exc)
        tts_available = False

    return VoiceChatResult(
        transcript=transcription.transcript,
        language=language,
        response_text=result.answer,
        audio_bytes=audio_bytes_out,
        sources=result.sources,
        eligibility_checked=result.eligibility_checked,
        rag_sources=result.rag_sources,
        tts_available=tts_available,
    )


def _get_language_instruction(language: str) -> str:
    instructions = {
        "en": "Please respond in English.",
        "hi": "Please respond in Hindi (हिन्दी में उत्तर दें).",
        "te": "Please respond in Telugu (తెలుగులో సమాధానం ఇవ్వండి).",
    }
    return instructions.get(language, "Please respond in English.")
