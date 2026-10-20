"""Models package — imports all models so Alembic and init_db can discover them."""

from app.models.user import User
from app.models.device import Device
from app.models.telemetry import TelemetryReading
from app.models.firmware import FirmwareRelease
from app.models.deployment import DeploymentJob, DeploymentAudit
from app.models.alert import Alert
from app.models.audit import AuditLog, CloudSyncQueue

__all__ = [
    "User",
    "Device",
    "TelemetryReading",
    "FirmwareRelease",
    "DeploymentJob",
    "DeploymentAudit",
    "Alert",
    "AuditLog",
    "CloudSyncQueue",
]
