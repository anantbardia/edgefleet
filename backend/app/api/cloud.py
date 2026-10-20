"""Cloud synchronization API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_operator, require_viewer
from app.database.session import get_db
from app.models.user import User
from app.schemas.cloud import CloudStatusResponse, CloudSyncTriggerResponse
from app.services.cloud_sync import cloud_sync_service

router = APIRouter(prefix="/cloud", tags=["Cloud Sync"])


@router.get("/status", response_model=CloudStatusResponse)
async def get_cloud_status(
    user: User = Depends(require_viewer),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve outbound cloud synchronization health, queue depth, and metrics."""
    status = await cloud_sync_service.get_status(db)
    return CloudStatusResponse(**status)


@router.post("/sync-now", response_model=CloudSyncTriggerResponse)
async def trigger_cloud_sync(
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Trigger an immediate batch synchronization with the cloud backend."""
    processed = await cloud_sync_service.sync_batch(db, batch_size=100)
    return CloudSyncTriggerResponse(
        message="Sync batch executed successfully",
        events_processed=processed,
        success=cloud_sync_service.is_connected,
    )
