#include "ota_handler.h"
#include "device_config.h"
#include "mqtt_client.h"

#include <string.h>
#include "esp_log.h"
#include "esp_ota_ops.h"
#include "esp_https_ota.h"
#include "esp_http_client.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "ota_handler";

static void emit_ota_stage(const char *dep_id, const char *stage, const char *status, const char *err)
{
    char json_buf[384];
    if (err) {
        snprintf(json_buf, sizeof(json_buf),
            "{\"schema_version\":\"1.0\",\"device_id\":\"%s\",\"deployment_id\":\"%s\","
            "\"stage\":\"%s\",\"status\":\"%s\",\"error\":\"%s\"}",
            EDGEFLEET_DEVICE_ID, dep_id, stage, status, err);
    } else {
        snprintf(json_buf, sizeof(json_buf),
            "{\"schema_version\":\"1.0\",\"device_id\":\"%s\",\"deployment_id\":\"%s\","
            "\"stage\":\"%s\",\"status\":\"%s\"}",
            EDGEFLEET_DEVICE_ID, dep_id, stage, status);
    }

    char topic[128];
    snprintf(topic, sizeof(topic), "edgefleet/v1/devices/%s/update/status", EDGEFLEET_DEVICE_ID);
    mqtt_client_publish(topic, json_buf, 1);
}

static void ota_task(void *pvParameter)
{
    ota_command_t cmd;
    memcpy(&cmd, pvParameter, sizeof(ota_command_t));
    free(pvParameter);

    ESP_LOGI(TAG, "Starting OTA task for URL: %s", cmd.firmware_url);
    emit_ota_stage(cmd.deployment_id, "TRANSFERRING", "in_progress", NULL);

    esp_http_client_config_t http_config = {
        .url = cmd.firmware_url,
        .timeout_ms = 30000,
        .keep_alive_enable = true,
    };

    esp_https_ota_config_t ota_config = {
        .http_config = &http_config,
    };

    emit_ota_stage(cmd.deployment_id, "VERIFYING", "in_progress", NULL);

    esp_https_ota_handle_t https_ota_handle = NULL;
    esp_err_t err = esp_https_ota_begin(&ota_config, &https_ota_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_https_ota_begin failed: %s", esp_err_to_name(err));
        emit_ota_stage(cmd.deployment_id, "FAILED", "failed", esp_err_to_name(err));
        vTaskDelete(NULL);
        return;
    }

    emit_ota_stage(cmd.deployment_id, "INSTALLING", "in_progress", NULL);

    while (1) {
        err = esp_https_ota_perform(https_ota_handle);
        if (err != ESP_ERR_HTTPS_OTA_IN_PROGRESS) {
            break;
        }
    }

    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_https_ota_perform failed: %s", esp_err_to_name(err));
        esp_https_ota_abort(https_ota_handle);
        emit_ota_stage(cmd.deployment_id, "FAILED", "failed", esp_err_to_name(err));
        vTaskDelete(NULL);
        return;
    }

    esp_err_t ota_finish_err = esp_https_ota_finish(https_ota_handle);
    if (ota_finish_err != ESP_OK) {
        ESP_LOGE(TAG, "esp_https_ota_finish failed: %s", esp_err_to_name(ota_finish_err));
        emit_ota_stage(cmd.deployment_id, "FAILED", "failed", esp_err_to_name(ota_finish_err));
        vTaskDelete(NULL);
        return;
    }

    ESP_LOGI(TAG, "Firmware written successfully! Rebooting target node...");
    emit_ota_stage(cmd.deployment_id, "REBOOTING", "in_progress", NULL);

    vTaskDelay(pdMS_TO_TICKS(1500));
    esp_restart();
}

esp_err_t ota_handler_start(const ota_command_t *cmd)
{
    if (!cmd) return ESP_ERR_INVALID_ARG;

    ota_command_t *task_param = malloc(sizeof(ota_command_t));
    if (!task_param) return ESP_ERR_NO_MEM;
    memcpy(task_param, cmd, sizeof(ota_command_t));

    BaseType_t ret = xTaskCreate(ota_task, "ota_task", 8192, task_param, 5, NULL);
    if (ret != pdPASS) {
        free(task_param);
        return ESP_FAIL;
    }
    return ESP_OK;
}
