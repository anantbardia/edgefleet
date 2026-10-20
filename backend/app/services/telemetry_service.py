"""Telemetry service for data ingestion, pruning, and real-time streaming."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.device import Device
from app.models.telemetry import TelemetryReading
from app.websocket.manager import ws_manager

logger = logging.getLogger("edgefleet.telemetry_service")


class TelemetryService:
    """Ingests and queries sensor telemetry data."""

    async def ingest_reading(
        self,
        db: AsyncSession,
        device_id: str,
        readings: Dict[str, Any],
        schema_version: str = "1.0",
        firmware_version: str = "",
        timestamp: datetime | None = None,
    ) -> TelemetryReading:
        """Ingest single telemetry reading, update device last_seen, and broadcast."""
        ts = timestamp or datetime.now(timezone.utc)

        # Resolve device by id or device_id
        res = await db.execute(
            select(Device).where(
                (Device.id == device_id) | (Device.device_id == device_id)
            )
        )
        dev = res.scalar_one_or_none()
        dev_pk = dev.id if dev else device_id

        reading = TelemetryReading(
            device_id=dev_pk,
            schema_version=schema_version,
            readings=readings,
            firmware_version=firmware_version,
            timestamp=ts,
        )
        db.add(reading)

        # Update device last_seen and online status
        if dev:
            dev.last_seen = ts
            dev.is_online = True
            if firmware_version:
                dev.firmware_version = firmware_version

        await db.commit()
        await db.refresh(reading)


        # Broadcast via WebSocket
        try:
            await ws_manager.broadcast_telemetry(
                device_id=device_id,
                readings=readings,
                timestamp=ts.isoformat(),
                version=firmware_version,
            )
        except Exception as exc:
            logger.debug("Failed broadcasting telemetry: %s", exc)

        return reading

    async def prune_old_telemetry(self, db: AsyncSession) -> int:
        """Prune telemetry older than retention threshold."""
        cutoff = datetime.now(timezone.utc) - timedelta(
            days=settings.TELEMETRY_RETENTION_DAYS
        )
        stmt = delete(TelemetryReading).where(TelemetryReading.timestamp < cutoff)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount or 0


telemetry_service = TelemetryService()
