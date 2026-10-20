# EdgeFleet System Architecture

## 1. Overview & Operational Principles

**EdgeFleet** is a lightweight, industrial-grade IoT device monitoring and Secure Firmware Over-The-Air (FOTA) deployment platform designed specifically for edge environments. It operates primarily on a **Raspberry Pi 4 (2 GB RAM)** gateway serving heterogeneous microcontrollers (ESP32 via Wi-Fi and Arduino Uno via USB serial), with an optional outbound cloud control plane.

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

## 2. Gateway Constraints & Design Decisions

### 2.1 Why No Docker on the Raspberry Pi 4 (2 GB RAM)?
- **RAM Footprint**: A Docker daemon, containerd, and 4 container runtimes consume ~350–500 MB of base RAM. On a 2 GB RAM Pi running OS, Mosquitto, and firmware operations, memory headroom is critical.
- **Native Systemd**: Running FastAPI under systemd and Mosquitto natively consumes less than **120 MB RAM total**.
- **USB Device Passthrough**: Flashing an Arduino Uno directly through native `avrdude` avoids USB device hotplug complexities and permissions mapping inside Docker containers.

### 2.2 Local SQLite (WAL Mode) vs. Cloud PostgreSQL
- **Local Autonomy**: Gateways must continue logging sensor telemetry, running deployment state machines, and responding to dashboard operators even during complete WAN / internet outages.
- **SQLite with WAL**: SQLite in Write-Ahead Logging (`WAL`) mode provides concurrent multi-reader access and sub-millisecond writes with zero maintenance overhead.
- **Outbound Asynchronous Sync**: Gateways buffer outbound events in a durable `cloud_sync_queue` table and batch-push them to the cloud control plane when internet connectivity is available.

---

## 3. Communication Pipelines

### 3.1 MQTT Broker & Schema
- **Topic Scheme**:
  - `edgefleet/v1/devices/{device_id}/telemetry`: High-frequency sensor readings (temperature, humidity, heap, RSSI, lux, VCC).
  - `edgefleet/v1/devices/{device_id}/status`: Device heartbeats and Last Will and Testament (`LWT`).
  - `edgefleet/v1/devices/{device_id}/commands`: Gateway instructions (e.g. `ota_update`, `reboot`).
  - `edgefleet/v1/devices/{device_id}/update/status`: In-flight deployment stage progression (`TRANSFERRING`, `VERIFYING`, `INSTALLING`, `REBOOTING`, `HEALTH_CHECK`, `SUCCESS`, `FAILED`).

### 3.2 Real-Time WebSocket Streaming
- Browsers establish a persistent WebSocket connection to `/api/ws`.
- Telemetry, online/offline transitions, and deployment progression received by the gateway's MQTT worker are immediately broadcast to all active dashboards with sub-50ms latency.

---

## 4. Hardware Deployment Adapters

### 4.1 ESP32 Wi-Fi OTA Adapter
- Dispatches signed firmware URLs via MQTT command.
- ESP32 streams binary over HTTP/HTTPS from `/api/firmware/{id}/download`.
- Writes into passive OTA slot (`ota_0` or `ota_1`).
- Bootloader boots into pending verification. If self-tests pass, `esp_ota_mark_app_valid_cancel_rollback()` commits the partition.

### 4.2 Arduino Uno USB Serial Adapter
- Acquires exclusive async lock on serial port (`/dev/ttyACM0`).
- Dispatches parameterized `avrdude` subprocess without shell interpolation:
  ```bash
  avrdude -p atmega328p -c arduino -P /dev/ttyACM0 -b 115200 -U flash:w:/path/to/firmware.hex:i
  ```
- Captures sanitized stdout/stderr, verifies exit code 0, releases lock.
