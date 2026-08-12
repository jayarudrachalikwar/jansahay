"""
Text-to-Speech service for JanSahay.

Provider: gTTS (Google Text-to-Speech, no API key required).
Supports English (en), Hindi (hi), Telugu (te).

Audio is returned as bytes (MP3) suitable for browser playback.
No files are persisted permanently.
"""
from __future__ import annotations

import io
import logging

logger = logging.getLogger(__name__)

# gTTS language codes for supported languages
_GTTS_LANG_MAP: dict[str, str] = {
    "en": "en",
    "hi": "hi",
    "te": "te",
}
_DEFAULT_LANG = "en"

# Approximate max text length for TTS (avoids excessively large responses)
_MAX_TTS_TEXT_LENGTH = 2000

AUDIO_CONTENT_TYPE = "audio/mpeg"


class TextToSpeechError(Exception):
    """Raised when TTS fails in a recoverable way."""


class TextToSpeechNotConfiguredError(TextToSpeechError):
    """Raised when the TTS provider is not available."""


def synthesize_speech(
    text: str,
    language: str = "en",
) -> bytes:
    """
    Convert text to speech audio bytes (MP3).

    Parameters
    ----------
    text     : The text to synthesize.
    language : Language code — en / hi / te.

    Returns
    -------
    MP3 audio bytes suitable for browser playback.
    """
    if not text or not text.strip():
        raise TextToSpeechError("Text for speech synthesis cannot be empty.")

    text = text.strip()
    if len(text) > _MAX_TTS_TEXT_LENGTH:
        text = text[:_MAX_TTS_TEXT_LENGTH]
        logger.debug("TTS text truncated to %d characters", _MAX_TTS_TEXT_LENGTH)

    from app.core.config import settings

    provider = settings.tts_provider.lower()
    if provider == "gtts":
        return _synthesize_with_gtts(text, language)

    raise TextToSpeechNotConfiguredError(
        f"Unknown TTS provider '{provider}'. Set TTS_PROVIDER=gtts."
    )


def _synthesize_with_gtts(text: str, language: str) -> bytes:
    """Synthesize speech using gTTS (no API key required)."""
    try:
        from gtts import gTTS
    except ImportError as exc:
        raise TextToSpeechNotConfiguredError(
            "gTTS library is not installed. Add gTTS to requirements.txt."
        ) from exc

    lang_code = _GTTS_LANG_MAP.get(language, _DEFAULT_LANG)

    try:
        tts = gTTS(text=text, lang=lang_code, slow=False)
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        audio_bytes = audio_buffer.read()

        if not audio_bytes:
            raise TextToSpeechError("TTS returned empty audio.")

        logger.debug(
            "TTS synthesized %d chars in language=%s → %d bytes",
            len(text), lang_code, len(audio_bytes),
        )
        return audio_bytes

    except TextToSpeechError:
        raise
    except Exception as exc:
        logger.warning("gTTS synthesis failed: %s", type(exc).__name__)
        raise TextToSpeechError("Text-to-speech is temporarily unavailable. Please try again.") from exc
