#!/usr/bin/env bash
set -euo pipefail

# EdgeFleet Automated Backup Script
BACKUP_DIR="/var/lib/edgefleet/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TARGET_ARCHIVE="$BACKUP_DIR/edgefleet_full_backup_$TIMESTAMP.tar.gz"

echo "=== Creating EdgeFleet Snapshot Archive ==="
mkdir -p "$BACKUP_DIR"

tar -czf "$TARGET_ARCHIVE" \
    --exclude='*.log' \
    -C / \
    opt/edgefleet/backend/edgefleet.db \
    var/lib/edgefleet/firmware \
    opt/edgefleet/.env 2>/dev/null || true

echo "✓ Backup created at: $TARGET_ARCHIVE ($(du -h "$TARGET_ARCHIVE" | awk '{print $1}'))"

# Keep only the 7 most recent backups
echo "Pruning older backups..."
find "$BACKUP_DIR" -name "edgefleet_full_backup_*.tar.gz" -type f -mtime +7 -delete
echo "Done."
