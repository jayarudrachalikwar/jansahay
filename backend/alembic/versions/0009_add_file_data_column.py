"""Add file_data column to government_documents for Vercel ephemeral filesystem compatibility

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-12

The file_data column stores uploaded PDF bytes directly in PostgreSQL.
This is required on Vercel where the filesystem is ephemeral � a file written
in one serverless function invocation is not available in the next.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = "0009_add_file_data"
down_revision = "0008_scheme_source"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "government_documents",
        sa.Column("file_data", sa.LargeBinary(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("government_documents", "file_data")

