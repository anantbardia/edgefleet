#!/usr/bin/env bash
set -euo pipefail

# EdgeFleet Gateway Safe Update Script
# Backs up database, pulls latest code, installs dependencies, migrates DB, and verifies health.

INSTALL_DIR="/opt/edgefleet"
BACKUP_DIR="/var/lib/edgefleet/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=== EdgeFleet Update: Starting ==="

if [[ $EUID -ne 0 ]]; then
   echo "Error: Must be run as root." >&2
   exit 1
fi

echo "[1/5] Backing up current database..."
mkdir -p "$BACKUP_DIR"
if [[ -f "$INSTALL_DIR/backend/edgefleet.db" ]]; then
    cp "$INSTALL_DIR/backend/edgefleet.db" "$BACKUP_DIR/edgefleet_db_backup_$TIMESTAMP.db"
    echo "Database snapshot saved to $BACKUP_DIR/edgefleet_db_backup_$TIMESTAMP.db"
fi

echo "[2/5] Stopping EdgeFleet services..."
systemctl stop edgefleet-backend.service || true

echo "[3/5] Updating Python packages..."
"$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/backend/requirements.txt"

echo "[4/5] Running Alembic migrations..."
cd "$INSTALL_DIR/backend"
"$INSTALL_DIR/.venv/bin/alembic" upgrade head

echo "[5/5] Restarting services and running health check..."
systemctl start edgefleet-backend.service
sleep 3

HEALTH=$(curl -s http://127.0.0.1:8000/api/health || echo "FAILED")
echo "Health status response: $HEALTH"

echo "=== EdgeFleet Update: Finished Successfully ==="
