"""Deployment service managing state machine, queue execution, and adapter orchestration."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.session import async_session_factory
from app.device_adapters.arduino_uno import arduino_adapter
from app.device_adapters.base import BaseDeviceAdapter
from app.device_adapters.esp32_ota import esp32_adapter
from app.device_adapters.esp32_serial import esp32_serial_adapter
from app.models.deployment import (
    CANCEL_UNSAFE_STATES,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    DeploymentAudit,
    DeploymentJob,
)
from app.models.device import Device
from app.models.firmware import FirmwareRelease
from app.services.alert_service import alert_service
from app.services.cloud_sync import cloud_sync_service
from app.websocket.manager import ws_manager

logger = logging.getLogger("edgefleet.deployment_service")


class DeploymentService:
    """Manages deployment jobs, queue execution, and hardware adapters."""

    def __init__(self):
        self._worker_task: Optional[asyncio.Task] = None
        self._queue_lock = asyncio.Lock()
        self._running = False

    def get_adapter_for_device(
        self, device: Device, job: Optional[DeploymentJob] = None
    ) -> BaseDeviceAdapter:
        """Resolve hardware deployment adapter by device configuration and job context."""
        if device.mcu_family == "esp32":
            # If serial_port is configured, or explicitly requested as USB/serial, use serial cable adapter
            if device.serial_port:
                return esp32_serial_adapter
            if job and job.progress_details and job.progress_details.get("connection") == "usb_serial":
                return esp32_serial_adapter
            return esp32_adapter
        elif device.mcu_family == "arduino_uno":
            return arduino_adapter
        raise ValueError(f"Unsupported MCU family: {device.mcu_family}")

    def get_adapter_for_mcu(self, mcu_family: str) -> BaseDeviceAdapter:
        """Resolve hardware deployment adapter by MCU family (defaulting to OTA for esp32)."""
        if mcu_family == "esp32":
            return esp32_adapter
        elif mcu_family == "arduino_uno":
            return arduino_adapter
        raise ValueError(f"Unsupported MCU family: {mcu_family}")

    async def transition_state(
        self,
        db: AsyncSession,
        job: DeploymentJob,
        new_state: str,
        details: Dict[str, Any] | None = None,
        failure_reason: str | None = None,
    ) -> DeploymentJob:
        """Enforce state machine transitions, record audit entry, and broadcast."""
        old_state = job.state

        if new_state not in VALID_TRANSITIONS.get(old_state, []):
            msg = f"Invalid state transition from {old_state} to {new_state}"
            logger.error(msg)
            raise ValueError(msg)

        now = datetime.now(timezone.utc)
        job.state = new_state
        if details:
            existing = job.progress_details or {}
            existing.update(details)
            job.progress_details = existing

        if failure_reason:
            job.failure_reason = failure_reason

        if new_state == "TRANSFERRING" and not job.started_at:
            job.started_at = now
        elif new_state in TERMINAL_STATES:
            job.completed_at = now

        # Add audit entry
        audit_entry = DeploymentAudit(
            deployment_id=job.id,
            timestamp=now,
            event_type=f"STATE_CHANGE_{new_state}",
            old_state=old_state,
            new_state=new_state,
            details=details or {},
        )
        db.add(audit_entry)
        await db.commit()
        await db.refresh(job)

        # Broadcast via WebSocket
        try:
            await ws_manager.broadcast_deployment(
                deployment_id=str(job.id),
                state=new_state,
                device_id=job.device_id,
                details=details,
                failure_reason=failure_reason,
            )
        except Exception as exc:
            logger.debug("Failed broadcasting deployment state: %s", exc)

        # Enqueue cloud sync
        try:
            await cloud_sync_service.enqueue_event(
                db=db,
                event_type="deployment_state_change",
                payload={
                    "deployment_id": str(job.id),
                    "old_state": old_state,
                    "new_state": new_state,
                    "device_id": job.device_id,
                    "target_version": job.target_version,
                },
            )
        except Exception as exc:
            logger.debug("Failed enqueuing cloud sync: %s", exc)

        return job

    async def execute_job(self, job_id: str):
        """Execute a single deployment job through its target adapter."""
        async with async_session_factory() as db:
            job_res = await db.execute(select(DeploymentJob).where(DeploymentJob.id == job_id))
            job = job_res.scalar_one_or_none()
            if not job or job.state in TERMINAL_STATES:
                return

            dev_res = await db.execute(select(Device).where(Device.device_id == job.device_id))
            device = dev_res.scalar_one_or_none()

            rel_res = await db.execute(select(FirmwareRelease).where(FirmwareRelease.id == job.release_id))
            release = rel_res.scalar_one_or_none()

            if not device or not release:
                await self.transition_state(
                    db, job, "FAILED", None, "Associated device or firmware release not found"
                )
                return

            adapter = self.get_adapter_for_device(device, job)

            # Move to PREFLIGHT
            try:
                await self.transition_state(db, job, "PREFLIGHT", {"stage": "preflight_checks"}, None)
                compat, warnings = await adapter.preflight_check(device, release)
                if not compat:
                    err = f"Preflight failed: {'; '.join(warnings)}"
                    await self.transition_state(db, job, "FAILED", {"warnings": warnings}, err)
                    return
            except Exception as exc:
                await self.transition_state(db, job, "FAILED", None, f"Preflight exception: {exc}")
                return

            # Progress callback for the adapter
            async def progress_callback(
                stage: str,
                details: Dict[str, Any] | None = None,
                failure_reason: str | None = None,
            ):
                async with async_session_factory() as inner_db:
                    j_res = await inner_db.execute(select(DeploymentJob).where(DeploymentJob.id == job_id))
                    current_j = j_res.scalar_one()
                    await self.transition_state(inner_db, current_j, stage, details, failure_reason)

            # Execute via adapter
            success = await adapter.execute_deployment(job, device, release, progress_callback)

            # Post-execution cleanup & device updates
            async with async_session_factory() as finalize_db:
                final_res = await finalize_db.execute(select(DeploymentJob).where(DeploymentJob.id == job_id))
                final_job = final_res.scalar_one()

                if success:
                    # Update device firmware version
                    await finalize_db.execute(
                        update(Device)
                        .where(Device.device_id == device.device_id)
                        .values(firmware_version=release.version)
                    )
                    await finalize_db.commit()
                else:
                    # Create deployment_failed alert
                    await alert_service.create_alert(
                        db=finalize_db,
                        alert_type="deployment_failed",
                        severity="critical",
                        message=f"Deployment {job_id} to {device.device_id} failed: {final_job.failure_reason}",
                        device_id=device.device_id,
                    )

                    # If part of a rollout, cancel remaining queued jobs in the same rollout
                    if final_job.rollout_id:
                        await self.cancel_remaining_rollout(finalize_db, final_job.rollout_id, job_id)

    async def cancel_remaining_rollout(self, db: AsyncSession, rollout_id: str, failed_job_id: str):
        """Cancel subsequent jobs in a multi-device rollout when a node fails."""
        stmt = (
            select(DeploymentJob)
            .where(
                DeploymentJob.rollout_id == rollout_id,
                DeploymentJob.id != failed_job_id,
                DeploymentJob.state == "QUEUED",
            )
        )
        res = await db.execute(stmt)
        remaining = res.scalars().all()

        for j in remaining:
            await self.transition_state(
                db,
                j,
                "CANCELLED",
                {"reason": f"Rollout aborted due to failure on prior job {failed_job_id}"},
                f"Rollout aborted due to prior failure",
            )
        logger.warning("Cancelled %d subsequent jobs in rollout %s", len(remaining), rollout_id)

    async def process_queue(self):
        """Background queue processor that picks next QUEUED job sequentially."""
        while self._running:
            try:
                async with async_session_factory() as db:
                    # Check if there is already an active (non-terminal, non-queued) job
                    active_stmt = select(DeploymentJob).where(
                        DeploymentJob.state.not_in(TERMINAL_STATES + ["QUEUED"])
                    )
                    active_res = await db.execute(active_stmt)
                    active_job = active_res.scalar_one_or_none()

                    if not active_job:
                        # Pick next queued job (FIFO)
                        next_stmt = (
                            select(DeploymentJob)
                            .where(DeploymentJob.state == "QUEUED")
                            .order_by(DeploymentJob.started_at.asc().nullsfirst(), DeploymentJob.id.asc())
                            .limit(1)
                        )
                        next_res = await db.execute(next_stmt)
                        next_job = next_res.scalar_one_or_none()

                        if next_job:
                            logger.info("Starting deployment job %s for device %s", next_job.id, next_job.device_id)
                            # Run job
                            asyncio.create_task(self.execute_job(str(next_job.id)))

            except Exception as exc:
                logger.error("Error in deployment queue loop: %s", exc)

            await asyncio.sleep(2.0)

    def start_worker(self):
        """Start background queue worker."""
        if not self._running:
            self._running = True
            self._worker_task = asyncio.create_task(self.process_queue())
            logger.info("Deployment queue worker started.")

    def stop_worker(self):
        """Stop background queue worker."""
        self._running = False
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            logger.info("Deployment queue worker stopped.")


deployment_service = DeploymentService()
