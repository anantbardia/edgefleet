# EdgeFleet — Distributed IoT Monitoring and Secure FOTA

> **Lightweight, industrial-grade IoT gateway platform engineered for the Raspberry Pi 4 (2 GB RAM).**  
> Supports Wi-Fi dual-partition OTA & direct USB cable flashing (`esptool`) for **ESP32** nodes, USB serial flashing for **Arduino Uno**, and resilient outbound cloud synchronization.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLOUD VPS (Ubuntu)                       │
│  ┌──────────┐  ┌──────────────┐  ┌────────────┐                │
│  │  Nginx   │──│ Cloud FastAPI │──│ PostgreSQL │                │
│  │  (HTTPS) │  │   Backend    │  │            │                │
│  └──────────┘  └──────────────┘  └────────────┘                │
└──────────────────────┬──────────────────────────────────────────┘
                       │ Outbound HTTPS (Gateway → Cloud)
┌──────────────────────▼──────────────────────────────────────────┐
│                   RASPBERRY PI 4 (2 GB RAM)                     │
│  ┌──────────┐  ┌──────────────┐  ┌────────┐  ┌──────────────┐ │
│  │  Nginx   │──│   FastAPI    │──│ SQLite  │  │  Cloud Sync  │ │
│  │ (static  │  │   Backend    │  │ (WAL)  │  │   Worker     │ │
│  │ + proxy) │  └──────┬───────┘  └────────┘  └──────────────┘ │
│  └──────────┘         │                                        │
│                 ┌─────▼─────┐                                  │
│                 │ Mosquitto │ ◄──── MQTT (LAN)                 │
│                 │   Broker  │                                  │
│                 └─────┬─────┘                                  │
│                       │           ┌──────────────────┐         │
│                       │           │ Arduino Uno R3   │         │
│                       │           │ (USB serial)     │         │
│                       │           └──────────────────┘         │
└───────────────────────┼────────────────────────────────────────┘
                        │ Wi-Fi (MQTT + HTTP OTA)
              ┌─────────▼─────────┐
              │   ESP32 Nodes     │
              │ (ESP-IDF, OTA,    │
              │  MQTT telemetry)  │
              └───────────────────┘
```

---

## Monorepo Layout

```
edgefleet/
├── backend/               # FastAPI async application (REST, WebSockets, MQTT client, state machine)
├── frontend/              # React 18 + Vite + TypeScript + Tailwind CSS industrial dashboard
├── firmware/
│   ├── esp32/             # Production ESP-IDF v5 project with dual-partition OTA and rollback
│   └── arduino_uno/       # Arduino Uno sketch with JSON telemetry and avrdude compatibility
├── deploy/
│   ├── raspberry-pi/      # Systemd units, Nginx, Mosquitto, installer, updater, and backup scripts
│   └── cloud/             # Docker Compose stack with PostgreSQL and Nginx for cloud VPS
├── scripts/
│   ├── mock_device.py     # Realistic ESP32 & Arduino Uno IoT device telemetry simulator
│   ├── serial_gateway.py  # USB cable serial telemetry bridge & COM port scanner
│   ├── seed_demo_data.py  # Rich demo database seeder (devices, firmware, telemetry, alerts)
│   ├── create_admin.py    # CLI administrator account generator
│   └── generate_api_schema.py # OpenAPI JSON exporter
├── tests/
│   └── backend/           # Pytest async test suite (25 unit and integration tests)
└── docs/                  # Comprehensive architectural, security, and setup guides
```

---

## Quick Start (Development & Simulation)

### 1. Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- (Optional) Local Mosquitto broker or use EdgeFleet's offline/simulated mode

### 2. Set Up Backend & Seed Database
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r backend/requirements.txt -r backend/requirements-dev.txt

# Populate realistic demo dataset
python scripts/seed_demo_data.py
```

### 3. Run Backend Server
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- API Docs: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
- Health Check: [http://localhost:8000/api/health](http://localhost:8000/api/health)

### 4. Run Frontend Dashboard
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

### 5. Launch Mock Hardware Simulator (Optional)
Simulate 3 ESP32 nodes and 1 Arduino Uno streaming real-time sensor telemetry and responding to OTA firmware update commands:
```bash
python scripts/mock_device.py --interval 5.0
```

---

## Default Demo Credentials

The database seeder pre-configures three accounts with different RBAC roles:

| Role | Email | Password | Permissions |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@edgefleet.local` | `adminpassword123` | Full access, firmware approvals, user management |
| **Operator** | `operator@edgefleet.local` | `operatorpassword123` | Upload releases, trigger FOTA rollouts, acknowledge alerts |
| **Viewer** | `viewer@edgefleet.local` | `viewerpassword123` | Read-only inspection of fleet devices & telemetry |

*Tip: The dashboard login page features quick one-click autofill buttons for each demo role.*

---

## Running the Automated Test Suite

```bash
pytest tests/backend -v
```
All 20 test suites cover authentication, RBAC, firmware validation, deployment state transitions, MQTT message handling, and cloud synchronization.

---

## Documentation Directory

- **[System Architecture](docs/ARCHITECTURE.md)** — Monorepo design, memory constraints, and design decisions
- **[Security & Threat Model](docs/SECURITY.md)** — RBAC, SHA-256 binary validation, safe subprocess rules, and rate limits
- **[API Reference](docs/API.md)** — Comprehensive REST endpoints, WebSocket schemas, and query parameters
- **[Firmware Update Mechanics](docs/FIRMWARE_UPDATE.md)** — ESP-IDF dual-partition OTA, rollback triggers, and avrdude protocol
- **[Raspberry Pi 4 Setup](docs/RASPBERRY_PI_SETUP.md)** — Hardware checklist, OS installation, and systemd units
- **[Cloud Control Plane](docs/CLOUD_DEPLOYMENT.md)** — VPS setup, Docker Compose, PostgreSQL, and multi-gateway sync
- **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)** — Error codes, serial locks, OTA timeouts, and repair steps
- **[Test Report](docs/TEST_REPORT.md)** — Automated test results and physical hardware commissioning checklist
