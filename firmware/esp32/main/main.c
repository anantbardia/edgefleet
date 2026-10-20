#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "nvs_flash.h"

#include "device_config.h"
#include "wifi_manager.h"
#include "mqtt_client.h"
#include "sensor_sim.h"
#include "health_check.h"

static const char *TAG = "edgefleet_main";

void telemetry_loop_task(void *pvParameters)
{
    sensor_readings_t readings;
    uint32_t uptime_sec = 0;
    uint32_t heartbeat_tick = 0;

    while (1) {
        vTaskDelay(pdMS_TO_TICKS(TELEMETRY_INTERVAL_MS));
        uptime_sec += (TELEMETRY_INTERVAL_MS / 1000);
        heartbeat_tick += TELEMETRY_INTERVAL_MS;

        // Read simulated sensors
        sensor_sim_read(&readings);

        // Emit JSON telemetry over UART / USB cable for direct cable monitoring and serial gateway
        printf("{\"schema_version\":\"1.0\",\"device_id\":\"%s\",\"temperature\":%.2f,\"humidity\":%.2f,\"heap_free\":%lu,\"rssi\":%d,\"uptime\":%lu}\n",
               EDGEFLEET_DEVICE_ID, readings.temperature, readings.humidity, (unsigned long)readings.heap_free, readings.wifi_rssi, (unsigned long)uptime_sec);
        fflush(stdout);

        if (wifi_manager_is_connected() && mqtt_client_is_connected()) {
            // Publish telemetry reading via MQTT
            mqtt_client_publish_telemetry(
                readings.temperature,
                readings.humidity,
                readings.heap_free,
                readings.wifi_rssi
            );

            // Publish status heartbeat periodically
            if (heartbeat_tick >= HEARTBEAT_INTERVAL_MS) {
                heartbeat_tick = 0;
                mqtt_client_publish_status(true, wifi_manager_get_ip(), uptime_sec);
            }
        }
    }
}

void app_main(void)
{
    ESP_LOGI(TAG, "===============================================");
    ESP_LOGI(TAG, "EdgeFleet Node Starting: %s (v%s)", EDGEFLEET_DEVICE_ID, EDGEFLEET_FIRMWARE_VER);
    ESP_LOGI(TAG, "Target Board: %s", EDGEFLEET_BOARD_VARIANT);
    ESP_LOGI(TAG, "===============================================");

    // 1. Initialize NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    // 2. Validate current partition and confirm OTA if this was a new update
    health_check_confirm_ota_success();

    // 3. Initialize simulated sensors
    sensor_sim_init();

    // 4. Initialize Wi-Fi
    wifi_manager_init();

    // 5. Initialize MQTT client
    mqtt_client_init();

    // 6. Start telemetry publication task
    xTaskCreate(telemetry_loop_task, "telemetry_loop", 4096, NULL, 4, NULL);

    ESP_LOGI(TAG, "EdgeFleet initialization complete. Running main task loop.");
}
