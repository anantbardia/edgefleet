"""Mock IoT Device Simulator for EdgeFleet.

Simulates ESP32 and Arduino Uno devices publishing realistic sensor telemetry,
handling status heartbeats, and responding to OTA firmware update commands.
All data is clearly tagged as simulated/mock.
"""

import argparse
import json
import logging
import random
import signal
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

import paho.mqtt.client as mqtt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [MOCK-DEVICE]: %(message)s",
)
logger = logging.getLogger("mock_device")


class MockDevice:
    def __init__(
        self,
        device_id: str,
        name: str,
        mcu_family: str,
        board_variant: str,
        firmware_version: str,
        ip_address: str,
    ):
        self.device_id = device_id
        self.name = name
        self.mcu_family = mcu_family
        self.board_variant = board_variant
        self.firmware_version = firmware_version
        self.ip_address = ip_address
        self.uptime = random.randint(1000, 50000)
        self.is_updating = False

        # Sensor state baselines for continuous smooth drift
        self.temp = random.uniform(22.0, 26.0)
        self.humidity = random.uniform(45.0, 65.0)

    def step_telemetry(self) -> Dict[str, Any]:
        self.uptime += 5
        # Smooth random walk
        self.temp += random.uniform(-0.3, 0.3)
        self.temp = max(15.0, min(38.0, self.temp))
        self.humidity += random.uniform(-0.5, 0.5)
        self.humidity = max(20.0, min(95.0, self.humidity))

        readings: Dict[str, Any] = {
            "temperature": round(self.temp, 2),
            "humidity": round(self.humidity, 2),
            "is_mock": True,
        }

        if self.mcu_family == "esp32":
            readings.update({
                "heap_free": random.randint(140000, 180000),
                "wifi_rssi": random.randint(-72, -45),
                "cpu_freq_mhz": 240,
                "hall_sensor": random.randint(10, 40),
            })
        else:
            readings.update({
                "light_lux": round(random.uniform(200.0, 850.0), 1),
                "vcc_mv": random.randint(4950, 5050),
                "loop_latency_us": random.randint(120, 350),
            })

        return {
            "schema_version": "1.0",
            "device_id": self.device_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "firmware_version": self.firmware_version,
            "readings": readings,
        }

    def get_status_payload(self, is_online: bool = True) -> Dict[str, Any]:
        return {
            "schema_version": "1.0",
            "device_id": self.device_id,
            "status": "online" if is_online else "offline",
            "firmware_version": self.firmware_version,
            "uptime_seconds": self.uptime,
            "ip_address": self.ip_address,
            "reset_reason": "power_on",
            "is_mock": True,
        }


class Simulator:
    def __init__(self, broker: str, port: int, interval: float, with_failures: bool = False):
        self.broker = broker
        self.port = port
        self.interval = interval
        self.with_failures = with_failures
        self.running = True

        self.devices: List[MockDevice] = [
            MockDevice("esp32-001", "ESP32 Lab Environment Node", "esp32", "esp32-wroom-32", "1.0.0", "192.168.1.101"),
            MockDevice("esp32-002", "ESP32 Production Line Sensor", "esp32", "esp32-c3-super-mini", "1.1.0", "192.168.1.102"),
            MockDevice("esp32-003", "ESP32 Warehouse Monitor", "esp32", "esp32-c3-devkitm-1", "1.0.0", "192.168.1.103"),
            MockDevice("uno-001", "Arduino Uno Telemetry Logger", "arduino_uno", "atmega328p", "0.9.0", "serial:/dev/ttyACM0"),
        ]

        # Use Callback API v2 compatibility
        try:
            self.client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id="edgefleet-mock-device-simulator",
            )
        except AttributeError:
            self.client = mqtt.Client(client_id="edgefleet-mock-device-simulator")

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        rc_code = rc if isinstance(rc, int) else getattr(rc, "value", 0)
        if rc_code == 0:
            logger.info("Connected to MQTT broker at %s:%d", self.broker, self.port)
            for dev in self.devices:
                cmd_topic = f"edgefleet/v1/devices/{dev.device_id}/commands"
                client.subscribe(cmd_topic, qos=1)
                logger.info("[%s] Subscribed to commands on %s", dev.device_id, cmd_topic)

                # Publish online status
                st_topic = f"edgefleet/v1/devices/{dev.device_id}/status"
                client.publish(st_topic, json.dumps(dev.get_status_payload(True)), qos=1, retain=True)
        else:
            logger.error("Connection failed with return code %s", rc)

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            logger.info("Received command on %s: %s", msg.topic, payload)

            cmd = payload.get("command")
            if cmd == "ota_update":
                device_id = payload.get("target_device")
                dep_id = payload.get("deployment_id")
                target_ver = payload.get("expected_version", "2.0.0")

                dev = next((d for d in self.devices if d.device_id == device_id), None)
                if not dev:
                    logger.warning("OTA command received for unknown device %s", device_id)
                    return

                # Spawn background simulated OTA update thread
                import threading
                t = threading.Thread(
                    target=self._simulate_ota_sequence,
                    args=(dev, dep_id, target_ver),
                    daemon=True,
                )
                t.start()

        except Exception as exc:
            logger.exception("Error handling mock command: %s", exc)

    def _simulate_ota_sequence(self, dev: MockDevice, dep_id: str, new_ver: str):
        dev.is_updating = True
        status_topic = f"edgefleet/v1/devices/{dev.device_id}/update/status"
        logger.info("[%s] [MOCK OTA] Starting OTA update sequence to version %s...", dev.device_id, new_ver)

        def emit(stage: str, status: str = "in_progress", detail: dict | None = None, err: str | None = None):
            body = {
                "schema_version": "1.0",
                "device_id": dev.device_id,
                "deployment_id": dep_id,
                "stage": stage,
                "status": status,
                "detail": detail or {},
                "error": err,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self.client.publish(status_topic, json.dumps(body), qos=1)
            logger.info("[%s] [MOCK OTA] Stage: %s (%s)", dev.device_id, stage, status)

        try:
            time.sleep(1.2)
            emit("VERIFYING", "in_progress", {"sha256_match": True, "downloaded_bytes": 1048576})
            time.sleep(1.5)
            emit("INSTALLING", "in_progress", {"partition": "ota_1", "bytes_flashed": 1048576})
            time.sleep(1.2)
            emit("REBOOTING", "in_progress", {"action": "esp_restart"})
            time.sleep(1.5)
            emit("HEALTH_CHECK", "in_progress", {"version": new_ver, "self_test": "pass"})
            time.sleep(0.8)

            # Success
            dev.firmware_version = new_ver
            emit("SUCCESS", "success", {"final_version": new_ver})

            # Broadcast new status with new version
            st_topic = f"edgefleet/v1/devices/{dev.device_id}/status"
            self.client.publish(st_topic, json.dumps(dev.get_status_payload(True)), qos=1, retain=True)
            logger.info("[%s] [MOCK OTA] Update completed successfully! Now running %s", dev.device_id, new_ver)

        except Exception as exc:
            emit("FAILED", "failed", err=str(exc))
        finally:
            dev.is_updating = False

    def run(self):
        try:
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
        except Exception as exc:
            logger.warning("Could not connect to broker (%s). Running in loopback mode.", exc)

        logger.info("Mock Device Simulator running. Simulating %d devices every %.1fs. Press Ctrl+C to stop.", len(self.devices), self.interval)

        while self.running:
            try:
                for dev in self.devices:
                    if dev.is_updating:
                        continue

                    telemetry = dev.step_telemetry()
                    topic = f"edgefleet/v1/devices/{dev.device_id}/telemetry"
                    self.client.publish(topic, json.dumps(telemetry), qos=0)

                time.sleep(self.interval)
            except KeyboardInterrupt:
                break
            except Exception as exc:
                logger.error("Simulation loop error: %s", exc)
                time.sleep(self.interval)

        logger.info("Stopping mock devices, sending offline LWT...")
        for dev in self.devices:
            st_topic = f"edgefleet/v1/devices/{dev.device_id}/status"
            self.client.publish(st_topic, json.dumps(dev.get_status_payload(False)), qos=1)

        self.client.loop_stop()
        self.client.disconnect()
        logger.info("Mock simulator shutdown complete.")


def main():
    parser = argparse.ArgumentParser(description="EdgeFleet Mock IoT Device Simulator")
    parser.add_argument("--broker", default="localhost", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--interval", type=float, default=5.0, help="Publish interval in seconds")
    parser.add_argument("--with-failures", action="store_true", help="Simulate intermittent faults")

    args = parser.parse_args()
    sim = Simulator(args.broker, args.port, args.interval, args.with_failures)

    def handle_sig(sig, frame):
        sim.running = False

    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGTERM, handle_sig)

    sim.run()


if __name__ == "__main__":
    main()
