"""Abstract base class for hardware deployment adapters."""

import json
from abc import ABC, abstractmethod
from typing import Any, Callable, Coroutine, List, Tuple

from app.models.deployment import DeploymentJob
from app.models.device import Device
from app.models.firmware import FirmwareRelease

# Callback signature: callback(state: str, details: dict | None = None, failure_reason: str | None = None)
ProgressCallback = Callable[[str, dict | None, str | None], Coroutine[Any, Any, None]]


def is_board_compatible(device_board: str | None, target_boards: Any) -> bool:
    """Check if device board variant matches target boards.

    Handles:
    - Target boards containing '*' or 'any' (matches everything)
    - Empty or None target_boards / device_board (matches everything)
    - Case insensitivity ('atmega328p' == 'ATmega328P')
    - Malformed nested JSON or stringified arrays ('["ATmega328P"]')
    - Hyphen vs underscore normalization ('esp32-wroom-32' vs 'esp32_wroom_32')
    """
    if not target_boards or not device_board:
        return True

    normalized_targets = set()

    def _extract_parts(val: Any):
        if val is None:
            return
        if isinstance(val, (list, tuple, set)):
            for item in val:
                _extract_parts(item)
            return

        val_str = str(val).strip()
        if not val_str:
            return

        # Try JSON parsing if it looks like a JSON array/string
        if (val_str.startswith("[") and val_str.endswith("]")) or (val_str.startswith('"') and val_str.endswith('"')):
            try:
                parsed = json.loads(val_str)
                _extract_parts(parsed)
                return
            except Exception:
                pass

        # Split by comma and strip quotes/brackets
        for part in val_str.replace("[", "").replace("]", "").replace('"', '').replace("'", "").split(","):
            cleaned = part.strip().lower()
            if cleaned:
                normalized_targets.add(cleaned)

    _extract_parts(target_boards)

    if not normalized_targets or "*" in normalized_targets or "any" in normalized_targets:
        return True

    dev = device_board.strip().lower()
    if not dev:
        return True

    dev_variants = {
        dev,
        dev.replace("-", "_"),
        dev.replace("_", "-"),
        dev.replace(" ", ""),
    }

    for tgt in normalized_targets:
        tgt_variants = {
            tgt,
            tgt.replace("-", "_"),
            tgt.replace("_", "-"),
            tgt.replace(" ", ""),
        }
        if dev_variants & tgt_variants:
            return True

    # Allow cross-variant upgrades between ESP32 family chips (e.g. C3, S3, WROOM)
    if ("esp32" in dev or "c3" in dev or "s3" in dev) and any("esp32" in t or "c3" in t or "s3" in t for t in normalized_targets):
        return True

    return False


class BaseDeviceAdapter(ABC):
    """Abstract interface for target-specific firmware deployment."""

    mcu_family: str

    @staticmethod
    def is_board_compatible(device_board: str | None, target_boards: Any) -> bool:
        return is_board_compatible(device_board, target_boards)

    @abstractmethod
    async def preflight_check(
        self,
        device: Device,
        release: FirmwareRelease,
    ) -> Tuple[bool, List[str]]:
        """Validate target hardware compatibility before queuing deployment.

        Returns (is_compatible, list_of_warning_or_error_messages).
        """
        pass

    @abstractmethod
    async def execute_deployment(
        self,
        job: DeploymentJob,
        device: Device,
        release: FirmwareRelease,
        on_progress: ProgressCallback,
    ) -> bool:
        """Run the end-to-end deployment procedure for this device.

        Should invoke on_progress with states:
        TRANSFERRING -> VERIFYING -> INSTALLING -> REBOOTING -> HEALTH_CHECK -> SUCCESS/FAILED.
        """
        pass

    @abstractmethod
    async def cancel_deployment(self, job: DeploymentJob) -> bool:
        """Attempt safe cancellation of an in-flight deployment."""
        pass
