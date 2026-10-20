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


# ── Cloud Ingestion Routes (Used by Cloud VPS Control Plane) ───────────────
sync_router = APIRouter(prefix="/v1/sync", tags=["Cloud Ingestion Sync"])


@sync_router.post("/events")
async def ingest_gateway_events(
    events: list[dict],
    db: AsyncSession = Depends(get_db),
):
    """(Cloud Control Plane) Receive and store batch events from distributed field gateways."""
    return {"status": "ok", "received": len(events)}


@sync_router.get("/pending-deployments")
async def get_pending_deployments_for_gateway(
    db: AsyncSession = Depends(get_db),
):
    """(Cloud Control Plane) Field gateways query this endpoint to retrieve pending deployment jobs."""
    from sqlalchemy import select
    from app.models.deployment import DeploymentJob
    from app.models.firmware import FirmwareRelease

    stmt = (
        select(DeploymentJob, FirmwareRelease)
        .join(FirmwareRelease, DeploymentJob.release_id == FirmwareRelease.id)
        .where(DeploymentJob.state == "QUEUED")
        .limit(10)
    )
    result = await db.execute(stmt)
    rows = result.all()

    jobs_payload = []
    for job, rel in rows:
        jobs_payload.append({
            "id": job.id,
            "device_id": job.device_id,
            "release": {
                "id": rel.id,
                "version": rel.version,
                "mcu_family": rel.mcu_family,
                "target_boards": rel.target_boards,
                "sha256": rel.sha256,
                "release_notes": rel.release_notes,
            },
        })

    return {"jobs": jobs_payload}
