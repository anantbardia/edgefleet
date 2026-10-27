#include "EdgeFleet.h"

// ESP32-C3 SuperMini onboard blue LED is on GPIO 8
#define LED_PIN 8

void setup() {
  pinMode(LED_PIN, OUTPUT);

  // Starts Wi-Fi, MQTT, and the background Wireless FOTA engine
  EdgeFleet.begin("host", "12345678", "10.162.65.199", "esp32-c3-mini", "1.0.0");
}

void loop() {
  // Keeps the wireless update engine running & sends telemetry
  EdgeFleet.loop();

  // ── YOUR OWN CODE / SENSORS HERE ──────────────────────────────────────────
  // Heartbeat LED blink (every 500ms)
  static unsigned long lastBlink = 0;
  if (millis() - lastBlink > 500) {
    lastBlink = millis();
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));
  }
}
