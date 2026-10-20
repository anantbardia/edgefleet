"""Unit and integration tests for hardware deployment adapters, including ESP32 serial cable flashing."""

import hashlib
import os
import tempfile
import pytest
from httpx import AsyncClient

from app.device_adapters import (
    ESP32SerialAdapter,
    esp32_serial_adapter,
    ESP32OTAAdapter,
    esp32_adapter,
    ArduinoUnoAdapter,
    arduino_adapter,
    list_available_ports,
)
from app.models.deployment import DeploymentJob
from app.models.device import Device
from app.models.firmware import FirmwareRelease
from app.services.deployment_service import deployment_service


@pytest.mark.asyncio
async def test_list_available_ports():
    """Verify list_available_ports returns a valid list structure."""
    ports = list_available_ports()
    assert isinstance(ports, list)
    for p in ports:
        assert "port" in p
        assert "description" in p
        assert "is_esp_candidate" in p
        assert "is_arduino_candidate" in p


@pytest.mark.asyncio
async def test_get_serial_ports_endpoint(client: AsyncClient, viewer_headers: dict):
    """Verify GET /api/devices/ports/serial returns port listing."""
    resp = await client.get("/api/devices/ports/serial", headers=viewer_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_esp32_serial_adapter_preflight():
    """Test ESP32SerialAdapter preflight checks for compatibility and warnings."""
    adapter = ESP32SerialAdapter()

    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        f.write(b"mock_esp32_binary_data")
        temp_bin_path = f.name

    try:
        release = FirmwareRelease(
            id="rel-esp-1",
            version="1.0.1",
            mcu_family="esp32",
            target_boards=["esp32-wroom-32"],
            file_path=temp_bin_path,
            file_size=len(b"mock_esp32_binary_data"),
            sha256=hashlib.sha256(b"mock_esp32_binary_data").hexdigest(),
        )

        # 1. Matching MCU with configured port
        dev_matching = Device(
            device_id="esp-cable-01",
            name="Test ESP",
            mcu_family="esp32",
            board_variant="esp32-wroom-32",
            serial_port="COM3",
        )
        compat, warnings = await adapter.preflight_check(dev_matching, release)
        assert compat is True

        # 2. Incompatible MCU
        dev_uno = Device(
            device_id="uno-01",
            name="Uno Test",
            mcu_family="arduino_uno",
            board_variant="atmega328p",
        )
        compat_uno, warnings_uno = await adapter.preflight_check(dev_uno, release)
        assert compat_uno is False
        assert any("Device MCU is arduino_uno" in msg for msg in warnings_uno)

        # 3. Missing binary file
        release_missing = FirmwareRelease(
            id="rel-esp-2",
            version="1.0.2",
            mcu_family="esp32",
            target_boards=["esp32-wroom-32"],
            file_path="/nonexistent/firmware.bin",
            file_size=100,
            sha256="abc",
        )
        compat_missing, warnings_missing = await adapter.preflight_check(dev_matching, release_missing)
        assert compat_missing is False
        assert any("not found" in msg for msg in warnings_missing)

    finally:
        if os.path.exists(temp_bin_path):
            os.remove(temp_bin_path)


@pytest.mark.asyncio
async def test_esp32_serial_adapter_execute_simulated():
    """Verify ESP32SerialAdapter executes full state machine lifecycle in simulated mode."""
    content = b"ESP32_APP_BINARY_PAYLOAD_TEST_123456"
    sha = hashlib.sha256(content).hexdigest()

    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        f.write(content)
        temp_bin_path = f.name

    try:
        release = FirmwareRelease(
            id="rel-sim-1",
            version="2.0.0",
            mcu_family="esp32",
            target_boards=["esp32-wroom-32"],
            file_path=temp_bin_path,
            file_size=len(content),
            sha256=sha,
        )

        device = Device(
            device_id="esp-sim-node",
            name="Simulated ESP32",
            mcu_family="esp32",
            board_variant="esp32-wroom-32",
            serial_port="COM99",  # Virtual / simulated port
        )

        job = DeploymentJob(
            id="job-sim-001",
            device_id="esp-sim-node",
            release_id="rel-sim-1",
            target_version="2.0.0",
            state="PREFLIGHT",
        )

        captured_stages = []
        captured_details = []

        async def mock_progress_callback(stage: str, details=None, failure_reason=None):
            captured_stages.append(stage)
            if details:
                captured_details.append(details)

        success = await esp32_serial_adapter.execute_deployment(
            job=job,
            device=device,
            release=release,
            on_progress=mock_progress_callback,
        )

        assert success is True
        # Check that state machine executed required progression
        expected_sequence = ["TRANSFERRING", "VERIFYING", "INSTALLING", "REBOOTING", "HEALTH_CHECK", "SUCCESS"]
        assert captured_stages == expected_sequence

        # Verify evidence in SUCCESS stage
        success_detail = captured_details[-1]
        assert success_detail["connection"] == "usb_serial"
        assert success_detail["programmer"] == "esptool"
        assert success_detail["port"] == "COM99"
        assert success_detail["final_version"] == "2.0.0"
        assert success_detail["verification_evidence"]["sha256"] == sha
        assert success_detail["verification_evidence"]["esptool_exit_code"] == 0

    finally:
        if os.path.exists(temp_bin_path):
            os.remove(temp_bin_path)


@pytest.mark.asyncio
async def test_deployment_service_adapter_routing():
    """Verify DeploymentService routes to ESP32SerialAdapter when serial_port is present."""
    # ESP32 with cable/serial port configured
    esp_cable = Device(
        device_id="esp-cable",
        name="Cable ESP",
        mcu_family="esp32",
        serial_port="COM4",
    )
    adapter_cable = deployment_service.get_adapter_for_device(esp_cable)
    assert isinstance(adapter_cable, ESP32SerialAdapter)

    # ESP32 without serial port (Wi-Fi OTA)
    esp_wifi = Device(
        device_id="esp-wifi",
        name="Wireless ESP",
        mcu_family="esp32",
        serial_port=None,
    )
    adapter_wifi = deployment_service.get_adapter_for_device(esp_wifi)
    assert isinstance(adapter_wifi, ESP32OTAAdapter)

    # Arduino Uno (always serial adapter)
    uno = Device(
        device_id="uno-node",
        name="Uno Node",
        mcu_family="arduino_uno",
        serial_port="COM5",
    )
    adapter_uno = deployment_service.get_adapter_for_device(uno)
    assert isinstance(adapter_uno, ArduinoUnoAdapter)
