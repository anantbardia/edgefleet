"""Seed realistic demo dataset for EdgeFleet."""

import asyncio
import hashlib
import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.config import settings
from app.core.security import get_password_hash
from app.database.session import async_session_factory, init_db
from app.models.alert import Alert
from app.models.audit import AuditLog
from app.models.deployment import DeploymentAudit, DeploymentJob
from app.models.device import Device
from app.models.firmware import FirmwareRelease
from app.models.telemetry import TelemetryReading
from app.models.user import User


def create_dummy_firmware(filename: str, content: bytes) -> tuple[str, int, str]:
    storage_dir = Path(settings.FIRMWARE_STORAGE_PATH)
    storage_dir.mkdir(parents=True, exist_ok=True)
    file_path = storage_dir / filename
    with open(file_path, "wb") as f:
        f.write(content)
    size = len(content)
    sha256 = hashlib.sha256(content).hexdigest()
    return str(file_path.resolve()), size, sha256


async def seed_data():
    print("Initializing database schema...")
    await init_db()

    async with async_session_factory() as db:
        print("Seeding Users...")
        admin_user = User(
            id=str(uuid.uuid4()),
            email="admin@edgefleet.local",
            hashed_password=get_password_hash("adminpassword123"),
            full_name="Fleet Administrator",
            role="admin",
            is_active=True,
        )
        operator_user = User(
            id=str(uuid.uuid4()),
            email="operator@edgefleet.local",
            hashed_password=get_password_hash("operatorpassword123"),
            full_name="Operations Engineer",
            role="operator",
            is_active=True,
        )
        viewer_user = User(
            id=str(uuid.uuid4()),
            email="viewer@edgefleet.local",
            hashed_password=get_password_hash("viewerpassword123"),
            full_name="Dashboard Observer",
            role="viewer",
            is_active=True,
        )

        for u in [admin_user, operator_user, viewer_user]:
            db.add(u)
        await db.commit()

        print("Seeding Devices...")
        now = datetime.now(timezone.utc)
        dev1 = Device(
            id=str(uuid.uuid4()),
            device_id="esp32-001",
            name="ESP32 Lab Environment Node",
            mcu_family="esp32",
            board_variant="esp32-wroom-32",
            sensor_types={"temperature": "float", "humidity": "float", "hall_sensor": "int"},
            firmware_version="1.0.0",
            is_online=True,
            last_seen=now - timedelta(seconds=12),
            uptime_seconds=86400 * 3 + 1420,
            ip_address="192.168.1.101",
            registered_at=now - timedelta(days=30),
            metadata_extra={"location": "Lab Bench A", "zone": "Indoor"},
            description="Primary bench sensor node running ESP-IDF with dual partition OTA.",
        )
        dev2 = Device(
            id=str(uuid.uuid4()),
            device_id="esp32-002",
            name="ESP32 Production Line Sensor",
            mcu_family="esp32",
            board_variant="esp32-c3-super-mini",
            sensor_types={"temperature": "float", "humidity": "float", "vibration": "float"},
            firmware_version="1.1.0",
            is_online=True,
            last_seen=now - timedelta(seconds=4),
            uptime_seconds=86400 * 7 + 450,
            ip_address="192.168.1.102",
            registered_at=now - timedelta(days=20),
            metadata_extra={"location": "Factory Floor Line 2", "zone": "Industrial"},
            description="Industrial enclosure unit monitoring robotic packaging cell.",
        )
        dev3 = Device(
            id=str(uuid.uuid4()),
            device_id="esp32-003",
            name="ESP32 Warehouse Monitor",
            mcu_family="esp32",
            board_variant="esp32-c3-devkitm-1",
            sensor_types={"temperature": "float", "humidity": "float"},
            firmware_version="1.0.0",
            is_online=False,
            last_seen=now - timedelta(hours=4, minutes=12),
            uptime_seconds=1240,
            ip_address="192.168.1.103",
            registered_at=now - timedelta(days=15),
            metadata_extra={"location": "Warehouse Cold Storage 3", "zone": "Logistics"},
            description="Battery backup climate monitor in cold storage rack.",
        )
        dev4 = Device(
            id=str(uuid.uuid4()),
            device_id="uno-001",
            name="Arduino Uno Telemetry Logger",
            mcu_family="arduino_uno",
            board_variant="atmega328p",
            sensor_types={"light_lux": "float", "vcc_mv": "int"},
            firmware_version="0.9.0",
            is_online=True,
            last_seen=now - timedelta(seconds=2),
            uptime_seconds=3600 * 12 + 10,
            ip_address="serial:/dev/ttyACM0",
            serial_port="/dev/ttyACM0",
            registered_at=now - timedelta(days=45),
            metadata_extra={"baud": 115200},
            description="Legacy ATmega328P connected via USB serial to gateway.",
        )

        devices = [dev1, dev2, dev3, dev4]
        for d in devices:
            db.add(d)
        await db.commit()

        print("Seeding Firmware Releases with real disk files...")
        esp_dummy = b"\x20\x00\x00\x00" + b"ESP32-APP-FIRMWARE-IMAGE-V1.1.0" * 2000
        esp_v2_dummy = b"\x20\x00\x00\x00" + b"ESP32-APP-FIRMWARE-IMAGE-V2.0.0" * 3000
        uno_dummy = b":100000000C945C000C946E000C946E000C946E0020\r\n:00000001FF\r\n"

        p1, sz1, h1 = create_dummy_firmware("esp32_1_1_0.bin", esp_dummy)
        p2, sz2, h2 = create_dummy_firmware("esp32_2_0_0.bin", esp_v2_dummy)
        p3, sz3, h3 = create_dummy_firmware("uno_1_0_0.hex", uno_dummy)

        rel1 = FirmwareRelease(
            id=str(uuid.uuid4()),
            version="1.1.0",
            mcu_family="esp32",
            target_boards=["esp32-wroom-32", "esp32-c3-devkitm-1", "esp32-c3-super-mini"],
            file_path=p1,
            file_size=sz1,
            sha256=h1,
            build_id="bld-20261015-01",
            release_notes="Enhanced Wi-Fi reconnection logic and low-power MQTT keepalives.",
            is_approved=True,
            created_at=now - timedelta(days=4),
            created_by=admin_user.id,
            original_filename="esp32_1_1_0.bin",
        )
        rel2 = FirmwareRelease(
            id=str(uuid.uuid4()),
            version="2.0.0",
            mcu_family="esp32",
            target_boards=["esp32-wroom-32", "esp32-s3-wroom-1", "esp32-c3-devkitm-1"],
            file_path=p2,
            file_size=sz2,
            sha256=h2,
            build_id="bld-20261019-01",
            release_notes="Major OTA update: TLS 1.3 support, MQTT 5, and dual partition fallback safety.",
            is_approved=True,
            created_at=now - timedelta(days=1),
            created_by=admin_user.id,
            original_filename="esp32_2_0_0.bin",
        )
        rel3 = FirmwareRelease(
            id=str(uuid.uuid4()),
            version="1.0.0",
            mcu_family="arduino_uno",
            target_boards=["atmega328p", "uno"],
            file_path=p3,
            file_size=sz3,
            sha256=h3,
            build_id="bld-uno-20261010-01",
            release_notes="Ring buffer optimization and 115200 baud streaming stability.",
            is_approved=True,
            created_at=now - timedelta(days=10),
            created_by=admin_user.id,
            original_filename="uno_1_0_0.hex",
        )

        for r in [rel1, rel2, rel3]:
            db.add(r)
        await db.commit()

        print("Seeding Historical Telemetry...")
        readings = []
        for i in range(100):
            t_offset = timedelta(minutes=(100 - i) * 15)
            ts = now - t_offset

            # ESP32-001
            readings.append(
                TelemetryReading(
                    device_id=dev1.id,
                    schema_version="1.0",
                    firmware_version="1.0.0",
                    readings={
                        "temperature": round(23.5 + random.uniform(-1.5, 2.0), 2),
                        "humidity": round(52.0 + random.uniform(-4.0, 5.0), 1),
                        "heap_free": random.randint(150000, 165000),
                        "wifi_rssi": random.randint(-65, -55),
                    },
                    timestamp=ts,
                )
            )
            # ESP32-002
            readings.append(
                TelemetryReading(
                    device_id=dev2.id,
                    schema_version="1.0",
                    firmware_version="1.1.0",
                    readings={
                        "temperature": round(28.2 + random.uniform(-2.0, 3.0), 2),
                        "humidity": round(46.0 + random.uniform(-3.0, 4.0), 1),
                        "heap_free": random.randint(170000, 182000),
                        "wifi_rssi": random.randint(-70, -60),
                    },
                    timestamp=ts,
                )
            )
            # Uno-001
            readings.append(
                TelemetryReading(
                    device_id=dev4.id,
                    schema_version="1.0",
                    firmware_version="0.9.0",
                    readings={
                        "light_lux": round(450.0 + random.uniform(-50.0, 80.0), 1),
                        "vcc_mv": random.randint(4980, 5020),
                    },
                    timestamp=ts,
                )
            )
        db.add_all(readings)
        await db.commit()

        print("Seeding Deployments and Audits...")
        dep1 = DeploymentJob(
            id=str(uuid.uuid4()),
            device_id=dev2.id,
            release_id=rel1.id,
            state="success",
            source_version="1.0.0",
            target_version="1.1.0",
            requested_by=admin_user.id,
            started_at=now - timedelta(days=2, hours=1),
            completed_at=now - timedelta(days=2, hours=1, seconds=-45),
            verification_evidence={"version_verified": True, "sha256": rel1.sha256},
            progress_details={"active_partition": "ota_1", "bytes_flashed": rel1.file_size},
        )
        db.add(dep1)
        await db.commit()

        audit1 = DeploymentAudit(
            deployment_id=dep1.id,
            timestamp=now - timedelta(days=2, hours=1),
            event_type="STATE_CHANGE_SUCCESS",
            old_state="health_check",
            new_state="success",
            details={"final_version": "1.1.0"},
        )
        db.add(audit1)

        print("Seeding Alerts...")
        alerts = [
            Alert(
                id=str(uuid.uuid4()),
                device_id=dev3.id,
                alert_type="device_offline",
                severity="warning",
                message="Device esp32-003 timed out (no heartbeat for >90s).",
                acknowledged=False,
                created_at=now - timedelta(hours=4),
            ),
            Alert(
                id=str(uuid.uuid4()),
                device_id=dev1.id,
                alert_type="sensor_error",
                severity="info",
                message="Temperature fluctuation detected (+2.3°C above baseline).",
                acknowledged=True,
                created_at=now - timedelta(days=1),
                acknowledged_at=now - timedelta(hours=20),
                acknowledged_by=admin_user.id,
            ),
        ]
        db.add_all(alerts)
        await db.commit()

        print("Seeding complete! Database is populated with rich demo data.")


if __name__ == "__main__":
    asyncio.run(seed_data())
