"""
SQLAlchemy ORM models.

Personal registration config (name, phone, batch) is stored only in environment
variables — never in this database.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base


class RegistrationStatus(str, enum.Enum):
    WAITING = "WAITING"
    ANNOUNCEMENT_DETECTED = "ANNOUNCEMENT_DETECTED"
    FORM_VALIDATING = "FORM_VALIDATING"
    FORM_OPENED = "FORM_OPENED"
    FORM_FILLED = "FORM_FILLED"
    SUBMISSION_PENDING = "SUBMISSION_PENDING"
    SUBMITTED = "SUBMITTED"
    FAILED = "FAILED"
    SEATS_FULL = "SEATS_FULL"
    MANUAL_INTERVENTION_REQUIRED = "MANUAL_INTERVENTION_REQUIRED"


class RegistrationAttempt(Base):
    __tablename__ = "registration_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Idempotency key: SHA-256 of the normalized form URL
    form_url_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    form_url: Mapped[str] = mapped_column(Text, nullable=False)

    # Raw announcement text (WhatsApp message or manual). May be truncated.
    # Phone numbers are NOT stored separately.
    announcement_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    announcement_source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="unknown"
    )

    status: Mapped[RegistrationStatus] = mapped_column(
        Enum(RegistrationStatus),
        nullable=False,
        default=RegistrationStatus.WAITING,
    )

    # Timestamps
    announced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Metrics
    processing_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Diagnostics
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<RegistrationAttempt id={self.id} status={self.status} "
            f"url_hash={self.form_url_hash[:8]}...>"
        )

