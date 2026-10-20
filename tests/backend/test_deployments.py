"""Tests for deployment management, preflight verification, and state transitions."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deployment import DeploymentJob
from app.models.firmware import FirmwareRelease


@pytest.mark.asyncio
async def test_deployment_preflight(
    client: AsyncClient, test_esp32_device, db_session: AsyncSession, operator_headers, admin_user
):
    # Create approved release
    rel = FirmwareRelease(
        version="1.1.0",
        mcu_family="esp32",
        target_boards=["esp32-wroom-32"],
        file_path="./test.bin",
        file_size=1024,
        sha256="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        is_approved=True,
        created_by=admin_user.id,
    )
    db_session.add(rel)
    await db_session.commit()

    resp = await client.post(
        "/api/deployments/preflight",
        json={"device_ids": [test_esp32_device.id], "release_id": rel.id},
        headers=operator_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["all_compatible"] is True
    assert "confirmation_token" in data
    assert len(data["results"]) == 1
    assert data["results"][0]["compatible"] is True


@pytest.mark.asyncio
async def test_deployment_creation_requires_valid_confirmation_token(
    client: AsyncClient, test_esp32_device, db_session: AsyncSession, operator_headers, admin_user
):
    # Unapproved release
    rel = FirmwareRelease(
        version="1.1.0",
        mcu_family="esp32",
        target_boards=["esp32-wroom-32"],
        file_path="./test_unapproved.bin",
        file_size=1024,
        sha256="1111111111111111111111111111111111111111111111111111111111111111",
        is_approved=False,
        created_by=admin_user.id,
    )
    db_session.add(rel)
    await db_session.commit()

    resp = await client.post(
        "/api/deployments",
        json={
            "device_ids": [test_esp32_device.id],
            "release_id": rel.id,
            "confirmation_token": "invalid_fake_token",
        },
        headers=operator_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_deployment_cancel_safe_vs_unsafe(
    client: AsyncClient, test_esp32_device, db_session: AsyncSession, operator_headers, admin_user
):
    # Create approved release
    rel = FirmwareRelease(
        version="1.2.0",
        mcu_family="esp32",
        target_boards=["esp32-wroom-32"],
        file_path="./test_cancel.bin",
        file_size=1024,
        sha256="2222222222222222222222222222222222222222222222222222222222222222",
        is_approved=True,
        created_by=admin_user.id,
    )
    db_session.add(rel)
    await db_session.commit()

    # 1. Safe cancel in queued state
    job1 = DeploymentJob(
        device_id=test_esp32_device.id,
        release_id=rel.id,
        state="queued",
        target_version="1.2.0",
        requested_by=admin_user.id,
    )
    db_session.add(job1)
    await db_session.commit()

    c_resp = await client.post(
        f"/api/deployments/{job1.id}/cancel",
        json={"reason": "Operator requested abort"},
        headers=operator_headers,
    )
    assert c_resp.status_code == 200
    assert c_resp.json()["message"] == "Deployment cancelled"

    # 2. Unsafe cancel in installing state
    job2 = DeploymentJob(
        device_id=test_esp32_device.id,
        release_id=rel.id,
        state="installing",
        target_version="1.2.0",
        requested_by=admin_user.id,
    )
    db_session.add(job2)
    await db_session.commit()

    unsafe_resp = await client.post(
        f"/api/deployments/{job2.id}/cancel",
        json={"reason": "Attempting abort during flash"},
        headers=operator_headers,
    )
    assert unsafe_resp.status_code == 409
