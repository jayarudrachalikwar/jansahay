"""
Voice-assisted farmer profile extraction.

Extracts structured profile field candidates from a natural-language transcript
using the Gemini API.  The extracted values are presented to the farmer for
confirmation BEFORE any profile update is made.

Security:
- User identity comes from the authenticated JWT, never from the transcript.
- Extracted values are suggestions only — never auto-saved.
- Gemini is prompted not to invent values not present in the transcript.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Profile fields that can be extracted from voice
EXTRACTABLE_FIELDS: dict[str, str] = {
    "state": "Indian state name (e.g. Telangana, Maharashtra)",
    "district": "District/taluk name",
    "village": "Village name",
    "primary_crop": "Main crop grown (e.g. cotton, rice, wheat)",
    "secondary_crop": "Secondary crop grown",
    "land_size": "Land size as a number",
    "land_unit": "Land unit — acres or hectares",
    "land_ownership": "Ownership type — owned, leased, or shared",
    "farming_type": "Type of farming — organic or conventional",
    "irrigation_type": "Irrigation method — drip, sprinkler, flood, or rainfed",
    "soil_type": "Soil type — black, red, alluvial, loamy, sandy",
    "annual_income": "Annual income as a number in INR",
    "gender": "Gender — Male, Female, or Other",
}


@dataclass
class ExtractedProfileFields:
    """Candidate field values extracted from a voice transcript."""
    fields: dict[str, str] = field(default_factory=dict)
    # fields the model was not confident about
    uncertain_fields: list[str] = field(default_factory=list)
    raw_transcript: str = ""


class ProfileExtractionError(Exception):
    pass


_EXTRACTION_PROMPT_TEMPLATE = """
You are helping extract structured farmer profile information from a spoken transcript.

Transcript: "{transcript}"

Extract the following fields if clearly mentioned in the transcript.
Return a JSON object with only the fields that are clearly present.
Do NOT invent or guess values not explicitly stated.
If a value is ambiguous, omit it.

Fields to extract:
{field_descriptions}

Return format:
{{
  "extracted": {{
    "field_name": "value",
    ...
  }},
  "uncertain": ["field_name_1", ...]
}}

Return ONLY valid JSON with no extra text.
""".strip()


def extract_profile_fields(transcript: str) -> ExtractedProfileFields:
    """
    Use Gemini to extract profile field candidates from a transcript.
    Returns suggestions only — the caller must present these to the farmer
    for confirmation before saving.
    """
    from app.core.config import settings
    from app.services.gemini_service import is_gemini_configured

    if not transcript or not transcript.strip():
        return ExtractedProfileFields(raw_transcript=transcript)

    if not is_gemini_configured():
        logger.debug("Profile extraction skipped — Gemini not configured")
        return ExtractedProfileFields(raw_transcript=transcript)

    field_descriptions = "\n".join(
        f"- {k}: {v}" for k, v in EXTRACTABLE_FIELDS.items()
    )
    prompt = _EXTRACTION_PROMPT_TEMPLATE.format(
        transcript=transcript.strip(),
        field_descriptions=field_descriptions,
    )

    try:
        from google import genai
        from google.genai import errors as genai_errors

        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=[prompt],
            config={"temperature": 0},
        )

        text = getattr(response, "text", "") or ""
        text = text.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(
                line for line in lines
                if not line.startswith("```")
            ).strip()

        data = json.loads(text)
        extracted = data.get("extracted", {})
        uncertain = data.get("uncertain", [])

        # Validate extracted fields — only keep known field names, string values
        clean: dict[str, str] = {}
        for k, v in extracted.items():
            if k in EXTRACTABLE_FIELDS and isinstance(v, (str, int, float)):
                clean[k] = str(v).strip()

        return ExtractedProfileFields(
            fields=clean,
            uncertain_fields=[u for u in uncertain if isinstance(u, str)],
            raw_transcript=transcript,
        )

    except json.JSONDecodeError as exc:
        logger.warning("Profile extraction returned invalid JSON: %s", exc)
        return ExtractedProfileFields(raw_transcript=transcript)
    except Exception as exc:
        logger.warning("Profile extraction failed: %s", type(exc).__name__)
        return ExtractedProfileFields(raw_transcript=transcript)
