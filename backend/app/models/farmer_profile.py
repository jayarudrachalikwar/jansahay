from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class FarmerProfile(Base):
    __tablename__ = "farmer_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(50), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    village: Mapped[str | None] = mapped_column(String(150), nullable=True)
    land_size: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    land_unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    land_ownership: Mapped[str | None] = mapped_column(String(50), nullable=True)
    primary_crop: Mapped[str | None] = mapped_column(String(100), nullable=True)
    secondary_crop: Mapped[str | None] = mapped_column(String(100), nullable=True)
    soil_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    irrigation_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    farming_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    annual_income: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
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

    user: Mapped["User"] = relationship(back_populates="farmer_profile")
