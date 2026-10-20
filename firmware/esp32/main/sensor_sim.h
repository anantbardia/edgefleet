#pragma once

typedef struct {
    float temperature;
    float humidity;
    uint32_t heap_free;
    int wifi_rssi;
} sensor_readings_t;

void sensor_sim_init(void);
void sensor_sim_read(sensor_readings_t *out_readings);
