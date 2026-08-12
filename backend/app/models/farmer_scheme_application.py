from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.scheme import GovernmentScheme
    from app.models.user import User


class ApplicationStatus(str, enum.Enum):
    not_started = "not_started"
    preparing = "preparing"
    ready_to_apply = "ready_to_apply"
    submitted = "submitted"


class FarmerSchemeApplication(Base):
    __tablename__ = "farmer_scheme_applications"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "scheme_id",
            name="uq_farmer_scheme_applications_user_scheme",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scheme_id: Mapped[int] = mapped_column(
        ForeignKey("government_schemes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status", native_enum=True),
        nullable=False,
        default=ApplicationStatus.preparing,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
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
        "GovernmentScheme",
        lazy="select",
    )
    user: Mapped["User"] = relationship(
        "User",
        lazy="select",
    )
