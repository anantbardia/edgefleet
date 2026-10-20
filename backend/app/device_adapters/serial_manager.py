"""Serial port discovery and synchronization manager for USB/UART devices."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("edgefleet.serial_manager")

# Common ESP USB-to-UART Bridge Vendor IDs
ESP_VENDOR_IDS = {
    0x10C4: "Silicon Labs (CP2102/CP2104)",
    0x1A86: "WCH (CH340/CH341)",
    0x0403: "FTDI (FT232)",
    0x303A: "Espressif (Native USB/JTAG/CDC)",
}

# Known Arduino Vendor IDs
ARDUINO_VENDOR_IDS = {
    0x2341: "Arduino LLC",
    0x2A03: "Arduino srl",
    0x1A86: "WCH (CH340 clone Uno)",
}

# Global dictionary of locks per port to avoid concurrent flashing / reading
_PORT_LOCKS: Dict[str, asyncio.Lock] = {}
_LOCK_REGISTRY_MUTEX = asyncio.Lock()


def get_port_lock(port: str) -> asyncio.Lock:
    """Retrieve or create an asyncio.Lock for a specific serial port."""
    normalized = port.strip()
    if normalized not in _PORT_LOCKS:
        _PORT_LOCKS[normalized] = asyncio.Lock()
    return _PORT_LOCKS[normalized]


def list_available_ports() -> List[Dict[str, Any]]:
    """Scan and list available serial ports with hardware identification."""
    results: List[Dict[str, Any]] = []
    try:
        import serial.tools.list_ports

        ports = serial.tools.list_ports.comports()
        for p in ports:
            vid = p.vid
            pid = p.pid
            desc = p.description or ""
            mfg = p.manufacturer or ""
            hwid = p.hwid or ""

            is_esp = False
            is_arduino = False

            if vid in ESP_VENDOR_IDS:
                is_esp = True
            elif any(token in desc.lower() or token in hwid.lower() for token in ["cp210", "ch340", "uart", "espressif", "esp32"]):
                is_esp = True

            if vid in ARDUINO_VENDOR_IDS:
                is_arduino = True
            elif any(token in desc.lower() or token in hwid.lower() for token in ["arduino", "uno", "mega"]):
                is_arduino = True

            results.append({
                "port": p.device,
                "description": desc,
                "manufacturer": mfg,
                "hwid": hwid,
                "vid": f"0x{vid:04X}" if vid else None,
                "pid": f"0x{pid:04X}" if pid else None,
                "is_esp_candidate": is_esp,
                "is_arduino_candidate": is_arduino,
            })
    except Exception as exc:
        logger.warning("Error enumerating serial ports: %s", exc)

    return results
