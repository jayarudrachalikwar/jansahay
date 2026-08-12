from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.scheme import GovernmentScheme


class SavedScheme(Base):
    __tablename__ = "saved_schemes"

    __table_args__ = (
        UniqueConstraint("user_id", "scheme_id", name="uq_saved_schemes_user_scheme"),
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
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    scheme: Mapped["GovernmentScheme"] = relationship(
        "GovernmentScheme",
        lazy="select",
    )
