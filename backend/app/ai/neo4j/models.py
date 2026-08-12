"""
Plain-Python data models for graph entities.

These are not SQLAlchemy models — they are lightweight dataclasses used
to pass structured data between the ingestion layer and the Neo4j repository
without leaking SQLAlchemy session state.

Every field maps directly to an existing PostgreSQL column on the
corresponding model to ensure no fabricated data is ever written to Neo4j.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SchemeNode:
    """Derived from GovernmentScheme (PostgreSQL)."""
    scheme_id: int          # GovernmentScheme.id
    name: str               # GovernmentScheme.name
    department: str         # GovernmentScheme.department
    state: str              # GovernmentScheme.state
    scheme_type: str        # GovernmentScheme.scheme_type
    is_active: bool         # GovernmentScheme.is_active
    # Parsed from eligibility_criteria — only field values that map to
    # real profile fields (state, crop, land_ownership, etc.)
    target_crops: list[str] = field(default_factory=list)
    target_categories: list[str] = field(default_factory=list)


@dataclass
class FarmerNode:
    """Derived from FarmerProfile + User (PostgreSQL)."""
    user_id: int            # FarmerProfile.user_id
    state: str | None       # FarmerProfile.state
    district: str | None    # FarmerProfile.district
    primary_crop: str | None    # FarmerProfile.primary_crop
    secondary_crop: str | None  # FarmerProfile.secondary_crop
    land_ownership: str | None  # FarmerProfile.land_ownership
    farming_type: str | None    # FarmerProfile.farming_type


@dataclass
class DocumentNode:
    """Derived from GovernmentDocument (PostgreSQL)."""
    document_id: str        # GovernmentDocument.document_id  (SHA-256 hash)
    filename: str           # GovernmentDocument.filename     (server-safe name)
    original_filename: str  # GovernmentDocument.original_filename
    # scheme_ids that this document is linked to (derived from admin tagging
    # or heuristic name matching — never hallucinated)
    scheme_ids: list[int] = field(default_factory=list)
