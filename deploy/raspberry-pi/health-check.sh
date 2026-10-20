#!/usr/bin/env bash
set -euo pipefail

# EdgeFleet Gateway Health Check Script
echo "=== EdgeFleet System Diagnostics ==="

# Check Nginx
if systemctl is-active --quiet nginx; then
    echo "✓ Nginx: RUNNING"
else
    echo "✗ Nginx: STOPPED"
fi

# Check Mosquitto
if systemctl is-active --quiet mosquitto; then
    echo "✓ Mosquitto MQTT: RUNNING"
else
    echo "✗ Mosquitto MQTT: STOPPED"
fi

# Check Backend
if systemctl is-active --quiet edgefleet-backend; then
    echo "✓ EdgeFleet Backend Service: RUNNING"
else
    echo "✗ EdgeFleet Backend Service: STOPPED"
fi

# Query REST Health Endpoint
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/health || echo "000")
if [[ "$HTTP_CODE" == "200" ]]; then
    echo "✓ API Health (/api/health): OK (HTTP 200)"
else
    echo "✗ API Health (/api/health): FAILED (HTTP $HTTP_CODE)"
fi

# Memory & Disk Check
echo "--- Resources ---"
echo "Free Memory: $(free -h | awk '/Mem:/ {print $4}')"
echo "Root Disk Free: $(df -h / | awk 'NR==2 {print $4}')"
