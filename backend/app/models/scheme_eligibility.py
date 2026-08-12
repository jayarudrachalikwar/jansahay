from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.scheme import GovernmentScheme


class SchemeEligibilityCriterion(Base):
    __tablename__ = "scheme_eligibility_criteria"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    scheme_id: Mapped[int] = mapped_column(
        ForeignKey("government_schemes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    criterion_type: Mapped[str] = mapped_column(String(100), nullable=False)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    operator: Mapped[str] = mapped_column(String(50), nullable=False)
    expected_value: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
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

    scheme: Mapped["GovernmentScheme"] = relationship(
        back_populates="eligibility_criteria",
    )
