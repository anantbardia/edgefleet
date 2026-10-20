# EdgeFleet Arduino Uno Firmware

This project contains the Arduino Uno sketch (`edgefleet_uno.ino`) designed to communicate directly with the EdgeFleet Raspberry Pi gateway over USB serial.

## Building with Arduino CLI

```bash
# Update board index
arduino-cli core update-index --config-file arduino-cli.yaml

# Install AVR core
arduino-cli core install arduino:avr --config-file arduino-cli.yaml

# Compile to Intel HEX format
arduino-cli compile --fqbn arduino:avr:uno edgefleet_uno --output-dir build/
```

The resulting `build/edgefleet_uno.ino.hex` file is uploaded to the EdgeFleet dashboard and flashed directly by the gateway using `avrdude`.

## Flashing manually via avrdude

```bash
avrdude -p atmega328p -c arduino -P /dev/ttyACM0 -b 115200 -U flash:w:build/edgefleet_uno.ino.hex:i
```
