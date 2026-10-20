#!/usr/bin/env python3
"""EdgeFleet USB/Serial Gateway CLI.

Connects to an ESP32 or Arduino device over a USB cable, reads serial telemetry,
displays real-time console feedback, and forwards telemetry to the EdgeFleet API or MQTT broker.

Usage:
    python scripts/serial_gateway.py --scan
    python scripts/serial_gateway.py --port COM3 --baud 115200
    python scripts/serial_gateway.py --auto
"""

import argparse
import json
import sys
import time
from datetime import datetime

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("Error: pyserial is required. Run 'pip install pyserial'")
    sys.exit(1)

try:
    import httpx
except ImportError:
    httpx = None


ESP_VENDORS = {
    0x10C4: "Silicon Labs CP210x (ESP32 DevKit)",
    0x1A86: "WCH CH340 (ESP32/Arduino Clone)",
    0x0403: "FTDI FT232",
    0x303A: "Espressif USB JTAG/Serial / CDC",
}


def scan_ports():
    """Scan and print all available serial ports."""
    ports = serial.tools.list_ports.comports()
    print("=" * 60)
    print("  EdgeFleet USB Serial Port Scanner")
    print("=" * 60)
    if not ports:
        print("  No serial devices detected. Check your USB cable connection.")
        return []

    results = []
    for p in ports:
        chip = ESP_VENDORS.get(p.vid, "Generic Serial Device")
        print(f"  • Port: {p.device}")
        print(f"    Description:  {p.description}")
        print(f"    Hardware ID:  {p.hwid}")
        print(f"    Detected IC:  {chip}")
        print("-" * 60)
        results.append(p)
    return results


def auto_detect_port():
    """Find the most likely ESP32 serial port."""
    ports = serial.tools.list_ports.comports()
    for p in ports:
        if p.vid in ESP_VENDORS:
            return p.device
        if any(token in (p.description or "").lower() for token in ["cp210", "ch340", "esp32", "uart"]):
            return p.device
    if ports:
        return ports[0].device
    return None


def main():
    parser = argparse.ArgumentParser(description="EdgeFleet USB Cable Telemetry Bridge")
    parser.add_argument("--scan", action="store_true", help="List detected serial ports and exit")
    parser.add_argument("--port", type=str, default=None, help="Serial port (e.g. COM3 or /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument("--api-url", type=str, default="http://localhost:8000", help="EdgeFleet API URL")
    parser.add_argument("--api-key", type=str, default="", help="Optional API key for ingestion")
    args = parser.parse_args()

    if args.scan:
        scan_ports()
        return

    port = args.port or auto_detect_port()
    if not port:
        print("No serial port specified and no devices detected.")
        print("Connect your ESP32 via USB cable and rerun with --scan or --port <PORT>.")
        sys.exit(1)

    print(f"[*] Opening serial port {port} at {args.baud} baud...")
    try:
        ser = serial.Serial(port, args.baud, timeout=1.0)
    except Exception as exc:
        print(f"[-] Failed to open serial port {port}: {exc}")
        print("    Tip: Check if another application (like Arduino IDE Serial Monitor or PuTTY) is using it.")
        sys.exit(1)

    print(f"[+] Connected to {port}! Waiting for telemetry lines from ESP32...")
    print("    Press Ctrl+C to stop.\n")

    client = httpx.Client(base_url=args.api_url, timeout=5.0) if httpx else None

    try:
        while True:
            line_bytes = ser.readline()
            if not line_bytes:
                continue

            line = line_bytes.decode("utf-8", errors="replace").strip()
            if not line:
                continue

            ts = datetime.now().strftime("%H:%M:%S")

            if line.startswith("{") and line.endswith("}"):
                try:
                    payload = json.loads(line)
                    dev_id = payload.get("device_id", "unknown")
                    temp = payload.get("temperature")
                    hum = payload.get("humidity")
                    heap = payload.get("heap_free")
                    rssi = payload.get("rssi")

                    print(f"[{ts}] [{dev_id}] Temp: {temp}°C | Humidity: {hum}% | Heap: {heap} B | RSSI: {rssi} dBm")

                    # Forward to API if client available
                    if client:
                        try:
                            # Forward to telemetry endpoint
                            readings = {k: v for k, v in payload.items() if k not in ("schema_version", "device_id")}
                            client.post(
                                "/api/telemetry",
                                json={"device_id": dev_id, "readings": readings},
                            )
                        except Exception:
                            pass
                except json.JSONDecodeError:
                    print(f"[{ts}] (RAW) {line}")
            else:
                # Raw output (bootloader, log messages, etc.)
                print(f"[{ts}] {line}")

    except KeyboardInterrupt:
        print("\n[*] Exiting serial gateway...")
    finally:
        ser.close()
        if client:
            client.close()


if __name__ == "__main__":
    main()
