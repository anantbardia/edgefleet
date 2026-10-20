"""Tests for authentication and role-based access control."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, admin_user):
    resp = await client.post(
        "/api/auth/login",
        json={"email": "test_admin@example.com", "password": "testpass123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, admin_user):
    resp = await client.post(
        "/api/auth/login",
        json={"email": "test_admin@example.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_auth_me(client: AsyncClient, admin_headers):
    resp = await client.get("/api/auth/me", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test_admin@example.com"
    assert data["role"] == "admin"



@pytest.mark.asyncio
async def test_rbac_restrictions(client: AsyncClient, viewer_headers, operator_headers):
    # Viewer cannot register a device (admin only)
    resp = await client.post(
        "/api/devices",
        json={"device_id": "esp32-new", "name": "New Node", "mcu_family": "esp32"},
        headers=viewer_headers,
    )
    assert resp.status_code == 403

    # Operator cannot register a device (admin only)
    resp = await client.post(
        "/api/devices",
        json={"device_id": "esp32-new", "name": "New Node", "mcu_family": "esp32"},
        headers=operator_headers,
    )
    assert resp.status_code == 403
