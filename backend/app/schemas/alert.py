"""Alert schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AlertResponse(BaseModel):
    """Alert details."""
    id: str
    device_id: Optional[str] = None
    alert_type: str
    severity: str
    message: str
    acknowledged: bool
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AlertAcknowledge(BaseModel):
    """Acknowledge an alert."""
    pass  # User ID comes from auth context


class AuditLogResponse(BaseModel):
    """Audit log entry."""
    id: int
    user_id: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    timestamp: datetime

    model_config = {"from_attributes": True}
