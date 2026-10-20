"""Telemetry API endpoints."""

from math import ceil
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_viewer
from app.core.exceptions import DeviceNotFoundError
from app.database.session import get_db
from app.models.device import Device
from app.models.telemetry import TelemetryReading
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.telemetry import TelemetryResponse

router = APIRouter(prefix="/devices", tags=["Telemetry"])


@router.get("/{device_id}/telemetry", response_model=PaginatedResponse[TelemetryResponse])
async def get_telemetry(
    device_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    user: User = Depends(require_viewer),
    db: AsyncSession = Depends(get_db),
):
    """Get telemetry readings for a device with time-range filtering and pagination."""
    # Resolve device
    result = await db.execute(
        select(Device).where(
            (Device.device_id == device_id) | (Device.id == device_id)
        )
    )
    device = result.scalar_one_or_none()
    if not device:
        raise DeviceNotFoundError(device_id)

    query = select(TelemetryReading).where(TelemetryReading.device_id == device.id)

    if start_time:
        query = query.where(TelemetryReading.timestamp >= start_time)
    if end_time:
        query = query.where(TelemetryReading.timestamp <= end_time)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Order and paginate
    query = query.order_by(TelemetryReading.timestamp.desc())
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    readings = result.scalars().all()

    return PaginatedResponse(
        items=[TelemetryResponse.model_validate(r) for r in readings],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if page_size else 0,
    )


@router.get("/{device_id}/telemetry/latest", response_model=TelemetryResponse | None)
async def get_latest_telemetry(
    device_id: str,
    user: User = Depends(require_viewer),
    db: AsyncSession = Depends(get_db),
):
    """Get the most recent telemetry reading for a device."""
    result = await db.execute(
        select(Device).where(
            (Device.device_id == device_id) | (Device.id == device_id)
        )
    )
    device = result.scalar_one_or_none()
    if not device:
        raise DeviceNotFoundError(device_id)

    result = await db.execute(
        select(TelemetryReading)
        .where(TelemetryReading.device_id == device.id)
        .order_by(TelemetryReading.timestamp.desc())
        .limit(1)
    )
    reading = result.scalar_one_or_none()
    if reading is None:
        return None
    return TelemetryResponse.model_validate(reading)
