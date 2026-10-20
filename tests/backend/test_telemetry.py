"""Tests for telemetry ingestion and historical querying."""

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.telemetry import TelemetryReading


@pytest.mark.asyncio
async def test_get_telemetry_history(
    client: AsyncClient, test_esp32_device, db_session: AsyncSession, viewer_headers
):
    # Insert sample reading
    reading = TelemetryReading(
        device_id=test_esp32_device.id,
        schema_version="1.0",
        readings={"temperature": 24.5, "humidity": 55.0},
        firmware_version="1.0.0",
        timestamp=datetime.now(timezone.utc),
    )
    db_session.add(reading)
    await db_session.commit()

    resp = await client.get(
        f"/api/devices/{test_esp32_device.device_id}/telemetry",
        headers=viewer_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["readings"]["temperature"] == 24.5


@pytest.mark.asyncio
async def test_get_latest_telemetry(
    client: AsyncClient, test_esp32_device, db_session: AsyncSession, viewer_headers
):
    reading = TelemetryReading(
        device_id=test_esp32_device.id,
        schema_version="1.0",
        readings={"temperature": 26.8},
        firmware_version="1.0.0",
        timestamp=datetime.now(timezone.utc),
    )
    db_session.add(reading)
    await db_session.commit()

    resp = await client.get(
        f"/api/devices/{test_esp32_device.device_id}/telemetry/latest",
        headers=viewer_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["readings"]["temperature"] == 26.8
