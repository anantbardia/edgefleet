"""Device service for lifecycle, online/offline monitoring, and heartbeats."""

import logging
from datetime import datetime, timedelta, timezone
from typing import List

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.device import Device
from app.services.alert_service import alert_service
from app.services.cloud_sync import cloud_sync_service
from app.websocket.manager import ws_manager

logger = logging.getLogger("edgefleet.device_service")


class DeviceService:
    """Manages device state, online/offline detection, and heartbeat timeouts."""

    async def check_heartbeats(self, db: AsyncSession) -> List[str]:
        """Scan active devices and mark those exceeding heartbeat threshold as offline."""
        timeout_threshold = datetime.now(timezone.utc) - timedelta(
            seconds=settings.HEARTBEAT_TIMEOUT_SECONDS
        )

        # Select devices currently marked online whose last_seen is older than threshold
        stmt = select(Device).where(
            Device.is_online == True,
            Device.last_seen < timeout_threshold,
        )
        res = await db.execute(stmt)
        timed_out_devices = res.scalars().all()

        offline_device_ids = []
        for dev in timed_out_devices:
            dev.is_online = False
            offline_device_ids.append(dev.device_id)

            # Raise offline alert
            await alert_service.create_alert(
                db=db,
                alert_type="device_offline",
                severity="warning",
                message=f"Device {dev.name or dev.device_id} timed out (no heartbeat for >{settings.HEARTBEAT_TIMEOUT_SECONDS}s).",
                device_id=dev.device_id,
                auto_commit=False,
            )

            # Broadcast WebSocket status
            await ws_manager.broadcast_device_status(
                device_id=dev.device_id,
                is_online=False,
                last_seen=dev.last_seen.isoformat() if dev.last_seen else None,
            )

            # Enqueue cloud sync
            await cloud_sync_service.enqueue_event(
                db=db,
                event_type="device_status",
                payload={
                    "device_id": dev.device_id,
                    "is_online": False,
                    "last_seen": dev.last_seen.isoformat() if dev.last_seen else None,
                },
            )

        if timed_out_devices:
            await db.commit()
            logger.info("Marked %d devices offline due to heartbeat timeout", len(timed_out_devices))

        return offline_device_ids

    async def mark_online(self, db: AsyncSession, device_id: str, **kwargs):
        """Mark a device online, resolve offline alerts, and broadcast update."""
        now = datetime.now(timezone.utc)
        update_data = {"is_online": True, "last_seen": now}
        update_data.update(kwargs)

        await db.execute(
            update(Device)
            .where(Device.device_id == device_id)
            .values(**update_data)
        )
        await db.commit()

        # Resolve offline alert
        await alert_service.auto_resolve_device_offline(db, device_id)

        # Broadcast WebSocket status
        await ws_manager.broadcast_device_status(
            device_id=device_id,
            is_online=True,
            last_seen=now.isoformat(),
            **kwargs,
        )


device_service = DeviceService()
