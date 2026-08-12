"""
Data transfer objects used by the importer pipeline.

RawSchemeRecord    — raw data as received from any upstream source
NormalizedScheme   — fully validated record ready for persistence
ImportReport       — summary statistics for a single import run
ImportOutcome      — per-record disposition
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Allowed values
# ---------------------------------------------------------------------------

ALLOWED_SOURCES = frozenset({"myscheme", "data_gov_in", "fixture", "manual"})

COVERAGE_TYPES = frozenset({"central", "state", "centrally_sponsored", "ut", "unknown"})

GEO_SCOPES = frozenset({"national", "state", "district", "block", "unknown"})


# ---------------------------------------------------------------------------
# Raw record — opaque dict wrapper from the upstream source
# ---------------------------------------------------------------------------

@dataclass
class RawSchemeRecord:
    """
    A single raw scheme record exactly as returned by the source.
    The source client is responsible for constructing these; no
    normalisation has been applied yet.
    """
    source: str                          # e.g. "myscheme", "fixture"
    external_id: str                     # source's own stable identifier
    raw_data: dict[str, Any]             # the complete raw payload
    fetched_at: datetime = field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Normalized record — ready for dedup + persistence
# ---------------------------------------------------------------------------

@dataclass
class NormalizedScheme:
    """
    Scheme record after normalization and field-length enforcement.
    Maps directly to GovernmentScheme model columns.
    """
    # --- Required fields ---
    name: str
    short_description: str
    detailed_description: str
    department: str
    state: str
    scheme_type: str
    benefits: str
    application_process: str

    # --- Source metadata ---
    external_id: str
    source: str

    # --- Optional fields ---
    official_website: str | None = None
    source_url: str | None = None
    ministry: str | None = None
    beneficiary_type: str | None = None
    coverage_type: str | None = None
    geo_scope: str | None = None
    tags: str | None = None
    eligibility_notes: str | None = None
    documents_required: str | None = None
    is_active: bool = True

    # Populated by normalizer when raw eligibility text CAN be safely structured
    structured_criteria: list[dict[str, str]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Per-record outcome
# ---------------------------------------------------------------------------

class RecordOutcome(str, Enum):
    NEW = "new"
    UPDATED = "updated"
    UNCHANGED = "unchanged"
    INVALID = "invalid"
    DUPLICATE = "duplicate"


@dataclass
class RecordResult:
    external_id: str
    outcome: RecordOutcome
    name: str | None = None
    reason: str | None = None      # validation failure reason, if any


# ---------------------------------------------------------------------------
# Import report
# ---------------------------------------------------------------------------

@dataclass
class ImportReport:
    source: str
    dry_run: bool
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None

    fetched: int = 0
    valid: int = 0
    invalid: int = 0
    new: int = 0
    updated: int = 0
    unchanged: int = 0
    duplicates: int = 0

    errors: list[str] = field(default_factory=list)
    record_results: list[RecordResult] = field(default_factory=list)

    def finish(self) -> None:
        self.finished_at = datetime.utcnow()

    def to_text(self) -> str:
        duration = ""
        if self.finished_at:
            secs = (self.finished_at - self.started_at).total_seconds()
            duration = f"  Duration:    {secs:.1f}s"

        lines = [
            f"Source:      {self.source}",
            f"Dry run:     {self.dry_run}",
            f"Started:     {self.started_at.isoformat()}",
        ]
        if self.finished_at:
            lines.append(f"Finished:    {self.finished_at.isoformat()}")
        if duration:
            lines.append(duration)
        lines += [
            "",
            f"Fetched:     {self.fetched}",
            f"Valid:       {self.valid}",
            f"Invalid:     {self.invalid}",
            f"New:         {self.new}",
            f"Updated:     {self.updated}",
            f"Unchanged:   {self.unchanged}",
            f"Duplicates:  {self.duplicates}",
        ]
        if self.errors:
            lines += ["", "Errors:"]
            for err in self.errors[:20]:
                lines.append(f"  - {err}")
            if len(self.errors) > 20:
                lines.append(f"  ... and {len(self.errors) - 20} more")
        return "\n".join(lines)
