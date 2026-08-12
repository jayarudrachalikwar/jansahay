"""Create government_documents table."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0005_create_government_documents"
down_revision: Union[str, None] = "0004_create_schemes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "government_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "uploaded",
                "processing",
                "indexed",
                "failed",
                "inactive",
                name="document_status",
            ),
            nullable=False,
            server_default="uploaded",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
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
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id"),
        sa.UniqueConstraint("filename"),
    )
    op.create_index(
        op.f("ix_government_documents_id"),
        "government_documents",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_government_documents_filename"),
        "government_documents",
        ["filename"],
        unique=True,
    )
    op.create_index(
        op.f("ix_government_documents_document_id"),
        "government_documents",
        ["document_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_government_documents_status"),
        "government_documents",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_government_documents_is_active"),
        "government_documents",
        ["is_active"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_government_documents_is_active"), table_name="government_documents")
    op.drop_index(op.f("ix_government_documents_status"), table_name="government_documents")
    op.drop_index(op.f("ix_government_documents_document_id"), table_name="government_documents")
    op.drop_index(op.f("ix_government_documents_filename"), table_name="government_documents")
    op.drop_index(op.f("ix_government_documents_id"), table_name="government_documents")
    op.drop_table("government_documents")
    op.execute("DROP TYPE IF EXISTS document_status")
