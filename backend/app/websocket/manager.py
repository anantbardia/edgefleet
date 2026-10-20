"""WebSocket connection manager for real-time dashboard events."""

import asyncio
import json
import logging
from typing import Any, Dict, Set

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("edgefleet.websocket")


class ConnectionManager:
    """Manages active WebSocket connections from web dashboards."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info("WebSocket connected. Active clients: %d", len(self.active_connections))

    async def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        async with self._lock:
            self.active_connections.discard(websocket)
        logger.info("WebSocket disconnected. Active clients: %d", len(self.active_connections))

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients."""
        if not self.active_connections:
            return

        payload = json.dumps(message)
        dead_connections = []

        async with self._lock:
            connections = list(self.active_connections)

        for connection in connections:
            try:
                await connection.send_text(payload)
            except Exception as exc:
                logger.debug("Failed sending to client: %s", exc)
                dead_connections.append(connection)

        if dead_connections:
            async with self._lock:
                for dead in dead_connections:
                    self.active_connections.discard(dead)

    async def broadcast_telemetry(self, device_id: str, readings: Dict[str, Any], timestamp: str, version: str):
        """Broadcast live telemetry reading."""
        await self.broadcast({
            "type": "telemetry",
            "device_id": device_id,
            "readings": readings,
            "timestamp": timestamp,
            "firmware_version": version,
        })

    async def broadcast_device_status(self, device_id: str, is_online: bool, **kwargs):
        """Broadcast device online/offline or heartbeat status."""
        data = {
            "type": "device_status",
            "device_id": device_id,
            "is_online": is_online,
            **kwargs,
        }
        await self.broadcast(data)

    async def broadcast_deployment(self, deployment_id: str, state: str, **kwargs):
        """Broadcast deployment state transition."""
        data = {
            "type": "deployment_update",
            "deployment_id": deployment_id,
            "state": state,
            **kwargs,
        }
        await self.broadcast(data)

    async def broadcast_alert(self, alert_dict: Dict[str, Any]):
        """Broadcast new alert."""
        await self.broadcast({
            "type": "alert",
            "alert": alert_dict,
        })


ws_manager = ConnectionManager()
