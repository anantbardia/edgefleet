"""Cloud synchronization service and worker."""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import httpx
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.audit import CloudSyncQueue

logger = logging.getLogger("edgefleet.cloud_sync")


class CloudSyncService:
    """Manages cloud sync queueing, processing, and outbound status."""

    def __init__(self):
        self._running = False
        self._last_sync_at: datetime | None = None
        self._last_connected: bool = False
        self._recent_errors: List[str] = []

    @property
    def last_sync_at(self) -> datetime | None:
        return self._last_sync_at

    @property
    def is_connected(self) -> bool:
        return self._last_connected

    @property
    def recent_errors(self) -> List[str]:
        return self._recent_errors[-5:]

    def _record_error(self, err: str):
        self._recent_errors.append(f"[{datetime.now(timezone.utc).isoformat()}] {err}")
        if len(self._recent_errors) > 20:
            self._recent_errors.pop(0)

    async def enqueue_event(
        self,
        db: AsyncSession,
        event_type: str,
        payload: Dict[str, Any],
        event_id: str | None = None,
    ) -> CloudSyncQueue:
        """Enqueue an event for asynchronous cloud synchronization."""
        # Ensure queue doesn't exceed max bound
        count_query = select(func.count(CloudSyncQueue.id)).where(
            CloudSyncQueue.status == "pending"
        )
        count_res = await db.execute(count_query)
        pending_count = count_res.scalar() or 0

        if pending_count >= settings.CLOUD_SYNC_QUEUE_MAX_SIZE:
            logger.warning(
                "Cloud sync queue is full (%d events). Dropping oldest pending events.",
                pending_count,
            )
            # Evict oldest pending
            oldest_subquery = (
                select(CloudSyncQueue.id)
                .where(CloudSyncQueue.status == "pending")
                .order_by(CloudSyncQueue.created_at.asc())
                .limit(10)
            )
            oldest_ids = (await db.execute(oldest_subquery)).scalars().all()
            if oldest_ids:
                await db.execute(
                    update(CloudSyncQueue)
                    .where(CloudSyncQueue.id.in_(oldest_ids))
                    .values(status="expired", error="Evicted due to queue capacity")
                )

        event = CloudSyncQueue(
            event_id=event_id or str(uuid.uuid4()),
            event_type=event_type,
            payload=payload,
            status="pending",
            created_at=datetime.now(timezone.utc),
            attempts=0,
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event

    async def get_status(self, db: AsyncSession) -> Dict[str, Any]:
        """Retrieve aggregated queue counts and connectivity state."""
        # Query counts by status
        stmt = (
            select(CloudSyncQueue.status, func.count(CloudSyncQueue.id))
            .group_by(CloudSyncQueue.status)
        )
        res = await db.execute(stmt)
        counts = dict(res.all())

        pending = counts.get("pending", 0)
        failed = counts.get("failed", 0)
        sent = counts.get("sent", 0)
        total = sum(counts.values())

        return {
            "enabled": settings.CLOUD_ENABLED,
            "api_url": settings.CLOUD_API_URL,
            "connected": self._last_connected,
            "last_sync_at": self._last_sync_at,
            "queue_size": total,
            "pending_events": pending,
            "failed_events": failed,
            "sent_events": sent,
            "recent_errors": self.recent_errors,
        }

    async def sync_batch(self, db: AsyncSession, batch_size: int = 50) -> int:
        """Push a batch of pending events to cloud backend."""
        if not settings.CLOUD_ENABLED or not settings.CLOUD_API_URL:
            return 0

        # Select pending events sorted by creation time
        stmt = (
            select(CloudSyncQueue)
            .where(CloudSyncQueue.status == "pending")
            .order_by(CloudSyncQueue.created_at.asc())
            .limit(batch_size)
        )
        res = await db.execute(stmt)
        events = res.scalars().all()

        if not events:
            return 0

        payload = [
            {
                "event_id": ev.event_id,
                "event_type": ev.event_type,
                "created_at": ev.created_at.isoformat(),
                "payload": ev.payload,
            }
            for ev in events
        ]

        url = f"{settings.CLOUD_API_URL.rstrip('/')}/api/v1/sync/events"
        headers = {
            "Authorization": f"Bearer {settings.CLOUD_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": f"EdgeFleet-Gateway/{settings.APP_VERSION}",
        }

        now = datetime.now(timezone.utc)
        success = False
        error_msg = None

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code in (200, 201, 202):
                    success = True
                    self._last_connected = True
                    self._last_sync_at = now
                else:
                    error_msg = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    self._record_error(error_msg)
                    self._last_connected = False
        except Exception as exc:
            error_msg = f"Network error: {str(exc)}"
            self._record_error(error_msg)
            self._last_connected = False

        # Update event statuses
        for ev in events:
            ev.attempts += 1
            ev.last_attempt_at = now
            if success:
                ev.status = "sent"
                ev.error = None
            else:
                if ev.attempts >= settings.CLOUD_SYNC_MAX_RETRIES:
                    ev.status = "failed"
                    ev.error = error_msg
                else:
                    ev.error = error_msg

        await db.commit()
        return len(events) if success else 0

    async def pull_pending_deployments(self, db: AsyncSession) -> int:
        """Poll cloud control plane for any pending firmware deployments targeted at this gateway."""
        if not settings.CLOUD_ENABLED or not settings.CLOUD_API_URL:
            return 0

        url = f"{settings.CLOUD_API_URL.rstrip('/')}/api/v1/sync/pending-deployments"
        headers = {
            "Authorization": f"Bearer {settings.CLOUD_API_KEY}",
            "User-Agent": f"EdgeFleet-Gateway/{settings.APP_VERSION}",
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    return 0

                jobs = resp.json().get("jobs", [])
                if not jobs:
                    return 0

                for job_data in jobs:
                    await self._process_remote_deployment(db, client, job_data)

                return len(jobs)
        except Exception as exc:
            logger.debug("Error checking remote cloud deployments: %s", exc)
            return 0

    async def _process_remote_deployment(
        self, db: AsyncSession, client: httpx.AsyncClient, job_data: Dict[str, Any]
    ):
        """Download firmware release binary, register release and device locally, and queue deployment."""
        from app.models.deployment import DeploymentJob
        from app.models.firmware import FirmwareRelease
        from app.models.device import Device
        import os

        rel_data = job_data.get("release", {})
        device_id = job_data.get("device_id")
        remote_job_id = job_data.get("id")

        if not rel_data or not device_id or not remote_job_id:
            return

        # Check if deployment job already exists locally
        existing_job = await db.execute(select(DeploymentJob).where(DeploymentJob.id == remote_job_id))
        if existing_job.scalar_one_or_none():
            return

        # 1. Ensure local firmware release binary exists
        rel_id = rel_data.get("id")
        filename = f"{rel_data.get('version')}_{rel_id[:8]}.bin"
        local_dir = settings.firmware_storage
        local_path = str(local_dir / filename)

        if not os.path.exists(local_path):
            # Download binary from cloud
            download_url = f"{settings.CLOUD_API_URL.rstrip('/')}/api/firmware/{rel_id}/download"
            headers = {"Authorization": f"Bearer {settings.CLOUD_API_KEY}"}
            file_resp = await client.get(download_url, headers=headers)
            if file_resp.status_code == 200:
                with open(local_path, "wb") as f:
                    f.write(file_resp.content)
            else:
                logger.warning("Failed to download cloud firmware binary %s", rel_id)
                return

        # Register FirmwareRelease locally if not present
        existing_rel = await db.execute(select(FirmwareRelease).where(FirmwareRelease.id == rel_id))
        if not existing_rel.scalar_one_or_none():
            release = FirmwareRelease(
                id=rel_id,
                version=rel_data.get("version"),
                mcu_family=rel_data.get("mcu_family", "esp32"),
                target_boards=rel_data.get("target_boards", []),
                file_path=local_path,
                file_size=os.path.getsize(local_path),
                sha256=rel_data.get("sha256"),
                is_approved=True,
                release_notes=rel_data.get("release_notes", "Synced from Cloud Control Plane"),
            )
            db.add(release)
            await db.commit()

        # 2. Ensure device exists locally
        dev_res = await db.execute(select(Device).where(Device.device_id == device_id))
        dev = dev_res.scalar_one_or_none()
        if not dev:
            # Auto-register device stub
            dev = Device(
                device_id=device_id,
                name=job_data.get("device_name", device_id),
                mcu_family=rel_data.get("mcu_family", "esp32"),
                board_variant="esp32-wroom-32",
            )
            db.add(dev)
            await db.commit()

        # 3. Create DeploymentJob in QUEUED state
        new_job = DeploymentJob(
            id=remote_job_id,
            device_id=device_id,
            release_id=rel_id,
            state="QUEUED",
            target_version=rel_data.get("version"),
            requested_by="cloud_control_plane",
            progress_details={"source": "cloud_sync"},
        )
        db.add(new_job)
        await db.commit()
        logger.info("Queued remote cloud deployment %s for device %s", remote_job_id, device_id)

    async def prune_old_events(self, db: AsyncSession):
        """Prune sent or expired events older than retention period."""
        cutoff = datetime.now(timezone.utc) - timedelta(
            days=settings.CLOUD_SYNC_RETENTION_DAYS
        )
        stmt = delete(CloudSyncQueue).where(
            CloudSyncQueue.status.in_(["sent", "expired"]),
            CloudSyncQueue.created_at < cutoff,
        )
        await db.execute(stmt)
        await db.commit()


cloud_sync_service = CloudSyncService()
