#!/usr/bin/env bash
# ==============================================================================
# EdgeFleet — Instant Live Demo & Mock Fleet Simulator
# Usage: ./start-demo.sh
# ==============================================================================

set -e

echo "=========================================================="
echo "      EdgeFleet — Live Demonstration & Mock Fleet         "
echo "=========================================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Detect Python environment
PYTHON="python3"
if [ -f "/opt/edgefleet/.venv/bin/python" ]; then
    PYTHON="/opt/edgefleet/.venv/bin/python"
elif [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    PYTHON="$SCRIPT_DIR/.venv/bin/python"
fi

# Ensure paho-mqtt is installed
if ! "$PYTHON" -c "import paho.mqtt.client" >/dev/null 2>&1; then
    echo "[*] Installing required paho-mqtt client library..."
    "$PYTHON" -m pip install paho-mqtt >/dev/null 2>&1 || pip3 install paho-mqtt >/dev/null 2>&1 || true
fi

# 1. Seed demo database records so all devices, users & firmware exist
echo "[1/2] Seeding demonstration devices, releases and admin credentials..."
"$PYTHON" scripts/seed_demo_data.py >/dev/null 2>&1 || true
echo "[✓] Database primed with 5 devices (ESP32-001, ESP32-C3, Arduino Uno)!"

# 2. Start mock device simulator
echo "[2/2] Starting real-time telemetry streaming into MQTT broker..."
echo ""
echo "----------------------------------------------------------"
echo "  [✓] esp32-001      : ESP32 Lab Environment Node (ONLINE)"
echo "  [✓] esp32-002      : Production Line Sensor     (ONLINE)"
echo "  [✓] esp32-003      : Warehouse Cold Storage     (ONLINE)"
echo "  [✓] esp32-c3-mini  : ESP32-C3 Wireless Node    (ONLINE)"
echo "  [✓] uno-001        : Arduino Uno Logger         (ONLINE)"
echo "----------------------------------------------------------"
echo "-> Open your Web Dashboard to see live graphs moving!"
echo "-> You can also launch OTA deployments in the dashboard."
echo "-> Press Ctrl+C anytime to stop simulation."
echo "=========================================================="
echo ""

exec "$PYTHON" scripts/mock_device.py --interval 4.0
