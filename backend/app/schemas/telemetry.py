"""Telemetry schemas."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class TelemetryMessage(BaseModel):
    """Inbound MQTT telemetry message schema."""
    schema_version: str = Field(default="1.0", pattern=r"^\d+\.\d+$")
    device_id: str
    timestamp: datetime
    firmware_version: Optional[str] = None
    readings: Dict[str, Any]


class TelemetryResponse(BaseModel):
    """Single telemetry reading response."""
    id: int
    device_id: str
    timestamp: datetime
    schema_version: str
    readings: Dict[str, Any]
    firmware_version: Optional[str] = None

    model_config = {"from_attributes": True}


class TelemetryQuery(BaseModel):
    """Query params for telemetry history."""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)
