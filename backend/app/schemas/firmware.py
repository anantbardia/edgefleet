"""Firmware release schemas."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class FirmwareUploadMeta(BaseModel):
    """Metadata submitted alongside firmware file upload."""
    version: str = Field(min_length=1, max_length=50, pattern=r"^\d+\.\d+\.\d+.*$")
    mcu_family: str = Field(pattern="^(esp32|arduino_uno)$")
    target_boards: List[str] = Field(min_length=1)
    build_id: Optional[str] = Field(None, max_length=100)
    release_notes: str = Field(default="", max_length=5000)


class FirmwareResponse(BaseModel):
    """Firmware release details."""
    id: str
    version: str
    mcu_family: str
    target_boards: List[str]
    file_size: int
    sha256: str
    build_id: Optional[str] = None
    release_notes: str
    is_approved: bool
    created_at: datetime
    created_by: Optional[str] = None
    original_filename: str
    signature_metadata: Optional[Dict] = None

    model_config = {"from_attributes": True}


class FirmwareApproval(BaseModel):
    """Approve or update a firmware release."""
    is_approved: Optional[bool] = None
    release_notes: Optional[str] = Field(None, max_length=5000)
