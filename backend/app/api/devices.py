"""Device management API endpoints."""

from math import ceil

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin, require_operator, require_viewer
from app.core.exceptions import DeviceNotFoundError, DuplicateResourceError
from app.database.session import get_db
from app.models.device import Device
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.device import DeviceCreate, DeviceResponse, DeviceSummary, DeviceUpdate

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.get("", response_model=PaginatedResponse[DeviceResponse])
async def list_devices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    mcu_family: str | None = None,
    is_online: bool | None = None,
    search: str | None = None,
    sort_by: str = Query("registered_at", pattern="^(device_id|name|mcu_family|is_online|last_seen|registered_at)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    user: User = Depends(require_viewer),
    db: AsyncSession = Depends(get_db),
):
    """List devices with filtering, searching, sorting, and pagination."""
    query = select(Device)

    # Filters
    if mcu_family:
        query = query.where(Device.mcu_family == mcu_family)
    if is_online is not None:
        query = query.where(Device.is_online == is_online)
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Device.device_id.ilike(search_term),
                Device.name.ilike(search_term),
                Device.board_variant.ilike(search_term),
            )
        )

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Sort
    sort_col = getattr(Device, sort_by, Device.registered_at)
    if sort_order == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    devices = result.scalars().all()

    return PaginatedResponse(
        items=[DeviceResponse.model_validate(d) for d in devices],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if page_size else 0,
    )


@router.get("/summary", response_model=DeviceSummary)
async def device_summary(
    user: User = Depends(require_viewer),
    db: AsyncSession = Depends(get_db),
):
    """Get device inventory summary statistics."""
    total_result = await db.execute(select(func.count(Device.id)))
    total = total_result.scalar() or 0

    online_result = await db.execute(
        select(func.count(Device.id)).where(Device.is_online == True)
    )
    online = online_result.scalar() or 0

    # Count by MCU family
    family_result = await db.execute(
        select(Device.mcu_family, func.count(Device.id)).group_by(Device.mcu_family)
    )
    by_mcu_family = dict(family_result.all())

    return DeviceSummary(
        total=total,
        online=online,
        offline=total - online,
        by_mcu_family=by_mcu_family,
    )


@router.get("/ports/serial")
async def get_serial_ports(
    user: User = Depends(require_viewer),
):
    """List detected USB serial ports for ESP32 and Arduino cable flashing."""
    from app.device_adapters.serial_manager import list_available_ports
    return list_available_ports()


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: str,
    user: User = Depends(require_viewer),
    db: AsyncSession = Depends(get_db),
):
    """Get device details by device_id."""
    result = await db.execute(
        select(Device).where(
            (Device.device_id == device_id) | (Device.id == device_id)
        )
    )
    device = result.scalar_one_or_none()
    if not device:
        raise DeviceNotFoundError(device_id)
    return DeviceResponse.model_validate(device)


@router.post("", response_model=DeviceResponse, status_code=201)
async def register_device(
    body: DeviceCreate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Register a new device (admin only)."""
    # Check for duplicate
    result = await db.execute(
        select(Device).where(Device.device_id == body.device_id)
    )
    if result.scalar_one_or_none():
        raise DuplicateResourceError(f"Device {body.device_id} already registered")

    device = Device(
        device_id=body.device_id,
        name=body.name,
        mcu_family=body.mcu_family,
        board_variant=body.board_variant,
        sensor_types=body.sensor_types,
        serial_port=body.serial_port,
        description=body.description,
    )
    db.add(device)
    await db.flush()
    await db.refresh(device)
    return DeviceResponse.model_validate(device)


@router.patch("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: str,
    body: DeviceUpdate,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Update device metadata (operator+)."""
    result = await db.execute(
        select(Device).where(
            (Device.device_id == device_id) | (Device.id == device_id)
        )
    )
    device = result.scalar_one_or_none()
    if not device:
        raise DeviceNotFoundError(device_id)

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(device, field, value)

    await db.flush()
    await db.refresh(device)
    return DeviceResponse.model_validate(device)


@router.delete("/{device_id}", status_code=204)
async def delete_device(
    device_id: str,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Deregister a device (admin only)."""
    result = await db.execute(
        select(Device).where(
            (Device.device_id == device_id) | (Device.id == device_id)
        )
    )
    device = result.scalar_one_or_none()
    if not device:
        raise DeviceNotFoundError(device_id)

    await db.delete(device)
