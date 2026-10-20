"""Cloud sync schemas."""

from datetime import datetime
from pydantic import BaseModel


class CloudStatusResponse(BaseModel):
    """Cloud synchronization status response."""

    enabled: bool
    api_url: str
    connected: bool
    last_sync_at: datetime | None = None
    queue_size: int = 0
    pending_events: int = 0
    failed_events: int = 0
    sent_events: int = 0
    recent_errors: list[str] = []


class CloudSyncTriggerResponse(BaseModel):
    """Response when manually triggering a cloud sync."""

    message: str
    events_processed: int
    success: bool
