"""Custom exception classes and handlers."""

from fastapi import HTTPException, status


class EdgeFleetError(Exception):
    """Base exception for EdgeFleet application errors."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class DeviceNotFoundError(EdgeFleetError):
    def __init__(self, device_id: str):
        super().__init__(f"Device not found: {device_id}", status_code=404)


class FirmwareNotFoundError(EdgeFleetError):
    def __init__(self, release_id: str):
        super().__init__(f"Firmware release not found: {release_id}", status_code=404)


class DeploymentNotFoundError(EdgeFleetError):
    def __init__(self, deployment_id: str):
        super().__init__(f"Deployment not found: {deployment_id}", status_code=404)


class InvalidStateTransitionError(EdgeFleetError):
    def __init__(self, current: str, target: str):
        super().__init__(
            f"Invalid state transition: {current} → {target}", status_code=409
        )


class IncompatibleFirmwareError(EdgeFleetError):
    def __init__(self, reason: str):
        super().__init__(f"Incompatible firmware: {reason}", status_code=422)


class DuplicateResourceError(EdgeFleetError):
    def __init__(self, resource: str):
        super().__init__(f"Duplicate resource: {resource}", status_code=409)


class FirmwareValidationError(EdgeFleetError):
    def __init__(self, reason: str):
        super().__init__(f"Firmware validation failed: {reason}", status_code=422)


class DeploymentConcurrencyError(EdgeFleetError):
    def __init__(self):
        super().__init__(
            "Deployment concurrency limit reached. Wait for current deployment to complete.",
            status_code=429,
        )


class CancellationUnsafeError(EdgeFleetError):
    def __init__(self, state: str):
        super().__init__(
            f"Cancellation is unsafe during state: {state}. "
            "The deployment must complete or fail.",
            status_code=409,
        )


class DuplicateFirmwareError(DuplicateResourceError):
    pass


class InvalidFirmwareError(FirmwareValidationError):
    pass


def credentials_exception():
    """Standard 401 exception for authentication failures."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def forbidden_exception(detail: str = "Insufficient permissions"):
    """Standard 403 exception for authorization failures."""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail,
    )


def register_exception_handlers(app):
    """Register custom exception handlers on FastAPI application."""
    from fastapi.responses import JSONResponse

    @app.exception_handler(EdgeFleetError)
    async def edgefleet_error_handler(request, exc: EdgeFleetError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "error_type": exc.__class__.__name__},
        )

