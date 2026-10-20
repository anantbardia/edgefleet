"""Tests for firmware upload, validation, hashing, and approvals."""

import io
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_upload_firmware_success(client: AsyncClient, operator_headers):
    dummy_bin = b"\x00\x11\x22\x33" * 256
    files = {"file": ("firmware_v1.bin", io.BytesIO(dummy_bin), "application/octet-stream")}
    data = {
        "version": "1.0.0",
        "mcu_family": "esp32",
        "target_boards": '["esp32-wroom-32"]',
        "release_notes": "Initial release test",
    }

    resp = await client.post(
        "/api/firmware/upload",
        files=files,
        data=data,
        headers=operator_headers,
    )
    assert resp.status_code == 201
    res_data = resp.json()
    assert res_data["version"] == "1.0.0"
    assert res_data["is_approved"] is False
    assert len(res_data["sha256"]) == 64


@pytest.mark.asyncio
async def test_upload_invalid_extension(client: AsyncClient, operator_headers):
    dummy_file = b"not_a_binary"
    files = {"file": ("firmware.txt", io.BytesIO(dummy_file), "text/plain")}
    data = {
        "version": "1.0.0",
        "mcu_family": "esp32",
        "target_boards": '["esp32-wroom-32"]',
    }

    resp = await client.post(
        "/api/firmware/upload",
        files=files,
        data=data,
        headers=operator_headers,
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_approve_firmware_admin_only(client: AsyncClient, operator_headers, admin_headers):
    # Upload first
    dummy_bin = b"\xAA\xBB\xCC\xDD" * 128
    files = {"file": ("app_v2.bin", io.BytesIO(dummy_bin), "application/octet-stream")}
    data = {
        "version": "2.0.0",
        "mcu_family": "esp32",
        "target_boards": '["esp32-wroom-32"]',
    }
    up_resp = await client.post(
        "/api/firmware/upload",
        files=files,
        data=data,
        headers=operator_headers,
    )
    rel_id = up_resp.json()["id"]

    # Operator cannot approve
    patch_resp = await client.patch(
        f"/api/firmware/{rel_id}",
        json={"is_approved": True},
        headers=operator_headers,
    )
    assert patch_resp.status_code == 403

    # Admin can approve
    app_resp = await client.patch(
        f"/api/firmware/{rel_id}",
        json={"is_approved": True},
        headers=admin_headers,
    )
    assert app_resp.status_code == 200
    assert app_resp.json()["is_approved"] is True
