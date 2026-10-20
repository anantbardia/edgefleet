"""MQTT inbound message handlers."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import async_session_factory
from app.device_adapters.esp32_ota import esp32_adapter
from app.models.device import Device
from app.services.alert_service import alert_service
from app.services.device_service import device_service
from app.services.telemetry_service import telemetry_service
from app.websocket.manager import ws_manager

logger = logging.getLogger("edgefleet.mqtt.handlers")


async def handle_telemetry(device_id: str, payload: Dict[str, Any]):
    """Process incoming telemetry readings from a device."""
    try:
        readings = payload.get("readings", {})
        schema_version = str(payload.get("schema_version", "1.0"))
        firmware_version = str(payload.get("firmware_version", ""))
        ts_raw = payload.get("timestamp")
        ts = None
        if ts_raw:
            try:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            except Exception:
                ts = datetime.now(timezone.utc)

        async with async_session_factory() as db:
            # Check device exists
            res = await db.execute(select(Device).where(Device.device_id == device_id))
            dev = res.scalar_one_or_none()
            if not dev:
                logger.warning("Received telemetry for unregistered device: %s. Auto-registering.", device_id)
                mcu = "esp32" if "esp32" in device_id.lower() else "arduino_uno"
                dev = Device(
                    device_id=device_id,
                    name=device_id,
                    mcu_family=mcu,
                    firmware_version=firmware_version or "1.0.0",
                    is_online=True,
                    last_seen=datetime.now(timezone.utc),
                )
                db.add(dev)
                await db.commit()

            await telemetry_service.ingest_reading(
                db=db,
                device_id=device_id,
                readings=readings,
                schema_version=schema_version,
                firmware_version=firmware_version,
                timestamp=ts,
            )

    except Exception as exc:
        logger.exception("Error handling telemetry for device %s: %s", device_id, exc)


async def handle_status(device_id: str, payload: Dict[str, Any]):
    """Process status reports and MQTT Last Will and Testament messages."""
    try:
        status = payload.get("status", "online")
        is_online = (status == "online")
        uptime = payload.get("uptime_seconds")
        ip_addr = payload.get("ip_address")
        fw_ver = payload.get("firmware_version")
        reset_reason = payload.get("reset_reason")

        async with async_session_factory() as db:
            res = await db.execute(select(Device).where(Device.device_id == device_id))
            dev = res.scalar_one_or_none()
            if not dev:
                logger.warning("Status report for unregistered device: %s", device_id)
                return

            update_fields: Dict[str, Any] = {
                "is_online": is_online,
                "last_seen": datetime.now(timezone.utc),
            }
            if uptime is not None:
                update_fields["uptime_seconds"] = int(uptime)
            if ip_addr:
                update_fields["ip_address"] = str(ip_addr)
            if fw_ver:
                update_fields["firmware_version"] = str(fw_ver)

            await db.execute(
                update(Device).where(Device.device_id == device_id).values(**update_fields)
            )
            await db.commit()

            # Handle unexpected reboot alert
            if reset_reason and reset_reason not in ("power_on", "ota_update", "normal"):
                await alert_service.create_alert(
                    db=db,
                    alert_type="unexpected_reboot",
                    severity="warning",
                    message=f"Device {device_id} rebooted unexpectedly with reason: {reset_reason}",
                    device_id=device_id,
                )

            # Broadcast status update
            await ws_manager.broadcast_device_status(
                device_id=device_id,
                is_online=is_online,
                uptime_seconds=uptime,
                ip_address=ip_addr,
                firmware_version=fw_ver,
            )

    except Exception as exc:
        logger.exception("Error handling status for device %s: %s", device_id, exc)


async def handle_events(device_id: str, payload: Dict[str, Any]):
    """Process event notifications, hardware faults, and anomalies."""
    try:
        event_name = payload.get("event", "generic_event")
        severity = payload.get("severity", "info")
        message = payload.get("message", f"Device event: {event_name}")

        async with async_session_factory() as db:
            await alert_service.create_alert(
                db=db,
                alert_type=event_name,
                severity=severity,
                message=message,
                device_id=device_id,
            )
    except Exception as exc:
        logger.exception("Error handling events for device %s: %s", device_id, exc)


async def handle_update_status(device_id: str, payload: Dict[str, Any]):
    """Process OTA progress updates emitted by target devices."""
    try:
        deployment_id = payload.get("deployment_id")
        if deployment_id:
            esp32_adapter.register_status_report(deployment_id, payload)
        logger.info("Device %s OTA update status: %s", device_id, payload)
    except Exception as exc:
        logger.exception("Error handling update status for device %s: %s", device_id, exc)
