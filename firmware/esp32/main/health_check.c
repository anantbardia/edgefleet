#include "health_check.h"
#include "esp_ota_ops.h"
#include "esp_system.h"
#include "esp_log.h"

static const char *TAG = "health_check";

esp_err_t health_check_run_self_test(void)
{
    // 1. Check free heap > 40KB
    uint32_t free_heap = esp_get_free_heap_size();
    if (free_heap < 40960) {
        ESP_LOGE(TAG, "Self-test FAILED: low heap memory (%lu bytes)", free_heap);
        return ESP_FAIL;
    }

    ESP_LOGI(TAG, "Self-test passed! Heap available: %lu bytes", free_heap);
    return ESP_OK;
}

esp_err_t health_check_confirm_ota_success(void)
{
    const esp_partition_t *running = esp_ota_get_running_partition();
    esp_ota_img_states_t ota_state;

    if (esp_ota_get_state_partition(running, &ota_state) == ESP_OK) {
        if (ota_state == ESP_OTA_IMG_PENDING_VERIFY) {
            ESP_LOGI(TAG, "Image in pending verify state. Running health checks before confirming...");
            if (health_check_run_self_test() == ESP_OK) {
                ESP_LOGI(TAG, "Health check PASSED. Confirming firmware and cancelling rollback...");
                return esp_ota_mark_app_valid_cancel_rollback();
            } else {
                ESP_LOGE(TAG, "Health check FAILED. Triggering automatic rollback to previous partition!");
                health_check_trigger_rollback();
                return ESP_FAIL;
            }
        }
    }
    return ESP_OK;
}

void health_check_trigger_rollback(void)
{
    esp_ota_mark_app_invalid_rollback_and_reboot();
}
