"""Device adapters package."""

from app.device_adapters.base import BaseDeviceAdapter
from app.device_adapters.esp32_ota import ESP32OTAAdapter, esp32_adapter
from app.device_adapters.esp32_serial import ESP32SerialAdapter, esp32_serial_adapter
from app.device_adapters.arduino_uno import ArduinoUnoAdapter, arduino_adapter
from app.device_adapters.serial_manager import list_available_ports, get_port_lock

__all__ = [
    "BaseDeviceAdapter",
    "ESP32OTAAdapter",
    "esp32_adapter",
    "ESP32SerialAdapter",
    "esp32_serial_adapter",
    "ArduinoUnoAdapter",
    "arduino_adapter",
    "list_available_ports",
    "get_port_lock",
]
