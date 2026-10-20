#pragma once

#include "esp_err.h"
#include <stdbool.h>

esp_err_t mqtt_client_init(void);
bool mqtt_client_is_connected(void);
int mqtt_client_publish(const char *topic, const char *data, int qos);
void mqtt_client_publish_telemetry(float temp, float humidity, uint32_t heap, int rssi);
void mqtt_client_publish_status(bool is_online, const char *ip_addr, uint32_t uptime);
