from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, LargeBinary, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class DocumentStatus(str, enum.Enum):
    uploaded = "uploaded"
    processing = "processing"
    indexed = "indexed"
    failed = "failed"
    inactive = "inactive"


class GovernmentDocument(Base):
    __tablename__ = "government_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Server-generated safe filename (UUID-based, never user-supplied)
    filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)

    # Original name supplied by the admin — for display only, never used in filesystem ops
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)

    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # bytes

    # PDF bytes stored in DB for Vercel compatibility (ephemeral filesystem).
    # Nullable so existing records and local Docker usage are unaffected.
    file_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Deterministic SHA-256 id used as Qdrant document_id payload
    document_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status", native_enum=True),
        nullable=False,
        default=DocumentStatus.uploaded,
        index=True,
    )

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

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
    ingested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
