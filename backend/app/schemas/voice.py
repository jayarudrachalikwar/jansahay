"""
Pydantic schemas for the voice API.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


SupportedLanguage = Literal["en", "hi", "te"]


class TranscribeResponse(BaseModel):
    transcript: str
    language: str


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    language: SupportedLanguage = "en"


class VoiceChatResponse(BaseModel):
    transcript: str
    language: str
    response_text: str
    audio_base64: str | None = None   # base64-encoded MP3, None if TTS failed
    sources: list[str] = Field(default_factory=list)
    eligibility_checked: bool = False
    rag_sources: list[dict] = Field(default_factory=list)
    tts_available: bool = True


class ProfileExtractResponse(BaseModel):
    raw_transcript: str
    extracted_fields: dict[str, str]
    uncertain_fields: list[str]
