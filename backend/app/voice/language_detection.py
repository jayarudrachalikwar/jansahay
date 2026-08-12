"""
Language detection for JanSahay voice pipeline.

Supports: en (English), hi (Hindi), te (Telugu).

Priority order:
  1. Explicit user-selected language (always wins).
  2. STT provider detected language (trusted for short utterances).
  3. langdetect heuristic on transcript text.
  4. Fallback: English.

Never claim high confidence when detection is uncertain.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = {"en", "hi", "te"}
DEFAULT_LANGUAGE = "en"

# langdetect language codes that map to our supported set
_LANGDETECT_MAP: dict[str, str] = {
    "en": "en",
    "hi": "hi",
    "te": "te",
}


def normalize_language_code(code: str | None) -> str:
    """
    Normalize a language code to one of en / hi / te.
    Returns DEFAULT_LANGUAGE for unrecognised or missing codes.
    """
    if not code:
        return DEFAULT_LANGUAGE
    normalized = code.strip().lower().split("-")[0]
    if normalized in SUPPORTED_LANGUAGES:
        return normalized
    return DEFAULT_LANGUAGE


def detect_from_text(text: str) -> str:
    """
    Attempt to detect language from transcript text using langdetect.
    Returns a supported language code or DEFAULT_LANGUAGE on failure.
    """
    if not text or len(text.strip()) < 5:
        return DEFAULT_LANGUAGE

    try:
        from langdetect import detect as _detect, DetectorFactory
        # Deterministic results
        DetectorFactory.seed = 0
        detected = _detect(text)
        mapped = _LANGDETECT_MAP.get(detected, DEFAULT_LANGUAGE)
        logger.debug("langdetect: %s → mapped to %s", detected, mapped)
        return mapped
    except Exception as exc:
        logger.debug("langdetect failed: %s — defaulting to %s", exc, DEFAULT_LANGUAGE)
        return DEFAULT_LANGUAGE


def resolve_language(
    user_preference: str | None,
    stt_detected: str | None,
    transcript: str | None,
) -> str:
    """
    Resolve the final language code given multiple signals.

    Parameters
    ----------
    user_preference : Explicit language chosen by the farmer in the UI.
    stt_detected    : Language code returned by the STT provider.
    transcript      : Transcribed text (used for heuristic detection).
    """
    # 1. User explicitly chose a language — always respected
    if user_preference:
        lang = normalize_language_code(user_preference)
        if lang != DEFAULT_LANGUAGE or user_preference.lower().startswith("en"):
            return lang

    # 2. STT provider detected language
    if stt_detected:
        lang = normalize_language_code(stt_detected)
        if lang in SUPPORTED_LANGUAGES:
            return lang

    # 3. Heuristic detection from transcript
    if transcript:
        return detect_from_text(transcript)

    return DEFAULT_LANGUAGE
