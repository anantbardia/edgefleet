"""Paho MQTT client wrapper with background thread and async event dispatch."""

import asyncio
import json
import logging
from typing import Any, Dict, Optional

import paho.mqtt.client as mqtt

from app.config import settings
from app.mqtt import handlers
from app.mqtt.topics import (
    EVENTS_TOPIC,
    STATUS_TOPIC,
    TELEMETRY_TOPIC,
    UPDATE_STATUS_TOPIC,
    make_command_topic,
    parse_topic,
)

logger = logging.getLogger("edgefleet.mqtt")


class MQTTClient:
    """Manages the MQTT connection, topic subscriptions, and message routing."""

    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._connected = False

    def start(self, loop: asyncio.AbstractEventLoop):
        """Initialize and start the MQTT client in a background network loop."""
        self._loop = loop

        # Callback API v2 compatibility
        try:
            self.client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id=settings.MQTT_CLIENT_ID,
            )
        except AttributeError:
            self.client = mqtt.Client(client_id=settings.MQTT_CLIENT_ID)

        if settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
            self.client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        try:
            logger.info("Connecting to MQTT broker at %s:%s", settings.MQTT_HOST, settings.MQTT_PORT)
            self.client.connect_async(settings.MQTT_HOST, settings.MQTT_PORT, keepalive=60)
            self.client.loop_start()
        except Exception as exc:
            logger.warning(
                "MQTT connection initiation failed: %s. Continuing in offline/mock mode.", exc
            )

    def stop(self):
        """Stop background network loop and disconnect."""
        if self.client:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except Exception as exc:
                logger.debug("Error stopping MQTT client: %s", exc)
        self._connected = False

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        rc_code = rc if isinstance(rc, int) else getattr(rc, "value", 0)
        if rc_code == 0:
            self._connected = True
            logger.info("Connected to MQTT broker successfully.")
            # Subscribe to all edgefleet device channels
            client.subscribe(TELEMETRY_TOPIC, qos=1)
            client.subscribe(STATUS_TOPIC, qos=1)
            client.subscribe(EVENTS_TOPIC, qos=1)
            client.subscribe(UPDATE_STATUS_TOPIC, qos=1)
            logger.info("Subscribed to MQTT topics.")
        else:
            self._connected = False
            logger.error("Failed to connect to MQTT broker, return code: %s", rc)

    def _on_disconnect(self, client, userdata, rc, properties=None, disconnect_flags=None):
        self._connected = False
        logger.warning("Disconnected from MQTT broker (code: %s)", rc)

    def _on_message(self, client, userdata, msg):
        """Route received MQTT message to appropriate async handler."""
        if not self._loop or not self._loop.is_running():
            return

        try:
            topic = msg.topic
            parsed = parse_topic(topic)
            if not parsed:
                return

            device_id, msg_type = parsed
            raw_payload = msg.payload.decode("utf-8", errors="replace")
            payload = json.loads(raw_payload)

            if msg_type == "telemetry":
                asyncio.run_coroutine_threadsafe(
                    handlers.handle_telemetry(device_id, payload), self._loop
                )
            elif msg_type == "status":
                asyncio.run_coroutine_threadsafe(
                    handlers.handle_status(device_id, payload), self._loop
                )
            elif msg_type == "events":
                asyncio.run_coroutine_threadsafe(
                    handlers.handle_events(device_id, payload), self._loop
                )
            elif msg_type == "update_status":
                asyncio.run_coroutine_threadsafe(
                    handlers.handle_update_status(device_id, payload), self._loop
                )

        except json.JSONDecodeError:
            logger.warning("Received invalid JSON payload on %s", msg.topic)
        except Exception as exc:
            logger.exception("Error processing message on %s: %s", msg.topic, exc)

    def publish_command(self, device_id: str, command: Dict[str, Any]) -> bool:
        """Publish a command to the device's command topic."""
        if not self.client or not self._connected:
            logger.warning("Cannot publish command to %s: MQTT client not connected", device_id)
            return False

        topic = make_command_topic(device_id)
        payload = json.dumps(command)
        res = self.client.publish(topic, payload, qos=1)
        return res.rc == mqtt.MQTT_ERR_SUCCESS

    @property
    def is_connected(self) -> bool:
        return self._connected


mqtt_client = MQTTClient()
