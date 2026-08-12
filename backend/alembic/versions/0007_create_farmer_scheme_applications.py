"""Create farmer_scheme_applications table."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0007_farmer_scheme_apps"
down_revision: Union[str, None] = "0006_create_saved_schemes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "farmer_scheme_applications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("scheme_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "not_started",
                "preparing",
                "ready_to_apply",
                "submitted",
                name="application_status",
            ),
            nullable=False,
            server_default="preparing",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["scheme_id"], ["government_schemes.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "scheme_id",
            name="uq_farmer_scheme_applications_user_scheme",
        ),
    )
    op.create_index(
        op.f("ix_farmer_scheme_applications_id"),
        "farmer_scheme_applications",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_farmer_scheme_applications_user_id"),
        "farmer_scheme_applications",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_farmer_scheme_applications_scheme_id"),
        "farmer_scheme_applications",
        ["scheme_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_farmer_scheme_applications_scheme_id"),
        table_name="farmer_scheme_applications",
    )
    op.drop_index(
        op.f("ix_farmer_scheme_applications_user_id"),
        table_name="farmer_scheme_applications",
    )
    op.drop_index(
        op.f("ix_farmer_scheme_applications_id"),
        table_name="farmer_scheme_applications",
    )
    op.drop_table("farmer_scheme_applications")
    op.execute("DROP TYPE IF EXISTS application_status")
