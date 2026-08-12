from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.scheme_eligibility import SchemeEligibilityCriterion


class GovernmentScheme(Base):
    __tablename__ = "government_schemes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    short_description: Mapped[str] = mapped_column(String(500), nullable=False)
    detailed_description: Mapped[str] = mapped_column(Text, nullable=False)
    department: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    scheme_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    benefits: Mapped[str] = mapped_column(Text, nullable=False)
    application_process: Mapped[str] = mapped_column(Text, nullable=False)
    official_website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # ------------------------------------------------------------------
    # Source / provenance fields (added in migration 0008)
    # All nullable — existing sample rows are unaffected.
    # ------------------------------------------------------------------

    # Stable identifier from the upstream source (e.g. myScheme schemeId)
    external_id: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)

    # Source name — "myscheme", "data_gov_in", "manual", "fixture"
    source: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    # Direct URL to the source scheme page
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # When this record was last confirmed against the upstream source
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Parent ministry (separate from implementing department)
    ministry: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Comma-separated list of beneficiary types (e.g. "farmer,women,SC/ST")
    beneficiary_type: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # "central", "state", "centrally_sponsored", "ut"
    coverage_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # "national", "state", "district", "block"
    geo_scope: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Comma-separated search tags
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Free-text eligibility information that cannot safely be structured
    eligibility_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Free-text list of required documents
    documents_required: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ------------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    eligibility_criteria: Mapped[list["SchemeEligibilityCriterion"]] = relationship(
        back_populates="scheme",
        cascade="all, delete-orphan",
    )
