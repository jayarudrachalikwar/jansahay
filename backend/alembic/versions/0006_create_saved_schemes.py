"""Create saved_schemes table."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0006_create_saved_schemes"
down_revision: Union[str, None] = "0005_create_government_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "saved_schemes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("scheme_id", sa.Integer(), nullable=False),
        sa.Column(
            "saved_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["scheme_id"], ["government_schemes.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "scheme_id", name="uq_saved_schemes_user_scheme"),
    )
    op.create_index(
        op.f("ix_saved_schemes_id"), "saved_schemes", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_saved_schemes_user_id"), "saved_schemes", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_saved_schemes_scheme_id"), "saved_schemes", ["scheme_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_saved_schemes_scheme_id"), table_name="saved_schemes")
    op.drop_index(op.f("ix_saved_schemes_user_id"), table_name="saved_schemes")
    op.drop_index(op.f("ix_saved_schemes_id"), table_name="saved_schemes")
    op.drop_table("saved_schemes")
