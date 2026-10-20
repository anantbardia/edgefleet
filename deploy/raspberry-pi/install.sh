#!/usr/bin/env bash
set -euo pipefail

# EdgeFleet Raspberry Pi 4 Gateway Installer
# Target: Raspberry Pi OS 64-bit (Debian Bookworm/Bullseye)

echo "=== EdgeFleet Gateway Installation ==="

if [[ $EUID -ne 0 ]]; then
   echo "Error: This script must be run as root (e.g. sudo bash install.sh)" >&2
   exit 1
fi

INSTALL_DIR="/opt/edgefleet"
FIRMWARE_DIR="/var/lib/edgefleet/firmware"
BACKUP_DIR="/var/lib/edgefleet/backups"
LOG_DIR="/var/log/edgefleet"

echo "[1/7] Updating apt repositories and installing system dependencies..."
apt-get update -y
apt-get install -y --no-install-recommends \
    python3 \
    python3-venv \
    python3-pip \
    nginx \
    mosquitto \
    mosquitto-clients \
    avrdude \
    jq \
    curl

echo "[2/7] Creating edgefleet system user..."
if ! id "edgefleet" &>/dev/null; then
    useradd -r -s /bin/false -d "$INSTALL_DIR" -G dialout edgefleet
    echo "Created user 'edgefleet' with 'dialout' serial permissions."
fi

echo "[3/7] Setting up directories and permissions..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR/backend"
mkdir -p "$INSTALL_DIR/frontend/dist"
mkdir -p "$FIRMWARE_DIR"
mkdir -p "$BACKUP_DIR"
mkdir -p "$LOG_DIR"

chown -R edgefleet:edgefleet "$INSTALL_DIR"
chown -R edgefleet:edgefleet "$FIRMWARE_DIR"
chown -R edgefleet:edgefleet "$BACKUP_DIR"
chown -R edgefleet:edgefleet "$LOG_DIR"

echo "[4/7] Deploying Python virtual environment..."
if [[ ! -d "$INSTALL_DIR/.venv" ]]; then
    python3 -m venv "$INSTALL_DIR/.venv"
fi

"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip
if [[ -f "$INSTALL_DIR/backend/requirements.txt" ]]; then
    "$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/backend/requirements.txt"
fi

echo "[5/7] Configuring environment and services..."
# Deploy .env if not present
if [[ ! -f "$INSTALL_DIR/.env" ]]; then
    if [[ -f "$INSTALL_DIR/.env.example" ]]; then
        cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
    else
        touch "$INSTALL_DIR/.env"
    fi
    # Generate random secret key
    SECRET=$(openssl rand -hex 32 2>/dev/null || date +%s | sha256sum | head -c 64)
    sed -i "s/CHANGE_ME_GENERATE_A_STRONG_SECRET/$SECRET/g" "$INSTALL_DIR/.env" || true
    chown edgefleet:edgefleet "$INSTALL_DIR/.env"
    chmod 600 "$INSTALL_DIR/.env"
fi

# Deploy udev rules for USB serial access (ESP32 & Arduino Uno)
cat << 'EOF' > /etc/udev/rules.d/99-edgefleet.rules
# Silicon Labs CP2102 / CP2104 (ESP32)
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", MODE="0666", GROUP="dialout"
# WCH CH340 / CH341 (ESP32 / Arduino clones)
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", MODE="0666", GROUP="dialout"
# Espressif Native USB-JTAG/Serial CDC
SUBSYSTEM=="tty", ATTRS{idVendor}=="303a", MODE="0666", GROUP="dialout"
# Arduino Uno
SUBSYSTEM=="tty", ATTRS{idVendor}=="2341", MODE="0666", GROUP="dialout"
EOF
udevadm control --reload-rules || true
udevadm trigger || true

# Run database migrations
echo "Initializing database..."
cd "$INSTALL_DIR/backend"
sudo -u edgefleet "$INSTALL_DIR/.venv/bin/alembic" upgrade head || true

# Deploy systemd units
cp "$(dirname "$0")/edgefleet-backend.service" /etc/systemd/system/
cp "$(dirname "$0")/edgefleet-sync.service" /etc/systemd/system/

# Deploy Mosquitto config
cp "$(dirname "$0")/mosquitto-edgefleet.conf" /etc/mosquitto/conf.d/
systemctl restart mosquitto

# Deploy Nginx config
cp "$(dirname "$0")/nginx-edgefleet.conf" /etc/nginx/sites-available/edgefleet.conf
ln -sf /etc/nginx/sites-available/edgefleet.conf /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo "[6/7] Enabling and starting EdgeFleet services..."
systemctl daemon-reload
systemctl enable edgefleet-backend.service
systemctl restart edgefleet-backend.service

echo "[7/7] Installation complete!"
echo "EdgeFleet Gateway is live on http://localhost"
echo "Check status: sudo systemctl status edgefleet-backend"
echo "Create admin: sudo -u edgefleet /opt/edgefleet/.venv/bin/python /opt/edgefleet/scripts/create_admin.py"
