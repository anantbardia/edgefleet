"""EdgeFleet FastAPI application entrypoint."""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import alerts, auth, cloud, deployments, devices, firmware, health, telemetry
from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.rate_limit import limiter
from app.database.session import async_session_factory, close_db, init_db
from app.mqtt.client import mqtt_client
from app.services.cloud_sync import cloud_sync_service
from app.services.deployment_service import deployment_service
from app.services.device_service import device_service
from app.websocket.manager import ws_manager

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("edgefleet")


async def heartbeat_monitoring_loop():
    """Background task to detect device offline timeouts."""
    while True:
        try:
            await asyncio.sleep(30.0)
            async with async_session_factory() as db:
                await device_service.check_heartbeats(db)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("Error in heartbeat monitor: %s", exc)


async def cloud_sync_periodic_loop():
    """Background task to periodically batch-sync pending events to cloud."""
    while True:
        try:
            await asyncio.sleep(settings.CLOUD_SYNC_INTERVAL_SECONDS)
            if settings.CLOUD_ENABLED and settings.CLOUD_API_URL:
                async with async_session_factory() as db:
                    await cloud_sync_service.sync_batch(db)
                    await cloud_sync_service.pull_pending_deployments(db)
                    await cloud_sync_service.prune_old_events(db)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("Error in cloud sync loop: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    logger.info("Initializing database...")
    await init_db()

    loop = asyncio.get_running_loop()

    # Start MQTT client
    mqtt_client.start(loop)

    # Start deployment queue worker
    deployment_service.start_worker()

    # Start background heartbeat monitor
    hb_task = asyncio.create_task(heartbeat_monitoring_loop())
    cloud_task = asyncio.create_task(cloud_sync_periodic_loop())

    logger.info("EdgeFleet Gateway backend started successfully.")

    yield

    logger.info("Shutting down EdgeFleet Gateway...")
    hb_task.cancel()
    cloud_task.cancel()
    deployment_service.stop_worker()
    mqtt_client.stop()
    await close_db()
    logger.info("EdgeFleet Gateway shutdown complete.")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # State and Rate Limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Custom Exception Handlers
    register_exception_handlers(app)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API Routers under /api
    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(devices.router, prefix="/api")
    app.include_router(telemetry.router, prefix="/api")
    app.include_router(firmware.router, prefix="/api")
    app.include_router(deployments.router, prefix="/api")
    app.include_router(alerts.router, prefix="/api")
    app.include_router(cloud.router, prefix="/api")
    app.include_router(cloud.sync_router, prefix="/api")

    # WebSocket endpoints
    @app.websocket("/ws")
    @app.websocket("/api/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await ws_manager.connect(websocket)
        try:
            while True:
                # Keepalive / ping-pong handling
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            await ws_manager.disconnect(websocket)
        except Exception:
            await ws_manager.disconnect(websocket)

    # Mount frontend dist if built
    dist_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if dist_dir.exists() and dist_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="frontend")

    return app


app = create_app()
