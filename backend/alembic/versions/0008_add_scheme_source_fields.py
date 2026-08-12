"""Add source/provenance fields to government_schemes table.

Backward-compatible: all new columns are nullable or have server defaults.
Existing rows get NULL for new columns — the seed sample schemes continue to work.
The unique constraint on (source, external_id) only applies where both are non-NULL,
handled at the application layer (partial unique constraint via index).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0008_scheme_source"
down_revision: Union[str, None] = "0007_farmer_scheme_apps"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------------------------------------------------------------------------
    # Provenance / source fields
    # ---------------------------------------------------------------------------
    op.add_column(
        "government_schemes",
        sa.Column("external_id", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "government_schemes",
        sa.Column("source", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "government_schemes",
        sa.Column("source_url", sa.String(length=1000), nullable=True),
    )
    op.add_column(
        "government_schemes",
        sa.Column(
            "last_verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # ---------------------------------------------------------------------------
    # Scheme classification fields (all nullable for backward compat)
    # ---------------------------------------------------------------------------
    op.add_column(
        "government_schemes",
        sa.Column("ministry", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "government_schemes",
        sa.Column("beneficiary_type", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "government_schemes",
        sa.Column("coverage_type", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "government_schemes",
        sa.Column("geo_scope", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "government_schemes",
        sa.Column("tags", sa.Text(), nullable=True),
    )

    # ---------------------------------------------------------------------------
    # Unstructured eligibility text (preserved when structured parsing is unsafe)
    # ---------------------------------------------------------------------------
    op.add_column(
        "government_schemes",
        sa.Column("eligibility_notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "government_schemes",
        sa.Column("documents_required", sa.Text(), nullable=True),
    )

    # ---------------------------------------------------------------------------
    # Indexes
    # ---------------------------------------------------------------------------
    # Index for looking up by source + external_id (deduplication)
    op.create_index(
        "ix_government_schemes_source",
        "government_schemes",
        ["source"],
        unique=False,
    )
    op.create_index(
        "ix_government_schemes_external_id",
        "government_schemes",
        ["external_id"],
        unique=False,
    )
    # Composite index for fast dedup lookups
    op.create_index(
        "ix_government_schemes_source_external_id",
        "government_schemes",
        ["source", "external_id"],
        unique=False,
    )
    # Partial unique index: unique per (source, external_id) only when both non-NULL
    # This is a raw SQL expression — Alembic supports it via postgresql_where
    op.execute(
        """
        CREATE UNIQUE INDEX uq_government_schemes_source_external_id
        ON government_schemes (source, external_id)
        WHERE source IS NOT NULL AND external_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_government_schemes_source_external_id")
    op.drop_index("ix_government_schemes_source_external_id", table_name="government_schemes")
    op.drop_index("ix_government_schemes_external_id", table_name="government_schemes")
    op.drop_index("ix_government_schemes_source", table_name="government_schemes")
    op.drop_column("government_schemes", "documents_required")
    op.drop_column("government_schemes", "eligibility_notes")
    op.drop_column("government_schemes", "tags")
    op.drop_column("government_schemes", "geo_scope")
    op.drop_column("government_schemes", "coverage_type")
    op.drop_column("government_schemes", "beneficiary_type")
    op.drop_column("government_schemes", "ministry")
    op.drop_column("government_schemes", "last_verified_at")
    op.drop_column("government_schemes", "source_url")
    op.drop_column("government_schemes", "source")
    op.drop_column("government_schemes", "external_id")
