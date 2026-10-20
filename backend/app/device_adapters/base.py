"""Abstract base class for hardware deployment adapters."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Coroutine, List, Tuple

from app.models.deployment import DeploymentJob
from app.models.device import Device
from app.models.firmware import FirmwareRelease

# Callback signature: callback(state: str, details: dict | None = None, failure_reason: str | None = None)
ProgressCallback = Callable[[str, dict | None, str | None], Coroutine[Any, Any, None]]


class BaseDeviceAdapter(ABC):
    """Abstract interface for target-specific firmware deployment."""

    mcu_family: str

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
