/*
 * EdgeFleet — ESP32-S3 Secure Wi-Fi & FOTA Node Firmware
 * Target: ESP32-S3 (ESP32-S3 DevKitC-1, WROOM-1, Zero, etc.)
 *
 * Requirements:
 * - Arduino IDE with ESP32 board package (by Espressif)
 * - Library: PubSubClient (install from Arduino Library Manager)
 * - Board: "ESP32S3 Dev Module" (or your specific S3 board)
 * - Partition Scheme: Any scheme with OTA (e.g. "Minimal SPIFFS (1.9MB APP with OTA/190KB SPIFFS)"
 *                     or "8MB with spiffs (3MB APP/1.5MB SPIFFS)" depending on flash size)
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <Update.h>
#include <PubSubClient.h>

// ── Configuration ────────────────────────────────────────────────────────────
// Adjust Wi-Fi settings to match your network (must reach the Raspberry Pi gateway)
const char* WIFI_SSID         = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD     = "YOUR_WIFI_PASSWORD";

// EdgeFleet Gateway details
const char* GATEWAY_HOST      = "192.168.137.99"; // Raspberry Pi Gateway IP
const int   MQTT_PORT         = 1883;

// Device Identity
const char* DEVICE_ID         = "esp32-s3-01";
const char* BOARD_VARIANT     = "ESP32-S3";
const char* CURRENT_VERSION   = "1.0.0"; // Increment when creating new releases (e.g., 1.1.0)

// Optional on-board status LED (Pin 2, Pin 13, or RGB LED on GPIO 48 on official S3 DevKit)
#define STATUS_LED_PIN        2 // Change to match your board, or leave as -1 if none

// ── Global Objects ───────────────────────────────────────────────────────────
WiFiClient espClient;
PubSubClient mqttClient(espClient);

unsigned long lastTelemetryTime = 0;
const unsigned long TELEMETRY_INTERVAL = 5000; // Emit readings every 5 seconds
bool otaInProgress = false;

// ── MQTT Topics ──────────────────────────────────────────────────────────────
String topicTelemetry;
String topicStatus;
String topicCommands;
String topicUpdateStatus;

void setupTopics() {
  topicTelemetry    = String("edgefleet/v1/devices/") + DEVICE_ID + "/telemetry";
  topicStatus       = String("edgefleet/v1/devices/") + DEVICE_ID + "/status";
  topicCommands     = String("edgefleet/v1/devices/") + DEVICE_ID + "/commands";
  topicUpdateStatus = String("edgefleet/v1/devices/") + DEVICE_ID + "/update/status";
}

// ── Helpers ──────────────────────────────────────────────────────────────────
void emitOtaStatus(const char* depId, const char* stage, const char* status, const char* err = nullptr) {
  char buf[384];
  if (err) {
    snprintf(buf, sizeof(buf),
      "{\"schema_version\":\"1.0\",\"device_id\":\"%s\",\"deployment_id\":\"%s\","
      "\"stage\":\"%s\",\"status\":\"%s\",\"error\":\"%s\"}",
      DEVICE_ID, depId, stage, status, err);
  } else {
    snprintf(buf, sizeof(buf),
      "{\"schema_version\":\"1.0\",\"device_id\":\"%s\",\"deployment_id\":\"%s\","
      "\"stage\":\"%s\",\"status\":\"%s\"}",
      DEVICE_ID, depId, stage, status);
  }

  Serial.printf("[EdgeFleet OTA] %s -> %s\n", stage, status);
  mqttClient.publish(topicUpdateStatus.c_str(), buf, false);
}

// ── Perform Wi-Fi FOTA Update ────────────────────────────────────────────────
void performOTA(String downloadUrl, String deploymentId) {
  otaInProgress = true;
  Serial.println("\n[OTA] Starting OTA update routine...");
  Serial.printf("[OTA] Target URL: %s\n", downloadUrl.c_str());

  // 1. Stage: TRANSFERRING
  emitOtaStatus(deploymentId.c_str(), "TRANSFERRING", "in_progress");

  HTTPClient http;
  http.begin(downloadUrl);
  http.setTimeout(30000);

  int httpCode = http.GET();
  if (httpCode != HTTP_CODE_OK) {
    char err[64];
    snprintf(err, sizeof(err), "HTTP GET failed, code: %d", httpCode);
    Serial.printf("[OTA Error] %s\n", err);
    emitOtaStatus(deploymentId.c_str(), "FAILED", "failed", err);
    http.end();
    otaInProgress = false;
    return;
  }

  int contentLength = http.getSize();
  Serial.printf("[OTA] Content-Length: %d bytes\n", contentLength);

  if (contentLength <= 0) {
    emitOtaStatus(deploymentId.c_str(), "FAILED", "failed", "Invalid firmware content length");
    http.end();
    otaInProgress = false;
    return;
  }

  // 2. Stage: VERIFYING
  emitOtaStatus(deploymentId.c_str(), "VERIFYING", "in_progress");

  bool canBegin = Update.begin(contentLength, U_FLASH);
  if (!canBegin) {
    Serial.printf("[OTA Error] Not enough space to begin OTA: %s\n", Update.errorString());
    emitOtaStatus(deploymentId.c_str(), "FAILED", "failed", "Insufficient OTA partition space");
    http.end();
    otaInProgress = false;
    return;
  }

  // 3. Stage: INSTALLING
  emitOtaStatus(deploymentId.c_str(), "INSTALLING", "in_progress");

  WiFiClient* stream = http.getStreamPtr();
  size_t written = Update.writeStream(*stream);

  Serial.printf("[OTA] Flashed %d of %d bytes\n", written, contentLength);

  if (written != (size_t)contentLength) {
    Serial.printf("[OTA Error] Incomplete write: %d/%d\n", written, contentLength);
    emitOtaStatus(deploymentId.c_str(), "FAILED", "failed", "Written bytes mismatch");
    Update.abort();
    http.end();
    otaInProgress = false;
    return;
  }

  if (!Update.end()) {
    Serial.printf("[OTA Error] Update.end() failed: %s\n", Update.errorString());
    emitOtaStatus(deploymentId.c_str(), "FAILED", "failed", Update.errorString());
    http.end();
    otaInProgress = false;
    return;
  }

  http.end();

  // 4. Stage: REBOOTING & SUCCESS
  emitOtaStatus(deploymentId.c_str(), "REBOOTING", "in_progress");
  emitOtaStatus(deploymentId.c_str(), "SUCCESS", "completed");
  
  // Ensure MQTT packets are sent
  mqttClient.loop();
  delay(1200);

  Serial.println("[OTA Success] Rebooting ESP32-S3 into new firmware partition!");
  ESP.restart();
}

// ── Inbound Command Parsing ──────────────────────────────────────────────────
void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  String message;
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  Serial.printf("[MQTT Inbound] Topic: %s\nPayload: %s\n", topic, message.c_str());

  // Check if command is ota_update
  if (message.indexOf("\"ota_update\"") >= 0) {
    // Extract firmware_url
    int urlIdx = message.indexOf("\"firmware_url\":");
    int depIdx = message.indexOf("\"deployment_id\":");

    if (urlIdx > 0 && depIdx > 0) {
      int urlStart = message.indexOf("\"", urlIdx + 15) + 1;
      int urlEnd   = message.indexOf("\"", urlStart);
      String firmwareUrl = message.substring(urlStart, urlEnd);

      int depStart = message.indexOf("\"", depIdx + 16) + 1;
      int depEnd   = message.indexOf("\"", depStart);
      String depId = message.substring(depStart, depEnd);

      // Normalize URL if relative
      if (firmwareUrl.startsWith("/")) {
        firmwareUrl = String("http://") + GATEWAY_HOST + firmwareUrl;
      }

      Serial.printf("[Command] OTA requested: url=%s depId=%s\n", firmwareUrl.c_str(), depId.c_str());
      performOTA(firmwareUrl, depId);
    }
  }
}

// ── Wi-Fi Connection ─────────────────────────────────────────────────────────
void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;

  Serial.printf("[Wi-Fi] Connecting to %s", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 25) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n[Wi-Fi] Connected! IP Address: %s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("\n[Wi-Fi Warning] Could not connect to Wi-Fi. Retrying in background...");
  }
}

// ── MQTT Connection ──────────────────────────────────────────────────────────
void connectMQTT() {
  if (mqttClient.connected()) return;
  if (WiFi.status() != WL_CONNECTED) return;

  Serial.printf("[MQTT] Connecting to EdgeFleet broker at %s:%d...\n", GATEWAY_HOST, MQTT_PORT);

  // LWT payload for auto-offline status
  const char* lwtPayload = "{\"status\":\"offline\"}";

  if (mqttClient.connect(DEVICE_ID, topicStatus.c_str(), 1, true, lwtPayload)) {
    Serial.println("[MQTT] Connected successfully!");

    // Subscribe to commands topic
    mqttClient.subscribe(topicCommands.c_str(), 1);
    Serial.printf("[MQTT] Subscribed to %s\n", topicCommands.c_str());

    // Send online status announcement
    char statusBuf[256];
    snprintf(statusBuf, sizeof(statusBuf),
      "{\"status\":\"online\",\"uptime_seconds\":%lu,\"ip_address\":\"%s\",\"firmware_version\":\"%s\",\"board_variant\":\"%s\"}",
      millis() / 1000, WiFi.localIP().toString().c_str(), CURRENT_VERSION, BOARD_VARIANT);
    mqttClient.publish(topicStatus.c_str(), statusBuf, true);

  } else {
    Serial.printf("[MQTT Error] Connection failed, rc=%d. Will retry...\n", mqttClient.state());
  }
}

// ── Telemetry Transmission ───────────────────────────────────────────────────
void sendTelemetry() {
  if (!mqttClient.connected()) return;

  // Read internal sensors or simulated telemetry
  float tempC = temperatureRead(); // ESP32-S3 internal temperature sensor
  long rssi = WiFi.RSSI();
  uint32_t freeHeap = ESP.getFreeHeap();
  unsigned long uptime = millis() / 1000;

  char teleBuf[384];
  snprintf(teleBuf, sizeof(teleBuf),
    "{\"schema_version\":\"1.0\",\"device_id\":\"%s\",\"firmware_version\":\"%s\","
    "\"readings\":{\"temperature\":%.1f,\"wifi_rssi\":%ld,\"free_heap\":%u,\"uptime_seconds\":%lu}}",
    DEVICE_ID, CURRENT_VERSION, tempC, rssi, freeHeap, uptime);

  mqttClient.publish(topicTelemetry.c_str(), teleBuf, false);
  Serial.printf("[Telemetry] %s\n", teleBuf);
}

// ── Arduino Setup & Loop ─────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n==================================================");
  Serial.printf("  EdgeFleet ESP32-S3 Node Firmware v%s\n", CURRENT_VERSION);
  Serial.printf("  Device ID: %s | Board: %s\n", DEVICE_ID, BOARD_VARIANT);
  Serial.println("==================================================");

  if (STATUS_LED_PIN >= 0) {
    pinMode(STATUS_LED_PIN, OUTPUT);
    digitalWrite(STATUS_LED_PIN, HIGH);
  }

  setupTopics();

  mqttClient.setServer(GATEWAY_HOST, MQTT_PORT);
  mqttClient.setCallback(onMqttMessage);
  mqttClient.setBufferSize(1024); // Support larger OTA command packets

  connectWiFi();
  connectMQTT();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  if (!mqttClient.connected() && WiFi.status() == WL_CONNECTED) {
    static unsigned long lastReconnectAttempt = 0;
    if (millis() - lastReconnectAttempt > 4000) {
      lastReconnectAttempt = millis();
      connectMQTT();
    }
  } else {
    mqttClient.loop();
  }

  // Periodic Telemetry
  if (!otaInProgress && (millis() - lastTelemetryTime > TELEMETRY_INTERVAL)) {
    lastTelemetryTime = millis();
    sendTelemetry();

    // Toggle status LED
    if (STATUS_LED_PIN >= 0) {
      digitalWrite(STATUS_LED_PIN, !digitalRead(STATUS_LED_PIN));
    }
  }
}
