"""Tests for device inventory and management."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_devices(client: AsyncClient, test_esp32_device, viewer_headers):
    resp = await client.get("/api/devices", headers=viewer_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(d["device_id"] == "esp32-test-01" for d in data["items"])


@pytest.mark.asyncio
async def test_get_device_detail(client: AsyncClient, test_esp32_device, viewer_headers):
    resp = await client.get(f"/api/devices/{test_esp32_device.device_id}", headers=viewer_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["device_id"] == test_esp32_device.device_id
    assert data["mcu_family"] == "esp32"


@pytest.mark.asyncio
async def test_register_device_admin(client: AsyncClient, admin_headers):
    payload = {
        "device_id": "esp32-created",
        "name": "Created ESP32",
        "mcu_family": "esp32",
        "board_variant": "esp32-c3-devkitm-1",
    }
    resp = await client.post("/api/devices", json=payload, headers=admin_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["device_id"] == "esp32-created"


@pytest.mark.asyncio
async def test_update_device_metadata(client: AsyncClient, test_esp32_device, operator_headers):
    payload = {"name": "Renamed Node"}
    resp = await client.patch(
        f"/api/devices/{test_esp32_device.device_id}",
        json=payload,
        headers=operator_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed Node"
