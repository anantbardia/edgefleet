"""Serial Telemetry Bridge for reading USB/cable telemetry from ESP32 & Arduino."""

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from app.config import settings
from app.database.session import async_session_factory
from app.device_adapters.serial_manager import get_port_lock, list_available_ports
from app.services.telemetry_service import telemetry_service

logger = logging.getLogger("edgefleet.serial_bridge")


class SerialTelemetryBridge:
    """Async background bridge that reads incoming JSON telemetry lines over USB serial cable."""

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._current_port: Optional[str] = None

    def start(self, port: Optional[str] = None):
        """Start reading telemetry from specified port or auto-detected ESP port."""
        if self._running:
            return
        self._running = True
        self._current_port = port
        self._task = asyncio.create_task(self._read_loop())
        logger.info("Serial telemetry bridge started on port: %s", port or "auto")

    def stop(self):
        """Stop serial bridge."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("Serial telemetry bridge stopped.")

    async def _read_loop(self):
        """Main non-blocking async serial reading loop."""
        import serial

        baud = settings.ESP32_SERIAL_TELEMETRY_BAUD

        while self._running:
            target_port = self._current_port
            if not target_port:
                ports = list_available_ports()
                candidates = [p["port"] for p in ports if p.get("is_esp_candidate")] or [p["port"] for p in ports]
                if candidates:
                    target_port = candidates[0]

            if not target_port:
                # No ports connected yet, retry in 3 seconds
                await asyncio.sleep(3.0)
                continue

            port_lock = get_port_lock(target_port)

            # Only read when port is not locked by an active flash operation
            if port_lock.locked():
                await asyncio.sleep(1.0)
                continue

            try:
                # Open serial port in non-blocking mode
                ser = serial.Serial(target_port, baud, timeout=1.0)
                logger.info("Connected to serial port %s at %d baud for telemetry ingestion", target_port, baud)

                while self._running:
                    # If flashing starts, release the serial port so esptool can flash
                    if port_lock.locked():
                        logger.info("Flash lock requested on %s, pausing serial telemetry reader", target_port)
                        ser.close()
                        await asyncio.sleep(2.0)
                        break

                    # Read a line from serial (in thread pool to prevent blocking asyncio loop)
                    line_bytes = await asyncio.to_thread(ser.readline)
                    if not line_bytes:
                        await asyncio.sleep(0.1)
                        continue

                    line_str = line_bytes.decode("utf-8", errors="replace").strip()
                    if not line_str:
                        continue

                    # Look for JSON formatted telemetry
                    if line_str.startswith("{") and line_str.endswith("}"):
                        try:
                            data = json.loads(line_str)
                            device_id = data.get("device_id")
                            if device_id:
                                # Ingest telemetry into database
                                async with async_session_factory() as db:
                                    # Extract metrics
                                    metrics: Dict[str, Any] = {}
                                    for key, val in data.items():
                                        if key not in ("schema_version", "device_id", "timestamp"):
                                            metrics[key] = val

                                    await telemetry_service.ingest_telemetry(
                                        db=db,
                                        device_id=device_id,
                                        readings=metrics,
                                    )
                                    logger.debug("Ingested cable telemetry for %s: %s", device_id, metrics)
                        except json.JSONDecodeError:
                            logger.debug("Non-JSON serial line received: %s", line_str)
                        except Exception as exc:
                            logger.warning("Error ingesting serial telemetry: %s", exc)

                if ser.is_open:
                    ser.close()

            except Exception as exc:
                # Could be device unplugged or port inaccessible
                logger.debug("Serial port %s disconnected or inaccessible: %s", target_port, exc)
                await asyncio.sleep(3.0)


serial_bridge = SerialTelemetryBridge()
