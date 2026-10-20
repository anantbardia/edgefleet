"""Firmware release database model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class FirmwareRelease(Base):
    """A firmware release artifact registered in the system."""

    __tablename__ = "firmware_releases"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    mcu_family: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    target_boards: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    build_id: Mapped[str] = mapped_column(String(100), nullable=True)
    release_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    created_by: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )
    signature_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False, default="")
