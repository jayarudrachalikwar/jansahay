from __future__ import annotations

import logging

from google import genai
from google.genai import errors as genai_errors

from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiNotConfiguredError(Exception):
    pass


class GeminiAPIError(Exception):
    pass


def is_gemini_configured() -> bool:
    return bool(settings.gemini_api_key and settings.gemini_api_key.strip())


def generate_assistant_response(
    *,
    system_instruction: str,
    user_message: str,
    history: list[dict[str, str]] | None = None,
) -> str:
    if not is_gemini_configured():
        raise GeminiNotConfiguredError("AI assistant is not configured.")

    client = genai.Client(api_key=settings.gemini_api_key)

    contents: list[dict] = []
    for item in history or []:
        role = "user" if item["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": item["content"]}]})

    contents.append({"role": "user", "parts": [{"text": user_message}]})

    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=contents,
            config={
                "system_instruction": system_instruction,
                "temperature": 0.4,
            },
        )
    except genai_errors.APIError as exc:
        logger.warning("Gemini API request failed")
        raise GeminiAPIError("AI assistant is temporarily unavailable. Please try again.") from exc
    except Exception as exc:
        logger.warning("Unexpected Gemini integration error")
        raise GeminiAPIError("AI assistant is temporarily unavailable. Please try again.") from exc

    answer = _extract_response_text(response)
    if not answer:
        raise GeminiAPIError("AI assistant returned an empty response. Please try again.")

    return answer


def _extract_response_text(response: object) -> str:
    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()

    candidates = getattr(response, "candidates", None)
    if not candidates:
        return ""

    for candidate in candidates:
        content = getattr(candidate, "content", None)
        if content is None:
            continue
        parts = getattr(content, "parts", None) or []
        for part in parts:
            part_text = getattr(part, "text", None)
            if isinstance(part_text, str) and part_text.strip():
                return part_text.strip()

    return ""
