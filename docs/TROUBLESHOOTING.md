# EdgeFleet Troubleshooting & Diagnostics

This reference provides rapid remediation workflows for common field issues encountered on EdgeFleet gateways and edge nodes.

---

## 1. Quick Diagnostic Checklist

| Symptom | Primary Cause | Immediate Fix |
| :--- | :--- | :--- |
| **Node marked Offline** | No MQTT heartbeat for > 90 seconds | Check node power and Wi-Fi signal. Inspect gateway Mosquitto broker status with `systemctl status mosquitto`. |
| **avrdude: programmer not responding** | Serial port locked or baud rate mismatch | Verify Arduino Uno is on `/dev/ttyACM0` via `ls -l /dev/ttyACM*`. Check user permissions (`groups edgefleet` must include `dialout`). |
| **ESP32 OTA failed during download** | Gateway IP not reachable or token expired | Verify ESP32 is connected to gateway Wi-Fi subnet. Test downloading binary directly via `curl` from ESP32 IP. |
| **ESP32 rolls back immediately** | Firmware self-test failed or crashed on boot | Connect serial monitor at 115200 baud. Check panic stack trace. Fix self-test assertion in `health_check.c`. |
| **WebSocket disconnects after 60s** | Nginx proxy timeout terminating idle socket | Ensure `proxy_read_timeout 86400;` and `Connection "upgrade";` are configured in Nginx site config. |

---

## 2. Arduino Uno USB Serial Remediation

### Error: `avrdude: ser_open(): can't open device "/dev/ttyACM0": Permission denied`
**Cause**: The process lacks permissions to read/write character device `/dev/ttyACM0`.
**Fix**:
```bash
sudo usermod -aG dialout edgefleet
sudo systemctl restart edgefleet-backend
```

### Error: `avrdude: stk500_recv(): programmer is not responding`
**Cause**: The bootloader auto-reset circuit failed to engage, or another process has the port open.
**Fix**:
1. Identify conflicting serial listeners:
   ```bash
   sudo lsof /dev/ttyACM0
   ```
2. Press the physical `RESET` button on the Arduino Uno 0.5s before flashing begins.

---

## 3. ESP32 OTA Rollback Diagnostics

When an ESP32 boots into a new partition, it sets the image state to `ESP_OTA_IMG_PENDING_VERIFY`. If the application encounters an unhandled exception or watchdog timeout before executing `esp_ota_mark_app_valid_cancel_rollback()`, the ESP-IDF bootloader marks the slot invalid and rolls back to the passive partition.

**How to verify active partition**:
```bash
# Flash monitor ESP32 over USB to inspect bootloader log:
idf.py -p /dev/ttyUSB0 monitor
```
Look for:
```
I (1420) esp_image: Verified image successfully!
I (1430) boot: Loaded app from partition at offset 0x160000
I (1480) health_check: Image in pending verify state. Running health checks...
I (1520) health_check: Health check PASSED. Confirming firmware and cancelling rollback...
```

---

## 4. SQLite Database Repair & Maintenance

If the gateway experiences an unexpected hard power loss:
```bash
# Verify SQLite integrity
sqlite3 /opt/edgefleet/backend/edgefleet.db "PRAGMA integrity_check;"

# Optimize Write-Ahead Logging
sqlite3 /opt/edgefleet/backend/edgefleet.db "PRAGMA wal_checkpoint(TRUNCATE);"
```

---

## 5. Log File Locations

- **EdgeFleet Backend**: `sudo journalctl -u edgefleet-backend -f`
- **Mosquitto Broker**: `/var/log/mosquitto/mosquitto.log`
- **Nginx Web Server**: `/var/log/nginx/error.log`
- **Firmware Artifacts**: `/var/lib/edgefleet/firmware/`
- **Database Backups**: `/var/lib/edgefleet/backups/`
