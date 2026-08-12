"""Create farmer_profiles table."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0003_create_farmer_profiles"
down_revision: Union[str, None] = "0002_create_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "farmer_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("gender", sa.String(length=50), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("district", sa.String(length=100), nullable=True),
        sa.Column("village", sa.String(length=150), nullable=True),
        sa.Column("land_size", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("land_unit", sa.String(length=30), nullable=True),
        sa.Column("land_ownership", sa.String(length=50), nullable=True),
        sa.Column("primary_crop", sa.String(length=100), nullable=True),
        sa.Column("secondary_crop", sa.String(length=100), nullable=True),
        sa.Column("soil_type", sa.String(length=100), nullable=True),
        sa.Column("irrigation_type", sa.String(length=100), nullable=True),
        sa.Column("farming_type", sa.String(length=100), nullable=True),
        sa.Column("annual_income", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_farmer_profiles_id"), "farmer_profiles", ["id"], unique=False)
    op.create_index(op.f("ix_farmer_profiles_user_id"), "farmer_profiles", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_farmer_profiles_user_id"), table_name="farmer_profiles")
    op.drop_index(op.f("ix_farmer_profiles_id"), table_name="farmer_profiles")
    op.drop_table("farmer_profiles")
