#include "sensor_sim.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include <stdlib.h>

static float s_temp = 24.2f;
static float s_humidity = 55.0f;

void sensor_sim_init(void)
{
    // Initialize baseline values
    s_temp = 24.2f;
    s_humidity = 55.0f;
}

void sensor_sim_read(sensor_readings_t *out_readings)
{
    if (!out_readings) return;

    // Simulate gentle sensor drift
    float temp_drift = ((float)(rand() % 100) - 50.0f) / 250.0f;
    float hum_drift = ((float)(rand() % 100) - 50.0f) / 100.0f;

    s_temp += temp_drift;
    if (s_temp < 15.0f) s_temp = 15.0f;
    if (s_temp > 35.0f) s_temp = 35.0f;

    s_humidity += hum_drift;
    if (s_humidity < 30.0f) s_humidity = 30.0f;
    if (s_humidity > 80.0f) s_humidity = 80.0f;

    out_readings->temperature = s_temp;
    out_readings->humidity = s_humidity;
    out_readings->heap_free = esp_get_free_heap_size();

    wifi_ap_record_t ap_info;
    if (esp_wifi_sta_get_ap_info(&ap_info) == ESP_OK) {
        out_readings->wifi_rssi = ap_info.rssi;
    } else {
        out_readings->wifi_rssi = -60;
    }
}
