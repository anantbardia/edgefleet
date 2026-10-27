#ifndef EDGEFLEET_H
#define EDGEFLEET_H

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <Update.h>
#include <PubSubClient.h>

class EdgeFleetClient {
private:
  WiFiClient _wifiClient;
  PubSubClient _mqttClient;
  
  String _ssid;
  String _password;
  String _gatewayHost;
  int _mqttPort;
  String _deviceId;
  String _version;
  String _boardVariant;

  unsigned long _lastTelemetryTime;
  unsigned long _telemetryInterval;
  bool _otaInProgress;

  String _topicTelemetry;
  String _topicStatus;
  String _topicCommands;
  String _topicUpdateStatus;

  static EdgeFleetClient* _instance;

  static void _mqttCallback(char* topic, byte* payload, unsigned int length) {
    if (_instance) {
      _instance->handleMqttMessage(topic, payload, length);
    }
  }

public:
  EdgeFleetClient() 
    : _mqttClient(_wifiClient), 
      _mqttPort(1883), 
      _boardVariant("ESP32-S3"),
      _lastTelemetryTime(0), 
      _telemetryInterval(5000), 
      _otaInProgress(false) {
    _instance = this;
  }

  void begin(const char* ssid, const char* password, const char* gateway_ip, const char* device_id = "esp32-s3-01", const char* version = "1.0.0", int mqtt_port = 1883) {
    _ssid = ssid;
    _password = password;
    _gatewayHost = gateway_ip;
    _deviceId = device_id;
    _version = version;
    _mqttPort = mqtt_port;

    _topicTelemetry    = "edgefleet/v1/devices/" + _deviceId + "/telemetry";
    _topicStatus       = "edgefleet/v1/devices/" + _deviceId + "/status";
    _topicCommands     = "edgefleet/v1/devices/" + _deviceId + "/commands";
    _topicUpdateStatus = "edgefleet/v1/devices/" + _deviceId + "/update/status";

    if (!Serial) {
      Serial.begin(115200);
    }
    delay(500);

    Serial.println("\n==================================================");
    Serial.printf("  EdgeFleet Node: %s (v%s)\n", _deviceId.c_str(), _version.c_str());
    Serial.printf("  Gateway Host  : %s:%d\n", _gatewayHost.c_str(), _mqttPort);
    Serial.println("==================================================");

    _mqttClient.setServer(_gatewayHost.c_str(), _mqttPort);
    _mqttClient.setCallback(_mqttCallback);

    connectWiFi();
    connectMQTT();
  }

  void loop() {
    if (WiFi.status() != WL_CONNECTED) {
      connectWiFi();
    }

    if (!_mqttClient.connected() && WiFi.status() == WL_CONNECTED) {
      static unsigned long lastReconnect = 0;
      if (millis() - lastReconnect > 4000) {
        lastReconnect = millis();
        connectMQTT();
      }
    } else {
      _mqttClient.loop();
    }

    if (!_otaInProgress && (millis() - _lastTelemetryTime > _telemetryInterval)) {
      _lastTelemetryTime = millis();
      sendTelemetry();
    }
  }

  void sendTelemetry(const char* customJsonReadings = nullptr) {
    if (!_mqttClient.connected()) return;

    char teleBuf[384];
    if (customJsonReadings && strlen(customJsonReadings) > 0) {
      snprintf(teleBuf, sizeof(teleBuf),
        "{\"device_id\":\"%s\",\"firmware_version\":\"%s\",\"readings\":%s}",
        _deviceId.c_str(), _version.c_str(), customJsonReadings);
    } else {
      float tempC = temperatureRead();
      long rssi = WiFi.RSSI();
      uint32_t freeHeap = ESP.getFreeHeap();
      unsigned long uptime = millis() / 1000;

      snprintf(teleBuf, sizeof(teleBuf),
        "{\"device_id\":\"%s\",\"firmware_version\":\"%s\","
        "\"readings\":{\"temperature\":%.1f,\"wifi_rssi\":%ld,\"free_heap\":%u,\"uptime_seconds\":%lu}}",
        _deviceId.c_str(), _version.c_str(), tempC, rssi, freeHeap, uptime);
    }

    _mqttClient.publish(_topicTelemetry.c_str(), teleBuf, false);
    Serial.printf("[Telemetry] %s\n", teleBuf);
  }

  void emitOtaStatus(const char* depId, const char* stage, const char* status, const char* err = nullptr) {
    char buf[384];
    if (err) {
      snprintf(buf, sizeof(buf),
        "{\"schema_version\":\"1.0\",\"device_id\":\"%s\",\"deployment_id\":\"%s\","
        "\"stage\":\"%s\",\"status\":\"%s\",\"error\":\"%s\"}",
        _deviceId.c_str(), depId, stage, status, err);
    } else {
      snprintf(buf, sizeof(buf),
        "{\"schema_version\":\"1.0\",\"device_id\":\"%s\",\"deployment_id\":\"%s\","
        "\"stage\":\"%s\",\"status\":\"%s\"}",
        _deviceId.c_str(), depId, stage, status);
    }
    Serial.printf("[EdgeFleet OTA] %s -> %s\n", stage, status);
    _mqttClient.publish(_topicUpdateStatus.c_str(), buf, false);
  }

  void performOTA(String downloadUrl, String deploymentId) {
    _otaInProgress = true;
    Serial.println("\n[OTA] Starting OTA update routine...");
    Serial.printf("[OTA] Target URL: %s\n", downloadUrl.c_str());

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
      _otaInProgress = false;
      return;
    }

    int contentLength = http.getSize();
    Serial.printf("[OTA] Content-Length: %d bytes\n", contentLength);

    if (contentLength <= 0 || !Update.begin(contentLength, U_FLASH)) {
      Serial.printf("[OTA Error] Space check failed: %s\n", Update.errorString());
      emitOtaStatus(deploymentId.c_str(), "FAILED", "failed", "Insufficient partition space");
      http.end();
      _otaInProgress = false;
      return;
    }

    emitOtaStatus(deploymentId.c_str(), "INSTALLING", "in_progress");
    WiFiClient* stream = http.getStreamPtr();
    size_t written = Update.writeStream(*stream);

    Serial.printf("[OTA] Flashed %d of %d bytes\n", written, contentLength);

    if (written != (size_t)contentLength || !Update.end()) {
      Serial.printf("[OTA Error] Write/verification failed: %s\n", Update.errorString());
      emitOtaStatus(deploymentId.c_str(), "FAILED", "failed", "Flash write mismatch");
      Update.abort();
      http.end();
      _otaInProgress = false;
      return;
    }

    http.end();
    emitOtaStatus(deploymentId.c_str(), "REBOOTING", "in_progress");
    emitOtaStatus(deploymentId.c_str(), "SUCCESS", "completed");

    _mqttClient.loop();
    delay(1200);

    Serial.println("[OTA Success] Rebooting ESP32 into new firmware partition!");
    ESP.restart();
  }

  void handleMqttMessage(char* topic, byte* payload, unsigned int length) {
    String message;
    for (unsigned int i = 0; i < length; i++) message += (char)payload[i];

    Serial.printf("[MQTT Inbound] Topic: %s\nPayload: %s\n", topic, message.c_str());

    if (message.indexOf("\"ota_update\"") >= 0) {
      int urlIdx = message.indexOf("\"firmware_url\"");
      int depIdx = message.indexOf("\"deployment_id\"");

      if (urlIdx > 0 && depIdx > 0) {
        int urlStart = message.indexOf("\"", urlIdx + 15) + 1;
        int urlEnd   = message.indexOf("\"", urlStart);
        String firmwareUrl = message.substring(urlStart, urlEnd);

        int depStart = message.indexOf("\"", depIdx + 16) + 1;
        int depEnd   = message.indexOf("\"", depStart);
        String depId = message.substring(depStart, depEnd);

        if (firmwareUrl.startsWith("/")) {
          firmwareUrl = "http://" + _gatewayHost + firmwareUrl;
        }

        Serial.printf("[Command] OTA requested: url=%s depId=%s\n", firmwareUrl.c_str(), depId.c_str());
        performOTA(firmwareUrl, depId);
      }
    }
  }

  void connectWiFi() {
    if (WiFi.status() == WL_CONNECTED) return;
    Serial.printf("[Wi-Fi] Connecting to %s", _ssid.c_str());
    WiFi.mode(WIFI_STA);
    WiFi.begin(_ssid.c_str(), _password.c_str());

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 25) {
      delay(500);
      Serial.print(".");
      attempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
      Serial.printf("\n[Wi-Fi] Connected! Local IP: %s\n", WiFi.localIP().toString().c_str());
    } else {
      Serial.println("\n[Wi-Fi Warning] Could not connect. Retrying...");
    }
  }

  void connectMQTT() {
    if (_mqttClient.connected() || WiFi.status() != WL_CONNECTED) return;
    Serial.printf("[MQTT] Connecting to EdgeFleet broker at %s:%d...\n", _gatewayHost.c_str(), _mqttPort);

    const char* lwtPayload = "{\"status\":\"offline\"}";
    if (_mqttClient.connect(_deviceId.c_str(), _topicStatus.c_str(), 1, true, lwtPayload)) {
      Serial.println("[MQTT] Connected successfully!");
      _mqttClient.subscribe(_topicCommands.c_str(), 1);

      char statusBuf[256];
      snprintf(statusBuf, sizeof(statusBuf),
        "{\"status\":\"online\",\"uptime_seconds\":%lu,\"ip_address\":\"%s\",\"firmware_version\":\"%s\",\"board_variant\":\"%s\"}",
        millis() / 1000, WiFi.localIP().toString().c_str(), _version.c_str(), _boardVariant.c_str());
      _mqttClient.publish(_topicStatus.c_str(), statusBuf, true);
    } else {
      Serial.printf("[MQTT Error] Connection failed, rc=%d. Retrying...\n", _mqttClient.state());
    }
  }
};

__attribute__((weak)) EdgeFleetClient* EdgeFleetClient::_instance = nullptr;
static EdgeFleetClient EdgeFleet;

#endif // EDGEFLEET_H
