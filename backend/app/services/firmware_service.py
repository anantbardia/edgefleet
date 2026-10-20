"""Firmware service handling file storage, validation, SHA-256 calculation, and approval."""

import hashlib
import os
from pathlib import Path
from typing import List, Tuple

import aiofiles
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import DuplicateFirmwareError, InvalidFirmwareError
from app.models.firmware import FirmwareRelease


class FirmwareService:
    """Manages firmware validation, hash verification, storage, and release approval."""

    def __init__(self):
        self.storage_dir = Path(settings.FIRMWARE_STORAGE_PATH)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    async def save_and_register_firmware(
        self,
        db: AsyncSession,
        file: UploadFile,
        version: str,
        mcu_family: str,
        target_boards: List[str],
        release_notes: str | None,
        created_by: str,
    ) -> FirmwareRelease:
        """Validate, hash, save, and record a firmware binary."""
        # 1. Validate extension
        filename = file.filename or "unknown"
        ext = os.path.splitext(filename)[1].lower()

        if mcu_family == "esp32" and ext != ".bin":
            raise InvalidFirmwareError(f"ESP32 firmware requires .bin extension, got '{ext}'")
        elif mcu_family == "arduino_uno" and ext not in (".hex", ".bin"):
            raise InvalidFirmwareError(f"Arduino Uno firmware requires .hex extension, got '{ext}'")

        # 2. Read in chunks, compute SHA-256, enforce size limit
        sha256_hasher = hashlib.sha256()
        total_bytes = 0
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

        temp_chunks = []
        while chunk := await file.read(64 * 1024):
            total_bytes += len(chunk)
            if total_bytes > max_bytes:
                raise InvalidFirmwareError(
                    f"Firmware file exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB} MB"
                )
            sha256_hasher.update(chunk)
            temp_chunks.append(chunk)

        if total_bytes == 0:
            raise InvalidFirmwareError("Firmware binary cannot be empty")

        digest = sha256_hasher.hexdigest()

        # 3. Check for duplicates
        dup_res = await db.execute(
            select(FirmwareRelease).where(FirmwareRelease.sha256 == digest)
        )
        if dup_res.scalar_one_or_none():
            raise DuplicateFirmwareError(f"Firmware with SHA-256 {digest} already exists in registry")

        # 4. Save to storage directory
        clean_ext = ext if ext else ".bin"
        storage_filename = f"{mcu_family}_{version.replace('.', '_')}_{digest[:8]}{clean_ext}"
        destination_path = self.storage_dir / storage_filename

        async with aiofiles.open(destination_path, "wb") as dest:
            for c in temp_chunks:
                await dest.write(c)

        # 5. Insert database record
        release = FirmwareRelease(
            version=version,
            mcu_family=mcu_family,
            target_boards=target_boards,
            file_path=str(destination_path.resolve()),
            file_size=total_bytes,
            sha256=digest,
            release_notes=release_notes,
            is_approved=False,  # Requires explicit approval
            created_by=created_by,
        )
        db.add(release)
        await db.commit()
        await db.refresh(release)
        return release


firmware_service = FirmwareService()
