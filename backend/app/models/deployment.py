"""Deployment job and audit database models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


# Valid deployment states
DEPLOYMENT_STATES = [
    "queued",
    "preflight",
    "transferring",
    "verifying",
    "installing",
    "rebooting",
    "health_check",
    "success",
    "failed",
    "cancelled",
    "recovery_required",
]

# Terminal states that allow no further transitions
TERMINAL_STATES = {"success", "failed", "cancelled", "recovery_required"}

# Valid state transitions
VALID_TRANSITIONS = {
    "queued": {"preflight", "cancelled", "failed"},
    "preflight": {"transferring", "failed", "cancelled"},
    "transferring": {"verifying", "installing", "failed", "cancelled"},
    "verifying": {"installing", "rebooting", "failed", "cancelled"},
    "installing": {"rebooting", "health_check", "success", "failed"},  # cancel unsafe during installation
    "rebooting": {"health_check", "success", "failed"},
    "health_check": {"success", "failed"},
    "failed": {"recovery_required"},
}

# States where cancellation is unsafe
CANCEL_UNSAFE_STATES = {"installing", "rebooting"}


class DeploymentJob(Base):
    """A firmware deployment job targeting a single device."""

    __tablename__ = "deployment_jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    device_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("devices.id"), nullable=False, index=True
    )
    release_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("firmware_releases.id"), nullable=False
    )
    rollout_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    state: Mapped[str] = mapped_column(
        String(30), nullable=False, default="queued", index=True
    )
    source_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_version: Mapped[str] = mapped_column(String(50), nullable=False)
    requested_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    progress_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class DeploymentAudit(Base):
    """Audit trail entry for a deployment state change."""

    __tablename__ = "deployment_audits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    deployment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("deployment_jobs.id"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    old_state: Mapped[str | None] = mapped_column(String(30), nullable=True)
    new_state: Mapped[str | None] = mapped_column(String(30), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
