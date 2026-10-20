# EdgeFleet — Complete Raspberry Pi 4 Deployment & Operations Guide

This guide is the complete, production-grade deployment manual for running the **EdgeFleet IoT Gateway** on a **Raspberry Pi 4 Model B (2 GB, 4 GB, or 8 GB RAM)**. It covers everything from bare-metal SD card provisioning to automated services, USB hardware integration (ESP32 cable & Arduino), reverse proxying, backups, and troubleshooting.

---

## Table of Contents
1. [Architecture & Hardware Bill of Materials](#1-architecture--hardware-bill-of-materials)
2. [Operating System Preparation (Headless 64-bit)](#2-operating-system-preparation-headless-64-bit)
3. [Network & Firewall Preparation](#3-network--firewall-preparation)
4. [Deployment Option A: Automated One-Line Installation](#4-deployment-option-a-automated-one-line-installation)
5. [Deployment Option B: Step-by-Step Manual Installation](#5-deployment-option-b-step-by-step-manual-installation)
6. [Hardware Interfacing (ESP32 Cable & Arduino USB)](#6-hardware-interfacing-esp32-cable--arduino-usb)
7. [Environment Configuration (`.env`)](#7-environment-configuration-env)
8. [Database & Admin Account Provisioning](#8-database--admin-account-provisioning)
9. [Systemd Services & Nginx Reverse Proxy](#9-systemd-services--nginx-reverse-proxy)
10. [Verification & Diagnostic Health Checks](#10-verification--diagnostic-health-checks)
11. [Day-2 Operations: Updates, Backups & Maintenance](#11-day-2-operations-updates-backups--maintenance)
12. [Troubleshooting & Common Failure Scenarios](#12-troubleshooting--common-failure-scenarios)

---

## 1. Architecture & Hardware Bill of Materials

### 1.1 Hardware Specifications
| Component | Specification | Notes |
| :--- | :--- | :--- |
| **SBC** | Raspberry Pi 4 Model B (2 GB RAM min) | Native ARM64 Debian Linux (no Docker overhead) |
| **Storage** | 16 GB+ Class 10 / UHS-I / A1 MicroSD or USB 3.0 SSD | High-endurance card recommended for SQLite WAL |
| **Power Supply** | Official Raspberry Pi 15.3W USB-C (5.1V / 3.0A) | Crucial to avoid low-voltage throttling during USB flash |
| **Cooling** | Passive aluminum heatsink case or active fan | Prevents thermal throttling during 460800 baud flashes |
| **Network** | Gigabit Ethernet cable or 2.4/5 GHz 802.11ac Wi-Fi | Static IP or DHCP reservation recommended |
| **ESP32 Cable** | 4-wire USB-A to Micro-USB / USB-C data cable | **Must** have data lines (D+/D-), not charge-only |
| **Arduino Cable** | Standard USB-A to USB-B cable | Connects Arduino Uno (ATmega328P Optiboot) |

### 1.2 Resource Footprint on 2 GB Pi 4
EdgeFleet is designed specifically for low-resource gateway constraints:
- **FastAPI / Uvicorn (2 workers)**: ~70–90 MB RAM
- **Mosquitto MQTT Broker**: ~8–12 MB RAM
- **Nginx Reverse Proxy**: ~15–20 MB RAM
- **SQLite Database**: Native file I/O with Write-Ahead Logging (WAL)
- **Total System Memory Consumption**: Under 350 MB RAM total (including OS kernel)

---

## 2. Operating System Preparation (Headless 64-bit)

EdgeFleet requires a **64-bit Linux kernel** (arm64/aarch64) for Python 3.11+ async performance and modern cryptography libraries.

### Step 2.1: Flash SD Card with Raspberry Pi Imager
1. Download and install [Raspberry Pi Imager](https://www.raspberrypi.com/software/).
2. Insert your MicroSD card or USB SSD into your workstation.
3. Select OS: **Raspberry Pi OS (other)** → **Raspberry Pi OS Lite (64-bit)** (Debian Bookworm or Bullseye).
4. Click the **Gear icon (Edit Settings)** to configure headless options before writing:
   - **Hostname**: `edgefleet-gateway`
   - **Username / Password**: Set username `pi` (or your preferred admin name) and a strong password.
   - **Configure Wireless LAN**: Enter your Wi-Fi SSID and password (and country code).
   - **Enable SSH**: Check **Allow public-key authentication only** (or set password authentication).
5. Click **Write** and verify the image.

### Step 2.2: Initial Boot & SSH Login
1. Insert the card into your Raspberry Pi 4, connect the Ethernet cable (or let Wi-Fi associate), and plug in the power supply.
2. Wait 45–60 seconds for the first boot expansion.
3. Locate the Pi's IP address on your local network or use mDNS:
   ```bash
   ssh pi@edgefleet-gateway.local
   # Or using IP address:
   ssh pi@192.168.1.150
   ```

### Step 2.3: Upgrade Base System Packages
```bash
sudo apt-get update -y && sudo apt-get upgrade -y
sudo apt-get install -y git curl ufw
```

---

## 3. Network & Firewall Preparation

Ensure the required local and external ports are accessible.

### 3.1 Port Allocation Map
| Port | Protocol | Service | Scope |
| :--- | :--- | :--- | :--- |
| **80** | TCP | Nginx (Frontend & Reverse Proxy) | LAN / Web Browser |
| **443** | TCP | Nginx (HTTPS with SSL Certificate) | Optional (Production) |
| **1883** | TCP | Mosquitto MQTT Broker | Local LAN (ESP32 telemetry/OTA) |
| **22** | TCP | SSH Server | Remote Administration |
| **8000** | TCP | FastAPI Backend (Internal) | `127.0.0.1` only (proxied by Nginx) |

### 3.2 Configure UFW (Uncomplicated Firewall)
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw allow 80/tcp comment 'EdgeFleet Web Dashboard & API'
sudo ufw allow 1883/tcp comment 'Mosquitto MQTT for ESP32 Nodes'
sudo ufw enable
```

---

## 4. Deployment Option A: Automated One-Line Installation

EdgeFleet includes an automated installer script (`install.sh`) that provisions the system, user accounts, virtualenv, dependencies, systemd units, and Nginx.

### Execute Automated Installer:
```bash
# 1. Clone repository into /opt/edgefleet
sudo git clone https://github.com/your-org/edgefleet.git /opt/edgefleet
sudo chown -R $USER:$USER /opt/edgefleet

# 2. Run automated installer as root
cd /opt/edgefleet/deploy/raspberry-pi
sudo bash install.sh
```

The script will automatically:
1. Install APT dependencies: `python3`, `python3-venv`, `python3-pip`, `nginx`, `mosquitto`, `mosquitto-clients`, `avrdude`, `jq`, `curl`.
2. Create system user `edgefleet` and add it to the `dialout` group.
3. Create system directories:
   - `/var/lib/edgefleet/firmware` (secure storage for binary releases)
   - `/var/lib/edgefleet/backups` (automated backup storage)
   - `/var/log/edgefleet` (application execution logs)
4. Deploy Python virtual environment at `/opt/edgefleet/.venv` with `esptool`, `pyserial`, `fastapi`, and dependencies.
5. Deploy `edgefleet-backend.service` and configure Mosquitto and Nginx.
6. Enable and start all daemons.

---

## 5. Deployment Option B: Step-by-Step Manual Installation

If you prefer granular control over each component or are integrating with existing automation (Ansible / Puppet / Chef), follow these manual steps.

### Step 5.1: Install System Packages
```bash
sudo apt-get update -y
sudo apt-get install -y --no-install-recommends \
    python3 \
    python3-venv \
    python3-pip \
    nginx \
    mosquitto \
    mosquitto-clients \
    avrdude \
    jq \
    curl \
    git
```

### Step 5.2: Create Dedicated Service User
Run EdgeFleet under an isolated service user with serial port hardware privileges:
```bash
sudo useradd -r -s /bin/false -d /opt/edgefleet -G dialout edgefleet
```

### Step 5.3: Create Directory Structure
```bash
sudo mkdir -p /opt/edgefleet
sudo mkdir -p /var/lib/edgefleet/firmware
sudo mkdir -p /var/lib/edgefleet/backups
sudo mkdir -p /var/log/edgefleet

sudo chown -R edgefleet:edgefleet /opt/edgefleet
sudo chown -R edgefleet:edgefleet /var/lib/edgefleet
sudo chown -R edgefleet:edgefleet /var/log/edgefleet
```

### Step 5.4: Copy Codebase to `/opt/edgefleet`
```bash
sudo cp -r /path/to/edgefleet/* /opt/edgefleet/
sudo chown -R edgefleet:edgefleet /opt/edgefleet
```

### Step 5.5: Create Virtual Environment & Install Dependencies
```bash
sudo -u edgefleet python3 -m venv /opt/edgefleet/.venv
sudo -u edgefleet /opt/edgefleet/.venv/bin/pip install --upgrade pip setuptools wheel
sudo -u edgefleet /opt/edgefleet/.venv/bin/pip install -r /opt/edgefleet/backend/requirements.txt
```

Verify that `esptool` is installed and functional:
```bash
sudo -u edgefleet /opt/edgefleet/.venv/bin/python -m esptool version
# Output: esptool v5.6.0 (or higher)
```

---

## 6. Hardware Interfacing (ESP32 Cable & Arduino USB)

EdgeFleet supports direct hardware flashing over USB cables for both **ESP32** and **Arduino Uno**.

### 6.1 Udev Rules for Serial Port Permissions
To prevent permission conflicts and ensure stable device nodes when nodes are plugged in or unplugged, create a custom udev rule:

```bash
sudo nano /etc/udev/rules.d/99-edgefleet.rules
```

Paste the following rules:
```udev
# Silicon Labs CP2102 / CP2104 (ESP32 DevKit)
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", MODE="0666", GROUP="dialout", SYMLINK+="esp32_cable_%n"

# WCH CH340 / CH341 (ESP32 / Arduino clones)
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", MODE="0666", GROUP="dialout", SYMLINK+="ch340_device_%n"

# Espressif Native USB-JTAG/Serial CDC (ESP32-S2 / ESP32-S3 / ESP32-C3)
SUBSYSTEM=="tty", ATTRS{idVendor}=="303a", MODE="0666", GROUP="dialout", SYMLINK+="esp32_native_%n"

# Arduino Uno R3 (ATmega328P with Atmega16U2 USB chip)
SUBSYSTEM=="tty", ATTRS{idVendor}=="2341", ATTRS{idProduct}=="0043", MODE="0666", GROUP="dialout", SYMLINK+="arduino_uno"
SUBSYSTEM=="tty", ATTRS{idVendor}=="2341", ATTRS{idProduct}=="0001", MODE="0666", GROUP="dialout", SYMLINK+="arduino_uno"
```

Reload the udev daemon:
```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### 6.2 Verifying Connected USB Cables
Plug in your ESP32 or Arduino via cable and verify detection:
```bash
ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
```
Or run the EdgeFleet CLI scanner:
```bash
sudo -u edgefleet /opt/edgefleet/.venv/bin/python /opt/edgefleet/scripts/serial_gateway.py --scan
```

---

## 7. Environment Configuration (`.env`)

Create production settings in `/opt/edgefleet/.env`:

```bash
sudo -u edgefleet nano /opt/edgefleet/.env
```

Paste and adjust the following production configuration:

```ini
# ── Application Settings ────────────────────────────────────────────────
APP_NAME=EdgeFleet Gateway
APP_VERSION=0.1.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
SECRET_KEY=GENERATE_A_64_CHAR_HEX_SECRET_STRING_USING_OPENSSL

# ── Database (SQLite WAL Mode) ──────────────────────────────────────────
DATABASE_URL=sqlite+aiosqlite:////opt/edgefleet/backend/edgefleet.db

# ── Local MQTT Broker ───────────────────────────────────────────────────
MQTT_HOST=127.0.0.1
MQTT_PORT=1883
MQTT_USERNAME=
MQTT_PASSWORD=
MQTT_CLIENT_ID=edgefleet-gateway-backend

# ── Storage & Paths ─────────────────────────────────────────────────────
FIRMWARE_STORAGE_PATH=/var/lib/edgefleet/firmware
MAX_UPLOAD_SIZE_MB=32

# ── CORS Origins ────────────────────────────────────────────────────────
CORS_ORIGINS=http://localhost,http://127.0.0.1,http://edgefleet-gateway.local

# ── Serial Flashing Adapters ────────────────────────────────────────────
AVRDUDE_PATH=/usr/bin/avrdude
ARDUINO_SERIAL_PORT_PATTERNS=/dev/ttyACM*,/dev/ttyUSB*
ESP32_SERIAL_PORT_PATTERNS=/dev/ttyUSB*,/dev/ttyACM*
ESP32_SERIAL_BAUD_RATE=460800
ESP32_SERIAL_APP_OFFSET=0x10000
ESP32_SERIAL_CHIP=auto
ESP32_SERIAL_TELEMETRY_BAUD=115200

# ── Heartbeat & Timeouts ────────────────────────────────────────────────
HEARTBEAT_TIMEOUT_SECONDS=90
DEPLOYMENT_TIMEOUT_SECONDS=300

# ── Outbound Cloud Sync (Optional) ──────────────────────────────────────
CLOUD_ENABLED=false
CLOUD_API_URL=
CLOUD_API_KEY=
CLOUD_SYNC_INTERVAL_SECONDS=60
```

> [!TIP]
> Generate a cryptographically secure `SECRET_KEY` by running:
> ```bash
> openssl rand -hex 32
> ```

Secure the file permissions:
```bash
sudo chmod 600 /opt/edgefleet/.env
sudo chown edgefleet:edgefleet /opt/edgefleet/.env
```

---

## 8. Database & Admin Account Provisioning

### 8.1 Initialize Database Schema
Run Alembic migrations to build the tables in SQLite:
```bash
cd /opt/edgefleet/backend
sudo -u edgefleet /opt/edgefleet/.venv/bin/alembic upgrade head
```

### 8.2 Create the Initial Administrator Account
Use the interactive CLI script to set up your administrator credentials:
```bash
sudo -u edgefleet /opt/edgefleet/.venv/bin/python /opt/edgefleet/scripts/create_admin.py \
    --email admin@edgefleet.local \
    --password "YourSecureMasterPassword123!"
```

*(Optional)* If you want to populate initial demo devices and test firmware:
```bash
sudo -u edgefleet /opt/edgefleet/.venv/bin/python /opt/edgefleet/scripts/seed_demo_data.py
```

---

## 9. Systemd Services & Nginx Reverse Proxy

### 9.1 Mosquitto MQTT Configuration
Deploy the custom Mosquitto configuration:
```bash
sudo cp /opt/edgefleet/deploy/raspberry-pi/mosquitto-edgefleet.conf /etc/mosquitto/conf.d/
sudo systemctl restart mosquitto
sudo systemctl enable mosquitto
```

Test that Mosquitto is active:
```bash
mosquitto_sub -t "edgefleet/v1/test" -C 1 &
mosquitto_pub -t "edgefleet/v1/test" -m "broker_online"
```

### 9.2 Deploy Systemd Units
Deploy `edgefleet-backend.service`:
```bash
sudo cp /opt/edgefleet/deploy/raspberry-pi/edgefleet-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable edgefleet-backend
sudo systemctl start edgefleet-backend
```

Check status:
```bash
sudo systemctl status edgefleet-backend
```

### 9.3 Deploy Nginx Reverse Proxy & Frontend Host
Deploy the Nginx site configuration:
```bash
sudo cp /opt/edgefleet/deploy/raspberry-pi/nginx-edgefleet.conf /etc/nginx/sites-available/edgefleet.conf
sudo ln -sf /etc/nginx/sites-available/edgefleet.conf /etc/nginx/sites-enabled/default

# Verify syntax and reload
sudo nginx -t
sudo systemctl reload nginx
sudo systemctl enable nginx
```

---

## 10. Verification & Diagnostic Health Checks

### 10.1 Run the Built-In Diagnostics Script
```bash
bash /opt/edgefleet/deploy/raspberry-pi/health-check.sh
```

Expected diagnostic output:
```
=== EdgeFleet System Diagnostics ===
✓ Nginx: RUNNING
✓ Mosquitto MQTT: RUNNING
✓ EdgeFleet Backend Service: RUNNING
✓ API Health (/api/health): OK (HTTP 200)
--- Resources ---
Free Memory: 1.6Gi
Root Disk Free: 12.4G
```

### 10.2 Verify API Endpoints via cURL
Test the public health check endpoint:
```bash
curl -s http://127.0.0.1/api/health | jq .
```
Expected output:
```json
{
  "status": "healthy",
  "app_name": "EdgeFleet",
  "version": "0.1.0",
  "database": "connected",
  "mqtt": "connected"
}
```

Check serial port detection over HTTP:
```bash
# Log in to get JWT token:
TOKEN=$(curl -s -X POST http://127.0.0.1/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@edgefleet.local","password":"YourSecureMasterPassword123!"}' | jq -r .access_token)

# List detected ports:
curl -s http://127.0.0.1/api/devices/ports/serial -H "Authorization: Bearer $TOKEN" | jq .
```

### 10.3 Access the Web Dashboard
Open your web browser and navigate to:
```
http://<YOUR_PI_IP_ADDRESS>/
# e.g. http://192.168.1.150/ or http://edgefleet-gateway.local/
```
Log in using:
- **Email**: `admin@edgefleet.local`
- **Password**: *(The password you created in Step 8.2)*

---

## 11. Day-2 Operations: Updates, Backups & Maintenance

### 11.1 Updating EdgeFleet
To pull new versions, recompile frontend, run migrations, and reload services with zero data loss:
```bash
cd /opt/edgefleet/deploy/raspberry-pi
sudo bash update.sh
```

### 11.2 Automated Backups
EdgeFleet includes an atomic backup script (`backup.sh`) that safely snapshots the SQLite database and firmware binaries:
```bash
sudo bash /opt/edgefleet/deploy/raspberry-pi/backup.sh
```

To schedule daily backups at 03:00 AM, add a root cron job:
```bash
sudo crontab -e
```
Add line:
```cron
0 3 * * * /bin/bash /opt/edgefleet/deploy/raspberry-pi/backup.sh > /var/log/edgefleet/backup.log 2>&1
```

### 11.3 Restoring from Backup
To restore a snapshot:
```bash
# 1. Stop backend service
sudo systemctl stop edgefleet-backend

# 2. Extract snapshot
sudo tar -xzvf /var/lib/edgefleet/backups/edgefleet-backup-YYYY-MM-DD.tar.gz -C /

# 3. Restart backend service
sudo systemctl start edgefleet-backend
```

---

## 12. Troubleshooting & Common Failure Scenarios

### 12.1 Inspecting Live Logs
```bash
# Stream backend application logs:
sudo journalctl -u edgefleet-backend -f -n 100

# Stream Nginx web logs:
sudo tail -f /var/log/nginx/error.log

# Stream Mosquitto MQTT logs:
sudo tail -f /var/log/mosquitto/mosquitto.log
```

### 12.2 Issue: ESP32 or Arduino Serial Port "Permission Denied"
* **Symptom**: `esptool.py` or `avrdude` reports `Permission denied: '/dev/ttyUSB0'`.
* **Resolution**:
  Ensure user `edgefleet` is in the `dialout` group:
  ```bash
  sudo usermod -a -G dialout edgefleet
  sudo systemctl restart edgefleet-backend
  ```

### 12.3 Issue: ESP32 Timed Out Waiting for Packet Header
* **Symptom**: `Failed to connect to ESP32: Timed out waiting for packet header`.
* **Resolution**:
  1. Confirm your cable has data lines (try another USB cable).
  2. Some ESP32 development boards require a 10 µF capacitor between `EN` and `GND` for automatic reset, or hold down the `BOOT` button on the ESP32 when flashing starts.
  3. Lower the baud rate in `/opt/edgefleet/.env` to `ESP32_SERIAL_BAUD_RATE=115200` if using long cables.

### 12.4 Issue: High CPU Temperature or Low Voltage
* **Symptom**: System reboots unexpectedly or freezes during flashing.
* **Resolution**:
  Check Pi throttling status:
  ```bash
  vcgencmd get_throttled
  # 0x0 means normal.
  # 0x50000 or 0x50005 indicates past/present undervoltage.
  ```
  Ensure you are using the official Raspberry Pi 5.1V 3.0A power supply and not a generic phone charger.

---

### Quick Reference Command Summary
```bash
# Health check:
bash /opt/edgefleet/deploy/raspberry-pi/health-check.sh

# Restart gateway:
sudo systemctl restart edgefleet-backend mosquitto nginx

# USB port scanner:
sudo -u edgefleet /opt/edgefleet/.venv/bin/python /opt/edgefleet/scripts/serial_gateway.py --scan

# Monitor serial telemetry over cable:
sudo -u edgefleet /opt/edgefleet/.venv/bin/python /opt/edgefleet/scripts/serial_gateway.py --auto
```
