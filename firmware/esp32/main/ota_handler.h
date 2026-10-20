#pragma once

#include "esp_err.h"

typedef struct {
    char deployment_id[64];
    char release_id[64];
    char firmware_url[256];
    char expected_sha256[65];
    char expected_version[32];
} ota_command_t;

esp_err_t ota_handler_start(const ota_command_t *cmd);
