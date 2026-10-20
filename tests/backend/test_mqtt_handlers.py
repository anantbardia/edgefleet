"""Tests for MQTT message routing and schema ingestion."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.models.telemetry import TelemetryReading
from app.mqtt import handlers


@pytest.mark.asyncio
async def test_handle_telemetry_ingestion(db_session: AsyncSession, test_esp32_device):
    # Store IDs as local variables before any async session operations
    dev_id = test_esp32_device.device_id
    dev_pk = test_esp32_device.id

    payload = {
        "schema_version": "1.0",
        "timestamp": "2026-10-19T22:00:00Z",
        "firmware_version": "1.0.0",
        "readings": {"temperature": 25.4, "humidity": 60.1},
    }

    await handlers.handle_telemetry(dev_id, payload)

    # Query in fresh transaction using dev_pk string
    res = await db_session.execute(
        select(TelemetryReading).where(TelemetryReading.device_id == dev_pk)
    )
    reading = res.scalar_one_or_none()
    assert reading is not None
    assert reading.readings["temperature"] == 25.4


@pytest.mark.asyncio
async def test_handle_status_offline_lwt(db_session: AsyncSession, test_esp32_device):
    dev_id = test_esp32_device.device_id

    payload = {
        "status": "offline",
        "uptime_seconds": 120,
    }

    await handlers.handle_status(dev_id, payload)

    # Query in fresh transaction using dev_id string
    res = await db_session.execute(
        select(Device.is_online).where(Device.device_id == dev_id)
    )
    is_online = res.scalar_one()
    assert is_online is False
