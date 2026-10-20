"""Pytest fixtures and test environment setup."""

import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.core.security import create_access_token, get_password_hash
from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.models.device import Device
from app.models.firmware import FirmwareRelease
from app.models.user import User

from sqlalchemy.pool import StaticPool
import app.database.session as session_module
import app.mqtt.handlers as mqtt_handlers_module
import app.services.deployment_service as dep_service_module

# In-memory shared SQLite for tests with StaticPool
TEST_DB_URL = "sqlite+aiosqlite:///?check_same_thread=False"

test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)
test_session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

# Override global async_session_factory so handlers use the test database
session_module.async_session_factory = test_session_factory
mqtt_handlers_module.async_session_factory = test_session_factory
dep_service_module.async_session_factory = test_session_factory


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide clean database session for each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_session_factory() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP client with test database override."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def admin_user(db_session: AsyncSession) -> User:
    """Create and return an admin user."""
    user = User(
        email="test_admin@example.com",
        hashed_password=get_password_hash("testpass123"),
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def operator_user(db_session: AsyncSession) -> User:
    """Create and return an operator user."""
    user = User(
        email="test_operator@example.com",
        hashed_password=get_password_hash("testpass123"),
        role="operator",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def viewer_user(db_session: AsyncSession) -> User:
    """Create and return a viewer user."""
    user = User(
        email="test_viewer@example.com",
        hashed_password=get_password_hash("testpass123"),
        role="viewer",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user



@pytest.fixture
def admin_headers(admin_user: User) -> dict:
    token = create_access_token({"sub": admin_user.id, "email": admin_user.email, "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def operator_headers(operator_user: User) -> dict:
    token = create_access_token({"sub": operator_user.id, "email": operator_user.email, "role": "operator"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def viewer_headers(viewer_user: User) -> dict:
    token = create_access_token({"sub": viewer_user.id, "email": viewer_user.email, "role": "viewer"})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(scope="function")
async def test_esp32_device(db_session: AsyncSession) -> Device:
    """Create a sample ESP32 device."""
    dev = Device(
        device_id="esp32-test-01",
        name="Test ESP32",
        mcu_family="esp32",
        board_variant="esp32-wroom-32",
        firmware_version="1.0.0",
        is_online=True,
    )
    db_session.add(dev)
    await db_session.commit()
    await db_session.refresh(dev)
    return dev


@pytest_asyncio.fixture(scope="function")
async def test_uno_device(db_session: AsyncSession) -> Device:
    """Create a sample Arduino Uno device."""
    dev = Device(
        device_id="uno-test-01",
        name="Test Arduino Uno",
        mcu_family="arduino_uno",
        board_variant="atmega328p",
        firmware_version="1.0.0",
        serial_port="/dev/ttyACM0",
        is_online=True,
    )
    db_session.add(dev)
    await db_session.commit()
    await db_session.refresh(dev)
    return dev
