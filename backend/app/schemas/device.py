"""Device schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DeviceCreate(BaseModel):
    """Register a new device."""
    device_id: str = Field(min_length=1, max_length=128, pattern="^[a-zA-Z0-9_-]+$")
    name: str = Field(max_length=255, default="")
    mcu_family: str = Field(pattern="^(esp32|arduino_uno)$")
    board_variant: str = Field(max_length=100, default="")
    sensor_types: Optional[List[str]] = None
    serial_port: Optional[str] = None
    description: str = Field(max_length=1000, default="")


class DeviceUpdate(BaseModel):
    """Update device metadata."""
    device_id: Optional[str] = Field(None, min_length=1, max_length=128, pattern="^[a-zA-Z0-9_-]+$")
    name: Optional[str] = Field(None, max_length=255)
    board_variant: Optional[str] = Field(None, max_length=100)
    sensor_types: Optional[List[str]] = None
    serial_port: Optional[str] = None
    description: Optional[str] = Field(None, max_length=1000)


class DeviceResponse(BaseModel):
    """Device details response."""
    id: str
    device_id: str
    name: str
    mcu_family: str
    board_variant: str
    sensor_types: Optional[List[str]] = None
    firmware_version: Optional[str] = None
    is_online: bool
    last_seen: Optional[datetime] = None
    uptime_seconds: Optional[int] = None
    ip_address: Optional[str] = None
    serial_port: Optional[str] = None
    registered_at: datetime
    description: str
    is_mock: bool

    model_config = {"from_attributes": True}


class DeviceStatusUpdate(BaseModel):
    """MQTT-driven device status update."""
    schema_version: str = "1.0"
    device_id: str
    status: str = Field(pattern="^(online|offline)$")
    firmware_version: Optional[str] = None
    uptime_seconds: Optional[int] = None
    ip_address: Optional[str] = None
    reset_reason: Optional[str] = None


class DeviceSummary(BaseModel):
    """Summary statistics for device inventory."""
    total: int
    online: int
    offline: int
    by_mcu_family: Dict[str, int]
