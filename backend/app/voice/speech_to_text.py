"""
Speech-to-Text service for JanSahay.

Provider: Google Gemini (reuses the existing GEMINI_API_KEY).
The Gemini API supports audio files natively through its multimodal interface.

Supports: English (en), Hindi (hi), Telugu (te).

Security:
- Audio is validated before transcription.
- Temporary files are cleaned up after use.
- Raw audio bytes are never logged.
- Credentials come from settings, never from the request.
"""
from __future__ import annotations

import io
import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

# Allowed MIME types from browsers (MediaRecorder typically produces webm/ogg/mp4)
ALLOWED_AUDIO_MIME_TYPES = frozenset({
    "audio/webm",
    "audio/webm;codecs=opus",
    "audio/ogg",
    "audio/ogg;codecs=opus",
    "audio/mp4",
    "audio/mpeg",
    "audio/wav",
    "audio/x-wav",
    "audio/flac",
    "audio/3gpp",
    "audio/aac",
    "application/octet-stream",  # some browsers send this for webm
})

# Gemini audio MIME for upload — webm and ogg are both accepted
_GEMINI_AUDIO_MIME = "audio/webm"

# Language hint strings for Gemini prompt
_LANGUAGE_PROMPTS: dict[str, str] = {
    "en": "Transcribe the following audio in English.",
    "hi": "Transcribe the following audio in Hindi (Devanagari script).",
    "te": "Transcribe the following audio in Telugu script.",
}
_DEFAULT_PROMPT = "Transcribe the following audio accurately."


class SpeechToTextError(Exception):
    """Raised when STT fails in a recoverable way (bad audio, provider error)."""


class SpeechToTextNotConfiguredError(SpeechToTextError):
    """Raised when the STT provider is not configured."""


@dataclass
class TranscriptionResult:
    transcript: str
    language: str          # resolved language code (en/hi/te)
    stt_detected_language: str | None = None
    confidence: float | None = None


def validate_audio(audio_bytes: bytes, content_type: str) -> None:
    """
    Validate audio bytes before sending to the STT provider.
    Raises SpeechToTextError on validation failure.
    """
    if not audio_bytes:
        raise SpeechToTextError("Audio is empty.")

    if len(audio_bytes) > settings.max_audio_size_bytes:
        raise SpeechToTextError(
            f"Audio exceeds the maximum allowed size of {settings.max_audio_size_mb} MB."
        )

    # Normalize content_type (strip codec parameters for the check)
    base_mime = content_type.split(";")[0].strip().lower()
    if base_mime not in {m.split(";")[0].strip().lower() for m in ALLOWED_AUDIO_MIME_TYPES}:
        raise SpeechToTextError(
            f"Unsupported audio format '{content_type}'. "
            f"Supported: webm, ogg, mp4, wav, flac, aac, mpeg."
        )


def transcribe_audio(
    audio_bytes: bytes,
    content_type: str = "audio/webm",
    language_hint: str | None = None,
) -> TranscriptionResult:
    """
    Transcribe audio using the configured STT provider.

    Parameters
    ----------
    audio_bytes   : Raw audio bytes from the browser.
    content_type  : MIME type of the audio.
    language_hint : Optional language code (en/hi/te) — improves accuracy.

    Returns
    -------
    TranscriptionResult with transcript and detected language.
    """
    validate_audio(audio_bytes, content_type)

    provider = settings.stt_provider.lower()
    if provider == "gemini":
        return _transcribe_with_gemini(audio_bytes, content_type, language_hint)

    raise SpeechToTextNotConfiguredError(
        f"Unknown STT provider '{provider}'. Set STT_PROVIDER=gemini."
    )


def _transcribe_with_gemini(
    audio_bytes: bytes,
    content_type: str,
    language_hint: str | None,
) -> TranscriptionResult:
    """
    Transcribe audio using the Gemini multimodal API.
    Uses the existing GEMINI_API_KEY — no new credentials required.
    """
    if not settings.gemini_api_key or not settings.gemini_api_key.strip():
        raise SpeechToTextNotConfiguredError(
            "Gemini API key is not configured. Set GEMINI_API_KEY to enable voice transcription."
        )

    from google import genai
    from google.genai import errors as genai_errors

    # Determine language prompt
    from app.voice.language_detection import normalize_language_code
    lang = normalize_language_code(language_hint) if language_hint else "en"
    prompt = _LANGUAGE_PROMPTS.get(lang, _DEFAULT_PROMPT)

    # Normalize MIME type — Gemini requires a clean type
    base_mime = content_type.split(";")[0].strip().lower()
    # Map browser MIME types to types Gemini accepts
    gemini_mime = _map_to_gemini_mime(base_mime)

    tmp_path: Path | None = None
    try:
        # Write to a temporary file (Gemini SDK requires file path or bytes)
        with tempfile.NamedTemporaryFile(
            suffix=_mime_to_extension(gemini_mime),
            delete=False,
            dir=None,
        ) as tmp:
            tmp.write(audio_bytes)
            tmp_path = Path(tmp.name)

        client = genai.Client(api_key=settings.gemini_api_key)

        # Upload the audio file to Gemini Files API
        with open(tmp_path, "rb") as audio_file:
            uploaded = client.files.upload(
                file=audio_file,
                config={"mime_type": gemini_mime},
            )

        # Generate transcription
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=[uploaded, prompt],
            config={"temperature": 0},
        )

        transcript = _extract_text(response)
        if not transcript:
            raise SpeechToTextError("Transcription returned an empty result.")

        # Clean up the uploaded file from Gemini
        try:
            client.files.delete(name=uploaded.name)
        except Exception:
            pass  # non-fatal — Gemini auto-expires files

        return TranscriptionResult(
            transcript=transcript.strip(),
            language=lang,
            stt_detected_language=None,  # Gemini doesn't return detected language separately
        )

    except SpeechToTextError:
        raise
    except genai_errors.APIError as exc:
        logger.warning("Gemini STT API error")
        raise SpeechToTextError("Speech-to-text service is temporarily unavailable.") from exc
    except Exception as exc:
        logger.warning("Unexpected STT error: %s", type(exc).__name__)
        raise SpeechToTextError("Speech-to-text failed. Please try again.") from exc
    finally:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass


def _map_to_gemini_mime(base_mime: str) -> str:
    """Map browser audio MIME types to Gemini-accepted types."""
    mapping = {
        "audio/webm": "audio/webm",
        "audio/ogg": "audio/ogg",
        "audio/mp4": "audio/mp4",
        "audio/mpeg": "audio/mpeg",
        "audio/wav": "audio/wav",
        "audio/x-wav": "audio/wav",
        "audio/flac": "audio/flac",
        "audio/3gpp": "audio/3gpp",
        "audio/aac": "audio/aac",
        "application/octet-stream": "audio/webm",  # assume webm from browser
    }
    return mapping.get(base_mime, "audio/webm")


def _mime_to_extension(mime: str) -> str:
    mapping = {
        "audio/webm": ".webm",
        "audio/ogg": ".ogg",
        "audio/mp4": ".mp4",
        "audio/mpeg": ".mp3",
        "audio/wav": ".wav",
        "audio/flac": ".flac",
        "audio/3gpp": ".3gpp",
        "audio/aac": ".aac",
    }
    return mapping.get(mime, ".webm")


def _extract_text(response: object) -> str:
    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()
    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            part_text = getattr(part, "text", None)
            if isinstance(part_text, str) and part_text.strip():
                return part_text.strip()
    return ""
