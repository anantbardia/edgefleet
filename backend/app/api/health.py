"""Health check endpoint."""

import time
from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import settings

router = APIRouter(tags=["Health"])

_start_time = time.monotonic()


@router.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    """Health check — no authentication required."""
    uptime = time.monotonic() - _start_time
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "uptime_seconds": round(uptime, 1),
        "mock_mode": settings.MOCK_MODE,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
