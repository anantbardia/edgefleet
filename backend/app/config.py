"""Application configuration loaded from environment variables."""

from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _BACKEND_DIR.parent
_ENV_FILE = None
if (_PROJECT_ROOT / ".env").is_file():
    _ENV_FILE = str(_PROJECT_ROOT / ".env")
elif (_BACKEND_DIR / ".env").is_file():
    _ENV_FILE = str(_BACKEND_DIR / ".env")
elif Path("/opt/edgefleet/.env").is_file():
    _ENV_FILE = "/opt/edgefleet/.env"


class Settings(BaseSettings):
    """EdgeFleet application settings.

    All values can be overridden via environment variables or a .env file.
    """

    # ── Application ──────────────────────────────────────────────────────
    APP_NAME: str = "EdgeFleet"
    APP_VERSION: str = "0.1.0"
    SECRET_KEY: str = "CHANGE_ME_GENERATE_A_STRONG_SECRET"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # ── Database ─────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./edgefleet.db"

    # ── MQTT ─────────────────────────────────────────────────────────────
    MQTT_HOST: str = "localhost"
    MQTT_PORT: int = 1883
    MQTT_USERNAME: str = ""
    MQTT_PASSWORD: str = ""
    MQTT_CLIENT_ID: str = "edgefleet-backend"

    # ── Authentication ───────────────────────────────────────────────────
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ADMIN_EMAIL: str = "admin@edgefleet.local"

    # ── Firmware Storage ─────────────────────────────────────────────────
    FIRMWARE_STORAGE_PATH: str = "./firmware_storage"
    MAX_UPLOAD_SIZE_MB: int = 16

    # ── CORS ─────────────────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # ── Telemetry ────────────────────────────────────────────────────────
    TELEMETRY_RETENTION_DAYS: int = 30
    HEARTBEAT_TIMEOUT_SECONDS: int = 90

    # ── Deployment ───────────────────────────────────────────────────────
    DEPLOYMENT_CONCURRENCY_LIMIT: int = 1
    DEPLOYMENT_TIMEOUT_SECONDS: int = 300

    # ── Arduino ──────────────────────────────────────────────────────────
    AVRDUDE_PATH: str = "/usr/bin/avrdude"
    ARDUINO_SERIAL_PORT_PATTERNS: str = "/dev/ttyACM*,/dev/ttyUSB*"

    # ── ESP32 Serial / Cable ─────────────────────────────────────────────
    ESP32_SERIAL_PORT_PATTERNS: str = "/dev/ttyUSB*,/dev/ttyACM*,COM*"
    ESP32_SERIAL_BAUD_RATE: int = 460800
    ESP32_SERIAL_APP_OFFSET: str = "0x10000"
    ESP32_SERIAL_CHIP: str = "auto"
    ESP32_SERIAL_TELEMETRY_BAUD: int = 115200

    # ── Cloud Sync ───────────────────────────────────────────────────────
    CLOUD_ENABLED: bool = False
    CLOUD_API_URL: str = ""
    CLOUD_API_KEY: str = ""
    CLOUD_SYNC_INTERVAL_SECONDS: int = 60
    CLOUD_SYNC_MAX_RETRIES: int = 10
    CLOUD_SYNC_QUEUE_MAX_SIZE: int = 10000
    CLOUD_SYNC_RETENTION_DAYS: int = 7

    # ── Mock Mode ────────────────────────────────────────────────────────
    MOCK_MODE: bool = False

    @property
    def cors_origin_list(self) -> List[str]:
        """Parse CORS_ORIGINS into a list."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def firmware_storage(self) -> Path:
        """Resolved firmware storage path."""
        p = Path(self.FIRMWARE_STORAGE_PATH)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    model_config = {"env_file": _ENV_FILE, "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
