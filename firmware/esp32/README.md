# EdgeFleet ESP32 Firmware

This directory contains the production-grade **ESP-IDF** firmware for ESP32 edge nodes.

## Features

- **Dual-Partition OTA Updates**: Uses ESP-IDF `esp_https_ota` with custom partition table (`partitions.csv` with `factory`, `ota_0`, `ota_1`).
- **Automatic Rollback Protection**: New firmware boots into `ESP_OTA_IMG_PENDING_VERIFY`. If `health_check_run_self_test()` fails or node crashes, bootloader automatically reverts to the previous working partition.
- **MQTT Telemetry & Commands**: Publishes sensor readings to `edgefleet/v1/devices/{device_id}/telemetry` and listens on `edgefleet/v1/devices/{device_id}/commands`.
- **Last Will and Testament (LWT)**: Immediately notifies EdgeFleet gateway if Wi-Fi or broker link drops unexpectedly.
- **Progress Reporting**: Streams discrete stages (`TRANSFERRING`, `VERIFYING`, `INSTALLING`, `REBOOTING`, `HEALTH_CHECK`, `SUCCESS`) to `update/status`.

## Building and Flashing

Ensure ESP-IDF v5.x is installed in your environment:

```bash
# Set target chip
idf.py set-target esp32

# Configure Wi-Fi SSID, password, and broker address if needed
idf.py menuconfig

# Build binary
idf.py build

# Flash via USB serial
idf.py -p /dev/ttyUSB0 flash monitor
```

The resulting binary `build/edgefleet_esp32.bin` can be directly uploaded via the EdgeFleet dashboard to deploy over Wi-Fi.
