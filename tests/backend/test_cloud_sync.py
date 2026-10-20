"""Tests for cloud sync queueing, backoff, and durability."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import CloudSyncQueue
from app.services.cloud_sync import cloud_sync_service


@pytest.mark.asyncio
async def test_enqueue_cloud_sync_event(db_session: AsyncSession):
    event = await cloud_sync_service.enqueue_event(
        db=db_session,
        event_type="device_registered",
        payload={"device_id": "esp32-001", "mcu": "esp32"},
    )
    assert event.id is not None
    assert event.status == "pending"
    assert event.attempts == 0

    res = await db_session.execute(
        select(CloudSyncQueue).where(CloudSyncQueue.event_id == event.event_id)
    )
    found = res.scalar_one_or_none()
    assert found is not None
    assert found.payload["device_id"] == "esp32-001"


@pytest.mark.asyncio
async def test_cloud_sync_status_reporting(db_session: AsyncSession):
    await cloud_sync_service.enqueue_event(
        db=db_session,
        event_type="test_event",
        payload={"data": 123},
    )
    status = await cloud_sync_service.get_status(db_session)
    assert status["pending_events"] >= 1
    assert "queue_size" in status
