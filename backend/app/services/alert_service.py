"""Alert service for raising and resolving system/device alerts."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.services.cloud_sync import cloud_sync_service
from app.websocket.manager import ws_manager

logger = logging.getLogger("edgefleet.alert_service")


class AlertService:
    """Handles alert creation, de-duplication, auto-resolution, and notifications."""

    async def create_alert(
        self,
        db: AsyncSession,
        alert_type: str,
        severity: str,
        message: str,
        device_id: str | None = None,
        auto_commit: bool = True,
    ) -> Alert:
        """Create a new alert, broadcast via WebSocket, and enqueue for cloud sync."""
        alert = Alert(
            device_id=device_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            acknowledged=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(alert)
        if auto_commit:
            await db.commit()
            await db.refresh(alert)

        alert_data = {
            "id": alert.id,
            "device_id": alert.device_id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "message": alert.message,
            "acknowledged": alert.acknowledged,
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
        }

        # WebSocket notification
        try:
            await ws_manager.broadcast_alert(alert_data)
        except Exception as exc:
            logger.debug("Failed to broadcast alert over websocket: %s", exc)

        # Enqueue for cloud sync
        try:
            await cloud_sync_service.enqueue_event(
                db=db,
                event_type="alert_created",
                payload=alert_data,
            )
        except Exception as exc:
            logger.debug("Failed to enqueue cloud sync for alert: %s", exc)

        return alert

    async def auto_resolve_device_offline(self, db: AsyncSession, device_id: str):
        """Auto-acknowledge or clear device_offline alerts when device recovers."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(Alert)
            .where(
                Alert.device_id == device_id,
                Alert.alert_type == "device_offline",
                Alert.acknowledged == False,
            )
            .values(
                acknowledged=True,
                acknowledged_at=now,
            )
        )
        await db.execute(stmt)
        await db.commit()


alert_service = AlertService()
