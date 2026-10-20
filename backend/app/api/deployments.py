"""Deployment management API endpoints."""

import uuid
from datetime import datetime, timezone
from math import ceil

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_operator, require_viewer
from app.core.exceptions import (
    CancellationUnsafeError,
    DeploymentConcurrencyError,
    DeploymentNotFoundError,
    DeviceNotFoundError,
    FirmwareNotFoundError,
    IncompatibleFirmwareError,
    InvalidStateTransitionError,
)
from app.database.session import get_db
from app.models.deployment import (
    CANCEL_UNSAFE_STATES,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    DeploymentAudit,
    DeploymentJob,
)
from app.models.device import Device
from app.models.firmware import FirmwareRelease
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.deployment import (
    CancelRequest,
    DeploymentAuditResponse,
    DeploymentCreate,
    DeploymentResponse,
    PreflightRequest,
    PreflightResponse,
    PreflightResult,
)
from app.config import settings
from app.core.security import create_access_token
from app.device_adapters.base import is_board_compatible

router = APIRouter(prefix="/deployments", tags=["Deployments"])


@router.post("/preflight", response_model=PreflightResponse)
async def preflight_check(
    body: PreflightRequest,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Run compatibility checks before deployment."""
    # Get release
    result = await db.execute(
        select(FirmwareRelease).where(FirmwareRelease.id == body.release_id)
    )
    release = result.scalar_one_or_none()
    if not release:
        raise FirmwareNotFoundError(body.release_id)

    results = []
    for dev_id in body.device_ids:
        result = await db.execute(
            select(Device).where(
                (Device.device_id == dev_id) | (Device.id == dev_id)
            )
        )
        device = result.scalar_one_or_none()

        if not device:
            results.append(PreflightResult(
                device_id=dev_id,
                compatible=False,
                errors=[f"Device {dev_id} not found"],
            ))
            continue

        warnings = []
        errors = []

        # MCU family check
        if device.mcu_family != release.mcu_family:
            errors.append(
                f"MCU family mismatch: device is {device.mcu_family}, "
                f"firmware targets {release.mcu_family}"
            )

        # Board variant check
        if release.target_boards and device.board_variant:
            if not is_board_compatible(device.board_variant, release.target_boards):
                if device.mcu_family == "esp32":
                    warnings.append(
                        f"Board variant '{device.board_variant}' differs from target boards: {release.target_boards}"
                    )
                else:
                    errors.append(
                        f"Board variant '{device.board_variant}' not in target boards: "
                        f"{release.target_boards}"
                    )

        # Approval check
        if not release.is_approved:
            errors.append("Firmware release is not approved")

        # Online check
        if not device.is_online:
            if device.mcu_family == "esp32" and not device.serial_port:
                errors.append("Device is offline — OTA requires connectivity (or configure USB serial cable)")
            else:
                warnings.append("Device is offline — USB serial flash will proceed directly via cable")

        # Same version check
        if device.firmware_version == release.version:
            warnings.append(f"Device already running version {release.version}")

        # Active deployment check
        active_result = await db.execute(
            select(func.count(DeploymentJob.id)).where(
                DeploymentJob.device_id == device.id,
                DeploymentJob.state.notin_(TERMINAL_STATES),
            )
        )
        if active_result.scalar():
            errors.append("Device has an active deployment")

        results.append(PreflightResult(
            device_id=dev_id,
            compatible=len(errors) == 0,
            warnings=warnings,
            errors=errors,
        ))

    all_compatible = all(r.compatible for r in results)

    # Generate a confirmation token (short-lived)
    confirmation_token = create_access_token(
        data={
            "purpose": "deployment_confirmation",
            "release_id": body.release_id,
            "device_ids": body.device_ids,
        },
    )

    return PreflightResponse(
        results=results,
        all_compatible=all_compatible,
        confirmation_token=confirmation_token,
    )


@router.post("", response_model=list[DeploymentResponse], status_code=201)
async def create_deployment(
    body: DeploymentCreate,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Create deployment job(s) for the selected devices."""
    # Check concurrency limit
    active_result = await db.execute(
        select(func.count(DeploymentJob.id)).where(
            DeploymentJob.state.notin_(TERMINAL_STATES)
        )
    )
    active_count = active_result.scalar() or 0
    if active_count >= settings.DEPLOYMENT_CONCURRENCY_LIMIT:
        raise DeploymentConcurrencyError()

    # Get release
    result = await db.execute(
        select(FirmwareRelease).where(FirmwareRelease.id == body.release_id)
    )
    release = result.scalar_one_or_none()
    if not release:
        raise FirmwareNotFoundError(body.release_id)

    if not release.is_approved:
        raise IncompatibleFirmwareError("Release is not approved for deployment")

    rollout_id = str(uuid.uuid4()) if len(body.device_ids) > 1 else None
    jobs = []

    for dev_id in body.device_ids:
        result = await db.execute(
            select(Device).where(
                (Device.device_id == dev_id) | (Device.id == dev_id)
            )
        )
        device = result.scalar_one_or_none()
        if not device:
            raise DeviceNotFoundError(dev_id)

        # Compatibility check
        if device.mcu_family != release.mcu_family:
            raise IncompatibleFirmwareError(
                f"MCU mismatch for {device.device_id}: "
                f"{device.mcu_family} vs {release.mcu_family}"
            )

        job = DeploymentJob(
            device_id=device.id,
            release_id=release.id,
            rollout_id=rollout_id,
            state="queued",
            source_version=device.firmware_version,
            target_version=release.version,
            requested_by=user.id,
        )
        db.add(job)
        await db.flush()

        # Audit entry
        audit = DeploymentAudit(
            deployment_id=job.id,
            event_type="deployment_created",
            old_state=None,
            new_state="queued",
            details={
                "release_id": release.id,
                "target_version": release.version,
                "requested_by": user.email,
            },
        )
        db.add(audit)
        jobs.append(job)

    await db.flush()
    for job in jobs:
        await db.refresh(job)

    return [DeploymentResponse.model_validate(j) for j in jobs]


@router.get("", response_model=PaginatedResponse[DeploymentResponse])
async def list_deployments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    state: str | None = None,
    device_id: str | None = None,
    user: User = Depends(require_viewer),
    db: AsyncSession = Depends(get_db),
):
    """List deployment jobs with filtering and pagination."""
    query = select(DeploymentJob)

    if state:
        query = query.where(DeploymentJob.state == state)
    if device_id:
        query = query.where(DeploymentJob.device_id == device_id)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(DeploymentJob.started_at.desc())
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    jobs = result.scalars().all()

    return PaginatedResponse(
        items=[DeploymentResponse.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if page_size else 0,
    )


@router.get("/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: str,
    user: User = Depends(require_viewer),
    db: AsyncSession = Depends(get_db),
):
    """Get deployment job details."""
    result = await db.execute(
        select(DeploymentJob).where(DeploymentJob.id == deployment_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise DeploymentNotFoundError(deployment_id)
    return DeploymentResponse.model_validate(job)


@router.post("/{deployment_id}/cancel")
async def cancel_deployment(
    deployment_id: str,
    body: CancelRequest = CancelRequest(),
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a deployment (safe states only)."""
    result = await db.execute(
        select(DeploymentJob).where(DeploymentJob.id == deployment_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise DeploymentNotFoundError(deployment_id)

    if job.state in TERMINAL_STATES:
        raise InvalidStateTransitionError(job.state, "cancelled")

    if job.state in CANCEL_UNSAFE_STATES:
        raise CancellationUnsafeError(job.state)

    old_state = job.state
    job.state = "cancelled"
    job.completed_at = datetime.now(timezone.utc)
    job.failure_reason = body.reason

    audit = DeploymentAudit(
        deployment_id=job.id,
        event_type="deployment_cancelled",
        old_state=old_state,
        new_state="cancelled",
        details={"reason": body.reason, "cancelled_by": user.email},
    )
    db.add(audit)

    # If part of a rollout, cancel remaining queued jobs
    if job.rollout_id:
        result = await db.execute(
            select(DeploymentJob).where(
                DeploymentJob.rollout_id == job.rollout_id,
                DeploymentJob.state == "queued",
                DeploymentJob.id != job.id,
            )
        )
        remaining = result.scalars().all()
        for r_job in remaining:
            r_job.state = "cancelled"
            r_job.completed_at = datetime.now(timezone.utc)
            r_job.failure_reason = f"Rollout cancelled: {body.reason}"
            db.add(DeploymentAudit(
                deployment_id=r_job.id,
                event_type="rollout_cancelled",
                old_state="queued",
                new_state="cancelled",
                details={"reason": f"Rollout cancelled by {user.email}"},
            ))

    return {"message": "Deployment cancelled", "deployment_id": deployment_id}


@router.get("/{deployment_id}/logs", response_model=list[DeploymentAuditResponse])
async def get_deployment_logs(
    deployment_id: str,
    user: User = Depends(require_viewer),
    db: AsyncSession = Depends(get_db),
):
    """Get audit trail for a deployment."""
    result = await db.execute(
        select(DeploymentJob).where(DeploymentJob.id == deployment_id)
    )
    if not result.scalar_one_or_none():
        raise DeploymentNotFoundError(deployment_id)

    result = await db.execute(
        select(DeploymentAudit)
        .where(DeploymentAudit.deployment_id == deployment_id)
        .order_by(DeploymentAudit.timestamp.asc())
    )
    audits = result.scalars().all()
    return [DeploymentAuditResponse.model_validate(a) for a in audits]
