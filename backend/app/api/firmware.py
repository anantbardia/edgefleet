"""Firmware management API endpoints."""

import hashlib
import uuid
from math import ceil
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin, require_operator, require_viewer
from app.config import settings
from app.core.exceptions import (
    DuplicateResourceError,
    FirmwareNotFoundError,
    FirmwareValidationError,
)
from app.core.rate_limit import limiter
from app.database.session import get_db
from app.models.firmware import FirmwareRelease
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.firmware import FirmwareApproval, FirmwareResponse

router = APIRouter(prefix="/firmware", tags=["Firmware"])

# Allowed extensions by MCU family
ALLOWED_EXTENSIONS = {
    "esp32": {".bin"},
    "arduino_uno": {".hex"},
}


@router.get("", response_model=PaginatedResponse[FirmwareResponse])
async def list_releases(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    mcu_family: str | None = None,
    is_approved: bool | None = None,
    user: User = Depends(require_viewer),
    db: AsyncSession = Depends(get_db),
):
    """List firmware releases with filtering and pagination."""
    query = select(FirmwareRelease)

    if mcu_family:
        query = query.where(FirmwareRelease.mcu_family == mcu_family)
    if is_approved is not None:
        query = query.where(FirmwareRelease.is_approved == is_approved)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(FirmwareRelease.created_at.desc())
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    releases = result.scalars().all()

    return PaginatedResponse(
        items=[FirmwareResponse.model_validate(r) for r in releases],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if page_size else 0,
    )


@router.get("/{release_id}", response_model=FirmwareResponse)
async def get_release(
    release_id: str,
    user: User = Depends(require_viewer),
    db: AsyncSession = Depends(get_db),
):
    """Get firmware release details."""
    result = await db.execute(
        select(FirmwareRelease).where(FirmwareRelease.id == release_id)
    )
    release = result.scalar_one_or_none()
    if not release:
        raise FirmwareNotFoundError(release_id)
    return FirmwareResponse.model_validate(release)


@router.post("/upload", response_model=FirmwareResponse, status_code=201)
@limiter.limit("10/minute")
async def upload_firmware(
    request: Request,
    file: UploadFile = File(...),
    version: str = Form(...),
    mcu_family: str = Form(...),
    target_boards: str = Form(...),  # comma-separated
    build_id: str = Form(default=""),
    release_notes: str = Form(default=""),
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Upload a firmware artifact.

    Validates file extension, size, computes SHA-256, and stores the artifact
    outside the web root.
    """
    # Validate MCU family
    if mcu_family not in ALLOWED_EXTENSIONS:
        raise FirmwareValidationError(f"Unsupported MCU family: {mcu_family}")

    # Validate version format
    import re
    if not re.match(r"^\d+\.\d+\.\d+", version):
        raise FirmwareValidationError(
            f"Invalid version format: {version}. Expected semver (e.g., 1.0.0)"
        )

    # Validate file extension
    if not file.filename:
        raise FirmwareValidationError("Filename is required")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS[mcu_family]:
        allowed = ", ".join(ALLOWED_EXTENSIONS[mcu_family])
        raise FirmwareValidationError(
            f"Invalid extension '{ext}' for {mcu_family}. Allowed: {allowed}"
        )

    # Read and validate size
    content = await file.read()
    if len(content) == 0:
        raise FirmwareValidationError("Empty firmware file")
    if len(content) > settings.max_upload_bytes:
        raise FirmwareValidationError(
            f"File too large: {len(content)} bytes (max {settings.MAX_UPLOAD_SIZE_MB} MB)"
        )

    # Compute SHA-256
    sha256 = hashlib.sha256(content).hexdigest()

    # Check for duplicate hash
    result = await db.execute(
        select(FirmwareRelease).where(FirmwareRelease.sha256 == sha256)
    )
    if result.scalar_one_or_none():
        raise DuplicateResourceError(
            f"Firmware with SHA-256 {sha256[:16]}... already exists"
        )

    # Parse target boards
    boards = [b.strip() for b in target_boards.split(",") if b.strip()]
    if not boards:
        raise FirmwareValidationError("At least one target board is required")

    # Store file
    release_id = str(uuid.uuid4())
    stored_filename = f"{release_id}_{sha256[:8]}{ext}"
    storage_path = settings.firmware_storage / stored_filename
    storage_path.write_bytes(content)

    # Create release record
    release = FirmwareRelease(
        id=release_id,
        version=version,
        mcu_family=mcu_family,
        target_boards=boards,
        file_path=str(storage_path),
        file_size=len(content),
        sha256=sha256,
        build_id=build_id or None,
        release_notes=release_notes,
        is_approved=False,
        created_by=user.id,
        original_filename=file.filename,
    )
    db.add(release)
    await db.flush()
    await db.refresh(release)

    return FirmwareResponse.model_validate(release)


@router.patch("/{release_id}", response_model=FirmwareResponse)
async def update_release(
    release_id: str,
    body: FirmwareApproval,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Approve or update a firmware release (admin only)."""
    result = await db.execute(
        select(FirmwareRelease).where(FirmwareRelease.id == release_id)
    )
    release = result.scalar_one_or_none()
    if not release:
        raise FirmwareNotFoundError(release_id)

    if body.is_approved is not None:
        release.is_approved = body.is_approved
    if body.release_notes is not None:
        release.release_notes = body.release_notes

    await db.flush()
    await db.refresh(release)
    return FirmwareResponse.model_validate(release)


@router.get("/{release_id}/download")
async def download_firmware(
    release_id: str,
    user: User = Depends(require_viewer),
    db: AsyncSession = Depends(get_db),
):
    """Download firmware binary (authenticated)."""
    result = await db.execute(
        select(FirmwareRelease).where(FirmwareRelease.id == release_id)
    )
    release = result.scalar_one_or_none()
    if not release:
        raise FirmwareNotFoundError(release_id)

    file_path = Path(release.file_path)
    if not file_path.exists():
        raise FirmwareNotFoundError(f"File missing for release {release_id}")

    return FileResponse(
        path=str(file_path),
        filename=release.original_filename,
        media_type="application/octet-stream",
    )
