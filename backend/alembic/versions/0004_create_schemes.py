"""Create government_schemes and scheme_eligibility_criteria tables."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0004_create_schemes"
down_revision: Union[str, None] = "0003_create_farmer_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "government_schemes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("short_description", sa.String(length=500), nullable=False),
        sa.Column("detailed_description", sa.Text(), nullable=False),
        sa.Column("department", sa.String(length=255), nullable=False),
        sa.Column("state", sa.String(length=100), nullable=False),
        sa.Column("scheme_type", sa.String(length=100), nullable=False),
        sa.Column("benefits", sa.Text(), nullable=False),
        sa.Column("application_process", sa.Text(), nullable=False),
        sa.Column("official_website", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_government_schemes_id"), "government_schemes", ["id"], unique=False)
    op.create_index(
        op.f("ix_government_schemes_name"), "government_schemes", ["name"], unique=False
    )
    op.create_index(
        op.f("ix_government_schemes_state"), "government_schemes", ["state"], unique=False
    )
    op.create_index(
        op.f("ix_government_schemes_scheme_type"),
        "government_schemes",
        ["scheme_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_government_schemes_is_active"),
        "government_schemes",
        ["is_active"],
        unique=False,
    )

    op.create_table(
        "scheme_eligibility_criteria",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scheme_id", sa.Integer(), nullable=False),
        sa.Column("criterion_type", sa.String(length=100), nullable=False),
        sa.Column("field_name", sa.String(length=100), nullable=False),
        sa.Column("operator", sa.String(length=50), nullable=False),
        sa.Column("expected_value", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["scheme_id"], ["government_schemes.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_scheme_eligibility_criteria_id"),
        "scheme_eligibility_criteria",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scheme_eligibility_criteria_scheme_id"),
        "scheme_eligibility_criteria",
        ["scheme_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_scheme_eligibility_criteria_scheme_id"),
        table_name="scheme_eligibility_criteria",
    )
    op.drop_index(
        op.f("ix_scheme_eligibility_criteria_id"),
        table_name="scheme_eligibility_criteria",
    )
    op.drop_table("scheme_eligibility_criteria")
    op.drop_index(op.f("ix_government_schemes_is_active"), table_name="government_schemes")
    op.drop_index(op.f("ix_government_schemes_scheme_type"), table_name="government_schemes")
    op.drop_index(op.f("ix_government_schemes_state"), table_name="government_schemes")
    op.drop_index(op.f("ix_government_schemes_name"), table_name="government_schemes")
    op.drop_index(op.f("ix_government_schemes_id"), table_name="government_schemes")
    op.drop_table("government_schemes")
