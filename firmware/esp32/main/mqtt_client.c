#include "mqtt_client.h"
#include "device_config.h"
#include "ota_handler.h"

#include <stdio.h>
#include <string.h>
#include "esp_log.h"
#include "mqtt_client.h"
#include "cJSON.h"

static const char *TAG = "mqtt_client";
static esp_mqtt_client_handle_t s_client = NULL;
static bool s_connected = false;

static void mqtt_event_handler(void *handler_args, esp_event_base_t base, int32_t event_id, void *event_data)
{
    esp_mqtt_event_handle_t event = event_data;
    switch ((esp_mqtt_event_id_t)event_id) {
    case MQTT_EVENT_CONNECTED: {
        ESP_LOGI(TAG, "Connected to EdgeFleet MQTT broker!");
        s_connected = true;

        // Subscribe to commands topic
        char cmd_topic[128];
        snprintf(cmd_topic, sizeof(cmd_topic), "edgefleet/v1/devices/%s/commands", EDGEFLEET_DEVICE_ID);
        esp_mqtt_client_subscribe(s_client, cmd_topic, 1);
        ESP_LOGI(TAG, "Subscribed to %s", cmd_topic);
        break;
    }
    case MQTT_EVENT_DISCONNECTED:
        ESP_LOGW(TAG, "Disconnected from MQTT broker");
        s_connected = false;
        break;

    case MQTT_EVENT_DATA: {
        ESP_LOGI(TAG, "Incoming data on topic: %.*s", event->topic_len, event->topic);
        
        // Null-terminate payload
        char *payload = malloc(event->data_len + 1);
        if (payload) {
            memcpy(payload, event->data, event->data_len);
            payload[event->data_len] = '\0';

            cJSON *root = cJSON_Parse(payload);
            if (root) {
                cJSON *cmd_item = cJSON_GetObjectItem(root, "command");
                if (cmd_item && cJSON_IsString(cmd_item) && strcmp(cmd_item->valuestring, "ota_update") == 0) {
                    ota_command_t ota_cmd = {0};
                    cJSON *dep = cJSON_GetObjectItem(root, "deployment_id");
                    cJSON *url = cJSON_GetObjectItem(root, "firmware_url");
                    cJSON *sha = cJSON_GetObjectItem(root, "expected_sha256");
                    cJSON *ver = cJSON_GetObjectItem(root, "expected_version");

                    if (dep) strncpy(ota_cmd.deployment_id, dep->valuestring, sizeof(ota_cmd.deployment_id) - 1);
                    if (url) strncpy(ota_cmd.firmware_url, url->valuestring, sizeof(ota_cmd.firmware_url) - 1);
                    if (sha) strncpy(ota_cmd.expected_sha256, sha->valuestring, sizeof(ota_cmd.expected_sha256) - 1);
                    if (ver) strncpy(ota_cmd.expected_version, ver->valuestring, sizeof(ota_cmd.expected_version) - 1);

                    ESP_LOGI(TAG, "Triggering OTA update from command. URL: %s", ota_cmd.firmware_url);
                    ota_handler_start(&ota_cmd);
                }
                cJSON_Delete(root);
            }
            free(payload);
        }
        break;
    }
    default:
        break;
    }
}

esp_err_t mqtt_client_init(void)
{
    char lwt_topic[128];
    snprintf(lwt_topic, sizeof(lwt_topic), "edgefleet/v1/devices/%s/status", EDGEFLEET_DEVICE_ID);

    char lwt_payload[128];
    snprintf(lwt_payload, sizeof(lwt_payload),
             "{\"schema_version\":\"1.0\",\"device_id\":\"%s\",\"status\":\"offline\"}",
             EDGEFLEET_DEVICE_ID);

    esp_mqtt_client_config_t mqtt_cfg = {
        .broker.address.uri = EDGEFLEET_MQTT_BROKER_URI,
        .credentials.username = EDGEFLEET_MQTT_USER,
        .credentials.authentication.password = EDGEFLEET_MQTT_PASS,
        .session.last_will = {
            .topic = lwt_topic,
            .msg = lwt_payload,
            .msg_len = strlen(lwt_payload),
            .qos = 1,
            .retain = 1,
        },
    };

    s_client = esp_mqtt_client_init(&mqtt_cfg);
    if (!s_client) {
        ESP_LOGE(TAG, "Failed to initialize MQTT client handle");
        return ESP_FAIL;
    }

    esp_mqtt_client_register_event(s_client, ESP_EVENT_ANY_ID, mqtt_event_handler, NULL);
    esp_mqtt_client_start(s_client);
    return ESP_OK;
}

bool mqtt_client_is_connected(void)
{
    return s_connected;
}

int mqtt_client_publish(const char *topic, const char *data, int qos)
{
    if (!s_client || !s_connected) return -1;
    return esp_mqtt_client_publish(s_client, topic, data, 0, qos, 0);
}

void mqtt_client_publish_telemetry(float temp, float humidity, uint32_t heap, int rssi)
{
    if (!s_connected) return;

    char topic[128];
    snprintf(topic, sizeof(topic), "edgefleet/v1/devices/%s/telemetry", EDGEFLEET_DEVICE_ID);

    char payload[256];
    snprintf(payload, sizeof(payload),
        "{\"schema_version\":\"1.0\",\"device_id\":\"%s\",\"firmware_version\":\"%s\","
        "\"readings\":{\"temperature\":%.2f,\"humidity\":%.1f,\"heap_free\":%lu,\"wifi_rssi\":%d}}",
        EDGEFLEET_DEVICE_ID, EDGEFLEET_FIRMWARE_VER, temp, humidity, heap, rssi);

    mqtt_client_publish(topic, payload, 0);
}

void mqtt_client_publish_status(bool is_online, const char *ip_addr, uint32_t uptime)
{
    if (!s_connected) return;

    char topic[128];
    snprintf(topic, sizeof(topic), "edgefleet/v1/devices/%s/status", EDGEFLEET_DEVICE_ID);

    char payload[256];
    snprintf(payload, sizeof(payload),
        "{\"schema_version\":\"1.0\",\"device_id\":\"%s\",\"status\":\"%s\","
        "\"firmware_version\":\"%s\",\"uptime_seconds\":%lu,\"ip_address\":\"%s\",\"reset_reason\":\"power_on\"}",
        EDGEFLEET_DEVICE_ID, is_online ? "online" : "offline",
        EDGEFLEET_FIRMWARE_VER, uptime, ip_addr ? ip_addr : "0.0.0.0");

    mqtt_client_publish(topic, payload, 1);
}
