"""
Source client abstraction for the scheme importer.

Every upstream source (myScheme via API Setu, data.gov.in, JSON fixture)
implements the SchemeSourceClient protocol.  The importer pipeline only
depends on this interface, not on any specific client.

VERIFIED EXTERNAL API STATUS (as of August 2026):
--------------------------------------------------
myScheme (myscheme.gov.in) via API Setu:
  - Listed under "Service APIs" on API Setu marketplace.
  - Access requires: consumer registration on API Setu, org PAN,
    GST certificate, Certificate of Incorporation, authority letter,
    domain-registered email, and publisher approval.
  - SOP: https://cdn.apisetu.gov.in/portal/assets/SOP-APISETU.pdf
  - devauth.myscheme.gov.in confirms login/signup is gated.
  - NO public, unauthenticated, open API exists.
  - Status: BLOCKED pending registration/approval.

data.gov.in (OGD Platform India):
  - Has a public API (https://www.data.gov.in/apis) requiring per-user
    API key registration.
  - Does not provide a dedicated nationwide welfare-scheme endpoint
    mapping to the JanSahay schema.
  - Could be explored for specific ministry datasets in a future phase.
  - Status: AVAILABLE after API key registration, but no suitable
    bulk scheme dataset confirmed.

Current usable source:
  FixtureSchemeClient — reads from a JSON file for development,
  testing, and dry-run validation.  Carries no production data.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterator

from app.importers.models import RawSchemeRecord

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Protocol / abstract base
# ---------------------------------------------------------------------------

class SchemeSourceError(Exception):
    """Raised when a source client cannot fetch data."""


class SchemeSourceClient:
    """
    Abstract base class for scheme source clients.
    Subclass and override `fetch` to add a new source.
    """

    source_name: str = "base"

    def fetch(self, **kwargs: object) -> Iterator[RawSchemeRecord]:
        """
        Yield RawSchemeRecord objects one at a time.

        Implementations must:
          - Yield complete, unparsed records from the upstream source.
          - Never perform normalisation here.
          - Raise SchemeSourceError on unrecoverable fetch failures.
          - Log recoverable per-record errors and continue.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Fixture client — reads from a local JSON file
# ---------------------------------------------------------------------------

class FixtureSchemeClient(SchemeSourceClient):
    """
    Reads scheme records from a local JSON fixture file.

    Intended for:
      - automated tests (uses in-memory data, no file required)
      - dry-run validation during development
      - demonstrating the full pipeline without external API access

    Expected JSON format:
      [
        {
          "schemeId":        "fixture-001",
          "schemeName":      "...",
          "schemeShortTitle": "...",
          "schemeDescription": "...",
          "openDate":        "...",
          "closeDate":       null,
          "state":           "Telangana",
          "ministry":        "Ministry of Agriculture",
          "department":      "Agriculture Department",
          "schemeType":      "Financial Assistance",
          "beneficiaryType": ["farmer", "small farmer"],
          "eligibilityCriteria": "...",
          "benefits":        "...",
          "applicationProcess": "...",
          "documents":       ["Aadhaar Card", "Land Records"],
          "tags":            ["agriculture", "income support"],
          "schemeUrl":       "https://..."
        },
        ...
      ]
    """

    source_name: str = "fixture"

    def __init__(self, fixture_path: Path | str | None = None) -> None:
        self._fixture_path = Path(fixture_path) if fixture_path else None
        self._inline_records: list[dict] | None = None

    @classmethod
    def from_records(cls, records: list[dict]) -> "FixtureSchemeClient":
        """Create a fixture client from in-memory records (for tests)."""
        client = cls()
        client._inline_records = records
        return client

    def fetch(self, **kwargs: object) -> Iterator[RawSchemeRecord]:
        """Yield RawSchemeRecord objects from fixture data."""
        records = self._load_records()
        logger.info("[IMPORTER] FixtureSchemeClient: loading %d record(s)", len(records))
        for item in records:
            raw_id = str(item.get("schemeId", ""))
            if not raw_id:
                logger.warning("[IMPORTER] Fixture record missing schemeId — skipping")
                continue
            yield RawSchemeRecord(
                source=self.source_name,
                external_id=raw_id,
                raw_data=item,
            )

    def _load_records(self) -> list[dict]:
        if self._inline_records is not None:
            return self._inline_records
        if self._fixture_path is None:
            raise SchemeSourceError("FixtureSchemeClient: no fixture path or inline records set.")
        if not self._fixture_path.exists():
            raise SchemeSourceError(
                f"FixtureSchemeClient: fixture file not found: {self._fixture_path}"
            )
        try:
            with open(self._fixture_path, encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, list):
                raise SchemeSourceError(
                    f"FixtureSchemeClient: expected a JSON array, got {type(data).__name__}"
                )
            return data
        except json.JSONDecodeError as exc:
            raise SchemeSourceError(
                f"FixtureSchemeClient: invalid JSON in {self._fixture_path}: {exc}"
            ) from exc


# ---------------------------------------------------------------------------
# myScheme client stub (blocked pending API Setu registration)
# ---------------------------------------------------------------------------

class MySchemeClient(SchemeSourceClient):
    """
    Client for the myScheme API via API Setu.

    STATUS: BLOCKED — requires formal registration and approval.
    See module docstring and SOP at:
    https://cdn.apisetu.gov.in/portal/assets/SOP-APISETU.pdf

    This is a stub that raises SchemeSourceError until credentials
    are obtained and the implementation is completed.

    Environment variables (once registered):
      MYSCHEME_API_KEY      — API key issued by API Setu after approval
      MYSCHEME_BASE_URL     — API Setu gateway URL for myScheme
    """

    source_name: str = "myscheme"

    def fetch(self, **kwargs: object) -> Iterator[RawSchemeRecord]:
        raise SchemeSourceError(
            "myScheme API is not yet accessible. "
            "Registration and approval via API Setu is required. "
            "See: https://cdn.apisetu.gov.in/portal/assets/SOP-APISETU.pdf\n"
            "Steps:\n"
            "  1. Sign up at https://partners.apisetu.gov.in/signup\n"
            "  2. Provide: org PAN, GST certificate, Certificate of Incorporation,\n"
            "     Authority Letter, and a valid use-case description.\n"
            "  3. Subscribe to the myScheme Service API and await publisher approval.\n"
            "  4. Once approved, set MYSCHEME_API_KEY and MYSCHEME_BASE_URL in .env.\n"
            "  5. Implement this client with the approved API contract."
        )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_CLIENTS: dict[str, type[SchemeSourceClient]] = {
    "fixture": FixtureSchemeClient,
    "myscheme": MySchemeClient,
}


def get_client(source: str) -> SchemeSourceClient:
    """Return a client instance for the given source name."""
    cls = _CLIENTS.get(source.lower())
    if cls is None:
        available = ", ".join(sorted(_CLIENTS.keys()))
        raise ValueError(
            f"Unknown source '{source}'. Available: {available}"
        )
    return cls()
